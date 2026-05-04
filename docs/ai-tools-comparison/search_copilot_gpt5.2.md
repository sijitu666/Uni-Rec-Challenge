# Cursor Hooks 机制调研与对比（Cursor / VS Code Copilot / Trae / Claude Code / OpenAI Codex）

> 日期：2026-04-19

## 结论速览

- Claude Code、Cursor、VS Code Copilot（Agent hooks，Preview）、OpenAI Codex 都提供“生命周期 hooks”：在固定事件点运行脚本（部分支持 HTTP/LLM），并用 JSON stdin/stdout + 特定退出码（常见 `exit 2`）表达阻止/继续/注入上下文等行为。
- Trae 在已检索的官方文档中未呈现同类“可编程生命周期 hooks”；其更接近“规则（Rules）+ 自动运行安全策略（Auto-run allow/deny）”。

## 1) Hooks 是什么（共同抽象）

Hook = 在 agent 运行的关键生命周期点触发的“确定性自动化”。典型特征：

- **输入**：宿主把事件上下文以 JSON 传给你的 handler（常见是 stdin；有的支持 HTTP POST）。
- **输出**：handler 用 stdout JSON（或退出码）告诉宿主：是否拦截、是否要求确认、是否继续会话、是否注入上下文、（部分产品）是否修改工具输入。
- **常见事件**：`SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`PreCompact`、`Stop`、`SubagentStart/Stop` 等。

从“用途”角度，hooks 更偏向：**安全门禁、质量自动化、审计治理、上下文注入**。

## 2) Cursor Hooks

官方文档：
- https://cursor.com/docs/hooks
- Claude 兼容（Third-party hooks）：https://cursor.com/docs/reference/third-party-hooks

### 它能做什么

- **Agent 与 Tab 分离的事件体系**：同一套 hooks 能覆盖 Cursor Agent（Cmd+K/Agent Chat）和 Cursor Tab（行内补全），但事件不同。
- **覆盖面较广**：除 `preToolUse/postToolUse` 外，还包含 shell、MCP、文件读取/编辑、提交 prompt、压缩、stop 等事件，并有 Tab 专用文件读写事件。
- **命令类 hooks**：stdin 收 JSON，stdout 出 JSON。
- **阻断语义**：命令类 hook 以退出码 `2` 阻断操作（等价于 deny），以退出码 `0` 成功并解析 JSON；其他退出码默认为“失败放行”（可配 `failClosed: true` 改为失败即阻断）。
- **循环控制**：`stop`/`subagentStop` 支持 `followup_message` 触发自动后续消息，并用 `loop_limit` 限制循环次数。

### 怎么配置（Cursor 原生）

- 配置文件：
  - 项目级：`<project-root>/.cursor/hooks.json`
  - 用户级：`~/.cursor/hooks.json`
- 多层来源合并与优先级（高到低）：Enterprise → Team → Project → User。
- Cursor 会监视 hooks 配置文件并自动重载。

最小示例（项目级/用户级都可；拦截危险 shell）：

```json
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "./hooks/block-rm.sh",
        "timeout": 30,
        "matcher": "rm -rf|rm -r"
      }
    ]
  }
}
```

> 注意：Cursor 不同来源的 hooks 运行时工作目录不同（用户级从 `~/.cursor/`，项目级从项目根）。

### Claude Code hooks 兼容（Cursor third-party hooks）

- Cursor 可读取 Claude Code 的 hooks 配置（需在设置中启用 Third-party skills），来源包括：
  - `.claude/settings.local.json`
  - `.claude/settings.json`
  - `~/.claude/settings.json`
- Cursor 会把 Claude 的 hook 事件名映射到 Cursor 对应事件名（例如 `PreToolUse` → `preToolUse`，`Stop` → `stop`）。
- 合并优先级（高到低）包含 Cursor 的 Enterprise/Team/Project/User，然后再叠加 Claude 的 local/project/user。

## 3) Claude Code Hooks（参考模型：覆盖最全）

官方文档：
- https://code.claude.com/docs/en/hooks

### 它能做什么

- **事件覆盖最全**：工具前后、权限请求、子代理、任务、通知、配置变更、目录/文件变化、压缩前后、worktree 生命周期、MCP elicitation 等。
- **handler 类型最丰富**：`command`、`http`、`prompt`、`agent`，并支持 async 执行（`async`/`asyncRewake`）。
- **阻断语义清晰**：`exit 2` 是“阻止/拒绝/继续”的核心机制，且按事件不同语义不同（例如 `PreToolUse` 阻止工具调用、`Stop` 阻止停止并继续对话）。
- **结构化控制**：大量事件支持 `hookSpecificOutput` 提供精细控制（例如 `permissionDecision`）。

### 怎么配置（Claude）

- 典型结构为三层：Event → matcher group → handlers（`hooks` 数组）。

示例（官方风格：拦截 destructive rm）：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(rm *)",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/block-rm.sh"
          }
        ]
      }
    ]
  }
}
```

