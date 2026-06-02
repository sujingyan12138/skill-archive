# LLM Wiki 摄取（Ingest）参考文档

基于 Karpathy LLM Wiki 模式的摄取操作详细指南。

---

## 核心概念

**摄取（Ingest）** 是 LLM Wiki 三大操作之一（Ingest / Query / Lint）。  
它将一份新的原始资料「编译」进 wiki，建立关联、更新索引、追加日志。

---

## 目录结构约定

```
<kb_root>/
├── raw/                  # 原始来源（只读，LLM 永不修改）
│   ├── articles/         # 文章、网页剪藏
│   ├── papers/           # 论文、报告
│   ├── notes/            # 个人笔记、会议记录
│   └── assets/           # 图片等媒体
├── wiki/                 # LLM 编译产物（LLM 完全拥有）
│   ├── index.md          # 全局目录（每页一行摘要）
│   ├── log.md            # 操作日志（append-only）
│   ├── concepts/         # 概念类页面
│   ├── entities/         # 实体类页面（人物、产品、组织）
│   └── comparisons/      # 对比分析页面
└── CLAUDE.md             # Schema：告诉 LLM wiki 结构和约定
```

---

## 核心原则：raw/ 存放完整原文，不做摘要，一律翻译为中文

**这是本 skill 最重要的原则。**

raw/ 目录是知识库的「源代码」层，必须满足：

1. **完整**：存入 raw/ 的是完整原始内容，不是摘要。不是「提炼」「总结」「提取要点」。
   - 一篇 5000 词的文章 → 存入 raw/ 的是 5000 词完整中文翻译

2. **原始**：raw/ 中的内容代表原始来源本身。LLM 只负责翻译语言，不压缩信息。

3. **中文**：无论原始内容是什么语言，存入 raw/ 时一律翻译为中文。

4. **不可修改**：LLM 永不编辑 raw/ 目录。如果需要更正，只能新增一个版本，并在 log.md 中注明。

**为什么这样做？**
- 完整原文才能支持未来可能的重新编译（如 wiki 结构改变）
- 中文存储保证 LLM 在编译 wiki 时基于统一的语言基础
- 翻译本身是一种深度理解过程，有助于 LLM 建立更准确的概念关联

---

## Wiki 页面 Frontmatter 标准

每个 wiki 页面必须包含以下 YAML frontmatter：

```yaml
---
title: "页面标题"
confidence: 0.9        # 0.0-1.0，LLM 对内容准确性的自我评估
last_ingested: 2026-04-11
sources:
  - raw/articles/example.md   # 来源文件路径（支持追溯）
stale: false           # 如果来源文件已变更，设为 true
---
```

---

## 摄取操作标准流程（SOP）

执行摄取时，按以下顺序操作：

### 步骤 1：读取并翻译来源
- 读取原始来源文件内容
- 将完整内容翻译为中文（不摘要、不压缩）
- 存入 `raw/` 对应分类目录（articles/papers/notes 等）
- 如果是图片：提取文本内容 + 视觉信息，存入 assets/

### 步骤 2：读取 raw/ 原文，提取关键信息
- 读取刚存入的 raw/ 文件（这就是编译的输入）
- 提取核心概念（通常 3-10 个）
- 提取关键实体（人物/产品/组织/地点）
- 识别与现有 wiki 的关联点
- 标记潜在的矛盾信息

### 步骤 3：更新 wiki 层

**3a. 创建或更新概念页面**
- 路径：`wiki/concepts/<概念名>.md`
- 包含：定义、来源、与其他概念的关系
- 使用 `[[concept-name]]` 格式添加内部链接

**3b. 创建或更新实体页面**
- 路径：`wiki/entities/<实体名>.md`
- 包含：描述、相关概念、来源引用

**3c. 如需要，创建对比分析页面**
- 路径：`wiki/comparisons/<比较主题>.md`
- 当来源包含多个方案/产品/方法的比较时使用

### 步骤 4：更新 wiki/index.md
在对应分类下添加新页面条目：
```
- [[concepts/新概念]] — 一句话摘要（来源：raw/xxx.md）
```

### 步骤 5：追加操作日志
在 `wiki/log.md` 追加：
```markdown
## [YYYY-MM-DD HH:MM] ingest | <来源文件名>

- 原始处理：raw/articles/xxx.md（翻译为中文）
- 新增页面：`wiki/concepts/xxx.md`
- 更新页面：`wiki/entities/yyy.md`（+N 个新关联）
- 关键发现：<简短描述>
```

---

## 一份来源应影响多少 wiki 页面？

Karpathy 原文：**「一个来源可能涉及 10-15 个 wiki 页面」**

这意味着：
- 不要只创建一个「全文摘要」页面
- 要将来源中的每个独立概念、实体拆解为单独页面
- 每个页面专注于一个主题，但通过链接互连

---

## 处理矛盾信息

当新来源与现有 wiki 内容矛盾时：
1. **不要直接覆盖**旧内容
2. 在相关 wiki 页面添加「矛盾注记」部分：
   ```markdown
   ## ⚠️ 矛盾注记
   - [旧来源] 认为：...
   - [新来源，2026-04-11] 认为：...
   - 待解决：需要更多来源确认
   ```
3. 将页面 frontmatter 中的 `confidence` 降低
4. 在 log.md 中记录矛盾

---

## 查询答案归档（Query → Wiki）

当用户提出查询并得到高质量答案时，将答案归档为新 wiki 页面：
- 路径：`wiki/concepts/<问题主题>.md` 或 `wiki/comparisons/<对比主题>.md`
- 在 frontmatter 的 sources 中注明 `query: <原始问题>`
- 在 log.md 中记录：`query | <问题摘要> → 已归档为 wiki/<页面路径>`

---

## 规模扩展指南

| wiki 规模 | 推荐检索方式 |
|-----------|------------|
| < 50 篇  | 直接读取 index.md，LLM 全量处理 |
| 50-150 篇 | index.md + 按类别分区读取 |
| > 150 篇 | 引入 qmd 混合搜索（BM25 + 向量） |

---

## 防幻觉措施

1. **每个 wiki 声明必须有来源追溯**（frontmatter sources 字段）
2. **置信度评分**：LLM 推断的内容 confidence ≤ 0.7，有直接来源 ≥ 0.85
3. **隔离 vault**（Steph Ango 建议）：人写的笔记与 LLM wiki 放不同目录/vault
4. **定期 Lint**：运行健康检查，标记 stale 页面

---

## 常用命令速查

```bash
# 初始化新知识库
python ingest.py init ~/my-kb

# 查看待处理文件
python ingest.py scan ~/my-kb

# 查看整体状态
python ingest.py status ~/my-kb

# 记录摄取日志（同时标记文件为已处理）
python ingest.py log ~/my-kb "ingest | article-name.md"

# 检测已变更文件
python ingest.py stale ~/my-kb
```
