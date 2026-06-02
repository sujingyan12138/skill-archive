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

把每日英语学习视频、词汇讲解、词根词缀材料，稳定沉淀到 `学习/Eng/`。

这个 skill 专门服务用户的六级备考，不走普通 `生活/复盘`。用户直接丢英语学习链接时，写入 `学习/Eng/英语主题关键词 YYYY-MM-DD.md`。

## Read First

1. `SOUL.md`
2. `CLAUDE.md`
3. `学习/Eng/index.md`，如果存在
4. 当天已有的 `学习/Eng/* YYYY-MM-DD.md`，如果存在
5. `学习/Eng/词根词缀积累.md`，如果材料涉及词根、词缀或词族

## 默认标准：所有英语视频都必须走完整本地处理

用户分享的每一个英语学习视频，默认都必须下载到本地，经过完整的**音频转写 + 视频画面 OCR**双重处理后，再基于这些可核验来源撰写笔记。

**为什么两个来源都要**：
- **音频转写（faster-whisper）**：捕获语言讲解、发音、例句朗读
- **画面 OCR（关键帧截图）**：捕获板书、PPT 文字、词根拆解图、记忆口诀等视觉教学信息——这些在音频里根本不存在

两个来源信息互补，缺一不可。不存在"轻量留痕"或"只看分享文案即可"的情况。

## Trigger Priority

如果用户消息里同时出现以下任意信号，必须优先使用本 skill，而不是先按普通聊天回答：

- 抖音、Douyin、B站、Bilibili、YouTube、短视频、分享链接
- 英语、六级、CET-6、单词、词根、词缀、语法、发音、介词
- "总结到 Eng"、"写进英语笔记"、"今天学了这个英语视频"

先跑本地工具链拿到转写和关键帧，再写 `学习/Eng/`。除非用户明确说"不用下载/不用精确，只按文案粗略记录"，否则不要跳过转写和画面分析。

## Standard Workflow (6 Steps, Must Follow)

### Step 1: 下载视频并获取完整内容（音频 + 画面）

**禁止**使用 WebFetch 直接抓取抖音/B站页面 —— 这些平台封锁外部 HTTP 访问。

必须使用本地工具链，一次性完成解析、下载、转写、截图和 OCR：

```bash
# 抖音英语视频
python tool/scripts/english_video_flywheel.py "<share text or url>" --preset precise

# B站英语视频
python tool/scripts/bilibili_video_flywheel.py "<url or BVID>" --preset precise
```

两个脚本的底层管线相同（下载 → 转写 → OCR），`--preset precise` 是唯一应使用的预设。画面获取采用“规律抽帧 + 智能补帧”：保留基础关键帧，同时在转写中出现重点、对比、步骤、板书、参数、界面等节点时补截额外画面。这一步会产生两个**同等重要**的信息来源：
- **音频 → 完整逐字稿**（faster-whisper 转写）：捕获口头讲解
- **画面 → 关键帧 OCR**（规律抽帧 + 智能补帧 + RapidOCR）：捕获板书、单词拆解、图表等视觉信息，这些在音频中不可见

### Step 2: 完整阅读转写 AND 查看关键帧截图 AND 阅读 OCR

读取 flywheel 输出的文件（全部在 `tool/video_captures/` 下）：
- 转写 + OCR：`tool/video_captures/{date}-{aweme_id}_transcript.md`
- 关键帧截图：`tool/video_captures/{aweme_id}_frame_*.jpg` 与 `*_smart_*.jpg`
- 视频元信息：`tool/video_captures/{date}-{desc}.md`

**三个信息来源必须全部查看，缺一不可**：

1. **从头到尾读完整转写**——理解口头讲解内容
2. **逐张查看关键帧截图**——理解画面中的软件界面、板书布局、参数面板、前后效果对比、手势指向等。这些视觉信息 OCR 文字根本无法体现，但对理解教学内容至关重要。这一步消耗 token 但不可跳过
3. **逐帧阅读 OCR 摘要**——提取画面中 OCR 能识别的文字（板书、字幕、标注）

对于词根词缀类英语视频，画面中有手写拆解、单词对比表格、记忆口诀图。对于工具教程类视频，画面中有 UI 布局、参数设置位置、生成效果对比。**不看画面写笔记 = 只听了半个视频**。

### Step 3: 撰写每日学习笔记

写入 `学习/Eng/英语主题关键词 YYYY-MM-DD.md`。先按 `* YYYY-MM-DD.md` 查找当天已有文件。

要求：
- 基于 Step 2 读取的**转写 + 画面 OCR**两个来源撰写
- 标注依据状态为"已下载视频并用 faster-whisper 转写，已每 10 秒抽取关键帧做 OCR"
- 包含：来源信息、核心词根/词汇（含画面中出现的视觉内容）、记忆策略、六级备考启发、复习任务
- 保留视频的教学方法和记忆抓手，不要只堆词典释义
- 如果视频画面中有重要的板书或图表，在笔记中描述或引用

### Step 4: 同步词根词缀积累

如果视频涉及可复习的词根、词缀或词族，更新 `学习/Eng/词根词缀积累.md`。

