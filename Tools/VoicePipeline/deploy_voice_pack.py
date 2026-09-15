#!/usr/bin/env python3
"""Stage a recorded actor pack into Vengeance-ready OGG files."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

MASTER_RE = re.compile(
    r"^[A-Za-z0-9_]+(?:__(?:controlled|angry|distressed|panicked))?(?: \d+)?\.(?:wav|ogg)$",
    re.IGNORECASE,
)


def inspect_wav(path: Path):
    with wave.open(str(path), "rb") as wav:
        return wav.getnchannels(), wav.getframerate(), wav.getsampwidth()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("masters", type=Path, help="folder containing approved mono WAV/OGG masters")
    parser.add_argument("target", type=Path, help="staging voice-ID folder")
    parser.add_argument("--ffmpeg", help="path to ffmpeg.exe; otherwise PATH is searched")
    parser.add_argument("--bitrate", default="128k")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-nonstandard-master", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()

    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    sources = sorted(
        p for p in args.masters.iterdir()
        if p.is_file() and p.suffix.lower() in {".wav", ".ogg"}
    )
    if not sources:
        raise SystemExit("No .wav or .ogg masters found")

    args.target.mkdir(parents=True, exist_ok=True)

    for src in sources:
        if not MASTER_RE.match(src.name):
            raise SystemExit(f"Invalid master filename: {src.name}")

        dst = args.target / (src.stem + ".ogg")
        if dst.exists() and not args.force:
            raise SystemExit(f"Refusing to overwrite {dst}; use --force")

        if src.suffix.lower() == ".ogg":
            shutil.copy2(src, dst)
            print(f"COPY {src.name} -> {dst.name}")
            continue

        channels, rate, sample_width = inspect_wav(src)
        if not args.allow_nonstandard_master:
            if channels != 1:
                raise SystemExit(f"{src.name}: recording master must be mono, got {channels} channels")
            if rate != 48000:
                raise SystemExit(f"{src.name}: recording master must be 48000 Hz, got {rate}")
            if sample_width != 3:
                raise SystemExit(
                    f"{src.name}: recording master should be 24-bit PCM (3 bytes/sample), got {sample_width}"
                )

        if not ffmpeg:
            raise SystemExit(
                "ffmpeg not found. Install/provide ffmpeg or supply pre-encoded OGG masters."
            )

        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y" if args.force else "-n",
            "-i", str(src),
            "-ac", "1",
            "-ar", "44100",
            "-c:a", "libvorbis",
            "-b:a", args.bitrate,
            str(dst),
        ]
        subprocess.run(cmd, check=True)
        print(f"ENCODE {src.name} -> {dst.name}")

    if not args.skip_validation:
        validator = Path(__file__).with_name("validate_voice_pack.py")
        cmd = [sys.executable, str(validator), str(args.target)]
        result = subprocess.run(cmd)
        if result.returncode:
            raise SystemExit(result.returncode)

    print(f"Staged {len(sources)} file(s) in {args.target}")


if __name__ == "__main__":
    main()
