#!/usr/bin/env python3
"""
MakeSlide - read pending Live Editor annotations (AI-applied layer)

Reads <directory>/annotations.jsonl (written by the Live Slide Editor's
"Annotate" mode via POST /api/annotations) and prints each pending annotation
so the agent can apply the requested change (effects, animation, layout, etc.)
and then clear the list.

Usage:
    python3 scripts/read_annotations.py [directory]
    python3 scripts/read_annotations.py [directory] --clear

Output format (one per annotation):
    #N  slide=2  selector=h1  instruction="give this a slide-in-from-left"
        element: <h1>Title text here...

--clear: after printing, delete annotations.jsonl (call this only after applying).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ANNOTATIONS_FILENAME = "annotations.jsonl"


def read_annotations(dir_path: Path) -> list[dict]:
    f = dir_path / ANNOTATIONS_FILENAME
    if not f.exists():
        return []
    out: list[dict] = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def clear_annotations(dir_path: Path) -> None:
    (dir_path / ANNOTATIONS_FILENAME).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read MakeSlide live-editor annotations")
    parser.add_argument("directory", nargs="?", default=".",
                        help="Directory containing annotations.jsonl (default: cwd)")
    parser.add_argument("--clear", action="store_true",
                        help="Delete annotations.jsonl after printing (call after applying)")
    args = parser.parse_args()

    dir_path = Path(args.directory).resolve()
    if not dir_path.is_dir():
        print(f"error: not a directory: {dir_path}", file=sys.stderr)
        return 1

    annotations = read_annotations(dir_path)
    if not annotations:
        print(f"[make-slide] no pending annotations in {dir_path}")
        return 0

    for i, rec in enumerate(annotations, 1):
        slide = rec.get("slide", "?")
        selector = rec.get("selector", "?")
        instruction = rec.get("instruction", "")
        snippet = rec.get("snippet", "")
        print(f"#{i}  slide={slide}  selector={selector}")
        print(f"    instruction: {instruction}")
        if snippet:
            print(f"    element: {snippet}")

    print()
    print(f"[make-slide] {len(annotations)} pending annotation(s) in {dir_path}")

    if args.clear:
        clear_annotations(dir_path)
        print("[make-slide] annotations.jsonl cleared")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
