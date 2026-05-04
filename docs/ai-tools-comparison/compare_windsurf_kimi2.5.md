# HyFormer vs OneTrans 算法对比与运行指南

## 第一部分：算法原理对比

### 推荐算法基础概念（小白入门）

#### 场景：短视频App的"猜你喜欢"

假设你打开抖音/快手，系统要预测你会不会点击某个视频。推荐系统会看两类信息：

| 特征类型 | 例子 | 特点 |
|---------|------|------|
| **非序列特征**（静态） | 用户年龄、性别、当前时间 | 与时序无关，单次固定值 |
| **序列特征**（动态） | 过去10分钟浏览记录、过去1小时点赞记录 | 有先后顺序，反映行为演变 |

**核心问题**：如何有效融合这两类特征，预测点击率(CTR)？

---

### OneTrans 算法解析

#### 核心思想
OneTrans 把两类特征都转换成"token"，然后用统一的Transformer处理。它的创新点是**不同的token用不同的参数**。

#### 工作流程图解

```
输入层：
┌─────────────────────────────────────────┐
│ 非序列特征 → [ns_len个伪token]           │  (如：4个静态信息token)
│ 序列特征   → [seq_len个序列token]        │  (如：16个行为记录token)
└─────────────────────────────────────────┘
                  ↓
          拼接成完整token序列
                  ↓
        ┌─────────────────┐
        │   OneTrans块    │  ← 关键：前ns_len个token各自用独立参数
        │  (Attention+FFN)│     后面的序列token共享一套参数
        └─────────────────┘
                  ↓
        ┌─────────────────┐
        │  金字塔压缩层   │  ← 逐层减少token数量，信息被吸收到前ns_len个token
        │ (pyramid stack) │    seq_len+ns_len → ... → ns_len
        └─────────────────┘
                  ↓
        对最终的ns_len个token取平均 → 预测结果
```

#### 关键创新点

**1. 参数分组策略**

```python
# ns_len=4 时，有5组独立的Q/K/V投影参数
# - token 0,1,2,3 各自用独立参数
# - token 4到末尾 共享第5组参数
self.kqv_list = nn.ModuleList([
    [nn.Linear(d_model, d_model) for _ in range(3)] 
    for _ in range(ns_len + 1)  # 5组参数
])
```

**为什么这样做？**
- 非序列token（前ns_len个）承载的是**全局静态信息**，需要精细处理
- 序列token（后面的）承载的是**行为流信息**，可以共享参数提高效率

**2. 金字塔压缩**

```python
# 假设初始有 2+16=18 个token (ns_len=2, seq_len=16)
stack_1: 18 → 17 tokens   # pyramid_stack_len=17
stack_2: 17 → 16 tokens   # pyramid_stack_len=16
stack_3: 16 → 15 tokens   # ...
...直到只剩 2 个token
```

**直觉理解**：类似"漏斗"，逐步把序列信息**蒸馏**到静态token中，最终用这ns_len个浓缩后的token做预测。

---

### HyFormer 算法解析

#### 核心思想
HyFormer 针对**多序列场景**设计（如：浏览序列、点赞序列、搜索序列）。它引入**查询token(Query)**主动从各序列中"提取"信息。

#### 工作流程图解

```
输入层：
┌──────────────────────────────────────────┐
│ 非序列特征 → [num_non_seq_tokens]        │
│ 序列1(浏览) → [seq1_len个token]         │
│ 序列2(点赞) → [seq2_len个token]         │  ← 支持多条序列
│ 序列3(搜索) → [seq3_len个token]         │
└──────────────────────────────────────────┘
                  ↓
        ┌─────────────────┐
        │  Query生成器     │  ← 从全局信息生成每序列对应的查询token
        └─────────────────┘
                  ↓
        ┌─────────────────────────────────┐
        │     HyFormer Layer (重复N层)     │
        │  ┌─────────────────────────┐    │
        │  │  Query Decoding         │    │  ← 查询token交叉注意力到对应序列
        │  │  (Cross-Attention)      │    │    "看看这条序列里有什么重要信息"
        │  └─────────────────────────┘    │
        │              ↓                   │
        │  ┌─────────────────────────┐    │
        │  │  Query Boosting         │    │  ← 混合所有query和非序列token
        │  │  (Token Mixing)         │    │    "综合所有信息，互相交流"
        │  └─────────────────────────┘    │
        └─────────────────────────────────┘
                  ↓
        最终 boosted tokens → 预测结果
```

