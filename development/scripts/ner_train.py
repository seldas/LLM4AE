import os
import json
import argparse
import random
import inspect
import warnings
import subprocess
import numpy as np

from transformers import (
    AutoTokenizer,
    AutoConfig,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification,
)

from data_loader import load_data_from_db, NERDataset, tokenize_and_align_labels


def load_seqeval_metric():
    """
    Compatibility loader for seqeval metric across old/new packages.
    """
    try:
        import evaluate
        return evaluate.load("seqeval")
    except Exception:
        try:
            from datasets import load_metric
            return load_metric("seqeval")
        except Exception as e:
            raise ImportError(
                "Could not load seqeval. Please install:\n"
                "  pip install evaluate seqeval"
            ) from e


metric = load_seqeval_metric()


def build_label_maps(raw_data):
    unique_labels = set()

    for item in raw_data:
        for ann in item.get("annotations", []):
            label = ann.get("label")
            if label is None:
                continue
            label = str(label).strip().upper()
            if label:
                unique_labels.add(label)

    label_list = ["O"]
    for label in sorted(unique_labels):
        label_list.append(f"B-{label}")
        label_list.append(f"I-{label}")

    label_to_id = {label: i for i, label in enumerate(label_list)}
    id_to_label = {i: label for label, i in label_to_id.items()}
    return label_list, label_to_id, id_to_label


def split_raw_data(raw_data, train_ratio=0.7, seed=42):
    raw_data = list(raw_data)
    rng = random.Random(seed)
    rng.shuffle(raw_data)

    split_idx = int(len(raw_data) * train_ratio)
    train_raw = raw_data[:split_idx]
    val_raw = raw_data[split_idx:]
    return train_raw, val_raw


def compute_metrics(eval_pred, label_list):
    predictions, labels = eval_pred

    if isinstance(predictions, tuple):
        predictions = predictions[0]

    predictions = np.argmax(predictions, axis=2)

    true_predictions = []
    true_labels = []

    for prediction, label in zip(predictions, labels):
        pred_labels = []
        gold_labels = []
        for p, l in zip(prediction, label):
            if l == -100:
                continue
            pred_labels.append(label_list[int(p)])
            gold_labels.append(label_list[int(l)])
        true_predictions.append(pred_labels)
        true_labels.append(gold_labels)

    results = metric.compute(predictions=true_predictions, references=true_labels)

    return {
        "precision": results.get("overall_precision", 0.0),
        "recall": results.get("overall_recall", 0.0),
        "f1": results.get("overall_f1", 0.0),
        "accuracy": results.get("overall_accuracy", 0.0),
    }


def get_world_size():
    try:
        return int(os.environ.get("WORLD_SIZE", "1"))
    except Exception:
        return 1


def get_local_rank():
    try:
        return int(os.environ.get("LOCAL_RANK", "-1"))
    except Exception:
        return -1


def can_import_torch():
    try:
        import torch
        return True
    except Exception:
        return False


