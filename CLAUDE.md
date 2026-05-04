# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research workspace for the TAAC2026 CTR (Click-Through Rate) prediction competition. It contains two parallel PyTorch reimplementations of recent industrial recommender architectures:

- **OneTrans_Pytorch** — PyTorch port of a TensorFlow OneTrans demo (pyramid-style token compression)
- **Hyformer_Pytorch** — PyTorch reimplementation of the HyFormer paper (multi-sequence query decoding)

Both projects target the same dataset (`TAAC2026/data_sample_1000`) and share identical project structure and utilities.

## Repository Structure

This repository uses **git submodules** to manage dependent projects:

```
Uni-Rec-Challenge/
├── official/                          # Official competition code
├── Hyformer_Pytorch/                  # Submodule - HyFormer implementation
│   └── https://github.com/sijitu666/Hyformer_Pytorch.git
├── OneTrans_Pytorch/                  # Submodule - OneTrans implementation
│   └── https://github.com/sijitu666/OneTrans_Pytorch.git
├── system_prompt_analysis/
│   ├── cchistory/                     # Submodule
│   ├── claude-code-system-prompts/    # Submodule
│   └── system-prompts-and-models-of-ai-tools/  # Submodule
└── docs/                              # Documentation
```

### Branches

- **main** - Main development branch (excludes improved_versions)
- **hy3-preview-opt** - Contains `official/improved_versions/` optimization code

## Clone and Setup

### Clone with all submodules

```bash
git clone --recursive https://github.com/sijitu666/Uni-Rec-Challenge.git
```

### If already cloned without submodules

```bash
git submodule update --init --recursive
```

### Update submodules to latest

```bash
git submodule update --remote
```

## Git Worktree Setup

This repository uses **git worktree** to manage multiple branches simultaneously in separate directories. This allows you to work on different branches in parallel with independent Claude Code sessions.

### Current Worktree Layout

```
/Users/xiazhiwei/
├── Uni-Rec-Challenge/              # main branch
└── Uni-Rec-Challenge-hy3/          # hy3-preview-opt branch
```

### Common Worktree Commands

```bash
# List all worktrees
git worktree list

# Add a new worktree for a branch
git worktree add <path> <branch-name>

# Remove a worktree
git worktree remove <path>

# Clean up stale worktrees
git worktree prune
```

### Using with Claude Code

Open separate VS Code windows for each worktree:

```bash
# Window 1 - main branch development
code /Users/xiazhiwei/Uni-Rec-Challenge

# Window 2 - hy3 preview optimization development
code /Users/xiazhiwei/Uni-Rec-Challenge-hy3
```

Each window runs an independent Claude Code session, allowing you to:
- Work on `main` branch features in one window
- Work on `hy3-preview-opt` optimizations in another
- Switch between contexts without stashing or committing

### Worktree Benefits

- **Parallel Development**: Work on multiple branches simultaneously
- **Context Isolation**: Each worktree has its own working directory
- **Shared History**: All worktrees share the same `.git` directory
- **No Stashing**: Switch branches without committing or stashing changes

## Common Commands

### Backbone sanity check (shape demo, no data needed)
```bash
cd OneTrans_Pytorch && python main_pytorch.py
cd Hyformer_Pytorch && python main_pytorch.py
```

### Training
```bash
# OneTrans
cd OneTrans_Pytorch
python scripts/run_taac2026_sample.py --epochs 5 --batch-size 32 --save-checkpoint
python scripts/run_taac2026_sample.py --epochs 5 --batch-size 32 --mask_type bimask_hard

# HyFormer
cd Hyformer_Pytorch
python scripts/run_taac2026_sample.py --epochs 5 --batch-size 32
python scripts/run_taac2026_sample.py --epochs 5 --batch-size 32 --seq-encoder-type longer
python scripts/run_taac2026_sample.py --epochs 5 --batch-size 32 --seq-encoder-type full_transformer
python scripts/run_taac2026_sample.py --epochs 5 --batch-size 32 --seq-encoder-type swiglu
```

### Resume training
```bash
python scripts/run_taac2026_sample.py --epochs 10 --batch-size 32 --resume best_model_YYYYMMDD_HHMMSS.pt --save-checkpoint
```

### Small-model run (reduces overfitting on sample data)
```bash
# OneTrans
python scripts/run_taac2026_sample.py --epochs 20 --batch-size 16 --d-model 64 --ns-len 2 --lr 5e-4 --weight-decay 1e-3

# HyFormer
python scripts/run_taac2026_sample.py --epochs 10 --d-model 64 --seq-encoder-type swiglu --hyformer-layers 2
```

## Architecture

Both projects share the same three-layer structure:

| Layer | File | Role |
|---|---|---|
| Backbone | `main_pytorch.py` | Core architectural blocks (closest to paper/original) |
| Task wrapper | `models/taac_*.py` | Wraps backbone into binary classifier with tokenizers |
| Training script | `scripts/run_taac2026_sample.py` | Data loading, AMP, training loop, checkpointing |

Shared utilities (`utils/`) are identical across both projects:
- `utils/taac_data.py` — dataset loading, schema detection, feature tensorization
- `utils/metrics.py` — AUC and accuracy
- `utils/common.py` — seed, split generation

### OneTrans key ideas
- Non-sequential features → `ns_len` pseudo tokens; sequential features → `seq_len` tokens
- Token order: `[ns_tokens, seq_tokens]`
- First `ns_len` tokens use per-token parameter groups; sequence tokens share one group
- Pyramid compression: query length shrinks step-by-step until only `ns_tokens` remain
- Mask modes: `origin`, `hard_mask`, `bimask_soft`, `bimask_hard`

### HyFormer key ideas
- Sequential features are grouped into `num_sequences` branches (auto-grouped from schema)
- Per-sequence query tokens are generated from global information (non-seq + mean-pooled sequences)
- Each HyFormer layer alternates: **Query Decoding** (queries cross-attend to sequences) → **Query Boosting** (decoded queries + non-seq tokens mixed via MLP-Mixer-style block)
- Sequence encoding modes: `longer` (short-query cross-attention), `full_transformer` (self-attention), `swiglu` (attention-free FFN)

## Data & Training Notes

- Dataset: `TAAC2026/data_sample_1000` (1000 samples, 800 train / 200 val) — for code verification only; real competition uses millions of samples
- Input: `non_seq=(N, 183)`, `seq=(N, 16, 45)` for OneTrans; `seq=(N, 3, 16, 15)` for HyFormer (3 auto-grouped sequences)
- Labels are class-imbalanced (~85% negative), so accuracy is misleading — use AUC as the primary metric
- Baseline results: OneTrans best val AUC ~0.51, HyFormer ~0.53 (both near random on sample data, expected)
- Checkpoints saved to `outputs/taac2026_sample/` with timestamped filenames
- AMP is auto-enabled on CUDA; disabled on CPU (Mac)
