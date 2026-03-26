import sqlite3
import os
import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans
from sklearn.model_selection import train_test_split
import warnings
from pathlib import Path
from collections import defaultdict

# --- Configuration ---
ROOT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = ROOT_DIR / 'server' / 'database' / 'llm4ae.db'
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_USER = "SME1" # or username like 'MJ.L'

def get_annotations_from_db(user_id_or_key):
    """
    Fetches narratives and annotations from the database for a specific user/migration_key.
    Returns a list of (text, {"entities": [(start, end, label), ...]})
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find user_id if migration_key is provided
    cursor.execute("SELECT id FROM users WHERE username = ? OR migration_key = ?", (user_id_or_key, user_id_or_key))
    user_row = cursor.fetchone()
    if not user_row:
        print(f"User {user_id_or_key} not found in database.")
        return []
    user_id = user_row['id']

    # Query narratives and their annotations
    # We only take cases that HAVE annotations from this user
    cursor.execute("""
        SELECT c.id, c.narrative, a.label, a.start_offset, a.end_offset
        FROM cases c
        JOIN annotations a ON c.id = a.case_id
        WHERE a.user_id = ?
    """, (user_id,))
    
    rows = cursor.fetchall()
    
    # Group by case_id
    case_data = defaultdict(lambda: {"text": "", "entities": []})
    for row in rows:
        cid = row['id']
        case_data[cid]["text"] = row['narrative']
        case_data[cid]["entities"].append((row['start_offset'], row['end_offset'], row['label']))
    
    # Convert to the format expected by the conversion script
    formatted_data = []
    for cid in case_data:
        # Deduplicate entities for the same case (if any)
        entities = list(set(case_data[cid]["entities"]))
        formatted_data.append((case_data[cid]["text"], {"entities": entities}))
    
    conn.close()
    return formatted_data

def validate_entities(entities):
    entities = sorted(entities, key=lambda x: x[0])
    for i in range(len(entities) - 1):
        if entities[i][1] > entities[i + 1][0]:
            return False
    return True

def clean_entities(entities, text):
    cleaned_entities = []
    for start, end, label in entities:
        start = max(0, min(start, len(text)))
        end = max(0, min(end, len(text)))
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            cleaned_entities.append((start, end, label))
    return cleaned_entities

def split_sentences(nlp, text, entities):
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    res_sentences = []
    res_entities = []

    for sentence in sentences:
        while len(sentence) > 512:
            split_index = sentence.rfind(' ', 0, 512)
            if split_index == -1:
                split_index = 512
            
            part1 = sentence[:split_index].strip()
            part2 = sentence[split_index:].strip()
            
            res_sentences.append(part1)
            
            p1_len = len(part1)
            p1_ents = []
            p2_ents = []
            for start, end, label in entities:
                if start < p1_len:
                    if end <= p1_len:
                        p1_ents.append((start, end, label))
                    else:
                        p1_ents.append((start, p1_len, label))
                        p2_ents.append((0, end - p1_len, label))
                else:
                    p2_ents.append((start - p1_len, end - p1_len, label))
            
            res_entities.append(p1_ents)
            sentence = part2
            entities = p2_ents
            
        res_sentences.append(sentence)
        res_entities.append(entities)
        
    return res_sentences, res_entities

def truncate_text_and_entities(text, entities, max_length=512):
    if len(text) <= max_length:
        return text, entities
    truncated_text = text[:max_length]
    truncated_entities = []
    for start, end, label in entities:
        if start < max_length:
            truncated_entities.append((start, min(end, max_length), label))
    return truncated_text, truncated_entities

def convert_to_docbin(lang, raw_data, output_path):
    nlp = spacy.blank(lang)
    nlp.add_pipe("sentencizer")
    db = DocBin()
    
    for text, annot in raw_data:
        sentences, entities_list = split_sentences(nlp, text, annot["entities"])
        for sentence, entities in zip(sentences, entities_list):
            sentence, entities = truncate_text_and_entities(sentence, entities, max_length=512)
            doc = nlp.make_doc(sentence)
            
            if not validate_entities(entities):
                print(f"Skipping text with overlapping entities: {repr(sentence[:100])}...")
                continue
            
            entities = clean_entities(entities, sentence)
            ents = []
            for start, end, label in entities:
                span = doc.char_span(start, end, label=label, alignment_mode="strict")
                if span is not None:
                    ents.append(span)
                else:
                    print(f"Skipping unaligned entity: {sentence[start:end]} at {start}:{end}")
            
            doc.ents = filter_spans(ents)
            db.add(doc)
    
    db.to_disk(output_path)
    print(f"Saved to {output_path}")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Fetching data for {DEFAULT_USER} from {DB_PATH}...")
    data = get_annotations_from_db(DEFAULT_USER)
    print(f"Found {len(data)} cases with annotations.")
    
    if not data:
        return

    train_data, dev_data = train_test_split(data, test_size=0.2, random_state=42)
    
    convert_to_docbin("en", train_data, OUTPUT_DIR / "train.spacy")
    convert_to_docbin("en", dev_data, OUTPUT_DIR / "dev.spacy")
    
    print("Data preparation complete.")

if __name__ == "__main__":
    main()
