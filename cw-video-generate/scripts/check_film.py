#!/usr/bin/env python
"""Validate timeline.json / subtitles.json / audio duration for a video task.

Checks the invariants the page relies on:
  - segments are contiguous and inside meta.duration
  - beats are ordered, unique, non-overlapping, inside their segment
  - chapter cards and the end card have sane windows
  - subtitle cues are ordered, non-overlapping, inside their segment,
    and do not run into a chapter card or the end card
  - an optional audio file matches meta.duration

Usage:
    python check_film.py --root <task_root>
    python check_film.py --root <task_root> --audio post-production/audio/film/film_full_scored.mp3
    python check_film.py --timeline t.json --subtitles s.json --strict
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_TOL = 0.02
DEFAULT_AUDIO_TOL = 0.10


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


def looks_like_sentence(text):
    """Long or punctuated labels read as titles, not breadcrumb keywords."""
    if len(text.strip()) > 12:
        return True
    # ASCII marks plus the ideographic comma/stop and full-width comma, colon,
    # semicolon. Built from code points so this file stays pure ASCII.
    marks = ":;,." + "".join(chr(code) for code in (0x3001, 0x3002, 0xFF0C, 0xFF1A, 0xFF1B))
    return any(mark in text for mark in marks)


def load_json(path):
    with open(str(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_paths(args):
    if args.root:
        root = Path(args.root).resolve()
        timeline = Path(args.timeline) if args.timeline else root / "post-production" / "timeline.json"
        subtitles = Path(args.subtitles) if args.subtitles else root / "post-production" / "subtitles.json"
    else:
        timeline = Path(args.timeline) if args.timeline else Path("post-production/timeline.json")
        subtitles = Path(args.subtitles) if args.subtitles else Path("post-production/subtitles.json")
    return timeline, subtitles


def check_timeline(timeline, tol, report):
    stats = {"segments": 0, "beats": 0, "duration": None}
    empty = ({}, {}, {})
    meta = timeline.get("meta")
    if not isinstance(meta, dict):
        report.error("timeline.meta must be an object")
        return (stats,) + empty
    duration = meta.get("duration")
    if not is_number(duration) or duration <= 0:
        report.error("meta.duration must be a positive number")
        return (stats,) + empty
    stats["duration"] = float(duration)

    crumb_nodes = meta.get("crumb_nodes") or []
    if not isinstance(crumb_nodes, list):
        report.error("meta.crumb_nodes must be an array")
        crumb_nodes = []
    for index, label in enumerate(crumb_nodes):
        if not isinstance(label, str) or not label.strip():
            report.error("meta.crumb_nodes[%d] must be a non-empty string" % index)

    segments = timeline.get("segments")
    if not isinstance(segments, list) or not segments:
        report.error("timeline.segments must be a non-empty array")
        return (stats,) + empty

    seg_by_id = {}
    beat_by_id = {}
    beat_owner = {}
    previous_end = None
    last_beat_end = None

    for s_index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            report.error("segments[%d] must be an object" % s_index)
            continue
        sid = segment.get("id")
        if not isinstance(sid, str) or not sid:
            report.error("segments[%d].id must be a non-empty string" % s_index)
            continue
        if sid in seg_by_id:
            report.error("duplicate segment id %r" % sid)
        seg_by_id[sid] = segment

        # A crumb that repeats a sentence-like chapter title is the usual
        # failure mode when labels are generated from the card row instead of
        # authored as keywords. A one-word title ("router") is a fine crumb.
        title = segment.get("title")
        node = crumb_nodes[s_index] if s_index < len(crumb_nodes) else None
        if (isinstance(title, str) and isinstance(node, str)
                and node.strip() == title.strip()
                and looks_like_sentence(node)):
            report.warn("crumb node %r is the chapter title; crumbs should be "
                        "short keywords" % node)

        t0 = segment.get("t0")
        t1 = segment.get("t1")
        if not is_number(t0) or not is_number(t1):
            report.error("segment %s: t0/t1 must be numbers" % sid)
            continue
        if t1 <= t0:
            report.error("segment %s: t1 (%.3f) must be greater than t0 (%.3f)" % (sid, t1, t0))
        if t0 < -tol:
            report.error("segment %s: t0 %.3f is negative" % (sid, t0))
        if t1 > duration + tol:
            report.error("segment %s: t1 %.3f exceeds duration %.3f" % (sid, t1, duration))

        if previous_end is None:
            if abs(t0) > tol:
                report.warn("first segment starts at %.3f, expected 0" % t0)
        else:
            delta = t0 - previous_end
            if delta > tol:
                report.error("gap of %.3f s before segment %s" % (delta, sid))
            elif delta < -tol:
                report.error("segments overlap by %.3f s before segment %s" % (-delta, sid))
        previous_end = t1

        beats = segment.get("beats")
        if not isinstance(beats, list) or not beats:
            report.warn("segment %s has no beats" % sid)
            beats = []

        previous_beat_end = None
        for b_index, beat in enumerate(beats):
            if not isinstance(beat, dict):
                report.error("segment %s beats[%d] must be an object" % (sid, b_index))
                continue
            bid = beat.get("id")
            if not isinstance(bid, str) or not bid:
                report.error("segment %s beats[%d].id must be a non-empty string" % (sid, b_index))
                continue
            if bid in beat_by_id:
                report.error("duplicate beat id %r" % bid)
            beat_by_id[bid] = beat
            beat_owner[bid] = sid

            # crumb indexes crumb_nodes from 0; an off-by-one is invisible
            # until the page starts lighting the wrong node.
            crumb = beat.get("crumb")
            if crumb is not None and not beat.get("crumb_all", False):
                if not is_number(crumb) or int(crumb) != crumb:
                    report.error("beat %s: crumb must be an integer index" % bid)
                elif crumb_nodes and not (0 <= crumb < len(crumb_nodes)):
                    report.error("beat %s: crumb %d outside crumb_nodes (0..%d)"
                                 % (bid, crumb, len(crumb_nodes) - 1))

            b_t0 = beat.get("t0")
            b_t1 = beat.get("t1")
            if not is_number(b_t0) or not is_number(b_t1):
                report.error("beat %s: t0/t1 must be numbers" % bid)
                continue
            if b_t1 <= b_t0:
                report.error("beat %s: t1 (%.3f) must be greater than t0 (%.3f)" % (bid, b_t1, b_t0))
            if b_t0 < t0 - tol:
                report.error("beat %s starts before segment %s (%.3f < %.3f)" % (bid, sid, b_t0, t0))
            if b_t1 > t1 + tol:
                report.error("beat %s ends after segment %s (%.3f > %.3f)" % (bid, sid, b_t1, t1))
            if previous_beat_end is not None:
                delta = b_t0 - previous_beat_end
                if delta < -tol:
                    report.error("beat %s overlaps previous beat by %.3f s" % (bid, -delta))
                elif delta > tol:
                    report.warn("gap of %.3f s before beat %s" % (delta, bid))
            previous_beat_end = b_t1

            for cue in beat.get("keywords", []) or []:
                if not isinstance(cue, dict):
                    continue
                at = cue.get("at")
                if is_number(at) and (at < -tol or at > (b_t1 - b_t0) + tol):
                    report.warn("beat %s keyword %r: at %.3f outside beat duration %.3f"
                                % (bid, cue.get("key"), at, b_t1 - b_t0))
                t = cue.get("t")
                if is_number(t) and (t < b_t0 - tol or t > b_t1 + tol):
                    report.warn("beat %s keyword %r: t %.3f outside beat" % (bid, cue.get("key"), t))

            for stage in beat.get("stage", []) or []:
                if not isinstance(stage, dict):
                    continue
                at = stage.get("at")
                if is_number(at) and (at < -tol or at > (b_t1 - b_t0) + tol):
                    report.warn("beat %s stage %r: at %.3f outside beat duration %.3f"
                                % (bid, stage.get("beat"), at, b_t1 - b_t0))
                t = stage.get("t")
                if is_number(t) and (t < b_t0 - tol or t > b_t1 + tol):
                    report.warn("beat %s stage %r: t %.3f outside beat" % (bid, stage.get("beat"), t))

        card = segment.get("card")
        if card is not None:
            if not isinstance(card, dict):
                report.error("segment %s: card must be an object or null" % sid)
            else:
                c_t0 = card.get("t0")
                c_t1 = card.get("t1")
                if not is_number(c_t0) or not is_number(c_t1):
                    report.error("segment %s: card t0/t1 must be numbers" % sid)
                elif c_t1 <= c_t0:
                    report.error("segment %s: card t1 must be greater than t0" % sid)
                else:
                    if abs(c_t0 - t0) > tol:
                        report.error("segment %s: card.t0 %.3f != segment.t0 %.3f" % (sid, c_t0, t0))
                    if beats and isinstance(beats[0], dict) and is_number(beats[0].get("t0")):
                        first_beat = beats[0]["t0"]
                        if abs(c_t1 - first_beat) > tol:
                            report.error("segment %s: card.t1 %.3f != first beat t0 %.3f"
                                         % (sid, c_t1, first_beat))
                    if c_t1 > t1 + tol:
                        report.error("segment %s: card ends after segment" % sid)
        elif beats and isinstance(beats[0], dict) and is_number(beats[0].get("t0")):
            if beats[0]["t0"] - t0 > tol:
                report.warn("segment %s: %.3f s of silence before first beat but no card"
                            % (sid, beats[0]["t0"] - t0))

        if beats and isinstance(beats[-1], dict) and is_number(beats[-1].get("t1")):
            last_beat_end = beats[-1]["t1"]

    info = timeline.get("meta", {}).get("end_card")
    if info is not None:
        if not isinstance(info, dict):
            report.error("meta.end_card must be an object or null")
        else:
            e_t0 = info.get("t0")
            e_t1 = info.get("t1")
            if not is_number(e_t0) or not is_number(e_t1):
                report.error("meta.end_card t0/t1 must be numbers")
            elif e_t1 <= e_t0:
                report.error("meta.end_card t1 must be greater than t0")
            else:
                if e_t1 > duration + tol:
                    report.error("meta.end_card ends at %.3f, beyond duration %.3f" % (e_t1, duration))
                if last_beat_end is not None and e_t0 < last_beat_end - tol:
                    report.error("meta.end_card starts %.3f s before the last beat ends"
                                 % (last_beat_end - e_t0))

    if segments:
        last_segment = segments[-1]
        if isinstance(last_segment, dict) and is_number(last_segment.get("t1")):
            if abs(last_segment["t1"] - duration) > tol:
                report.warn("last segment ends at %.3f, duration is %.3f"
                            % (last_segment["t1"], duration))

    for gate in timeline.get("gates", []) or []:
        if not isinstance(gate, dict):
            continue
        at = gate.get("at")
        if is_number(at) and (at < -tol or at > duration + tol):
            report.error("gate %r: at %.3f outside duration" % (gate.get("id"), at))
        to_id = gate.get("to")
        if isinstance(to_id, str) and to_id not in seg_by_id:
            report.error("gate %r: unknown target segment %r" % (gate.get("id"), to_id))

    stats["segments"] = len(seg_by_id)
    stats["beats"] = len(beat_by_id)
    return stats, seg_by_id, beat_by_id, beat_owner


def check_subtitles(subtitles, seg_by_id, beat_owner, duration, tol, report):
    stats = {"cues": 0}
    if subtitles is None:
        return stats
    cues = subtitles.get("cues")
    if not isinstance(cues, list):
        report.error("subtitles.cues must be an array")
        return stats

    end_card = subtitles.get("_end_card")
    previous = None
    for index, cue in enumerate(cues):
        if not isinstance(cue, dict):
            report.error("cues[%d] must be an object" % index)
            continue
        text = cue.get("text")
        if not isinstance(text, str) or not text.strip():
            report.error("cues[%d].text must be a non-empty string" % index)
        t0 = cue.get("t0")
        t1 = cue.get("t1")
        if not is_number(t0) or not is_number(t1):
            report.error("cues[%d].t0/t1 must be numbers" % index)
            continue
        if t1 <= t0:
            report.error("cues[%d]: t1 (%.3f) must be greater than t0 (%.3f)" % (index, t1, t0))
        if t0 < -tol:
            report.error("cues[%d]: negative t0" % index)
        if t1 > duration + tol:
            report.error("cues[%d]: t1 %.3f exceeds duration %.3f" % (index, t1, duration))

        sid = cue.get("segment")
        if not isinstance(sid, str) or sid not in seg_by_id:
            report.error("cues[%d]: unknown segment %r" % (index, sid))
        else:
            segment = seg_by_id[sid]
            s_t0 = segment.get("t0")
            s_t1 = segment.get("t1")
            if is_number(s_t0) and t0 < s_t0 - tol:
                report.error("cues[%d]: starts before segment %s" % (index, sid))
            if is_number(s_t1) and t1 > s_t1 + tol:
                report.error("cues[%d]: runs into the next segment (%s)" % (index, sid))
            card = segment.get("card")
            if isinstance(card, dict) and is_number(card.get("t1")):
                if t0 < card["t1"] - tol and t1 > card.get("t0", 0) + tol:
                    report.error("cues[%d]: overlaps chapter card of %s" % (index, sid))

        bid = cue.get("beat")
        if isinstance(bid, str) and bid in beat_owner:
            if beat_owner[bid] != sid:
                report.error("cues[%d]: beat %s belongs to %s, not %s"
                             % (index, bid, beat_owner[bid], sid))

        if end_card is not None:
            e_t0 = end_card.get("t0") if isinstance(end_card, dict) else None
            if is_number(e_t0) and t1 > e_t0 + tol:
                report.error("cues[%d]: runs into the end card" % index)

        if previous is not None:
            p_t0 = previous[0]
            p_t1 = previous[1]
            if t0 < p_t0 - tol:
                report.error("cues[%d]: not sorted by t0" % index)
            if t0 < p_t1 - tol:
                report.error("cues[%d]: overlaps previous cue by %.3f s" % (index, p_t1 - t0))
        previous = (t0, t1)

    stats["cues"] = len(cues)
    return stats


def resolve_ffprobe(explicit):
    if explicit:
        return explicit
    found = shutil.which("ffprobe")
    if found:
        return found
    env_dir = os.environ.get("FFMPEG_DIR")
    if env_dir:
        candidate = Path(env_dir) / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if candidate.is_file():
            return str(candidate)
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
        report.warn("ffprobe failed on %s: %s"
                    % (path, proc.stderr.decode("utf-8", "replace").strip()[:300]))
        return None
    text = proc.stdout.decode("utf-8", "replace").strip()
    try:
        return float(text)
    except ValueError:
        report.warn("ffprobe returned a non-number: %r" % text[:100])
        return None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Validate a video task's clock and subtitles.")
    parser.add_argument("--root", help="task root (contains pre-production/production/post-production)")
    parser.add_argument("--timeline", help="path to timeline.json")
    parser.add_argument("--subtitles", help="path to subtitles.json")
    parser.add_argument("--audio", help="optional audio file (master/scored track)")
    parser.add_argument("--audio-role", default="master", choices=("master", "narration", "bed"),
                        help="master/bed must match duration; narration may be shorter")
    parser.add_argument("--ffprobe", help="explicit ffprobe path")
    parser.add_argument("--tol", type=float, default=DEFAULT_TOL, help="structural tolerance (s)")
    parser.add_argument("--audio-tol", type=float, default=DEFAULT_AUDIO_TOL,
                        help="audio duration tolerance (s)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args()

    timeline_path, subtitles_path = resolve_paths(args)
    report = Report()

    if not timeline_path.is_file():
        print("missing timeline: %s" % timeline_path, file=sys.stderr)
        return 2
    try:
        timeline = load_json(timeline_path)
    except (ValueError, OSError) as exc:
        print("cannot read timeline: %s" % exc, file=sys.stderr)
        return 2

    stats, seg_by_id, _beat_ids, beat_owner = check_timeline(timeline, args.tol, report)

    duration = stats.get("duration") or 0.0
    subtitles = None
    if subtitles_path.is_file():
        try:
            subtitles = load_json(subtitles_path)
        except (ValueError, OSError) as exc:
            report.error("cannot read subtitles: %s" % exc)
        if subtitles is not None:
            subtitles["_end_card"] = timeline.get("meta", {}).get("end_card")
            subtitle_stats = check_subtitles(
                subtitles, seg_by_id, beat_owner, duration, args.tol, report
            )
            stats.update(subtitle_stats)
    else:
        report.warn("no subtitles file: %s" % subtitles_path)

    audio_duration = None
    if args.audio:
        audio_path = Path(args.audio)
        if not audio_path.is_file():
            report.error("audio file not found: %s" % audio_path)
        else:
            ffprobe = resolve_ffprobe(args.ffprobe)
            if ffprobe is None:
                report.warn("ffprobe not found; skipped audio duration check")
            else:
                audio_duration = probe_duration(ffprobe, audio_path, report)
                if audio_duration is not None:
                    delta = audio_duration - duration
                    is_error = abs(delta) > args.audio_tol and args.audio_role in ("master", "bed")
                    message = ("audio %.3f s vs timeline %.3f s (delta %+.3f s)"
                               % (audio_duration, duration, delta))
                    if is_error:
                        report.error(message)
                    elif abs(delta) > args.audio_tol:
                        report.warn(message + "; expected for a narration track")

    errors = report.errors
    warnings = report.warnings
    if args.strict:
        errors = errors + ["WARN: " + item for item in warnings]
        warnings = []

    payload = {
        "timeline": str(timeline_path),
        "subtitles": str(subtitles_path) if subtitles_path.is_file() else None,
        "audio": args.audio,
        "audio_duration": audio_duration,
        "stats": stats,
        "errors": errors,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Film check")
        print("  timeline : %s" % timeline_path)
        if subtitles_path.is_file():
            print("  subtitles: %s" % subtitles_path)
        print("  duration : %.3f s" % duration)
        print("  segments : %d" % stats.get("segments", 0))
        print("  beats    : %d" % stats.get("beats", 0))
        print("  cues     : %d" % stats.get("cues", 0))
        if audio_duration is not None:
            print("  audio    : %.3f s (%+.3f s)" % (audio_duration, audio_duration - duration))
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
