---
name: skill-updater
description: 让从 GitHub 仓库或官网下载安装的 skill 与 Claude Code 插件跟上上游最新版，自建内容一律不碰；并体检各 agent 副本目录是否错乱。当用户说「更新 skill」「检查技能有没有新版本」「升级我装的技能」「更新插件」「claude 插件有新版吗」「为什么某个 skill 是旧版」「把 xx 更新一下」「各个 agent 的技能目录同步了吗」，或问到 .cc-switch/skills、.codex/skills、.claude/skills、.workbuddy/skills、.claude/plugins 的版本一致性时使用。
---

# Skill Updater

本机的 skill 与 Claude 插件分散在多个目录，其中一批是从 GitHub 下载的，上游更新后本地不会自动跟进。这个技能负责把这些「下载型」内容拉回最新，并保证各 agent 目录之间不错乱；**你自己写的内容一律不动**。

## 一、目录结构（本机实况）

skill 在四处：

| 位置 | 角色 |
|---|---|
| `C:\Users\Chen\.cc-switch\skills` | **主源**，真实目录 |
| `C:\Users\Chen\.codex\skills` | 独立副本（`~/.codex` 实为 `E:\Codex\.codex` 的软链） |
| `C:\Users\Chen\.claude\skills` | 大多是主源的软链，少数是真实目录 |
| `C:\Users\Chen\.workbuddy\skills` | 独立副本（WorkBuddy 专用） |

另有 `C:\Users\Chen\.deepseek\skills` 等独立技能集，不在本脚本管辖范围。

Claude Code 插件在 `C:\Users\Chen\.claude\plugins`：

| 位置 | 角色 |
|---|---|
| `marketplaces\<市场名>\` | 市场的 git 克隆 —— **货架**，声明有哪些插件、各自从哪来 |
| `cache\<市场名>\<插件名>\<版本>\` | **真正被加载的插件代码** —— 版本目录名就是版本号 |
| `installed_plugins.json` | 凭证：哪个插件装在哪、什么版本 |
| `known_marketplaces.json` | 每个市场的上游仓库地址 |
| `settings.json` 的 `enabledPlugins` | 是否启用 |

所以「更新插件」＝ 刷新市场定义 → 把新版本内容同步进 `cache` → 改凭证。

### 与 `skill-sync` 的关系（重要）

**本脚本不调用 `skill-sync`，是有意为之。**

- `skill-sync` 管的是「**项目级** `.codex\skills` ↔ `.claude\skills`」的**双向**合并，按文件修改时间决定谁新谁赢，而且不认识 `.cc-switch`（主源）和 `.workbuddy`。
- 本脚本走的是「**主源 → 各副本**」的单向写入，结果确定：更新完成后每个副本与主源逐字节一致。
- 两者混用很危险：双向 mtime 合并有可能把某个**陈旧副本**按「时间更新」的理由反向覆盖刚拉新的主源，正好制造错乱。需要判断哪边该赢时，用下面的 `mirrors` 命令看事实，而不是让工具盲猜。

## 二、用法

脚本：`<本技能目录>\scripts\skill_update.py`，只用 Python 标准库，无需装依赖。
不想敲命令就双击技能目录下的 `update-skills.bat`（不带参数＝只检查）。

```bash
cd "C:\Users\Chen\.cc-switch\skills\skill-updater"

# —— skill ——
python scripts/skill_update.py list                   # 看来源清单和上次同步时间
python scripts/skill_update.py check                  # 检查上游有无新版本（只读）
python scripts/skill_update.py update --dry-run       # 预览会改哪些文件
python scripts/skill_update.py update --yes           # 真正更新（自动备份）
python scripts/skill_update.py update playwright-cli --yes   # 只更新某一个
python scripts/skill_update.py scan some-skill        # 本地文件指纹反查上游路径

# —— Claude 插件 ——
python scripts/skill_update.py plugin-list            # 本机装了哪些插件、什么版本、是否启用
python scripts/skill_update.py plugin-check           # 检查插件有无新版
python scripts/skill_update.py plugin-update --dry-run
python scripts/skill_update.py plugin-update --yes
python scripts/skill_update.py plugin-update --yes --pull-marketplaces   # 顺带更新市场克隆

# —— 体检与对齐 ——
python scripts/skill_update.py doctor                 # 体检 SKILL.md 的 frontmatter 能否被解析
python scripts/skill_update.py doctor --fix           # 自动修（给有问题的裸值加引号）
python scripts/skill_update.py mirrors                # 四个目录里的 skill 是否一致
python scripts/skill_update.py mirrors --fix          # 对齐（默认以改动最新的一方为准）
python scripts/skill_update.py mirrors --fix --prefer primary   # 一律以主源为准
```

`check` 与 `update` 会**同时处理 skill 和插件**；只要其中一边用 `--skills-only` / `--plugins-only`。

常用参数：

- `--proxy http://127.0.0.1:10808` —— 网络不通时走代理（默认直连）
- `--refresh` —— 忽略缓存强制重新下载
- `--prune` —— skill：连同「上游已删除的文件」一起移走（默认保留并提示）
- `--prune-old` —— 插件：删掉 `cache` 里的旧版本目录（已备份）
- `--json` —— 机器可读输出

