#!/bin/bash
# V8: Focal Loss
# 改进点: 损失函数从BCE改为Focal Loss, alpha=0.25
# 预期效果: 处理类别不平衡问题，关注困难样本

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
    --lr 1e-4 \
    --loss_type focal \
    --focal_alpha 0.25 \
    --focal_gamma 2.0 \
    --ns_groups_json "" \
    --emb_skip_threshold 1000000 \
    --num_workers 8 \
    "$@"
