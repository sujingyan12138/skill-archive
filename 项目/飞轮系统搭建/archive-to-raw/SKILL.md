---
name: archive-to-raw
description: Archive a URL, article, blog post, paper, report, AI conversation, note, local document, audio, or video into the correct raw/ area of this Obsidian flywheel without updating wiki. Use when the user says “帮我入库到 raw”, “归档原始资料”, “这个链接以后要提问”, “保存到 raw”, “只入库不摄取”, or provides a link/file and wants a complete, traceable source preserved for later questions. Route articles to raw/articles, papers/reports to raw/papers, conversations/notes to raw/notes, videos to raw/videos, and attachments to raw/assets; check duplicates and update the corresponding index.md.
---

# Archive to raw

把用户交给 AI 的链接或本地文件完整保存到 `raw/`。这一步只建立可追溯原始来源，不提炼概念、不更新 `wiki/`，也不调用 `llm-ingest` 完成正式摄取。

## 先确认边界

- 用户说“入库到 raw”“保存原始资料”“以后方便提问”时，执行本技能。
- 用户只想做日常学习总结时，转交英语或非英语学习总结技能，不默认进入 `raw/`。
- 用户说“摄取”“消化 raw”“更新 wiki”时，先确保来源已在 `raw/`，再使用 `llm-ingest`。
- 不创建或恢复已退役的 `资料/`。

## 路由

| 来源 | 目标 |
|---|---|
| 博客、文章、网页正文、教程 | `raw/articles/` |
| 论文、研究报告、白皮书、正式 PDF 报告 | `raw/papers/` |
| AI 对话导出、零散笔记、网页摘录 | `raw/notes/` |
| 视频、视频博客、以视听内容为主的链接 | `raw/videos/` |
| PDF/DOCX 原件、图片及文档附件 | `raw/assets/` |

默认自动判断。只有文章与报告的性质确实难以区分、且选择会明显影响后续使用时才询问用户。

## 标准流程

1. 读取仓库 `CLAUDE.md` 和目标 `raw/<category>/index.md`。
2. 对 URL 先查重；对本地文件检查源文件哈希或已有同名文件：

```powershell
python ".codex/skills/archive-to-raw/scripts/raw_intake.py" find --repo . --url "<URL>"
python ".codex/skills/archive-to-raw/scripts/raw_intake.py" find --repo . --file "<本地文件>"
```

3. 获取完整来源而不是摘要：
   - 网页保存标题、作者、发布时间、原始 URL、抓取时间和完整正文。
   - 非中文正文按仓库规则保存完整中文译文；能可靠取得原文时一并保留原文或原始附件。
   - 无法穿过登录、付费墙或反爬时，不得把标题、简介或搜索片段标成完整正文。说明限制并请求用户导出文件；只有用户接受时才保存 `status: partial` 的占位来源。
   - 知乎等直接请求返回 403 的网站，优先用现有浏览器会话打开目标页，按回答 ID 或文章主容器提取正文；不要把同页其他回答、推荐流或广告混入来源。
   - 浏览器已取得目标正文 HTML 时，优先用 `scripts/webpage_to_raw.py` 转 Markdown、本地化图片并更新索引，避免每次重写清理逻辑。
4. 先为目标生成不冲突的路径：

```powershell
python ".codex/skills/archive-to-raw/scripts/raw_intake.py" suggest --repo . --category articles --title "<标题>"
```

   - `articles`、`papers` 默认使用 `YYYY-MM-DD-标题.md`。
   - `notes` 默认保留用户文件名，不强制加日期，传入 `--no-date`。
   - `videos` 使用来源包目录，传入 `--directory`。
5. 写入或复制完整来源。Markdown frontmatter 至少包含：

```yaml
---
title: "来源标题"
source_type: article
source_url: "https://example.com/..."
author: "作者或 unknown"
published_at: "YYYY-MM-DD 或 unknown"
captured_at: "YYYY-MM-DD"
status: complete
language: zh
tags:
  - raw
---
```

6. 注册入口并验证：

