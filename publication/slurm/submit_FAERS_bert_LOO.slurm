#!/bin/bash
# ==============================================================================
# SLURM Submission Script for BioBERT Leave-One-Drug-AE-Pair-Out (LOO) & CV
# ==============================================================================
#SBATCH --job-name=faers_bert_loo
#SBATCH --output=slurm_logs/faers_loo_%j.log
#SBATCH --error=slurm_logs/faers_loo_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --gres=gpu:7               # Request 7 GPUs (or change to gpu:8 or gpu:4)
#SBATCH --mem=128G                 # Request 128GB RAM
#SBATCH --time=24:00:00            # Max runtime: 24 hours
#SBATCH --partition=gpu            # Partition name (adjust to your cluster partition, e.g. gpu, compute, etc.)

set -eo pipefail

echo "=============================================================================="
echo " Job ID          : ${SLURM_JOB_ID}"
echo " Job Name        : ${SLURM_JOB_NAME}"
echo " Node List       : ${SLURM_JOB_NODELIST}"
echo " Allocated GPUs  : ${CUDA_VISIBLE_DEVICES:-"Auto (SLURM allocated)"}"
echo " Submit Dir      : ${SLURM_SUBMIT_DIR}"
echo " Start Time      : $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================================================="

# 1. Navigate to Project Root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

mkdir -p publication/slurm/slurm_logs

# 2. Activate Conda / Python Environment (adjust environment name/path if needed)
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate llm4ae || true
fi

export PYTHONUNBUFFERED=1
export NO_COLOR=1

# 3. Detect Allocated GPUs from SLURM
if [ -n "${CUDA_VISIBLE_DEVICES}" ]; then
    # SLURM re-indexes GPUs inside container/allocation (e.g. 0,1,2,3,4,5,6)
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

echo "Running on GPU indexes: ${GPU_ARGS}"

# 4. Execute BioBERT Leave-One-Pair-Out (LOO) with 5 Random Seeds Across All GPUs
python publication/scripts/run_FAERS_bert_LOO.py \
    --mode loo \
    --gpu-ids ${GPU_ARGS} \
    --workers-per-gpu 2 \
    --seeds 42 123 456 789 1011 \
    --batch-size 64 \
    --max-batch-items 8192 \
    --eval-batch-size 64 \
    --max-steps 8000 \
    --results-dir publication/results/bert_runs_FAERS_LOO

echo "=============================================================================="
echo " Job Completed Successfully at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================================================="
