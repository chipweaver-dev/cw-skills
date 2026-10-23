#!/usr/bin/env python
"""Validate post-production/publish/metadata.json against the film.

The publishing metadata (title, descriptions, hashtags, chapters, cover
mapping) is a deliverable, so it gets the same treatment as the timeline:
one file, derived numbers, and a deterministic check.

Checks:
  - required fields exist and have the right types
  - title / short description stay inside platform-friendly lengths
  - 3 to 8 hashtags, each starting with '#' and present in the short text
  - chapter count and start times match timeline.json segments
  - media.duration_seconds matches meta.duration (tolerance 0.5 s)
  - cover and master paths exist under post-production/
  - optional: mp4 duration agrees with the metadata (needs ffprobe)

Usage:
    python check_publish.py --root <task_root>
    python check_publish.py --root <task_root> --video post-production/film/master.mp4
    python check_publish.py --metadata m.json --timeline t.json --strict
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DURATION_TOL = 0.5
CHAPTER_TOL = 1.0
TITLE_MAX = 80
TITLE_WARN = 50
SHORT_MIN_WARN = 60
SHORT_MAX_WARN = 200
SHORT_MAX_ERROR = 320
LONG_MIN_ERROR = 100
HASHTAG_MIN = 3
HASHTAG_MAX = 8


class Report(object):
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def load_json(path):
    with open(str(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_clock(text):
    """Accept mm:ss or hh:mm:ss; return seconds or None."""
    if not isinstance(text, str) or not text.strip():
        return None
    parts = text.strip().split(":")
    if len(parts) not in (2, 3):
        return None
    try:
        values = [float(part) for part in parts]
    except ValueError:
        return None
    seconds = 0.0
    for value in values:
        seconds = seconds * 60.0 + value
    return seconds


def require(meta, key, kind, report):
    value = meta.get(key)
    if value is None:
        report.error("metadata.%s is missing" % key)
        return None
    if kind is str and not isinstance(value, str):
        report.error("metadata.%s must be a string" % key)
        return None
    if kind is list and not isinstance(value, list):
        report.error("metadata.%s must be an array" % key)
        return None
    if kind is dict and not isinstance(value, dict):
        report.error("metadata.%s must be an object" % key)
        return None
    return value


def check_text(meta, report):
    title = require(meta, "title", str, report)
    if title is not None:
        if not title.strip():
            report.error("metadata.title is empty")
        elif len(title) > TITLE_MAX:
            report.error("metadata.title is %d chars, max %d" % (len(title), TITLE_MAX))
        elif len(title) > TITLE_WARN:
            report.warn("metadata.title is %d chars; some platforms truncate near %d"
                        % (len(title), TITLE_WARN))

    short = require(meta, "short_description", str, report)
    if short is not None:
        if not short.strip():
            report.error("metadata.short_description is empty")
        elif len(short) > SHORT_MAX_ERROR:
            report.error("metadata.short_description is %d chars, max %d"
                         % (len(short), SHORT_MAX_ERROR))
        elif not (SHORT_MIN_WARN <= len(short) <= SHORT_MAX_WARN):
            report.warn("metadata.short_description is %d chars; the usual target is %d-%d"
                        % (len(short), SHORT_MIN_WARN, SHORT_MAX_WARN))

    long_text = require(meta, "long_description", str, report)
    if long_text is not None and len(long_text.strip()) < LONG_MIN_ERROR:
        report.error("metadata.long_description is %d chars, needs at least %d"
                     % (len(long_text.strip()), LONG_MIN_ERROR))


def check_hashtags(meta, report):
    tags = require(meta, "hashtags", list, report)
    if tags is None:
        return
    if not (HASHTAG_MIN <= len(tags) <= HASHTAG_MAX):
        report.error("metadata.hashtags has %d entries, expected %d-%d"
                     % (len(tags), HASHTAG_MIN, HASHTAG_MAX))
    short = meta.get("short_description")
    for index, tag in enumerate(tags):
        if not isinstance(tag, str) or not tag.strip():
            report.error("metadata.hashtags[%d] must be a non-empty string" % index)
            continue
        if not tag.startswith("#"):
            report.error("metadata.hashtags[%d] %r must start with '#'" % (index, tag))
        if any(ch.isspace() for ch in tag):
            report.error("metadata.hashtags[%d] %r contains whitespace" % (index, tag))
        if isinstance(short, str) and tag not in short:
            report.warn("metadata.hashtags[%d] %r does not appear in short_description"
                        % (index, tag))

    plain = require(meta, "tags", list, report)
    if plain is not None and not plain:
        report.warn("metadata.tags is empty; search tags differ from on-screen hashtags")


def check_media(meta, timeline, post_dir, report):
    media = require(meta, "media", dict, report)
    duration = None
    if isinstance(timeline.get("meta"), dict):
        value = timeline["meta"].get("duration")
        if is_number(value):
            duration = float(value)
    if media is not None:
        value = media.get("duration_seconds")
        if not is_number(value):
            report.error("metadata.media.duration_seconds must be a number")
        elif duration is not None and abs(float(value) - duration) > DURATION_TOL:
            report.error("metadata.media.duration_seconds %.3f vs timeline %.3f"
                         % (float(value), duration))
        master = media.get("master")
        if isinstance(master, str) and master:
            if not (post_dir / master).is_file():
                report.error("metadata.media.master not found: %s" % (post_dir / master))
        else:
            report.error("metadata.media.master must be a relative path")
        loudness = media.get("loudness")
        if not isinstance(loudness, dict):
            report.warn("metadata.media.loudness is missing; quote the MP4 measurement")

    cover = require(meta, "cover", dict, report)
    if cover is not None:
        for key in ("16x9", "9x16"):
            rel = cover.get(key)
            if not isinstance(rel, str) or not rel:
                report.error("metadata.cover.%s must be a relative path" % key)
            elif not (post_dir / rel).is_file():
                report.error("metadata.cover.%s not found: %s" % (key, post_dir / rel))


def check_chapters(meta, timeline, report):
    chapters = require(meta, "chapters", list, report)
    if chapters is None:
        return
    segments = timeline.get("segments")
    if not isinstance(segments, list):
        report.error("timeline.segments must be an array")
        return
    if len(chapters) != len(segments):
        report.error("metadata.chapters has %d entries, timeline has %d segments"
                     % (len(chapters), len(segments)))
    previous = None
    for index, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            report.error("metadata.chapters[%d] must be an object" % index)
            continue
        start = parse_clock(chapter.get("start"))
        if start is None:
            report.error("metadata.chapters[%d].start must be mm:ss" % index)
            continue
        title = chapter.get("title")
        if not isinstance(title, str) or not title.strip():
            report.error("metadata.chapters[%d].title is empty" % index)
        if previous is not None and start < previous:
            report.error("metadata.chapters[%d] starts before the previous chapter" % index)
        previous = start
        if index < len(segments):
            t0 = segments[index].get("t0")
            if is_number(t0) and abs(start - float(t0)) > CHAPTER_TOL:
                report.error("metadata.chapters[%d].start %.1f s vs segment %s t0 %.1f s"
                             % (index, start, segments[index].get("id"), float(t0)))


def resolve_ffprobe(explicit):
    if explicit:
        return explicit
    found = shutil.which("ffprobe")
    if found:
        return found
    return None


def probe_duration(ffprobe, path, report):
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nk=1:nw=1", str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except OSError as exc:
        report.warn("cannot run ffprobe: %s" % exc)
        return None
    if proc.returncode != 0:
        report.warn("ffprobe failed on %s" % path)
        return None
    try:
        return float(proc.stdout.decode("utf-8", "replace").strip())
    except ValueError:
        report.warn("ffprobe returned a non-number for %s" % path)
        return None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Validate publishing metadata against the film.")
    parser.add_argument("--root", help="task root (contains pre-production/production/post-production)")
    parser.add_argument("--metadata", help="path to publish/metadata.json")
    parser.add_argument("--timeline", help="path to timeline.json")
    parser.add_argument("--video", help="optional mp4 to probe for its real duration")
    parser.add_argument("--ffprobe", help="explicit ffprobe path")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args()

    if args.root:
        root = Path(args.root).resolve()
    else:
        root = Path(".").resolve()
    post_dir = root / "post-production"
    metadata_path = Path(args.metadata) if args.metadata else post_dir / "publish" / "metadata.json"
    timeline_path = Path(args.timeline) if args.timeline else post_dir / "timeline.json"

    report = Report()
    if not metadata_path.is_file():
        print("missing metadata: %s" % metadata_path, file=sys.stderr)
        return 2
    if not timeline_path.is_file():
        print("missing timeline: %s" % timeline_path, file=sys.stderr)
        return 2
    try:
        meta = load_json(metadata_path)
        timeline = load_json(timeline_path)
    except (ValueError, OSError) as exc:
        print("cannot read input: %s" % exc, file=sys.stderr)
        return 2
    if not isinstance(meta, dict):
        print("metadata must be a JSON object", file=sys.stderr)
        return 2

    check_text(meta, report)
    check_hashtags(meta, report)
    check_media(meta, timeline, post_dir, report)
    check_chapters(meta, timeline, report)
    require(meta, "credits", dict, report)

    video_duration = None
    if args.video:
        video_path = Path(args.video)
        if not video_path.is_file():
            report.error("video not found: %s" % video_path)
        else:
            ffprobe = resolve_ffprobe(args.ffprobe)
            if ffprobe is None:
                report.warn("ffprobe not found; skipped video duration check")
            else:
                video_duration = probe_duration(ffprobe, video_path, report)
                media = meta.get("media")
                if video_duration is not None and isinstance(media, dict):
                    value = media.get("duration_seconds")
                    if is_number(value) and abs(video_duration - float(value)) > DURATION_TOL:
                        report.error("video %.3f s vs metadata.media.duration_seconds %.3f"
                                     % (video_duration, float(value)))

    errors = report.errors
    warnings = report.warnings
    if args.strict:
        errors = errors + ["WARN: " + item for item in warnings]
        warnings = []

    payload = {
        "metadata": str(metadata_path),
        "timeline": str(timeline_path),
        "video_duration": video_duration,
        "chapters": len(meta.get("chapters") or []),
        "hashtags": len(meta.get("hashtags") or []),
        "errors": errors,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Publish check")
        print("  metadata : %s" % metadata_path)
        print("  timeline : %s" % timeline_path)
        print("  chapters : %d" % payload["chapters"])
        print("  hashtags : %d" % payload["hashtags"])
        if video_duration is not None:
            print("  video    : %.3f s" % video_duration)
        for item in report.errors:
            print("  ERROR: %s" % item)
        for item in report.warnings:
            print("  WARN : %s" % item)
        if errors:
            print("result: FAIL (%d error(s), %d warning(s))" % (len(errors), len(warnings)))
        else:
            print("result: OK (%d warning(s))" % len(warnings))

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
