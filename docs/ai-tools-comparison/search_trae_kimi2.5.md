# AI 编程工具 Hooks 机制深度调研报告

> 调研时间：2026-04-19
> 调研范围：Cursor、VSCode Copilot、Claude Code、Trae、Codex CLI

---

## 一、Cursor Hooks 机制详解

### 1.1 什么是 Hooks？

**Hooks** 是 Cursor 1.7 版本引入的一个强大功能，允许用户在 AI Agent 生命周期的特定节点插入自定义脚本或逻辑，从而**观察、控制或扩展** Agent 的行为。

### 1.2 核心作用

1. **观察与审计** - 记录 Agent 的工具调用、Prompt 和响应
2. **安全管控** - 实时拦截危险命令、脱敏敏感信息
3. **自动化工作流** - 连接外部系统、自动格式化、发送通知等
4. **上下文注入** - 在会话开始时自动注入项目上下文

### 1.3 配置方式

**配置文件位置**（二选一）：
- **项目级**：`.cursor/hooks.json` - 仅对当前项目生效，可版本控制
- **用户级**：`~/.cursor/hooks.json` - 全局生效

**基本配置结构**：
```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [
      { "command": "bun run hooks/after-file-edit.ts" }
    ],
    "beforeShellExecution": [
      { "command": "sh -c 'echo \"Command: $1\" >> audit.log'" }
    ],
    "stop": [
      { "command": "osascript -e 'display notification \"Agent completed\"'" }
    ]
  }
}
```

### 1.4 支持的 Hook 事件

#### Agent 模式（Cmd+K/Agent Chat）

| 事件名称 | 触发时机 | 适用场景 |
|---------|---------|---------|
| `sessionStart` / `sessionEnd` | 会话开始/结束 | 初始化环境、清理资源 |
| `beforeShellExecution` | 执行 Shell 命令前 | 拦截危险命令、审计 |
| `afterShellExecution` | Shell 命令执行后 | 记录执行结果 |
| `afterFileEdit` | 文件编辑后 | 自动格式化、运行 lint |
| `beforeReadFile` | 读取文件前 | 访问控制、敏感文件保护 |
| `beforeSubmitPrompt` | 提交 Prompt 前 | Prompt 校验、关键词过滤 |
| `beforeMCPExecution` | MCP 工具执行前 | 控制外部工具使用 |
| `afterMCPExecution` | MCP 工具执行后 | 记录工具调用结果 |
| `stop` | Agent 完成时 | 发送通知、自动提交代码 |
| `subagentStart` / `subagentStop` | Subagent 启动/停止 | 控制 Task 工具执行 |
| `preToolUse` / `postToolUse` | 工具使用前后 | 通用工具拦截 |
| `afterAgentResponse` / `afterAgentThought` | Agent 响应/思考后 | 跟踪 Agent 行为 |
| `preCompact` | 上下文窗口压缩前 | 监听上下文压缩 |

#### Tab 模式（行内补全）

| 事件名称 | 触发时机 | 适用场景 |
|---------|---------|---------|
| `beforeTabFileRead` | Tab 补全读取文件前 | 控制 Tab 文件访问 |
| `afterTabFileEdit` | Tab 编辑后 | 对 Tab 编辑进行后处理 |

### 1.5 两种 Hook 类型

#### 1. 命令驱动 Hook（默认）
- 执行 Shell 脚本
- 通过 `stdin` 接收 JSON 输入
- 通过 `stdout` 返回 JSON
- 退出码行为：
  - `0` - Hook 成功，使用 JSON 输出
  - `2` - 阻止该操作（等同于返回 `permission: "deny"`）
  - 其他 - Hook 失败，但操作继续执行（默认失败放行）

#### 2. Prompt 驱动 Hook
- 使用 LLM 评估自然语言条件
- 返回 `{ ok: boolean, reason?: string }`
- 使用快速模型进行快速评估
- `$ARGUMENTS` 占位符自动替换为 hook 输入的 JSON

### 1.6 实际应用场景举例

#### 场景 1：自动格式化代码
```json
{
  "afterFileEdit": [
    { "command": "bunx @biomejs/biome lint --fix --unsafe" }
  ]
}
```

#### 场景 2：阻止危险命令
```bash
#!/bin/bash
# before-shell-execution.sh
read -r input
command=$(echo "$input" | jq -r '.command')

if [[ "$command" == *"rm -rf"* ]] || [[ "$command" == *"drop database"* ]]; then
  echo '{"permission": "deny", "agentMessage": "危险命令被阻止"}'
else
  echo '{"permission": "allow"}'
fi
```

