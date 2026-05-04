# Hooks 机制实现日志记录方案调研结论

> 记录时间：2026-04-19
> 背景：探讨如何使用 Hooks、Sub-Agent、Rules 或 Prompt 实现调研结果的自动化文档记录

---

## 一、问题定义

**需求**：每次完成调研任务后，自动或半自动地将结果写入 Markdown 文档，或记录进开发日志。

**核心诉求**：
1. 减少人工操作，避免遗漏
2. 保持文档格式一致性
3. 支持不同 AI 编程工具（Cursor、Trae 等）

---

## 二、三种实现方案对比

### 2.1 Hooks 机制 ✅ **最推荐（自动化首选）**

**原理**：在 AI Agent 生命周期的特定节点（如 `stop` 事件）自动触发自定义脚本。

**配置示例**（Cursor/Claude Code）：
```json
{
  "version": 1,
  "hooks": {
    "stop": [
      {
        "command": "sh -c 'python3 scripts/save_research.py \"$RESEARCH_TOPIC\" \"$OUTPUT_FILE\"'",
        "env": {
          "RESEARCH_TOPIC": "{{session.topic}}",
          "OUTPUT_FILE": "docs/research/{{date}}-{{topic}}.md"
        }
      }
    ]
  }
}
```

**优点**：
- ✅ 完全自动化，无需人工干预
- ✅ 每次会话结束自动触发
- ✅ 可以访问会话上下文
- ✅ 可集成到 CI/CD 流程

**缺点**：
- ❌ 需要编写脚本处理输入数据
- ❌ 需要维护 hooks 配置
- ❌ **Trae 不支持**

**适用工具**：Cursor、Claude Code、VSCode Copilot（预览版）

---

### 2.2 Sub-Agent 模式 ✅ **次推荐（复杂任务）**

**原理**：通过调用专门的 Sub-Agent 处理复杂的多步骤任务。

**配置示例**：
```markdown
<!-- .cursor/rules/01-research-workflow.md -->
当你完成一次调研任务后：

1. **调用 SaveResearch Sub-Agent**
   ```
   /task SaveResearch
   Input: {{research_content}}
   Output: docs/research/{{date}}-{{topic}}.md
   Template: templates/research-report.md
   ```
```

**Sub-Agent 伪代码**：
```typescript
export default {
  name: "SaveResearch",
  async execute(input: ResearchInput) {
    // 1. 加载模板
    const template = await loadTemplate('templates/research-report.md');
    // 2. 格式化内容
    const formatted = formatResearch(input.content, template);
    // 3. 保存文件
    const filename = `${getDate()}-${slugify(input.topic)}.md`;
    await writeFile(`docs/research/${filename}`, formatted);
    // 4. 更新索引
    await updateIndex(filename, input.topic);
    return { success: true, file: filename };
  }
};
```

**优点**：
- ✅ 更灵活，可处理复杂逻辑
- ✅ 可复用，多项目共享
- ✅ 可人工确认后再执行

**缺点**：
- ❌ 需要显式调用
- ❌ 配置相对复杂
- ❌ **Trae 支持有限**

**适用工具**：Cursor、Claude Code

---

### 2.3 Rules / Prompt 模式 ⚠️ **基础方案（保底）**

**原理**：通过规则文件定义标准操作流程，依赖 AI 的遵循能力。

**配置示例**：
```markdown
<!-- .cursor/rules/99-post-research.md -->
# 调研后处理规则

每次完成调研任务后，你必须：

1. **创建文档**
   - 文件名格式：`search_{topic}_{date}.md`
   - 存放位置：`/Users/xiazhiwei/Uni-Rec-Challenge/`

2. **文档结构**
   ```markdown
   # {调研主题}
   > 调研时间：{date}
   
   ## 一、核心发现
   ## 二、详细分析
   ## 三、结论与建议
   ## 四、参考资源
   ```

3. **确认完成**
   - 回复用户："调研结果已保存至 {filepath}"
```

