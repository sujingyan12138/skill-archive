#!/usr/bin/env python3
"""skill-updater —— 让从 GitHub 下载的 skill 与 Claude Code 插件保持最新。

只处理 sources.json 里登记过的 skill；自建 skill 一律不碰。
插件不需要清单：marketplaces / cache / installed_plugins.json 本身就是完整信息源。

子命令
------
list                            列出来源清单与当前状态
check   [skill ...]             检查上游有没有新版本（不写入任何文件；同时包含插件）
update  [skill ...]             拉取上游最新版，备份本地旧版，覆盖，并同步到各副本目录
scan    [skill ...]             本地文件指纹反查上游路径（用于核对 / 发现登记错误）
add     <目录名> <owner/repo> <仓库内路径> [ref]    登记一个新来源

doctor  [skill ...] [--fix]     体检 SKILL.md frontmatter 能否被解析；--fix 自动修
mirrors [skill ...] [--fix]     体检主源与各副本是否一致；--fix 对齐（默认以最新的一方为准）

plugin-list                     列出本机 Claude 插件、版本、启用状态
plugin-check  [plugin ...]      检查插件有无新版本
plugin-update [plugin ...]      更新插件（改 cache 与 installed_plugins.json）

常用参数
--------
--yes        非交互确认（给脚本 / AI 调用）
--dry-run    只显示将要做什么，不落盘
--prune      skill：上游已删除的文件也从本地移走（默认只是保留并提示）
--prune-old  插件：删掉 cache 里的旧版本目录（已备份）
--skills-only / --plugins-only   check、update 只处理其中一边
--pull-marketplaces              插件：同时把 marketplaces/ 的克隆拉到最新
--proxy URL  走代理，例如 http://127.0.0.1:10808
--refresh    忽略下载缓存，强制重新拉取
--json       以 JSON 输出结果
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG = ROOT / "sources.json"
STATE = ROOT / ".state.json"
CACHE = ROOT / ".cache"


def bind_workdir(cfg: dict) -> Path:
    """状态、缓存、配置始终落在主源那份里，保证从任意副本调用都共享同一份记录。"""
    global STATE, CACHE, CONFIG
    PINNED_CACHE.clear()          # 换配置就要重新读 pin；同一次运行内可能被调多次，清空是幂等的
    primary = cfg.get("roots", {}).get("primary")
    candidates = []
    if primary:
        candidates.append(Path(primary) / "skill-updater")
    candidates.append(ROOT)
    for cand in candidates:
        try:
            if (cand / "sources.json").exists():
                CONFIG = cand / "sources.json"
                STATE = cand / ".state.json"
                CACHE = cand / ".cache"
                return cand
        except OSError:
            continue
    return ROOT

IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode",
               ".pytest_cache", ".cache", ".skill-backups"}
IGNORE_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", ".in_use", ".last_inuse_sweep",
                ".state.json"}
CACHE_TTL = 3600          # zip 缓存有效期（秒）
SHA_CACHE_TTL = 600       # commit sha 缓存有效期（秒）
MAX_FILE = 5 * 1024 * 1024


# ---------------------------------------------------------------- 基础工具

def log(msg=""):
    print(msg, flush=True)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm(b: bytes) -> bytes:
    """文本文件统一换行符，避免 CRLF/LF 差异被当成内容改动。"""
    if b"\x00" in b:
        return b
    try:
        b.decode("utf-8")
    except UnicodeDecodeError:
        return b
    return b.replace(b"\r\n", b"\n")


def http_get(url: str, timeout=120, proxy: str | None = None) -> bytes:
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={
        "User-Agent": "skill-updater/1.0",
        "Accept": "*/*",
    })
    with opener.open(req, timeout=timeout) as r:
        return r.read()


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"!! 无法解析 {path}: {e}")
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ignored(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in IGNORE_DIRS for p in parts[:-1]):
        return True
    if parts[-1] in IGNORE_FILES:
        return True
    return False


# ---------------------------------------------------------------- 上游获取

def unzip_tree(blob: bytes) -> dict[str, bytes]:
    """把 GitHub 的 zip 包解成 {仓库内相对路径: 字节}（已剔除忽略项）。"""
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile as e:
        raise RuntimeError(f"返回的不是有效 zip（{e}）") from e

    out: dict[str, bytes] = {}
    for name in zf.namelist():
        if name.endswith("/"):
            continue
        parts = name.split("/")
        if len(parts) < 2:          # 丢掉 "<repo>-<ref>/" 这层根目录
            continue
        rel = "/".join(parts[1:])
        if ignored(rel):
            continue
        try:
            data = zf.read(name)
        except Exception:            # noqa: BLE001
            continue
        if len(data) > MAX_FILE:
            continue
        out[rel] = data
    return out


def _blob_for(repo: str, ref: str, proxy=None, refresh=False, variants=None) -> bytes:
    """按若干种 ref 写法依次尝试下载，带磁盘缓存。"""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / f"{repo.replace('/', '__')}__{ref}.zip"

    if not refresh and cache_file.exists() and time.time() - cache_file.stat().st_mtime < CACHE_TTL:
        return cache_file.read_bytes()

    variants = variants or [f"refs/heads/{ref}", ref]
    last_err = None
    for v in variants:
        for url in (
            f"https://codeload.github.com/{repo}/zip/{v}",
            f"https://github.com/{repo}/archive/{v}.zip",
        ):
            try:
                blob = http_get(url, proxy=proxy)
            except Exception as e:                 # noqa: BLE001
                last_err = e
                continue
            try:
                zipfile.ZipFile(io.BytesIO(blob))
            except zipfile.BadZipFile:
                last_err = RuntimeError(f"{url} 不是 zip（多半是 404 页面）")
                continue
            cache_file.write_bytes(blob)
            return blob
    raise RuntimeError(f"下载 {repo}@{ref} 失败: {last_err}")


def fetch_zip(repo: str, ref: str, proxy=None, refresh=False) -> dict[str, bytes]:
    """下载并解压仓库（分支名）。"""
    return unzip_tree(_blob_for(repo, ref, proxy, refresh))


def fetch_zip_ref(repo: str, ref: str, proxy=None, refresh=False) -> dict[str, bytes]:
    """下载并解压仓库，ref 可以是分支名、标签或 commit sha。"""
    return unzip_tree(_blob_for(repo, ref, proxy, refresh,
                                variants=[f"refs/heads/{ref}", f"refs/tags/{ref}", ref]))


def default_branch(repo: str, proxy=None) -> str | None:
    """仓库默认分支名（缓存 1 天）。"""
    CACHE.mkdir(parents=True, exist_ok=True)
    cf = CACHE / f"branch__{repo.replace('/', '__')}.json"
    if cf.exists() and time.time() - cf.stat().st_mtime < 86400:
        try:
            return json.loads(cf.read_text(encoding="utf-8")).get("branch")
        except Exception:            # noqa: BLE001
            pass
    try:
        raw = http_get(f"https://api.github.com/repos/{repo}", timeout=30, proxy=proxy)
        br = json.loads(raw.decode("utf-8", "ignore")).get("default_branch")
        save_json(cf, {"branch": br})
        return br
    except Exception:                # noqa: BLE001
        return None


def _sha_from_atom(raw: bytes) -> str | None:
    """从 commits/<ref>.atom 里抠出最新一条 commit sha（形如 .../Grit::Commit/<sha>）。"""
    marker = b"Commit/"
    i = raw.find(marker)
    if i < 0:
        return None
    j = k = i + len(marker)
    hexset = b"0123456789abcdef"
    while k < len(raw) and raw[k] in hexset:
        k += 1
    sha = raw[j:k].decode("ascii", "ignore")
    return sha if 7 <= len(sha) <= 40 else None


def latest_commit(repo: str, ref: str, proxy=None) -> str | None:
    """取分支最新 commit sha，用于廉价地判断上游有没有变。

    优先走 Atom feed（github.com/<repo>/commits/<ref>.atom）——它**不走 api.github.com**，
    因此不受匿名访问 60 次/小时的限流；API 那条路只在 Atom 失败时兜底。
    取不到（断网 / 限流 / 分支不存在）返回 None，调用方应退回全量比对，
    而不是把它当作"没有更新"。
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    cf = CACHE / f"sha__{repo.replace('/', '__')}__{ref}.json"
    if cf.exists() and time.time() - cf.stat().st_mtime < SHA_CACHE_TTL:
        try:
            return json.loads(cf.read_text(encoding="utf-8")).get("sha")
        except Exception:            # noqa: BLE001
            pass
    sha = None
    try:
        raw = http_get(f"https://github.com/{repo}/commits/{ref}.atom", timeout=30, proxy=proxy)
        sha = _sha_from_atom(raw)
    except Exception:                # noqa: BLE001
        pass
    if not sha:                      # 兜底：API（可能已限流）
        try:
            raw = http_get(f"https://api.github.com/repos/{repo}/commits/{ref}", timeout=30, proxy=proxy)
            sha = json.loads(raw.decode("utf-8", "ignore")).get("sha")
        except Exception:            # noqa: BLE001
            return None
    if sha:
        save_json(cf, {"sha": sha, "at": datetime.now().isoformat(timespec="seconds")})
    return sha


