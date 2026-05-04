#!/bin/bash
# V2: 扩大模型宽度
# 改进点: d_model从64增加到128, emb_dim从64增加到128
# 预期效果: 增加模型参数容量，提升特征表示能力

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
    --d_model 128 \
    --emb_dim 128 \
    --seq_encoder_type swiglu \
    --dropout_rate 0.01 \
    --lr 1e-4 \
    --loss_type bce \
    --ns_groups_json "" \
    --emb_skip_threshold 1000000 \
    --num_workers 8 \
    "$@"
