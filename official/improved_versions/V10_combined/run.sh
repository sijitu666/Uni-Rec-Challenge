#!/bin/bash
# V10: 综合改进版本
# 改进点: 组合多个有效的改进策略
# - d_model: 128 (更宽)
# - num_hyformer_blocks: 3 (更深)
# - num_heads: 8 (更多注意力头)
# - seq_encoder_type: transformer (序列自注意力)
# - use_rope: True (位置编码)
# - dropout_rate: 0.2 (正则化)
# - lr: 5e-5 (稳定学习率)
# - loss_type: focal (处理类别不平衡)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

python3 -u "${PARENT_DIR}/train.py" \
    --ns_tokenizer_type rankmixer \
    --user_ns_tokens 5 \
    --item_ns_tokens 2 \
    --num_queries 2 \
    --num_hyformer_blocks 3 \
    --num_heads 8 \
    --d_model 128 \
    --emb_dim 128 \
    --seq_encoder_type transformer \
    --use_rope \
    --dropout_rate 0.2 \
    --lr 5e-5 \
    --loss_type focal \
    --focal_alpha 0.25 \
    --focal_gamma 2.0 \
    --ns_groups_json "" \
    --emb_skip_threshold 1000000 \
    --num_workers 8 \
    "$@"
