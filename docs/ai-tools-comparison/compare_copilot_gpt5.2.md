# HyFormer vs OneTrans（Copilot / GPT-5.2 对话整理）

本文把上面两轮对话内容整理成一份可复制的对比与运行指南，便于后续回看。

---

## 1. 两个仓库的算法框架与基本原理（面向小白）

### 整体框架（两个仓库共同点）

- 都是“可跑通的推荐/CTR 训练工程”：数据下载/读取 → 特征张量化 → 模型前向 → `CrossEntropyLoss` → 评测（Accuracy、AUC）→ AMP 混合精度 → 保存/恢复 checkpoint。
- 数据张量化核心在 `utils/taac_data.py`：
  - 非序列特征（scalar/array）会被转成一个长向量；array 会被总结成 `mean/std/min/max/last/length` 这 6 个统计量。
  - 数值做了 `log1p` 风格的压缩（`squash_numeric`），字符串会哈希成稳定的浮点数。
  - 标签会做映射（把原始 label 映射到 0..C-1）。
- 评测指标在 `utils/metrics.py`：AUC 用排序秩（rank）计算；二分类直接算正样本得分的 AUC，多分类做 one-vs-rest 平均。

### 推荐算法小白先懂 3 件事（生活例子）

- 目标：给“用户 u”从候选“物品 i”里挑更可能喜欢/点击/购买的。常见监督学习目标是 CTR/转化率：预测

  P(click=1 | u, i, context, history)

- 特征分两大类（这俩仓库也按这个切）
  1) 非序列特征（non-seq）：一次请求就有的“静态/上下文”信息。例：用户年龄、会员等级、当前时间、曝光位、商品类目等。
  2) 序列特征（seq）：用户最近行为列表（有顺序）。例：最近 20 次浏览/点击的类目、价格、品牌等。
- 为什么要“序列建模”：你昨天看“露营帐篷”，今天看“户外炉具”，系统推“登山包”更合理；序列模型要学的就是这种“最近兴趣的迁移”。

---

## 2. OneTrans（OneTrans_Pytorch）核心结构与直观理解

可以把 OneTrans 理解成：把结构化特征塞进 token 序列里，然后把序列信息逐步“压缩吸收”到前缀 token 里。

### 2.1 输入怎么喂（token 化）

- 非序列向量 [B, non_seq_dim] → 通过线性层 → `ns_len` 个“伪 token”：[B, ns_len, d_model]
- 序列矩阵 [B, seq_len, seq_feature_dim] → 通过线性层 → 序列 token：[B, seq_len, d_model]
- 拼起来成为 token 序列：[ns_tokens, seq_tokens]

### 2.2 与普通 Transformer 的关键差异

- 不同 token 用不同参数：
  - 前 `ns_len` 个 token（非序列伪 token）每个都有自己的一套 Q/K/V 投影层和 FFN
  - 后面的序列 token 共享一套（“共享组”）
- 注意力 mask 可选：支持 `origin / hard_mask / bimask_soft / bimask_hard`
  - `bimask_*` 的直观理解：让非序列 token 更“全局”，序列 token 更“因果/只看过去”。

### 2.3 金字塔压缩（pyramid compression）：核心思想

- 先做“全长”的 base block，然后后续 block 让 query 长度逐步变短：

  [ns + seq] → [ns + seq - 1] → ... → [ns]

- 类比：做读书笔记，先读全文，再一轮轮压缩，最后只留下最关键的 `ns_len` 条摘要；最终用这些摘要做预测。

### 2.4 实际例子

- 电商推荐：
  - 非序列：用户等级、当前小时、价格带 → 变成 `ns_len=4` 个摘要 token
  - 序列：最近 16 次浏览类目/品牌 → 变成 16 个行为 token
  - 金字塔压缩让 16 条行为信息逐步“吸收”进 4 个摘要 token，最后预测“会不会点”。

---

## 3. HyFormer（Hyformer_Pytorch）核心结构与直观理解

HyFormer 更像：多条行为序列分支 + query token 去每条序列里检索信息，再把检索结果与上下文特征进行融合。

### 3.1 为什么强调多序列（multi-sequence）

- 真实推荐常见多种行为流：浏览序列、点击序列、加购序列、搜索词序列……语义不同。
- 该仓库在 sample 数据上做了“自动分组”：把检测到的序列通道均匀分到 `--num-sequences` 组里，形成多个分支输入。

### 3.2 输入怎么喂（更结构化）

- 非序列向量 → `num_non_seq_tokens` 个 non-seq tokens
- 序列张量形状：[B, num_sequences, seq_len, seq_feature_dim]（每个分支各自一条序列）
- 还有 query tokens：每个序列分支有 `global_tokens_per_seq` 个 query token，由全局信息生成（非序列向量 + 每个序列分支的均值池化表示）。

### 3.3 每层做两件事（抓住这点就懂了）

