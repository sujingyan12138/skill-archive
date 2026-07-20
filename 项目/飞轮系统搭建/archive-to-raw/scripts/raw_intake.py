from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


CATEGORIES = {"articles", "papers", "notes", "videos", "assets"}
INDEX_HEADINGS = {
    "articles": "当前条目",
    "papers": "当前条目",
    "notes": "当前条目",
    "videos": "当前视频",
    "assets": "当前附件",
}
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "spm",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "raw").is_dir() and (candidate / "wiki").is_dir():
            return candidate
    raise ValueError(f"Cannot find a knowledge-base root from: {start}")


def normalize_url(value: str) -> str:
    value = value.strip()
    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        return value.rstrip("/")
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS and not key.lower().startswith("utm_")
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "-", value)
    value = re.sub(r"\s+", " ", value).strip(" .-")
    return value or "未命名来源"


def unique_path(base: Path, is_directory: bool) -> Path:
    if not base.exists():
        return base
    if is_directory:
        stem, suffix = base.name, ""
    else:
        stem, suffix = base.stem, base.suffix
    number = 2
    while True:
        candidate = base.with_name(f"{stem}-{number}{suffix}")
        if not candidate.exists():
            return candidate
        number += 1


def iter_raw_markdown(repo: Path):
    yield from (repo / "raw").rglob("*.md")


def find_url(repo: Path, url: str) -> list[str]:
    wanted = normalize_url(url)
    matches: list[str] = []
    pattern = re.compile(r"^source_url:\s*[\"']?(.+?)[\"']?\s*$", re.MULTILINE)
    for path in iter_raw_markdown(repo):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for match in pattern.finditer(text):
            if normalize_url(match.group(1)) == wanted:
                matches.append(path.relative_to(repo).as_posix())
                break
    return sorted(set(matches))


def find_file(repo: Path, source: Path) -> list[str]:
    wanted = sha256(source)
    matches: list[str] = []
    hash_pattern = re.compile(r"^source_sha256:\s*[\"']?([0-9a-fA-F]{64})[\"']?\s*$", re.MULTILINE)
    for path in (repo / "raw").rglob("*"):
        if not path.is_file() or path.name == "index.md":
            continue
        if path.suffix.lower() == ".md":
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                text = ""
            if any(match.group(1).lower() == wanted for match in hash_pattern.finditer(text)):
                matches.append(path.relative_to(repo).as_posix())
                continue
        try:
            if path.stat().st_size == source.stat().st_size and sha256(path) == wanted:
                matches.append(path.relative_to(repo).as_posix())
        except OSError:
            continue
    return sorted(set(matches))


def resolve_raw_path(repo: Path, value: str) -> Path:
    raw_root = (repo / "raw").resolve()
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    path = path.resolve()
    try:
        relative = path.relative_to(raw_root)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside {raw_root}: {path}") from exc
    if not relative.parts or relative.parts[0] not in CATEGORIES:
        raise ValueError(f"Path must be under one raw category: {path}")
    return path


def category_for(path: Path, repo: Path) -> str:
    return path.resolve().relative_to((repo / "raw").resolve()).parts[0]


def entry_for(path: Path, repo: Path, title: str) -> tuple[str, str]:
    category = category_for(path, repo)
    relative = path.relative_to(repo).as_posix()
    identity = relative.casefold()
    if path.is_dir():
        source_info = path / "source-info.md"
        if source_info.exists():
            target = source_info.relative_to(repo).with_suffix("").as_posix()
            return f"- [[{target}|{title}]]", target.casefold()
        return f"- `{relative}/` — {title}", identity
    if path.suffix.lower() == ".md":
        target = path.relative_to(repo).with_suffix("").as_posix()
        return f"- [[{target}|{title}]]", target.casefold()
    link = path.relative_to(repo / "raw" / category).as_posix().replace(" ", "%20")
    return f"- [{title}](<{link}>)", identity


