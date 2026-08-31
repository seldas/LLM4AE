#!/bin/bash
# ==============================================================================
# SLURM Submission Script for BERT Model Ablation Study on VAERS (8 GPUs)
# Models: BioBERT, ClinicalBERT, BERT, Bio_ClinicalBERT (5 Runs Each = 20 Total Runs)
# ==============================================================================
#SBATCH --job-name=vaers_bert_ablation
#SBATCH --output=slurm_logs/vaers_ablation_%j.log
#SBATCH --error=slurm_logs/vaers_ablation_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --gres=gpu:8
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --partition=gpu

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

mkdir -p publication/slurm/slurm_logs

if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate llm4ae || true
fi

export PYTHONUNBUFFERED=1
export NO_COLOR=1

if [ -n "${CUDA_VISIBLE_DEVICES}" ]; then
    IFS=',' read -ra GPU_ARR <<< "${CUDA_VISIBLE_DEVICES}"
    GPU_COUNT=${#GPU_ARR[@]}
    GPU_IDS=()
    for ((i=0; i<GPU_COUNT; i++)); do
        GPU_IDS+=("$i")
    done
    GPU_ARGS="${GPU_IDS[*]}"
else
    GPU_ARGS="0 1 2 3 4 5 6 7"
fi

echo "========================================================================"
echo "Running VAERS BERT Ablation (BioBERT, ClinicalBERT, BERT, Bio_ClinicalBERT)"
echo "Active GPUs: ${GPU_ARGS}"
echo "========================================================================"

python publication/scripts/run_VAERS_bert_ablation.py \
    --models BioBERT ClinicalBERT BERT Bio_ClinicalBERT \
    --seeds 42 123 456 789 1011 \
    --gpu-ids ${GPU_ARGS} \
    --split 0.8 0.1 0.1 \
    --max-steps 8000 \
    --results-dir results/bert_replim_VAERS

