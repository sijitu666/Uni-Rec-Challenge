#!/bin/bash
# V5: 时间特征增强
# 改进点: 增加时间桶数量从65到129 (使用dataset_v5.py)
# 预期效果: 更精细的时间间隔建模

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
export PYTHONPATH="${SCRIPT_DIR}:${PARENT_DIR}:${PYTHONPATH}"

python3 -u "${SCRIPT_DIR}/train_v5.py" \
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
    --loss_type bce \
    --ns_groups_json "" \
    --emb_skip_threshold 1000000 \
    --num_workers 8 \
    "$@"
