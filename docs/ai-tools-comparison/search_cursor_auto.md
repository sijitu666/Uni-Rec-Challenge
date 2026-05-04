# Cursor Hooks 机制调研（联网检索整理）

> 基于 Cursor / VS Code / OpenAI / Anthropic 官方文档，以及中文社区文章（博客园等；检索未命中可直接打开的知乎高赞帖，但同类中文实战文思路一致）。  
> 整理日期：2026-04-19

---

## 1. Cursor Hooks 是做什么的？

**Hooks** 让你在 AI **Agent 循环**的固定阶段，用**自定义脚本**介入：观察、拦截、改写行为。实现方式是 **spawn 子进程**，通过 **stdin/stdout 用 JSON** 通信。

- 官方文档：<https://cursor.com/docs/hooks>

官方列的典型用途包括：

- 编辑后跑格式化（Prettier 等）
- 做事件统计 / 埋点
- 扫描 PII、密钥
- **门控高风险操作**（例如 SQL 写、危险 shell）
- 控制 **Subagent（Task 工具）**
- **会话开始时注入上下文**

Cursor 还区分 **Agent（Cmd+K / Agent Chat）** 与 **Tab（行内补全）** 两套事件，例如 Tab 有 `beforeTabFileRead`、`afterTabFileEdit`，策略可以和 Agent 分开。

