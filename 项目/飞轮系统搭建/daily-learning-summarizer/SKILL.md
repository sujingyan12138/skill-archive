---
name: daily-learning-summarizer
description: Use when the user gives a non-English-learning learning link, video, article, tutorial, podcast, Douyin/Bilibili/YouTube link, or other lightweight study material and wants it summarized into the same-day daily summary in 生活/复盘 instead of the full raw -> wiki -> outputs flywheel. Trigger on "帮我总结这个视频并写进今天的每日总结", "这个链接我刚学习了", "轻量总结一下", "日常学习资料记到复盘里". If the material is about English, CET-6, vocabulary, roots/affixes, grammar, pronunciation, or English short videos, use english-learning-summarizer instead.
tags:
  - 工具
  - 复盘
  - 学习总结
  - 轻量资料
---

# Daily Learning Summarizer

## Purpose

把"今天临时看过、值得留痕、但不值得完整进入飞轮系统"的学习内容，稳定写进当天每日总结。

默认规则：用户直接给出学习链接时，先按轻量学习处理；只有用户明确说这是重要资料、需要长期追溯或后续输出，才升级到完整飞轮并进入 `raw/`。

它适合处理：

- B站、抖音（非英语）、YouTube 等学习视频
- 技术博客、教程、资讯文章
- 临时看到的课程、访谈、播客
- 用户明确说"不想重处理，但想总结一下"的资料

如果材料是**英语学习**、六级备考、词汇、词根词缀或英语短视频，改用 `english-learning-summarizer`，写入 `学习/Eng/`。两个 skill 的底层视频处理管线相同（下载 → 音频转写 + 画面 OCR），区别只在于输出位置。

它不负责完整摄取原始资料，也不默认更新 `raw/`、`wiki/` 或 `outputs/`。

## Trigger Priority

用户直接丢学习链接时，先判断内容类型：

- 英语、六级、词根词缀、语法、发音、英语短视频：立即改用 `english-learning-summarizer`
- 其它学习视频、技术教程、访谈、课程、博客：使用本 skill

视频类资料默认要走**本地转写 + 画面 OCR**双通道处理，不要只根据标题、简介或分享文案写"视频内容总结"。

## Read First

1. `SOUL.md`
2. `CLAUDE.md`
3. 当天已有的 `生活/复盘/* YYYY-MM-DD.md`，如果存在
4. 必要时读取：
   - `生活/复盘/复盘.md`
   - `主页.md`
   - `仓库地图.md`

## Routing Rules

### 写进每日总结

当资料满足这些条件时，写入 `生活/复盘/主题关键词 YYYY-MM-DD.md`：

- 用户刚刚学习过
- 主要目标是留痕、总结、反思
- 不需要保留完整原文或完整字幕
- 暂时不需要抽象成 wiki 概念页
- 不需要生成正式成果文档

### 升级进完整飞轮

只有用户明确要求、需要长期追溯，或已经把相关文件放进 `raw/` 时，才升级为正式资料流程。可以把这些信号作为提醒，但不要替用户自动升级：

- 用户说这份资料很重要、以后会反复用
- 内容足够长，值得保留完整原文、字幕或转写
- 资料会支撑后续写作、项目、研究或系统建设
- 需要可追溯引用来源
- 需要更新 `wiki/` 或产出 `outputs/`

升级路径是：

1. 转成完整 Markdown
2. 放入 `raw/articles/`、`raw/papers/` 或 `raw/notes/`
3. 附件放入 `raw/assets/`
4. 再决定是否更新 `wiki/` 和 `outputs/`

## Recommended Workflow

1. 确认当天日期，先用 `生活/复盘/* YYYY-MM-DD.md` 查找当天已有文件
2. 如果当天文件已存在：更新，不要重复新建；如果当天学习/复盘内容已经覆盖多个主题，必要时把文件重命名为多个事件关键词的综合标题，方便检索；如果不存在，根据当天主线生成 8 到 20 字主题关键词，再新建 `生活/复盘/主题关键词 YYYY-MM-DD.md`
3. 获取资料元信息（标题、作者、链接、发布时间、时长）
4. 如果是视频类，按下方「Video Handling」的流程获取完整内容（下载 → 音频转写 + 画面 OCR）。画面获取采用“规律抽帧 + 智能补帧”：先按视频类型设定基础间隔，再在转写中出现关键节点时补截画面。
5. 写入一段轻量学习总结（基于转写和画面 OCR 两个来源）
6. 给出对当前仓库、项目、学习状态的启发
7. 写一个最小下一步，除非用户只要求纯摘要
8. 用户给出自己的“小感悟”并要求写入每日复盘时，先保留用户原文，再写整理版、启发和下一步
9. 避免把外部资料标题直接写成 Obsidian 双链，除非确实要创建同名笔记

## Video Handling (B站 & 抖音)

处理 B站或抖音（非英语）视频时，底层管线相同：下载 → 音频转写 + 画面 OCR → 总结 → 清理。