- Query Decoding（查询解码）：query 对该分支序列做 cross-attention，相当于“带着问题去翻历史记录找答案”。
- Query Boosting（查询增强/混合）：把所有分支的 decoded queries 和 non-seq tokens 拼在一起，用类似 MLP-Mixer 的 token mixing 让不同分支/不同特征发生交互融合。

### 3.4 序列编码器可选（seq_encoder_type）

- `full_transformer`：标准自注意力建模序列
- `longer`：先把长序列 pool 成短序列，再 cross-attend（先摘要再对齐）
- `swiglu`：不用注意力，纯前馈（更快的 baseline）

### 3.5 实际例子

- 视频推荐：
  - 分支 A（浏览历史）、分支 B（点赞历史）、分支 C（搜索词历史）
  - 生成 3 个 query：分别去问“最近在看什么？”“真正喜欢什么？”“当下要找什么？”
  - 每个 query 在各自序列里检索，再与用户画像/时间等 non-seq tokens 混合，预测某条视频点击概率。

---

## 4. 两个算法怎么选（小白建议）

- 想要“概念更少、快速跑通、把序列信息压成摘要再分类” → OneTrans 更友好
- 想要“贴近真实多行为流、强调序列与特征交互、结构更灵活” → HyFormer 更贴近工业语义

---

## 5. 如何在本机跑这两个 baseline（uv 环境 + mac / GPU 说明）

### 5.1 需要 GPU 吗？mac 能跑训练吗？

- 不需要 GPU 也能跑通（只是更慢）。
- 在 mac 上可以训练跑起来：用 `--device cpu` 或（Apple Silicon 推荐）`--device mps`。
- 这两个训练脚本的 AMP 只会在 CUDA 上启用，所以 mac 上建议显式加 `--no-amp`。

### 5.2 用 uv 创建环境 + 安装依赖（共享一套环境即可）

在 workspace 根目录执行（/Users/xiazhiwei/Uni-Rec-Challenge）：

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge

uv venv --python 3.11
source .venv/bin/activate

# 脚本里确定会用到的
uv pip install torch datasets huggingface_hub pyarrow
```

可选：确认设备可用性（看有没有 mps / cuda）：

```bash
python -c "import torch; print('torch', torch.__version__); print('cuda', torch.cuda.is_available()); print('mps', hasattr(torch.backends,'mps') and torch.backends.mps.is_available())"
```

说明：
- Apple Silicon 通常会显示 `mps True`，可用 `--device mps`。
- mac 没有 CUDA。

---

## 6. OneTrans baseline 怎么跑

### 6.1 先跑骨架 shape demo（最快验证代码能跑）

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge/OneTrans_Pytorch
python main_pytorch.py
```

### 6.2 最小训练（mac 推荐 mps；没有 mps 就用 cpu）

Apple Silicon（推荐）：

```bash
python scripts/run_taac2026_sample.py \
  --device mps --no-amp \
  --max-rows 1000 --epochs 1 --batch-size 32
```

CPU：

```bash
python scripts/run_taac2026_sample.py \
  --device cpu --no-amp \
  --max-rows 1000 --epochs 1 --batch-size 32
```

试试不同 mask：

```bash
python scripts/run_taac2026_sample.py --device mps --no-amp --max-rows 1000 --epochs 1 --mask_type bimask_hard
```

---

## 7. HyFormer baseline 怎么跑

### 7.1 先跑骨架 shape demo

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge/Hyformer_Pytorch
python main_pytorch.py
```

### 7.2 最小训练（mac 上建议 `--no-amp`）

Apple Silicon（推荐）：

```bash
python scripts/run_taac2026_sample.py \
  --device mps --no-amp \
  --max-rows 1000 --epochs 1 --batch-size 16 \
  --num-sequences 3 --seq-len 16
```

CPU：

```bash
python scripts/run_taac2026_sample.py \
  --device cpu --no-amp \
  --max-rows 1000 --epochs 1 --batch-size 16 \
  --num-sequences 3 --seq-len 16
```

切换序列编码器：

```bash
python scripts/run_taac2026_sample.py --device mps --no-amp --max-rows 1000 --epochs 1 --seq-encoder-type swiglu
python scripts/run_taac2026_sample.py --device mps --no-amp --max-rows 1000 --epochs 1 --seq-encoder-type full_transformer
```

---

## 8. 数据下载 / 离线说明

- 默认会从 Hugging Face 拉 `TAAC2026/data_sample_1000`，首次运行需要联网。
- 如果你有本地 parquet，两边都可以用：

```bash
--local-parquet /path/to/xxx.parquet
```

---

## 9. 结果在哪里看

- 控制台每个 epoch 会输出：`train_loss/train_auc/train_acc/val_loss/val_auc/val_acc`。
- 如果加 `--save-checkpoint`，会在各自仓库的 `outputs/taac2026_sample/` 下写 `run_metadata.json` 和 checkpoint（脚本启动时也会打印保存路径）。
