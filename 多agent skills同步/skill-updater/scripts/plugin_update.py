#!/usr/bin/env python3
"""Claude Code 插件更新。

`~/.claude/plugins` 的目录语义
------------------------------
    marketplaces/<市场名>/          市场的 git 克隆 —— 这是「目录/货架」，
                                    里面 .claude-plugin/marketplace.json 声明了
                                    该市场有哪些插件、各自从哪来、版本是什么。
    cache/<市场名>/<插件名>/<版本>/  真正被加载的插件代码 —— 这是「买回来的货」。
                                    版本目录名就是版本号（semver 或上游 commit sha）。
    installed_plugins.json          购买凭证：哪个插件、装在哪、什么版本。
    known_marketplaces.json         每个市场的上游仓库地址。
    settings.json 的 enabledPlugins 是否启用。

所以「更新插件」= 刷新市场的定义 → 按定义把新版本内容同步进 cache → 改凭证。
cache 里那份才是真正生效的插件；marketplaces 里那份只是来源清单，别改错地方。

本模块只读写这几个 json，不碰 .git 配置，也不动用户的其他设置。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import skill_update as su

HEX = set("0123456789abcdefABCDEF")
PLUGIN_CONFIG_NAME = "plugins.json"

DEFAULT_CONFIG = {
    "claude_dir": str(Path.home() / ".claude"),
    "backup_dir": str(Path.home() / ".skill-backups"),
    "marketplace_repos": {},
    "skip": [],
}

GIT_URL_RE = re.compile(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


class Opts:
    """把 argparse 的各种命名空间统一成一个简单的选项对象。"""

    def __init__(self, proxy=None, refresh=False, json=False, dry_run=False, yes=False,
                 prune_old=False, pull_marketplaces=False, no_marketplace_report=False, plugins=None):
        self.proxy = proxy
        self.refresh = refresh
        self.json = json
        self.dry_run = dry_run
        self.yes = yes
        self.prune_old = prune_old
        self.pull_marketplaces = pull_marketplaces
        self.no_marketplace_report = no_marketplace_report
        self.plugins = plugins or []


def opts_from(args, **over) -> Opts:
    names = list(getattr(args, "plugins", None) or []) or list(getattr(args, "names", None) or [])
    o = Opts(
        proxy=getattr(args, "proxy", None),
        refresh=bool(getattr(args, "refresh", False)),
        json=bool(getattr(args, "json", False)),
        dry_run=bool(getattr(args, "dry_run", False)),
        yes=bool(getattr(args, "yes", False)),
        prune_old=bool(getattr(args, "prune_old", False)),
        pull_marketplaces=bool(getattr(args, "pull_marketplaces", False)),
        no_marketplace_report=bool(getattr(args, "no_marketplace_report", False)),
        plugins=names,
    )
    for k, v in over.items():
        setattr(o, k, v)
    return o


# ------------------------------------------------------------------ 环境

class Env:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.claude = Path(cfg["claude_dir"])
        self.plugins = self.claude / "plugins"
        self.cache = self.plugins / "cache"
        self.markets = self.plugins / "marketplaces"
        self.backup_root = Path(cfg["backup_dir"]) / "plugins"
        self.installed = su.load_json(self.plugins / "installed_plugins.json", {}) or {}
        self.known = su.load_json(self.plugins / "known_marketplaces.json", {}) or {}
        self.enabled: dict[str, bool] = {}
        for fname in ("settings.json", "settings.local.json"):
            data = su.load_json(self.claude / fname, {}) or {}
            for k, v in (data.get("enabledPlugins") or {}).items():
                self.enabled[k] = bool(v)

    @property
    def installed_map(self) -> dict:
        return self.installed.setdefault("plugins", {})


def load_config(root: Path) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    p = root / PLUGIN_CONFIG_NAME
    if p.exists():
        cfg.update(su.load_json(p, {}) or {})
    return cfg


# ------------------------------------------------------------------ 市场

def marketplace_repo(env: Env, mname: str) -> str | None:
    """市场名 → GitHub 仓库 owner/repo。"""
    src = (env.known.get(mname) or {}).get("source") or {}
    repo = src.get("repo")
    if not repo:
        repo = (env.cfg.get("marketplace_repos") or {}).get(mname)
    if repo:
        return repo
    loc = (env.known.get(mname) or {}).get("installLocation")
    if loc and Path(loc, ".git").exists():
        try:
            url = subprocess.run(["git", "-C", str(loc), "remote", "get-url", "origin"],
                                 capture_output=True, text=True, timeout=20).stdout.strip()
            m = GIT_URL_RE.search(url)
            if m:
                return f"{m.group(1)}/{m.group(2)}"
        except Exception:            # noqa: BLE001
            pass
    return None


def read_marketplace_manifest(tree: dict[str, bytes]) -> dict | None:
    raw = tree.get(".claude-plugin/marketplace.json")
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8", "ignore"))
    except Exception:                # noqa: BLE001
        return None


def local_git_head(d: Path) -> str | None:
    if not (d / ".git").exists():
        return None
    try:
        r = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or None
    except Exception:                # noqa: BLE001
        return None


# ------------------------------------------------------------------ 版本比较

def ver_eq(a: str | None, b: str | None) -> bool:
    """版本相同？两种形态：semver 字符串，或 commit sha（可能只存前 12 位）。"""
    a = (a or "").strip()
    b = (b or "").strip()
    if not a or not b:
        return a == b
    if a == b:
        return True
    if len(a) >= 12 and len(b) >= 12 and set(a[:12]) <= HEX and set(b[:12]) <= HEX:
        return a[:12].lower() == b[:12].lower()
    return False


# ------------------------------------------------------------------ 盘点

def enumerate_keys(env: Env) -> list[str]:
    keys: list[str] = []
    for k in env.installed_map:
        keys.append(k)
    for k in env.enabled:
        if k not in keys:
            keys.append(k)
    if env.cache.is_dir():
        for mkt in sorted(p for p in env.cache.iterdir() if p.is_dir()):
            for plug in sorted(p for p in mkt.iterdir() if p.is_dir()):
                k = f"{plug.name}@{mkt.name}"
                if k not in keys:
                    keys.append(k)
    return [k for k in keys if k not in (env.cfg.get("skip") or [])]


def state_of(env: Env, key: str) -> dict:
    plugin, _, mkt = key.rpartition("@")
    recs = env.installed_map.get(key) or []
    rec = recs[0] if recs else None
    cdir = env.cache / mkt / plugin
    versions = sorted(p.name for p in cdir.iterdir() if p.is_dir()) if cdir.is_dir() else []
    cur_ver = (rec or {}).get("version") or (versions[-1] if versions else None)
    if rec and rec.get("installPath"):
        path = Path(rec["installPath"])
    elif cur_ver:
        path = cdir / cur_ver
    else:
        path = None
    return {
        "key": key, "plugin": plugin, "marketplace": mkt,
        "record": rec, "registered": rec is not None,
        "current": cur_ver, "path": path, "versions": versions,
        "enabled": env.enabled.get(key),
    }


# ------------------------------------------------------------------ 计划

def plan_plugin(env: Env, st: dict, args) -> dict:
    plugin, mkt = st["plugin"], st["marketplace"]
    repo = marketplace_repo(env, mkt)
    if not repo:
        return {**st, "status": "error", "error": f"市场 {mkt} 查不到上游仓库（可在 plugins.json 的 marketplace_repos 里补）"}
    ref = su.default_branch(repo, args.proxy) or "main"
    try:
        tree = su.fetch_zip(repo, ref, args.proxy, args.refresh)
    except Exception as e:           # noqa: BLE001
        return {**st, "status": "error", "error": f"读取市场 {repo} 失败: {e}"}

    manifest = read_marketplace_manifest(tree)
    if not manifest:
        return {**st, "status": "error", "error": f"{repo} 没有 .claude-plugin/marketplace.json"}
    entry = next((p for p in manifest.get("plugins", []) if p.get("name") == plugin), None)
    if not entry:
        return {**st, "status": "error", "error": f"市场 {mkt} 里已没有名为 {plugin} 的插件"}

    src = entry.get("source")
    full_sha = None
    if isinstance(src, str):                       # 市场仓库内的本地目录
        sub = src.strip().lstrip("./").strip("/")
        full_sha = su.latest_commit(repo, ref, args.proxy)
        new_ver = entry.get("version") or (full_sha or "")[:12]
        if not new_ver:
            return {**st, "status": "error", "origin": f"{repo}:{sub or '/'}",
                    "error": "取不到市场仓库的最新 commit（GitHub 不可达或 API 限流），无法确定版本号。稍后重试，或用 --proxy"}
        content = su.sub_tree(tree, sub)
        origin = f"{repo}:{sub or '/'}"
    elif isinstance(src, dict):                    # 外部仓库（url / git-subdir）
        m = GIT_URL_RE.search(src.get("url") or "")
        if not m:
            return {**st, "status": "error", "error": f"看不懂的 source：{json.dumps(src, ensure_ascii=False)[:120]}"}
        srepo = f"{m.group(1)}/{m.group(2)}"
        sref = src.get("sha") or src.get("ref")
        if not sref:
            sref = su.default_branch(srepo, args.proxy) or "main"
        else:
            full_sha = sref if len(sref) == 40 and set(sref) <= HEX else None
        try:
            stree = su.fetch_zip_ref(srepo, sref, args.proxy, args.refresh)
        except Exception as e:       # noqa: BLE001
            return {**st, "status": "error", "error": f"读取 {srepo}@{sref[:12]} 失败: {e}"}
        sub = (src.get("path") or "").strip("/")
        content = su.sub_tree(stree, sub)
        new_ver = entry.get("version") or (sref if len(sref) < 40 else sref[:12])
        origin = f"{srepo}:{sub or '/'}@{sref[:12]}"
        if not full_sha and len(sref) == 40:
            full_sha = sref
    else:
        return {**st, "status": "error", "error": f"插件 {plugin} 的 source 字段缺失"}

    if not content:
        return {**st, "status": "error", "error": f"上游内容为空：{origin}", "origin": origin}

    if ver_eq(st["current"], new_ver):
        status = "up-to-date"
    elif st["registered"]:
        status = "update-available"
    else:
        status = "unregistered"

    return {**st, "status": status, "origin": origin, "new_version": new_ver,
            "full_sha": full_sha, "content": content, "files": len(content)}


def plan_all(env: Env, args, only: list[str] | None = None) -> list[dict]:
    out = []
    for key in enumerate_keys(env):
        if only and key not in only and key.rpartition("@")[0] not in only:
            continue
        out.append(plan_plugin(env, state_of(env, key), args))
    return out


# ------------------------------------------------------------------ 落盘

def backup_plugin(st: dict, env: Env) -> Path | None:
    src = st.get("path")
    if not src or not Path(src).is_dir():
        return None
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = env.backup_root / st["marketplace"] / st["plugin"] / f"{st.get('current') or 'unknown'}__{ts}"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest / "files", dirs_exist_ok=True)
    su.save_json(dest / "META.json", {
        "plugin": st["plugin"], "marketplace": st["marketplace"],
        "version": st.get("current"), "install_path": str(src),
        "backed_up_at": datetime.now().isoformat(timespec="seconds"),
        "upstream": st.get("origin"), "new_version": st.get("new_version"),
    })
    return dest


def install_plugin(env: Env, st: dict, args) -> tuple[Path, list[str]]:
    ver = (st.get("new_version") or "").strip()
    # 硬防线：版本号为空会把内容直接铺在 <插件>/ 下，破坏 cache 的
    # <市场>/<插件>/<版本>/ 结构，让 Claude 找不到插件。宁可不装。
    if not ver or "/" in ver or "\\" in ver or ver in (".", ".."):
        raise RuntimeError(f"版本号非法（{ver!r}），拒绝写入 cache —— 多半是上游 commit 没取到")
    new_dir = env.cache / st["marketplace"] / st["plugin"] / ver
    content: dict[str, bytes] = st["content"]
    new_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for rel, data in sorted(content.items()):
        fp = new_dir / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        if fp.exists() and su.norm(fp.read_bytes()) == su.norm(data):
            continue
        fp.write_bytes(data)
        written.append(rel)

    # 注意：目录里那个 `.in_use` 是 Claude 自己维护的「占用中」标记目录（不是文件，
    # 直接读会被 Windows 报 Permission denied）。它属于运行时状态，不属于插件内容，
    # 所以这里既不复制也不删除，让 Claude 自己在新版本目录里生成。

    old_dirs = [p for p in new_dir.parent.iterdir() if p.is_dir() and p.name != ver]
    if args.prune_old:
        for p in old_dirs:
            shutil.rmtree(p, ignore_errors=True)

    return new_dir, written


def update_record(env: Env, st: dict, new_dir: Path) -> bool:
    if not st["registered"]:
        return False
    recs = env.installed_map.get(st["key"])
    rec = recs[0]
    rec["installPath"] = str(new_dir)
    rec["version"] = st["new_version"]
    rec["lastUpdated"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if "gitCommitSha" in rec and st.get("full_sha"):
        rec["gitCommitSha"] = st["full_sha"]
    return True


def save_installed(env: Env):
    """写凭证前先留一份原文件，万一 Claude 同时在写可以对照。"""
    src = env.plugins / "installed_plugins.json"
    if src.exists():
        keep = env.backup_root / "_records"
        keep.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d")
        dst = keep / f"installed_plugins.{stamp}.json"
        if not dst.exists():
            shutil.copy2(src, dst)
    su.save_json(src, env.installed)


def pull_marketplace(env: Env, mname: str, repo: str, proxy=None) -> tuple[bool, str]:
    meta = env.known.get(mname) or {}
    loc = Path(meta.get("installLocation") or (env.markets / mname))
    if not loc.is_dir():
        return False, "本地没有这个市场的克隆"
    ref = su.default_branch(repo, proxy) or "main"
    url = f"https://github.com/{repo}.git"
    try:
        r = subprocess.run(["git", "-C", str(loc), "pull", "--ff-only", "--no-rebase", url, ref],
                           capture_output=True, text=True, timeout=180,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except Exception as e:           # noqa: BLE001
        return False, f"git 调用失败: {e}"
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip().splitlines()
        return False, msg[-1][:160] if msg else f"exit {r.returncode}"
    return True, (r.stdout or "").strip().splitlines()[-1][:160] if (r.stdout or "").strip() else "已是最新"


# ------------------------------------------------------------------ 子命令

MARK = {
    "up-to-date": "✅ 已是最新",
    "update-available": "⬆️  有更新",
    "unregistered": "❓ 未登记",
    "error": "❌ 检查失败",
    "disabled": "⏸  已停用",
}


def cmd_check(env: Env, args) -> int:
    o = opts_from(args)
    report = plan_all(env, o, o.plugins or None)
    if o.json:
        su.log(json.dumps(
            [{k: v for k, v in r.items() if k != "content"} for r in report],
            ensure_ascii=False, indent=2))
        return 0

    su.log(f"{'插件':<40} {'结果':<12} 版本")
    su.log("-" * 108)
    pending = 0
    for r in report:
        label = f"{r['plugin']}@{r['marketplace']}"
        if r["status"] == "error":
            su.log(f"{label:<40} {MARK['error']:<12} {r['error'][:60]}")
            pending += 1
            continue
        if r["enabled"] is False:
            label += " (已停用)"
        extra = []
        if r["status"] == "update-available":
            extra.append(f"{r['current']} → {r['new_version']}")
            extra.append(f"{r['files']} 个文件")
            pending += 1
        elif r["status"] == "unregistered":
            extra.append(f"本地 {r['current']} / 上游 {r['new_version']}（未登记在 installed_plugins.json）")
            pending += 1
        elif r["status"] == "up-to-date":
            note = "" if r["registered"] else "  [未登记在 installed_plugins.json]"
            extra.append(f"{r['current']}（{r['files']} 个文件）{note}")
        su.log(f"{label:<40} {MARK[r['status']]:<12} {' '.join(extra)}")

    su.log()
    fresh = sum(1 for r in report if r["status"] == "up-to-date")
    su.log(f"共 {len(report)} 个插件，{fresh} 个已是最新，{pending} 个待处理。")

    if not o.no_marketplace_report:
        report_marketplaces(env, o)
    return 0


def report_marketplaces(env: Env, o: Opts):
    if not env.known:
        return
    su.log()
    su.log("市场克隆状态（marketplaces/，仅作参考）")
    su.log("-" * 108)
    for mname, meta in env.known.items():
        repo = marketplace_repo(env, mname)
        loc = Path(meta.get("installLocation") or (env.markets / mname))
        local = local_git_head(loc)
        if not repo:
            su.log(f"{mname:<34} 未知道上游仓库")
            continue
        ref = su.default_branch(repo, o.proxy) or "main"
        remote = su.latest_commit(repo, ref, o.proxy)
        if not local:
            su.log(f"{mname:<34} {repo:<42} 本地无 git 记录")
        elif remote and local[:12] != remote[:12]:
            su.log(f"{mname:<34} {repo:<42} 本地 {local[:8]} 落后于上游 {remote[:8]}（Claude 会自动更新）")
        else:
            su.log(f"{mname:<34} {repo:<42} {local[:8]} 已是最新")

    orphans = []
    if env.markets.is_dir():
        for p in sorted(env.markets.iterdir()):
            if p.is_dir() and p.name not in env.known:
                orphans.append(p.name)
    if orphans:
        su.log()
        su.log("孤立的市场克隆（不在 known_marketplaces.json 里，可能是重复克隆）：")
        for orphan in orphans:
            su.log(f"  · {orphan}")


def cmd_update(env: Env, args) -> int:
    o = opts_from(args)
    report = plan_all(env, o, o.plugins or None)
    todo = [r for r in report if r["status"] in ("update-available", "unregistered")]

    if not todo:
        su.log("插件全部已是最新，无需更新。")
        if not o.no_marketplace_report:
            report_marketplaces(env, o)
        return 0

    su.log("=" * 96)
    su.log("插件更新计划")
    su.log("=" * 96)
    for r in todo:
        flag = "   [未登记在 installed_plugins.json]" if r["status"] == "unregistered" else ""
        su.log(f"\n▸ {r['plugin']}@{r['marketplace']}{flag}")
        su.log(f"  来源  : {r['origin']}")
        su.log(f"  版本  : {r.get('current') or '(无)'} → {r['new_version']}")
        if r.get("path"):
            su.log(f"  当前  : {r['path']}")
        su.log(f"  新位置: {env.cache / r['marketplace'] / r['plugin'] / r['new_version']}  （{r['files']} 个文件）")

    if o.dry_run:
        su.log("\n(--dry-run：以上仅为预览，未改动任何文件)")
        return 0
    if not o.yes:
        if not sys.stdin.isatty():
            su.log("\n需要 --yes 才会真正执行（当前为非交互环境）。")
            return 2
        ans = input(f"\n确认更新以上 {len(todo)} 个插件？旧版会备份到 {env.backup_root} [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            su.log("已取消。")
            return 1

    su.log("\n" + "=" * 96)
    ok, failed = [], []
    for r in todo:
        su.log(f"\n▸ 更新 {r['plugin']}@{r['marketplace']} …")
        try:
            bk = backup_plugin(r, env)
            if bk:
                su.log(f"  备份 → {bk}")
            new_dir, written = install_plugin(env, r, o)
            su.log(f"  写入 {len(written)} 个文件 → {new_dir}")
            if update_record(env, r, new_dir):
                su.log("  已更新 installed_plugins.json")
            else:
                su.log("  提示：installed_plugins.json 里没有它的记录，本次只更新了 cache 内容")
            ok.append(r["key"])
        except Exception as e:       # noqa: BLE001
            su.log(f"  !! 失败: {e}")
            failed.append((r["key"], str(e)))
    save_installed(env)

    if o.pull_marketplaces:
        su.log("\n" + "-" * 96)
        su.log("同步市场克隆")
        for mname in env.known:
            repo = marketplace_repo(env, mname)
            if not repo:
                continue
            good, msg = pull_marketplace(env, mname, repo, o.proxy)
            su.log(f"  {'✔' if good else '✘'} {mname}: {msg}")

    su.log("\n" + "=" * 96)
    su.log(f"完成：成功 {len(ok)} 个" + (f"，失败 {len(failed)} 个" if failed else ""))
    for k, err in failed:
        su.log(f"  ✗ {k}: {err}")
    if ok:
        su.log(f"备份位置: {env.backup_root}")
        su.log("提示：重启 Claude Code 后新版本才会被加载。")
    return 1 if failed else 0


def cmd_list(env: Env, args) -> int:
    su.log(f"Claude 目录 : {env.claude}")
    su.log(f"插件缓存    : {env.cache}")
    su.log(f"市场克隆    : {env.markets}")
    su.log(f"备份目录    : {env.backup_root}")
    su.log()
    su.log(f"{'插件':<40} {'当前版本':<22} {'已启用':<8} 已装版本目录")
    su.log("-" * 108)
    for key in enumerate_keys(env):
        st = state_of(env, key)
        en = {True: "是", False: "否", None: "—"}[st["enabled"]]
        reg = "" if st["registered"] else "  [未登记]"
        su.log(f"{key:<40} {str(st['current'] or '—'):<22} {en:<8} {', '.join(st['versions']) or '—'}{reg}")
    su.log()
    su.log(f"共 {len(enumerate_keys(env))} 个插件；版本目录里可能残留历史版本。")
    return 0