```powershell
python ".codex/skills/archive-to-raw/scripts/raw_intake.py" register --repo . --path "<raw 内目标路径>" --title "<显示标题>"
python ".codex/skills/archive-to-raw/scripts/raw_intake.py" verify --repo . --path "<raw 内目标路径>"
```

7. 向用户报告保存路径、完整性、附件、索引更新结果，以及是否尚未摄取到 `wiki/`。

## 文档与本地文件

- Markdown/TXT：保留完整文字，必要时补齐元信息。
- PDF/DOCX/PPTX/HTML 等：原件复制到 `raw/assets/`，用仓库 `tool/scripts/docx_to_md.py` 转成 Markdown 后放入对应文章、论文或笔记目录。
- 图片引用改为指向 `raw/assets/` 的相对路径。
- 完整 AI 对话优先保持用户提供的文件名与原始顺序；不要擅自改写聊天内容。
- 重名时不覆盖。相同来源 URL 或相同哈希已经存在时，复用现有来源并补索引；不同内容使用脚本建议的递增名称。

## 网页提取的已验证路径

1. 先尝试网站专用 API/CLI 或普通只读请求；成功时直接取得正文。
2. 普通请求被 403、登录状态或动态渲染拦住时，改用现有浏览器会话，不要反复撞同一个接口。
3. 在页面中按来源稳定标识定位唯一主容器。例如知乎回答应核对 `data-zop` 中的 `itemId`、作者和问题标题，不能直接抓整个页面。
4. 只导出该主容器的 HTML，再运行：

```powershell
python ".codex/skills/archive-to-raw/scripts/webpage_to_raw.py" `
  --repo . --html-file "<临时正文.html>" --title "<标题>" `
  --url "<原始URL>" --author "<作者>" --published-at "<发布时间>"
```

5. 脚本会识别 `data-original`、`data-actualsrc`、`data-src` 等懒加载图片地址，把配图下载到 `raw/assets/`，再生成 Markdown 和更新两个索引。
6. 验收时检查正文首尾、章节数量、字符数、配图数、来源 URL、查重命中和索引命中。文件存在不等于内容完整。

## 视频与视频博客

视频为了以后能直接提问，不能只保存 URL 或 mp4：

1. 先读 `tool/视频学习统一处理规范.md`。
2. 在 `raw/videos/YYYY-MM-DD-主题/` 建立自包含来源包。
3. 尽可能保存：
   - `source-info.md`：标题、平台、作者、URL、抓取时间和完整性状态
   - 原始视频或音频
   - 完整音频转写
   - 关键帧及画面 OCR
4. 抖音、B 站优先复用仓库已有抓取和转写脚本；普通本地视频使用 `tool/scripts/video_to_md.py`。
5. 视频衍生的关键帧可留在视频来源包内以保持整体可迁移；其他文档附件统一进入 `raw/assets/`。
6. 下载受限时，明确 `status: partial`，不要声称已经形成可完整提问的来源包。

平台优先级：

- B站：复用 `tool/scripts/bilibili_video_flywheel.py`，下载器优先 `IDM`，失败再回退 `yt-dlp`。
- 抖音：复用 `douyin_learning_capture.py` 的元信息与 IDM/Python 下载逻辑，再统一交给 `video_to_md.py`。
- YouTube：优先复用已安装的 `yt-dlp`/IDM 下载能力，下载后交给 `video_to_md.py`。
- 小红书：先在真实浏览器中取得可验证的标题、作者和媒体地址；能交给 IDM 时复用 IDM，下载后仍走同一转写、关键帧和 OCR 管线。
- 不为不同平台复制四套后处理逻辑；平台层只负责“解析与下载”，后处理统一复用。

## 不要做

- 不更新 `wiki/`、`wiki/index.md` 或 `wiki/log.md`。
- 不把原始资料压缩成一篇 AI 摘要来代替全文。
- 不因“文件已放入 raw”就声称完成了 `llm-ingest`。
- 不为这个对话入口额外要求用户运行 EXE；用户给链接或文件路径即可。
