---
name: daily-learning-summarizer
description: Use when the user gives a non-English-learning learning link, video, article, tutorial, podcast, Douyin/Bilibili/YouTube link, or other lightweight study material and wants a deep AI summary saved to 学习/速看 instead of the full raw -> wiki -> outputs flywheel. Trigger on "帮我总结这个视频", "这个链接我刚学习了", "轻量总结一下", "认真学习一下", "日常学习资料记到速看里". Never place AI-generated learning summaries in 生活/复盘; if the material is about English, CET-6, vocabulary, roots/affixes, grammar, pronunciation, or English short videos, use english-learning-summarizer instead.
tags:
  - 工具
  - 速看
  - 学习总结
  - 轻量资料
---

# Daily Learning Summarizer

## Purpose

把“今天临时看过、值得留痕、但不值得完整进入飞轮系统”的非英语学习内容，稳定写进 `学习/速看/`。

轻量指不默认进入 `raw -> wiki -> outputs`，不是浅层摘要。对视频、访谈、教程、演讲和长文，继续向下提炼逻辑、假设、模型、局限与行动启发。

适用内容：

- B站、抖音、YouTube 等非英语学习视频
- 技术博客、教程、资讯文章
- 课程、访谈、播客
- 用户明确说“不想重处理，但想认真总结”的材料

英语、六级、词汇、词根词缀、语法和发音材料改用 `english-learning-summarizer`。完整重要来源改用 `llm-ingest` 或升级到正式飞轮。

## Read First

1. `SOUL.md`
2. `CLAUDE.md`
3. `tool/视频学习统一处理规范.md`，视频类任务必须完整读取并遵循
4. 当天已有的 `学习/速看/* YYYY-MM-DD.md`
5. 必要时读取 `学习/速看/index.md`、`主页.md` 和 `仓库地图.md`

## Routing Rules

### 写进速看

材料同时满足以下条件时，写入 `学习/速看/主题关键词 YYYY-MM-DD.md`：

- 用户刚刚学习过，目标是总结、留痕和反思
- 不需要长期保留完整原文或完整字幕
- 暂时不需要抽象成 wiki 概念页
- 不需要生成正式成果文档

同一天已有相关速看文件时优先更新，不重复创建。当天内容跨越多个主题时，可把文件名提炼成多个事件的综合关键词。

### 升级完整飞轮

出现以下信号时提醒用户考虑升级，但不要擅自升级：

- 用户明确说资料重要、以后会反复使用
- 需要长期追溯、引用或支撑写作与研究
- 需要保留完整原文、字幕或来源包
- 需要更新 `wiki/` 或产出 `outputs/`

升级路径：完整来源进入 `raw/`，再决定更新哪些 `wiki/` 页面和 `outputs/`。

## Recommended Workflow

1. 判断内容是否属于非英语轻量学习；英语内容立即切换到 `english-learning-summarizer`。
2. 确认日期并查找当天已有的 `学习/速看/* YYYY-MM-DD.md`。
3. 获取标题、作者、链接、发布时间、时长等元信息。
4. 视频类任务严格执行 `tool/视频学习统一处理规范.md`：按价值选择 `fast` 或 `precise`，获取音频转写、关键帧截图和画面 OCR，并实际查看三个来源。
5. 拆解核心论点、证据类型、论证方式、隐含前提和主要受众。
6. 至少用两种视角交叉理解，例如支持者/批评者、初学者/专家或短期/长期。
7. 用第一性原理检查观点依赖的基础事实，再用剃刀原则压缩真正要解决的问题。
8. 写入凝练的速看总结，同时纳入音频和画面信息。
9. 给出一个与用户当前系统、项目或学习状态相关的最小下一步，除非用户只要求纯摘要。
10. 按共享规范清理临时文件并汇报创建或更新的笔记。

## Deep Summary Requirements

- **核心结论**：材料最想让读者改变的判断是什么。
- **论证链条**：作者使用案例、数据、经验、对比还是逻辑推理。
- **隐含前提**：观点依赖哪些背景、价值判断和受众处境。
- **多视角分析**：至少从两个角度解释同一观点。
- **第一性原理**：拆到基础事实，判断哪些结论稳定、哪些只是经验。
- **剃刀结论**：用一句话概括本质问题。
- **局限与误读**：说明适用边界，避免把案例当万能规则。
- **行动化启发**：留下一个能立即执行的小动作。

质量要求：

- 每个总结点最多 3 句，第一句先给明确判断。
- 不写“很有启发”“值得学习”等没有信息增量的空话。
- 来源不足或包含推断时明确标注，不把常识扩展冒充原材料内容。
- 视频类任务的证据声明、失败边界和清理规则以共享规范为准。

## Quick-Look Summary Template

```markdown
## 今天学习的资料

- 标题：
- 链接：
- 来源：
- 主题：
- 依据状态：

## 视频画面信息

- 画面中的界面、板书、代码、图表或效果对比：

## 资料核心内容总结

写 3 到 5 个“观点 + 为什么 + 意味着什么”的要点。

## 深层逻辑与隐含前提

- 论证链条：
- 隐含前提：
- 最容易被误解的地方：

## 多视角分析

- 支持者/创作者视角：
- 批评者/受众视角：
- 对我当前项目或学习的意义：

## 第一性原理与剃刀结论

- 第一性原理：
- 剃刀结论：
- 适用边界：

## 下一步

只写一个很小的动作。
```

## Personal Reflection Boundary

如果用户提供自己的“小感悟”并明确要求写入 `生活/复盘/`，使用 `YYYY-MM-DD 今日感悟.md`，完整保留用户原文后再按要求整理。不要把当前 AI 学习总结混入个人感悟区。

## Compression Style

- 把故事压成原则。
- 把清单压成模型。
- 把情绪压成判断。
- 把下一步压成今天能完成的动作。