def sub_tree(tree: dict[str, bytes], sub: str) -> dict[str, bytes]:
    if not sub:
        return dict(tree)
    prefix = sub.strip("/") + "/"
    return {k[len(prefix):]: v for k, v in tree.items() if k.startswith(prefix)}


# ---------------------------------------------------------------- 本地读写

def local_tree(d: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    if not d.is_dir():
        return out
    for p in d.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(d).as_posix()
        if ignored(rel):
            continue
        try:
            data = p.read_bytes()
        except Exception:            # noqa: BLE001
            continue
        if len(data) > MAX_FILE:
            continue
        out[rel] = data
    return out


def dir_fingerprint(d: Path) -> tuple[str, int]:
    """本地目录的整体指纹，用来发现「上游没动、但本地被改过」。"""
    lt = local_tree(d)
    h = hashlib.sha256()
    for rel in sorted(lt):
        h.update(rel.encode("utf-8"))
        h.update(sha256(norm(lt[rel])).encode("ascii"))
    return h.hexdigest()[:16], len(lt)


def compare(local: dict[str, bytes], upstream: dict[str, bytes]) -> dict:
    same = [k for k in upstream if k in local and norm(local[k]) == norm(upstream[k])]
    changed = [k for k in upstream if k in local and norm(local[k]) != norm(upstream[k])]
    added = [k for k in upstream if k not in local]            # 上游新增
    removed = [k for k in local if k not in upstream]          # 上游已删除 / 本地新增
    return {
        "same": sorted(same),
        "changed": sorted(changed),
        "added": sorted(added),
        "removed": sorted(removed),
    }


def status_of(d: dict, local_count: int) -> str:
    if not local_count:
        return "missing"
    if d["changed"] or d["added"]:
        return "update-available"
    if d["removed"]:
        return "local-extra"          # 上游没有任何变化，只是本地多了文件
    return "identical"


def make_diff(local: dict[str, bytes], upstream: dict[str, bytes], rel: str) -> str:
    def lines(d, key):
        return d.get(key, b"").decode("utf-8", "replace").splitlines()
    a = lines(local, rel)
    b = lines(upstream, rel)
    return "\n".join(difflib.unified_diff(a, b, fromfile=f"local/{rel}", tofile=f"upstream/{rel}", lineterm=""))


# ---------------------------------------------------------------- 备份与写入

def backup_skill(skill_dir: Path, skill: str, cmp_result: dict, upstream: dict, backup_root: Path) -> Path | None:
    # 本地压根没有这个 skill（首次安装）时无需备份 —— shutil.copytree 对不存在的源
    # 会抛 WinError 3，早期版本因此让"首次安装"直接失败。
    if not skill_dir.is_dir():
        return None
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_root / skill / ts
    dest.mkdir(parents=True, exist_ok=True)
    files = dest / "files"
    shutil.copytree(skill_dir, files, dirs_exist_ok=True)

    changed_preview = []
    loc = local_tree(skill_dir)
    for rel in cmp_result["changed"]:
        try:
            diff = make_diff(loc, upstream, rel)
        except Exception:            # noqa: BLE001
            continue
        if diff:
            changed_preview.append(diff)
    if changed_preview:
        (dest / "LOCAL-CHANGES.diff").write_text("\n\n".join(changed_preview), encoding="utf-8")

    save_json(dest / "META.json", {
        "skill": skill,
        "backed_up_at": datetime.now().isoformat(timespec="seconds"),
        "source_dir": str(skill_dir),
        "files_total": len(loc),
        "changed_files": cmp_result["changed"],
        "upstream_added": cmp_result["added"],
        "local_only": cmp_result["removed"],
    })
    return dest


def write_skill(dest: Path, upstream: dict[str, bytes], prune: bool, trash_dir: Path | None):
    """把上游内容写入 dest。默认只增改，不删除（prune=True 时把多余文件移走）。"""
    dest.mkdir(parents=True, exist_ok=True)
    written, removed = [], []
    for rel, data in sorted(upstream.items()):
        fp = dest / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        if fp.exists() and norm(fp.read_bytes()) == norm(data):
            continue
        fp.write_bytes(data)
        written.append(rel)
    if prune:
        cur = local_tree(dest)
        for rel in sorted(cur):
            if rel in upstream:
                continue
            fp = dest / rel
            if trash_dir is not None:
                tp = trash_dir / rel
                tp.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(fp), str(tp))
            else:
                fp.unlink()
            removed.append(rel)
    return written, removed