#### 关键创新点

**1. 查询生成机制**

```python
# 每序列有独立的查询生成器
pooled_sequences = [masked_mean_pool(seq) for seq in sequences]
global_info = concat([non_seq_features] + pooled_sequences)
query_tokens = [
    generator[seq_i](global_info)  # 每序列一个生成器
    for seq_i in range(num_sequences)
]
```

**直觉**：就像派不同的"调研员"去各序列"采集情报"，每个调研员专精一类行为。

**2. Query Decoding（解码）**

```python
# 查询token作为Query，序列token作为Key/Value
attn_out, _ = self.attn(
    query_norm(query),      # 查询
    kv_norm(key_value),     # 序列作为Key
    kv_norm(key_value),     # 序列作为Value
)
return query + attn_out    # 残差连接
```

**作用**：查询token"关注"到序列中与之相关的部分，实现**跨序列信息提取**。

**3. Query Boosting（增强）**

```python
# 将解码后的查询和所有非序列token混合
mixed_tokens = concat(decoded_queries + [non_seq_tokens])
# 使用类似MLP-Mixer的结构：先token间混合，再特征维度混合
boosted_tokens = token_mix(mixed_tokens)
```

**作用**：让不同序列的情报员"开会交流"，互相补充信息，并与静态特征融合。

**4. 三种序列编码器**

| 类型 | 原理 | 适用场景 |
|-----|------|---------|
| `longer` | 短查询交叉注意力压缩长序列 | 超长序列（效率优先） |
| `full_transformer` | 标准自注意力 | 常规长度序列 |
| `swiglu` | 无注意力纯前馈 | 短序列（速度优先） |

---

### 两个算法的对比总结

| 维度 | OneTrans | HyFormer |
|-----|----------|----------|
| **设计目标** | 统一处理单序列 | 专门处理多序列 |
| **核心机制** | 金字塔压缩 + 参数分组 | 查询解码 + 查询增强 |
| **序列表示** | 单条序列，压缩到ns_len个token | 多条序列独立编码，用Query提取 |
| **信息流动** | 序列token → 非序列token（单向） | Query ↔ 序列 ↔ 非序列token（多向） |
| **计算效率** | 金字塔减少计算量 | 多序列可能更重，但支持灵活配置 |
| **适用场景** | 单行为序列（如点击流） | 多行为序列（浏览+点赞+搜索） |

---

## 第二部分：运行指南

### 环境准备（用uv）

```bash
# 进入项目目录（分别对每个仓库执行）
cd /Users/xiazhiwei/Uni-Rec-Challenge/OneTrans_Pytorch
# 或
cd /Users/xiazhiwei/Uni-Rec-Challenge/Hyformer_Pytorch

# 创建uv环境（Python 3.11或3.12都可以）
uv venv --python 3.11

# 激活环境
source .venv/bin/activate

# 安装依赖（Mac CPU版本PyTorch + 其他依赖）
uv pip install torch datasets huggingface_hub pandas pyarrow numpy

# 验证安装
python -c "import torch; print(f'PyTorch {torch.__version__}, Device: {torch.device(\"cpu\")}')"
```

---

### 快速验证（先跑sanity check）

```bash
# OneTrans: 验证backbone能否正常前向传播
cd /Users/xiazhiwei/Uni-Rec-Challenge/OneTrans_Pytorch
python main_pytorch.py
# 预期输出: 打印各层tensor shape，最终 shape 为 [4, 16]

# HyFormer: 验证backbone
cd /Users/xiazhiwei/Uni-Rec-Challenge/Hyformer_Pytorch
python main_pytorch.py
# 预期输出: 打印各层tensor shape，最终 shape 为 [4, 17, 16]
```

