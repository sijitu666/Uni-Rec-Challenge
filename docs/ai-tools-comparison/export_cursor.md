# 推荐算法基础内容总结
_Exported on 2026/4/19 at GMT+8 2:23:02 from Cursor (2.5.26)_

---

**User**

总结这两个仓库的算法框架，给一个推荐算法小白讲懂这两个算法基本原理，给一些容易理解的实际例子讲讲推荐算法的基础内容

---

**Cursor**

我先快速浏览当前工作区结构，确认“这两个仓库”分别是哪两个，然后基于它们的代码框架给你做一份面向小白的推荐算法讲解。接下来我会先看目录和关键说明文档。

我已经确认是 `OneTrans_Pytorch` 和 `Hyformer_Pytorch` 两个仓库。现在我会读它们的 README 和核心模型代码，然后用“入门友好”的方式对比讲清楚。

你这两个仓库本质上是在做同一件事：**预测用户会不会点击/喜欢某个内容（CTR/推荐打分）**，但它们“理解用户行为序列”的方式不同。

---

## 先用一句话区分两者

- `OneTrans_Pytorch`：把用户信息和行为序列拼成一串 token，然后通过“逐层压缩序列”提炼出最终表示。  
- `Hyformer_Pytorch`：把不同行为序列分成多条“分支”，每条分支用专门 query 去读，再统一融合（boost）。

---

## 推荐算法小白先要懂的 3 个基础概念

- **非序列特征**：静态信息，比如年龄、性别、会员等级、手机型号。  
- **序列特征**：有时间顺序的行为，比如最近看过的商品/视频。  
- **目标**：给每个候选内容一个分数，分数越高越值得推荐。

你可以把模型理解成：  
“输入 = 用户档案 + 最近行为；输出 = 点击概率（或兴趣分）”。

---

## OneTrans 框架（`OneTrans_Pytorch`）

核心流程（非常直观）：

1. 非序列特征 -> 映射成 `ns_len` 个 pseudo token  
2. 序列特征 -> 映射成 `seq_len` 个序列 token  
3. 拼起来：`[ns_tokens, seq_tokens]`  
4. 过基础 OneTrans block  
5. 过金字塔压缩 block（长度一步步变短）  
6. 最后只留下前面的 `ns_tokens`，池化后做分类/打分

### 它的“特别点”
- 前 `ns_len` 个 token 用**各自独立参数**（更像“专家位”）
- 后面的序列 token 共享参数
- 压缩过程像“把长行为历史的信息，逐步灌进少量核心 token”

### 小白类比
像你做购物推荐：  
- 静态信息是“用户画像卡片”（预算、品牌偏好）  
- 行为序列是“最近浏览清单”  
- OneTrans 会不断把浏览清单压缩总结，最后浓缩到几张画像卡片里，再决定推荐什么。

---

## HyFormer 框架（`Hyformer_Pytorch`）

核心流程：

1. 非序列特征 -> 非序列 token  
2. 序列特征按语义分成多条分支（如浏览、收藏、加购）  
3. 每个分支形成自己的序列 token 流  
4. 用全局信息生成每个分支的 query token  
5. 交替做两件事：  
   - **Query Decoding**：query 去“读”对应分支序列  
   - **Query Boosting**：把各分支 query + 非序列 token 一起融合增强  
6. 最后池化，接分类头输出分数

### 它的“特别点”
- 强调“**多序列分而治之**”：每类行为单独建模  
- query 相当于“提问器”：对每条行为序列问“对当前推荐目标最相关的信息是什么？”
- 融合器（boost mixer）负责跨分支交互

### 小白类比
还是电商推荐：  
- 浏览记录一条线、加购记录一条线、购买记录一条线  
- 每条线都派一个“小分析师（query）”总结重点  
- 最后开会合并观点，得出推荐结论。

---

## 两个框架怎么选（入门视角）

- 数据只有“一条主行为序列”且你想先跑通：`OneTrans` 更直接。  
- 你的业务天然有“多行为通道”（看、搜、购、评）：`HyFormer` 更贴近现实。  
- `OneTrans` 偏“统一序列 + 压缩”；`HyFormer` 偏“多分支 + 查询融合”。

---

## 推荐算法基础内容（配实际例子）

### 1) 召回 + 排序（工业界常见两阶段）
- **召回**：先从千万内容里捞几百个（快）。  
- **排序**：用这类模型精排这几百个（准）。

例子：短视频 App  
- 召回先找“可能感兴趣”的 500 条  
- 排序模型给每条打分，最终展示前 20 条。

### 2) 为什么要建模“序列”
- 用户兴趣会变。  
- 最近行为通常比很久以前更重要。

例子：  
昨天一直看“露营装备”，今天首页应该多给户外内容，而不是半年前看过的数码评测。

### 3) 为什么要同时看“静态 + 动态”
- 静态画像决定长期偏好  
- 动态序列反映短期意图

例子：  
同样都爱运动鞋（长期偏好），但这周在搜“登山包”（短期意图），推荐就要偏户外。