# ---------------------------------------------------------------- 目标目录

class Targets:
    def __init__(self, cfg: dict):
        roots = cfg.get("roots", {})
        self.primary = Path(roots["primary"])
        self.mirrors = [Path(p) for p in roots.get("mirrors", [])]
        self.backup_root = Path(roots.get("backup_dir", str(Path.home() / ".skill-backups")))

    def resolve(self, skill: str):
        """返回 [(路径, 类型)]；类型 ∈ primary / mirror / symlink / absent"""
        out = []
        p = self.primary / skill
        if p.exists():
            out.append((p, "primary"))
        else:
            out.append((p, "absent"))
        for m in self.mirrors:
            t = m / skill
            if t.is_symlink():
                out.append((t, "symlink"))
            elif t.is_dir():
                out.append((t, "mirror"))
            else:
                out.append((t, "absent"))
        return out


# ---------------------------------------------------------------- 子命令

# 有意保留的本地改写。登记的文件在比对时按"上游原样"处理，因此
# check 不会报「本地被改过」，update 也不会用上游内容覆盖它。
# 适用场景：目录名与上游 frontmatter 的 name 不一致（如部署名 ≠ 仓库名）。
PINNED_CACHE: dict[str, dict] = {}


def pinned_for(cfg: dict, skill: str) -> dict:
    """{仓库内相对路径: 期望的 sha256 十六进制前缀或完整值}"""
    if skill not in PINNED_CACHE:
        raw = (cfg["skills"].get(skill) or {}).get("pinned") or {}
        PINNED_CACHE[skill] = {k: str(v).lower() for k, v in raw.items()}
    return PINNED_CACHE[skill]


