# System Prompt Analysis — Reference Workspace

本目录汇总了 IDE / CLI agent 系统提示词的提取结果与三方参考仓库，便于离线对照学习。

## 目录结构

| 路径 | 说明 |
|---|---|
| `system-prompts-and-models-of-ai-tools/` | x1xhlol 维护，35 个 IDE/CLI agent 的系统提示词与工具 schema |
| `cchistory/` | badlogic 的 npm 抓包工具，可批量重放历代 Claude Code 版本并落盘 |
| `claude-code-system-prompts/` | Piebald-AI 维护，从 Claude Code 编译产物里直接抽出 110+ 子提示词 + 系统 reminder + 子 agent prompt |
| `extracted_copilot_gpt5.2_system_prompt.md` | 从用户的 `export_copilot.json` 解析出的 Copilot panel/editAgent 系统提示词（GPT-5.2，约 29KB） |

## 提示词获取方式（按主动性递增）

1. **公开收集仓库** — 直接 clone 上面的三个仓库；最快但可能滞后版本。
2. **IDE 自带的 Debug View（无侵入）**
   - VSCode/Copilot：`Developer: Open Chat Debug View` → `Export` → 得到 JSON（即用户提供的方案）。
   - Cursor：用户文件夹下 `~/Library/Application Support/Cursor/logs/` + Output 面板。
   - Trae/Antigravity：底部状态栏的 chat log 导出按钮。
3. **运行时反向代理（最权威）**
   - Anthropic 官方 SDK：`export ANTHROPIC_BASE_URL=http://localhost:8000`，启动 mitmproxy reverse 模式即可拦下含 `system` 字段的 JSON 请求。
   - OpenAI 系（Copilot/Cursor 多数模型）：把 `OPENAI_BASE_URL` 指向本地代理，或在系统层使用 mitmproxy + 安装 CA 证书。
   - 适配工具：`claude-trace`（Anthropic 协议专用）、`proxyclawd`（带 TUI/Web）、`mitmweb`（通用）。
4. **二进制反编译** — Claude Code 是单文件 minified JS，Piebald 仓库的 `tools/updatePrompts.js` 即针对该文件做字符串提取；npm 包每次更新会自动跑。
5. **重放抓取** — `cchistory <version>` 会下载老版本 npm 包，patch 掉版本检查后跑一次最简单的请求触发系统提示词输出。

## 我从你的 export_copilot.json 学到了什么

- 格式：`{exportedAt, totalPrompts, totalLogEntries, prompts[], mcpServers[]}`
- 每个 `prompt` 包含若干 `logs`，其中 `name == 'panel/editAgent'` 的条目是真正发往模型的 chat completion，`requestMessages.messages` 即 OpenAI 标准消息数组（role 为枚举数字：0=system, 1=user/assistant 拼接的多模态片段）。
- 有效系统提示词是 messages[0]，长度 28,964 字符 / 约 7-8K tokens。
- 模型记录为 `gpt-5.2`，title 子任务用的是 `gpt-4o-mini-2024-07-18`，metadata 还附带 `timeToFirstToken / usage / requestId` 等可观测字段。
