# PCVRHyFormer Baseline 改进方案记录

## 概述

本文档记录了基于官方 PCVRHyFormer baseline 模型的 12 个渐进式改进版本。PCVRHyFormer 是一个用于 CTR（点击率）预测的混合 Transformer 模型，采用多序列 Query Decoding + RankMixer Query Boosting 架构。

### 数据集结构
- **训练数据**: Parquet 格式，包含 `user_int_feats`、`item_int_feats`、`user_dense_feats`、序列特征 (`seq_a/b/c/d`) 及对应的 timestamp bucket
- **标签**: `label_type == 2` 为正样本（点击后转化），其他为负样本
- **评估指标**: Binary AUC（主要）、LogLoss
- **数据划分**: 按 Row Group 拆分，默认最后 10% 作为验证集

### Baseline 架构要点
- **NS Tokenizer**: 将用户/物品的非序列特征投影为固定数量的 NS token
- **Seq Tokenizer**: 序列特征先按 domain 做 embedding + projection
- **MultiSeqQueryGenerator**: 利用 NS token 和 MeanPool(seq) 生成 per-sequence 的 Query token
- **MultiSeqHyFormerBlock**: Sequence Evolution → Query Decoding (Cross-Attn) → Query Boosting (RankMixer)
- **Classifier**: 简单的 2 层 MLP 输出单 logit

---

## 版本索引

| 版本 | 目录名 | 改进方向 | 修改文件 |
|------|--------|---------|---------|
| V1 | `V1_Baseline` | 基线版本（直接拷贝） | 无修改 |
| V2 | `V2_DNN_Classifier` | 分类头增强 | `model.py` |
| V3 | `V3_Asymmetric_FocalLoss` | 非对称 Focal Loss | `model.py`, `trainer.py`, `train.py`, `utils.py` |
| V4 | `V4_MultiHead_Pooling` | 多头注意力输出池化 | `model.py` |
| V5 | `V5_SwiGLU_FFN` | 全局 SwiGLU 替换 GELU | `model.py` |
| V6 | `V6_Deeper_HyFormer` | 加深网络层数 | `model.py` |
| V7 | `V7_Wider_Embeddings` | 加宽 Embedding 维度 | `model.py` |
| V8 | `V8_Auxiliary_MultiTask` | 辅助多任务学习 | `model.py`, `trainer.py` |
| V9 | `V9_SENet_Recalibration` | SE 特征重标定 | `model.py` |
| V10 | `V10_GRN_QueryBoosting` | GRN 门控残差网络 | `model.py` |
| V11 | `V11_StochasticDepth` | 随机深度正则化 | `model.py` |
| V12 | `V12_LabelSmoothing` | 标签平滑 | `model.py`, `trainer.py`, `utils.py` |

---

## 版本详情

### V1: Baseline（基线版本）

**说明**: 直接拷贝官方 `official/` 目录下的所有文件，作为后续改进的基准参考。

**运行命令**:
```bash
cd official/improved_versions/V1_Baseline
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log \
    --d_model 64 --emb_dim 64 --num_hyformer_blocks 2 --num_heads 4
```

**预期效果**: 基准 AUC，供后续版本对比。

---

### V2: DNN_Classifier（深层分类器）

**改进点**: 将简单的 2 层 MLP 分类器替换为 3 层深层残差 MLP。

**具体改动** (`model.py`):
- 原分类器: `d_model -> d_model -> action_num` (2 层)
- 新分类器: `d_model -> 2*d_model -> 2*d_model -> 2*d_model -> action_num` (4 层，带 LayerNorm + SiLU + Dropout)

**改进原理**: 更深的分类头可以学习更复杂的决策边界，每层都有 LayerNorm 稳定训练。虽然参数量增加，但对于 CTR 预测任务，适度的深度可以提升模型表达力。

**运行命令**:
```bash
cd official/improved_versions/V2_DNN_Classifier
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log
```

---

### V3: Asymmetric_FocalLoss（非对称 Focal Loss）

**改进点**: 引入非对称 Focal Loss，对正负样本使用不同的 focusing 参数。

**具体改动**:
- `utils.py`: 新增 `asymmetric_focal_loss()` 函数
- `trainer.py`: 支持 `--loss_type asymmetric`，导入并使用非对称 focal loss
- `train.py`: 新增 `asymmetric` loss type 选项

**改进原理**: 
- CTR 任务通常负样本远多于正样本（~85% vs ~15%）
- 非对称 Focal Loss 对负样本使用更高的 gamma（neg_gamma=4.0 vs pos_gamma=2.0），更激进地降低简单负样本的权重
- 同时使用独立的 alpha 参数（pos_alpha=0.25, neg_alpha=0.75）平衡正负样本的重要性

**运行命令**:
```bash
cd official/improved_versions/V3_Asymmetric_FocalLoss
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log \
    --loss_type asymmetric
```

---

### V4: MultiHead_Pooling（多头注意力输出池化）

**改进点**: 将简单的 concat + MLP 输出投影替换为带有多头注意力池化的自适应聚合方式。

