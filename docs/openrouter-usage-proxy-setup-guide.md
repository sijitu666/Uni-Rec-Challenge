# OpenRouter Usage Proxy 安装与配置指南

> 本文档记录了 OpenRouter 用量监控工具 `openrouter-usage-proxy` 的完整安装、配置和验证过程。

## 目录

- [背景与问题](#背景与问题)
- [OpenRouter Activity 数据延迟](#openrouter-activity-数据延迟)
- [第三方实时监控工具](#第三方实时监控工具)
- [openrouter-usage-proxy 安装过程](#openrouter-usage-proxy-安装过程)
- [测试与验证](#测试与验证)
- [使用指南](#使用指南)
- [附录：可用模型示例](#附录可用模型示例)

---

## 背景与问题

### 问题 1：OpenRouter Activity 更新延迟

**问**：OpenRouter 更新的个人 activity 模型用量是不是有延迟？

**答**：**是的，延迟时间为 1 天（24 小时）**。

#### 官方说明

根据 [OpenRouter 官方 API 文档](https://openrouter.ai/docs/api/api-reference/analytics/get-user-activity)：

> Returns user activity data grouped by endpoint for the **last 30 (completed) UTC days**.

关键词是 "**completed** UTC days" —— 只返回已经完成的 UTC 日期数据。

#### 第三方证实

GitHub 项目 [olivierpetitjean/OpenRouterWidget](https://github.com/olivierpetitjean/OpenRouterWidget) 文档明确说明：

> **"Today's usage will appear tomorrow. This is an OpenRouter API limitation."**
>
> （今天的使用量会在明天显示。这是 OpenRouter API 的限制。）

> **"The activity endpoint only returns completed UTC days."**
>
> （Activity 端点只返回已完成的 UTC 日期。）

#### 延迟原因

- OpenRouter 以 UTC 日期为单位统计和展示用量数据
- 当前正在进行的 UTC 日期（today）的数据不会实时显示在 activity 页面
- 必须等到 UTC 日期结束（即第二天）后，该日的数据才会出现在 API 和 activity 页面中

#### 实时用量替代方案

如需实时跟踪用量，可以使用：

1. **API 响应中的 `usage` 字段**（推荐）
   ```json
   {
     "usage": {
       "prompt_tokens": 194,
       "completion_tokens": 2000,
       "total_tokens": 2194,
       "cost": 0.2
     }
   }
   ```

2. **Live Usage Accounting**（2025 年 4 月更新）
   - OpenRouter 在每次 API 响应中实时返回 token 和成本数据
   - 无需额外 API 调用

---

### 问题 2：实时统计 OpenRouter 用量的第三方工具

虽然 OpenRouter 官方 activity 页面有 1 天延迟，但有以下第三方工具可以实现**实时或近实时**统计：

#### 🖥️ 桌面应用（最推荐）

| 工具 | 平台 | 功能 | 价格 |
|------|------|------|------|
| **CostGoat** ⭐ | macOS, Windows, Linux | 实时信用余额、低余额警报、使用趋势 | $9/月（7天免费试用） |
| **OpenRouter Usage Monitor** | macOS | 菜单栏实时显示、7天趋势、按模型分解 | App Store 下载 |
| **OpenRouterWidget** | Windows 10/11 | 消费图表、实时余额、Top 5 模型统计 | 免费（开源） |

#### 🌐 浏览器扩展

- **OpenRouter Balance 扩展**
  - 启动时实时获取余额
  - 余额低于 $1 时显示红色警告
  - 网址：https://cusmize.com/extensions/hpaolkhhoefnbjdgmgmfjdgmdbalgjlj

#### 🔧 开发者工具（本地代理/CLI）

| 工具 | 类型 | 特点 | GitHub |
|------|------|------|-------|
| **openrouter-usage-proxy** ⭐ | 透明代理 + Web 仪表板 | 拦截所有请求、记录到 SQLite、按 API key 统计 | [Loulen/openrouter-usage-proxy](https://github.com/Loulen/openrouter-usage-proxy) |
| **AI Consumption Tracker** | CLI + TUI | 多提供商支持、自动扫描 API keys | [rygel/AIUsageTracker](https://github.com/rygel/AIUsageTracker) |

#### 📊 企业级监控

| 工具 | 特点 | 适用场景 |
|------|------|----------|
| **Grafient** | 聚合所有路由模型的成本、token 使用量、请求量 | 需要预算警报的团队 |
| **SigNoz** (OpenTelemetry) | 使用 OpenTelemetry 跟踪、统一 traces/logs/metrics | 生产环境详细监控 |

---

## openrouter-usage-proxy 安装过程

### 工具简介

**openrouter-usage-proxy** 是一个透明中间件代理，用于：
- 拦截所有到 OpenRouter 的 API 调用
- 记录用量信息（model、tokens、costs、API keys）
- 通过 Web 仪表板显示分析数据
- 数据持久化到 SQLite 数据库

### 架构图

```
┌─────────────┐      ┌─────────────────┐      ┌──────────────┐
│   Client    │ ───▶ │  Proxy Server   │ ───▶ │  OpenRouter  │
│  (Your App) │ ◀─── │  (localhost:3000)│ ◀─── │     API      │
│ + API Key   │      │  (transparent)   │      │              │
└─────────────┘      └────────┬────────┘      └──────────────┘
                              │
                              │ logs usage
                              ▼
                     ┌─────────────────┐
                     │  SQLite DB      │
                     └────────┬────────┘
                              │
                              │ reads
                              ▼
                     ┌─────────────────┐
                     │  Web Dashboard  │
                     │ (localhost:3000) │
                     └─────────────────┘
```

### 步骤 1：克隆源码

```bash
cd /Users/xiazhiwei/Uni-Rec-Challenge
git clone https://github.com/Loulen/openrouter-usage-proxy.git
```

### 步骤 2：安装依赖（解决 Node 版本问题）

#### 问题：better-sqlite3 编译失败

初始尝试使用 Node 25.8.1 安装时遇到 `better-sqlite3` 原生模块编译错误：

```
npm error gyp ERR! build error 
npm error gyp ERR! stack Error: `make` failed with exit code: 2
npm error ImportError: dlopen(...): Symbol not found: _XML_SetAllocTrackerActivationThreshold
```

#### 解决方案：使用 Node 22 LTS

```bash
# 安装 Node 22
brew install node@22

# 使用 Node 22 的 npm 全局安装（跳过脚本先）
npm install -g openrouter-usage-proxy --ignore-scripts

# 然后用 Node 22 重新安装（这次会编译 better-sqlite3）
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
npm install -g openrouter-usage-proxy
```

**验证 Node 版本**：
```bash
node --version  # 应该显示 v22.22.2
```

### 步骤 3：启动服务

```bash
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
openrouter-proxy --server-port 3000
```

**预期输出**：
```
[cli] OpenRouter Usage Proxy starting...
[cli] Server port: 3000
[cli] Client port: 3000
[static] Serving static files from: /opt/homebrew/lib/node_modules/openrouter-usage-proxy/client/dist
[server] OpenRouter Usage Proxy running on http://localhost:3000
[server] Dashboard API: http://localhost:3000/api/logs
[server] Settings API: http://localhost:3000/api/settings
[server] API Keys API: http://localhost:3000/api/api-keys
[server] Proxy endpoint: http://localhost:3000/openrouter/api/v1/chat/completions
[cli] Unified mode: Dashboard at http://localhost:3000/
[cli] Ready! Press Ctrl+C to stop.
```

### 服务端点

| 服务 | URL | 说明 |
|------|-----|------|
| Web 仪表板 | http://localhost:3000/ | 查看用量日志和统计 |
| 代理 API | http://localhost:3000/openrouter/api/v1/* | 转发请求到 OpenRouter |
| 日志 API | http://localhost:3000/api/logs | 查询记录的用量数据 |
| 统计 API | http://localhost:3000/api/logs/stats | 获取汇总统计 |

---

## 测试与验证

### 测试 1：查询空日志

```bash
curl -s http://localhost:3000/api/logs | python3 -m json.tool
```

**预期结果**：`[]`（空数组，因为还没有请求）

### 测试 2：发送请求到代理（失败示例）

#### 尝试 1：模型地区不可用（403）
```bash
curl -X POST http://localhost:3000/openrouter/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
    "model": "openai/gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

**结果**：`{"error":{"message":"This model is not available in your region.","code":403}}`

#### 尝试 2：模型不存在（404）
```bash
curl -X POST http://localhost:3000/openrouter/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
    "model": "meta-llama/llama-3.1-8b-instruct:free",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

**结果**：`{"error":{"message":"No endpoints found for meta-llama/llama-3.1-8b-instruct:free.","code":404}}`

### 测试 3：发送成功请求 ✅

```bash
curl -X POST http://localhost:3000/openrouter/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
    "model": "tencent/hy3-preview:free",
    "messages": [{"role": "user", "content": "Hi! Just say hello."}],
    "stream": false
  }'
```

**成功响应**：
```json
{
  "id": "gen-1777914353-Nd1ra51a92PDfZiFI1dv",
  "model": "tencent/hy3-preview-20260421:free",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Hello! 😊"
    }
  }],
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 149,
    "total_tokens": 167,
    "cost": 0
  }
}
```

### 验证：代理是否捕获了请求

#### 查询日志
```bash
curl -s "http://localhost:3000/api/logs?limit=10" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total captured requests: {len(data)}')
for d in data:
    print(f'ID: {d[\"id\"]}, Status: {d[\"status_code\"]}, Model: {d[\"model\"]}, Tokens: {d[\"total_tokens\"]}, Cost: {d[\"cost\"]}')
"
```

**输出**：
```
Total captured requests: 5
ID: 5, Status: 200, Model: tencent/hy3-preview-20260421:free, Tokens: 167, Cost: 0
ID: 4, Status: 404, Model: unknown, Tokens: None, Cost: None
ID: 3, Status: 404, Model: unknown, Tokens: None, Cost: None
ID: 2, Status: 404, Model: unknown, Tokens: None, Cost: None
ID: 1, Status: 403, Model: unknown, Tokens: None, Cost: None
```

#### 查询统计
```bash
curl -s http://localhost:3000/api/logs/stats | python3 -m json.tool
```

**输出**：
```json
{
  "request_count": 5,
  "total_tokens": 167,
  "total_cost": 0
}
```

### 验证结论 ✅

**openrouter-usage-proxy 确实成功捕获了请求用量！**

| 功能 | 状态 | 说明 |
|------|------|------|
| 捕获成功请求（200） | ✅ | 完整记录 model、tokens、cost |
| 捕获失败请求（403/404） | ✅ | 记录 status_code、api_key_hash、request_path |
| 统计 API | ✅ | 正确汇总所有请求数据 |
| 日志 API | ✅ | 可按时间顺序查询所有请求 |

---

## 使用指南

### 1. 启动代理服务

```bash
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
openrouter-proxy --server-port 3000
```

### 2. 查看可视化仪表板

打开浏览器访问：**http://localhost:3000/**

### 3. 在应用中使用代理

将 OpenRouter 的请求地址从：
```
https://openrouter.ai/api/v1/...
```

改为代理地址：
```
http://localhost:3000/openrouter/api/v1/...
```

#### 示例：curl 请求
```bash
curl -X POST http://localhost:3000/openrouter/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_OPENROUTER_API_KEY" \
  -d '{
    "model": "tencent/hy3-preview:free",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

#### 示例：Claude Code
```bash
export OPENROUTER_BASE_URL=http://localhost:3000/openrouter/api
claude
```

#### 示例：VS Code (RooCode)
1. 打开设置（Ctrl+, 或 Cmd+,）
2. 搜索 "RooCode" 设置
3. 勾选 "Use custom base URL"
4. 输入：`http://localhost:3000/openrouter/api/v1`
5. 保存并重启

### 4. 数据库位置

SQLite 数据库文件在：
```
/Users/xiazhiwei/Uni-Rec-Challenge/openrouter-usage-proxy/server/usage.db
```

或直接通过全局安装路径：
```
/opt/homebrew/lib/node_modules/openrouter-usage-proxy/server/usage.db
```

### 5. API 查询接口

#### 获取所有日志
```bash
curl http://localhost:3000/api/logs
curl "http://localhost:3000/api/logs?limit=50"  # 限制返回数量
```

#### 获取统计信息
```bash
curl http://localhost:3000/api/logs/stats
```

**响应示例**：
```json
{
  "request_count": 10,
  "total_tokens": 5000,
  "total_cost": 0.15
}
```

#### 按 API Key 统计
```bash
curl http://localhost:3000/api/api-keys
```

---

## 附录：可用模型示例

### 免费模型（测试用）

| 模型 | 说明 | 状态 |
|------|------|------|
| `tencent/hy3-preview:free` | 腾讯混元 3 预览版 | ✅ 可用 |
| `poolside/laguna-xs.2:free` | Poolside 模型 | ⚠️ 隐私设置限制 |
| `x-ai/grok-4.3` | xAI Grok | 需验证 |
| `ibm-granite/granite-4.1-8b` | IBM Granite | 需验证 |

### 查询可用模型列表

```bash
curl -s "https://openrouter.ai/api/v1/models" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" | \
  python3 -c "import json, sys; data=json.load(sys.stdin); [print(m['id']) for m in data.get('data', [:10])]"
```

---

## 常见问题

### Q1: 为什么请求失败了？
- **403**：模型在你所在的地区不可用，尝试其他模型
- **404**：模型名称错误或该模型没有可用的端点
- **隐私设置**：某些模型需要在 https://openrouter.ai/settings/privacy 配置数据策略

### Q2: 为什么 tokens/cost 是 null？
- 只有成功的请求（status 200）才会记录 tokens 和 cost
- 失败的请求只记录基本信息（status_code、api_key_hash 等）

### Q3: 如何停止服务？
- 在运行服务的终端按 `Ctrl+C`

### Q4: 如何查看更详细的日志？
- 日志存储在 SQLite 数据库中，可以用任意 SQLite 客户端打开查看
- 或使用提供的 API 接口查询

---

## 参考资料

- **openrouter-usage-proxy GitHub**: https://github.com/Loulen/openrouter-usage-proxy
- **OpenRouter 官方文档**: https://openrouter.ai/docs
- **OpenRouter API 参考**: https://openrouter.ai/docs/api/api-reference/introduction
- **Activity API 文档**: https://openrouter.ai/docs/api/api-reference/analytics/get-user-activity

---

## 更新记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-05-04 | 1.0 | 初始版本，记录完整安装和验证过程 |

---

**文档作者**：Trae AI Assistant  
**最后更新**：2026-05-04
