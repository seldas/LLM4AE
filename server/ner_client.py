import spacy
from spacy.util import filter_spans
from pathlib import Path
import os
import custom_scorer  

class NERClient:
    def __init__(self, model_path=None):
        if model_path is None:
            # Default path relative to this file (server/ner_client.py)
            model_path = "/app/BERT_MODEL/model-best"
        
        self.model_path = model_path
        self.nlp = None

    def _load_model(self):
        if self.nlp is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"NER model not found at {self.model_path}")
            print(f"Loading NER model from {self.model_path}...")
            self.nlp = spacy.load(self.model_path)
            # Add sentencizer if not present (though it should be in the saved model)
            if "sentencizer" not in self.nlp.pipe_names and "transformer" not in self.nlp.pipe_names:
                 self.nlp.add_pipe("sentencizer")

    def annotate_text(self, text):
        """
        Annotates text using the BERT model.
        Handles long text by splitting into 512-char chunks and merging results.
        """
        self._load_model()
        
        # Simple splitting logic similar to prepare_data.py but for inference
        # We'll use spaCy's sentence splitter first
        doc_full = spacy.blank("en")
        doc_full.add_pipe("sentencizer")
        doc = doc_full(text)
        
        all_entities = []
        current_offset = 0
        
        for sent in doc.sents:
            sent_text = sent.text
            # If a sentence is still too long (>512), we split it roughly
            chunks = []
            while len(sent_text) > 512:
                split_idx = sent_text.rfind(' ', 0, 512)
                if split_idx == -1: split_idx = 512
                chunks.append(sent_text[:split_idx])
                sent_text = sent_text[split_idx:].strip()
            chunks.append(sent_text)
            
            sent_start_in_full = sent.start_char
            chunk_offset = 0
            for chunk in chunks:
                if not chunk.strip(): continue
                
                # Find the actual start of this chunk in the original text to handle strip()
                actual_chunk_start = text.find(chunk, sent_start_in_full + chunk_offset)
                
                pred_doc = self.nlp(chunk)
                for ent in pred_doc.ents:
                    all_entities.append({
                        "start": actual_chunk_start + ent.start_char,
                        "end": actual_chunk_start + ent.end_char,
                        "label": ent.label_,
                        "text": ent.text
                    })
                chunk_offset = (actual_chunk_start - sent_start_in_full) + len(chunk)

        # Resolve any overlaps that might occur at chunk boundaries
        # Sort and filter
        all_entities.sort(key=lambda x: x["start"])
        
        # Convert back to spacy spans for filter_spans
        final_doc = spacy.blank("en")(text)
        spans = []
        for ent in all_entities:
            span = final_doc.char_span(ent["start"], ent["end"], label=ent["label"], alignment_mode="contract")
            if span:
                spans.append(span)
        
        filtered_spans = filter_spans(spans)
        
        return [
            {
                "start": s.start_char,
                "end": s.end_char,
                "label": s.label_,
                "text": s.text
            } for s in filtered_spans
        ]

# Singleton instance
_client = None

def get_ner_client():
    global _client
    if _client is None:
        _client = NERClient()
    return _client

if __name__ == "__main__":
    # Test
    client = get_ner_client()
    try:
        results = client.annotate_text("The patient experienced a severe headache after taking Aspirin.")
        print(results)
    except Exception as e:
        print(e)