def gpu_runtime_probe():
    """
    Best-effort probe of CUDA/NVML health.
    Returns dict with:
      - torch_ok
      - cuda_available
      - device_count
      - nvml_ok
      - notes
    """
    info = {
        "torch_ok": False,
        "cuda_available": False,
        "device_count": 0,
        "nvml_ok": False,
        "notes": [],
    }

    if not can_import_torch():
        info["notes"].append("torch import failed")
        return info

    import torch

    info["torch_ok"] = True

    try:
        info["cuda_available"] = torch.cuda.is_available()
    except Exception as e:
        info["notes"].append(f"torch.cuda.is_available() failed: {e}")
        return info

    if info["cuda_available"]:
        try:
            info["device_count"] = torch.cuda.device_count()
        except Exception as e:
            info["notes"].append(f"torch.cuda.device_count() failed: {e}")

    # Try pynvml if available
    try:
        import pynvml
        pynvml.nvmlInit()
        _ = pynvml.nvmlDeviceGetCount()
        pynvml.nvmlShutdown()
        info["nvml_ok"] = True
    except Exception as e:
        info["notes"].append(f"NVML probe failed: {e}")

    # Optional shell probe
    try:
        proc = subprocess.run(
            ["nvidia-smi", "-L"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            info["notes"].append(f"nvidia-smi failed: {proc.stderr.strip()}")
    except Exception as e:
        info["notes"].append(f"nvidia-smi probe failed: {e}")

    return info


def choose_ddp_backend(user_choice="auto"):
    """
    Decide DDP backend.
    - If user explicitly chose nccl/gloo, use it.
    - If auto:
        * single process -> None
        * distributed + healthy NVML/CUDA -> nccl
        * distributed + unhealthy NVML -> gloo
    """
    world_size = get_world_size()
    if world_size <= 1:
        return None

    if user_choice in ("nccl", "gloo"):
        return user_choice

    probe = gpu_runtime_probe()

    if probe["cuda_available"] and probe["nvml_ok"]:
        return "nccl"

    warnings.warn(
        "Distributed launch detected but CUDA/NVML probe looks unhealthy. "
        "Falling back to ddp_backend='gloo'. "
        f"Probe notes: {probe['notes']}"
    )
    return "gloo"


def load_token_classification_model(model_path, num_labels, id_to_label, label_to_id):
    """
    Load model while allowing classifier head shape mismatch.
    """
    config = AutoConfig.from_pretrained(model_path)
    config.num_labels = num_labels
    config.id2label = id_to_label
    config.label2id = label_to_id

    print(f"Loading token classification model from: {model_path}")
    print(f"Target num_labels = {num_labels}")

    model = AutoModelForTokenClassification.from_pretrained(
        model_path,
        config=config,
        ignore_mismatched_sizes=True,
    )

    classifier = getattr(model, "classifier", None)
    if classifier is not None and hasattr(classifier, "out_features"):
        print(f"classifier.out_features = {classifier.out_features}")

    return model


def build_training_arguments(
    output_dir,
    logging_dir,
    ddp_backend="auto",
    no_cuda=False,
):
    """
    Build TrainingArguments compatibly across transformers versions.
    """
    world_size = get_world_size()
    backend = choose_ddp_backend(ddp_backend)

    kwargs = {
        "output_dir": output_dir,
        "learning_rate": 2e-5,
        "per_device_train_batch_size": 16,
        "per_device_eval_batch_size": 16,
        "num_train_epochs": 3,
        "weight_decay": 0.01,
        "save_total_limit": 2,
        "logging_dir": logging_dir,
        "report_to": "none",
    }

    sig = inspect.signature(TrainingArguments.__init__)
    params = sig.parameters

    if "evaluation_strategy" in params:
        kwargs["evaluation_strategy"] = "epoch"
    elif "eval_strategy" in params:
        kwargs["eval_strategy"] = "epoch"

    if "save_strategy" in params:
        kwargs["save_strategy"] = "epoch"

    if "logging_strategy" in params:
        kwargs["logging_strategy"] = "epoch"

    if "load_best_model_at_end" in params:
        kwargs["load_best_model_at_end"] = False

    if "ddp_find_unused_parameters" in params and world_size > 1:
        kwargs["ddp_find_unused_parameters"] = False

    if "ddp_backend" in params and backend is not None:
        kwargs["ddp_backend"] = backend

    # transformers version compatibility
    if no_cuda:
        if "no_cuda" in params:
            kwargs["no_cuda"] = True
        elif "use_cpu" in params:
            kwargs["use_cpu"] = True

    return TrainingArguments(**kwargs)


def maybe_fail_early_for_bad_distributed_env(ddp_backend_choice):
    """
    Fail early with a clearer message for known broken NCCL/NVML setups.
    """
    world_size = get_world_size()
    if world_size <= 1:
        return

    chosen = choose_ddp_backend(ddp_backend_choice)
    probe = gpu_runtime_probe()

    print(f"Distributed launch detected: WORLD_SIZE={world_size}, LOCAL_RANK={get_local_rank()}")
    print(f"Chosen DDP backend: {chosen}")
    print(f"GPU probe: {json.dumps(probe, indent=2)}")

    # If user explicitly requested NCCL but NVML is broken, fail before training.
    if chosen == "nccl" and not probe["nvml_ok"]:
        raise RuntimeError(
            "Distributed NCCL training requested, but NVML/CUDA runtime looks unhealthy.\n"
            "This matches errors like: nvmlInit_v2() failed: Driver/library version mismatch\n\n"
            "Recommended fixes:\n"
            "1. Repair the NVIDIA driver/container CUDA runtime mismatch, OR\n"
            "2. Relaunch with --ddp_backend gloo, OR\n"
            "3. Run single-process training (do not use torchrun / set WORLD_SIZE=1).\n"
        )


def main(
    include_ai=False,
    model_path="../models/foundation",
    output_dir="../models/bert_ner_latest",
    data_dir=None,
    seed=42,
    ddp_backend="auto",
    no_cuda=False,
):
    print("--- Starting Fine-tuning Pipeline ---")

    os.makedirs(output_dir, exist_ok=True)
    logging_dir = os.path.join(output_dir, "logs")
    os.makedirs(logging_dir, exist_ok=True)

    maybe_fail_early_for_bad_distributed_env(ddp_backend)

    tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)

    train_raw = None
    val_raw = None

    train_json = os.path.join(data_dir, "train_dataset.json") if data_dir else None
    val_json = os.path.join(data_dir, "val_dataset.json") if data_dir else None

    # 1. Load raw data
    if data_dir and os.path.exists(train_json) and os.path.exists(val_json):
        print(f"Loading existing datasets from {data_dir} ...")

        with open(train_json, "r", encoding="utf-8") as f:
            train_raw = json.load(f)
        with open(val_json, "r", encoding="utf-8") as f:
            val_raw = json.load(f)

        if not train_raw or not val_raw:
            raise ValueError(
                f"Loaded dataset files are empty or invalid: "
                f"train={len(train_raw) if train_raw else 0}, "
                f"val={len(val_raw) if val_raw else 0}"
            )

        label_list, label_to_id, id_to_label = build_label_maps(train_raw + val_raw)

    else:
        print(f"Loading data from DB (include_ai={include_ai}) ...")
        raw_data = load_data_from_db(include_ai=include_ai)

        if not raw_data:
            raise ValueError("No data found in database.")

        print(f"Loaded {len(raw_data)} records.")
        train_raw, val_raw = split_raw_data(raw_data, train_ratio=0.7, seed=seed)

        if not train_raw or not val_raw:
            raise ValueError(
                f"Dataset split failed: train={len(train_raw)}, val={len(val_raw)}. "
                "Need enough records for both sets."
            )

        label_list, label_to_id, id_to_label = build_label_maps(train_raw + val_raw)

        print(f"Saving train/val raw datasets to {output_dir} for reproducibility ...")
        with open(os.path.join(output_dir, "train_dataset.json"), "w", encoding="utf-8") as f:
            json.dump(train_raw, f, ensure_ascii=False, indent=2)
        with open(os.path.join(output_dir, "val_dataset.json"), "w", encoding="utf-8") as f:
            json.dump(val_raw, f, ensure_ascii=False, indent=2)

    if len(label_list) <= 1:
        raise ValueError("Only label 'O' was found. No entity labels were extracted from annotations.")

    print(f"Number of labels: {len(label_list)}")
    print(f"Labels: {label_list}")

    # 2. Tokenize
    print("Tokenizing datasets ...")
    train_processed = tokenize_and_align_labels(train_raw, tokenizer, label_to_id)
    val_processed = tokenize_and_align_labels(val_raw, tokenizer, label_to_id)

    train_dataset = NERDataset(train_processed)
    val_dataset = NERDataset(val_processed)

    # 3. Load model
    model = load_token_classification_model(
        model_path=model_path,
        num_labels=len(label_list),
        id_to_label=id_to_label,
        label_to_id=label_to_id,
    )

    # 4. Training args
    training_args = build_training_arguments(
        output_dir=output_dir,
        logging_dir=logging_dir,
        ddp_backend=ddp_backend,
        no_cuda=no_cuda,
    )

    data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": train_dataset,
        "eval_dataset": val_dataset,
        "data_collator": data_collator,
        "compute_metrics": lambda p: compute_metrics(p, label_list),
    }

    trainer_sig = inspect.signature(Trainer.__init__)
    if "tokenizer" in trainer_sig.parameters:
        trainer_kwargs["tokenizer"] = tokenizer

    trainer = Trainer(**trainer_kwargs)

    # 5. Train
    print("--- Training ---")
    try:
        train_result = trainer.train()
    except Exception as e:
        msg = str(e)
        if (
            "nvmlInit_v2() failed" in msg
            or "Driver/library version mismatch" in msg
            or "DistBackendError" in msg
            or "NCCL error" in msg
        ):
            raise RuntimeError(
                "Distributed GPU training failed because the NVIDIA driver/runtime stack is inconsistent.\n\n"
                "This is an environment issue, not a label/model issue.\n\n"
                "What to do next:\n"
                "1. Best fix: repair the host/container NVIDIA driver/library mismatch.\n"
                "2. Workaround: relaunch with --ddp_backend gloo.\n"
                "3. Safer workaround: do not use torchrun; run single-process training on one GPU.\n"
                "4. Last resort: run with --no_cuda on CPU.\n"
            ) from e
        raise

    print("Training complete.")
    if hasattr(train_result, "metrics"):
        print(json.dumps(train_result.metrics, indent=2))

    # 6. Evaluate
    print("--- Evaluation ---")
    eval_results = trainer.evaluate()
    print(json.dumps(eval_results, indent=2))

    # 7. Save
    print("--- Saving model ---")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    with open(os.path.join(output_dir, "labels.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "label_list": label_list,
                "label_to_id": label_to_id,
                "id_to_label": {str(k): v for k, v in id_to_label.items()},
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"--- Fine-tuned model saved to: {output_dir} ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--include_ai",
        action="store_true",
        help="Include AI-generated annotations for training",
    )
    parser.add_argument(
        "--base_model",
        type=str,
        default="../models/foundation",
        help="Path or HF model name for the base model/checkpoint",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="../models/bert_ner_latest",
        help="Directory to save the fine-tuned model",
    )
    parser.add_argument(
        "--data_dir",
        type=str,
        default=None,
        help="Directory containing train_dataset.json and val_dataset.json to reuse",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic split",
    )
    parser.add_argument(
        "--ddp_backend",
        type=str,
        default="auto",
        choices=["auto", "nccl", "gloo"],
        help="Distributed backend. Use gloo if NCCL/NVML is broken.",
    )
    parser.add_argument(
        "--no_cuda",
        action="store_true",
        help="Force CPU training",
    )

    args = parser.parse_args()

    main(
        include_ai=args.include_ai,
        model_path=args.base_model,
        output_dir=args.output_dir,
        data_dir=args.data_dir,
        seed=args.seed,
        ddp_backend=args.ddp_backend,
        no_cuda=args.no_cuda,
    )