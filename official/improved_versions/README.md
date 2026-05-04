# PCVRHyFormer 改进版本汇总

基于官方baseline的10个改进版本，每个版本针对不同的优化方向。

## 版本列表

| 版本 | 改进点 | 预期效果 |
|------|--------|----------|
| V1 | 增加模型深度 (blocks: 2→3) | 增强模型表达能力 |
| V2 | 扩大模型宽度 (d_model: 64→128) | 增加参数容量 |
| V3 | 多头注意力增强 (heads: 4→8) | 提升注意力多样性 |
| V4 | 序列编码器升级 (swiglu→transformer) | 引入序列自注意力 |
| V5 | 时间特征增强 (buckets: 65→129) | 更精细的时间建模 |
| V6 | 正则化增强 (dropout: 0.01→0.3) | 减少过拟合 |
| V7 | 学习率优化 (lr: 1e-4→5e-5) | 更稳定的收敛 |
| V8 | Focal Loss (bce→focal, alpha=0.25) | 处理类别不平衡 |
| V9 | 查询数量增加 (queries: 2→4) | 增强查询多样性 |
| V10 | 综合改进版本 | 多个改进点组合 |

## 使用方法

每个版本目录下包含：
- `run.sh` - 训练脚本
- `config.txt` - 配置说明

直接运行对应版本的脚本即可：
```bash
cd official/improved_versions
bash V1_deeper/run.sh
```

## 基线参考

官方baseline配置：
- d_model: 64
- emb_dim: 64
- num_queries: 2
- num_hyformer_blocks: 2
- num_heads: 4
- seq_encoder_type: swiglu
- dropout_rate: 0.01
- lr: 1e-4
- loss_type: bce
- num_time_buckets: 65
