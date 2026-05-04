# AI Agent 学习路线与资源整理

> 对话时间: 2026-04-21
> 对话参与者: 用户 & Trae (Kimi K2.5)
> 主题: AI Agent 学习资源推荐，重点了解 Claude Code、OpenCode 等工具的机制

---

## 用户需求

用户希望学习 AI Agent 相关知识，用于后续找工作。已了解 OpenCode、Claude Code 的基本机制，希望深入学习，寻找相关教程或简单的代码仓库快速上手。

---

## 推荐学习路径

### 阶段一：快速上手（1-2 周）

#### 1. learn-claude-code ⭐ 最推荐

- **GitHub**: https://github.com/shareAI-lab/learn-claude-code
- **特点**: 12 节循序渐进的课程，从最小循环到完整 Agent
- **适合**: 零基础到进阶，代码能跑、过程可观察
- **内容**:
  - s01: 核心循环 (One loop & Bash is all you need)
  - s02: 工具调度
  - s03: 计划模式
  - s04: 子代理
  - s05-s12: 上下文压缩、任务持久化、多 Agent 协作等

**快速开始**:
```bash
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env  # 填入你的 API Key
python agents/s01_agent_loop.py  # 从这里开始
```

#### 2. 保姆级教程：从零搭建 AI Agent

- **来源**: CSDN 博客
- **特点**: 2 小时完整实战，从零写出一个真正能用的 Agent
- **核心内容**:
  - ReAct 循环实现
  - 工具系统设计
  - 记忆系统
  - 完整可运行代码

---

### 阶段二：深入理解架构（2-4 周）

#### 3. learn-coding-agent ⭐ 架构深度解析

- **GitHub**: https://github.com/sanbuphy/learn-coding-agent
- **特点**: 51 万行代码逐行解析 Claude Code 架构
- **核心内容**:
  - 12 层渐进式安全带机制
  - 权限系统五层关卡
  - MCP 协议集成
  - 子代理系统
  - 隐藏功能分析（卧底模式等）

**12 层机制速览**:

| 层次 | 机制 | 解决的问题 |
|------|------|-----------|
| s01 | 核心循环 | 最基本的 agent 循环 |
| s02 | 工具调度 | 一个工具 = 一个 handler |
| s03 | 计划模式 | 先列步骤再执行 |
| s04 | 子代理 | 拆解大任务，清理上下文 |
| s05 | 按需知识 | 延迟加载 CLAUDE.md |
| s06 | 上下文压缩 | 三层压缩策略 |
| s07 | 持久化任务 | 大目标 → 小任务 → 磁盘 |
| s08 | 后台任务 | 慢操作放后台 |
| s09 | 代理团队 | 多代理协作 |
| s10 | 团队协议 | 代理间通信规范 |
| s11 | 自主代理 | 空闲循环 + 自动认领 |
| s12 | 工作树隔离 | 各干各的目录 |

#### 4. OpenCode 源码学习

- **GitHub**: https://github.com/opencode-ai/opencode
- **特点**: 开源的 Claude Code 替代品，不绑定特定 AI 提供商
- **技术栈**: TypeScript + Bun + Hono + SolidJS
- **学习价值**:
  - Provider 系统（多模型支持）
  - Tool 系统（工具注册与执行）
  - Session 系统（会话管理）
  - Agent 系统（智能体）
  - Permission 系统（权限控制）

**推荐学习顺序**:
1. 阅读 README.md 和 CONTRIBUTING.md
2. 阅读 AGENTS.md 了解代码风格
3. 按顺序阅读 `packages/opencode/src/` 下的核心模块

---

### 阶段三：生产级框架实践（4-8 周）

#### 5. Microsoft Agent Framework

- **GitHub**: https://github.com/microsoft/agent-framework
- **特点**: 微软官方出品，生产级框架
- **支持语言**: Python + .NET
- **核心能力**:
  - Agents: 单 Agent 工具调用
  - Workflows: 多 Agent 图工作流
  - MCP 集成
  - A2A 协议（Agent-to-Agent 通信）

```bash
# Python 快速开始
pip install agent-framework

# 示例代码
from agent_framework.openai import OpenAIChatClient
client = OpenAIChatClient()
agent = client.as_agent(name="HelloAgent", instructions="You are a friendly assistant.")
result = await agent.run("What is the largest city in France?")
```

#### 6. Agent-Framework-Samples

- **GitHub**: https://github.com/microsoft/Agent-Framework-Samples
- **特点**: 微软官方示例库，从入门到实战
- **内容**:
  - 00.ForBeginners: 初学者友好示例
  - 01.AgentFoundation: 核心概念
  - 02.CreateYourFirstAgent: 创建第一个 Agent
  - 03-09: 工具、RAG、工作流、多 Agent 等

