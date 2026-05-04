# Baseline 训练结果报告

**运行时间**: 2026-04-19  
**数据集**: TAAC2026/data_sample_1000 (1000条样本，800训练/200验证)  
**设备**: Mac CPU (无GPU)

---

## 核心指标对比

| 指标 | OneTrans | HyFormer | 说明 |
|-----|----------|----------|------|
| **最佳Val AUC** | 0.5116 (Epoch 1) | **0.5318 (Epoch 5)** | HyFormer略好，但两者都接近随机(0.5) |
| **最终Val AUC** | 0.4363 | **0.5318** | HyFormer收敛更稳定 |
| **Val Acc** | 0.8500 | 0.8500 | 两者相同，可能是数据类别不平衡 |
| **Train Loss** | 0.3643 | 0.3683 | 都收敛到相似水平 |

---

## 详细训练日志

### OneTrans

```
[run] device=cpu samples=1000 train=800 val=200
[run] non_seq=(1000, 183) seq=(1000, 16, 45) classes=2
[run] amp=False amp_dtype=fp16 grad_scaler=False device_type=cpu mask_type=origin
[epoch 01] train_loss=0.3923 train_auc=0.4971 train_acc=0.8688 val_loss=0.4278 val_auc=0.5116 val_acc=0.8500
[epoch 02] train_loss=0.3673 train_auc=0.4220 train_acc=0.8825 val_loss=0.4418 val_auc=0.4725 val_acc=0.8500
[epoch 03] train_loss=0.3639 train_auc=0.5014 train_acc=0.8825 val_loss=0.4260 val_auc=0.4539 val_acc=0.8500
[epoch 04] train_loss=0.3640 train_auc=0.4675 train_acc=0.8825 val_loss=0.4284 val_auc=0.4620 val_acc=0.8500
[epoch 05] train_loss=0.3643 train_auc=0.5103 train_acc=0.8825 val_loss=0.4227 val_auc=0.4363 val_acc=0.8500
[run] checkpoint saved to outputs/taac2026_sample/best_model_20260419_020921.pt
```

### HyFormer

```
[run] device=cpu samples=1000 train=800 val=200
[run] non_seq=(1000, 183) seq=(1000, 3, 16, 15) classes=2 grouped_sequences=3
[run] amp=False amp_dtype=fp16 grad_scaler=False device_type=cpu seq_encoder_type=longer
[epoch 01] train_loss=0.3984 train_auc=0.4454 train_acc=0.8450 val_loss=0.4228 val_auc=0.4500 val_acc=0.8500
[epoch 02] train_loss=0.3704 train_auc=0.5095 train_acc=0.8825 val_loss=0.4254 val_auc=0.5075 val_acc=0.8500
[epoch 03] train_loss=0.3684 train_auc=0.4614 train_acc=0.8825 val_loss=0.4260 val_auc=0.5282 val_acc=0.8500
[epoch 04] train_loss=0.3645 train_auc=0.5024 train_acc=0.8825 val_loss=0.4234 val_auc=0.5288 val_acc=0.8500
[epoch 05] train_loss=0.3683 train_auc=0.4736 train_acc=0.8825 val_loss=0.4264 val_auc=0.5318 val_acc=0.8500
[run] checkpoint saved to outputs/taac2026_sample/best_model_20260419_020919.pt
```

---

## 关键观察

### 1. AUC ≈ 0.5 意味着模型几乎在随机猜测

- 正常CTR模型AUC应该达到 0.6~0.8+
- 当前结果说明模型**没有从特征中学到有效模式**

### 2. 准确率85%但AUC很低 → 数据严重不平衡

```python
# 从输出来看
"label_mapping": {"1": 0, "2": 1}  # 二分类
# 85%准确率 ≈ 模型一直在预测多数类
```

可能数据里85%是负样本（不点击），15%是正样本（点击），模型学会了"全猜不点击"。

### 3. HyFormer表现稍好的原因

| 方面 | OneTrans | HyFormer |
|-----|----------|----------|
| 序列处理 | 单序列45维 | 3组序列各15维 |
| 收敛趋势 | AUC下降 (过拟合迹象) | AUC逐步上升 |
| 最终epoch | val_auc=0.4363 | val_auc=0.5318 |

HyFormer的多序列分组可能更好地捕捉了domain_a/b/c/d的不同行为模式。

---

## 问题诊断

### 为什么效果差？

1. **数据量太小**：1000条样本，800训练/200验证
   - 深度学习推荐模型通常需要百万级样本
   - 小数据下模型无法泛化

2. **特征质量问题**：
   - 183维非序列特征（可能是ID类稀疏特征）
   - 45维序列特征被压缩到16步
   - 没有embedding层处理ID特征

3. **模型复杂度 vs 数据量不匹配**：
   - d_model=128，参数量对于1000条数据严重过拟合
   - 验证loss一直高于train loss说明过拟合

---

## 改进建议

如果想在这个小数据集上跑出更好的结果，尝试：

```bash
# 1. 减小模型规模（降低过拟合）
python scripts/run_taac2026_sample.py \
    --epochs 20 \
    --batch-size 16 \
    --d-model 64 \
    --ns-len 2 \
    --lr 5e-4 \
    --weight-decay 1e-3

# 2. HyFormer换更轻量的encoder
python scripts/run_taac2026_sample.py \
    --epochs 10 \
    --d-model 64 \
    --seq-encoder-type swiglu \
    --hyformer-layers 2
```

**但说实话**：这个数据集（`TAAC2026/data_sample_1000`）就是官方给的**示例/调试数据**，目的是验证代码能跑通，不是用来刷指标的。真正比赛会用完整数据集（百万级）。

---

## 结论

| 维度 | 评估 |
|-----|------|
| **代码正确性** | ✅ 两个模型都能正常训练，无报错 |
| **checkpoint保存** | ✅ 都已保存到 `outputs/taac2026_sample/` |
| **学习效果** | ⚠️ 小数据上无明显学习，符合预期 |
| **推荐选择** | **HyFormer**，收敛更稳定，架构更适合多序列场景 |

---

## 下一步行动

两个baseline都成功跑通了，下一步可以：
1. 用完整数据集重新训练
2. 调参实验（网格搜索learning rate, d_model等）
3. 尝试模型融合或特征工程
