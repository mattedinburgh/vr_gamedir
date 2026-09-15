#!/usr/bin/env python3
"""Inventory Vengeance Reloaded voice assets with no third-party dependencies."""

from __future__ import annotations

import argparse
import csv
import re
import struct
from collections import defaultdict
from pathlib import Path

EMOTIONS = {"controlled", "angry", "distressed", "panicked"}
NAME_RE = re.compile(
    r"^(?P<event>.+?)(?:__(?P<emotion>controlled|angry|distressed|panicked))?(?: (?P<variant>\d+))?$",
    re.IGNORECASE,
)


def parse_ogg(path: Path):
    data = path.read_bytes()
    ident = data.find(b"\x01vorbis")
    if ident < 0:
        return None, None, None, None
    channels = data[ident + 11]
    rate = struct.unpack_from("<I", data, ident + 12)[0]
    nominal = struct.unpack_from("<i", data, ident + 20)[0]
    page = data.rfind(b"OggS")
    granule = struct.unpack_from("<Q", data, page + 6)[0] if page >= 0 else 0
    duration = (granule / rate) if rate else 0.0
    return channels, rate, nominal, duration


def classify_folder(rel_parent: Path):
    parts = list(rel_parent.parts)
    faction = parts[0] if parts else ""
    gender = next((p for p in parts if p.lower() in {"male", "female"}), "")
    rank = next(
        (p for p in parts if p.lower() in {"admin", "regular", "elite", "green", "veteran"}),
        "",
    )
    voice_id = parts[-1] if parts and re.fullmatch(r"\d{2}", parts[-1]) else ""
    return faction, gender, rank, voice_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path("voice_inventory.csv"))
    parser.add_argument("--coverage-out", type=Path, default=Path("voice_coverage.csv"))
    args = parser.parse_args()

    voice_root = args.game_root / "Data-Voice-Taunts" / "Voice"
    if not voice_root.is_dir():
        raise SystemExit(f"Voice root not found: {voice_root}")

    rows = []
    coverage = defaultdict(lambda: {"files": 0, "voice_folders": set(), "variants": 0})

    for path in sorted(voice_root.rglob("*.ogg")):
        rel = path.relative_to(voice_root)
        match = NAME_RE.match(path.stem)
        if not match:
            event, emotion, variant = path.stem.upper(), "", ""
        else:
            event = match.group("event").upper()
            emotion = (match.group("emotion") or "legacy").lower()
            variant = match.group("variant") or ""

        channels, rate, nominal, duration = parse_ogg(path)
        faction, gender, rank, voice_id = classify_folder(rel.parent)
        key = (event, emotion)
        coverage[key]["files"] += 1
        coverage[key]["voice_folders"].add(str(rel.parent))
        if variant != "":
            coverage[key]["variants"] += 1

        rows.append(
            {
                "relative_path": str(rel),
                "faction_or_group": faction,
                "gender": gender,
                "rank": rank,
                "voice_id": voice_id,
                "event": event,
                "emotion": emotion,
                "variant": variant,
                "channels": channels,
                "sample_rate_hz": rate,
                "nominal_bitrate": nominal,
                "duration_s": f"{duration:.3f}" if duration is not None else "",
                "bytes": path.stat().st_size,
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    coverage_rows = []
    for (event, emotion), data in sorted(coverage.items()):
        coverage_rows.append(
            {
                "event": event,
                "emotion": emotion,
                "files": data["files"],
                "voice_folders": len(data["voice_folders"]),
                "numbered_variants": data["variants"],
            }
        )

    args.coverage_out.parent.mkdir(parents=True, exist_ok=True)
    with args.coverage_out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["event", "emotion", "files", "voice_folders", "numbered_variants"],
        )
        writer.writeheader()
        writer.writerows(coverage_rows)

    print(f"Inventoried {len(rows)} OGG files")
    print(f"Wrote {args.out}")
    print(f"Wrote {args.coverage_out}")


if __name__ == "__main__":
    main()
