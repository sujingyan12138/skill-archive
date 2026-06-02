---
name: llm-ingest
description: "This skill should be used when the user wants to add new documents to a Karpathy-style LLM Wiki knowledge base. It implements the Ingest phase of the Ingest/Query/Lint cycle: reading raw source files, compiling them into structured wiki Markdown pages, updating the index, and appending to the operation log. Key features: Raw storage rule - always store the complete original text in raw/ (never summarize), translated to Chinese. Use this skill when the user says things like 摄取这篇文章, 把这个加入知识库, ingest this paper, 更新我的 wiki, 处理 raw 目录里的新文件, or asks to build or maintain a personal knowledge base powered by LLMs. Also use when initializing a new knowledge base directory structure."
---

# LLM Wiki 摄取技能（llm-ingest）

基于 Andrej Karpathy 的 LLM Wiki 模式，将原始资料「编译」进结构化知识库。

---

## 核心定位

**摄取（Ingest）= 将一份新来源编译进 wiki，建立关联、更新索引、追加日志。**

这是 LLM Wiki 三大核心操作（Ingest / Query / Lint）中的第一环，也是知识积累的起点。

---

## 触发场景

- 用户说「把这篇文章/论文/笔记加入我的知识库」
- 用户说「处理 raw/ 里的新文件」
- 用户说「ingest 这个来源」
- 用户希望初始化一个新的 LLM Wiki 知识库
- 用户希望了解哪些文件还没有被处理

---

## 知识库结构（必须遵守）

```
<kb_root>/
├── raw/        ← 原始来源（只读，永不修改）
│   ├── articles/    ← 文章类
│   ├── papers/      ← 论文类
│   ├── notes/       ← 笔记类
│   └── assets/      ← 图片等资产
├── wiki/       ← LLM 编译产物（LLM 完全拥有）
│   ├── index.md     ← 全局目录
│   ├── log.md       ← append-only 操作日志
│   ├── concepts/    ← 概念类页面
│   ├── entities/    ← 实体类页面
│   └── comparisons/ ← 对比分析页面
└── CLAUDE.md   ← Schema 配置（约定 + 工作流）
```

**严格原则**：
- `raw/` 只读，LLM 永不编辑
- `wiki/` 由 LLM 完全拥有，人类不直接手动编辑
- 每个 wiki 页面必须可追溯到 `raw/` 中的来源文件

---

## 执行摄取的标准流程

### 第 1 步：使用脚本了解当前状态

运行辅助脚本（位于此 skill 的 `scripts/ingest.py`）来获取准确的状态信息：

```bash
# 如果是新知识库，先初始化
python <skill_scripts_dir>/ingest.py init <kb_root>

# 查看待处理文件列表
python <skill_scripts_dir>/ingest.py scan <kb_root>

# 查看整体状态摘要
python <skill_scripts_dir>/ingest.py status <kb_root>
```

`<skill_scripts_dir>` 是此 skill 的 `scripts/` 目录绝对路径。

### 第 2 步：读取来源文件

- 读取 `raw/` 中用户指定（或 scan 发现的）文件
- 对于图片：先读文本部分，再单独读取图片文件获取视觉信息
- 识别文件类型（文章/论文/笔记/数据/代码）以决定提取策略

### 第 3 步：将完整原文存入 raw/（一律翻译为中文）

**这是核心原则：raw/ 目录存放的是完整原始内容，不做任何摘要压缩。**

- 读取原始来源文件后，将完整内容**翻译为中文**，存入 `raw/` 对应分类目录
- raw/ 中的文件**只写一次**，LLM 永不修改

### 第 4 步：提取 + 编译到 wiki

从 raw/ 中的完整中文原文出发，提取以下内容并写入 wiki 页面：

| 提取对象 | 目标路径 | 页面类型 |
|---------|---------|---------|
| 核心概念（3-10 个） | `wiki/concepts/<name>.md` | 定义 + 来源 + 关联链接 |
| 关键实体（人/产品/组织） | `wiki/entities/<name>.md` | 描述 + 相关概念 + 来源 |
| 多方案比较 | `wiki/comparisons/<topic>.md` | 结构化对比表格 |
| 综合洞察（可选） | `wiki/concepts/<insight>.md` | 跨来源综合分析 |

**关键**：一份来源通常应影响 **10-15 个 wiki 页面**，而不只是一个摘要页面。

每个 wiki 页面使用标准 frontmatter：
```yaml
---
title: "页面标题"
confidence: 0.9
last_ingested: YYYY-MM-DD
sources:
  - raw/articles/example.md
stale: false
---
```

使用 `[[concept-name]]` 格式在页面内添加内部链接（Obsidian wiki-link 格式）。

### 第 5 步：更新 wiki/index.md

在对应分类下追加新页面条目，格式：
```
- [[concepts/new-concept]] — 一句话摘要（来源：raw/xxx.md）
```

### 第 6 步：追加操作日志 + 更新状态

使用脚本追加日志（同时自动标记文件为「已摄取」）：

```bash
python <skill_scripts_dir>/ingest.py log <kb_root> "ingest | <来源文件名>"
```

或手动在 `wiki/log.md` 追加：
```markdown
## [YYYY-MM-DD HH:MM] ingest | <来源文件名>

- 新增页面：`wiki/concepts/xxx.md`
- 更新页面：`wiki/entities/yyy.md`
- 关键发现：<简短描述>
```

---

## 处理特殊情况

**矛盾信息**：当新来源与现有 wiki 内容矛盾时，不要直接覆盖。在相关页面添加「⚠️ 矛盾注记」部分，降低 confidence 值，并在 log.md 记录。

**查询答案也归档**：用户提问后得到的高质量答案，也应作为新 wiki 页面保存。这让每次探索都成为知识积累。

**批量摄取**：一次处理多个文件时，按相关性分批处理，保持每批都有完整的 index 和 log 更新。

---

## 参考文档

详细的操作规范、SOP 流程、矛盾处理方法、规模扩展指南，参见：
`references/ingest-guide.md`（此 skill 的 references 目录）

---

## 脚本能力速查

`scripts/ingest.py` 提供以下命令（无需安装额外依赖，纯标准库）：

| 命令 | 功能 |
|------|------|
| `init <kb_root>` | 初始化知识库目录结构（raw/、wiki/、CLAUDE.md 等） |
| `scan <kb_root>` | 列出待处理文件（新增 + 已变更） |
| `status <kb_root>` | 显示整体状态摘要（文件数、页面数、最近日志） |
| `log <kb_root> <msg>` | 追加操作日志，若消息含 `ingest \|` 则自动标记文件 |
| `stale <kb_root>` | 检测自上次摄取以来内容已变更的文件 |
