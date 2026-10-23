#!/usr/bin/env python
"""Fail if engineering files contain non-ASCII characters.

The project rule is: .py/.bat/.sh/.ts/.tsx/.css/HDL sources stay pure ASCII;
Chinese belongs in Markdown and JSON data only. This checker walks the given
files/directories and reports every non-ASCII character with file:line:col.
Scratch directories (.tmp, node_modules, build output) are skipped: they hold
tool-written files, not project source.

Usage:
    python check_ascii.py .
    python check_ascii.py production post-production --ext .py,.bat,.ts
    python check_ascii.py . --all
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DEFAULT_EXTS = (
    ".v", ".sv", ".svh", ".svi", ".vh", ".vhd",
    ".py", ".tcl", ".sh", ".bash", ".bat", ".cmd",
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp",
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".css", ".scss", ".sass",
)

EXTRA_EXTS = (".md", ".json", ".txt", ".html", ".htm", ".svg", ".xml", ".yml", ".yaml")

# .tmp holds scratch output, including the Chrome profile a render writes while
# it runs. Those files are third-party code, not project source, so scanning
# them reports false failures.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "dist", "build", "out",
    ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".tmp",
}


def iter_files(raw_paths, exts):
    for raw in raw_paths:
        path = Path(raw)
        if path.is_file():
            yield path
            continue
        if not path.is_dir():
            print("skip missing: %s" % path, file=sys.stderr)
            continue
        for root, dirs, files in os.walk(str(path)):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in files:
                candidate = Path(root) / name
                if candidate.suffix.lower() in exts:
                    yield candidate


def read_text(path):
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.decode("utf-8", errors="replace")


def scan_file(path, limit):
    text = read_text(path)
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for col_no, ch in enumerate(line, 1):
            if ord(ch) > 127:
                code = "U+%04X" % ord(ch)
                snippet = line.strip()
                if len(snippet) > 100:
                    snippet = snippet[:100] + "..."
                hits.append((line_no, col_no, code, snippet))
                if len(hits) >= limit:
                    return hits
    return hits


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Scan engineering files for non-ASCII characters.")
    parser.add_argument("paths", nargs="+", help="files or directories")
    parser.add_argument("--ext", default="", help="comma-separated extensions to add")
    parser.add_argument("--all", action="store_true", help="also scan Markdown/JSON/text files")
    parser.add_argument("--limit", type=int, default=20, help="max hits reported per file")
    args = parser.parse_args()

    exts = set(DEFAULT_EXTS)
    if args.all:
        exts.update(EXTRA_EXTS)
    if args.ext:
        for item in args.ext.split(","):
            item = item.strip().lower()
            if item:
                exts.add(item if item.startswith(".") else "." + item)

    files = sorted(set(iter_files(args.paths, exts)))
    if not files:
        print("no matching files")
        return 0

    bad_files = 0
    bad_chars = 0
    for path in files:
        hits = scan_file(path, args.limit)
        if not hits:
            continue
        bad_files += 1
        print("%s" % path)
        for line_no, col_no, code, snippet in hits:
            print("  %d:%d  %s  %s" % (line_no, col_no, code, snippet))
            bad_chars += 1
        # Report the true count even when the per-file display is capped.
        total = sum(1 for line in read_text(path).splitlines()
                    for ch in line if ord(ch) > 127)
        if total > len(hits):
            print("  ... %d more non-ASCII character(s)" % (total - len(hits)))

    print("")
    print("scanned %d file(s), %d file(s) with non-ASCII, %d shown"
          % (len(files), bad_files, bad_chars))
    if bad_files:
        print("FAIL: engineering files must be pure ASCII")
        return 1
    print("OK: all scanned files are ASCII")
    return 0


if __name__ == "__main__":
    sys.exit(main())