def register(index_path: Path, heading: str, entry: str, identity: str) -> bool:
    text = index_path.read_text(encoding="utf-8") if index_path.exists() else f"# {index_path.parent.name}\n"
    normalized = text.casefold().replace("\\", "/")
    if identity in normalized:
        return False

    placeholder = re.compile(
        r"## 当前状态\s*\n+(?:- 目前还没有正式条目|- 暂无(?:正式)?条目)\s*\n?",
        re.MULTILINE,
    )
    if placeholder.search(text):
        text = placeholder.sub(f"## {heading}\n\n{entry}\n", text, count=1)
    else:
        heading_pattern = re.compile(rf"^## {re.escape(heading)}\s*$", re.MULTILINE)
        match = heading_pattern.search(text)
        if match:
            next_heading = re.search(r"^## ", text[match.end() :], re.MULTILINE)
            insert_at = match.end() + (next_heading.start() if next_heading else len(text[match.end() :]))
            before = text[:insert_at].rstrip()
            after = text[insert_at:].lstrip("\n")
            text = f"{before}\n{entry}\n\n{after}" if after else f"{before}\n{entry}\n"
        else:
            text = f"{text.rstrip()}\n\n## {heading}\n\n{entry}\n"
    index_path.write_text(text, encoding="utf-8")
    return True


def is_registered(path: Path, repo: Path) -> bool:
    category = category_for(path, repo)
    _, identity = entry_for(path, repo, path.stem)
    index_path = repo / "raw" / category / "index.md"
    if not index_path.exists():
        return False
    return identity in index_path.read_text(encoding="utf-8").casefold().replace("\\", "/")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reserve raw paths, detect duplicates, and maintain raw indexes.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    find_parser = subparsers.add_parser("find", help="Find an existing raw source by URL or file hash.")
    find_parser.add_argument("--repo", type=Path, default=Path.cwd())
    find_group = find_parser.add_mutually_exclusive_group(required=True)
    find_group.add_argument("--url")
    find_group.add_argument("--file", type=Path)

    suggest_parser = subparsers.add_parser("suggest", help="Suggest a non-conflicting destination path.")
    suggest_parser.add_argument("--repo", type=Path, default=Path.cwd())
    suggest_parser.add_argument("--category", choices=sorted(CATEGORIES), required=True)
    suggest_parser.add_argument("--title", required=True)
    suggest_parser.add_argument("--extension", default=".md")
    suggest_parser.add_argument("--no-date", action="store_true")
    suggest_parser.add_argument("--directory", action="store_true")

    register_parser = subparsers.add_parser("register", help="Add an existing raw item to its category index.")
    register_parser.add_argument("--repo", type=Path, default=Path.cwd())
    register_parser.add_argument("--path", required=True)
    register_parser.add_argument("--title", required=True)

    verify_parser = subparsers.add_parser("verify", help="Verify that a raw item exists and is indexed.")
    verify_parser.add_argument("--repo", type=Path, default=Path.cwd())
    verify_parser.add_argument("--path", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = find_repo_root(args.repo)

    if args.command == "find":
        if args.url:
            matches = find_url(repo, args.url)
            key = normalize_url(args.url)
        else:
            source = args.file.resolve()
            if not source.is_file():
                raise FileNotFoundError(source)
            matches = find_file(repo, source)
            key = sha256(source)
        print(json.dumps({"key": key, "matches": matches}, ensure_ascii=False, indent=2))
        return 0 if matches else 1

    if args.command == "suggest":
        extension = "" if args.directory else args.extension
        if extension and not extension.startswith("."):
            extension = f".{extension}"
        prefix = "" if args.no_date else f"{date.today().isoformat()}-"
        base = repo / "raw" / args.category / f"{prefix}{safe_name(args.title)}{extension}"
        path = unique_path(base, args.directory)
        print(json.dumps({"path": path.relative_to(repo).as_posix()}, ensure_ascii=False, indent=2))
        return 0

    path = resolve_raw_path(repo, args.path)
    if not path.exists():
        raise FileNotFoundError(path)

    if args.command == "register":
        category = category_for(path, repo)
        entry, identity = entry_for(path, repo, args.title)
        changed = register(repo / "raw" / category / "index.md", INDEX_HEADINGS[category], entry, identity)
        print(json.dumps({"path": path.relative_to(repo).as_posix(), "index_updated": changed}, ensure_ascii=False, indent=2))
        return 0

    registered = is_registered(path, repo)
    result = {"path": path.relative_to(repo).as_posix(), "exists": True, "indexed": registered}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if registered else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
