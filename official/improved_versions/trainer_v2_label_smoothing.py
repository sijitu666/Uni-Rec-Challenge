"""
V2: Label Smoothing Trainer - 减少过拟合
小红书多篇提到"还好没有过拟合"，说明过拟合是普遍问题

改进点：
1. Label Smoothing（硬标签0/1 → 平滑为0.05/0.95）
2. 可配置 smoothing 参数
3. 与 Focal Loss 兼容

使用方法：
  将本文件保存为 trainer_v2_label_smoothing.py，替换官方 trainer.py
"""

import os
import glob
import shutil
import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm
from sklearn.metrics import roc_auc_score

from utils import sigmoid_focal_loss, EarlyStopping
from model import ModelInput


class PCVRHyFormerRankingTrainerV2:
    """
    V2: Trainer with Label Smoothing + Gradient Clipping + LR Scheduler.

    Improvements over official trainer:
    1. Label Smoothing (reduces overfitting)
    2. Gradient Clipping (training stability, max_norm=5.0)
    3. LR Scheduler with Warmup (better convergence)
    """

    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        valid_loader: DataLoader,
        lr: float,
        num_epochs: int,
        device: str,
        save_dir: str,
        early_stopping: EarlyStopping,
        loss_type: str = 'bce',
        focal_alpha: float = 0.1,
        focal_gamma: float = 2.0,
        sparse_lr: float = 0.05,
        sparse_weight_decay: float = 0.0,
        reinit_sparse_after_epoch: int = 1,
        reinit_cardinality_threshold: int = 0,
        ckpt_params: Optional[Dict[str, Any]] = None,
        writer: Optional[Any] = None,
        schema_path: Optional[str] = None,
        ns_groups_path: Optional[str] = None,
        eval_every_n_steps: int = 0,
        train_config: Optional[Dict[str, Any]] = None,
        # V2 new parameters
        label_smoothing: float = 0.1,
        gradient_clip_norm: float = 5.0,
        use_lr_scheduler: bool = True,
        warmup_epochs: int = 1,
        min_lr_ratio: float = 0.1,
    ) -> None:
        self.model: nn.Module = model
        self.train_loader: DataLoader = train_loader
        self.valid_loader: DataLoader = valid_loader
        self.writer = writer
        self.schema_path: Optional[str] = schema_path
        self.ns_groups_path: Optional[str] = ns_groups_path

        # Dual optimizer: Adagrad for sparse Embeddings, AdamW for dense params.
        self.sparse_optimizer: Optional[torch.optim.Optimizer]
        if hasattr(model, 'get_sparse_params'):
            sparse_params = model.get_sparse_params()
            dense_params = model.get_dense_params()
            sparse_param_count = sum(p.numel() for p in sparse_params)
            dense_param_count = sum(p.numel() for p in dense_params)
            logging.info(f"Sparse params: {len(sparse_params)} tensors, {sparse_param_count:,} parameters (Adagrad lr={sparse_lr})")
            logging.info(f"Dense params: {len(dense_params)} tensors, {dense_param_count:,} parameters (AdamW lr={lr})")
            self.sparse_optimizer = torch.optim.Adagrad(
                sparse_params, lr=sparse_lr, weight_decay=sparse_weight_decay
            )
            self.dense_optimizer: torch.optim.Optimizer = torch.optim.AdamW(
                dense_params, lr=lr, betas=(0.9, 0.98)
            )
        else:
            self.sparse_optimizer = None
            self.dense_optimizer = torch.optim.AdamW(
                model.parameters(), lr=lr, betas=(0.9, 0.98)
            )

        self.num_epochs: int = num_epochs
        self.device: str = device
        self.save_dir: str = save_dir
        self.early_stopping: EarlyStopping = early_stopping
        self.loss_type: str = loss_type
        self.focal_alpha: float = focal_alpha
        self.focal_gamma: float = focal_gamma
        self.reinit_sparse_after_epoch: int = reinit_sparse_after_epoch
        self.reinit_cardinality_threshold: int = reinit_cardinality_threshold
        self.sparse_lr: float = sparse_lr
        self.sparse_weight_decay: float = sparse_weight_decay
        self.ckpt_params: Dict[str, Any] = ckpt_params or {}
        self.eval_every_n_steps: int = eval_every_n_steps
        self.train_config: Optional[Dict[str, Any]] = train_config

        # V2: Label Smoothing
        self.label_smoothing: float = label_smoothing

        # V2: Gradient Clipping
        self.gradient_clip_norm: float = gradient_clip_norm

        # V2: LR Scheduler with Warmup
        self.use_lr_scheduler: bool = use_lr_scheduler
        self.warmup_epochs: int = warmup_epochs
        self.min_lr_ratio: float = min_lr_ratio
        self.lr_schedulers: Dict[str, Any] = {}

        if use_lr_scheduler and self.dense_optimizer is not None:
            # Cosine Annealing with warmup
            self.lr_schedulers['dense'] = torch.optim.lr_scheduler.CosineAnnealingLR(
                self.dense_optimizer, T_max=num_epochs - warmup_epochs, eta_min=lr * min_lr_ratio
            )
            logging.info(f"LR Scheduler: CosineAnnealingLR, T_max={num_epochs - warmup_epochs}, min_lr={lr * min_lr_ratio}")

        logging.info(f"PCVRHyFormerRankingTrainerV2: label_smoothing={label_smoothing}, "
                     f"gradient_clip_norm={gradient_clip_norm}, use_lr_scheduler={use_lr_scheduler}")

    def _build_step_dir_name(self, global_step: int, is_best: bool = False) -> str:
        parts = [f"global_step{global_step}"]
        for key in ("layer", "head", "hidden"):
            if key in self.ckpt_params:
                parts.append(f"{key}={self.ckpt_params[key]}")
        name = ".".join(parts)
        if is_best:
            name += ".best_model"
        return name

    def _write_sidecar_files(self, ckpt_dir: str) -> None:
        os.makedirs(ckpt_dir, exist_ok=True)
        if self.schema_path and os.path.exists(self.schema_path):
            shutil.copy2(self.schema_path, ckpt_dir)

        ns_groups_copied = False
        if self.ns_groups_path and os.path.exists(self.ns_groups_path):
            shutil.copy2(self.ns_groups_path, ckpt_dir)
            ns_groups_copied = True

        if self.train_config:
            import json
            cfg_to_dump = dict(self.train_config)
            if ns_groups_copied:
                cfg_to_dump['ns_groups_json'] = os.path.basename(self.ns_groups_path)
            with open(os.path.join(ckpt_dir, 'train_config.json'), 'w') as f:
                json.dump(cfg_to_dump, f, indent=2)

    def _save_step_checkpoint(
        self,
        global_step: int,
        is_best: bool = False,
        skip_model_file: bool = False,
    ) -> str:
        dir_name = self._build_step_dir_name(global_step, is_best=is_best)
        ckpt_dir = os.path.join(self.save_dir, dir_name)
        os.makedirs(ckpt_dir, exist_ok=True)
        if not skip_model_file:
            torch.save(self.model.state_dict(), os.path.join(ckpt_dir, "model.pt"))
        self._write_sidecar_files(ckpt_dir)
        logging.info(f"Saved checkpoint to {ckpt_dir}/model.pt")
        return ckpt_dir

    def _remove_old_best_dirs(self) -> None:
        pattern = os.path.join(self.save_dir, "global_step*.best_model")
        for old_dir in glob.glob(pattern):
            shutil.rmtree(old_dir)
            logging.info(f"Removed old best_model dir: {old_dir}")

    def _batch_to_device(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        device_batch: Dict[str, Any] = {}
        for k, v in batch.items():
            if isinstance(v, torch.Tensor):
                device_batch[k] = v.to(self.device, non_blocking=True)
            else:
                device_batch[k] = v
        return device_batch

    def _handle_validation_result(
        self,
        total_step: int,
        val_auc: float,
        val_logloss: float,
    ) -> None:
        old_best = self.early_stopping.best_score
        is_likely_new_best = (
            old_best is None
            or val_auc > old_best + self.early_stopping.delta
        )
        if not is_likely_new_best:
            self.early_stopping(val_auc, self.model, {
                "best_val_AUC": val_auc,
                "best_val_logloss": val_logloss,
            })
            return

        best_dir = os.path.join(
            self.save_dir,
            self._build_step_dir_name(total_step, is_best=True),
        )
        self.early_stopping.checkpoint_path = os.path.join(best_dir, "model.pt")
        self._remove_old_best_dirs()

        self.early_stopping(val_auc, self.model, {
            "best_val_AUC": val_auc,
            "best_val_logloss": val_logloss,
        })

        if self.early_stopping.best_score != old_best and os.path.exists(
            self.early_stopping.checkpoint_path
        ):
            self._save_step_checkpoint(
                total_step, is_best=True, skip_model_file=True)

    def _make_model_input(self, device_batch: Dict[str, Any]) -> ModelInput:
        seq_domains = device_batch['_seq_domains']
        seq_data: Dict[str, torch.Tensor] = {}
        seq_lens: Dict[str, torch.Tensor] = {}
        seq_time_buckets: Dict[str, torch.Tensor] = {}
        for domain in seq_domains:
            seq_data[domain] = device_batch[domain]
            seq_lens[domain] = device_batch[f'{domain}_len']
            B = device_batch[domain].shape[0]
            L = device_batch[domain].shape[2]
            seq_time_buckets[domain] = device_batch.get(
                f'{domain}_time_bucket',
                torch.zeros(B, L, dtype=torch.long, device=self.device))
        return ModelInput(
            user_int_feats=device_batch['user_int_feats'],
            item_int_feats=device_batch['item_int_feats'],
            user_dense_feats=device_batch['user_dense_feats'],
            item_dense_feats=device_batch['item_dense_feats'],
            seq_data=seq_data,
            seq_lens=seq_lens,
            seq_time_buckets=seq_time_buckets,
        )

    def _smooth_labels(self, labels: torch.Tensor) -> torch.Tensor:
        """Apply label smoothing: 0 -> smoothing/2, 1 -> 1 - smoothing/2"""
        if self.label_smoothing <= 0:
            return labels
        return labels * (1 - self.label_smoothing) + 0.5 * self.label_smoothing

    def _train_step(self, batch: Dict[str, Any]) -> float:
        device_batch = self._batch_to_device(batch)
        label = device_batch['label'].float()

        self.dense_optimizer.zero_grad()
        if self.sparse_optimizer is not None:
            self.sparse_optimizer.zero_grad()

        model_input = self._make_model_input(device_batch)
        logits = self.model(model_input)
        logits = logits.squeeze(-1)

        # V2: Apply label smoothing if enabled
        if self.label_smoothing > 0 and self.loss_type != 'focal':
            smoothed_labels = self._smooth_labels(label)
            loss = F.binary_cross_entropy_with_logits(logits, smoothed_labels)
        elif self.loss_type == 'focal':
            # Focal loss with label smoothing
            if self.label_smoothing > 0:
                smoothed_labels = self._smooth_labels(label)
                bce_loss = F.binary_cross_entropy_with_logits(logits, smoothed_labels, reduction='none')
            else:
                bce_loss = F.binary_cross_entropy_with_logits(logits, label, reduction='none')

            probs = torch.sigmoid(logits)
            if self.label_smoothing > 0:
                probs_t = probs * smoothed_labels + (1 - probs) * (1 - smoothed_labels)
            else:
                probs_t = probs * label + (1 - probs) * (1 - label)

            focal_weight = torch.pow(1 - probs_t, self.focal_gamma)
            if self.focal_alpha >= 0:
                alpha_t = self.focal_alpha * (smoothed_labels if self.label_smoothing > 0 else label) + \
                         (1 - self.focal_alpha) * (1 - (smoothed_labels if self.label_smoothing > 0 else label))
                focal_weight = alpha_t * focal_weight
            loss = focal_weight * bce_loss
            loss = loss.mean()
        else:
            loss = F.binary_cross_entropy_with_logits(logits, label)

        loss.backward()

        # V2: Gradient Clipping
        if self.gradient_clip_norm > 0:
            nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=self.gradient_clip_norm, foreach=False)

        self.dense_optimizer.step()
        if self.sparse_optimizer is not None:
            self.sparse_optimizer.step()

        return loss.item()

    def train(self) -> None:
        print("Start training (PCVRHyFormer V2 - Label Smoothing + Gradient Clip + LR Scheduler)")
        self.model.train()
        total_step = 0

        for epoch in range(1, self.num_epochs + 1):
            train_pbar = tqdm(enumerate(self.train_loader), total=len(self.train_loader),
                                  dynamic_ncols=True)
            loss_sum = 0.0

            for step, batch in train_pbar:
                loss = self._train_step(batch)
                total_step += 1
                loss_sum += loss

                if self.writer:
                    self.writer.add_scalar('Loss/train', loss, total_step)

                train_pbar.set_postfix({"loss": f"{loss:.4f}"})

                if self.eval_every_n_steps > 0 and total_step % self.eval_every_n_steps == 0:
                    logging.info(f"Evaluating at step {total_step}")
                    val_auc, val_logloss = self.evaluate(epoch=epoch)
                    self.model.train()
                    torch.cuda.empty_cache()
                    logging.info(f"Step {total_step} Validation | AUC: {val_auc}, LogLoss: {val_logloss}")
                    if self.writer:
                        self.writer.add_scalar('AUC/valid', val_auc, total_step)
                        self.writer.add_scalar('LogLoss/valid', val_logloss, total_step)
                    self._handle_validation_result(total_step, val_auc, val_logloss)
                    if self.early_stopping.early_stop:
                        logging.info(f"Early stopping at step {total_step}")
                        return

            logging.info(f"Epoch {epoch}, Average Loss: {loss_sum / len(self.train_loader)}")

            # V2: LR Scheduler step (after warmup)
            if self.use_lr_scheduler and epoch >= self.warmup_epochs:
                if 'dense' in self.lr_schedulers:
                    old_lr = self.dense_optimizer.param_groups[0]['lr']
                    self.lr_schedulers['dense'].step()
                    new_lr = self.dense_optimizer.param_groups[0]['lr']
                    logging.info(f"LR Scheduler: {old_lr:.6f} -> {new_lr:.6f}")

            val_auc, val_logloss = self.evaluate(epoch=epoch)
            self.model.train()
            torch.cuda.empty_cache()
            logging.info(f"Epoch {epoch} Validation | AUC: {val_auc}, LogLoss: {val_logloss}")

            if self.writer:
                self.writer.add_scalar('AUC/valid', val_auc, total_step)
                self.writer.add_scalar('LogLoss/valid', val_logloss, total_step)

            self._handle_validation_result(total_step, val_auc, val_logloss)

            if self.early_stopping.early_stop:
                logging.info(f"Early stopping at epoch {epoch}")
                break

            # High cardinality re-init
            if epoch >= self.reinit_sparse_after_epoch and self.sparse_optimizer is not None:
                old_state: Dict[int, Any] = {}
                for group in self.sparse_optimizer.param_groups:
                    for p in group['params']:
                        if p.data_ptr() in self.sparse_optimizer.state:
                            old_state[p.data_ptr()] = self.sparse_optimizer.state[p]

                reinit_ptrs = self.model.reinit_high_cardinality_params(self.reinit_cardinality_threshold)
                self.sparse_optimizer = torch.optim.Adagrad(
                    self.model.get_sparse_params(), lr=self.sparse_lr, weight_decay=self.sparse_weight_decay
                )
                restored = 0
                for p in self.model.get_sparse_params():
                    if p.data_ptr() not in reinit_ptrs and p.data_ptr() in old_state:
                        self.sparse_optimizer.state[p] = old_state[p.data_ptr()]
                        restored += 1
                logging.info(f"Rebuilt Adagrad optimizer after epoch {epoch}, restored optimizer state for {restored} low-cardinality params")

    def evaluate(self, epoch: Optional[int] = None) -> Tuple[float, float]:
        print("Start Evaluation (PCVRHyFormer V2) - validation")
        self.model.eval()
        if not epoch:
            epoch = -1

        pbar = tqdm(enumerate(self.valid_loader), total=len(self.valid_loader))

        all_logits_list = []
        all_labels_list = []

        with torch.no_grad():
            for step, batch in pbar:
                logits, labels = self._evaluate_step(batch)
                all_logits_list.append(logits.detach().cpu())
                all_labels_list.append(labels.detach().cpu())

        all_logits = torch.cat(all_logits_list, dim=0)
        all_labels = torch.cat(all_labels_list, dim=0).long()

        probs = torch.sigmoid(all_logits).numpy()
        labels_np = all_labels.numpy()

        nan_mask = np.isnan(probs)
        if nan_mask.any():
            n_nan = int(nan_mask.sum())
            logging.warning(f"[Evaluate] {n_nan}/{len(probs)} predictions are NaN, filtering them out")
            valid_mask = ~nan_mask
            probs = probs[valid_mask]
            labels_np = labels_np[valid_mask]

        if len(probs) == 0 or len(np.unique(labels_np)) < 2:
            auc = 0.0
        else:
            auc = float(roc_auc_score(labels_np, probs))

        valid_logits = all_logits[~torch.isnan(all_logits)]
        valid_labels = all_labels[~torch.isnan(all_logits)]
        if len(valid_logits) > 0:
            logloss = F.binary_cross_entropy_with_logits(valid_logits, valid_labels.float()).item()
        else:
            logloss = float('inf')

        return auc, logloss

    def _evaluate_step(
        self, batch: Dict[str, Any]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        device_batch = self._batch_to_device(batch)
        label = device_batch['label']
        model_input = self._make_model_input(device_batch)
        logits, _ = self.model.predict(model_input)
        logits = logits.squeeze(-1)
        return logits, label
