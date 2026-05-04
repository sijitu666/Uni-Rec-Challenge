#!/bin/bash
# V4: 序列编码器升级
# 改进点: seq_encoder_type从swiglu改为transformer
# 预期效果: 引入序列自注意力机制，捕获序列内部的依赖关系

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
    --seq_encoder_type transformer \
    --use_rope \
    --dropout_rate 0.01 \
    --lr 1e-4 \
    --loss_type bce \
    --ns_groups_json "" \
    --emb_skip_threshold 1000000 \
    --num_workers 8 \
    "$@"
