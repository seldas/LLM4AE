#!/bin/bash
# ==============================================================================
# SLURM Submission Script for BioBERT 10-Fold CV on VAERS
# ==============================================================================
#SBATCH --job-name=vaers_bert_cv
#SBATCH --output=slurm_logs/vaers_cv_%j.log
#SBATCH --error=slurm_logs/vaers_cv_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --gres=gpu:7
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
    GPU_ARGS="0 1 2 3 4 5 6"
fi

echo "Running VAERS BioBERT 10-Fold on GPUs: ${GPU_ARGS}"

python publication/scripts/run_VAERS_bert.py \
    --folds 10 \
    --gpu-ids ${GPU_ARGS} \
    --split 0.8 0.1 0.1 \
    --max-steps 8000 \
    --results-dir publication/results/bert_runs_VAERS
