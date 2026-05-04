# AI编程工具Hooks机制调研报告

> 调研时间：2026-04-19  
> 调研范围：Cursor、VSCode Copilot、Claude Code、Codex CLI、Trae

---

## 一、Cursor Hooks机制详解

### 1.1 用途与核心价值

Cursor Hooks是一个**生命周期钩子系统**，允许在AI Agent执行过程中的特定节点插入自定义脚本/命令，实现以下目标：

- **安全策略执行**：阻止危险命令（如`rm -rf`、`DROP TABLE`）
- **代码质量自动化**：自动运行格式化工具、Linter、测试
- **审计日志**：记录工具调用、命令执行、文件变更
- **上下文注入**：动态添加项目信息、API密钥
- **审批控制**：自动批准安全操作，敏感操作需确认

### 1.2 配置方法

**配置文件位置**：
- 项目级：`.cursor/hooks.json`（随版本控制，团队共享）
- 用户级：`~/.cursor/hooks.json`（个人使用）

**配置示例**：
```json
{
  "hooks": {
    "beforeShellExecution": [
      {
        "type": "command",
        "command": "./scripts/validate-command.sh",
        "failClosed": true
      }
    ],
    "afterFileEdit": [
      {
        "type": "command", 
        "command": "npx prettier --write \"$FILE_PATH\""
      }
    ],
    "stop": [
      {
        "type": "prompt",
        "command": "检查代码是否符合项目规范"
      }
    ]
  }
}
```

### 1.3 生命周期事件

Cursor 1.7 Beta 目前提供6个核心钩子：

| 钩子 | 触发时机 | 用途 |
|------|----------|------|
| `beforeSubmitPrompt` | 用户提交prompt前 | 记录上下文、审计 |
| `beforeShellExecution` | 执行shell命令前 | **拦截/批准命令** |
| `beforeMCPExecution` | 执行MCP工具前 | 工具调用管控 |
| `beforeReadFile` | 读取文件前 | 访问控制 |
| `afterFileEdit` | 文件编辑后 | 自动格式化、运行测试 |
| `stop` | 任务完成时 | 验证、提交、通知 |

### 1.4 钩子返回值

钩子可以返回JSON控制行为：

```json
{
  "continue": true|false,
  "permission": "allow|deny|ask",
  "user_message": "显示给用户的消息",
  "agent_message": "给AI的额外信息"
}
```

**退出码**：
- 退出码 `2` 会阻止操作执行（相当于`permission: "deny"`）

### 1.5 应用场景举例

1. **Git命令管控**：强制使用`gh` CLI而非原始git命令
2. **自动格式化**：文件保存后自动运行Prettier
3. **API密钥扫描**：拦截包含密钥的prompt提交
4. **测试强制执行**：文件修改后自动运行相关测试
5. **提交信息生成**：根据改动自动生成commit message

---

## 二、其他AI编程工具Hooks功能对比

### 2.1 VSCode Copilot

**支持状态**：✅ Preview阶段

**官方文档**：https://code.visualstudio.com/docs/copilot/customization/hooks

**配置位置**：
- `.github/hooks/` 目录
- 支持项目级和用户级配置

**支持的生命周期事件**：
- `SessionStart` - 会话开始
- `UserPromptSubmit` - 用户提交prompt
- `PreToolUse` - 工具使用前
- `PostToolUse` - 工具使用后
- `PreCompact` - 上下文压缩前
- `SubagentStart` - 子Agent启动
- `SubagentStop` - 子Agent停止
- `Stop` - 任务完成

