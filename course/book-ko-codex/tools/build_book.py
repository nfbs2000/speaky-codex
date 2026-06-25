#!/usr/bin/env python3
from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


BOOK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = Path(os.environ.get("CODEX_BOOK_SOURCE_ROOT", BOOK_ROOT / "src"))
REPO_URL = "https://github.com/nfbs2000/speaky-codex"
LATEST_REF = "main"


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


EDITION_REF = os.environ.get("CODEX_BOOK_EDITION_REF") or git_output("rev-parse", "HEAD")
EDITION_LABEL = EDITION_REF[:10]


@dataclass(frozen=True)
class TocEntry:
    title: str
    source_path: Path
    output_path: Path
    part: str


@dataclass(frozen=True)
class ResolvedSource:
    path: str
    kind: str


def should_skip_repo_path(path: Path) -> bool:
    parts = set(path.parts)
    return bool(
        {".git", "target", "node_modules", ".venv", ".ruff_cache"} & parts
        or path.as_posix().startswith("course/book-ko-codex/")
    )


def repo_inventory() -> tuple[set[str], set[str]]:
    files: set[str] = set()
    dirs: set[str] = set()
    for path in REPO_ROOT.rglob("*"):
        rel = path.relative_to(REPO_ROOT)
        if should_skip_repo_path(rel):
            continue
        rel_posix = rel.as_posix()
        if path.is_dir():
            dirs.add(rel_posix)
        elif path.is_file():
            files.add(rel_posix)
    return files, dirs


REPO_FILES, REPO_DIRS = repo_inventory()


def parse_summary() -> list[TocEntry]:
    summary_path = SRC_ROOT / "SUMMARY.md"
    current_part = "시작"
    entries: list[TocEntry] = []
    item_re = re.compile(r"^\s*(?:-\s+)?\[([^\]]+)\]\(([^)]+)\)")
    for line in summary_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# ") and not line.startswith("# 목차"):
            current_part = line[2:].strip()
            continue
        match = item_re.match(line)
        if not match:
            continue
        title, href = match.groups()
        source_rel = Path(href.removeprefix("./"))
        if source_rel.name == "SUMMARY.md":
            continue
        output_rel = source_rel.with_suffix(".html")
        entries.append(TocEntry(title=title, source_path=source_rel, output_path=output_rel, part=current_part))
    return entries


def source_like(token: str) -> bool:
    if len(token) > 180 or " " in token and "/" not in token:
        return False
    if token.startswith(("http://", "https://", "ws://")):
        return False
    if token in {"item/*", "item.*", "thread/goal/*"}:
        return False
    source_prefixes = (
        "codex-rs/",
        "sdk/",
        "desktop/",
        "observability/",
        "docs/",
        "app-server/",
        "app-server-protocol/",
        "core/",
        "core-",
        "hooks/",
        "models-manager/",
        "state/",
        "tasks/",
        "tools/",
        "tui/",
        "session/",
        "context/",
        "context_manager/",
    )
    source_suffixes = (
        ".rs",
        ".ts",
        ".tsx",
        ".js",
        ".mjs",
        ".cjs",
        ".md",
        ".toml",
        ".sql",
        ".json",
        ".jsonl",
        ".yml",
        ".yaml",
        ".bzl",
        ".bazel",
        ".lock",
    )
    return token.startswith(source_prefixes) or token.endswith(source_suffixes) or "*" in token


def normalize_source_token(token: str) -> str | None:
    value = token.strip().strip(".,;:)")
    if not source_like(value):
        return None
    value = value.removeprefix("./")
    if value.endswith("/..."):
        value = value[: -len("/...")]
    if value.endswith("/**"):
        value = value[: -len("/**")]
    if "*" in value:
        value = value[: value.find("*")].rstrip("/")
    if value.endswith("/"):
        value = value.rstrip("/")
    if not value or value.startswith("/"):
        return None
    return value