**具体改动** (`model.py`):
- 保留原有 `output_proj`（MLP 投影 -> d_model）
- 新增 `output_attn_pool`（MultiheadAttention）：用一个可学习的 query 向量对拼接后的所有 Q tokens 做注意力加权聚合
- 最终输出 = MLP 投影 + 注意力池化结果（残差融合）

**改进原理**: 
- 不同序列的 Q token 重要性可能不同，注意力池化可以自适应地学习权重
- 残差连接确保 MLP 路径和注意力路径互补
- 比简单的 concat 更能捕获跨序列的交互信息

**运行命令**:
```bash
cd official/improved_versions/V4_MultiHead_Pooling
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log
```

---

### V5: SwiGLU_FFN（全局 SwiGLU 激活）

**改进点**: 将模型中所有 FFN 层的 GELU 激活替换为 SwiGLU（SiLU 门控）。

**具体改动** (`model.py`):
- 新增 `SwiGLU_activation` 辅助类，可在 `nn.Sequential` 中使用
- `TransformerEncoder.ffn`: GELU → SwiGLU
- `LongerEncoder.ffn`: GELU → SwiGLU

**改进原理**: 
- SwiGLU = x1 * SiLU(x2)，通过门控机制带来更好的梯度流
- 被 LLM（PaLM、LLaMA）和多个 CTR 模型验证为优于 GELU
- 在保持推理效率的同时提升表达力

**运行命令**:
```bash
cd official/improved_versions/V5_SwiGLU_FFN
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log
```

---

### V6: Deeper_HyFormer（加深网络）

**改进点**: 将 HyFormer Block 数量从 2 增加到 4。

**具体改动** (`model.py`):
- `num_hyformer_blocks` 默认值: 2 → 4

**改进原理**: 
- 更多的 HyFormer 层可以提供更深的序列交互和特征变换
- 每增加一层，模型就能多进行一次"序列编码 → Query 解码 → Query 增强"的循环
- 需要配合足够的数据量和正则化手段防止过拟合

**运行命令**:
```bash
cd official/improved_versions/V6_Deeper_HyFormer
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log
```

---

### V7: Wider_Embeddings（加宽嵌入）

**改进点**: 将模型维度和 Embedding 维度从 64 扩展到 128。

**具体改动** (`model.py`):
- `d_model`: 64 → 128
- `emb_dim`: 64 → 128

**改进原理**: 
- 更宽的表示维度可以捕获更丰富的特征交互
- 128 维在工业级 CTR 模型中是一个常见选择，在精度和计算量之间取得平衡
- 配合竞赛平台的 GPU 资源，128 维通常不会造成显存瓶颈

**运行命令**:
```bash
cd official/improved_versions/V7_Wider_Embeddings
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log \
    --d_model 128 --emb_dim 128
```

---

### V8: Auxiliary_MultiTask（辅助多任务学习）

**改进点**: 添加辅助预测头，利用多任务学习增强共享表示。

**具体改动**:
- `model.py`: 新增 `aux_head`（3 个辅助分类器输出），`forward()` 返回 `(logits, aux_logits)`
- `trainer.py`: 在训练 loss 中加入辅助任务 loss（权重 0.1），使用 BCE loss

**改进原理**: 
- 多任务学习是一种有效的正则化手段
- 辅助任务迫使共享表示学习更丰富的特征，减少对主任务标签的过拟合
- 辅助 loss 权重很小（0.1），以避免干扰主任务的优化

**运行命令**:
```bash
cd official/improved_versions/V8_Auxiliary_MultiTask
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log
```

---

### V9: SENet_Recalibration（特征重标定）

**改进点**: 在 NS Tokenizer 之后加入 Squeeze-and-Excitation 模块，对特征进行自适应重标定。

**具体改动** (`model.py`):
- 新增 `SENetRecalibration` 类：通过"全局均值池化 → 2 层 FC → Sigmoid"学习特征权重
- 在 `PCVRHyFormer.__init__` 中为 user/item NS 分别创建 SE 模块
- 在 `forward()` 中对 user_ns 和 item_ns 应用 SE 重标定

**改进原理**: 
- SENet 通过通道维度的注意力机制，让模型自动学习哪些特征对当前任务更重要
- 特别适合 CTR 场景中特征重要性差异大的情况
- 计算量增加很小（只有 2 层 FC），但能有效提升特征利用率

**运行命令**:
```bash
cd official/improved_versions/V9_SENet_Recalibration
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log
```

---

### V10: GRN_QueryBoosting（门控残差网络增强）

**改进点**: 将 RankMixer 的参数无关 token mixing 替换为 GRN（Gated Residual Network）的带门控残差机制。

**具体改动** (`model.py`):
- 新增 `GRNQueryBoosting` 类：
  - 门控: `sigmoid(Linear(x)) * x`，自适应控制信息流
  - FFN: 共享参数的 2 层全连接
  - 残差连接 + Post-LN 稳定训练
- `MultiSeqHyFormerBlock` 中的 mixer 使用 GRN 替代 RankMixer
- 移除了 RankMixer 的 `d_model % T == 0` 约束