def effective_upstream(skill: str, local: dict[str, bytes], upstream: dict[str, bytes]) -> dict[str, bytes]:
    """把被 pin 的文件换成本地现有内容，让指纹比对把它们视作「未改动」。"""
    pins = PINNED_CACHE.get(skill) or {}
    if not pins:
        return upstream
    out = dict(upstream)
    for rel, want in pins.items():
        if rel in upstream and rel in local:
            got = sha256(norm(local[rel]))
            if got.startswith(want):
                out[rel] = local[rel]
    return out


def cmd_list(cfg, args):
    t = Targets(cfg)
    log(f"主源     : {t.primary}")
    for m in t.mirrors:
        log(f"副本     : {m}")
    log(f"备份目录 : {t.backup_root}")
    log()
    st = load_json(STATE, {})
    log(f"{'skill':<32} {'状态':<10} {'上游':<45} 最后更新")
    log("-" * 110)
    for skill, meta in sorted(cfg["skills"].items()):
        repo = meta["repo"]
        sub = meta.get("path", "")
        label = f"{repo}:{sub or '/'}"
        rec = st.get(skill, {})
        flag = "" if meta.get("enabled", True) else " [已停用]"
        log(f"{skill:<32} {'✓' if rec.get('last_sync') else '—':<10} {label:<45} {rec.get('last_sync', '从未')}{flag}")
    log()
    log("自建 skill 不在此清单中，脚本不会改动它们。")


