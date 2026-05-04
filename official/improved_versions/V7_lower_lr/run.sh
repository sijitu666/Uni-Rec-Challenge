#!/bin/bash
# V7: 学习率优化
# 改进点: 学习率从1e-4降低到5e-5
# 预期效果: 更稳定的收敛，避免震荡

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

python3 -u "${PARENT_DIR}/train.py" \
    --ns_tokenizer_type rankmixer \
    --user_ns_tokens 5 \
    --item_ns_tokens 2 \
    --num_queries 2 \
    --num_hyformer_blocks 2 \
    --num_heads 4 \
    --d_model 64 \
    --emb_dim 64 \
    --seq_encoder_type swiglu \
    --dropout_rate 0.01 \
    --lr 5e-5 \
    --loss_type bce \
    --ns_groups_json "" \
    --emb_skip_threshold 1000000 \
    --num_workers 8 \
    "$@"