def resolve_source(token: str) -> ResolvedSource | None:
    normalized = normalize_source_token(token)
    if normalized is None:
        return None

    candidates = [normalized]
    if not normalized.startswith("codex-rs/"):
        candidates.extend(
            [
                f"codex-rs/{normalized}",
                f"codex-rs/core/src/{normalized}",
                f"codex-rs/tui/src/{normalized}",
                f"codex-rs/app-server-protocol/src/protocol/{normalized}",
                f"codex-rs/core-skills/src/{normalized}",
                f"codex-rs/hooks/src/{normalized}",
                f"codex-rs/state/src/runtime/{normalized}",
                f"sdk/typescript/src/{normalized}",
            ]
        )

    for candidate in candidates:
        if candidate in REPO_FILES:
            return ResolvedSource(path=candidate, kind="blob")
        if candidate in REPO_DIRS:
            return ResolvedSource(path=candidate, kind="tree")
    return None


def github_url(path: str, ref: str, kind: str = "blob") -> str:
    quoted = quote(path, safe="/")
    return f"{REPO_URL}/{kind}/{ref}/{quoted}"


def relative_href(current: Path, target: Path) -> str:
    current_dir = current.parent if current.name else current
    href = os.path.relpath(target.as_posix(), current_dir.as_posix() or ".")
    return href.replace(os.sep, "/")


def slug(value: str, fallback: str) -> str:
    base = re.sub(r"<[^>]+>", "", value)
    base = re.sub(r"`([^`]+)`", r"\1", base)
    base = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", base).strip("-").lower()
    return base or fallback


class MarkdownRenderer:
    def __init__(self, current_output: Path):
        self.current_output = current_output
        self.refs: dict[str, ResolvedSource] = {}
        self.unresolved: set[str] = set()
        self.heading_count = 0

    def render_inline(self, text: str) -> str:
        placeholders: list[tuple[str, str]] = []

        def code_repl(match: re.Match[str]) -> str:
            token = f"@@CODE{len(placeholders)}@@"
            placeholders.append((token, self.render_code_span(match.group(1))))
            return token

        without_code = re.sub(r"`([^`\n]+)`", code_repl, text)
        escaped = html.escape(without_code)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

        def link_repl(match: re.Match[str]) -> str:
            label = match.group(1)
            href = html.unescape(match.group(2))
            href = self.rewrite_markdown_href(href)
            return f'<a href="{html.escape(href, quote=True)}">{label}</a>'

        escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, escaped)
        for token, rendered in placeholders:
            escaped = escaped.replace(token, rendered)
        return escaped

    def rewrite_markdown_href(self, href: str) -> str:
        if href.startswith(("./", "../")) and href.endswith(".md"):
            href_path = (self.current_output.parent / href).with_suffix(".html")
            return href_path.as_posix()
        return href

    def render_code_span(self, code: str) -> str:
        escaped = html.escape(code)
        resolved = resolve_source(code)
        if resolved:
            self.refs[resolved.path] = resolved
            href = github_url(resolved.path, LATEST_REF, resolved.kind)
            return f'<a class="source-code" href="{html.escape(href, quote=True)}"><code>{escaped}</code></a>'
        if normalize_source_token(code) is not None:
            self.unresolved.add(code)
        return f"<code>{escaped}</code>"

    def is_block_start(self, line: str, next_line: str | None) -> bool:
        stripped = line.strip()
        return bool(
            stripped.startswith("```")
            or re.match(r"^#{1,6}\s+", stripped)
            or stripped.startswith(">")
            or re.match(r"^\s*[-*]\s+", line)
            or re.match(r"^\s*\d+\.\s+", line)
            or stripped == "---"
            or (stripped.startswith("|") and next_line and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", next_line))
        )

    def render(self, markdown: str) -> tuple[str, str]:
        lines = markdown.splitlines()
        output: list[str] = []
        page_title = "Untitled"
        skipped_first_h1 = False
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                i += 1
                continue

            if stripped.startswith("```"):
                language = stripped[3:].strip()
                code_lines: list[str] = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1
                code = "\n".join(code_lines)
                if language == "mermaid":
                    output.append(f'<div class="diagram"><pre class="mermaid">{html.escape(code)}</pre></div>')
                else:
                    lang_class = f' class="language-{html.escape(language)}"' if language else ""
                    output.append(f'<pre class="code-block"><code{lang_class}>{html.escape(code)}</code></pre>')
                continue

            heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading:
                level = len(heading.group(1))
                raw_title = heading.group(2).strip()
                if level == 1 and not skipped_first_h1:
                    page_title = re.sub(r"`([^`]+)`", r"\1", raw_title)
                    skipped_first_h1 = True
                    i += 1
                    continue
                self.heading_count += 1
                heading_id = slug(raw_title, f"section-{self.heading_count}")
                output.append(
                    f'<h{level} id="{html.escape(heading_id, quote=True)}">{self.render_inline(raw_title)}</h{level}>'
                )
                i += 1
                continue

            if stripped == "---":
                output.append("<hr />")
                i += 1
                continue

            if stripped.startswith(">"):
                quote_lines: list[str] = []
                while i < len(lines) and lines[i].strip().startswith(">"):
                    quote_lines.append(lines[i].strip().removeprefix(">").strip())
                    i += 1
                output.append(f'<blockquote><p>{" ".join(self.render_inline(line) for line in quote_lines)}</p></blockquote>')
                continue

            if stripped.startswith("|") and i + 1 < len(lines):
                separator = lines[i + 1].strip()
                if re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", separator):
                    table_lines: list[str] = []
                    while i < len(lines) and lines[i].strip().startswith("|"):
                        table_lines.append(lines[i].strip())
                        i += 1
                    output.append(self.render_table(table_lines))
                    continue

            if re.match(r"^\s*[-*]\s+", line):
                items: list[str] = []
                while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                    items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]).strip())
                    i += 1
                output.append("<ul>" + "".join(f"<li>{self.render_inline(item)}</li>" for item in items) + "</ul>")
                continue

            if re.match(r"^\s*\d+\.\s+", line):
                items = []
                while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                    items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip())
                    i += 1
                output.append("<ol>" + "".join(f"<li>{self.render_inline(item)}</li>" for item in items) + "</ol>")
                continue

            paragraph: list[str] = [stripped]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                next_next = lines[i + 1] if i + 1 < len(lines) else None
                if not next_line.strip() or self.is_block_start(next_line, next_next):
                    break
                paragraph.append(next_line.strip())
                i += 1
            output.append(f"<p>{self.render_inline(' '.join(paragraph))}</p>")

        return "\n".join(output), page_title

    def render_table(self, rows: list[str]) -> str:
        parsed = [self.parse_table_row(row) for row in rows]
        header = parsed[0]
        body = parsed[2:]
        header_html = "".join(f"<th>{self.render_inline(cell)}</th>" for cell in header)
        body_html = []
        for row in body:
            cells = "".join(f"<td>{self.render_inline(cell)}</td>" for cell in row)
            body_html.append(f"<tr>{cells}</tr>")
        return f'<div class="table-wrap"><table><thead><tr>{header_html}</tr></thead><tbody>{"".join(body_html)}</tbody></table></div>'

    def parse_table_row(self, row: str) -> list[str]:
        row = row.strip().strip("|")
        return [cell.strip() for cell in row.split("|")]


