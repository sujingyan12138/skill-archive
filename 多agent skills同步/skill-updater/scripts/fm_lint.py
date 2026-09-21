#!/usr/bin/env python3
"""SKILL.md frontmatter 校验与修复。

只做一件事：判断 SKILL.md 开头的 YAML frontmatter 能不能被正常解析。
不依赖 PyYAML —— 自己实现了 YAML plain scalar 的关键限制，
因为这些限制正是最常见的「frontmatter 静默解析失败」的元凶。

core 概念
---------
YAML 的 plain scalar（不加引号的裸值）**不能包含 `: `（冒号+空格）**，
因为它会被当成嵌套映射的键分隔符，解析器直接报
"mapping values are not allowed here"，导致整个 frontmatter 丢失。

典型受害者：

    description: ...when an AI repeats failed attempts: search the ledger...

这里 `attempts: search` 就是罪魁祸首，工具会静默加载不了这个 skill。

同类禁忌（都在本文件里检测）：
  - ` #`（空格+井号）：会被当成行内注释，值被截断
  - 行首 tab：YAML 禁止用 tab 做缩进
  - 值以引号开头却没配对的收尾引号
  - 文件开头的 BOM
"""
from __future__ import annotations

import re
from pathlib import Path

# 裸值不能以这些字符开头（YAML indicator characters）
BAD_START = set("!&*?|>%@`\"'#,[]{}")

REQUIRED = ("name", "description")
KEY_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*)\s*:(.*)$")


class Issue:
    def __init__(self, level: str, line: int, code: str, msg: str, fix: str | None = None):
        self.level, self.line, self.code, self.msg, self.fix = level, line, code, msg, fix

    def __str__(self) -> str:
        where = f"第 {self.line} 行" if self.line else "文件"
        return f"[{self.level}] {where}: {self.msg}"

    def as_dict(self) -> dict:
        return {"level": self.level, "line": self.line, "code": self.code, "msg": self.msg}


def _split_value(raw: str) -> tuple[str, str]:
    """返回 (去掉引号的纯值, 引号类型)。引号类型 ∈ '', "'", '"'。"""
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1], v[0]
    return v, ""