### 4) 模型训练目标是什么
- 常用二分类：点/不点、买/不买  
- 损失函数通常是交叉熵，评估常用 AUC、Accuracy

---

如果你愿意，我可以下一步给你画一版**“OneTrans vs HyFormer 的一页流程图（纯文字版）**，并结合你比赛数据字段，告诉你每个字段在两种框架里该怎么喂进去。

---

**User**

好的，我现在了解了两篇论文的基本算法原理了，现在我如果想要跑一下这两份代码仓库的代码，我应该怎么跑？需要gpu么？跑训练可以在我的mac电脑上跑起来么？结合代码要求看看怎么跑一下这两个baseline，看看结果（如果需要创建环境请用uv创建环境），给我命令我来跑就行，不用你调用工具直接跑

---

**Cursor**

很好，你现在可以直接开跑了。结合这两个仓库的代码结构，我给你一套**可在 Mac 上跑通**的最小命令方案（用 `uv` 建环境）。

## 先回答你三个关键问题

- **需要 GPU 吗？**  
  不强制。两个 baseline 都能在 CPU 跑通（尤其是样例数据 `data_sample_1000`）。
- **Mac 能跑训练吗？**  
  可以。只是速度比 NVIDIA CUDA 慢很多。  
- **建议怎么跑？**  
  先跑 `main_pytorch.py` 做骨干网络 shape sanity check，再跑 `scripts/run_taac2026_sample.py` 小 epoch 训练看 AUC/ACC。

---

## 1) 用 `uv` 创建环境（一次即可）

在工作区根目录（`/Users/xiazhiwei/Uni-Rec-Challenge`）执行：

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge

# 1) 创建虚拟环境（推荐 Python 3.10 或 3.11）
uv venv --python 3.11

# 2) 激活环境
source .venv/bin/activate

# 3) 安装通用依赖
uv pip install torch datasets pandas pyarrow scikit-learn tqdm numpy
```

> 说明：这两个仓库都没有单独复杂依赖声明，以上这批通常足够跑通。

---

## 2) 跑 OneTrans baseline

### 2.1 骨干网络自检（不训练）
```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge/OneTrans_Pytorch
python main_pytorch.py
```

你会看到各阶段 shape 打印（例如压缩后 token 长度逐步减少）。

### 2.2 跑一个最小训练（CPU 友好）
```bash
python scripts/run_taac2026_sample.py \
  --epochs 3 \
  --batch-size 32 \
  --no-amp \
  --mask_type bimask_hard \
  --save-checkpoint
```

可再试默认 mask：
```bash
python scripts/run_taac2026_sample.py \
  --epochs 3 \
  --batch-size 32 \
  --no-amp \
  --mask_type origin
```

---

## 3) 跑 HyFormer baseline

### 3.1 骨干网络自检
```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge/Hyformer_Pytorch
python main_pytorch.py
```

### 3.2 跑最小训练（先用 `longer`）
```bash
python scripts/run_taac2026_sample.py \
  --epochs 3 \
  --batch-size 32 \
  --no-amp \
  --seq-encoder-type longer \
  --save-checkpoint
```

再对比两种 encoder：
```bash
python scripts/run_taac2026_sample.py \
  --epochs 3 \
  --batch-size 32 \
  --no-amp \
  --seq-encoder-type full_transformer
```

```bash
python scripts/run_taac2026_sample.py \
  --epochs 3 \
  --batch-size 32 \
  --no-amp \
  --seq-encoder-type swiglu
```

---

## 4) Mac 上的实际建议（很重要）

- 你在 Mac 上跑时，**强烈建议带 `--no-amp`**（代码里 AMP 主要针对 CUDA）。  
- 首次运行会从 Hugging Face 拉 `TAAC2026/data_sample_1000`，需要联网。  
- 如果你只是验证流程，`--epochs 1~3` 就够。  
- 如果内存紧张，把 `--batch-size` 调到 `16` 或 `8`。

---

## 5) 你可以怎么“看结果”

训练日志里重点看：
- `val_auc`（越高越好）
- `val_acc`（分类准确率）

并且开启 `--save-checkpoint` 后会生成类似：
- `best_model_YYYYMMDD_HHMMSS.pt`

你可以把 OneTrans 和 HyFormer 在同样 `epochs/batch-size` 下的 `val_auc` 抄出来做表格对比。

---

如果你愿意，我下一步可以直接给你一份**“可复制粘贴的一键脚本版”**（包含两个仓库依次跑、自动记录日志到文件、最后 grep 出 AUC 对比）。

---

**User**

把我们上面两条对话内容写入当前目录的一个compare_cursor_auto.md的文档中

---

**Cursor**

我会把前面两轮问答（算法原理讲解 + 运行方式说明）整理成一个 `compare_cursor_auto.md`，放在当前目录，内容用 Markdown 结构化方便你后续查看。

已写入完成，文件在：

- `compare_cursor_auto.md`

我把前面两轮核心问答都整理进去了（算法原理对比 + 本地运行命令与建议）。如果你希望我改成“原始逐句聊天记录”格式，我也可以再给你转成 QA 时间线版本。