def render_sidebar(entries: list[TocEntry], current: Path) -> str:
    groups: list[tuple[str, list[TocEntry]]] = []
    for entry in entries:
        if not groups or groups[-1][0] != entry.part:
            groups.append((entry.part, []))
        groups[-1][1].append(entry)

    parts_html = []
    for part, part_entries in groups:
        links = []
        for entry in part_entries:
            active = " active" if entry.output_path == current else ""
            href = relative_href(current, entry.output_path)
            links.append(f'<a class="toc-link{active}" href="{html.escape(href, quote=True)}">{html.escape(entry.title)}</a>')
        parts_html.append(
            f'<section class="toc-section"><h2>{html.escape(part)}</h2><div class="toc-links">{"".join(links)}</div></section>'
        )

    home_active = " active" if current == Path("index.html") else ""
    return f"""
<aside class="sidebar" aria-label="책 목차">
  <div class="brand">
    <p class="eyebrow">Codex Source Book</p>
    <a class="brand-title" href="{html.escape(relative_href(current, Path("index.html")), quote=True)}">Codex 오픈소스 해부</a>
    <p class="brand-subtitle">공개 Rust 구현으로 읽는 로컬 코딩 에이전트. 온라인판은 실제 fork 소스 참조를 함께 제공합니다.</p>
  </div>
  <nav class="toc-nav">
    <a class="toc-link{home_active}" href="{html.escape(relative_href(current, Path("index.html")), quote=True)}">목차</a>
    {"".join(parts_html)}
  </nav>
  <div class="meta-panel">
    <p>Fork: <a href="{REPO_URL}">nfbs2000/speaky-codex</a></p>
    <p>Latest source: <a href="{REPO_URL}/tree/{LATEST_REF}">{LATEST_REF}</a></p>
    <p>Edition snapshot: <a href="{REPO_URL}/tree/{EDITION_REF}">{EDITION_LABEL}</a></p>
  </div>
</aside>
"""


