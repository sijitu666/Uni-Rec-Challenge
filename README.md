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

| Submodule | Description |
|-----------|-------------|
| Hyformer_Pytorch | PyTorch reimplementation of HyFormer architecture |
| OneTrans_Pytorch | PyTorch port of OneTrans model |
| system_prompt_analysis/cchistory | Claude Code history analysis tool |
| system_prompt_analysis/claude-code-system-prompts | Claude Code system prompts collection |
| system_prompt_analysis/system-prompts-and-models-of-ai-tools | AI tools prompts and models |

## Project Structure

- `official/` - Official competition code
- `Hyformer_Pytorch/` - HyFormer implementation (submodule)
- `OneTrans_Pytorch/` - OneTrans implementation (submodule)
- `system_prompt_analysis/` - Analysis tools and prompts (submodules)
- `docs/` - Documentation
