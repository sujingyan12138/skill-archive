---
name: flywheel-kb-copilot
description: Use when the user wants long-term help building, organizing, extending, auditing, or evolving this Obsidian flywheel knowledge base itself. Trigger on “巡检仓库”, “优化我的笔记仓库”, “继续完善我的飞轮系统”, “帮我整理知识库结构”, “看看什么该并入飞轮”, “把工作流做成 skill”, or requests to turn repeated collaboration patterns into reusable system assets.
tags:
  - 工具
  - 知识库
  - 飞轮系统
---

# Flywheel KB Copilot

## Purpose

这个 skill 用来支持“持续搭建知识库本身”，而不只是处理某一篇资料。

它关注的是：

- 仓库结构是否清晰
- 什么内容该进入飞轮、什么不该强行并入
- 哪些对话值得回流成长期资产
- 哪些规则应该写进 `SOUL.md`、`CLAUDE.md`、`学习/经历/`、`wiki/` 或 `outputs/`

## Read First

1. `SOUL.md`
2. `CLAUDE.md`
3. `主页.md`
4. `仓库地图.md`
5. `inspection/reports/` 中最新报告，如存在
6. 与本次任务最相关的区块：
   - 生活类：`生活/`
   - 学习类：`学习/`
   - 输入类：`raw/`
   - 知识类：`wiki/`
   - 输出类：`outputs/`
   - 工具类：`tool/`

## Core Principles

- 优先让系统更顺手，而不是更复杂
- 优先做稳定入口和可持续流程，而不是过度自动化
- 优先把“反复出现的高价值模式”写成资产
- 不把所有内容都硬塞进 `wiki/`
- 让 `生活 / 学习 / 资料 / 飞轮` 保持边界清楚但能互相回流

## Routing Rules

### 什么时候写进哪里

- `生活/`
  - 日常状态、个人整理、写作草稿、生活复盘
  - `生活/复盘/` 只放用户亲自写下的 `YYYY-MM-DD 今日感悟.md` 和固定的 `复盘.md`；AI 不在这里生成学习总结或项目摘要
- `学习/`
  - 技术知识、提示词、项目经历、排障经验、方法积累
  - 非英语日常学习视频、文章、教程等 AI 轻量总结写入 `学习/速看/主题关键词 YYYY-MM-DD.md`
- `raw/`
  - 正式原始资料入口，保存完整原始内容和可追溯来源；视频本体进 `raw/videos/`，可读转写稿进 `raw/articles/` 或 `raw/notes/`
  - 完整 AI 对话导出进入 `raw/notes/`；默认保留用户提供的文件名，不强制添加日期，并更新 `raw/notes/index.md`
  - 归档 AI 对话只保存原始来源，不自动把整段聊天写入 `wiki/`；提示词、稳定概念和用户原创感悟再按内容分别提炼
- `wiki/`
  - 已抽象、已概念化、适合反复查询的知识
  - 页面文件名优先中文短名；英文 slug、官方英文名和旧文件名写入 frontmatter `aliases`
- `outputs/`
  - 教程、问答、memo、对外表达、最终产出
- `inspection/`
  - 巡检、结构性问题、系统维护建议

### 什么时候更新长期规则

- 更新 `SOUL.md`
  - 只有稳定重复出现的偏好、习惯、学习风格
- 更新 `CLAUDE.md`
  - 只有真正影响后续协作流程的系统规则
- 更新 `学习/经历/`
  - 这次对话产出了可迁移的方法、教训或排障路径
- 更新 `outputs/`
  - 这次对话已经形成对未来自己有用的成品

## Recommended Workflow

1. 先判断本次任务是在处理：
   - 资料
   - 结构
   - 输出
   - 复盘
   - 规则沉淀
2. 再决定最小必要改动，不要同时大改太多层
3. 如果是高复用模式，顺手沉淀成：
   - 一页说明
   - 一篇经历
   - 一个 skill
   - 一次巡检结论
4. 如果只是一次性问题，回答即可，不必硬落文件
5. 如果用户给的是日常学习链接，且目标只是总结、留痕、反思，优先使用 `daily-learning-summarizer` 流程，不默认推动完整飞轮。
6. 如果用户给的是完整 AI 对话导出并要求保存，优先完整复制到 `raw/notes/`、处理重名并更新索引；是否继续摄取或提炼由用户另行决定。
7. 如果用户给出链接或文件并明确说“入库到 raw”“保存原始资料”“以后方便提问”，转交 `archive-to-raw`：只完成完整来源归档和 raw 索引更新，不自动更新 wiki。

## Good Trigger Examples

- “我以后想让 AI 可以和我一起更好地搭建这个数据库”
- “帮我看哪些目录可以并入飞轮系统”
- “这次对话里有哪些值得保存到知识库”
- “把这个固定工作流做成一个 skill”
