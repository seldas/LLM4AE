import spacy
from spacy.tokens import DocBin
from spacy.training import Example
from pathlib import Path
import json
import sys, os

# Import custom scorer logic
# We can either import it if it's in the same directory, or just provide the logic here.
# Since we want it simplified, I'll use the logic from custom_scorer.py.
from custom_scorer import spancat_char_score

# --- Configuration ---
SCRIPTS_DIR = Path(__file__).resolve().parent
NER_DIR = SCRIPTS_DIR.parent
MODEL_PATH = NER_DIR / "output" / "model-best"
TEST_DATA_PATH = NER_DIR / "data" / "dev.spacy"

def evaluate():
    if not MODEL_PATH.exists():
        print(f"Model not found at {MODEL_PATH}. Please train the model first.")
        return

    if not TEST_DATA_PATH.exists():
        print(f"Test data not found at {TEST_DATA_PATH}. Please prepare data first.")
        return

    print(f"Loading model from {MODEL_PATH}...")
    nlp = spacy.load(MODEL_PATH)
    
    print(f"Loading test data from {TEST_DATA_PATH}...")
    doc_bin = DocBin().from_disk(TEST_DATA_PATH)
    docs = list(doc_bin.get_docs(nlp.vocab))
    
    examples = []
    for gold_doc in docs:
        pred_doc = nlp(gold_doc.text)
        examples.append(Example(pred_doc, gold_doc))
    
    print(f"Evaluating on {len(examples)} examples...")
    results = spancat_char_score(examples)
    
    # Print results
    print("\nOverall Results:")
    print(f"Precision: {results['ents_p']:.4f}")
    print(f"Recall:    {results['ents_r']:.4f}")
    print(f"F1 Score:  {results['ents_f']:.4f}")
    
    print("\nResults per label:")
    for label, metrics in results['ents_per_type'].items():
        print(f"  {label:10}: P={metrics['p']:.4f}, R={metrics['r']:.4f}, F={metrics['f']:.4f}")

    # Save results to file
    output_file = os.path.join(NER_DIR, "output/evaluation_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to {output_file}")

if __name__ == "__main__":
    evaluate()
