# PCVRHyFormer 改进版本汇总

本文档详细记录了基于官方baseline的10个改进版本，每个版本针对不同的优化方向。

## 基线配置 (Baseline)

官方baseline的关键配置：
- `d_model`: 64
- `emb_dim`: 64
- `num_queries`: 2
- `num_hyformer_blocks`: 2
- `num_heads`: 4
- `seq_encoder_type`: swiglu
- `dropout_rate`: 0.01
- `lr`: 1e-4
- `loss_type`: bce
- `num_time_buckets`: 65

## 改进版本详情

### V1: 增加模型深度 (Deeper Model)

**改进点:**
- `num_hyformer_blocks`: 2 → 3

**原理:**
增加HyFormer Block的堆叠层数，使模型能够学习更深层次的特征交互。每一层MultiSeqHyFormerBlock包含序列编码、查询解码和查询增强，增加层数可以让这些操作进行多次迭代，提升表达能力。

**预期效果:**
- 正向: 增强模型表达能力，可能改善AUC
- 风险: 训练时间增加，需注意过拟合

**运行命令:**
```bash
cd V1_deeper && bash run.sh
```

---

### V2: 扩大模型宽度 (Wider Model)

**改进点:**
- `d_model`: 64 → 128
- `emb_dim`: 64 → 128

**原理:**
增加模型的隐藏维度，使每个token的表示更加丰富。更宽的模型可以容纳更多信息，提升特征交互的复杂度。

**预期效果:**
- 正向: 显著提升模型容量
- 风险: 参数数量大幅增加，需要更多数据防止过拟合

**注意:** d_model必须能被num_heads整除，128/4=32，符合要求。

**运行命令:**
```bash
cd V2_wider && bash run.sh
```

---

### V3: 多头注意力增强 (More Attention Heads)

**改进点:**
- `num_heads`: 4 → 8

**原理:**
增加注意力头的数量，使模型能够同时关注不同类型的特征交互。每个头可以学习不同的注意力模式，增强模型的表达能力。

**预期效果:**
- 正向: 提升注意力多样性
- 风险: 计算量略有增加

**注意:** d_model必须能被num_heads整除，64/8=8，符合要求。

**运行命令:**
```bash
cd V3_more_heads && bash run.sh
```

---

### V4: 序列编码器升级 (Transformer Encoder)

**改进点:**
- `seq_encoder_type`: swiglu → transformer
- `use_rope`: False → True (启用RoPE位置编码)

**原理:**
将序列编码器从SwiGLU(无注意力)升级为Transformer Encoder(带自注意力)。Transformer编码器可以捕获序列内部的长距离依赖关系，配合RoPE位置编码，可以更好地建模序列的顺序信息。

**预期效果:**
- 正向: 提升序列建模能力，可能显著改善AUC
- 风险: 计算量增加，训练时间变长

**运行命令:**
```bash
cd V4_transformer_encoder && bash run.sh
```

---

### V5: 时间特征增强 (More Time Buckets)

**改进点:**
- `num_time_buckets`: 65 → 129
- 修改了`dataset.py`中的`BUCKET_BOUNDARIES`数组，在原边界之间插入中间值

**原理:**
原始时间桶边界只有64个，对于长时间间隔的区分不够精细。增加桶边界数量，可以更细致地建模用户行为的时间衰减效应。

**预期效果:**
- 正向: 更好的时间衰减建模
- 风险: 时间嵌入参数增加

**注意:** 此版本使用修改版的`dataset_v5.py`和`train_v5.py`。

**运行命令:**
```bash
cd V5_more_time_buckets && bash run.sh
```

---

### V6: 正则化增强 (Strong Regularization)

**改进点:**
- `dropout_rate`: 0.01 → 0.3

**原理:**
原始模型的dropout率很低(0.01)，可能导致过拟合。增加dropout率可以强制模型学习更鲁棒的特征表示，减少对某些特定特征的依赖。

