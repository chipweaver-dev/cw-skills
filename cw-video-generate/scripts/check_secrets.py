#!/usr/bin/env python
"""Scan a task tree for likely credentials before delivery.

This is a heuristic gate, not a substitute for keeping secrets in .env.
It reports the file, line and a masked sample; it never prints a full value.

Usage:
    python check_secrets.py <task_root>
    python check_secrets.py <task_root> --include .env
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "dist", "build", "out",
    ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
}

TEXT_EXTS = {
    ".py", ".bat", ".cmd", ".sh", ".bash", ".ps1", ".tcl",
    ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".css", ".html",
    ".env", ".xml", ".srt", ".ass", ".vtt",
}

PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "OpenAI-style key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "GitHub token"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "Slack token"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{20,}"), "bearer token"),
    (re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|passwd|authorization)\b"
        r"\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{16,})"
    ), "assigned credential"),
]

PLACEHOLDER = re.compile(
    r"(?i)(example|change[_ -]?me|your[_ -]?|placeholder|redacted|dummy|"
    r"sample|xxx+|<[^>]+>|\.\.\.|\$\{|os\.environ|getenv)"
)


def iter_files(raw_paths):
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
                if candidate.suffix.lower() in TEXT_EXTS or name == ".env":
                    yield candidate


def mask(value):
    value = value.strip().strip("'\"")
    if len(value) <= 8:
        return value[:2] + "***"
    return value[:6] + "***" + value[-2:]


def scan(path):
    try:
        if path.stat().st_size > 2 * 1024 * 1024:
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for pattern, kind in PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            sample = match.group(0)
            if PLACEHOLDER.search(sample):
                continue
            # A bare variable name is fine; only report something that looks
            # like a value or a private-key marker.
            if kind == "assigned credential":
                value = match.group(2) if match.lastindex and match.lastindex >= 2 else ""
                if PLACEHOLDER.search(value):
                    continue
                sample = value
            hits.append((line_no, kind, mask(sample)))
            break
    return hits


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Scan for likely credentials.")
    parser.add_argument("paths", nargs="+", help="files or directories")
    parser.add_argument("--include", default="", help="comma-separated extra extensions")
    args = parser.parse_args()

    global TEXT_EXTS
    if args.include:
        for item in args.include.split(","):
            item = item.strip().lower()
            if item:
                TEXT_EXTS.add(item if item.startswith(".") else "." + item)

    self_path = Path(__file__).resolve()
    files = sorted(set(path for path in iter_files(args.paths)
                       if path.resolve() != self_path))
    hits_total = 0
    files_with_hits = set()

    for path in files:
        hits = scan(path)
        if not hits:
            continue
        files_with_hits.add(path)
        for line_no, kind, sample in hits:
            print("%s:%d  [%s]  %s" % (path, line_no, kind, sample))
            hits_total += 1

    print("")
    print("scanned %d file(s), %d hit(s) in %d file(s)"
          % (len(files), hits_total, len(files_with_hits)))
    if hits_total:
        print("REVIEW: move real secrets to .env or a secret store; "
              "keep only variable names in products")
        return 1
    print("OK: no likely credentials found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
