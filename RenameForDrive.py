"""
Rename images so Google Drive name-sorting shows highest-rated first.

What this does:
- Takes one or more paths (files and/or folders). You can drag & drop onto this script on Windows.
- For each folder, it finds images named like "<elo>_<id>.<ext>" (e.g., 1180_cg.png).
- It renames them to "<rank>-<elo>_<id>.<ext>", where:
  - rank starts at 1 for the highest ELO and increases (ties broken by filename).
  - rank is zero-padded to the number of digits in the folder's image count, so
    ascending "Name" sort in Google Drive shows best images first.
- The original ELO remains in the filename after the dash.

Notes:
- This is a destructive rename. Prefer running on a copy intended for sharing/upload.
- Files that don't match the "<elo>_<id>.<ext>" pattern (or prior "<rank>-<elo>_<id>.<ext>") are skipped.
"""

import os
import re
import sys
import uuid
from typing import Dict, List, Optional, Tuple

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

# Patterns:
#  - Simple:        1180_cg
#  - With rank:     001-1180_cg, 001__1180_cg, 001-1180_cg_v2 (we only use text up to id)
PAT_SIMPLE = re.compile(r'^(?P<elo>\d+)_+(?P<id>[A-Za-z0-9]+)$')
PAT_WITH_RANK = re.compile(r'^(?P<rank>\d+)[-_]+(?P<elo>\d+)_+(?P<id>[A-Za-z0-9]+)$')


def is_image_file(path: str) -> bool:
    _, ext = os.path.splitext(path)
    return ext.lower() in IMAGE_EXTS


def parse_name(basename_no_ext: str) -> Optional[Tuple[int, str]]:
    """
    Returns (elo, id) if parseable, else None.
    Supports:
      - "<elo>_<id>"
      - "<rank>-<elo>_<id>" or "<rank>__<elo>_<id>"
    """
    m = PAT_WITH_RANK.match(basename_no_ext)
    if m:
        try:
            elo = int(m.group('elo'))
            ident = m.group('id')
            return elo, ident
        except ValueError:
            return None
    m = PAT_SIMPLE.match(basename_no_ext)
    if m:
        try:
            elo = int(m.group('elo'))
            ident = m.group('id')
            return elo, ident
        except ValueError:
            return None
    return None


def collect_targets(args: List[str]) -> Dict[str, List[str]]:
    """
    Group image files by their directory.
    - If arg is a directory: include image files from that directory (non-recursive).
    - If arg is a file: include it directly.
    """
    groups: Dict[str, List[str]] = {}
    for arg in args:
        path = os.path.abspath(arg)
        if os.path.isdir(path):
            for name in os.listdir(path):
                fpath = os.path.join(path, name)
                if os.path.isfile(fpath) and is_image_file(fpath):
                    groups.setdefault(path, []).append(fpath)
        elif os.path.isfile(path) and is_image_file(path):
            d = os.path.dirname(path) or os.getcwd()
            groups.setdefault(d, []).append(path)
        else:
            # skip non-existing or non-image files
            continue
    return groups


def plan_directory(dirpath: str, files: List[str]) -> List[Tuple[str, str]]:
    """
    Build a list of (old_path, new_basename) for the directory.
    Sorting key: elo desc, then case-insensitive basename asc for ties.
    Rank width: digits of count.
    """
    parsed: List[Tuple[str, int, str, str]] = []  # (path, elo, ident, basename_no_ext)
    for f in files:
        base = os.path.basename(f)
        name, ext = os.path.splitext(base)
        parts = parse_name(name)
        if parts is None:
            continue
        elo, ident = parts
        parsed.append((f, elo, ident, name))

    if not parsed:
        return []

    parsed.sort(key=lambda t: (-t[1], t[3].lower()))
    width = len(str(len(parsed)))

    ops: List[Tuple[str, str]] = []
    for idx, (path, elo, ident, _) in enumerate(parsed, start=1):
        _, ext = os.path.splitext(path)
        new_base = f"{str(idx).zfill(width)}-{elo}_{ident}{ext.lower()}"
        ops.append((path, new_base))
    return ops


def two_phase_rename(dirpath: str, operations: List[Tuple[str, str]]) -> None:
    """
    Do a safe two-phase rename in a directory to avoid transient name collisions:
      1) old -> tmp unique name
      2) tmp -> final
    Skips renames where old basename == final basename (case-insensitive on Windows).
    """
    # Phase 1: move to tmp names
    tmp_map: List[Tuple[str, str]] = []  # (tmp_path, final_path)
    for old_path, new_basename in operations:
        old_base = os.path.basename(old_path)
        if old_base.lower() == new_basename.lower():
            # Already has desired name
            continue
        tmp_name = f".renametmp.{uuid.uuid4().hex}.tmp"
        tmp_path = os.path.join(dirpath, tmp_name)
        final_path = os.path.join(dirpath, new_basename)
        os.rename(old_path, tmp_path)
        tmp_map.append((tmp_path, final_path))

    # Phase 2: move to final names
    for tmp_path, final_path in tmp_map:
        if os.path.exists(final_path):
            # Extremely unlikely if we generated unique ranking, but guard anyway
            base, ext = os.path.splitext(final_path)
            final_path = f"{base}__{uuid.uuid4().hex[:6]}{ext}"
        os.rename(tmp_path, final_path)
        print(f"{os.path.basename(tmp_path)} -> {os.path.basename(final_path)}")

    if tmp_map:
        print(f"Renamed {len(tmp_map)} file(s) in {dirpath}")
    else:
        print(f"No changes needed in {dirpath}")


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("Usage:")
        print("  Drag & drop files/folders onto this script, or run:")
        print("    python RenameForDrive.py <folder-or-file> [more ...]")
        return 1

    groups = collect_targets(argv[1:])
    if not groups:
        print("No image files found to process.")
        return 0

    for dirpath, files in groups.items():
        ops = plan_directory(dirpath, files)
        if not ops:
            print(f"No matching files in {dirpath}")
            continue
        two_phase_rename(dirpath, ops)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
