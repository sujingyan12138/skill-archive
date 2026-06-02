#!/usr/bin/env python3
"""
llm-ingest: LLM Wiki 知识库摄取辅助脚本
基于 Karpathy LLM Wiki 模式 (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

用法:
    python ingest.py scan   <kb_root>          # 扫描 raw/ 并列出未处理文件
    python ingest.py status <kb_root>          # 显示知识库状态摘要
    python ingest.py log    <kb_root> <msg>    # 向 wiki/log.md 追加日志条目
    python ingest.py init   <kb_root>          # 初始化知识库目录结构
    python ingest.py stale  <kb_root>          # 检测 raw/ 中已变更的文件（基于哈希）
"""

import sys
import os
import hashlib
import json
import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ──────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────
RAW_DIR = "raw"
WIKI_DIR = "wiki"
INDEX_FILE = "wiki/index.md"
LOG_FILE = "wiki/log.md"
SCHEMA_FILE = "CLAUDE.md"
STATE_FILE = ".ingest_state.json"  # 隐藏的状态文件，存储文件哈希

SUPPORTED_EXTENSIONS = {
    ".md", ".txt", ".pdf", ".html", ".htm",
    ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".csv", ".tex", ".rst", ".org"
}

IGNORE_PATTERNS = {
    ".git", ".DS_Store", "__pycache__", "node_modules",
    ".ingest_state.json", "*.pyc"
}


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────
def file_hash(path: Path) -> str:
    """计算文件内容的 SHA256 哈希（前 4096 字节，快速版）"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(4096))
        h.update(str(path.stat().st_size).encode())
    return h.hexdigest()[:16]


def load_state(kb_root: Path) -> dict:
    state_path = kb_root / STATE_FILE
    if state_path.exists():
        with open(state_path, encoding="utf-8") as f:
            return json.load(f)
    return {"ingested": {}}


def save_state(kb_root: Path, state: dict):
    state_path = kb_root / STATE_FILE
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def is_ignored(path: Path) -> bool:
    for part in path.parts:
        if part in IGNORE_PATTERNS or part.startswith("."):
            return True
    return False


def scan_raw(kb_root: Path) -> list[Path]:
    """递归扫描 raw/ 目录，返回支持的文件列表"""
    raw_dir = kb_root / RAW_DIR
    if not raw_dir.exists():
        return []
    files = []
    for f in raw_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            if not is_ignored(f.relative_to(kb_root)):
                files.append(f)
    return sorted(files)


# ──────────────────────────────────────────────
# 命令：init
# ──────────────────────────────────────────────
def cmd_init(kb_root: Path):
    """初始化知识库目录结构"""
    dirs = [
        kb_root / RAW_DIR / "articles",
        kb_root / RAW_DIR / "papers",
        kb_root / RAW_DIR / "notes",
        kb_root / RAW_DIR / "assets",
        kb_root / WIKI_DIR / "concepts",
        kb_root / WIKI_DIR / "entities",
        kb_root / WIKI_DIR / "comparisons",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {d.relative_to(kb_root)}/")

    # 创建 index.md
    index_path = kb_root / INDEX_FILE
    if not index_path.exists():
        index_path.write_text(
            "# Wiki Index\n\n"
            "> 此文件由 LLM 自动维护，每次摄取后更新。\n\n"
            "## 概念（Concepts）\n\n"
            "## 实体（Entities）\n\n"
            "## 对比分析（Comparisons）\n\n",
            encoding="utf-8",
        )
        print(f"  ✓ {INDEX_FILE}")

    # 创建 log.md
    log_path = kb_root / LOG_FILE
    if not log_path.exists():
        log_path.write_text(
            "# 操作日志\n\n"
            "> 此文件为 append-only 操作记录。格式：`## [日期] 操作类型 | 描述`\n\n"
            ,
            encoding="utf-8",
        )
        print(f"  ✓ {LOG_FILE}")

    # 创建 CLAUDE.md schema 模板
    schema_path = kb_root / SCHEMA_FILE
    if not schema_path.exists():
        schema_path.write_text(
            "# Wiki Schema（知识库配置）\n\n"
            "> 此文件告诉 LLM 知识库的结构和操作约定。\n\n"
            "## 目录结构\n\n"
            "- `raw/`：原始来源，只读，永不修改\n"
            "- `wiki/`：LLM 编译产物，由 LLM 完全拥有\n"
            "- `wiki/index.md`：全局内容目录，每页一行摘要\n"
            "- `wiki/log.md`：操作日志，append-only\n\n"
            "## 摄取约定（Ingest）\n\n"
            "1. 读取新来源，提取关键概念和实体\n"
            "2. 在 `wiki/concepts/` 或 `wiki/entities/` 创建或更新对应 .md 文件\n"
            "3. 使用 `[[wiki-links]]` 格式添加交叉引用\n"
            "4. 更新 `wiki/index.md` 目录\n"
            "5. 在每个 wiki 页面的 frontmatter 中记录来源文件\n\n"
            "## Wiki 页面 Frontmatter 格式\n\n"
            "```yaml\n"
            "---\n"
            "title: \"页面标题\"\n"
            "confidence: 0.9\n"
            "last_ingested: YYYY-MM-DD\n"
            "sources:\n"
            "  - raw/articles/example.md\n"
            "stale: false\n"
            "---\n"
            "```\n\n"
            "## 查询约定（Query）\n\n"
            "1. 先读取 `wiki/index.md` 定位相关页面\n"
            "2. 读取相关页面内容并综合答案\n"
            "3. 优质答案归档回 wiki 作为新页面\n\n"
            "## 整理约定（Lint）\n\n"
            "- 检查页面间矛盾，在 frontmatter 标注 `stale: true`\n"
            "- 补全孤立页面的入站链接\n"
            "- 发现缺少独立页面的重要概念\n",
            encoding="utf-8",
        )
        print(f"  ✓ {SCHEMA_FILE}")

    print(f"\n✅ 知识库初始化完成：{kb_root}")
    print("   下一步：将原始资料放入 raw/，然后运行 `ingest.py scan <kb_root>` 查看待处理文件。")


# ──────────────────────────────────────────────
# 命令：scan
# ──────────────────────────────────────────────
def cmd_scan(kb_root: Path):
    """扫描 raw/ 并区分「已摄取」与「待处理」文件"""
    state = load_state(kb_root)
    ingested = state.get("ingested", {})
    files = scan_raw(kb_root)

    if not files:
        print(f"⚠️  raw/ 目录为空或不存在：{kb_root / RAW_DIR}")
        return

    new_files = []
    changed_files = []
    done_files = []

    for f in files:
        rel = str(f.relative_to(kb_root))
        current_hash = file_hash(f)
        if rel not in ingested:
            new_files.append((f, rel))
        elif ingested[rel]["hash"] != current_hash:
            changed_files.append((f, rel, ingested[rel]["hash"], current_hash))
        else:
            done_files.append((f, rel))

    print(f"\n📂 知识库：{kb_root}")
    print(f"   raw/ 文件总数：{len(files)}")
    print(f"   ✅ 已摄取：{len(done_files)}")
    print(f"   🆕 待摄取（新文件）：{len(new_files)}")
    print(f"   🔄 已变更（需重新摄取）：{len(changed_files)}")

    if new_files:
        print("\n──── 🆕 待摄取文件 ────")
        for f, rel in new_files:
            size_kb = f.stat().st_size / 1024
            print(f"  {rel}  ({size_kb:.1f} KB)")

    if changed_files:
        print("\n──── 🔄 已变更文件 ────")
        for f, rel, old_h, new_h in changed_files:
            print(f"  {rel}  (hash: {old_h} → {new_h})")

    if not new_files and not changed_files:
        print("\n🎉 所有文件均已摄取，知识库是最新的。")
    else:
        total_pending = len(new_files) + len(changed_files)
        print(f"\n💡 共 {total_pending} 个文件待处理。")
        print("   请将待摄取文件路径提供给 LLM，执行 Ingest 操作。")
        print("   完成后运行 `ingest.py log <kb_root> \"ingest | <文件名>\"` 记录日志。")


# ──────────────────────────────────────────────
# 命令：status
# ──────────────────────────────────────────────
def cmd_status(kb_root: Path):
    """显示知识库整体状态"""
    state = load_state(kb_root)
    ingested = state.get("ingested", {})

    # 统计 raw/
    raw_files = scan_raw(kb_root)
    raw_size = sum(f.stat().st_size for f in raw_files)

    # 统计 wiki/
    wiki_dir = kb_root / WIKI_DIR
    wiki_files = list(wiki_dir.rglob("*.md")) if wiki_dir.exists() else []
    wiki_size = sum(f.stat().st_size for f in wiki_files)

    # 最近日志
    log_path = kb_root / LOG_FILE
    recent_logs = []
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").splitlines()
        recent_logs = [l for l in lines if l.startswith("## [")][-5:]

    print(f"\n📊 知识库状态：{kb_root}")
    print(f"   ── 原始来源（raw/）──")
    print(f"   文件数：{len(raw_files)}")
    print(f"   已摄取：{len(ingested)}")
    print(f"   总大小：{raw_size / 1024:.1f} KB")
    print(f"\n   ── Wiki 层（wiki/）──")
    print(f"   页面数：{len(wiki_files)}")
    print(f"   总大小：{wiki_size / 1024:.1f} KB")

    if recent_logs:
        print(f"\n   ── 最近操作（log.md）──")
        for log in recent_logs:
            print(f"   {log}")

    # 检测是否有 index.md
    index_ok = (kb_root / INDEX_FILE).exists()
    schema_ok = (kb_root / SCHEMA_FILE).exists()
    print(f"\n   ── 配置检查 ──")
    print(f"   {'✅' if index_ok else '❌'} wiki/index.md {'存在' if index_ok else '缺失（建议创建）'}")
    print(f"   {'✅' if schema_ok else '❌'} CLAUDE.md {'存在' if schema_ok else '缺失（建议创建）'}")


# ──────────────────────────────────────────────
# 命令：log
# ──────────────────────────────────────────────
def cmd_log(kb_root: Path, message: str):
    """向 wiki/log.md 追加一条操作记录"""
    log_path = kb_root / LOG_FILE
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = f"\n## [{now_str()}] {message}\n"

    if not log_path.exists():
        log_path.write_text("# 操作日志\n\n> append-only 操作记录。\n", encoding="utf-8")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

    print(f"✅ 日志已追加：{entry.strip()}")

    # 同时更新 state（如果消息包含 ingest | <文件>，标记为已摄取）
    if message.startswith("ingest |"):
        parts = message.split("|", 1)
        if len(parts) == 2:
            filename = parts[1].strip()
            # 尝试在 raw/ 中找到该文件
            raw_dir = kb_root / RAW_DIR
            matched = list(raw_dir.rglob(f"*{filename}*")) if raw_dir.exists() else []
            if matched:
                state = load_state(kb_root)
                for f in matched:
                    rel = str(f.relative_to(kb_root))
                    state.setdefault("ingested", {})[rel] = {
                        "hash": file_hash(f),
                        "ingested_at": now_str()
                    }
                save_state(kb_root, state)
                print(f"   已标记 {len(matched)} 个文件为「已摄取」")


# ──────────────────────────────────────────────
# 命令：stale
# ──────────────────────────────────────────────
def cmd_stale(kb_root: Path):
    """检测自上次摄取以来内容已变更的文件"""
    state = load_state(kb_root)
    ingested = state.get("ingested", {})
    files = scan_raw(kb_root)

    stale = []
    for f in files:
        rel = str(f.relative_to(kb_root))
        if rel in ingested:
            current_hash = file_hash(f)
            if ingested[rel]["hash"] != current_hash:
                stale.append((rel, ingested[rel].get("ingested_at", "?"), current_hash))

    if not stale:
        print("✅ 所有已摄取文件均未变更。")
    else:
        print(f"🔄 检测到 {len(stale)} 个已变更文件（需重新摄取）：\n")
        for rel, ingested_at, new_hash in stale:
            print(f"  {rel}")
            print(f"    上次摄取：{ingested_at} | 新哈希：{new_hash}")


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────
def main():
    usage = (
        "用法：\n"
        "  python ingest.py init   <kb_root>        # 初始化知识库\n"
        "  python ingest.py scan   <kb_root>        # 扫描待处理文件\n"
        "  python ingest.py status <kb_root>        # 显示状态摘要\n"
        "  python ingest.py log    <kb_root> <msg>  # 追加操作日志\n"
        "  python ingest.py stale  <kb_root>        # 检测已变更文件\n"
    )

    if len(sys.argv) < 3:
        print(usage)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    kb_root = Path(sys.argv[2]).expanduser().resolve()

    if not kb_root.exists() and cmd != "init":
        print(f"❌ 目录不存在：{kb_root}")
        print("   提示：先运行 `ingest.py init <kb_root>` 初始化知识库。")
        sys.exit(1)

    if cmd == "init":
        kb_root.mkdir(parents=True, exist_ok=True)
        cmd_init(kb_root)
    elif cmd == "scan":
        cmd_scan(kb_root)
    elif cmd == "status":
        cmd_status(kb_root)
    elif cmd == "log":
        if len(sys.argv) < 4:
            print("❌ 缺少日志消息。用法：ingest.py log <kb_root> <message>")
            sys.exit(1)
        msg = " ".join(sys.argv[3:])
        cmd_log(kb_root, msg)
    elif cmd == "stale":
        cmd_stale(kb_root)
    else:
        print(f"❌ 未知命令：{cmd}")
        print(usage)
        sys.exit(1)


if __name__ == "__main__":
    main()