脚本逻辑通常为：stdin 读 JSON（例如 `.tool_input.command`），stdout 输出 `hookSpecificOutput.permissionDecision: "deny"`，或直接 `exit 2` 阻止。

## 4) VS Code Copilot Agent hooks（Preview）

官方文档：
- https://code.visualstudio.com/docs/copilot/customization/hooks

### 它能做什么

- 支持 8 个核心事件：`SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`PreCompact`、`SubagentStart`、`SubagentStop`、`Stop`。
- 兼容 Claude Code 与 Copilot CLI 的 hook 配置形状（PascalCase 事件名），stdin/stdout JSON；`exit 2` 为 blocking。
- `PreToolUse` 可通过 `hookSpecificOutput.permissionDecision: allow|deny|ask` 控制单次工具调用。
- `Stop` 可阻止停止并继续（会消耗更多 premium requests，官方文档提醒需用 `stop_hook_active` 防止无限循环）。

### 怎么配置

- 默认扫描位置：
  - workspace：`.github/hooks/*.json`
  - Claude format：`.claude/settings.json`、`.claude/settings.local.json`
  - user：`~/.copilot/hooks`、`~/.claude/settings.json`
- 可通过 `chat.hookFilesLocations` 自定义启用/禁用加载位置。

Quick start（官方示例：PostToolUse 后跑 prettier）：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "type": "command",
        "command": "npx prettier --write \"$TOOL_INPUT_FILE_PATH\""
      }
    ]
  }
}
```

### 关键差异/坑

- VS Code 官方 FAQ：解析 Claude matcher 语法但**当前忽略 matcher 值**，导致 hooks 可能对所有工具调用都触发。
- Claude 与 VS Code 工具命名/输入字段命名不同（Claude 常见 snake_case，VS Code 工具常见 camelCase），迁移脚本时需要适配。

## 5) Trae：规则（Rules）+ Auto-run 安全策略（非生命周期 hooks）

官方文档：
- Rules：https://docs.trae.ai/ide/rules?_lang=en
- Auto-run & security：https://docs.trae.ai/ide/auto-run-and-security?_lang=en

### 它提供的“相邻机制”

- **Rules**：把团队规范/代码风格/语言框架/交互偏好写成规则；project rules 位于 `.trae/rules/`（Markdown），用于约束模型输出。
- **Auto-run**：对“自动运行 MCP / 自动运行终端命令”提供模式开关与 allowlist/denylist（安全策略层面）。

### 基于已检索官方页的判断

- 未发现类似 Claude/Cursor/VS Code/Codex 这种“事件 → handler（脚本/HTTP）→ JSON 协议”的生命周期 hooks 系统。

## 6) OpenAI Codex Hooks（官方 hosted docs + 现状限制）

官方文档：
- Hooks：https://developers.openai.com/codex/hooks
- Config reference（特性开关等）：https://developers.openai.com/codex/config-reference

### 它能做什么

- 官方明确 Hooks 为实验特性；需在 `config.toml` 开启：

```toml
[features]
codex_hooks = true
```

- Codex 会在“激活的 config layer 旁”发现 `hooks.json`；常用位置：
  - `~/.codex/hooks.json`
  - `<repo>/.codex/hooks.json`
- 多个 `hooks.json` 会**叠加加载**（高优先级不替换低优先级 hooks）。
- 当前限制（官方页明确标注 Work in progress）：
  - `PreToolUse` / `PostToolUse` 目前主要支持 Bash 工具拦截/结果处理；对 MCP、Write、WebSearch 等非 shell 工具拦截仍不完整。
  - `PreToolUse` 只是 guardrail，不能视为完整 enforcement boundary（模型可能通过“写脚本再 Bash 执行”绕过）。

### 配置形状

Codex hooks 结构同样是三层：Event → matcher group → handlers。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.codex/hooks/pre_tool_use_policy.py",
            "statusMessage": "Checking Bash command"
          }
        ]
      }
    ]
  }
}
```

### matcher 与事件现状

- `matcher` 是 regex string，但只有部分事件目前生效（官方表格指出 `Stop`、`UserPromptSubmit` 不支持 matcher）。
- 当前 runtime 下，`PreToolUse` / `PostToolUse` 的 `tool_name` 常为 `Bash`。

### 输入/输出与阻断

- 所有 command hook 从 stdin 接收一个 JSON 对象，包含如 `session_id`、`transcript_path`、`cwd`、`hook_event_name`、`model` 等公共字段。
- `PreToolUse` 可用 `hookSpecificOutput.permissionDecision: "deny"`（或旧形态 `decision: "block"`）阻止 Bash，也可用 `exit 2` 并把原因写到 stderr。
- 官方页说明：部分字段虽会被解析但**暂不支持**，并表现为 fail-open。

## 7) 对比矩阵（关键维度）

| 产品 | 是否是生命周期 hooks | 配置格式 | 事件覆盖程度 | 主要拦截能力 | matcher 现状 | 兼容/生态 |
|---|---|---|---|---|---|---|
| Claude Code | 是 | settings.json 三层结构；支持 command/http/prompt/agent | 最全 | 可拦截 tool/permission/stop 等（`exit 2` + JSON） | 生效且规则细 | 参考实现与生态最成熟 |
| Cursor | 是 | hooks.json（`version: 1`） | 很全（含 shell/MCP/文件/Tab） | 可 deny/ask、可改输入、可 followup 循环；支持 `failClosed` | 生效 | 官方支持 Claude hooks 兼容与映射/合并 |
| VS Code Copilot (Preview) | 是 | Claude/Copilot CLI 兼容格式；`.github/hooks/*.json` | 8 个核心事件 | `exit 2` block；`PreToolUse` 有 `permissionDecision` | 当前忽略 Claude matcher 值（官方说明） | 兼容 Claude/Copilot CLI；支持 agent frontmatter hooks |
| OpenAI Codex (Experimental) | 是 | hooks.json（Claude-like 三层结构） | 目前较少（重点 turn-scope） | 目前主要对 Bash 做 deny/block（WIP，fail open 多） | 部分事件支持 matcher，部分忽略 | 官方 docs + schema 指向 GitHub 生成文件 |
| Trae | 否（更像规则/策略） | `.trae/rules`（Markdown）+ auto-run 安全策略 | 不适用 | allow/deny 自动运行命令/MCP（策略层） | 不适用 | 兼容导入 AGENTS.md/CLAUDE.md 作为上下文规则 |

## 8) 典型应用场景（跨产品通用）

- **安全门禁**：拦截危险命令（`rm -rf`、`DROP TABLE`）、限制网络访问、阻止读取敏感文件（Cursor 的 `beforeReadFile` 很适合）。
- **质量自动化**：写文件后自动格式化/跑 lint/test，把结果回灌为上下文。
- **审计与治理**：记录每次 tool 调用与输出摘要；企业分发与集中管理（Cursor Enterprise/Team，Claude managed policy）。
- **上下文注入**：`SessionStart` 注入版本/分支/环境信息；`UserPromptSubmit` 注入“先问清复现/先跑测试”等守则。

## 9) 官方链接汇总（便于引用）

- Cursor Hooks：https://cursor.com/docs/hooks
- Cursor Third-party hooks（Claude 兼容）：https://cursor.com/docs/reference/third-party-hooks
- Claude Code Hooks reference：https://code.claude.com/docs/en/hooks
- VS Code Copilot Agent hooks（Preview）：https://code.visualstudio.com/docs/copilot/customization/hooks
- Trae Rules：https://docs.trae.ai/ide/rules?_lang=en
- Trae Auto-run & security：https://docs.trae.ai/ide/auto-run-and-security?_lang=en
- OpenAI Codex Hooks：https://developers.openai.com/codex/hooks
- OpenAI Codex Config reference：https://developers.openai.com/codex/config-reference
