import os
import sqlite3
import json
import random
import torch
from transformers import AutoTokenizer

def load_data_from_db(db_path="../../server/database/llm4ae.db", include_ai=False):
    """
    Loads narratives and annotations from the SQLite database.
    By default, only human annotations are included.
    """
    if not os.path.exists(db_path):
        # Try absolute path or relative to current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_db_path = os.path.join(script_dir, "../../server/database/llm4ae.db")
        if os.path.exists(alt_db_path):
            db_path = alt_db_path
        else:
            # Try from current directory
            alt_db_path = "server/database/llm4ae.db"
            if os.path.exists(alt_db_path):
                db_path = alt_db_path
            else:
                raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Fetch all cases with narrative and pages
    cases = conn.execute("SELECT id, narrative, pages FROM cases").fetchall()
    
    all_data = []
    for case in cases:
        case_id = case["id"]
        # Use narrative column first, then try pages if empty
        narrative = (case["narrative"] or "").strip()
        pages_raw = case["pages"]
        
        if not narrative and pages_raw:
            try:
                pages_list = json.loads(pages_raw)
                if isinstance(pages_list, list) and len(pages_list) > 0:
                    narrative = pages_list[0]
                elif isinstance(pages_list, str):
                    narrative = pages_list
            except json.JSONDecodeError:
                # If it's not JSON, maybe it's just raw text
                narrative = pages_raw
        
        if not narrative:
            # Skip if still no narrative text
            continue
            
        # Build query for annotations
        query = "SELECT a.label, a.start_offset, a.end_offset, a.text_content, u.role_id FROM annotations a JOIN users u ON a.user_id = u.id WHERE a.case_id = ?"
        if not include_ai:
            query += " AND u.role_id != 4" # Role 4 is AI
            
        anns = conn.execute(query, (case_id,)).fetchall()
        
        # Convert to the format expected by tokenization logic
        formatted_anns = []
        for ann in anns:
            formatted_anns.append({
                "label": ann["label"],
                "textContext": {
                    "start": ann["start_offset"],
                    "end": ann["end_offset"],
                    "text": ann["text_content"]
                }
            })
            
        all_data.append({
            "pages": [narrative],
            "annotations": formatted_anns
        })
        
    conn.close()
    return all_data

def tokenize_and_align_labels(examples, tokenizer, label_to_id, max_length=512):
    """
    examples: List of JSON-like data (one per case)
    Converts char-level annotations to BIO-tagged token-level labels.
    """
    tokenized_inputs = []
    
    for item in examples:
        text = item["pages"][0]
        annotations = item.get("annotations", [])
        
        if not text: continue
        
        # Tokenize text
        tokenized = tokenizer(
            text, 
            truncation=True, 
            padding="max_length", 
            max_length=max_length, 
            return_offsets_mapping=True
        )
        
        labels = [0] * len(tokenized["input_ids"]) # Default to 'O' tag (which should be at index 0)
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
                    # Logic for B- and I- prefixes
                    # B- if it's the start of the annotation OR if it's the first token in range
                    # We use a simple heuristic: if the previous token was also in range, it's I-
                    # But the offset mapping allows more precise check:
                    is_start = (start_tok == start_char) or (i > 0 and offset_mapping[i-1][0] < start_char and start_tok >= start_char)
                    
                    bio_prefix = "B-" if is_start else "I-"
                    tag = f"{bio_prefix}{label_name}"
                    if tag in label_to_id:
                        labels[i] = label_to_id[tag]
        
        # Mask special tokens in labels (-100 tells PyTorch to ignore them in loss)
        labels = [
            -100 if offset_mapping[i] == (0, 0) else labels[i]
            for i in range(len(labels))
        ]
        
        tokenized["labels"] = labels
        # remove offset_mapping as it's not needed for training and contains tuples (which torch doesn't like)
        del tokenized["offset_mapping"] 
        tokenized_inputs.append(tokenized)
        
    return tokenized_inputs

def prepare_datasets(all_data, tokenizer, split_ratio=0.7):
    """
    Split ratio 0.7 for training, 0.3 for validation.
    """
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
        return {key: torch.tensor(val) for key, val in self.data[idx].items()}