def parse(text: str) -> tuple[dict, list[Issue]]:
    """解析 frontmatter。返回 (字段字典, 问题列表)。字典里已剔除引号。"""
    issues: list[Issue] = []
    data: dict[str, str] = {}

    if text.startswith("\ufeff"):
        issues.append(Issue("error", 1, "bom", "文件开头有 BOM，部分加载器会认不出首行 `---`"))
        text = text.lstrip("\ufeff")

    lines = text.splitlines()
    if not lines:
        return data, [Issue("error", 1, "empty", "文件为空")]

    if lines[0].strip() != "---":
        if lines[0].strip().startswith("---"):
            issues.append(Issue("error", 1, "delim-ws", f"首行 `---` 后有多余字符：{lines[0]!r}"))
        elif not lines[0].strip():
            issues.append(Issue("error", 1, "delim-blank", "首行是空白，frontmatter 必须从第 1 行第 1 列开始"))
        else:
            issues.append(Issue("error", 1, "delim-missing", "首行不是 `---`，整个 frontmatter 不存在"))
        return data, issues

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return data, issues + [Issue("error", 0, "unclosed", "找不到结束的 `---`，frontmatter 未闭合")]

    nested_indent: int | None = None      # 正处于块标量 / 嵌套块中
    block_key: str | None = None          # 正在收集哪个键的块标量内容
    block_lines: list[str] = []
    for idx in range(1, end):
        line = lines[idx]
        lineno = idx + 1
        if "\t" in line and not (block_key and line.startswith("  ")):
            issues.append(Issue("error", lineno, "tab", "本行含 tab，YAML 禁止用 tab 做缩进"))

        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        if nested_indent is not None and indent > nested_indent:
            if block_key:
                block_lines.append(line.strip())
            continue                      # 块标量 / 嵌套映射的续行，内容随意
        if block_key:
            data[block_key] = " ".join(block_lines).strip()
            block_key, block_lines = None, []
        nested_indent = None

        if line.lstrip().startswith("#"):
            continue

        m = KEY_RE.match(line.lstrip())
        if not m:
            if not line.lstrip().startswith("-"):
                issues.append(Issue("error", lineno, "no-colon",
                                    f"本行不是合法的 `键: 值`，frontmatter 会整体解析失败：{line.strip()[:60]!r}"))
            continue

        key, raw = m.group(1), m.group(2)
        key_indent = indent
        if not raw.strip():
            nested_indent = key_indent
            data[key] = ""
            continue

        value = raw.strip()

        # 块标量：后面的缩进行都是内容，随便写
        if value[:1] in ("|", ">"):
            nested_indent = key_indent
            block_key, block_lines = key, []
            continue

        quoted = value[0] in "\"'" and len(value) >= 2 and value[-1] == value[0]
        if quoted:
            inner = value[1:-1]
            if value[0] == '"':
                inner = inner.replace('\\"', '"').replace("\\\\", "\\")
            else:
                inner = inner.replace("''", "'")
            data[key] = inner
            continue

        # ---- 以下都是「裸值」的检查 ----
        if ": " in value or value.endswith(":"):
            pos = value.find(": ")
            if pos < 0:
                pos = len(value) - 1
            seg = value[max(0, pos - 30): pos + 30]
            issues.append(Issue(
                "error", lineno, "colon-space",
                f"裸值里出现了 `: `（{seg!r}），YAML 会报 mapping values are not allowed here，"
                f"整个 frontmatter 报废。给值加引号，或把 `: ` 换成别的标点",
                fix="quote"))
            data[key] = value
            continue

        if " #" in value:
            issues.append(Issue(
                "error", lineno, "inline-hash",
                f"裸值里出现 ` #`，井号后的内容会被当成注释截断：{value[:60]!r}",
                fix="quote"))
            data[key] = value
            continue

        if value[0] in BAD_START:
            issues.append(Issue(
                "error", lineno, "bad-start",
                f"裸值以 YAML 保留字符 {value[0]!r} 开头，需加引号：{value[:50]!r}",
                fix="quote"))
            data[key] = value
            continue

        data[key] = value

    if block_key:
        data[block_key] = " ".join(block_lines).strip()

    for req in REQUIRED:
        if not data.get(req):
            issues.append(Issue("error", 0, f"missing-{req}", f"缺少必填字段 `{req}`（或值为空）"))

    return data, issues


def text_issues(text: str) -> list[Issue]:
    _, issues = parse(text)
    return issues


def check_dir(skill_dir: Path) -> list[Issue]:
    f = skill_dir / "SKILL.md"
    if not f.exists():
        return [Issue("error", 0, "no-skill-md", "没有 SKILL.md")]
    try:
        text = f.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return [Issue("error", 0, "encoding", f"SKILL.md 不是 UTF-8：{e}")]
    issues = text_issues(text)
    data, _ = parse(text)
    if data.get("name") and data["name"] != skill_dir.name:
        issues.append(Issue("warn", 0, "name-mismatch",
                            f"`name: {data['name']}` 与目录名 `{skill_dir.name}` 不一致，部分加载器以目录名为准"))
    return issues


# ------------------------------------------------------------------ 自动修复

def fix_text(text: str) -> tuple[str, list[str]]:
    """把裸值改成引号包裹的形式，其余原样保留。返回 (新文本, 修复说明)。"""
    notes: list[str] = []
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
        notes.append("去掉 BOM")

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text, notes
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return text, notes

    out = list(lines)
    for idx in range(1, end):
        nl = "\n" if lines[idx].endswith("\n") else ""
        raw_line = lines[idx].rstrip("\r\n")
        m = KEY_RE.match(raw_line.lstrip())
        if not m:
            continue
        key, raw = m.group(1), m.group(2)
        value = raw.strip()
        if not value or value[:1] in ("|", ">") or (value[0] in "\"'" and value[-1] == value[0]):
            continue
        need = (": " in value) or value.endswith(":") or (" #" in value) or (value[0] in BAD_START)
        if not need:
            continue
        # 优先单引号（把内部单引号翻倍）；含换行不可能（逐行处理）
        quoted = "'" + value.replace("'", "''") + "'"
        indent = raw_line[: len(raw_line) - len(raw_line.lstrip(" "))]
        out[idx] = f"{indent}{key}: {quoted}{nl}"
        notes.append(f"第 {idx + 1} 行 `{key}` 的裸值加了单引号")
    return "".join(out), notes