def page_shell(title: str, current: Path, body: str, entries: list[TocEntry]) -> str:
    css_href = relative_href(current, Path("assets/styles.css"))
    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(title)} | Codex 오픈소스 해부</title>
    <meta name="description" content="Codex 오픈소스 저장소를 실제 fork 소스와 함께 읽는 한국어 온라인 책" />
    <link rel="stylesheet" href="{html.escape(css_href, quote=True)}" />
  </head>
  <body>
    <div class="layout">
{render_sidebar(entries, current)}
      <main class="content">{body}</main>
    </div>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({{
        startOnLoad: true,
        theme: "base",
        themeVariables: {{
          background: "#fffdf8",
          primaryColor: "#f1eee6",
          primaryTextColor: "#191817",
          primaryBorderColor: "#d9d1c3",
          lineColor: "#1f6f8b",
          secondaryColor: "#e8f0ec",
          tertiaryColor: "#fff6ed",
          fontFamily: "Inter, system-ui, sans-serif"
        }}
      }});
    </script>
  </body>
</html>
"""


def source_reference_section(renderer: MarkdownRenderer) -> str:
    resolved = sorted(renderer.refs.values(), key=lambda ref: ref.path)
    unresolved = sorted(renderer.unresolved)
    if not resolved and not unresolved:
        return ""

    resolved_rows = []
    for ref in resolved:
        latest = github_url(ref.path, LATEST_REF, ref.kind)
        edition = github_url(ref.path, EDITION_REF, ref.kind)
        resolved_rows.append(
            "<tr>"
            f"<td><code>{html.escape(ref.path)}</code></td>"
            f'<td><a href="{html.escape(latest, quote=True)}">Latest</a></td>'
            f'<td><a href="{html.escape(edition, quote=True)}">Edition</a></td>'
            "</tr>"
        )

    unresolved_rows = "".join(f"<li><code>{html.escape(item)}</code></li>" for item in unresolved)
    unresolved_html = (
        f"""
<details class="unresolved-refs">
  <summary>현재 fork에서 찾지 못한 참조 {len(unresolved)}개</summary>
  <p>이 경로들은 원고에 있지만 현재 <code>nfbs2000/speaky-codex</code> snapshot에는 없어서 404 링크를 만들지 않았습니다.</p>
  <ul>{unresolved_rows}</ul>
</details>
"""
        if unresolved
        else ""
    )

    resolved_html = (
        f"""
<div class="table-wrap source-table">
  <table>
    <thead><tr><th>경로</th><th>Latest</th><th>Edition</th></tr></thead>
    <tbody>{"".join(resolved_rows)}</tbody>
  </table>
</div>
"""
        if resolved_rows
        else ""
    )

    return f"""
<section class="source-references" id="source-references">
  <h2>이 장의 실제 소스 참조</h2>
  <p>본문의 코드 경로 중 현재 fork에 존재하는 항목만 실제 GitHub 소스로 연결했습니다. <code>Latest</code>는 <code>main</code>, <code>Edition</code>은 이 온라인판 생성 시점의 snapshot입니다.</p>
  {resolved_html}
  {unresolved_html}
