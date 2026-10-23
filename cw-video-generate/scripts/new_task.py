#!/usr/bin/env python
"""Create a video-task skeleton from the skill templates.

The skeleton is intentionally minimal: it gives you the directory contract,
pre-production skeleton, review log, reading-text schema, timeline-source
schema, and a run.bat placeholder. Asset scripts and the React page are
built per task (see references/pipeline.md).

Usage:
    python new_task.py ./my_task --title "My Topic"
    python new_task.py ./my_task --title "My Topic" --version v0.2 --force
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "assets" / "templates"

FILES = (
    ("pre-production.md", "pre-production/{version}/pre-production.md"),
    ("review.md", "pre-production/{version}/review.md"),
    ("review_log.md", "pre-production/review_log.md"),
    ("timeline_source.json", "production/{version}/toolbox/timeline_source.json"),
    ("reading_text.json", "production/{version}/toolbox/reading_text.json"),
    ("toolbox_README.md", "production/{version}/toolbox/README.md"),
    ("run.bat", "production/{version}/run.bat"),
    ("post-production_README.md", "post-production/README.md"),
)

DIRS = (
    "pre-production/{version}/research",
    "pre-production/resource",
    "production/{version}/toolbox",
    "post-production/audio/film",
    "post-production/web/src",
    ".tmp",
)


def render(template, title, version, today):
    text = template
    safe_title = title.replace("{{", "{ {").replace("}}", "} }")
    text = text.replace("{{TITLE_JSON}}", json.dumps(safe_title, ensure_ascii=False)[1:-1])
    text = text.replace("{{TITLE}}", safe_title)
    text = text.replace("{{VERSION}}", version)
    text = text.replace("{{DATE}}", today)
    return text


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Create a video-task skeleton.")
    parser.add_argument("task_dir", help="target task root")
    parser.add_argument("--title", required=True, help="video title")
    parser.add_argument("--version", default="v0.1", help="initial version (default v0.1)")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    args = parser.parse_args()

    root = Path(args.task_dir).resolve()
    if not TEMPLATES.is_dir():
        print("missing templates: %s" % TEMPLATES, file=sys.stderr)
        return 2
    if root.exists() and not root.is_dir():
        print("target exists and is not a directory: %s" % root, file=sys.stderr)
        return 2
    if root.exists() and any(root.iterdir()) and not args.force:
        print("target is not empty: %s (use --force to overwrite)" % root, file=sys.stderr)
        return 2

    for pattern in DIRS:
        (root / pattern.format(version=args.version)).mkdir(parents=True, exist_ok=True)
    for name in (".gitkeep",):
        (root / ".tmp" / name).write_text("", encoding="utf-8")
        (root / "post-production" / "audio" / "film" / name).write_text("", encoding="utf-8")
        (root / "post-production" / "web" / "src" / name).write_text("", encoding="utf-8")

    today = date.today().isoformat()
    written = []
    for source_name, target_pattern in FILES:
        source = TEMPLATES / source_name
        if not source.is_file():
            print("missing template: %s" % source, file=sys.stderr)
            return 2
        target = root / target_pattern.format(version=args.version)
        if target.exists() and not args.force:
            print("exists, skipped: %s" % target)
            continue
        text = render(source.read_text(encoding="utf-8"), args.title, args.version, today)
        if target.suffix.lower() in (".bat", ".cmd"):
            text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(str(target), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        written.append(target)

    print("created %s" % root)
    for target in written:
        print("  %s" % target.relative_to(root))
    print("")
    print("next:")
    print("  1. fill pre-production/%s/pre-production.md" % args.version)
    print("  2. put sources in pre-production/resource/ and research/")
    print("  3. build toolbox scripts and set %s/run.bat" % args.version)
    print("  4. read references/pipeline.md for the narration/page contracts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
