# Git Worktree 学习记录

**日期**: 2025-05-04  
**主题**: Git Worktree 原理与使用  
**相关技术**: Git, Submodule, Worktree

---

## 学习背景

在管理 Uni-Rec-Challenge 项目时，需要同时维护多个分支（main 和 hy3-preview-opt），并且希望能够在不同分支之间快速切换而不影响各自的工作状态。

## 核心概念

### 什么是 Git Worktree？

Git Worktree 允许在同一个仓库中同时检出多个分支到不同的目录，实现并行开发。

### Worktree vs 普通 Clone

| 特性 | 普通 Clone | Worktree |
|------|-----------|----------|
| `.git` 大小 | 每个 clone 都有完整历史 | 共享同一个 `.git` |
| 磁盘占用 | N 倍空间 | 几乎不增加 |
| 提交可见性 | 需要 push/pull 同步 | 实时共享 |
| 分支切换 | stash + checkout | 直接 cd 切换目录 |

## 实践过程

### 1. 查看现有 Worktree

```bash
$ git worktree list
/Users/xiazhiwei/Uni-Rec-Challenge      87a6988 [main]
```

### 2. 创建新的 Worktree

```bash
$ git worktree add ../Uni-Rec-Challenge-hy3 hy3-preview-opt
Preparing worktree (checking out 'hy3-preview-opt')
HEAD is now at 8c71028 Add improved_versions for hy3 preview optimization
```

### 3. 验证 Worktree 结构

```bash
$ git worktree list
/Users/xiazhiwei/Uni-Rec-Challenge      87a6988 [main]
/Users/xiazhiwei/Uni-Rec-Challenge-hy3  8c71028 [hy3-preview-opt]
```

## 核心原理发现

### Worktree 目录的 `.git` 不是目录而是文件

```bash
$ cat /Users/xiazhiwei/Uni-Rec-Challenge-hy3/.git
gitdir: /Users/xiazhiwei/Uni-Rec-Challenge/.git/worktrees/Uni-Rec-Challenge-hy3
```

这说明 worktree 的 `.git` 是一个**文本文件**，指向主仓库的 git 目录！

### 内部结构

```
主仓库: Uni-Rec-Challenge/
├── .git/                           ← 唯一的 git 对象库
│   ├── objects/                    ← 所有版本文件
│   ├── refs/heads/                 ← 分支引用
│   └── worktrees/                  ← worktree 管理目录
│       └── Uni-Rec-Challenge-hy3/  ← hy3 worktree 的状态
│           ├── HEAD                ← 当前指向的 commit
│           ├── index               ← 暂存区
│           └── gitdir              ← 指向 worktree 目录

worktree: Uni-Rec-Challenge-hy3/
├── .git (文件)                     ← 内容为 "gitdir: ..."
└── src/...                         ← 工作文件
```

## 关键结论

**Worktree = 多个工作目录 + 一个共享的 git 仓库**

- ✅ 工作目录是独立的（像两个独立的 clone）
- ❌ 不占双倍空间（`.git` 是共享的）
- ❌ 不需要分别 push（提交在一个 worktree，另一个也能看到）

## 常用命令总结

```bash
# 列出所有 worktree
git worktree list

# 添加 worktree
git worktree add <路径> <分支名>

# 移除 worktree
git worktree remove <路径>

# 清理已删除分支的 worktree
git worktree prune
```

## 与 AI 编码工具的配合

打开多个 VS Code 窗口，每个窗口对应一个 worktree：

```bash
# 窗口 1 - main 分支
code /Users/xiazhiwei/Uni-Rec-Challenge

# 窗口 2 - hy3-preview-opt 分支
code /Users/xiazhiwei/Uni-Rec-Challenge-hy3
```

每个窗口运行独立的 Claude Code/Codex 会话，实现真正的并行开发。

## 相关文档

- [CLAUDE.md](/CLAUDE.md) - 包含 Worktree 使用说明
- [AGENTS.md](/AGENTS.md) - 包含 Worktree 使用说明
- [README.md](/README.md) - 项目概览和 Worktree 表格

---

## 学习心得

1. **Worktree 解决了多分支开发的痛点**：不再需要 stash/pop，直接 cd 切换目录即可
2. **空间效率极高**：多个 worktree 共享同一个 `.git`，几乎不增加磁盘占用
3. **与 AI 工具配合完美**：每个 worktree 可以独立运行 AI 编码会话，互不干扰
4. **原理简单但强大**：本质上是通过 `.git` 文件指向共享的 git 目录

## 后续计划

- [ ] 探索更多 worktree 的高级用法
- [ ] 研究 worktree 与 submodule 的组合使用
- [ ] 记录更多 Git 高级特性的学习过程

---

**记录格式模板**：
- 日期和主题
- 学习背景
- 核心概念
- 实践过程（包含具体命令和输出）
- 原理发现
- 关键结论
- 常用命令
- 学习心得
- 后续计划