---

### 完整训练运行

#### OneTrans 训练

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge/OneTrans_Pytorch

# 基础训练（5轮，32 batch size）
python scripts/run_taac2026_sample.py \
    --epochs 5 \
    --batch-size 32 \
    --d-model 128 \
    --ns-len 4 \
    --seq-len 16 \
    --save-checkpoint

# 不同mask模式对比
python scripts/run_taac2026_sample.py --epochs 5 --batch-size 32 --mask_type bimask_hard
python scripts/run_taac2026_sample.py --epochs 5 --batch-size 32 --mask_type hard_mask

# 小数据快速验证（只取100条）
python scripts/run_taac2026_sample.py --max-rows 100 --epochs 2 --batch-size 16
```

#### HyFormer 训练

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge/Hyformer_Pytorch

# 基础训练（默认 longer encoder）
python scripts/run_taac2026_sample.py \
    --epochs 5 \
    --batch-size 32 \
    --d-model 128 \
    --num-sequences 3 \
    --num-non-seq-tokens 13 \
    --hyformer-layers 4 \
    --save-checkpoint

# 尝试不同序列编码器
python scripts/run_taac2026_sample.py --epochs 5 --seq-encoder-type full_transformer
python scripts/run_taac2026_sample.py --epochs 5 --seq-encoder-type swiglu

# 小数据快速验证
python scripts/run_taac2026_sample.py --max-rows 100 --epochs 2 --batch-size 16
```

---

### 关键参数说明

| 参数 | OneTrans | HyFormer | 说明 |
|------|----------|----------|------|
| `--max-rows` | ✅ | ✅ | 限制加载数据条数（快速测试用）|
| `--batch-size` | 32 | 32 | Mac CPU可以降到16或8 |
| `--d-model` | 128 | 128 | 模型维度，Mac可保持默认 |
| `--epochs` | 5 | 5 | 训练轮数 |
| `--mask_type` | `origin`/`hard_mask`/`bimask_*` | - | OneTrans特有的mask模式 |
| `--seq-encoder-type` | - | `longer`/`full_transformer`/`swiglu` | HyFormer的序列编码器选择 |

---

### Mac运行的注意事项

**不需要额外配置**：代码中 `device` 默认是 `"cuda" if torch.cuda.is_available() else "cpu"`，Mac会自动用CPU。

**AMP混合精度**：Mac CPU不支持AMP（代码中 `should_enable_amp` 会检查 `device_type != "cuda"` 时返回False），所以自动以普通精度运行。

**预期运行时间**（MacBook Pro M系列，1000条数据）：
- OneTrans: 每轮约 10-30秒
- HyFormer: 每轮约 15-40秒（多序列计算稍重）

**首次运行会下载数据集**（约几秒），缓存到 `.cache/taac2026/`。

---

### 断点续训（可选）

```bash
# 保存checkpoint后，可以从中断处继续训练
python scripts/run_taac2026_sample.py \
    --epochs 10 \
    --resume best_model_20260419_xxxxxx.pt \
    --save-checkpoint
```

---

## 学习建议

**学习路径**：
1. **先理解OneTrans**：它是单序列的经典范式，掌握"token化+Transformer+压缩"的基础套路
2. **再理解HyFormer**：扩展到多序列场景，理解"查询机制"如何实现序列间的信息交互

**代码阅读顺序**：
- OneTrans: `main_pytorch.py` 中的 `main()` 函数demo
- HyFormer: `main_pytorch.py` 中的 `main()` 函数demo

**实践建议**：
- 如果数据只有**单一行为序列**（如点击历史）→ 从OneTrans入手
- 如果数据有**多种行为序列**（如浏览、点赞、收藏都有）→ 尝试HyFormer的多序列建模能力
