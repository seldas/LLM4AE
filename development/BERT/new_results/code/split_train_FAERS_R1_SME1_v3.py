# -*- coding: utf-8 -*-
import spacy
from spacy.tokens import DocBin
from sklearn.model_selection import train_test_split

# åŠ è½½åŽŸå§‹ .spacy æ–‡ä»¶
input_path = "train_FAVERS_R1_v1_SME1_new_revision.spacy"
doc_bin = DocBin().from_disk(input_path)
nlp = spacy.blank("en") 
docs = list(doc_bin.get_docs(nlp.vocab))

# å°†æ•°æ®æ‹†åˆ†ä¸ºè®­ç»ƒé›†å’Œæµ‹è¯•é›†
train_docs, test_docs = train_test_split(docs, test_size=0.2, random_state=42)

# å°†è®­ç»ƒé›†ä¿å­˜åˆ°æ–°çš„ .spacy æ–‡ä»¶ä¸­
train_doc_bin = DocBin(docs=train_docs)
train_output_path = "train_FAVERS_R1_v1_SME1_new_revision_splited.spacy"
train_doc_bin.to_disk(train_output_path)

# å°†æµ‹è¯•é›†ä¿å­˜åˆ°æ–°çš„ .spacy æ–‡ä»¶ä¸­
test_doc_bin = DocBin(docs=test_docs)
test_output_path = "dev_FAVERS_R1_v1_SME1_new_revision_splited.spacy"
test_doc_bin.to_disk(test_output_path)

print("Training data saved to {}".format(train_output_path))
print("Test data saved to {}".format(test_output_path))


