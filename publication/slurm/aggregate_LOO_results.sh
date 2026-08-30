#!/bin/bash
# ==============================================================================
# Aggregate Finished SLURM Array Results into Final Summary Excel
# ==============================================================================
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate llm4ae || true
fi

python publication/scripts/run_FAERS_bert_LOO.py \
    --mode loo \
    --aggregate-only \
    --results-dir publication/results/bert_runs_FAERS_LOO