要求：
- 只写视频**实际讲到**的单词和解释
- 视频讲了几层含义就写几层
- 保留视频独有的记忆抓手或教学角度（包括画面中展示的记忆方法）
- 如果想补充视频没讲的同词族词，明确标注"以下为体系补充，非视频内容"

### Step 5: 清理临时文件

```bash
python tool/scripts/cleanup_english_video.py {aweme_id}
```

删除：视频（.mp4）、关键帧截图（.jpg）、OCR 缓存（.json）、转写中间文件（_transcript.md）、元信息捕获文件。`tool/video_downloads/` 和 `tool/video_captures/` 是临时处理站，不是持久存储。

笔记中不引用已删除的本地文件路径，保留平台原始链接即可。

### Step 6: 汇报结果

告诉用户哪些文件被创建/更新了，以及临时文件已清理。

## Performance: Whisper Daemon

每次冷启动 `video_to_md.py` 都要重新加载 Whisper 模型（small ~25s）。启动常驻 daemon 消除此开销：

```bash
python tool/scripts/whisper_daemon.py          # 启动（一次）
python tool/scripts/whisper_daemon.py --status # 查看
python tool/scripts/whisper_daemon.py --stop   # 停止
```

`video_to_md.py` 会自动检测 daemon——运行中走 daemon（免加载），否则回退本地加载。

## Traps & Lessons Learned

### Trap 1: WebFetch 抓取抖音/B站
**症状**：WebFetch 返回空内容或安全拦截页面。
**正确做法**：永远用 `douyin_learning_capture.py` 或 `english_video_flywheel.py`。

### Trap 2: 不下载视频就开始写笔记
**症状**：只拿到分享文案，却在笔记里写"根据视频内容"，或者基于标题猜测视频内容然后补充大量自己的推断。
**正确做法**：必须先跑完整 flywheel 拿到转写和 OCR，再写笔记。没有转写 = 不能写"根据视频"。

### Trap 3: 补充视频没讲的内容却不标注
**症状**：基于词根学术知识补充视频没讲的单词（如 comport, opportune, sport），写成视频原意。
**正确做法**：只写视频实际讲到的。想补充词族知识时，明确标注"以下为体系补充，非视频内容"。

### Trap 4: 临时文件堆积
**症状**：下载的视频、截图、转写文件留在磁盘上。
**正确做法**：Step 5 必须执行。如果某次处理失败，排查后手动清理。

### Trap 5: 只看转写不看画面 OCR
**症状**：写了完整的逐字稿总结，却忽略了画面截图中的板书、拆解图、对比表等视觉信息。结果笔记里只有"说了什么"，没有"展示了什么"。
**正确做法**：Step 2 必须同时读转写和 OCR 帧。画面中经常有音频里完全没提到的关键内容（手写词根拆解、单词对比、记忆口诀等）。

### Trap 6: yt-dlp 下载 B站 视频时指定 `-f` 参数或忘记并发
**症状**：`yt-dlp -f "best[height<=720]"` 或 `-f "worst"` 报错 `Requested format is not available`；或者下载能跑但很慢。
**原因**：B站高清格式需要登录，未登录时格式过滤会排除所有可用格式。另外 B站使用 DASH 分片格式，默认逐个碎片串行下载，网络等待时间长。
**正确做法**：不传 `-f` 参数，加 `--concurrent-fragments 8` 并行下载 DASH 碎片。详见 `daily-learning-summarizer` skill 的「B站视频」章节。

## Daily Note Template

```markdown
---
tags:
  - 英语
  - 六级
  - 学习总结
  - 词根词缀
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
- 依据状态：已下载视频并用 faster-whisper 转写，已每 10 秒抽取关键帧做 OCR。笔记基于完整转写与画面 OCR。处理后已清理临时文件。

## 视频画面信息

画面中出现的板书/图表/关键文字（基于 OCR）：
- ...
- ...

## 今日学到的词根/词汇

### 词根/核心记忆点

- 核心含义：
- 记忆抓手：
- 视频教学方法（含画面展示的记忆方式）：

## 记忆策略

## 六级备考启发

## 今日复习任务
```

## Vocabulary Card Template

写入 `词根词缀积累.md` 时，使用这种卡片：

```markdown
## port：携带 + 口/门户（两层核心含义）

- 核心画面：从 airport 出发——飞机 + 港口 → 人和货物进出搬运的通道
- 记忆抓手：port 有两层——① 携带/搬运（carry）；② 口/门户/通道（gate/portal）
- 视频来源：抖音 @作者名，主题为"xxx"，已下载并用 faster-whisper 转写 + 关键帧 OCR

### 第一层：port = 携带/搬运
- report：re-(回) + port(带) → 把消息带回来 → 报告
- ...

### 第二层：port = 口/门户/通道
- airport：航空港 → 机场
- ...

复习提示：
> ...
```

## Writing Priorities

- 所有英语视频默认走完整本地处理流程（音频转写 + 画面 OCR，两者同等重要）
- 服务六级备考，尤其是词汇、阅读和长期复习
- 优先把"记忆抓手"写清楚，而不是堆词典释义
- 每次只给一个很小的复习动作
- 只写视频实际讲到的内容，补充要标注
- 处理后必须清理临时文件
- 文件名 `英语主题关键词 YYYY-MM-DD.md`，主题在前、日期在后
