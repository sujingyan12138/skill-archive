from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

from raw_intake import find_repo_root, normalize_url, register, safe_name, unique_path


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def clean_date(value: str) -> str:
    match = re.match(r"(\d{4}-\d{2}-\d{2})", value or "")
    return match.group(1) if match else "unknown"


def image_extension(url: str, content_type: str | None) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
        if guessed:
            return ".jpg" if guessed == ".jpe" else guessed
    suffix = Path(urlsplit(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"} else ".jpg"


def choose_image_url(image) -> str | None:
    for attribute in ("data-original", "data-actualsrc", "data-src", "src"):
        value = image.get(attribute)
        if value and not value.startswith("data:image/svg+xml"):
            return value
    return None


def localize_images(soup: BeautifulSoup, repo: Path, title: str, source_url: str) -> tuple[int, list[str]]:
    assets = repo / "raw" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    downloaded: dict[str, str] = {}
    failures: list[str] = []
    prefix = f"{date.today().isoformat()}-{safe_name(title)}"

    for image in soup.find_all("img"):
        remote = choose_image_url(image)
        if not remote:
            image.decompose()
            continue
        remote = urljoin(source_url, remote)
        normalized = normalize_url(remote)
        if normalized in downloaded:
            image["src"] = f"../assets/{downloaded[normalized]}"
            continue
        try:
            response = requests.get(
                remote,
                headers={"User-Agent": USER_AGENT, "Referer": source_url},
                timeout=30,
            )
            response.raise_for_status()
            extension = image_extension(remote, response.headers.get("Content-Type"))
            number = len(downloaded) + 1
            filename = f"{prefix}-{number:02d}{extension}"
            target = unique_path(assets / filename, is_directory=False)
            target.write_bytes(response.content)
            downloaded[normalized] = target.name
            image["src"] = f"../assets/{target.name}"
        except requests.RequestException:
            failures.append(remote)
            image["src"] = remote
        for attribute in ("data-original", "data-actualsrc", "data-src", "srcset"):
            image.attrs.pop(attribute, None)
        if not image.get("alt"):
            image["alt"] = f"{title} 配图"
    return len(downloaded), failures


def normalize_links(soup: BeautifulSoup, source_url: str) -> None:
    for link in soup.find_all("a", href=True):
        link["href"] = urljoin(source_url, link["href"])
    for unwanted in soup.find_all(["script", "style", "noscript", "button"]):
        unwanted.decompose()


def html_to_markdown(html: str) -> str:
    text = markdownify(html, heading_style="ATX", bullets="-")
    text = text.replace("\u200b", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert an already isolated webpage body HTML into a raw article.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--html-file", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--author", default="unknown")
    parser.add_argument("--published-at", default="unknown")
    parser.add_argument("--modified-at", default="unknown")
    parser.add_argument("--category", choices=("articles", "papers", "notes"), default="articles")
    parser.add_argument("--status", choices=("complete", "partial"), default="complete")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-images", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = find_repo_root(args.repo)
    html = args.html_file.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    normalize_links(soup, args.url)
    image_count, failures = (0, []) if args.no_images else localize_images(soup, repo, args.title, args.url)
    body = html_to_markdown(str(soup))
    if not body:
        raise ValueError("The isolated HTML did not contain readable text.")

    if args.output:
        output = args.output if args.output.is_absolute() else repo / args.output
        output = output.resolve()
        output.relative_to((repo / "raw" / args.category).resolve())
        if output.exists():
            raise FileExistsError(output)
    else:
        filename = f"{date.today().isoformat()}-{safe_name(args.title)}.md"
        output = unique_path(repo / "raw" / args.category / filename, is_directory=False)

    source_type = {"articles": "article", "papers": "paper", "notes": "note"}[args.category]
    frontmatter = (
        "---\n"
        f"title: {yaml_string(args.title)}\n"
        f"source_type: {source_type}\n"
        f"source_url: {yaml_string(normalize_url(args.url))}\n"
        f"author: {yaml_string(args.author)}\n"
        f"published_at: {yaml_string(clean_date(args.published_at))}\n"
        f"modified_at: {yaml_string(clean_date(args.modified_at))}\n"
        f"captured_at: {date.today().isoformat()}\n"
        f"status: {args.status}\n"
        "language: zh\n"
        "tags:\n"
        "  - raw\n"
        "  - 网页归档\n"
        "---\n\n"
    )
    notes = [
        f"- 正文由 AI 在目标网页中按主内容容器提取，未混入推荐流和同页其他回答。",
        f"- 已本地化 {image_count} 张正文配图到 `raw/assets/`。",
        "- 本文件只完成原始资料归档，尚未执行 `llm-ingest` 或更新 `wiki/`。",
    ]
    if failures:
        notes.append(f"- 有 {len(failures)} 张图片下载失败，Markdown 中保留远程原始链接。")
    content = (
        f"{frontmatter}# {args.title}\n\n"
        f"> 来源：[{args.author}]({args.url})\n\n"
        f"## 原始正文\n\n{body}\n\n"
        f"## 归档说明\n\n{chr(10).join(notes)}\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    relative = output.relative_to(repo).as_posix()
    entry = f"- [[{output.relative_to(repo).with_suffix('').as_posix()}|{args.title}]]"
    index_changed = register(
        repo / "raw" / args.category / "index.md",
        "当前条目",
        entry,
        output.relative_to(repo).with_suffix("").as_posix().casefold(),
    )
    assets_index_changed = False
    if image_count:
        article_target = output.relative_to(repo).with_suffix("").as_posix()
        asset_entry = (
            f"- [[{article_target}|{args.title}]] — {image_count} 张正文配图，"
            f"文件名前缀 `{date.today().isoformat()}-{safe_name(args.title)}-`"
        )
        assets_index_changed = register(
            repo / "raw" / "assets" / "index.md",
            "当前附件",
            asset_entry,
            article_target.casefold(),
        )
    print(
        json.dumps(
            {
                "path": relative,
                "characters": len(body),
                "localized_images": image_count,
                "failed_images": failures,
                "index_updated": index_changed,
                "assets_index_updated": assets_index_changed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
