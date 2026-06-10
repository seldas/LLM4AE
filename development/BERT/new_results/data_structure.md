code directory:
1. train_FAVERS_R1_SME1SME1_v4_data_v1.cfg -> file used to train spacy model for FAERS dataset
2. split_train_FAERS_R1_SME1_v3.py -> split training data into train and dev for training spacy model(FAERS)
3. plot_results.ipynb-> compare EHTER and LLM using all data, plot results
4. FAERS_R1_sme1sme1_v1.ipynb -> get SME1 spacy file located at data/processed_data folder
5. FAERS_R1_llmllm_v1.ipynb -> get LLM spacy file located at data/processed_data folder
6. FAERS_R1_etherether_v1.ipynb -> get ETHER spacy file located at data/processed_data folder
7. custom_scorer_v5.py -> modified method to calculate F1, recall and precision
8. custom_scorer_v3.py -> modified method to calculate F1, recall and precision
9. Testing_BERTs.ipynb -> mapping and compare accuracy between LLM, BERT and ETHER, results saved into output folder
10. mapping.ipynb -> check which json file has correct Narrative and save it into true_files.txt, which located at data/processed_data folder
11. train_VAERS_SME1SME1_v2.cfg -> file used to train spacy model for VAERS dataset
12. split_train_VAERS_R1_SME1SME1_v1.py -> split training data into train and dev for training spacy model(VAERS)
13. VAERS_SME1SME1_revision.ipynb -> get SME1 spacy file located at data/processed_data folder
14. VAERS_LLMLLM_revision.ipynb -> get LLM spacy file located at data/processed_data folder
15. VAERS_testing_LLM.ipynb -> calculate accuracy for LLM, results saved into output folder



data directory:
1. VAERS_LLM: VAERS dataset 
2. processed_data: data generated during data analysis
3. Latest Annotation 07182025: FAERS dataset
4. mapping: data used to map narrative and original json file(FAERS dataset)

output directory:
Final results for FAERS and VAERS dataset

model directory:
Model trained by spacy using FAERS and VAERS data


NER_model_readme.md:
how to use code provided

