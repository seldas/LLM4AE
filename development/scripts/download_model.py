import os
import argparse
from transformers import AutoTokenizer, AutoModelForTokenClassification

def download_foundation_model(model_name="dmis-lab/biobert-base-cased-v1.2", save_dir="../models/foundation"):
    print(f"--- Downloading foundation model: {model_name} ---")
    
    os.makedirs(save_dir, exist_ok=True)
    
    # Download tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name, num_labels=2) # Dummy labels for init
    
    tokenizer.save_pretrained(save_dir)
    model.save_pretrained(save_dir)
    
    print(f"--- Model and tokenizer saved to: {os.path.abspath(save_dir)} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download foundation BERT model")
    parser.add_argument("--model", type=str, default="dmis-lab/biobert-base-cased-v1.2", help="HuggingFace model ID")
    args = parser.parse_args()
    
    download_foundation_model(args.model)
