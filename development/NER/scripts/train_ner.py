import os
import subprocess
import sys
from pathlib import Path

# --- Configuration ---
SCRIPTS_DIR = Path(__file__).resolve().parent
NER_DIR = SCRIPTS_DIR.parent
DATA_DIR = NER_DIR / "data"
OUTPUT_DIR = NER_DIR / "output"
CONFIG_PATH = SCRIPTS_DIR / "config.cfg"
CUSTOM_SCORER_PATH = SCRIPTS_DIR / "custom_scorer.py"

def create_default_config():
    """
    Creates a default spaCy config file using BioBERT.
    """
    # Note: In a real scenario, you might want to use 'spacy init config' 
    # but here we provide a pre-filled one for BioBERT NER.
    config_content = f"""
[paths]
train = "{DATA_DIR / 'train.spacy'}"
dev = "{DATA_DIR / 'dev.spacy'}"
vectors = null
init_tok2vec = null

[system]
gpu_allocator = "pytorch"
seed = 0

[nlp]
lang = "en"
pipeline = ["transformer","ner"]
batch_size = 32

[components]

[components.ner]
factory = "ner"
scorer = {{"@scorers":"ade_weighted_ner_scorer.v1"}}

[components.ner.model]
@architectures = "spacy.TransitionBasedParser.v2"
state_type = "ner"
hidden_width = 64
maxout_pieces = 2
use_upper = false

[components.ner.model.tok2vec]
@architectures = "spacy-transformers.TransformerListener.v1"
grad_factor = 1.0
pooling = {{"@layers":"reduce_mean.v1"}}
upstream = "*"

[components.transformer]
factory = "transformer"
max_batch_items = 4096

[components.transformer.model]
@architectures = "spacy-transformers.TransformerModel.v3"
name = "dmis-lab/biobert-base-cased-v1.1"

[corpora]

[corpora.dev]
@readers = "spacy.Corpus.v1"
path = ${{paths.dev}}

[corpora.train]
@readers = "spacy.Corpus.v1"
path = ${{paths.train}}

[training]
accumulate_gradient = 3
dev_corpus = "corpora.dev"
train_corpus = "corpora.train"
seed = 123
gpu_allocator = "pytorch"
dropout = 0.1
patience = 1600
max_epochs = 0
max_steps = 20000
eval_frequency = 200

[training.batcher]
@batchers = "spacy.batch_by_padded.v1"
size = 2000
buffer = 256

[training.optimizer]
@optimizers = "Adam.v1"

[training.optimizer.learn_rate]
@schedules = "warmup_linear.v1"
warmup_steps = 250
total_steps = 20000
initial_rate = 0.0001

[training.score_weights]
ents_f = 1.0

[initialize]
    """.strip()
    
    with open(CONFIG_PATH, "w") as f:
        f.write(config_content)
    print(f"Created default config at {CONFIG_PATH}")

def train():
    if not CONFIG_PATH.exists():
        create_default_config()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # We need to include the custom_scorer.py so spaCy can find the registered scorer
    # One way is to set PYTHONPATH or use the --code flag in spacy train
    cmd = [
        sys.executable, "-m", "spacy", "train",
        str(CONFIG_PATH),
        "--output", str(OUTPUT_DIR),
        "--code", str(CUSTOM_SCORER_PATH),
        "--gpu-id", "0"  # Set to -1 for CPU
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Training failed with error: {e}")
    except FileNotFoundError:
        print("spaCy command not found. Make sure it is installed.")

if __name__ == "__main__":
    train()