</section>
"""


def chapter_nav(entries: list[TocEntry], entry: TocEntry) -> str:
    index = entries.index(entry)
    prev_entry = entries[index - 1] if index > 0 else None
    next_entry = entries[index + 1] if index + 1 < len(entries) else None
    prev_html = (
        f'<a class="nav-card" href="{html.escape(relative_href(entry.output_path, prev_entry.output_path), quote=True)}"><span>이전</span><strong>{html.escape(prev_entry.title)}</strong></a>'
        if prev_entry
        else '<span class="nav-card disabled"><span>이전</span><strong>없음</strong></span>'
    )
    next_html = (
        f'<a class="nav-card" href="{html.escape(relative_href(entry.output_path, next_entry.output_path), quote=True)}"><span>다음</span><strong>{html.escape(next_entry.title)}</strong></a>'
        if next_entry
        else '<span class="nav-card disabled"><span>다음</span><strong>없음</strong></span>'
    )
    return f'<nav class="chapter-nav" aria-label="장 이동">{prev_html}{next_html}</nav>'


def render_chapter(entries: list[TocEntry], entry: TocEntry) -> None:
    markdown = (SRC_ROOT / entry.source_path).read_text(encoding="utf-8")
    renderer = MarkdownRenderer(entry.output_path)
    rendered, title = renderer.render(markdown)
    title = title if title != "Untitled" else entry.title
    body = f"""
<article class="book-page">
  <header class="chapter-header">
    <p class="eyebrow">{html.escape(entry.part)}</p>
    <h1>{html.escape(title)}</h1>
    <p class="chapter-meta">온라인판은 원고 본문을 유지하면서 현재 fork의 실제 소스 링크를 함께 제공합니다.</p>
  </header>
  <div class="markdown-body">{rendered}</div>
  {source_reference_section(renderer)}
  {chapter_nav(entries, entry)}
</article>
"""
    output_path = BOOK_ROOT / entry.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page_shell(title, entry.output_path, body, entries), encoding="utf-8")


def render_index(entries: list[TocEntry]) -> None:
    groups: list[tuple[str, list[TocEntry]]] = []
    for entry in entries:
        if not groups or groups[-1][0] != entry.part:
            groups.append((entry.part, []))
        groups[-1][1].append(entry)

    group_html = []
    for part, part_entries in groups:
        chapter_cards = []
        for entry in part_entries:
            href = relative_href(Path("index.html"), entry.output_path)
            chapter_cards.append(
                f'<a class="toc-card" href="{html.escape(href, quote=True)}"><span>{html.escape(part)}</span><strong>{html.escape(entry.title)}</strong></a>'
            )
        group_html.append(f'<section class="toc-group"><h2>{html.escape(part)}</h2><div class="toc-card-grid">{"".join(chapter_cards)}</div></section>')

    first_chapter = next((entry for entry in entries if "1장:" in entry.title), entries[0])
    body = f"""
<article class="cover-page">
  <header class="cover-hero">
    <p class="eyebrow">Codex Source Book</p>
    <h1>Codex 오픈소스 해부</h1>
    <p>공개 Rust 구현으로 읽는 로컬 코딩 에이전트. 이 온라인판은 책의 관점을 그대로 유지하면서 각 장의 실제 fork 소스 참조를 함께 제공합니다.</p>
    <div class="cover-actions">
      <a class="primary-link" href="{html.escape(relative_href(Path("index.html"), first_chapter.output_path), quote=True)}">1장부터 읽기</a>
      <a class="secondary-link" href="{REPO_URL}">fork 소스 보기</a>
    </div>
  </header>
  <section class="edition-panel">
    <h2>온라인판 기준</h2>
    <p><strong>Latest</strong> 링크는 <code>{LATEST_REF}</code>를, <strong>Edition</strong> 링크는 <code>{EDITION_LABEL}</code> snapshot을 가리킵니다.</p>
    <p>원고 source는 이 repo의 <code>course/book-ko-codex/src</code> 아래에 포함되어 있습니다.</p>
  </section>
  <section class="full-toc" id="toc">
    <h2>목차</h2>
    {"".join(group_html)}
  </section>
</article>
"""
    (BOOK_ROOT / "index.html").write_text(page_shell("목차", Path("index.html"), body, entries), encoding="utf-8")


def clean_generated() -> None:
    for html_file in BOOK_ROOT.glob("*.html"):
        html_file.unlink()
    for child in BOOK_ROOT.iterdir():
        if child.is_dir() and (child.name.startswith("part") or child.name == "appendix"):
            shutil.rmtree(child)


def main() -> None:
    if not SRC_ROOT.exists():
        raise SystemExit(f"source root not found: {SRC_ROOT}")
    entries = parse_summary()
    clean_generated()
    render_index(entries)
    for entry in entries:
        render_chapter(entries, entry)
    print(f"generated {len(entries) + 1} pages from {SRC_ROOT}")


if __name__ == "__main__":
    main()