**预期效果:**
- 正向: 减少过拟合，提升验证集AUC
- 风险: dropout过高可能导致欠拟合

**注意:** 序列ID特征的dropout会自动设置为`dropout_rate*2=0.6`。

**运行命令:**
```bash
cd V6_strong_regularization && bash run.sh
```

---

### V7: 学习率优化 (Lower Learning Rate)

**改进点:**
- `lr`: 1e-4 → 5e-5

**原理:**
原始学习率1e-4可能过大，导致训练不稳定或收敛到次优解。降低学习率可以让模型以更小的步长探索参数空间，通常能获得更好的收敛结果。

**预期效果:**
- 正向: 更稳定的收敛
- 风险: 训练速度变慢，可能需要更多epoch

**运行命令:**
```bash
cd V7_lower_lr && bash run.sh
```

---

### V8: Focal Loss

**改进点:**
- `loss_type`: bce → focal
- `focal_alpha`: 0.25 (正值类别权重)
- `focal_gamma`: 2.0 (聚焦参数)

**原理:**
数据集中负样本占比约85%，存在严重的类别不平衡。Focal Loss通过降低简单样本的权重，让模型更关注困难样本。alpha参数平衡正负样本，gamma参数控制聚焦程度。

**预期效果:**
- 正向: 处理类别不平衡，可能改善AUC
- 风险: 如果alpha设置不当，可能损害性能

**运行命令:**
```bash
cd V8_focal_loss && bash run.sh
```

---

### V9: 查询数量增加 (More Queries)

**改进点:**
- `num_queries`: 2 → 4

**原理:**
每个序列域生成的查询令牌数量从2增加到4。更多的查询令牌可以让模型从不同的角度关注序列信息，捕获更丰富的序列特征交互模式。

**预期效果:**
- 正向: 增强查询多样性
- 风险: 输出维度增加(4*num_sequences*d_model)，参数增加

**运行命令:**
```bash
cd V9_more_queries && bash run.sh
```

---

### V10: 综合改进版本 (Combined Improvements)

**改进点组合:**
1. `d_model`: 64 → 128 (更宽的模型)
2. `num_hyformer_blocks`: 2 → 3 (更深的模型)
3. `num_heads`: 4 → 8 (更多注意力头)
4. `seq_encoder_type`: swiglu → transformer (序列自注意力)
5. `use_rope`: False → True (启用RoPE位置编码)
6. `dropout_rate`: 0.01 → 0.2 (增强正则化)
7. `lr`: 1e-4 → 5e-5 (更稳定的学习率)
8. `loss_type`: bce → focal (处理类别不平衡)

**原理:**
综合多个经过验证的改进策略，从模型容量、正则化、优化方法和损失函数多个角度提升模型性能。

**预期效果:**
- 正向: 全面提升模型性能，预期AUC显著提升
- 风险: 参数数量大幅增加，需要足够的训练数据和epoch

**运行命令:**
```bash
cd V10_combined && bash run.sh
```

---

## 使用建议

1. **单独测试**: 建议先单独运行每个版本，观察其对性能的影响
2. **组合策略**: V10是综合版本，可以作为最终提交的有力候选
3. **早停机制**: 所有版本都支持early stopping，建议耐心等待模型收敛
4. **资源考虑**: V2、V10等大模型版本需要更多GPU内存和训练时间

## 文件结构

```
official/improved_versions/
├── README.md           # 简要说明
├── summary.md          # 本文档，详细说明
├── V1_deeper/
│   ├── run.sh         # 运行脚本
│   └── config.txt     # 配置说明
├── V2_wider/
│   ├── run.sh
│   └── config.txt
...
└── V10_combined/
    ├── run.sh
    └── config.txt
```

## 提交到平台

每个版本的`run.sh`脚本可以直接在竞赛平台上运行。需要：
1. 将对应版本的`run.sh`内容复制到平台的训练脚本中
2. 确保数据路径`--data_dir`指向正确的训练数据目录
3. 根据需要调整`--ckpt_dir`、`--log_dir`等路径参数
