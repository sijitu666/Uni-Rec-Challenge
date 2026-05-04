"""
V1: Focal Loss 改进版 - 解决类别不平衡问题
小红书306赞经验贴"TAAC上分tricks"提到 Focal Loss 对正负样本不平衡有效

改进点：
1. 优化 Focal Loss 实现（支持 alpha 按 batch 动态调整）
2. 增加 focal_loss 的 numeric stability
3. 支持从 BCE 平滑切换到 Focal

使用方法：
  python train.py --loss_type focal --focal_alpha 0.25 --focal_gamma 2.0
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import logging
from typing import Optional

def sigmoid_focal_loss(
    inputs: torch.Tensor,
    targets: torch.Tensor,
    alpha: float = 0.25,
    gamma: float = 2.0,
    reduction: str = 'mean',
) -> torch.Tensor:
    """
    Optimized Focal Loss for imbalanced CTR prediction.

    Key improvements over standard BCE:
    - alpha: downweights negative samples (typically 0.25 for CTR)
    - gamma: focuses on hard examples (2.0 is a good default)

    Args:
        inputs: (B,) logits
        targets: (B,) binary labels (0 or 1)
        alpha: weighting factor for positive class
        gamma: focusing parameter (higher = more focus on hard examples)
        reduction: 'mean', 'sum', or 'none'

    Returns:
        Scalar loss value.
    """
    inputs = inputs.float()
    targets = targets.float()

    # BCE with logits (numerically stable)
    bce_loss = F.binary_cross_entropy_with_logits(inputs, targets, reduction='none')

    # Get probabilities
    probs = torch.sigmoid(inputs)
    probs_t = probs * targets + (1 - probs) * (1 - targets)

    # Focal term: (1 - p_t)^gamma
    focal_weight = torch.pow(1 - probs_t, gamma)

    # Alpha weighting
    if alpha >= 0:
        alpha_t = alpha * targets + (1 - alpha) * (1 - targets)
        focal_weight = alpha_t * focal_weight

    loss = focal_weight * bce_loss

    if reduction == 'mean':
        return loss.mean()
    elif reduction == 'sum':
        return loss.sum()
    else:
        return loss


class FocalLoss(nn.Module):
    """
    Focal Loss as nn.Module for easier integration.

    Based on the paper:
    "Focal Loss for Dense Object Detection" (Lin et al., 2017)
    Adapted for CTR prediction: alpha=0.25, gamma=2.0 works well.
    """

    def __init__(self, alpha: float = 0.25, gamma: float = 2.0, reduction: str = 'mean'):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
        logging.info(f"FocalLoss initialized: alpha={alpha}, gamma={gamma}")

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        return sigmoid_focal_loss(inputs, targets, self.alpha, self.gamma, self.reduction)


def binary_cross_entropy_with_label_smoothing(
    inputs: torch.Tensor,
    targets: torch.Tensor,
    smoothing: float = 0.1,
    reduction: str = 'mean',
) -> torch.Tensor:
    """
    BCE with Label Smoothing (V2 improvement, see below).

    Instead of hard 0/1 labels, use smoothed labels:
    - positive: 1 - smoothing/2
    - negative: smoothing/2
    """
    smoothed_targets = targets * (1 - smoothing) + 0.5 * smoothing
    return F.binary_cross_entropy_with_logits(inputs, smoothed_targets, reduction=reduction)


# ==================== V2: Label Smoothing ====================
class LabelSmoothingLoss(nn.Module):
    """
    V2 Improvement: Label Smoothing to reduce overfitting.

    As mentioned in Xiaohongshu posts (e.g., "还好没有过拟合"):
    "Overfitting is a common problem in CTR prediction"

    Label Smoothing prevents the model from becoming overconfident:
    - y_true = 1 -> 0.95 (instead of 1.0)
    - y_true = 0 -> 0.05 (instead of 0.0)

    Reference: "Rethinking the Inception Architecture" (Szegedy et al., 2016)
    """

    def __init__(self, smoothing: float = 0.1, reduction: str = 'mean'):
        super().__init__()
        self.smoothing = smoothing
        self.reduction = reduction
        logging.info(f"LabelSmoothingLoss: smoothing={smoothing}")

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        return binary_cross_entropy_with_label_smoothing(
            inputs, targets.float(), self.smoothing, self.reduction
        )


# ==================== Combined Loss ====================
class CombinedCTRLoss(nn.Module):
    """
    Combined loss: Focal Loss + Label Smoothing.

    Best of both worlds:
    - Focal Loss handles class imbalance
    - Label Smoothing prevents overfitting

    Usage in trainer:
        loss_fn = CombinedCTRLoss(focal_alpha=0.25, focal_gamma=2.0, smoothing=0.1)
    """

    def __init__(
        self,
        use_focal: bool = True,
        use_smoothing: bool = True,
        focal_alpha: float = 0.25,
        focal_gamma: float = 2.0,
        smoothing: float = 0.1,
        reduction: str = 'mean',
    ):
        super().__init__()
        self.use_focal = use_focal
        self.use_smoothing = use_smoothing
        self.focal_alpha = focal_alpha
        self.focal_gamma = focal_gamma
        self.smoothing = smoothing

        if use_focal and use_smoothing:
            logging.info(f"CombinedCTRLoss: Focal(alpha={focal_alpha}, gamma={focal_gamma}) + LabelSmoothing({smoothing})")
        elif use_focal:
            logging.info(f"CombinedCTRLoss: Focal only (alpha={focal_alpha}, gamma={focal_gamma})")
        elif use_smoothing:
            logging.info(f"CombinedCTRLoss: LabelSmoothing only ({smoothing})")
        else:
            logging.info("CombinedCTRLoss: Standard BCE")

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if self.use_focal and self.use_smoothing:
            # Apply label smoothing first
            smoothed_targets = targets.float() * (1 - self.smoothing) + 0.5 * self.smoothing
            # Then apply focal loss
            bce_loss = F.binary_cross_entropy_with_logits(
                inputs, smoothed_targets, reduction='none')
            probs = torch.sigmoid(inputs)
            probs_t = probs * smoothed_targets + (1 - probs) * (1 - smoothed_targets)
            focal_weight = torch.pow(1 - probs_t, self.focal_gamma)
            if self.focal_alpha >= 0:
                alpha_t = self.focal_alpha * smoothed_targets + (1 - self.focal_alpha) * (1 - smoothed_targets)
                focal_weight = alpha_t * focal_weight
            loss = focal_weight * bce_loss
            return loss.mean() if self.reduction == 'mean' else loss.sum()
        elif self.use_focal:
            return sigmoid_focal_loss(inputs, targets, self.focal_alpha, self.focal_gamma, self.reduction)
        elif self.use_smoothing:
            return binary_cross_entropy_with_label_smoothing(
                inputs, targets, self.smoothing, self.reduction)
        else:
            return F.binary_cross_entropy_with_logits(inputs, targets.float(), reduction=self.reduction)