#### 场景 3：Git 自动提交
```json
{
  "stop": [
    { "command": "git add -A && git commit -m 'Cursor Agent: session complete'" }
  ]
}
```

#### 场景 4：敏感文件保护
```json
{
  "beforeReadFile": [
    { 
      "command": "sh -c 'if [[ \"$1\" == *.env* ]]; then echo \"{\\"permission\\": \\"deny\\"}\"; else echo \"{\\"permission\\": \\"allow\\"}\"; fi'"
    }
  ]
}
```

#### 场景 5：TypeScript 自动化 Hook（企业级示例）
```typescript
// stop 钩子：记录遥测数据并自动重试
import type { StopPayload } from "cursor-hooks";

const input: StopPayload = await Bun.stdin.json();

// 记录失败次数到磁盘
const failureCount = await logToDisk(input);

// 转发到内部 API
await fetch(process.env.AGENT_TELEMETRY_URL!, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(input),
});

// 连续失败两次时自动安排重试
if (failureCount >= 2) {
  await scheduleRetry(input);
}
```

### 1.7 企业级合作伙伴集成

Cursor Hooks 已与多家安全/治理厂商集成：

| 合作伙伴 | 功能描述 |
|---------|---------|
| **Mint** | MCP 服务器清单构建、工具使用监控、敏感数据扫描 |
| **Oasis Security** | 最小权限策略实施、审计追踪 |
| **Runlayer** | MCP 工具封装、集中控制和可见性 |
| **Corridor** | 代码实现和安全设计决策实时反馈 |
| **Semgrep** | AI 生成代码漏洞扫描、实时反馈 |
| **Endor Labs** | 包安装拦截、恶意依赖扫描 |
| **Snyk** | Agent 操作实时审查、提示注入防护 |
| **1Password** | 环境文件验证、按需访问机密信息 |

---

## 二、其他 AI 编程工具 Hooks 支持情况

### 2.1 VSCode Copilot ✅ 支持 Hooks（预览版）

VSCode Copilot 也已引入类似的 Hooks 机制，功能与 Cursor 类似。

**配置位置**：
- 用户级：`~/.github/copilot/hooks.json`
- 工作区级：`.github/copilot/hooks.json`

**支持的事件**：
- `preToolUse` / `postToolUse` - 工具使用前后
- `beforeShellExecution` - Shell 命令执行前
- `afterFileEdit` - 文件编辑后
- `sessionStart` / `sessionEnd` - 会话生命周期

**配置方式**：
- 命令面板输入 `/hooks`
- 运行 `Chat: Configure Hooks` 命令
- 聊天视图设置图标 → Hooks

**配置示例**：
```json
{
  "hooks": {
    "beforeShellExecution": [
      {
        "type": "command",
        "command": "security-scan.sh",
        "timeout": 5000
      }
    ]
  }
}
```

### 2.2 Claude Code ✅ 完整支持 Hooks

Claude Code 在 2025 年中期推出了 Hooks 系统，功能非常完善。

**配置位置**：
- `~/.claude/settings.json` - 用户级
- `.claude/settings.json` - 项目级
- `.claude/settings.local.json` - 本地工作区（不提交到版本控制）

**特色功能**：
- **HTTP Hooks** - 可以调用远程 API
- **Prompt-based Hooks** - 用自然语言定义条件
- **异步 Hooks** - 不阻塞主流程
- **MCP Tools Hooks** - 控制 MCP 工具

**Claude Code 特有的事件**：
- `permission_prompt` - 需要权限确认时
- `idle_prompt` - Claude 等待输入时
- `ConfigChange` - 配置文件变更时
- `elicitation_dialog` - Claude 向用户提问时

**配置示例**：
```json
{
  "hooks": {
    "FileEdit": [
      {
        "matcher": "\\.ts$",
        "hooks": [
          {
            "type": "command",
            "command": "npm run format"
          }
        ]
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "notify-send 'Claude Code' 'Task completed'"
      }
    ]
  }
}
```

### 2.3 Trae ❌ 暂不支持 Hooks

根据官方文档和社区调研，**Trae 目前没有 Hooks 机制**。

**Trae 当前的扩展体系**：
- **Rules** - AI 规则配置（`.trae/rules`）
- **Agents** - 自定义 Agent
- **MCP** - 模型上下文协议（支持 Tools、Resources、Prompts、Logging）
- **Skills** - 技能系统