**改进原理**: 
- RankMixer 的参数无关 token mixing 虽然高效但灵活性受限
- GRN 通过学习门控参数，能自适应地决定哪些 token 需要更多交互
- 门控机制也提供了隐式的正则化效果

**运行命令**:
```bash
cd official/improved_versions/V10_GRN_QueryBoosting
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log
```

---

### V11: StochasticDepth（随机深度）

**改进点**: 在 HyFormer Block 层级引入随机深度（Stochastic Depth），训练时以一定概率随机丢弃整个 Block。

**具体改动** (`model.py`):
- 为每个 Block 设定线性递增的生存概率（0.8 → 1.0）
- 在 `_run_multi_seq_blocks` 训练阶段:
  - 以 `1 - survival_prob` 的概率跳过该 Block
  - 对保留的 Block 输出按 `1/survival_prob` 做缩放（保持期望一致）

**改进原理**: 
- Stochastic Depth 是 Deep Networks with Stochastic Depth 中提出的有效正则化方法
- 更深的层有更高的生存概率（深层学习更抽象的特征，不宜过多丢弃）
- 训练时相当于隐式地训练了多个不同深度的子网络（类似 ensemble）
- 特别适合 V6 等加深网络的版本

**运行命令**:
```bash
cd official/improved_versions/V11_StochasticDepth
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log
```

---

### V12: LabelSmoothing（标签平滑）

**改进点**: 对训练标签应用标签平滑（Label Smoothing），将 one-hot 标签变为软标签。

**具体改动**:
- `utils.py`: 新增 `smooth_labels()` 函数
- `trainer.py`: 在 `_train_step()` 中对 `label` 应用标签平滑后再计算 loss

**改进原理**: 
- 标签平滑是一种经典的正则化技术，防止模型对训练标签过度自信
- 软标签使得模型在预测时更加保守，通常能改善泛化能力
- 在类别不平衡的场景中，标签平滑还能缓解模型偏向多数类的问题

**运行命令**:
```bash
cd official/improved_versions/V12_LabelSmoothing
bash run.sh --data_dir /path/to/data --ckpt_dir /path/to/ckpt --log_dir /path/to/log
```

---

## 使用指南

### 通用运行方式

每个版本都是一个独立的、可运行的程序包，包含完整的训练代码。使用方法：

```bash
cd official/improved_versions/<版本目录>
bash run.sh \
    --data_dir /path/to/training_data \
    --ckpt_dir /path/to/checkpoints \
    --log_dir /path/to/logs \
    --num_epochs 50 \
    --batch_size 256 \
    --patience 5
```

### 环境变量（可选）

```bash
export TRAIN_DATA_PATH=/path/to/training_data
export TRAIN_CKPT_PATH=/path/to/checkpoints
export TRAIN_LOG_PATH=/path/to/logs
```

### 快速对比脚本

```bash
# 依次运行所有版本（需要根据平台调整路径）
for v in V1_Baseline V2_DNN_Classifier V3_Asymmetric_FocalLoss V4_MultiHead_Pooling \
         V5_SwiGLU_FFN V6_Deeper_HyFormer V7_Wider_Embeddings V8_Auxiliary_MultiTask \
         V9_SENet_Recalibration V10_GRN_QueryBoosting V11_StochasticDepth V12_LabelSmoothing; do
    echo "=== Running $v ==="
    cd official/improved_versions/$v
    bash run.sh --data_dir $DATA_DIR --ckpt_dir $CKPT_DIR/$v --log_dir $LOG_DIR/$v
done
```

---

## 改进脉络

```
V1 (Baseline) ── 基础架构
    │
    ├── V2 (DNN Classifier) ── 分类头增强
    ├── V3 (Asymmetric Focal) ── Loss 优化
    ├── V4 (Multi-Head Pooling) ── 输出聚合优化
    ├── V5 (SwiGLU FFN) ── 激活函数升级
    ├── V6 (Deeper) ── 深度扩展
    ├── V7 (Wider) ── 宽度扩展
    ├── V8 (Multi-Task) ── 多任务正则化
    ├── V9 (SENet) ── 特征重标定
    ├── V10 (GRN Boosting) ── 增强模块升级
    ├── V11 (Stochastic Depth) ── 随机深度正则化
    └── V12 (Label Smoothing) ── 标签平滑正则化
```

---

## 组合建议

以上改进点可以自由组合，建议的组合方式：

1. **轻量级组合** (V3 + V12): 只改进 Loss 函数，零额外推理开销
2. **结构优化组合** (V4 + V9 + V10): 改进模型内部结构，提升特征利用
3. **规模和正则化组合** (V7 + V11 + V12): 增大模型容量 + 强化正则化
4. **全能组合** (V2 + V5 + V7 + V10): 全面提升模型表达能力

---

## 文件清单

每个版本目录包含以下文件：

```
V*_Name/
├── model.py          # 模型定义（核心改动）
├── train.py          # 训练入口（部分版本有改动）
├── trainer.py        # 训练器（部分版本有改动）
├── dataset.py        # 数据加载（所有版本相同）
├── utils.py          # 工具函数（部分版本有改动）
├── ns_groups.json    # NS 分组配置（所有版本相同）
└── run.sh            # 运行脚本
```