**核心原则**：视频的信息有三个来源——音频（人声讲解）、画面截图（软件界面、参数面板、效果对比、板书布局）和画面 OCR（可识别的文字）。只看转写不看画面，等于只听了半个视频。三个来源必须全部查看后再动笔。

画面截图不固定死为每 10 秒一张。默认由 AI 判断：

- 轻量学习：基础间隔 20 秒左右，并在“注意、这里、对比、总结、关键、流程、参数、界面、数据”等转写节点补截少量关键帧。
- 重要飞轮：基础间隔 10 到 15 秒，并补截更多关键节点。
- 口播/访谈类：可以降低截图频率，但仍需抽查画面和 OCR。
- 游戏、软件教程、PPT、图表、设计/视觉案例：提高截图密度，保留关键画面。

英语视频走 `english-learning-summarizer`，非英语视频走此流程。

### 抖音视频

与非英语抖音视频的流程与英语视频完全相同，只是输出到 `生活/复盘/` 而非 `学习/Eng/`：

```bash
# 轻量学习默认快档：解析 → 下载 → 转写 → 关键帧 OCR
python tool/scripts/english_video_flywheel.py "<share text or url>" --preset fast

# 重要资料、后续要反复追问时，再用精确档
python tool/scripts/english_video_flywheel.py "<share text or url>" --preset precise
```

工具链说明：`english_video_flywheel.py` 虽然名字带 "english"，但它本质上是"下载抖音视频 + 转写 + OCR"的通用工具，对非英语内容同样有效。

### B站视频

```bash
# 轻量学习默认快档：capture → 下载 → faster-whisper 转写 → 关键帧 OCR
python tool/scripts/bilibili_video_flywheel.py "<url or BVID>" --preset fast

# 重要资料、后续要反复追问时，再用精确档
python tool/scripts/bilibili_video_flywheel.py "<url or BVID>" --preset precise
```

这一步会完成：B站 API 元信息抓取 → 下载 → faster-whisper 转写 → 规律关键帧 + 智能补帧 + OCR。轻量学习默认 `fast`，重要飞轮再用 `precise`。

**B站下载链路说明**：

B站使用 **DASH 分片格式**——视频流和音频流分别被切成数百个 200KB-1MB 的 `.m4s` 碎片。`bilibili_video_flywheel.py` 内部调用 yt-dlp 时自动加 `--concurrent-fragments 8`，同时下载 8 个碎片，消除串行等待。对 ~17MB 视频（~30+ 碎片）可提速 4-8 倍。

**yt-dlp B站下载陷阱**：

- 不要指定 `-f` 格式选择器——B站高清格式需要登录。flywheel 已内置正确的无格式选择器调用
- 不要加 `--user-agent` 模拟移动端 —— yt-dlp 会跳到 `m.bilibili.com` 导致错误
- 如果下载超时，flywheel 已内置重试逻辑

### 共享的清理逻辑

处理完成后，`tool/video_downloads/` 和 `tool/video_captures/` 中的对应临时文件必须删除：

- 抖音：`python tool/scripts/cleanup_english_video.py {aweme_id}`
- B站：手动删除 `tool/video_downloads/{bvid}.mp4` + `tool/video_captures/` 下所有相关文件（capture .md, transcript .md, keyframes .jpg, OCR .json）
- 笔记中不引用已删除的本地路径，保留平台原始链接即可

## Temporary File Cleanup

`tool/video_downloads/` 和 `tool/video_captures/` 是**临时处理站**，不是持久存储。处理完轻量学习资料后，下载的视频、音频、截图、转写中间文件都应该删除。

- 抖音：`python tool/scripts/cleanup_english_video.py {aweme_id}`
- B站：处理完成后手动删除对应文件
- 笔记中不要引用已删除的本地文件路径，保留平台原始链接即可

## Daily Summary Template

写入每日总结时，优先使用下面结构：

```markdown
## 今天学习的资料

- 标题：**资料标题**
- 链接：资料链接
- 来源：作者或平台
- 主题：关键词
- 依据状态：已下载视频并用 faster-whisper 转写 + 关键帧 OCR

## 视频画面信息

画面中出现的幻灯片/板书/代码/图表等视觉内容（基于关键帧 OCR）：
- ...
- ...

## 资料核心内容总结

用自己的话总结 3 到 5 个要点。不要只写音频讲的内容，画面中的图表、代码、板书同样要纳入。

## 对我当前系统/项目的启发

## 下一步

只写一个很小的动作。
```

## Writing Priorities

- 轻量，但不能敷衍
- 用户自己的原话优先保留，整理版放在原文之后
- 优先写"我学到了什么"和"这对我有什么用"
- 视频类必须同时纳入音频转写和画面 OCR 信息；截图频率由 AI 依据视频类型和关键节点判断，不机械固定每 10 秒
- 不把日常学习内容硬塞进 `wiki/`
- 如果信息来源不完整，要诚实标注
- 文件名采用 `主题关键词 YYYY-MM-DD.md`；如果当天有多个学习事件，文件名应提炼多个事件的综合关键词，而不是只沿用第一条资料的主题
