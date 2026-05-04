# 配置文档索引

> 本文档索引了 Uni-Rec-Challenge 项目中所有配置和安装指南。

## 文档列表

| 工具/主题 | 文档 | 最后更新 | 说明 |
|----------|------|----------|------|
| **OpenRouter Usage Proxy** | [openrouter-usage-proxy-setup-guide.md](./openrouter-usage-proxy-setup-guide.md) | 2026-05-04 | OpenRouter 用量监控工具安装与配置完整指南 |

---

## 按类别分类

### 监控与统计工具

- [OpenRouter Usage Proxy 安装与配置](./openrouter-usage-proxy-setup-guide.md)
  - 透明代理 + Web 仪表板
  - 记录用量到 SQLite
  - 实时查看 tokens、cost、model 等信息

### OpenRouter 相关知识

从 [openrouter-usage-proxy-setup-guide.md](./openrouter-usage-proxy-setup-guide.md) 中可以了解：

1. **Activity 数据延迟**：1 天（J-1 规则）
2. **第三方实时工具对比**：CostGoat、OpenRouterWidget、OpenRouter Usage Monitor 等
3. **Node.js 版本兼容性**：better-sqlite3 与 Node 版本的对应问题
4. **免费模型测试**：tencent/hy3-preview:free 等

---

## 如何使用配置记录 Agent

当完成一个有价值的配置过程后，可以说：

```
"把上面我们完整的对话过程中的有用知识记录成为一个md文档"
```

Trae AI Assistant 会：
1. 回顾最近对话，提取关键信息
2. 创建结构化的 markdown 文档
3. 保存到 `docs/` 目录
4. 更新本索引文件

详细配置记录规范见：[../trae_config.yaml](../trae_config.yaml)

---

## 文档模板

所有配置文档应遵循以下结构：

```markdown
# [工具名] 安装与配置指南

## 目录
## 背景与问题
## 安装过程
## 测试与验证
## 使用指南
## 常见问题
## 参考资料
```

详细模板见：[../trae_config.yaml](../trae_config.yaml)

---

## 更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-05-04 | 初始创建索引，添加 openrouter-usage-proxy 配置文档 |

---

**维护者**：Trae AI Assistant  
**最后更新**：2026-05-04
