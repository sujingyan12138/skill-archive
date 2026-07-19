---
name: english-learning-summarizer
description: Immediately use when the user gives any English-learning video/link or English study material, especially 抖音/Douyin/TikTok/Bilibili/YouTube vocabulary clips, root/affix explanations, CET-6 material, pronunciation/grammar videos, or asks to summarize daily English study into 学习/Eng. Trigger on "抖音英语学习链接", "英语视频", "词根/词缀", "六级词汇", "我今天学了这个英语视频", "帮我把这个词根视频总结到 Eng". Do not answer from title/share text alone; first run the local video capture/transcription workflow.
tags:
  - 工具
  - 英语
  - 六级
  - 词汇
  - 学习总结
---

# English Learning Summarizer

## Purpose

把英语学习视频、六级词汇、词根词缀、语法和发音材料稳定沉淀到 `学习/Eng/`。

这个技能关注语言学习本身：准确还原视频实际讲到的内容，保留词汇拆解、发音、例句、板书记忆抓手和复习动作。它不写入 `学习/速看/` 或 `生活/复盘/`。

## Read First

1. `SOUL.md`
2. `CLAUDE.md`
3. `tool/视频学习统一处理规范.md`，视频类任务必须完整读取并遵循
4. `学习/Eng/index.md`
5. 当天已有的 `学习/Eng/* YYYY-MM-DD.md`
6. 涉及词根、词缀或词族时读取 `学习/Eng/词根词缀积累.md`

## Trigger Priority

消息同时包含视频/链接信号和以下任一英语学习信号时，优先使用本技能：

- 英语、六级、CET-6、单词、词根、词缀
- 语法、发音、介词、例句、阅读词汇
- “总结到 Eng”“写进英语笔记”“今天学了这个英语视频”

普通非英语学习材料改用 `daily-learning-summarizer`。

## Video Standard

所有英语学习视频默认执行 `tool/视频学习统一处理规范.md`，并使用 `precise` 预设。必须同时获得并查看：

1. 完整音频转写，用于口头讲解、发音和例句。
2. 关键帧截图，用于板书布局、手势、表格和视觉记忆方法。
3. 画面 OCR，用于单词拆解、字幕、标注和图表文字。

用户明确要求只按文案粗略记录时，可以降低来源等级，但必须标注“未核验完整视频，仅依据现有文案”，不能写成已经观看并理解完整视频。

## Standard Workflow

1. 判断英语学习主题，确认当天日期并查找已有 `学习/Eng/* YYYY-MM-DD.md`。
2. 按共享规范使用 `precise` 生成来源包，完整阅读转写、查看关键帧并核对 OCR。
3. 写入或更新 `学习/Eng/英语主题关键词 YYYY-MM-DD.md`。
4. 笔记包含来源信息、画面信息、核心词根/词汇、视频实际使用的记忆策略、六级启发和一个最小复习任务。
5. 如果材料涉及可复习的词根、词缀或词族，同步更新 `学习/Eng/词根词缀积累.md`。
6. 按共享规范清理临时文件，并告诉用户创建或更新了哪些文件。

## Daily Note Requirements

- 只写视频实际讲到的单词、解释、例句和教学角度。
- 视频讲了几层含义就保留几层，不擅自简化成单一词典义。
- 优先记录让人记住的画面、比喻、拆词方式和语境。
- 明显转写错误要结合音频、画面和上下文校正。
- 如果补充视频没讲的同词族词或语法知识，标注“以下为体系补充，非视频内容”。
- 每次只给一个很小的复习动作，避免把笔记写成新的学习负担。

## Vocabulary Accumulation Rules

更新 `词根词缀积累.md` 时：

- 使用稳定的词根或词缀标题，避免同一主题重复建卡。
- 保留核心画面、词义层次、视频来源和记忆抓手。
- 将具体单词放到对应含义下面，不把推断写成视频原意。
- 已有同词根卡片时更新原卡，而不是创建第二份。

## English-Specific Traps

### 把体系补充写成视频原意

只写视频实际讲到的内容。扩展词族、搭配或词源时明确标注来源边界。

### 只记词典释义

这个技能的价值是保留视频独有的教学方法。必须记录记忆画面、词根拆解、例句语境或板书结构，而不只是列中文释义。

### 忽略视觉教学

词根视频常在画面中展示拆解图、单词对比和口诀。共享规范中的关键帧查看不能跳过。

## Daily Note Template

```markdown
---
tags:
  - 英语
  - 六级
  - 学习总结
---

# 英语主题关键词 YYYY-MM-DD

## 今日学习来源

- 平台：
- 链接：
- 视频 ID：
- 作者：
- 发布时间：
- 时长：
- 主题：
- 依据状态：已完成音频转写、关键帧查看和画面 OCR，处理后已清理临时文件。

## 视频画面信息

- 板书、图表、拆词、手势或关键文字：

## 今日学到的词根/词汇

### 词根或核心记忆点

- 核心含义：
- 记忆抓手：
- 视频教学方法：
- 视频实际例词：

## 记忆策略

## 六级备考启发

## 今日复习任务
```

## Vocabulary Card Template

```markdown
## 词根：核心含义

- 核心画面：
- 记忆抓手：
- 视频来源：

### 第一层含义
- 视频实际讲到的例词：

### 第二层含义
- 视频实际讲到的例词：

复习提示：
> 一个很小的复习动作。
```

## Writing Priorities

- 服务六级备考、词汇理解和长期复习。
- 记忆抓手优先于堆砌词典释义。
- 三源处理、工具命令、缓存、证据和清理规则统一以 `tool/视频学习统一处理规范.md` 为准。
- 文件名保持 `英语主题关键词 YYYY-MM-DD.md`，主题在前、日期在后。
