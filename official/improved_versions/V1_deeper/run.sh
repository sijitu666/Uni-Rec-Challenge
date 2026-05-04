#!/bin/bash
# V1: 增加模型深度
# 改进点: num_hyformer_blocks从2增加到3
# 预期效果: 增强模型表达能力，提升特征交互的层次性

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

python3 -u "${PARENT_DIR}/train.py" \
    --ns_tokenizer_type rankmixer \
    --user_ns_tokens 5 \
    --item_ns_tokens 2 \
    --num_queries 2 \
    --num_hyformer_blocks 3 \
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
