import os
import argparse
import numpy as np
from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification, 
    TrainingArguments, 
    Trainer,
    DataCollatorForTokenClassification
)
from datasets import load_metric
from data_loader import load_json_data, prepare_datasets, NERDataset

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

def main(folders, model_path="../models/foundation", output_dir="../models/bert_ner_latest"):
    print(f"--- Starting Fine-tuning Pipeline ---")
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    # 1. Load and Prepare Data
    raw_data = load_json_data(folders)
    if not raw_data:
        print("Error: No data found in provided folders.")
        return

    train_raw, val_raw, label_list, label_to_id, id_to_label = prepare_datasets(raw_data, tokenizer)
    
    train_dataset = NERDataset(train_raw)
    val_dataset = NERDataset(val_raw)
    
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
        report_to="none" # Disable wandb etc for now
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
    os.makedirs(output_dir, exist_ok=True)
    trainer.save_model(output_dir)
    print(f"--- Fine-tuned model saved to: {output_dir} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folders", nargs="+", required=True, help="List of folder names in history/ to use for training")
    parser.add_argument("--base_model", type=str, default="../models/foundation")
    args = parser.parse_args()
    
    main(args.folders, args.base_model)
