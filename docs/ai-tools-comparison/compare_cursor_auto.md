# 对话记录：OneTrans 与 HyFormer

## 对话 1：算法框架与基础原理讲解

### 用户
总结这两个仓库的算法框架，给一个推荐算法小白讲懂这两个算法基本原理，给一些容易理解的实际例子讲讲推荐算法的基础内容

### 助手
你这两个仓库本质上是在做同一件事：**预测用户会不会点击/喜欢某个内容（CTR/推荐打分）**，但它们“理解用户行为序列”的方式不同。

- `OneTrans_Pytorch`：把用户信息和行为序列拼成一串 token，然后通过“逐层压缩序列”提炼出最终表示。  
- `Hyformer_Pytorch`：把不同行为序列分成多条“分支”，每条分支用专门 query 去读，再统一融合（boost）。

先理解推荐算法小白最需要的 3 个概念：

- **非序列特征**：静态信息，比如年龄、性别、会员等级、手机型号。  
- **序列特征**：有时间顺序的行为，比如最近看过的商品/视频。  
- **目标**：给每个候选内容一个分数，分数越高越值得推荐。

### OneTrans 框架

1. 非序列特征 -> 映射成 `ns_len` 个 pseudo token  
2. 序列特征 -> 映射成 `seq_len` 个序列 token  
3. 拼起来：`[ns_tokens, seq_tokens]`  
4. 过基础 OneTrans block  
5. 过金字塔压缩 block（长度一步步变短）  
6. 最后只留下前面的 `ns_tokens`，池化后做分类/打分

特点：

- 前 `ns_len` 个 token 用各自独立参数（更像“专家位”）  
- 后面的序列 token 共享参数  
- 压缩过程是逐步将长序列信息注入少量核心 token

### HyFormer 框架

1. 非序列特征 -> 非序列 token  
2. 序列特征按语义分成多条分支  
3. 每个分支形成自己的序列 token 流  
4. 用全局信息生成每个分支的 query token  
5. 交替执行：  
   - Query Decoding（query 读分支序列）  
   - Query Boosting（query + 非序列 token 融合增强）  
6. 最后池化并分类

特点：

- 多序列分而治之  
- query 类似“提问器”，每条行为分支有专门提取器  
- boost 负责跨分支交互融合

### 推荐基础知识（结合例子）

- 工业界常见两阶段：召回（快）+ 排序（准）  
- 序列建模用于捕捉用户短期兴趣变化  
- 静态画像（长期偏好）+ 动态行为（短期意图）一起建模更有效  
- 常见训练目标是二分类（点击/不点击），指标看 AUC 和 Accuracy

---

## 对话 2：如何在本地运行两个 baseline

### 用户
好的，我现在了解了两篇论文的基本算法原理了，现在我如果想要跑一下这两份代码仓库的代码，我应该怎么跑？需要gpu么？跑训练可以在我的mac电脑上跑起来么？结合代码要求看看怎么跑一下这两个baseline，看看结果（如果需要创建环境请用uv创建环境），给我命令我来跑就行，不用你调用工具直接跑

### 助手
结论：

- 不强制需要 GPU，CPU 可跑通  
- Mac 可以跑训练（速度较慢）  
- 建议先跑 `main_pytorch.py` 做 shape 验证，再跑 `scripts/run_taac2026_sample.py` 做小规模训练

### 环境创建（uv）

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge
uv venv --python 3.11
source .venv/bin/activate
uv pip install torch datasets pandas pyarrow scikit-learn tqdm numpy
```

### OneTrans 运行命令

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge/OneTrans_Pytorch
python main_pytorch.py
```

```bash
python scripts/run_taac2026_sample.py \
  --epochs 3 \
  --batch-size 32 \
  --no-amp \
  --mask_type bimask_hard \
  --save-checkpoint
```

```bash
python scripts/run_taac2026_sample.py \
  --epochs 3 \
  --batch-size 32 \
  --no-amp \
  --mask_type origin
```

### HyFormer 运行命令

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge/Hyformer_Pytorch
python main_pytorch.py
```

```bash
python scripts/run_taac2026_sample.py \
  --epochs 3 \
  --batch-size 32 \
  --no-amp \
  --seq-encoder-type longer \
  --save-checkpoint
```

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

### 结果查看建议

- 重点看验证集 `val_auc`、`val_acc`  
- 开启 `--save-checkpoint` 会保存 `best_model_*.pt`  
- 使用相同超参数对比 OneTrans 与 HyFormer 的 AUC 更公平
