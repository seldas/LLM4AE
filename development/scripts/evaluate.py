import os
import argparse
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, Trainer, TrainingArguments, DataCollatorForTokenClassification
from datasets import load_metric
from data_loader import load_json_data, NERDataset, tokenize_and_align_labels

metric = load_metric("seqeval")

def compute_metrics(p, label_list):
    predictions, labels = p
    predictions = np.argmax(predictions, axis=2)

    true_predictions = [
        [label_list[p] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    true_labels = [
        [label_list[l] for (p, l) in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]

    results = metric.compute(predictions=true_predictions, references=true_labels)
    return results

def main(folders, model_path="../models/bert_ner_latest", output_file="../results/evaluation_report.txt"):
    print(f"--- Evaluating fine-tuned model: {model_path} ---")
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    
    id2label = model.config.id2label
    label_list = [id2label[i] for i in range(len(id2label))]
    label_to_id = {l: i for i, l in enumerate(label_list)}
    
    # 1. Load Data
    raw_data = load_json_data(folders)
    if not raw_data:
        print("Error: No data found for evaluation.")
        return
        
    # Process all provided data as evaluation data
    tokenized_data = tokenize_and_align_labels(raw_data, tokenizer, label_to_id)
    eval_dataset = NERDataset(tokenized_data)
    
    # 2. Setup Evaluator
    training_args = TrainingArguments(
        output_dir="../results/tmp",
        per_device_eval_batch_size=8,
        report_to="none"
    )
    
    data_collator = DataCollatorForTokenClassification(tokenizer)
    
    trainer = Trainer(
        model=model,
        args=training_args,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer
    )

    # 3. Predict and Metrics
    predictions, labels, _ = trainer.predict(eval_dataset)
    results = compute_metrics((predictions, labels), label_list)
    
    # 4. Save results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("--- NER Model Evaluation Report ---\n\n")
        f.write(f"Model: {os.path.abspath(model_path)}\n")
        f.write(f"Test Sets: {', '.join(folders)}\n\n")
        
        # Summary metrics
        f.write("Overall Performance:\n")
        f.write(f"Precision: {results['overall_precision']:.4f}\n")
        f.write(f"Recall:    {results['overall_recall']:.4f}\n")
        f.write(f"F1 Score:  {results['overall_f1']:.4f}\n")
        f.write(f"Accuracy:  {results['overall_accuracy']:.4f}\n\n")
        
        # Per-entity metrics
        f.write("Per-Entity Report:\n")
        f.write(f"{'Entity':<20} | {'Precision':<10} | {'Recall':<10} | {'F1':<10}\n")
        f.write("-" * 60 + "\n")
        for key in sorted(results.keys()):
            if key.startswith("overall") or key == "accuracy":
                continue
            res = results[key]
            f.write(f"{key:<20} | {res['precision']:<10.4f} | {res['recall']:<10.4f} | {res['f1']:<10.4f}\n")
            
    print(f"--- Evaluation complete. Report saved to: {output_file} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folders", nargs="+", required=True, help="List of history folders to evaluate on")
    parser.add_argument("--model", type=str, default="../models/bert_ner_latest")
    args = parser.parse_args()
    
    main(args.folders, args.model)