**优点**：
- ✅ 最简单，无需额外配置
- ✅ **跨平台兼容**（所有 AI 工具都支持）
- ✅ 易于理解和维护

**缺点**：
- ❌ 依赖 AI 的"自觉性"，可能遗漏
- ❌ 无法强制执行
- ❌ 无法自动化后续操作

**适用工具**：所有工具（Cursor、Trae、Claude Code、Copilot）

---

## 三、推荐方案：分层混合架构 🎯

```
┌─────────────────────────────────────────┐
│  Layer 3: Hooks (自动化执行)              │
│  - 会话结束后自动触发                     │
│  - 调用 Sub-Agent 或脚本                  │
├─────────────────────────────────────────┤
│  Layer 2: Sub-Agent (复杂逻辑)            │
│  - 格式化内容                             │
│  - 应用模板                               │
│  - 多步骤处理                             │
├─────────────────────────────────────────┤
│  Layer 1: Rules (规范约束)                │
│  - 提醒执行保存操作                        │
│  - 定义文档标准                            │
│  - 作为 fallback                          │
└─────────────────────────────────────────┘
```

### 具体实现步骤

**Step 1: Rules（基础保障）**
```markdown
<!-- .cursor/rules/99-research-cleanup.md -->
# 调研任务收尾规范

每次完成调研后，执行以下检查清单：

- [ ] 是否已保存为 Markdown 文档？
- [ ] 文件名是否符合 `search_{topic}_{date}.md` 格式？
- [ ] 是否包含完整的调研报告结构？
- [ ] 是否更新了相关索引？

如果未完成，请立即执行 `/save-research` 命令。
```

**Step 2: Sub-Agent（核心逻辑）**
```json
// .cursor/hooks.json
{
  "version": 1,
  "hooks": {
    "stop": [
      {
        "command": "cursor-agent /save-research",
        "condition": "session.tags.includes('research')"
      }
    ]
  }
}
```

**Step 3: 自动化脚本（可选增强）**
```bash
#!/bin/bash
# scripts/auto-archive.sh
# 每天自动归档旧的调研文档
find docs/research -name "*.md" -mtime +30 -exec mv {} archive/ \;
```

---

## 四、针对 Trae 的特殊方案

由于 **Trae 不支持 Hooks**，推荐以下方案：

### 方案 A：纯 Rules（推荐）

```markdown
<!-- .trae/rules/research-workflow.md -->
# 调研工作流

## 触发条件
当用户要求"调研"、"搜索"、"查询"等操作时激活。

## 执行流程
1. 执行调研任务
2. **强制步骤**：将结果写入 `search_{topic}_{date}.md`
3. **强制步骤**：回复用户时包含文件路径

## 输出模板
必须严格使用以下模板...
```

### 方案 B：MCP + 外部服务

```json
// .trae/mcp.json
{
  "servers": {
    "research-archive": {
      "command": "node",
      "args": ["mcp-servers/research-archive.js"]
    }
  }
}
```

---

## 五、最终结论

| 方案 | 自动化程度 | 实现复杂度 | 适用工具 | 推荐度 |
|------|-----------|-----------|---------|-------|
| **Hooks** | ⭐⭐⭐⭐⭐ | 中等 | Cursor, Claude Code, Copilot | 🥇 |
| **Sub-Agent** | ⭐⭐⭐⭐ | 较高 | Cursor, Claude Code | 🥈 |
| **Rules** | ⭐⭐⭐ | 低 | **所有工具** | 🥉 |
| **MCP** | ⭐⭐⭐⭐ | 中等 | Trae, Claude Code | 🥈 |

### 选型建议

| 使用场景 | 推荐方案 |
|---------|---------|
| **Cursor / Claude Code 用户** | Hooks + Sub-Agent 混合方案 |
| **Trae 用户** | 纯 Rules + 手动确认 |
| **追求最大兼容性** | 纯 Rules 方案 |
| **企业级安全合规** | Hooks + 审计日志 |

---

## 六、参考文档

- [Hooks 机制深度调研报告](./search_trae_kimi2.5.md)

---

*记录时间：2026-04-19*
