#!/usr/bin/env python3
"""Extract selected JA2 UI assets from local SLF archives into a staging folder.

This helper only reads the supplied game archives and writes copies under build/.
It does not modify the game installation or VFS configuration.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

LIBHEADER = struct.Struct("<256s256siiHHB3xi")
DIRENTRY = struct.Struct("<256sIIBB2xIIH2x")
FILE_OK = 0

def zstr(b: bytes) -> str:
    return b.split(b"\0", 1)[0].decode("latin-1", errors="replace")

def index_slf(path: Path):
    size = path.stat().st_size
    with path.open("rb") as f:
        raw = f.read(LIBHEADER.size)
        if len(raw) != LIBHEADER.size:
            raise ValueError(f"{path}: short SLF header")
        name, mount, entries, used, sort_mode, version, subdirs, reserved = LIBHEADER.unpack(raw)
        table = size - entries * DIRENTRY.size
        if entries < 0 or table < LIBHEADER.size:
            raise ValueError(f"{path}: invalid SLF directory")
        f.seek(table)
        out = []
        for _ in range(entries):
            row = f.read(DIRENTRY.size)
            if len(row) != DIRENTRY.size:
                raise ValueError(f"{path}: short SLF directory")
            filename, offset, length, state, rsv, ftlo, fthi, rsv2 = DIRENTRY.unpack(row)
            if state == FILE_OK:
                out.append((zstr(filename).replace("\\", "/"), offset, length))
    return out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-root", required=True)
    ap.add_argument("--manifest", default="tools/cold_ui/slf_bridge_manifest.json")
    ap.add_argument("--output-root", default="build/cold-ui-base-extract")
    args = ap.parse_args()

    root = Path(args.game_root)
    output = Path(args.output_root)
    spec = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    for archive in spec["archives"]:
        src = root / archive["archive"]
        entries = index_slf(src)
        by_name = {Path(name).name.lower(): (name, off, length) for name, off, length in entries}
        with src.open("rb") as f:
            for wanted in archive["targets"]:
                hit = by_name.get(Path(wanted).name.lower())
                if hit is None:
                    print(f"MISSING {archive['archive']} :: {wanted}")
                    continue
                name, off, length = hit
                f.seek(off)
                data = f.read(length)
                if len(data) != length:
                    raise ValueError(f"{src}: short read for {name}")
                dst = output / archive["mount"] / wanted
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                print(f"EXTRACTED {name} -> {dst}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