**配置示例**：
```json
// .github/hooks/format.json
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

### 2.2 Claude Code

**支持状态**：✅ 官方稳定功能

**官方文档**：
- 使用指南：https://code.claude.com/docs/en/hooks-guide
- API参考：https://code.claude.com/docs/en/hooks

**配置位置**：
- `~/.claude/hooks/` - 用户级hooks
- `.claude/hooks/` - 项目级hooks
- 支持通过 `/hooks` 菜单管理

**支持的生命周期事件（20+）**：
- 会话管理：`SessionStart`, `SessionEnd`
- 工具调用：`PreToolUse`, `PostToolUse`, `PostToolUseFailure`
- 权限控制：`PermissionRequest`, `PermissionDenied`
- 子Agent：`SubagentStart`, `SubagentStop`
- 任务管理：`TaskCreated`, `TaskCompleted`, `Stop`, `StopFailure`
- 上下文管理：`PreCompact`, `PostCompact`, `InstructionsLoaded`
- 文件监控：`FileChanged`, `CwdChanged`, `ConfigChange`
- 交互事件：`Elicitation`, `ElicitationResult`, `Notification`
- 工作区管理：`WorktreeCreate`, `WorktreeRemove`, `TeammateIdle`

**特色功能**：
- **异步hooks**：后台执行，不阻塞主流程
- **HTTP hooks**：可调用远程API
- **Prompt-based hooks**：用自然语言定义规则
- **Agent-based hooks**：用AI Agent处理hook逻辑

**异步hooks示例**：
```json
{
  "hooks": {
    "FileChanged": [
      {
        "type": "command",
        "command": "npm test",
        "async": true
      }
    ]
  }
}
```

### 2.3 Codex CLI

**支持状态**：✅ Experimental（实验中）

**官方文档**：https://developers.openai.com/codex/hooks

**启用方式**：在`config.toml`中开启feature flag
```toml
[features]
codex_hooks = true
```

**支持的生命周期事件**：
- `SessionStart` - 会话开始
- `PreToolUse` - 工具使用前
- `PostToolUse` - 工具使用后
- `UserPromptSubmit` - 用户提交prompt
- `Stop` - 会话停止

**功能特点**：
- 可发送对话到自定义日志/分析引擎
- 扫描prompt中的API密钥泄露
- 自动创建持久化记忆
- 在对话停止时运行自定义验证器

**限制**：
- 目前Windows支持暂时禁用
- 需要显式开启feature flag

### 2.4 Trae

**支持状态**：❓ 不明确

**调研结果**：
根据公开资料，Trae主要强调以下功能：
- MCP（Model Context Protocol）支持，有专用市场
- 自定义AI模型接入
- Agent自主任务处理
- 项目规则文件（类似Cursor Rules）

**但官方文档中未找到类似Cursor Hooks的"生命周期钩子"机制**。Trae的配置更多集中在：
- 项目级规则文件（`.trae/rules`等）
- MCP服务器集成
- 而非执行期钩子（execution-time hooks）

---

## 三、功能对比总结

| 工具 | Hooks支持 | 成熟度 | 配置方式 | 事件数量 | 特色功能 |
|------|-----------|--------|----------|----------|----------|
| **Cursor** | ✅ Beta | ⭐⭐⭐ | `.cursor/hooks.json` | 6个核心 | 命令/Prompt双模式，团队分发，UI调试面板 |
| **VSCode Copilot** | ✅ Preview | ⭐⭐ | `.github/hooks/` | 8个 | 与GitHub深度集成，设置UI友好 |
| **Claude Code** | ✅ 稳定 | ⭐⭐⭐⭐⭐ | `~/.claude/hooks/` | 20+ | 异步hooks、HTTP hooks、Agent hooks、/hooks菜单 |
| **Codex CLI** | ✅ Experimental | ⭐⭐ | `config.toml` | 5个 | 云端任务集成，需feature flag |
| **Trae** | ❓ 不明确 | - | 项目规则文件 | - | MCP生态为主，无原生执行期钩子 |

---

## 四、关键结论与建议

### 4.1 核心发现

1. **Cursor Hooks是目前Beta阶段最完善的钩子系统**，特别擅长**命令执行管控**（`beforeShellExecution`），可以精确拦截/批准shell命令。

2. **Claude Code的Hooks最全面**，事件类型最多（20+），支持异步和HTTP调用，适合复杂企业级自动化场景。

3. **VSCode Copilot的Hooks正在追赶**，API设计与Cursor类似，适合已经使用Copilot生态的开发者。

4. **Codex CLI的Hooks还在早期**，功能相对简单，主要面向CLI使用场景。

### 4.2 工具选型建议

| 需求场景 | 推荐工具 | 原因 |
|----------|----------|------|
| 命令安全管控 | Cursor / Claude Code | `beforeShellExecution` 可拦截危险命令 |
| 复杂自动化流程 | Claude Code | 20+事件、异步支持、HTTP hooks |
| 代码格式化/质量 | Cursor / VSCode Copilot | `afterFileEdit` 自动触发 |
| 团队规范统一 | Cursor / VSCode Copilot | 项目级hooks.json可版本控制 |
| MCP生态集成 | Trae | 专用MCP市场，一键安装 |

### 4.3 迁移注意事项

- **Cursor ↔ VSCode Copilot**：配置格式高度相似，主要是路径差异（`.cursor/` vs `.github/`）
- **Cursor/VSCode ↔ Claude Code**：Claude Code事件更丰富，但核心概念（Pre/Post/Stop）一致
- **无Hooks功能的工具**：可考虑通过MCP服务器实现部分类似功能，但无法达到执行期拦截的粒度

---

## 五、参考资源

### 官方文档
- Cursor Hooks: https://cursor.com/docs/hooks
- VSCode Copilot Hooks: https://code.visualstudio.com/docs/copilot/customization/hooks
- Claude Code Hooks Guide: https://code.claude.com/docs/en/hooks-guide
- Claude Code Hooks Reference: https://code.claude.com/docs/en/hooks
- Codex CLI Hooks: https://developers.openai.com/codex/hooks

### 经验分享
- GitButler深度解析: https://blog.gitbutler.com/cursor-hooks-deep-dive
- 知乎Cursor Rules教程: https://zhuanlan.zhihu.com/p/1906795650714146104

---

*报告完成*
