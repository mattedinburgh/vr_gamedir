#!/usr/bin/env python3
"""Validate a staged situational voice actor pack."""

from __future__ import annotations

import argparse
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

NAME_RE = re.compile(
    r"^(?P<event>[A-Za-z0-9_]+)(?:__(?P<emotion>controlled|angry|distressed|panicked))?(?: (?P<variant>\d+))?\.ogg$",
    re.IGNORECASE,
)
PRODUCTION_EMOTION_REQUIREMENTS = {
    "GOT_HIT_GUNFIRE": {"controlled", "distressed", "panicked"},
    "GOT_HIT_BLOODLOSS": {"distressed", "panicked"},
    "GOT_HIT_EXPLOSION": {"controlled", "distressed", "panicked"},
    "RUN_AWAY": {"controlled", "distressed", "panicked"},
    "OUT_OF_AMMO": {"controlled", "distressed"},
    "NOTICED_UNSEEN": {"controlled", "distressed", "panicked"},
    "ALERT": {"controlled", "distressed"},
}


def parse_ogg(path: Path):
    data = path.read_bytes()
    ident = data.find(b"\x01vorbis")
    if ident < 0:
        raise ValueError("missing Vorbis identification header")
    channels = data[ident + 11]
    rate = struct.unpack_from("<I", data, ident + 12)[0]
    nominal = struct.unpack_from("<i", data, ident + 20)[0]
    page = data.rfind(b"OggS")
    granule = struct.unpack_from("<Q", data, page + 6)[0] if page >= 0 else 0
    duration = granule / rate if rate else 0.0
    return channels, rate, nominal, duration


def load_baseline(path: Path):
    return [
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=Path)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(__file__).with_name("baseline_events.txt"),
    )
    parser.add_argument("--complete", action="store_true")
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()

    errors = []
    warnings = []
    banks = defaultdict(lambda: {"base": False, "variants": set()})
    event_emotions = defaultdict(set)

    files = sorted(args.pack.glob("*.ogg"))
    if not files:
        errors.append("pack contains no .ogg files")

    for path in files:
        match = NAME_RE.match(path.name)
        if not match:
            errors.append(f"{path.name}: invalid filename")
            continue

        event = match.group("event").upper()
        emotion = (match.group("emotion") or "legacy").lower()
        variant = match.group("variant")
        bank = banks[(event, emotion)]
        if variant is None:
            bank["base"] = True
        else:
            bank["variants"].add(int(variant))
        event_emotions[event].add(emotion)

        try:
            channels, rate, nominal, duration = parse_ogg(path)
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            continue

        if channels != 1:
            errors.append(f"{path.name}: must be mono, got {channels} channels")
        if rate != 44100:
            errors.append(f"{path.name}: must be 44100 Hz, got {rate}")
        if nominal > 0 and not 80000 <= nominal <= 192000:
            warnings.append(f"{path.name}: unusual nominal bitrate {nominal}")
        if duration > 5.0:
            warnings.append(f"{path.name}: long combat line ({duration:.2f}s)")
        if duration < 0.08:
            warnings.append(f"{path.name}: extremely short clip ({duration:.2f}s)")

    for (event, emotion), bank in sorted(banks.items()):
        if bank["variants"] and not bank["base"]:
            errors.append(f"{event}__{emotion}: numbered variants exist without base file")
        if bank["variants"]:
            expected = set(range(max(bank["variants"]) + 1))
            missing = sorted(expected - bank["variants"])
            if missing:
                errors.append(
                    f"{event}__{emotion}: numbered variant gap(s): "
                    + ", ".join(map(str, missing))
                )
        total = (1 if bank["base"] else 0) + len(bank["variants"])
        if total > 64:
            errors.append(f"{event}__{emotion}: {total} files exceeds runtime limit 64")

    # Current Vengeance voice discovery uses alert.ogg as the folder probe.
    if not (args.pack / "ALERT.ogg").exists() and not (args.pack / "alert.ogg").exists():
        errors.append("ALERT.ogg is required for voice-folder discovery")

    if args.complete:
        for event in load_baseline(args.baseline):
            emotions = event_emotions.get(event, set())
            if "legacy" not in emotions and "controlled" not in emotions:
                errors.append(f"{event}: missing baseline legacy/controlled recording")

    if args.production:
        for event, required in PRODUCTION_EMOTION_REQUIREMENTS.items():
            present = event_emotions.get(event, set())
            for emotion in sorted(required - present):
                errors.append(f"{event}: missing production {emotion} bank")

    for warning in warnings:
        print("WARNING:", warning)
    for error in errors:
        print("ERROR:", error)

    print(f"Checked {len(files)} OGG files; {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