> 全局参数要写在子命令**前面**，例如 `python scripts/skill_update.py --proxy ... update --yes`。

## 三、更新时的行为

skill：

1. 下载上游 zip（带缓存，1 小时有效）
2. 与主源逐文件比对，报告哪些文件会被覆盖、上游新增了什么、本地多出什么
3. **先备份**到 `.skill-backups\<skill>\<时间戳>\`，内含完整旧版 `files\`、`LOCAL-CHANGES.diff`（本地相对上游的差异）、`META.json`
4. 逐文件覆盖写入主源，再同步到其余副本
5. 记录同步状态到 `.state.json`

插件：

1. 读 `marketplaces/cache/*.json` 摸清现状
2. 从市场上游仓库读最新的 `marketplace.json`，算出该插件的新版本号与内容位置
   - 市场内的本地目录（如 `./plugins/x`）→ 版本＝市场仓库的 commit sha
   - 外部仓库（`source.url`）→ 版本＝市场钉的 `sha`（钉住即视为最新，跟随市场的节奏）
3. **先备份**旧版本到 `.skill-backups\plugins\<市场>\<插件>\<旧版本>__<时间戳>\`
4. 把内容写进 `cache\<市场>\<插件>\<新版本>\`，更新 `installed_plugins.json`（改前另存一份到 `.skill-backups\plugins\_records\`）
5. 旧版本目录默认保留，加 `--prune-old` 才删

比对时文本文件会做换行归一化，纯 CRLF/LF 差异不会被误判成内容改动。

**插件更新后需重启 Claude Code 才会加载新版本。**

## 四、来源清单

`sources.json` 登记下载型 skill 的来源（`owner/repo` + 仓库内路径 + 分支），目前 12 项、10 项启用：

- `anthropics/skills` → skill-creator、frontend-design
- `mattpocock/skills` → grill-me、grilling
- `jackwener/opencli` → opencli-browser、opencli-usage、smart-search
- `microsoft/playwright-cli` → playwright-cli
- `LiamGvchi/gc-minimal-zine-poster` → gc-minimal-zine-poster-v0-3
- `humanizer-latest` → `blader/humanizer`（根，v4.0.0；用 `transform` 把 `name` 行改成本地名，正文跟随上游，见上）
- ⏸ `openai/skills` → hatch-pet（本地 v2 版比上游新，覆盖会降级，暂不启用）
- ⏸ `teng-lin/notebooklm-py` → notebooklm（由 pip 包附带，应走 `pip install -U notebooklm-py`）

**插件不需要逐条登记** —— `marketplaces/cache/*.json` 已经是完整清单，脚本实时读取。`plugins.json` 只放 `claude_dir`、`backup_dir`、`marketplace_repos`（补市场地址）、`skip` 这几项。

### `transform`：只改一行，正文跟随上游（首选）

偶尔要「只改一两个地方，其余跟随上游」，比如**目录名与上游 frontmatter 的 `name` 不一致**（部署名 ≠ 仓库名）。

```json
"humanizer-latest": {
  "repo": "blader/humanizer", "path": "", "ref": "main", "enabled": true,
  "transform": {
    "SKILL.md": [["^name: humanizer$", "name: humanizer-latest"]]
  }
}
```

每次比对/更新前，脚本先把上游文件内容按规则做正则替换，再拿结果跟本地比。所以：

- 本地只要和「上游 + 替换」一致就报「已是最新」
- 上游更新正文时**照常更新**，替换规则自动重新施加
- 替换只作用于指定文件、指定行，其他文件完全不受影响

`transform` 的值是 `{仓库内相对路径: [[正则, 替换], ...]}`，正则用 Python `re` 语法、`re.M` 多行模式。

### `pinned`：整文件冻结（已不推荐）

```json
"pinned": { "SKILL.md": "<该文件归一化后的 sha256>" }
```

被 pin 的文件在比对时按「本地原样」处理：`check` 不报「本地被改过」，`update` 也不会用上游覆盖。

⚠️ **已知硬伤（2026-11-10 实测）**：pin 会把文件**永久冻结在登记时的那个版本**。humanizer-latest 就因此从 v3.0.0 一直卡到上游发了 v4.0.0 —— `check` 一直报「已是最新」，实际内容落后一整年。更糟的是 `update` 会把 state 里的 commit 记成新版本，导致下次 `check` 走「commit 没变」的快速路径，连「本地被改过」都不再报。

**结论：需要「本地改名 / 改一行」时一律用 `transform`；`pinned` 只保留给「整文件都必须原样保留」的极少数场景。** 两者可并存，执行顺序是 transform 先、pinned 后。

### 新增一个 skill 来源

```bash
python scripts/skill_update.py add <本地目录名> <owner/repo> <仓库内路径> [分支]
python scripts/skill_update.py check <本地目录名>     # 验证路径对不对
```

`仓库内路径` 填仓库根就是该 skill 时用空字符串 `""`。不确定路径就先用 `scan` 反查。

## 五、排障

- **报「上游路径不存在」**：`sources.json` 里的 `path` 写错了，或上游改了目录结构。用 `scan` 反查新路径。
- **报「本地被改过」**：上游没有新版本，但本地这个 skill 的文件和上次检查时不一样了（脚本用目录指纹判断）。下次 `update` 会先备份再覆盖，改动可从备份的 `LOCAL-CHANGES.diff` 里找回。
- **`doctor` 报「裸值里出现了 `: `」**：YAML 的裸值不能含「冒号+空格」，否则整个 frontmatter 解析失败、工具会静默加载不了这个 skill。`--fix` 会把该值换成单引号包裹的写法。
- **`mirrors` 报「⚠️ 不一致」**：同一个 skill 在不同 agent 目录里内容不同，通常是某一次在别的目录里直接改了。用 `mirrors --fix` 对齐（默认以改动最新的一方为准，不会丢内容）。
- **`plugin-update` 报 `Permission denied: .in_use`**：`cache` 里的 `.in_use` 是 Claude 维护的**目录**（占用标记），不是文件，别去读写它。脚本已忽略它。若报错来自别的文件，多半是 Claude Code 正在运行，重启 Claude 后再跑。
- **插件「未登记在 installed_plugins.json」**：`settings.json` 里启用了、`cache` 里也有，但凭证文件缺记录（Claude 的历史遗留）。脚本只更新 `cache` 内容，不会伪造凭证。
- **某个 skill 混在自建里、来源不明**：跑 `scan <目录名>`，它用本地文件哈希去已登记的所有仓库里找匹配路径。
- **误更新想回退**：从 `.skill-backups\<skill 或 plugins\<市场>\<插件>>\<时间戳>\files\` 整目录拷回去即可。
- **网络失败**：确认 `codeload.github.com` 与 `api.github.com` 能否直连；不行就加 `--proxy`。
- **插件报「取不到市场仓库的最新 commit」**：`api.github.com` 匿名额度只有 **60 次/小时**，用光后取不到 sha。脚本对这类仓库**优先走 Atom feed**（`https://github.com/<repo>/commits/<ref>.atom`）——它不走 API、不受该限流，API 仅作兜底。若两条路都失败，脚本会**明确报错**，绝不会把"没查成"伪装成"没有更新"（早期版本会因此算出空版本号，误报"有更新"，且真执行会把文件铺在 `cache/<插件>/` 下、破坏版本目录结构）。
- **下载缓存占空间**：删掉本技能目录下的 `.cache\` 即可，会自动重建。
- **校验 transform 有没有生效 / 为什么本地版本落后**（调试用）：绕过 CLI 直接复验，注意两个 API 惯例 —— ① `bind_workdir(cfg)` 返回的是 **`skill-updater` 自己的目录**（`<primary>/skill-updater`），**不是主源根**；要拿主源根得用 `Path(cfg["roots"]["primary"])`。② 比对一律走 `sha256(norm(bytes))`，不是 `sha256sum` 的原始字节哈希。复验脚本：
  ```python
  import skill_update as su
  from pathlib import Path
  cfg = su.load_json(su.CONFIG, {}); su.bind_workdir(cfg)
  root = Path(cfg["roots"]["primary"])
  su.TRANSFORM_CACHE.update({k: v["transform"] for k, v in cfg["skills"].items() if v.get("transform")})
  tree = su.fetch_zip("blader/humanizer", "main")
  loc = su.local_tree(root / "humanizer-latest")
  eff = su.effective_upstream("humanizer-latest", loc, tree)   # 上游 + transform 后的结果
  print(eff["SKILL.md"].decode()[:80])                          # name 行应已是本地名
  print(su.compare(loc, eff))                                   # changed 为空 = 已对齐
  ```
- **`check` 报「已是最新」但本地明显落后**：先怀疑快速路径。`cmd_check` 在上游 commit 未变时会直接返回，不再逐文件比对；而 `update` 可能因为 pin 保护只写了部分文件、却把 commit 记成了新版。排查办法是直接跑上面的复验脚本（不走快速路径），或临时删掉 `.state.json` 里该 skill 的 `commit` 字段强制全量比对。
- **`sha256sum` 算出的哈希和脚本里的不一致**：正常现象。脚本比对前做 CRLF/LF 归一化，`sha256sum` 不会，纯换行差异的两份文件哈希不同。判断"是否最新"只看 `check` 的输出，别拿 `sha256sum` 对值。

## 六、注意

- 上游更新会**覆盖本地对下载型 skill 的个性化改动** —— 这正是备份和 `LOCAL-CHANGES.diff` 存在的理由。动手前先看 `--dry-run` 的输出。
- 更新完 skill 内容即生效；若某个 agent 缓存了技能列表，重开一个会话即可。
- `mirrors --fix` 会**覆盖**被判定为落后的那一份（先整目录备份）。它是唯一会写入「非主源且非下载型」内容的地方，用之前先看清报告。
