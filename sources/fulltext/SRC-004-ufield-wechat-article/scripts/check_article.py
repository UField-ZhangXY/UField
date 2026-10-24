"""Basic article checks; not a substitute for visual or factual review."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


def check_markdown(text):
    errors = []
    if not re.match(r"\A---\s*\n.*?\n---(?:\s*\n|$)", text, re.S):
        errors.append("Missing YAML frontmatter")
    if not re.search(r"^#\s+\S", text, re.M):
        errors.append("Missing H1 title")
    # Join quote runs across blank lines conservatively: parsers can merge them.
    block, start, fence = [], 0, None
    def flush():
        if block and len("".join(block)) > 280:
            errors.append(f"Quote at line {start}: {len(''.join(block))} chars > 280")
        block.clear()
    for line_number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            flush()
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence:
            continue
        quote = re.match(r"^\s{0,3}>\s?(.*)$", line)
        if quote:
            if not block:
                start = line_number
            block.append(quote.group(1))
        elif line.strip():
            flush()
    flush()
    errors.extend(check_svg(text))
    return errors


def check_svg(text):
    errors = []
    if re.search(r"SVGHOLD\d+", text):
        errors.append("Unresolved SVG placeholder")
    for i, svg in enumerate(re.findall(r"<svg\b[\s\S]*?</svg>", text), 1):
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            errors.append(f"SVG {i} invalid XML: {exc}")
    return errors


class PreviewParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.article_count = 0
        self.old_preview_count = 0
    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.article_count += attributes.get("id") == "wechatHtml"
        self.old_preview_count += attributes.get("id") == "articleContent"


def check_preview(text):
    parser = PreviewParser()
    parser.feed(text)
    errors = check_svg(text)
    if parser.article_count != 1:
        errors.append(f"Expected one wechatHtml container, found {parser.article_count}")
    if parser.old_preview_count:
        errors.append("Old articleContent preview container present; inspect duplicate content")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", type=Path)
    parser.add_argument("clean_html", type=Path, nargs="?")
    args = parser.parse_args()
    errors = check_markdown(args.markdown.read_text(encoding="utf-8-sig"))
    if args.clean_html:
        errors.extend(check_preview(args.clean_html.read_text(encoding="utf-8-sig")))
    for error in errors:
        print("FAIL:", error)
    if not errors:
        print("PASS: basic structural checks; visual/factual review still required")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