**缺失功能**：
- 没有生命周期事件的自动触发机制
- 无法在执行前后插入自定义逻辑
- 无法拦截和修改 Agent 行为

**替代方案**：
- 使用 **Rules** 定义代码规范和约束
- 使用 **MCP** 扩展工具能力
- 期待未来版本加入 Hooks 支持

### 2.4 OpenAI Codex CLI ⚠️ 部分支持/开发中

从 GitHub 仓库和社区讨论来看：

**当前状态**：
- Codex CLI 有一个 `hooks` 引擎模块（`codex-rs/hooks/src/engine/dispatcher.rs`）
- 社区有提案建议添加 `PreToolUse`/`PostToolUse` 生命周期钩子（Issue #14882）
- 目前支持基础的 `notify` 配置用于任务完成通知
- **Hooks 功能尚未完全成熟**，还在积极开发中

**社区需求**（Issue #7396）：
- 请求添加 `post-run hooks` 在任务完成后自动执行脚本
- 目前只能通过 `&&` 链式命令或 wrapper 脚本实现

**示例配置**：
```json
{
  "notify": {
    "on_complete": "python on_complete.py"
  }
}
```

---

## 三、功能对比总结

| 工具 | Hooks 支持 | 成熟度 | 特色功能 | 配置方式 |
|------|-----------|-------|---------|---------|
| **Cursor** | ✅ 完整支持 | ⭐⭐⭐⭐⭐ | 最成熟，企业级功能，支持命令/Prompt 两种模式，多合作伙伴集成 | `.cursor/hooks.json` |
| **Claude Code** | ✅ 完整支持 | ⭐⭐⭐⭐⭐ | HTTP Hooks、异步 Hooks、MCP 工具 Hooks、Prompt-based Hooks | `.claude/settings.json` |
| **VSCode Copilot** | ✅ 预览版 | ⭐⭐⭐⭐ | 与 VSCode 生态深度集成，界面友好 | `.github/copilot/hooks.json` |
| **Trae** | ❌ 不支持 | - | 暂无计划，可通过 Rules 和 MCP 部分替代 | - |
| **Codex CLI** | ⚠️ 开发中 | ⭐⭐ | 基础 notify 功能，完整 Hooks 待开发 | `settings.json` |

---

## 四、选型建议

### 4.1 企业级安全合规场景
**推荐：Cursor 或 Claude Code**
- Cursor 提供完整的企业级控制、审计日志、沙箱模式
- 与多家安全厂商集成（Snyk、Semgrep、1Password 等）
- 支持 MDM 和云分发

### 4.2 个人开发者/自动化工作流
**推荐：Cursor 或 Claude Code**
- 自动格式化、自动提交、通知提醒
- 配置简单，社区示例丰富

### 4.3 VSCode 生态用户
**推荐：VSCode Copilot**
- 与编辑器深度集成
- 无需切换工具

### 4.4 Trae 用户
- 目前无法使用 Hooks，建议：
  1. 通过 **Rules** 定义项目规范
  2. 通过 **MCP** 扩展工具能力
  3. 关注官方更新，期待未来支持

---

## 五、参考资源

### 官方文档
- [Cursor Hooks 官方文档](https://cursor.com/docs/hooks)
- [Claude Code Hooks 文档](https://docs.anthropic.com/zh-CN/docs/claude-code/hooks)
- [VSCode Copilot Hooks 文档](https://code.visualstudio.com/docs/copilot/customization/hooks)
- [Trae Rules 文档](https://docs.trae.ai/ide/rules-for-ai)

### 社区资源
- [cursor-hooks TypeScript 类型定义](https://github.com/johnlindquist/cursor-hooks)
- [GitButler Cursor Hooks 集成指南](https://gitbutler.com)
- [Claude Code Hooks 实战指南](https://code.claude.com/docs/en/hooks-guide)

### 相关文章
- [Cursor 1.7 Adds Hooks for Agent Lifecycle Control - InfoQ](https://www.infoq.com/news/2025/10/cursor-hooks/)
- [Cursor Adds Enterprise Controls for Safer, Observable Agent-Driven Coding](https://oltre.dev/articles/cursor-adds-enterprise-controls-for-safer-observable-agent-driven-coding-1762092341977/)
- [How to Use Cursor 1.7 Hooks to Customize Your AI Coding Agent](https://skywork.ai/blog/how-to-cursor-1-7-hooks-guide/)
- [Claude Code Hooks 深度解析 - 腾讯云](https://cloud.tencent.com/developer/article/2649082)

---

*报告生成时间：2026-04-19*
