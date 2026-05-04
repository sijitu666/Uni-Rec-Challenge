# AI 辅助工具 Hooks 机制调研报告

**Cursor 的 Hooks 机制**是近期 AI IDE 发展中非常核心且高阶的一项功能。基于对 Cursor 官方文档、知乎讨论以及 GitHub 社区实践的汇总，以下是关于 Cursor Hooks 以及其他主流 AI 编码工具 Hooks 机制的深度解析。

---

### 一、 什么是 Cursor 的 Hooks 机制？

简单来说，Cursor 的 Hooks（钩子）是一种**生命周期干预机制**。

当 Cursor 的 AI Agent（智能体）在帮你写代码、读文件或执行终端命令时，会经历一系列特定的生命周期节点。Hooks 允许开发者在这些**特定的触发点**（例如：在执行一段 Shell 命令之前，或者在修改完毕一个文件之后），通过运行**外部的自定义脚本（Shell/Python/Node等）**来拦截、干预或增强 AI 的行为。

与其他“提示词规则（Prompt Rules）”不同：提示词可能会被 LLM 遗忘或忽略，但 **Hooks 是确定性强制执行的系统级拦截**。

#### Cursor 支持的常见 Hook 触发点：
*   `beforeSubmitPrompt`：在你提交 Prompt 给 AI 之前触发。
*   `beforeShellExecution`：在 AI Agent 试图在终端执行 Shell 命令之前触发（最常用）。
*   `beforeMCPExecution`：在 AI 调用外部 MCP（Model Context Protocol）工具前触发。
*   `beforeReadFile` / `afterFileEdit`：在 AI 读取或修改文件后触发。
*   `stop`：当 AI 任务执行结束时触发。

---

### 二、 一般如何配置及常见应用场景举例

**配置方式：**
通常，你可以在项目根目录（或用户全局目录 `~/.cursor/`、企业级目录 `/etc/cursor/`）下创建一个 `hooks.json` 文件。

你可以编写如下配置：
```json
{
  // 1. 拦截并检查 AI 将要执行的 Shell 命令
  "beforeShellExecution": {
    "command": "./scripts/security_check.sh"
  },
  // 2. AI 修改完文件后自动进行格式化
  "afterFileEdit": {
    "command": "npm run format -- ${file}"
  }
}
```

**知乎/社区开发者总结的 3 大神仙应用场景：**

1.  **安全防御与权限管控（Guardrails）：**
    *   **场景：** AI 有时候会“发疯”，尝试执行 `rm -rf` 或者直接 push 未经测试的代码到 main 分支。
    *   **做法：** 利用 `beforeShellExecution` 钩子，写一个脚本拦截所有包含敏感操作的命令，或者结合 1Password 强制在执行部署命令前进行身份验证。
2.  **代码质量与合规底线（Auto-Fix & Lint）：**
    *   **场景：** AI 生成的代码经常包含未导入的包或格式错误。
    *   **做法：** 很多团队（如 Semgrep 公司分享的经验）利用 `afterFileEdit`，一旦 AI 修改了文件，立刻触发 ESLint 或静态扫描工具。如果扫描失败，直接将报错回传给 AI 强制其重写，直到通过为止。
3.  **动态上下文注入：**
    *   **场景：** 每次跟 AI 对话前，想让它知道当前 CI/CD 的报错信息或 JIRA 上的最新任务状态。
    *   **做法：** 在 `beforeSubmitPrompt` 触发脚本，自动拉取 JIRA API 信息，拼接在你的提问背后。

---

### 三、 其他 AI Coding 工具的 Hooks 机制横评

除了 Cursor，目前这股“Agent Hook 开发流”正在席卷各路 AI Coding 工具，以下是对官方文档的总结对比：

#### 1. VS Code Github Copilot：有，且偏向企业级管控
*   **机制：** Copilot 提供了一整套非常完善的 Hooks SDK。你可以在 `.github/hooks/hooks.json` 中配置。
*   **支持的事件：** `sessionStart`, `preToolUse`, `postToolUse`, `userPromptSubmitted` 等。
*   **侧重点：** 官方文档强调该功能主要供 DevOps 团队进行**合规审计**和**组织策略强制执行**（比如禁止 Copilot 越权执行某些破坏性脚本，记录所有的 prompt 审计日志）。

#### 2. Claude Code (CLI 工具)： 有，极其强大且官方力推！
*   **机制：** Claude Code (Anthropic 官方出的终端 AI 工具) 将 Hooks 视作**一等公民**。你可以直接在终端输入 `/hooks` 呼出自带的 UI 界面进行配置，或修改 `~/.claude/settings.json`。
*   **特色：** 它支持不仅限于运行脚本（`command`），还能配置 `http`（任务完成直接调接口发 Slack 消息报警）、`prompt`（让另一个小型 LLM 检查主代理的生成结果是否安全）。这是目前在 CLI 领域**最原生、最好用**的 Hook 系统之一。

#### 3. OpenAI Codex CLI： 有，实验性功能
*   **机制：** OpenAI 近期推出的 Codex CLI 工具也引入了这套机制，配置路径为 `~/.codex/hooks.json`。
*   **特色：** 事件与前面类似（`PreToolUse`、`PostToolUse` 等）。文档提到一个特殊场景是可以利用 Hook 实现“自动对话总结”，以节约上下文 Token，或是扫描 Prompt 防止向 OpenAI 回传包含公司 API Token 的机密数据。

#### 4. Trae (字节跳动 AI IDE)： 暂无独立的、显式的顶层 Agent Hook 配置文件
*   **现状：** 根据目前的文档和社区反馈，Trae 作为一个以“开箱即用”和“深度集成”为卖点的字节系 VS Code Fork 变体，其在 Agent 底层拦截机制上的开放度还在演进中。目前尚未单独大肆宣传类似 Cursor 的 `.cursor/hooks.json` 这种让用户自己高度定制的生命周期钩子接入点。不过，你依然可以通过标准 VS code Task、Pre-commit Hook 或者编写 Trae/VS Code 扩展插件达到类似的代码自动化拦截效果。

### 总结
**“Prompt 是建议，而 Hook 是法律”。**
如果说在过去半年里，大家还在折腾 `.cursorrules`（让 AI 听话地遵守代码风格）；那么随着各类 AI 工具（Cursor, Claude Code, Copilot）纷纷实装 Hooks 机制，接下来的趋势将是 **“AI 自动化流水线”**。开发者正在把 AI 真正当成一个会出错的“初级程序员”，然后用各种脚本和扫描工具（Hooks）去给这位 AI 程序员套上不可逾越的护栏。
