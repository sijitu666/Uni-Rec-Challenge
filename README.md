# Uni-Rec-Challenge

TAAC2026 CTR (Click-Through Rate) prediction competition research workspace.

## Clone Repository

This repository contains git submodules. To clone with all submodules:

```bash
git clone --recursive https://github.com/sijitu666/Uni-Rec-Challenge.git
```

Or if you already cloned without `--recursive`:

```bash
git submodule update --init --recursive
```

## Submodules

| Submodule | Description | URL |
|-----------|-------------|-----|
| Hyformer_Pytorch | PyTorch reimplementation of HyFormer architecture | https://github.com/sijitu666/Hyformer_Pytorch.git |
| OneTrans_Pytorch | PyTorch port of OneTrans model | https://github.com/sijitu666/OneTrans_Pytorch.git |
| system_prompt_analysis/cchistory | Claude Code history analysis tool | https://github.com/badlogic/cchistory.git |
| system_prompt_analysis/claude-code-system-prompts | Claude Code system prompts collection | https://github.com/Piebald-AI/claude-code-system-prompts.git |
| system_prompt_analysis/system-prompts-and-models-of-ai-tools | AI tools prompts and models | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools.git |

### Submodule Commands

```bash
# Update all submodules to latest
git submodule update --remote

# Update specific submodule
git submodule update --remote Hyformer_Pytorch

# Commit submodule changes in main repo
git add Hyformer_Pytorch OneTrans_Pytorch
git commit -m "Update submodules"
```

## Git Worktree

This repository uses **git worktree** for parallel branch development:

```bash
# List worktrees
git worktree list

# Add worktree for a branch
git worktree add ../Uni-Rec-Challenge-feature feature-branch

# Remove worktree
git worktree remove ../Uni-Rec-Challenge-feature
```

### Current Worktrees

| Path | Branch | Purpose |
|------|--------|---------|
| `/Users/xiazhiwei/Uni-Rec-Challenge` | main | Main development |
| `/Users/xiazhiwei/Uni-Rec-Challenge-hy3` | hy3-preview-opt | Optimization preview |

Open separate VS Code windows for parallel development with independent Claude Code sessions.

## Branches

- **main** - Main development branch
- **hy3-preview-opt** - Optimization preview branch (contains `official/improved_versions/`)

## Project Structure

```
Uni-Rec-Challenge/
├── official/              # Official competition code
├── Hyformer_Pytorch/      # HyFormer implementation (submodule)
├── OneTrans_Pytorch/      # OneTrans implementation (submodule)
├── system_prompt_analysis/ # Analysis tools and prompts (submodules)
├── docs/                  # Documentation
├── CLAUDE.md             # Guidance for Claude Code
└── AGENTS.md             # Guidance for Codex
```

## Quick Start

See [CLAUDE.md](CLAUDE.md) or [AGENTS.md](AGENTS.md) for detailed development commands and architecture notes.
