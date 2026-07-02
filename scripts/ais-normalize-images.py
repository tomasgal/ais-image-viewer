#!/usr/bin/env python3
"""
Normalize AI image metadata and anonymize filenames.

This maintenance script is intended for a simple self-hosted image directory.
For every JPEG/PNG file whose basename does not already match the anonymous
filename pattern, it:

1. removes embedded content-oriented metadata,
2. preserves selected technical metadata where available,
3. writes a small homogeneous XMP metadata profile identifying the file as
   AI-generated media,
4. renames the file to a random browser-safe name,
5. optionally regenerates the static viewer index.

The anonymous filename is also used as the processing marker. Files that already
match the pattern are skipped.

Requires the ExifTool CLI, usually installed on Debian/Raspberry Pi OS with:

    sudo apt install libimage-exiftool-perl
"""

from __future__ import annotations

import argparse
import re
import secrets
import shutil
import string
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ANON_RE = re.compile(r"^[a-z0-9]{4}(-[a-z0-9]{4}){3}$")
ALPHABET = string.ascii_lowercase + string.digits

DESCRIPTION = "AI-generated image"
CREATOR_TOOL = "AIs image viewer import pipeline"
DIGITAL_SOURCE_TYPE = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
KEYWORDS = ["ai-generated", "synthetic-media"]


def random_stem() -> str:
    return "-".join(
        "".join(secrets.choice(ALPHABET) for _ in range(4))
        for _ in range(4)
    )


def is_anonymized(path: Path) -> bool:
    return bool(ANON_RE.fullmatch(path.stem))


def new_unique_path(image_dir: Path, ext: str) -> Path:
    """Return a random target path that does not currently exist.

    The uniqueness check is performed on the complete filename including the
    extension. A matching random stem with a different extension is accepted.
    """

    ext = ext.lower()

    for _ in range(10000):
        candidate = image_dir / f"{random_stem()}{ext}"
        if not candidate.exists():
            return candidate

    raise RuntimeError("Could not generate a unique filename after many attempts")


def run_exiftool(cmd: list[str], dry_run: bool, allow_no_writable_warning: bool = False) -> bool:
    if dry_run:
        print("DRY-RUN CMD:", " ".join(str(x) for x in cmd))
        return True

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if stdout:
        print(stdout)

    if stderr:
        print(stderr, file=sys.stderr)

    if result.returncode == 0:
        return True

    if allow_no_writable_warning and "No writable tags set" in stderr and "Error" not in stderr:
        return True

    return False


def normalize_metadata(path: Path, dry_run: bool) -> bool:
    """Normalize metadata in two phases.

    Phase 1 removes embedded metadata while copying back selected technical
    tags from the original file. Phase 2 writes the homogeneous XMP profile.
    """

    strip_cmd = [
        "exiftool",
        "-m",
        "-overwrite_original",
        "-P",
        "-all=",
        "-tagsFromFile", "@",
        "-ICC_Profile:all",
        "-Orientation",
        "-SRGBRendering",
        str(path),
    ]

    if not run_exiftool(strip_cmd, dry_run, allow_no_writable_warning=True):
        print(f"ERROR: metadata strip failed: {path.name}", file=sys.stderr)
        return False

    set_cmd = [
        "exiftool",
        "-m",
        "-overwrite_original",
        "-P",
        f"-XMP-iptcExt:DigitalSourceType={DIGITAL_SOURCE_TYPE}",
        f"-XMP-dc:Description={DESCRIPTION}",
        f"-XMP-xmp:CreatorTool={CREATOR_TOOL}",
        "-XMP-dc:Subject=",
    ]

    for keyword in KEYWORDS:
        set_cmd.append(f"-XMP-dc:Subject+={keyword}")

    set_cmd.append(str(path))

    if not run_exiftool(set_cmd, dry_run):
        print(f"ERROR: metadata write failed: {path.name}", file=sys.stderr)
        return False

    return True


def regenerate_index(index_command: str | None, dry_run: bool) -> int:
    if not index_command:
        return 0

    if dry_run:
        print("DRY-RUN CMD:", index_command)
        return 0

    result = subprocess.run(index_command, shell=True, text=True)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize AI image metadata and anonymize filenames.")
    parser.add_argument("--image-dir", default="/srv/ais/images", help="Directory containing JPEG/PNG images.")
    parser.add_argument(
        "--index-command",
        default="",
        help="Optional command to regenerate the static index after successful processing.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen, but do not change files.")
    args = parser.parse_args()

    if shutil.which("exiftool") is None:
        print("ERROR: exiftool not found. Install libimage-exiftool-perl.", file=sys.stderr)
        return 1

    image_dir = Path(args.image_dir)

    if not image_dir.is_dir():
        print(f"ERROR: directory does not exist: {image_dir}", file=sys.stderr)
        return 1

    files = sorted(
        p for p in image_dir.iterdir()
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    )

    processed = 0
    skipped = 0
    failed = 0

    for path in files:
        if is_anonymized(path):
            skipped += 1
            continue

        target = new_unique_path(image_dir, path.suffix)

        print(f"PROCESS {path.name}")
        print(f"RENAME  {path.name} -> {target.name}")

        if not normalize_metadata(path, args.dry_run):
            failed += 1
            continue

        if args.dry_run:
            processed += 1
            continue

        try:
            if target.exists():
                print(f"ERROR: target already exists, skipping rename: {target.name}", file=sys.stderr)
                failed += 1
                continue

            path.rename(target)
            print(f"RENAMED {path.name} -> {target.name}")
            processed += 1
        except OSError as exc:
            print(f"ERROR: rename failed: {path.name}: {exc}", file=sys.stderr)
            failed += 1

    print(f"Done. To process: {processed}, already normalized: {skipped}, failed: {failed}")

    if failed == 0:
        return regenerate_index(args.index_command, args.dry_run)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