---

## 学习建议

### 推荐学习顺序

```
Week 1-2: 快速上手
  └─ learn-claude-code (s01-s04)
  └─ 保姆级教程（从零搭建）

Week 3-4: 深入架构
  └─ learn-coding-agent（12 层机制）
  └─ OpenCode 源码阅读

Week 5-8: 生产实践
  └─ Microsoft Agent Framework
  └─ 自己实现一个简化版 Agent
```

### 面试准备要点

1. **核心概念**:
   - ReAct 循环（Reasoning + Acting）
   - Tool Use / Function Calling
   - 上下文管理（压缩、修剪）
   - 多 Agent 协作

2. **工程实践**:
   - 权限控制设计
   - 错误处理与重试
   - 会话状态管理
   - MCP 协议理解

3. **项目经验**:
   - 跑通 learn-claude-code 全部 12 节课
   - 阅读 OpenCode 核心源码
   - 尝试自己实现一个简化版 Agent

---

## 关键链接汇总

| 资源 | 链接 | 用途 |
|------|------|------|
| learn-claude-code | https://github.com/shareAI-lab/learn-claude-code | 入门首选 |
| learn-coding-agent | https://github.com/sanbuphy/learn-coding-agent | 架构深度解析 |
| OpenCode | https://github.com/opencode-ai/opencode | 开源实现参考 |
| MS Agent Framework | https://github.com/microsoft/agent-framework | 生产级框架 |
| MS Samples | https://github.com/microsoft/Agent-Framework-Samples | 官方示例 |

---

## 补充：Claude Code 核心概念

### 1. Skills（技能包）

Skills 是预封装的工作流，用完即走，不占用上下文。

**官方 Skills 库**: https://github.com/anthropics/skills

常用官方 Skills:
```bash
# 前端设计技能
npx skills-installer install @anthropics/claude-code/frontend-design

# 文档协同技能
npx skills-installer install @anthropics/claude-code/doc-coauthoring

# PDF 处理技能
npx skills-installer install @anthropics/claude-code/pdf
```

### 2. Hooks（钩子）

Hooks 是在特定事件触发时自动执行的脚本。

**Hook 事件类型**:

| 事件类型 | 触发时机 | 典型用途 |
|---------|---------|---------|
| user-prompt-submit | 用户提交提示词前 | 验证、修改提示词 |
| tool-use | 工具使用前 | 权限检查、参数验证 |
| after-tool-use | 工具使用后 | 日志记录、结果处理 |
| permission-request | 权限请求时 | 拦截危险操作 |

### 3. MCP Servers（模型上下文协议服务器）

MCP 是 AI 的扩展接口标准，通过添加 MCP 服务器可以扩展 Claude Code 获取外部工具、资源、服务的能力。

**常用 MCP 服务器**:

| MCP Server | 功能 | Star 数 |
|-----------|------|--------|
| chrome-devtools-mcp | 浏览器自动化，26 个工具 | 18.5k |
| github-mcp | GitHub API 集成 | 10k+ |
| postgres-mcp | PostgreSQL 数据库操作 | 5k+ |

安装示例:
```bash
claude mcp add chrome-devtools npx chrome-devtools-mcp@latest
```

### 4. Subagents（子代理）

Subagents 是可以并行处理任务的独立 AI 代理，每个子代理拥有独立的 200K 上下文窗口。

### 5. CLAUDE.md（项目记忆文件）

CLAUDE.md 是 Claude Code 的"项目记忆文件"，记录项目结构、构建命令、代码规范、架构决策等信息。

**作用**:
- 📚 项目知识库
- 🚀 快速启动
- 🤝 团队协作
- 🔄 持续迭代

### 6. Plan 模式（规划模式）

"先规划、后执行"的工作模式，Claude 会先分析项目架构再起草实现方案。

**进入方式**: 按两次 Shift+Tab 或输入 `/plan`

**适合场景**:
- ✅ 复杂功能开发
- ✅ 架构重构
- ✅ 性能优化
- ✅ 代码迁移

---

## 总结

对于想深入 AI Agent 领域的工程师，建议按照以下优先级学习：

1. **首先跑通** `learn-claude-code` 的 12 节课，建立直观认识
2. **深入阅读** `learn-coding-agent` 的架构解析，理解生产级设计
3. **参考源码** `OpenCode` 的开源实现，学习工程实践
4. **实践框架** `Microsoft Agent Framework`，掌握企业级开发

这份学习路线从入门到进阶，覆盖了理论学习、源码阅读、工程实践三个层面，适合用于面试准备和技能提升。
