#!/bin/bash
# ==============================================================================
# SLURM Submission Script for BioBERT Stratified 10-Fold CV on FAERS
# ==============================================================================
#SBATCH --job-name=faers_bert_cv
#SBATCH --output=slurm_logs/faers_cv_%j.log
#SBATCH --error=slurm_logs/faers_cv_%j.err
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

echo "Running 10-Fold CV x 5 Seeds on GPUs: ${GPU_ARGS}"

python publication/scripts/run_FAERS_bert_LOO.py \
    --mode cv \
    --folds 10 \
    --gpu-ids ${GPU_ARGS} \
    --workers-per-gpu 2 \
    --seeds 42 123 456 789 1011 \
    --batch-size 64 \
    --max-batch-items 8192 \
    --eval-batch-size 64 \
    --max-steps 8000 \
    --results-dir publication/results/bert_runs_FAERS_10fold_5seeds
