import os
import json
import random
import torch
from transformers import AutoTokenizer

def load_json_data(folders, base_history_dir="../../server/history"):
    all_data = []
    for folder in folders:
        folder_path = os.path.join(base_history_dir, folder)
        if not os.path.exists(folder_path):
            print(f"Warning: Folder {folder_path} does not exist.")
            continue
            
        for filename in os.listdir(folder_path):
            if filename.endswith(".json"):
                with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                    all_data.append(json.load(f))
    return all_data

def tokenize_and_align_labels(examples, tokenizer, label_to_id, max_length=512):
    """
    examples: List of JSON data (one per file/page)
    Converts char-level annotations to BIO-tagged token-level labels.
    """
    tokenized_inputs = []
    
    for item in examples:
        text = item["pages"][0] # Assuming single page for now
        annotations = item.get("annotations", [])
        
        # Tokenize text
        tokenized = tokenizer(
            text, 
            truncation=True, 
            padding="max_length", 
            max_length=max_length, 
            return_offsets_mapping=True
        )
        
        labels = [0] * len(tokenized["input_ids"]) # Default to 'O' tag
        offset_mapping = tokenized["offset_mapping"]
        
        for ann in annotations:
            start_char = ann["textContext"]["start"]
            end_char = ann["textContext"]["end"]
            label_name = ann["label"].upper().strip()
            
            # Find tokens within this range
            for i, (start_tok, end_tok) in enumerate(offset_mapping):
                if start_tok == end_tok == 0: continue # Skip special tokens
                
                # Align logic: BIO format
                if start_tok >= start_char and end_tok <= end_char:
                    bio_prefix = "B-" if start_tok == start_char else "I-"
                    tag = f"{bio_prefix}{label_name}"
                    if tag in label_to_id:
                        labels[i] = label_to_id[tag]
        
        # Mask special tokens in labels (-100 tells PyTorch to ignore them in loss)
        labels = [
            -100 if offset_mapping[i] == (0, 0) else labels[i]
            for i in range(len(labels))
        ]
        
        tokenized["labels"] = labels
        tokenized_inputs.append(tokenized)
        
    return tokenized_inputs

def prepare_datasets(all_data, tokenizer, split_ratio=0.8):
    random.shuffle(all_data)
    split_idx = int(len(all_data) * split_ratio)
    
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]
    
    # Identify unique labels
    unique_labels = set()
    for item in all_data:
        for ann in item.get("annotations", []):
            unique_labels.add(ann["label"].upper().strip())
            
    label_list = ["O"]
    for l in sorted(list(unique_labels)):
        label_list.extend([f"B-{l}", f"I-{l}"])
        
    label_to_id = {l: i for i, l in enumerate(label_list)}
    id_to_label = {i: l for l, i in label_to_id.items()}
    
    train_set = tokenize_and_align_labels(train_data, tokenizer, label_to_id)
    val_set = tokenize_and_align_labels(val_data, tokenizer, label_to_id)
    
    return train_set, val_set, label_list, label_to_id, id_to_label

class NERDataset(torch.utils.data.Dataset):
    def __init__(self, tokenized_data):
        self.data = tokenized_data
        
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        item = {key: torch.tensor(val) for key, val in self.data[idx].items() if key != "offset_mapping"}
        return item