另外文档提到：**可加载第三方工具（如 Claude Code）的 hooks 配置**，详见官方 [Third Party Hooks](https://cursor.com/docs/agent/third-party-hooks)（以该页最新说明为准）。

### 1.1 Agent 侧主要事件（摘录）

- `sessionStart` / `sessionEnd` — 会话生命周期
- `preToolUse` / `postToolUse` / `postToolUseFailure` — 通用工具调用
- `subagentStart` / `subagentStop` — Subagent（Task）
- `beforeShellExecution` / `afterShellExecution` — Shell
- `beforeMCPExecution` / `afterMCPExecution` — MCP
- `beforeReadFile` / `afterFileEdit` — 读文件 / 编辑后
- `beforeSubmitPrompt` — 提交 prompt 前
- `preCompact` — 上下文压缩前
- `stop` — Agent 结束
- `afterAgentResponse` / `afterAgentThought` — 响应 / 思考后

### 1.2 Tab 侧事件

- `beforeTabFileRead`
- `afterTabFileEdit`

企业场景：Cloud agents 会跑仓库 hooks；Enterprise 还可有 team /企业托管 hooks（见官方 Hooks 文档说明）。

---

## 2. 一般怎么配置？

1. **配置文件位置**
   - 用户级：`~/.cursor/hooks.json`（全局）
   - 项目级：`项目根/.cursor/hooks.json`（仅该项目）

   Cursor 会**监视文件并自动重载**。

2. **基本形态**：`version` + `hooks` 映射「事件名 → 若干条 hook 定义」，每条通常有 `command`（可带 `timeout`、`matcher` 等）。

3. **两种执行类型**（官方文档）
   - **Command（默认）**：shell 脚本，stdin 进 JSON，stdout 出 JSON。
   - **Prompt**：用 LLM 做策略判断（例如自然语言安全策略），不必写脚本。

4. **拦截与退出码**（Command）：文档说明 **exit code `2` 可 block**（等价于返回 deny）；其它失败默认存在 **fail-open** 等行为，以实现为准。

5. **实操注意**（社区与官方 quickstart 常见提醒）

   - 脚本需 **`chmod +x`**
   - 用户级 hooks 与项目级 hooks 的**工作目录**不同：项目级脚本路径常写成 `.cursor/hooks/...`，而非 `./hooks/...`

### 2.1 最小示例（官方风格）

用户级 `~/.cursor/hooks.json`：

```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [{ "command": "./hooks/format.sh" }]
  }
}
```

项目级 `.cursor/hooks.json` 中 `command` 建议类似：`.cursor/hooks/format.sh`。

### 2.2 `beforeShellExecution` 带 matcher 示例

```json
{
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "./scripts/approve-network.sh",
        "timeout": 30,
        "matcher": "curl|wget|nc"
      }
    ]
  }
}
```

### 2.3 Prompt 型 hook示例

```json
{
  "hooks": {
    "beforeShellExecution": [
      {
        "type": "prompt",
        "prompt": "Does this command look safe to execute? Only allow read-only operations.",
        "timeout": 10
      }
    ]
  }
}
```

### 2.4 JSON Schema（可选）

在 VS Code/Cursor 的 `settings.json` 中为 `hooks.json` 配置 schema可获得补全，例如社区常用：

- `https://unpkg.com/cursor-hooks/schema/hooks.schema.json`（见 egghead 等教程）

---

## 3. 应用场景举例

| 场景 | 常用事件（Agent 侧） | 思路 |
|------|----------------------|------|
| 保存/编辑后自动格式化 | `afterFileEdit` | Prettier / 项目脚本 |
| 拦截危险终端命令 | `beforeShellExecution` + `matcher` | 审计或拒绝 |
| MCP 调用前后审计 | `beforeMCPExecution` / `afterMCPExecution` | 合规日志 |
| 读敏感文件前控制 | `beforeReadFile` | 脱敏或拒绝 |
| 用户发 prompt 前校验 | `beforeSubmitPrompt` | 策略、敏感内容检查 |
| 会话级注入说明/上下文 | `sessionStart` | 团队规范摘要等 |

---

## 4. 中文社区参考

- 博客园等平台有「Cursor Hooks 实战 / 官方文档学习要点」类文章，与官方事件、配置路径、安全门控思路一致。
- 示例检索结果：<https://www.cnblogs.com/goloving/p/19463129>（具体标题以页面为准）

---

## 5. 其他工具是否有类似机制？

### 5.1 VS Code + GitHub Copilot

**有。** **Agent hooks（Preview）** — 在 Agent 会话生命周期执行自定义 shell，结构化 JSON 输入/输出。

- 文档：<https://code.visualstudio.com/docs/copilot/customization/hooks>
- 工作区示例：`.github/hooks/*.json`（如文档中的 `format.json`）
- 也支持从 **Claude 格式**配置等路径加载（见文档中的 Hook file locations 表格）
- **Preview**；企业可能**禁用** hooks

### 5.2 Trae

公开信息里 **Trae 更强调 MCP、`.rules` 等**；GitHub 上存在 **Lifecycle hooks** 类 **feature request**（希望与 Cursor/Copilot 等生态对齐）。**不宜直接等同于**「已提供与 Cursor 文档同规格的全套 hooks」— 以 [Trae 官方文档](https://traeide.com/docs) 与当前版本为准。

### 5.3 Claude Code（CLI）

**有。** 官方 Hooks Guide / Hooks reference；在 `~/.claude/settings.json` 或项目 settings 中配置。

- 示例文档入口：<https://code.claude.com/docs/en/hooks-guide>

### 5.4 OpenAI Codex CLI

**有（实验性）。**

- 文档：<https://developers.openai.com/codex/hooks/>
- 需在 `config.toml` 中：`[features]` → `codex_hooks = true`
- 常见路径：`~/.codex/hooks.json`、`/.codex/hooks.json`
- 文档注明：**Windows 上暂时禁用**；行为持续迭代

---

## 6. 小结对比表

| 工具 | 是否有「Agent 生命周期 hooks」类机制 | 备注 |
|------|--------------------------------------|------|
| **Cursor** | 是 | `~/.cursor/hooks.json` / `.cursor/hooks.json`，事件细（含 shell/MCP/Tab 等） |
| **VS Code + Copilot** | 是（Preview） | `.github/hooks/*.json` 等；可消费 Claude 配置 |
| **Trae** | 不完全等同 / 以官方为准 | 社区有 hooks 诉求；以文档与版本为准 |
| **Claude Code** | 是 | `settings.json` 等 |
| **Codex CLI** | 是（实验） | `hooks.json` + feature flag |

---

## 7. 参考链接

- Cursor Hooks：<https://cursor.com/docs/hooks>
- Cursor 中文 Hooks页（若可用）：<https://cursor.com/cn/docs/hooks>
- Cursor Third Party Hooks：<https://cursor.com/docs/agent/third-party-hooks>
- VS Code Copilot Agent hooks：<https://code.visualstudio.com/docs/copilot/customization/hooks>
- OpenAI Codex Hooks：<https://developers.openai.com/codex/hooks/>
- Claude Code hooks guide：<https://code.claude.com/docs/en/hooks-guide>
