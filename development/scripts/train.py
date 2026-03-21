import os
import argparse
import numpy as np
import json
from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification, 
    TrainingArguments, 
    Trainer,
    DataCollatorForTokenClassification
)
from datasets import load_metric
from data_loader import load_data_from_db, prepare_datasets, NERDataset, tokenize_and_align_labels

# Load seqeval for evaluation
metric = load_metric("seqeval")

def compute_metrics(p, label_list):
    predictions, labels = p
    predictions = np.argmax(predictions, axis=2)

    # Remove ignored index (special tokens)
    true_predictions = [
        [label_list[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    true_labels = [
        [label_list[l] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]

    results = metric.compute(predictions=true_predictions, references=true_labels)
    return {
        "precision": results["overall_precision"],
        "recall": results["overall_recall"],
        "f1": results["overall_f1"],
        "accuracy": results["overall_accuracy"],
    }

def main(include_ai=False, model_path="../models/foundation", output_dir="../models/bert_ner_latest", data_dir=None):
    print(f"--- Starting Fine-tuning Pipeline ---")
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    os.makedirs(output_dir, exist_ok=True)
    
    train_raw = None
    val_raw = None

    # 1. Load Data
    if data_dir and os.path.exists(os.path.join(data_dir, "train_dataset.json")) and os.path.exists(os.path.join(data_dir, "val_dataset.json")):
        print(f"Loading existing datasets from {data_dir}...")
        with open(os.path.join(data_dir, "train_dataset.json"), "r", encoding="utf-8") as f:
            train_raw = json.load(f)
        with open(os.path.join(data_dir, "val_dataset.json"), "r", encoding="utf-8") as f:
            val_raw = json.load(f)
        
        # We still need to identify labels to build the label_list and ID mapping
        all_data = train_raw + val_raw
        unique_labels = set()
        for item in all_data:
            for ann in item.get("annotations", []):
                unique_labels.add(ann["label"].upper().strip())
        
        label_list = ["O"]
        for l in sorted(list(unique_labels)):
            label_list.extend([f"B-{l}", f"I-{l}"])
        
        label_to_id = {l: i for i, l in enumerate(label_list)}
        id_to_label = {i: l for l, i in label_to_id.items()}
        
        train_processed = tokenize_and_align_labels(train_raw, tokenizer, label_to_id)
        val_processed = tokenize_and_align_labels(val_raw, tokenizer, label_to_id)

    else:
        print(f"Loading data from DB (Include AI: {include_ai})...")
        raw_data = load_data_from_db(include_ai=include_ai)
        if not raw_data:
            print("Error: No data found in database.")
            return

        print(f"Loaded {len(raw_data)} cases. Preparing datasets (70:30 split)...")
        train_processed, val_processed, label_list, label_to_id, id_to_label = prepare_datasets(raw_data, tokenizer)
        
        # For saving, we need the raw data that was used in the split
        # We'll re-extract them from the split indices if we had them, 
        # but prepare_datasets returns tokenized. Let's fix this by splitting first.
        import random
        random.shuffle(raw_data)
        split_idx = int(len(raw_data) * 0.7)
        train_raw = raw_data[:split_idx]
        val_raw = raw_data[split_idx:]
        
        # Save for reproducibility
        print(f"Saving datasets for reproducibility to {output_dir}...")
        with open(os.path.join(output_dir, "train_dataset.json"), "w", encoding="utf-8") as f:
            json.dump(train_raw, f, ensure_ascii=False, indent=2)
        with open(os.path.join(output_dir, "val_dataset.json"), "w", encoding="utf-8") as f:
            json.dump(val_raw, f, ensure_ascii=False, indent=2)

    train_dataset = NERDataset(train_processed)
    val_dataset = NERDataset(val_processed)
    
    # 2. Initialize Model
    model = AutoModelForTokenClassification.from_pretrained(
        model_path, 
        num_labels=len(label_list),
        id2label=id_to_label,
        label2id=label_to_id
    )

    # 3. Training Config
    training_args = TrainingArguments(
        output_dir=output_dir,
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=3,
        weight_decay=0.01,
        save_total_limit=2,
        logging_dir="../logs",
        report_to="none" 
    )

    data_collator = DataCollatorForTokenClassification(tokenizer)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=lambda p: compute_metrics(p, label_list)
    )

    # 4. Train
    print("--- Training ---")
    trainer.train()
    
    # 5. Save Final Model
    trainer.save_model(output_dir)
    print(f"--- Fine-tuned model saved to: {output_dir} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--include_ai", action="store_true", help="Include AI-generated annotations for training")
    parser.add_argument("--base_model", type=str, default="../models/foundation")
    parser.add_argument("--output_dir", type=str, default="../models/bert_ner_latest")
    parser.add_argument("--data_dir", type=str, default=None, help="Directory containing train_dataset.json and val_dataset.json to reuse")
    args = parser.parse_args()
    
    main(args.include_ai, args.base_model, args.output_dir, args.data_dir)
