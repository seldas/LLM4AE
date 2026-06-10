

**mapping files:**

mapping.ipynb->create file: true\_files.txt, only file in this txt file will be processed in the FAERS\_R1\_etherether\_v1.ipynb





**to create .spacy file for ETHER:**

FAERS\_R1\_etherether\_v1.ipynb





**to create .spacy file for LLM:**

FAERS\_R1\_llmllm\_v1.ipynb



**to create .spacy file for SME:**

FAERS\_R1\_sme1sme1\_v1.ipynb









**to train BERT model:**

1. login into nodes:

qlogin -q hpc.q@ncshpc405.fda.gov





2\. activate conda environment

source ~/miniconda3/bin/activate

conda activate transformer\_ner



(if using ncshpcgpu01, need to do this:

qlogin -q hpc.q@ncshpcgpu01.fda.gov

export HOME=/compute001/Wzhang

source "$HOME/miniconda3/etc/profile.d/conda.sh"

)

3\. change directory

cd /compute001/Wzhang/





4\. split train data into 2 parts

split:

train\_FAVERS\_R1\_v1\_SME1\_new\_revision.spacy

into:

"train\_FAVERS\_R1\_v1\_SME1\_new\_revision\_splited.spacy"

"dev\_FAVERS\_R1\_v1\_SME1\_new\_revision\_splited.spacy"



using this code to split file:

python split\_train\_FAERS\_R1\_SME1\_v3.py



5\. run this code to train BERT and save it in specific directory

nohup python -m spacy train train\_FAVERS\_R1\_SME1SME1\_v4\_data\_v1.cfg --output ./SMESMEoutput\_FAERS\_test\_data\_v1 --gpu-id 0  --code custom\_scorer\_v3.py > train\_FAVERS\_R1\_SME1SME1\_v4\_data\_v1.log \&









**for running Testing\_BERTs.iynb(evaluate the results for different methods):**

1\. login to HPC

qlogin -q hpc.q@ncshpc405.fda.gov

2\. activate conda environment

source ~/miniconda3/bin/activate

cd /compute001/Wzhang/

conda activate transformer\_ner

3\. using python by typing: python

4\. copy and paste code to run









**for creating conda environment using environment.yml:**

conda create -n transformer\_ner1 python=3.10 -y

conda activate transformer\_ner1

pip install --extra-index-url https://download.pytorch.org/whl/cu118 torch==2.7.1+cu118

pip install spacy

pip install pandas





