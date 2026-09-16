#!/usr/bin/env python3
"""Turn an English recording manifest into a performer call sheet ordered for vocal safety."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

PAIN_EVENTS = {
    "GOT_HIT",
    "GOT_HIT_GUNFIRE",
    "GOT_HIT_BLADE",
    "GOT_HIT_HTH",
    "GOT_HIT_FALLROOF",
    "GOT_HIT_BLOODLOSS",
    "GOT_HIT_EXPLOSION",
    "GOT_HIT_GAS",
    "GOT_HIT_TENTACLES",
    "GOT_HIT_STRUCTURE_EXPLOSION",
    "GOT_HIT_OBJECT",
    "GOT_HIT_THROWING_KNIFE",
    "GOT_BLINDED",
    "GOT_DEAFENED",
}


def strain_bucket(row):
    event = row["event"].upper()
    emotion = row["emotion"].lower()
    intensity = int(row.get("intensity") or 0)

    if emotion == "panicked" or (event in PAIN_EVENTS and intensity >= 3):
        return 3, "high_strain"
    if emotion in {"angry", "distressed"} or intensity >= 3:
        return 2, "emotional"
    return 1, "normal"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("recording_manifest.csv"),
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--priority-max", type=int, default=3)
    args = parser.parse_args()

    with args.manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    selected = []
    for row in rows:
        if int(row.get("priority") or 99) > args.priority_max:
            continue
        session, strain = strain_bucket(row)
        output = dict(row)
        output["actor_id"] = args.actor_id
        output["session"] = session
        output["strain_class"] = strain
        selected.append(output)

    # Normal tactical speech first, emotional speech second, vocally stressful
    # screams/panic last. Inside a session, baseline precedes optional variants.
    selected.sort(
        key=lambda row: (
            int(row["session"]),
            0 if row["scope"] == "baseline" else 1,
            row["event"],
            row["emotion"],
            row["file_stem"],
        )
    )

    fields = [
        "actor_id",
        "session",
        "strain_class",
        "scope",
        "file_stem",
        "event",
        "emotion",
        "intensity",
        "spoken_en",
        "popup_en",
        "direction",
        "priority",
        "target_seconds",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(selected)

    counts = {}
    for row in selected:
        counts[row["session"]] = counts.get(row["session"], 0) + 1
    print(f"Wrote {len(selected)} lines to {args.out}")
    for session in sorted(counts):
        print(f"Session {session}: {counts[session]} line(s)")


if __name__ == "__main__":
    main()
