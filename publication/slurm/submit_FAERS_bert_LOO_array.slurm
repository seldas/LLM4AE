#!/bin/bash
# ==============================================================================
# SLURM Job Array Script for FAERS BioBERT LOO (1 GPU per task)
# ==============================================================================
# Benefits:
#   - Solves the queue waiting problem: requests only 1 GPU per sub-job.
#   - SLURM schedules tasks dynamically onto ANY node with at least 1 free GPU.
#   - 20 sub-jobs total (4 LOO Folds x 5 Seeds, task IDs 0 to 19).
# ==============================================================================
#SBATCH --job-name=faers_loo_arr
#SBATCH --output=slurm_logs/faers_loo_arr_%A_%a.log
#SBATCH --error=slurm_logs/faers_loo_arr_%A_%a.err
#SBATCH --array=0-19%8             # 20 tasks total, max 8 concurrent (adjust %N as needed)
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1               # Only 1 GPU requested per sub-job!
#SBATCH --mem=24G                  # 24GB RAM per sub-job
#SBATCH --time=04:00:00            # Max 4 hours per fold/seed
#SBATCH --partition=gpu            # Change to your cluster's GPU partition name

set -eo pipefail

echo "=============================================================================="
echo " Array Job ID    : ${SLURM_ARRAY_JOB_ID}"
echo " Array Task ID   : ${SLURM_ARRAY_TASK_ID} / 19"
echo " Node List       : ${SLURM_JOB_NODELIST}"
echo " CUDA Device     : ${CUDA_VISIBLE_DEVICES:-"0"}"
echo " Start Time      : $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================================================="

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

# Run the single task corresponding to this SLURM Array ID (0..19)
python publication/scripts/run_FAERS_bert_LOO.py \
    --mode loo \
    --task-index ${SLURM_ARRAY_TASK_ID} \
    --gpu-ids 0 \
    --batch-size 64 \
    --max-batch-items 8192 \
    --eval-batch-size 64 \
    --max-steps 8000 \
    --results-dir publication/results/bert_runs_FAERS_LOO

echo "=============================================================================="
echo " Task ${SLURM_ARRAY_TASK_ID} Finished Successfully at $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================================================="
