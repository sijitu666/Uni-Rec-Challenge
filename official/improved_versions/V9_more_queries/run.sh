#!/bin/bash
# V9: 查询数量增加
# 改进点: num_queries从2增加到4
# 预期效果: 增强查询多样性，捕获更多不同的序列信息

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

python3 -u "${PARENT_DIR}/train.py" \
    --ns_tokenizer_type rankmixer \
    --user_ns_tokens 5 \
    --item_ns_tokens 2 \
    --num_queries 4 \
    --num_hyformer_blocks 2 \
    --num_heads 4 \
    --d_model 64 \
    --emb_dim 64 \
    --seq_encoder_type swiglu \
    --dropout_rate 0.01 \
    --lr 1e-4 \
    --loss_type bce \
    --ns_groups_json "" \
    --emb_skip_threshold 1000000 \
    --num_workers 8 \
    "$@"