def cmd_check(cfg, args):
    t = Targets(cfg)
    st = load_json(STATE, {})
    report = {}
    for skill, meta in sorted(cfg["skills"].items()):
        repo, sub, ref = meta["repo"], meta.get("path", ""), meta.get("ref", "main")
        if args.skills and skill not in args.skills:
            continue
        if not meta.get("enabled", True):
            report[skill] = {"status": "disabled", "source": f"{repo}:{sub or '/'}", "note": meta.get("note", "")}
            continue
        rec = st.get(skill, {})
        sha = latest_commit(repo, ref, args.proxy)
        fp, n = dir_fingerprint(t.primary / skill)
        if sha and rec.get("commit") == sha[:12] and n:
            # 注意 n 判空：主源里根本没有这个技能时不能报「已是最新」。
            # commit 没变只能说明「上次比对过且一致」，不能说明本地还在。
            prev = rec.get("local_fp")
            dirty = bool(prev) and prev != fp
            report[skill] = {
                "status": "local-modified" if dirty else "up-to-date",
                "commit": sha[:8],
                "source": f"{repo}:{sub or '/'}",
                "local_files": n,
            }
            if prev is None or dirty:               # 建立基线 / 报告后归位，不重复刷屏
                st.setdefault(skill, {})["local_fp"] = fp
            continue
        try:
            tree = sub_tree(fetch_zip(repo, ref, args.proxy, args.refresh), sub)
        except Exception as e:       # noqa: BLE001
            report[skill] = {"status": "error", "error": str(e)}
            continue
        if not tree:
            report[skill] = {"status": "error", "error": f"上游路径不存在: {repo}:{sub or '/'}"}
            continue
        if sha:                      # 记住这个 commit，下次 check 就不必重新下载
            st.setdefault(skill, {})["commit"] = sha[:12]
        st.setdefault(skill, {})["local_fp"] = fp
        if not n:
            elsewhere = [_short(r, t.primary) for r in t.mirrors if (r / skill).is_dir()]
            report[skill] = {
                "status": "missing",
                "source": f"{repo}:{sub or '/'}",
                "local_files": 0,
                "found_in": elsewhere,
                "enabled": meta.get("enabled", True),
            }
            continue
        loc = local_tree(t.primary / skill)
        tree = effective_upstream(skill, loc, tree)      # 被 pin 的文件按本地原样比对
        d = compare(loc, tree)
        s = status_of(d, n)
        report[skill] = {
            "status": s,
            "commit": (sha or "")[:8],
            "source": f"{repo}:{sub or '/'}",
            "changed": d["changed"],
            "upstream_added": d["added"],
            "local_only": d["removed"],
            "local_files": n,
            "upstream_files": len(tree),
            "enabled": meta.get("enabled", True),
        }

    if st:
        save_json(STATE, st)

    if args.json:
        log(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    mark = {
        "identical": "✅ 已是最新",
        "update-available": "⬆️  有更新",
        "local-extra": "ℹ️  本地有额外文件",
        "local-modified": "✏️  本地被改过",
        "missing": "❓ 主源未装",
        "error": "❌ 检查失败",
        "up-to-date": "✅ 已是最新",
        "disabled": "⏸  已停用",
    }
    log(f"{'skill':<32} {'结果':<12} 说明")
    log("-" * 100)
    for skill, r in report.items():
        if r["status"] == "error":
            log(f"{skill:<32} {mark['error']:<12} {r['error']}")
            continue
        if r["status"] == "disabled":
            log(f"{skill:<32} {mark['disabled']:<12} {r.get('note', '')[:52]}")
            continue
        if r["status"] == "local-modified":
            log(f"{skill:<32} {mark['local-modified']:<12} 上游无更新，本地与上次记录不同（下次 update 会备份后覆盖）")
            continue
        if r["status"] == "missing":
            where = "、".join(r.get("found_in") or []) or "任何副本目录里都没有"
            log(f"{skill:<32} {mark['missing']:<12} 主源没有这个 skill；实际存在于：{where}")
            log(f"{'':<32} {'':<12} 更新它会先在主源创建，再同步给其余副本")
            continue
        label = mark[r["status"]]
        extra = []
        if r.get("changed"):
            extra.append(f"{len(r['changed'])} 个文件内容不同")
        if r.get("upstream_added"):
            extra.append(f"上游新增 {len(r['upstream_added'])}")
        if r.get("local_only"):
            extra.append(f"本地多出 {len(r['local_only'])}")
        detail = "，".join(extra) or f"文件 {r.get('local_files', 0)}"
        log(f"{skill:<32} {label:<12} {detail}")
    fresh = sum(1 for r in report.values() if r["status"] in ("identical", "up-to-date", "local-extra"))
    log()
    log(f"共 {len(report)} 项，{fresh} 项已是最新。")
    return 0


def cmd_update(cfg, args):
    t = Targets(cfg)
    st = load_json(STATE, {})
    plan = []
    for skill, meta in sorted(cfg["skills"].items()):
        if args.skills and skill not in args.skills:
            continue
        if not meta.get("enabled", True):
            log(f"· {skill}: 已停用，跳过（{meta.get('note', '')[:60]}）")
            continue
        repo, sub, ref = meta["repo"], meta.get("path", ""), meta.get("ref", "main")
        try:
            tree = sub_tree(fetch_zip(repo, ref, args.proxy, args.refresh), sub)
        except Exception as e:       # noqa: BLE001
            log(f"· {skill}: 下载失败，跳过 —— {e}")
            continue
        if not tree:
            log(f"· {skill}: 上游路径不存在 {repo}:{sub or '/'}，跳过")
            continue
        local_dir = t.primary / skill
        loc = local_tree(local_dir)
        tree = effective_upstream(skill, loc, tree)      # 被 pin 的文件保留本地版本
        d = compare(loc, tree)
        s = status_of(d, len(loc))
        plan.append((skill, meta, tree, d, s, local_dir))

    stale = {"update-available", "missing"} | ({"local-extra"} if args.prune else set())
    todo = [p for p in plan if p[4] in stale]
    if not todo:
        log("全部已是最新，无需更新。")
        if any(p[4] == "local-extra" for p in plan):
            log("（提示：有 skill 本地存在上游已没有的文件，加 --prune 可清理到备份区）")
        return 0

    log("=" * 96)
    log("更新计划")
    log("=" * 96)
    for skill, meta, tree, d, s, local_dir in todo:
        log(f"\n▸ {skill}   [{s}]")
        log(f"  来源: {meta['repo']}:{meta.get('path') or '/'}  ({len(tree)} 个文件)")
        for f in d["changed"][:10]:
            log(f"    ~ 覆盖改动  {f}")
        for f in d["added"][:10]:
            log(f"    + 上游新增  {f}")
        for f in d["removed"][:10]:
            log(f"    - 仅本地有  {f}")
        extra = len(d["changed"]) + len(d["added"]) + len(d["removed"]) - 30
        if extra > 0:
            log(f"    … 另有 {extra} 项未列出")
        if d["removed"] and not args.prune:
            log(f"    提示: 这些本地多余文件会保留；加 --prune 可一并移走")

    if args.dry_run:
        log("\n(--dry-run：以上仅为预览，未改动任何文件)")
        return 0

    if not args.yes:
        if not sys.stdin.isatty():
            log("\n需要 --yes 才会真正执行（当前为非交互环境）。")
            return 2
        ans = input(f"\n确认更新以上 {len(todo)} 个 skill？本地旧版会备份到 {t.backup_root} [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            log("已取消。")
            return 1

    log("\n" + "=" * 96)
    ok, failed = [], []
    for skill, meta, tree, d, s, local_dir in todo:
        log(f"\n▸ 更新 {skill} …")
        try:
            bdir = backup_skill(local_dir, skill, d, tree, t.backup_root)
            trash = (bdir / "pruned") if bdir else None
            if bdir:
                log(f"  备份 → {bdir}")
            else:
                log("  （本地原先没有这个 skill，无需备份）")

            written, removed = write_skill(local_dir, tree, prune=args.prune, trash_dir=trash)
            log(f"  主源: 写入 {len(written)} 个文件" + (f"，移走 {len(removed)} 个" if removed else ""))

            for path, kind in t.resolve(skill):
                if kind == "primary":
                    continue
                if kind == "symlink":
                    log(f"  副本: {path} 是软链，自动跟随主源")
                    continue
                if kind == "absent":
                    log(f"  副本: {path.parent} 下不存在，未创建（需要时手动装一次）")
                    continue
                w2, r2 = write_skill(path, tree, prune=args.prune, trash_dir=None)
                log(f"  副本: {path.name} 写入 {len(w2)} 个文件")

            fp, _ = dir_fingerprint(local_dir)
            st[skill] = {
                "last_sync": datetime.now().isoformat(timespec="seconds"),
                "source": f"{meta['repo']}:{meta.get('path') or '/'}",
                "commit": (latest_commit(meta["repo"], meta.get("ref", "main"), args.proxy) or "")[:12],
                "files": len(tree),
                "local_fp": fp,
                "backup": str(bdir) if bdir else None,
            }
            ok.append(skill)
        except Exception as e:       # noqa: BLE001
            log(f"  !! 失败: {e}")
            failed.append((skill, str(e)))

    save_json(STATE, st)
    log("\n" + "=" * 96)
    log(f"完成：成功 {len(ok)} 个" + (f"，失败 {len(failed)} 个" if failed else ""))
    for skill, err in failed:
        log(f"  ✗ {skill}: {err}")
    if ok:
        log(f"备份位置: {t.backup_root}")
    return 1 if failed else 0


def cmd_scan(cfg, args):
    """用本地文件指纹在候选仓库里反查来源路径。"""
    t = Targets(cfg)
    repos = sorted({m["repo"] for m in cfg["skills"].values()})
    index: dict[str, set[str]] = {}
    for repo in repos:
        try:
            tree = fetch_zip(repo, "main", args.proxy, args.refresh)
        except Exception as e:       # noqa: BLE001
            log(f"· 跳过 {repo}: {e}")
            continue
        log(f"· 已索引 {repo}（{len(tree)} 个文件）")
        for rel, data in tree.items():
            index.setdefault(sha256(data), set()).add(f"{repo}:{rel}")
    log()
    names = args.skills or sorted(p.name for p in t.primary.iterdir() if p.is_dir())
    for skill in names:
        d = t.primary / skill
        if not d.is_dir():
            continue
        loc = local_tree(d)
        if not loc:
            continue
        hits: dict[str, int] = {}
        for rel, data in loc.items():
            for target in index.get(sha256(data), ()):
                repo_path = target.rsplit("/", 1)[0]
                hits[repo_path] = hits.get(repo_path, 0) + 1
        if not hits:
            log(f"{skill:<34} 无匹配（可能是自建，或上游已大改）")
            continue
        best = sorted(hits.items(), key=lambda kv: -kv[1])[:3]
        desc = "  ".join(f"{p} ({n}/{len(loc)})" for p, n in best)
        log(f"{skill:<34} {desc}")


def cmd_add(cfg, args):
    skill, repo, sub = args.name, args.repo, args.path
    ref = args.ref or "main"
    cfg["skills"][skill] = {"repo": repo, "path": sub, "ref": ref}
    save_json(CONFIG, cfg)
    log(f"已登记 {skill} → {repo}:{sub or '/'}@{ref}")
    log("接着跑 `check` 或 `update` 验证路径是否正确。")


def cmd_doctor(cfg, args):
    """体检所有副本目录里的 SKILL.md frontmatter，需要时修掉。"""
    import fm_lint

    t = Targets(cfg)
    roots = [t.primary] + t.mirrors
    issues_total = 0
    fixed_files = 0

    for root in roots:
        if not root.is_dir():
            continue
        log(f"# {root}")
        for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
            if args.skills and d.name not in args.skills:
                continue
            issues = fm_lint.check_dir(d)
            if not issues:
                continue
            for i in issues:
                log(f"  {d.name:<34} {i}")
            issues_total += len(issues)
            if args.fix and any(i.fix for i in issues):
                f = d / "SKILL.md"
                old = f.read_text(encoding="utf-8")
                new, notes = fm_lint.fix_text(old)
                if new != old:
                    f.write_text(new, encoding="utf-8")
                    fixed_files += 1
                    log(f"  {'':<34} ✎ 已修复：{'；'.join(notes)}")
        log()

    log(f"共 {issues_total} 个问题" + (f"，已修复 {fixed_files} 个文件" if args.fix else "（加 --fix 可自动修）"))
    return 1 if issues_total and not args.fix else 0


def cmd_mirrors(cfg, args):
    """体检主源与各副本是否一致；必要时把某一方对齐到其他方。"""
    t = Targets(cfg)
    roots = [t.primary] + t.mirrors
    names = sorted({p.name for r in roots if r.is_dir()
                    for p in r.iterdir() if p.is_dir() and not p.name.startswith(".")})
    if args.skills:
        names = [n for n in names if n in args.skills]

    if args.json:
        out = []
        for n in names:
            row = {"skill": n, "copies": {}}
            for r in roots:
                d = r / n
                if d.is_symlink():
                    row["copies"][str(r)] = {"kind": "symlink"}
                elif d.is_dir():
                    fp, cnt = dir_fingerprint(d)
                    newest = max((p.stat().st_mtime for p in d.rglob("*") if p.is_file()), default=0)
                    row["copies"][str(r)] = {"kind": "present", "fp": fp, "files": cnt,
                                             "newest": datetime.fromtimestamp(newest).isoformat(timespec="seconds")}
                else:
                    row["copies"][str(r)] = {"kind": "missing"}
            out.append(row)
        log(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    drifted = []
    log(f"{'skill':<34} " + " ".join(f"{_short(r, t.primary):<22}" for r in roots))
    log("-" * 118)
    for n in names:
        cells, kinds = [], []
        for r in roots:
            d = r / n
            if d.is_symlink():
                kinds.append("symlink")
                cells.append("→软链")
            elif d.is_dir():
                fp, cnt = dir_fingerprint(d)
                newest = max((p.stat().st_mtime for p in d.rglob("*") if p.is_file()), default=0)
                kinds.append("present")
                cells.append(f"{fp}({cnt}) {datetime.fromtimestamp(newest).strftime('%m-%d')}")
            else:
                kinds.append("missing")
                cells.append("—")
        present = {kinds[i]: i for i in range(len(roots)) if kinds[i] == "present"}
        fps = {cells[i].split("(")[0] for i in range(len(roots)) if kinds[i] == "present"}
        flag = ""
        if len(fps) > 1:
            flag = "  ⚠️ 不一致"
            drifted.append(n)
        log(f"{n:<34} " + " ".join(f"{c:<22}" for c in cells) + flag)

    log()
    log("说明：`→软链` 表示该副本是指向主源的符号链接（自动跟随，无需同步）；"
        "`—` 表示该目录里没有装这个 skill（不算不一致）。")
    log(f"共 {len(names)} 个 skill，{len(drifted)} 个存在内容漂移"
        + (f"：{', '.join(drifted)}" if drifted else "。"))

    if not args.fix:
        if drifted:
            log()
            log("对齐前必须先指定「以哪一份为准」，脚本不会替你猜：")
            log("    mirrors --fix --from .codex        # 以某个目录为准（推荐，最明确）")
            log("    mirrors --fix --prefer primary     # 一律以主源为准")
            log("    mirrors --fix --prefer newest      # 以文件时间最新的一份为准")
            log("注意：mtime 不可靠 —— 整目录复制会刷新所有文件的时间戳，")
            log("      看起来「更新」的那份内容可能反而是旧的。优先用 --from。")
            log(f"被覆盖的一方会先整目录备份到 {t.backup_root}\\mirrors\\")
        return 1 if drifted else 0

    if not drifted:
        log("无需对齐。")
        return 0

    base = None
    if args.from_root:
        base = _pick_root(roots, args.from_root)
        if base is None:
            log(f"!! --from {args.from_root} 认不出是哪个目录。可用：primary / " +
                " / ".join(r.name for r in roots[1:]))
            return 2
    elif args.prefer is None:
        log("!! 请用 --from <目录> 或 --prefer primary|newest 指定基准。")
        return 2

    log()
    log("=" * 96)
    log(f"对齐计划（基准：{_short(base, t.primary) if base else 'mtime 最新的一份'}）")
    log("=" * 96)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    done = 0
    for n in drifted:
        live = [r for r in roots if (r / n).is_dir() and not (r / n).is_symlink()]
        if len(live) < 2:
            log(f"\n· {n}: 只有一份真实副本，跳过")
            continue
        if base is not None:
            if base not in live:
                log(f"\n· {n}: 基准目录 {base} 里没有这个 skill，跳过")
                continue
            src = base
        else:
            src = max(live, key=lambda r: max((p.stat().st_mtime for p in (r / n).rglob("*") if p.is_file()), default=0))
        log(f"\n▸ {n}")
        log(f"  基准: {_short(src, t.primary)}  ({src})")
        src_tree = local_tree(src / n)
        for r in live:
            if r == src:
                continue
            bk = t.backup_root / "mirrors" / n / f"{_short(r, t.primary).replace('/', '_')}__{ts}"
            try:
                if (r / n).exists():
                    bk.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(r / n, bk / "files", dirs_exist_ok=True)
                w, rm = write_skill(r / n, src_tree, prune=True, trash_dir=bk / "removed")
                log(f"  {r}: 覆盖 {len(w)} 个文件" + (f"，移走 {len(rm)} 个" if rm else "") + f"（旧版备份 → {bk}）")
                done += 1
            except Exception as e:            # noqa: BLE001
                log(f"  {r}: !! 失败 {e}")
    log()
    log(f"完成，覆盖了 {done} 份副本。")
    return 0


def _pick_root(roots: list[Path], spec: str) -> Path | None:
    """把 --from 的值解析成某个根目录；支持 primary / .codex / 完整路径。"""
    s = spec.strip().strip('"').rstrip("\\/").lower()
    if s in ("primary", "main", "主源", "cc-switch", ".cc-switch"):
        return roots[0]
    for r in roots:
        if str(r).lower().rstrip("\\/") == s:
            return r
    key = s.lstrip(".")
    for r in roots[1:]:
        if r.name.lstrip(".").lower() == key:
            return r
    return None


def _short(p: Path, primary: Path) -> str:
    """给路径起个短名字：主源用 .cc-switch，副本用 .codex / .claude 之类。"""
    if p == primary:
        return "主源(.cc-switch)"
    try:
        return f"{p.parent.name}/{p.name}"
    except Exception:                        # noqa: BLE001
        return str(p)


# ---------------------------------------------------------------- 入口

def _plugin_env():
    """构造插件环境（延迟 import 以避免循环依赖）。"""
    import plugin_update as plug
    cfg = load_json(CONFIG, None)
    root = bind_workdir(cfg) if cfg else ROOT
    return plug, plug.Env(plug.load_config(root))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skill_update", description="更新从 GitHub 下载的 skill 与 Claude 插件", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--proxy", help="代理地址，如 http://127.0.0.1:10808")
    ap.add_argument("--refresh", action="store_true", help="忽略缓存强制重新下载")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("check", "update", "scan"):
        p = sub.add_parser(name)
        p.add_argument("skills", nargs="*", help="只处理这些 skill（默认全部）")
    for name in ("check", "update"):
        p = sub.choices[name]
        p.add_argument("--skills-only", action="store_true", help="只处理 skill，跳过插件")
        p.add_argument("--plugins-only", action="store_true", help="只处理插件，跳过 skill")
        p.add_argument("--no-marketplace-report", action="store_true", help="不打印市场克隆状态")
    pu = sub.choices["update"]
    pu.add_argument("--dry-run", action="store_true")
    pu.add_argument("--yes", "-y", action="store_true")
    pu.add_argument("--prune", action="store_true", help="上游已删除的文件也一并移走")
    pu.add_argument("--prune-old", action="store_true", help="插件：删掉 cache 里的旧版本目录（已备份）")
    pu.add_argument("--pull-marketplaces", action="store_true", help="插件：同时把 marketplaces/ 的克隆拉到最新")

    sub.add_parser("list")

    pd = sub.add_parser("doctor", help="体检 SKILL.md 的 frontmatter 能否被正常解析")
    pd.add_argument("skills", nargs="*")
    pd.add_argument("--fix", action="store_true", help="自动修复（给有问题的裸值加引号）")

    pm = sub.add_parser("mirrors", help="体检主源与各副本目录是否一致（防止各 agent 之间错乱）")
    pm.add_argument("skills", nargs="*")
    pm.add_argument("--fix", action="store_true", help="把不一致的副本对齐（必须配 --from 或 --prefer）")
    pm.add_argument("--from", dest="from_root",
                    help="以哪个目录为基准：primary / .codex / .claude / .workbuddy，或完整路径")
    pm.add_argument("--prefer", choices=["primary", "newest"], default=None,
                    help="primary=以主源为准；newest=以文件时间最新的一份为准（mtime 易被整目录复制刷新，慎用）")

    pa = sub.add_parser("add")
    pa.add_argument("name")
    pa.add_argument("repo")
    pa.add_argument("path")
    pa.add_argument("ref", nargs="?", default="main")

    sub.add_parser("plugin-list", help="列出本机 Claude 插件与其版本")
    for name in ("plugin-check", "plugin-update"):
        p = sub.add_parser(name)
        p.add_argument("plugins", nargs="*", help="只处理这些插件（默认全部）")
        p.add_argument("--no-marketplace-report", action="store_true")
    ppu = sub.choices["plugin-update"]
    ppu.add_argument("--dry-run", action="store_true")
    ppu.add_argument("--yes", "-y", action="store_true")
    ppu.add_argument("--prune-old", action="store_true", help="删掉 cache 里的旧版本目录（已备份）")
    ppu.add_argument("--pull-marketplaces", action="store_true", help="同时把 marketplaces/ 的克隆拉到最新")

    args = ap.parse_args(argv)

    if args.cmd.startswith("plugin-"):
        plug, env = _plugin_env()
        if args.cmd == "plugin-list":
            return plug.cmd_list(env, args) or 0
        if args.cmd == "plugin-check":
            return plug.cmd_check(env, args)
        return plug.cmd_update(env, args)

    cfg = load_json(CONFIG, None)
    if cfg is None:
        log(f"找不到配置：{CONFIG}")
        return 2
    bind_workdir(cfg)
    pins = {k: (v or {}).get("pinned") or {} for k, v in cfg["skills"].items()}
    pins = {k: v for k, v in pins.items() if v}
    PINNED_CACHE.update(pins)     # 预载 pin，避免后续再次 bind_workdir 时被清掉

    rc = 0
    if args.cmd in ("check", "update") and not args.skills_only:
        plug, env = _plugin_env()
        run_plugins = True
    else:
        run_plugins = False

    if args.cmd == "check":
        if not args.plugins_only:
            rc = cmd_check(cfg, args) or 0
        if run_plugins:
            log()
            log("=" * 96)
            log("Claude 插件")
            log("=" * 96)
            rc = plug.cmd_check(env, args) or rc
        return rc
    if args.cmd == "update":
        if not args.plugins_only:
            rc = cmd_update(cfg, args) or 0
        if run_plugins:
            log()
            log("=" * 96)
            log("Claude 插件")
            log("=" * 96)
            rc = plug.cmd_update(env, args) or rc
        return rc
    if args.cmd == "scan":
        return cmd_scan(cfg, args) or 0
    if args.cmd == "list":
        return cmd_list(cfg, args) or 0
    if args.cmd == "doctor":
        return cmd_doctor(cfg, args) or 0
    if args.cmd == "mirrors":
        return cmd_mirrors(cfg, args) or 0
    if args.cmd == "add":
        return cmd_add(cfg, args) or 0
    return 0


if __name__ == "__main__":
    # 以脚本方式运行时，把 __main__ 登记成 skill_update，
    # 这样 plugin_update 里那句 `import skill_update as su` 会拿到同一个模块实例。
    # 否则 Python 会再加载一份 skill_update，那份从没被 bind_workdir 指过路，
    # 于是 STATE / CACHE 会各存一份，缓存和状态会散落到副本目录里。
    sys.modules.setdefault("skill_update", sys.modules[__name__])
    sys.exit(main())
