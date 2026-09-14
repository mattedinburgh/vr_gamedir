#!/usr/bin/env python3
"""Strict read-only extractor for selected JA2 UI assets from local SLF archives.

The extractor never modifies the game installation. It reads only allow-listed
files from the user's own Interface.slf/Laptop.slf and stages copies under
build/. Matching is case-insensitive and prefers the exact archive path; a
basename fallback is allowed only when it is unique.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Dict, List, Tuple

LIBHEADER = struct.Struct("<256s256siiHHB3xi")
DIRENTRY = struct.Struct("<256sIIBB2xIIH2x")
FILE_OK = 0
EXTRACTOR_VERSION = "cold-ui-slf-v3"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def zstr(b: bytes) -> str:
    return b.split(b"\0", 1)[0].decode("latin-1", errors="replace")


def norm_name(name: str) -> str:
    return str(PurePosixPath(name.replace("\\", "/"))).lstrip("./").lower()


def safe_target(name: str) -> PurePosixPath:
    p = PurePosixPath(name.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe target path in manifest: {name!r}")
    return p


def find_loose_source(root: Path, loose_roots, mount: str, wanted: str):
    """Resolve a target from loose VFS data layers before falling back to SLF."""
    rel = safe_target(wanted)
    for layer in loose_roots:
        candidate = (root / layer / mount).joinpath(*rel.parts)
        if candidate.is_file():
            return candidate, layer
    return None, None


def index_slf(path: Path) -> List[Tuple[str, int, int]]:
    size = path.stat().st_size
    if size < LIBHEADER.size:
        raise ValueError(f"{path}: file too small for SLF header")

    with path.open("rb") as f:
        raw = f.read(LIBHEADER.size)
        if len(raw) != LIBHEADER.size:
            raise ValueError(f"{path}: short SLF header")

        _name, _mount, entries, _used, _sort_mode, _version, _subdirs, _reserved = LIBHEADER.unpack(raw)
        if entries < 0:
            raise ValueError(f"{path}: negative SLF entry count")

        table = size - entries * DIRENTRY.size
        if table < LIBHEADER.size or table > size:
            raise ValueError(f"{path}: invalid SLF directory offset")

        f.seek(table)
        out: List[Tuple[str, int, int]] = []
        for idx in range(entries):
            row = f.read(DIRENTRY.size)
            if len(row) != DIRENTRY.size:
                raise ValueError(f"{path}: short SLF directory at entry {idx}")

            filename, offset, length, state, _rsv, _ftlo, _fthi, _rsv2 = DIRENTRY.unpack(row)
            if state != FILE_OK:
                continue

            name = zstr(filename).replace("\\", "/")
            if not name:
                continue
            if offset < LIBHEADER.size or length < 0 or offset + length > table:
                raise ValueError(
                    f"{path}: invalid data bounds for {name!r}: offset={offset}, length={length}, table={table}"
                )
            out.append((name, offset, length))
    return out


def build_lookup(entries: List[Tuple[str, int, int]]):
    exact: Dict[str, Tuple[str, int, int]] = {}
    basenames: Dict[str, List[Tuple[str, int, int]]] = defaultdict(list)

    for entry in entries:
        name = entry[0]
        key = norm_name(name)
        if key in exact:
            raise ValueError(f"duplicate exact SLF entry after normalization: {name!r}")
        exact[key] = entry
        basenames[PurePosixPath(key).name].append(entry)

    return exact, basenames


def resolve_target(wanted: str, exact, basenames):
    key = norm_name(wanted)
    if key in exact:
        return exact[key], "exact"

    base = PurePosixPath(key).name
    candidates = basenames.get(base, [])
    if len(candidates) == 1:
        return candidates[0], "unique-basename"
    if len(candidates) > 1:
        names = [c[0] for c in candidates]
        raise ValueError(f"ambiguous basename {wanted!r}; candidates: {names}")
    return None, "missing"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-root", required=True)
    ap.add_argument("--manifest", default="tools/cold_ui/slf_bridge_manifest.json")
    ap.add_argument("--output-root", default="build/cold-ui-base-extract")
    ap.add_argument("--report", default="build/cold-ui-slf-extract-report.json")
    ap.add_argument("--allow-missing", action="store_true", help="Report missing allow-listed assets without failing.")
    ap.add_argument("--force", action="store_true", help="Rewrite staged files even when bytes are already identical.")
    args = ap.parse_args()

    root = Path(args.game_root).resolve()
    output = Path(args.output_root).resolve()
    manifest_path = Path(args.manifest)
    spec = json.loads(manifest_path.read_text(encoding="utf-8"))
    loose_roots = spec.get(
        "loose_roots",
        [
            "Data-UI",
            "Data-PCM",
            "Data-AIMv53",
            "Data-Maps-Tiles",
            "Data-Vengeance",
            "Data-1.13",
            "Data",
        ],
    )

    report = {
        "extractor_version": EXTRACTOR_VERSION,
        "game_root": str(root),
        "manifest": str(manifest_path),
        "output_root": str(output),
        "archives": [],
        "summary": {"extracted": 0, "unchanged": 0, "missing": 0},
    }

    missing: List[str] = []

    for archive in spec["archives"]:
        rel_archive = Path(archive["archive"])
        src = root / rel_archive
        archive_row = {
            "archive": archive["archive"],
            "mount": archive["mount"],
            "targets": [],
        }

        if not src.is_file():
            msg = f"required archive not found: {src}"
            if args.allow_missing:
                archive_row["error"] = msg
                for wanted in archive["targets"]:
                    archive_row["targets"].append({"target": wanted, "status": "missing-archive"})
                    report["summary"]["missing"] += 1
                    missing.append(f"{archive['archive']}::{wanted}")
                report["archives"].append(archive_row)
                continue
            raise FileNotFoundError(msg)

        archive_row["archive_sha256"] = sha256_file(src)
        archive_row["archive_size"] = src.stat().st_size

        entries = index_slf(src)
        exact, basenames = build_lookup(entries)
        archive_row["indexed_entries"] = len(entries)

        with src.open("rb") as fsrc:
            for wanted in archive["targets"]:
                target_path = safe_target(wanted)
                row = {"target": wanted}

                loose_src, loose_layer = find_loose_source(
                    root, loose_roots, archive["mount"], wanted
                )
                if loose_src is not None:
                    data = loose_src.read_bytes()
                    source_hash = sha256_bytes(data)
                    dst = output / archive["mount"] / Path(*target_path.parts)
                    dst.parent.mkdir(parents=True, exist_ok=True)

                    row.update({
                        "source_kind": "loose-vfs",
                        "source_layer": loose_layer,
                        "source_path": str(loose_src),
                        "length": len(data),
                        "sha256": source_hash,
                        "output": str(dst),
                    })

                    if not args.force and dst.is_file() and sha256_file(dst) == source_hash:
                        row["status"] = "unchanged"
                        report["summary"]["unchanged"] += 1
                    else:
                        dst.write_bytes(data)
                        if sha256_file(dst) != source_hash:
                            raise ValueError(f"{dst}: post-write hash mismatch")
                        row["status"] = "extracted"
                        report["summary"]["extracted"] += 1

                    archive_row["targets"].append(row)
                    continue

                try:
                    hit, match_mode = resolve_target(wanted, exact, basenames)
                except ValueError as exc:
                    row["status"] = "ambiguous"
                    row["error"] = str(exc)
                    archive_row["targets"].append(row)
                    raise

                if hit is None:
                    row["status"] = "missing"
                    archive_row["targets"].append(row)
                    report["summary"]["missing"] += 1
                    missing.append(f"{archive['archive']}::{wanted}")
                    continue

                name, off, length = hit
                fsrc.seek(off)
                data = fsrc.read(length)
                if len(data) != length:
                    raise ValueError(f"{src}: short read for {name}")

                dst = output / archive["mount"] / Path(*target_path.parts)
                dst.parent.mkdir(parents=True, exist_ok=True)
                source_hash = sha256_bytes(data)

                row.update({
                    "source_kind": "slf",
                    "archive_entry": name,
                    "match_mode": match_mode,
                    "offset": off,
                    "length": length,
                    "sha256": source_hash,
                    "output": str(dst),
                })

                if not args.force and dst.is_file() and sha256_file(dst) == source_hash:
                    row["status"] = "unchanged"
                    report["summary"]["unchanged"] += 1
                else:
                    dst.write_bytes(data)
                    if sha256_file(dst) != source_hash:
                        raise ValueError(f"{dst}: post-write hash mismatch")
                    row["status"] = "extracted"
                    report["summary"]["extracted"] += 1

                archive_row["targets"].append(row)

        report["archives"].append(archive_row)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"summary": report["summary"], "report": str(report_path)}, indent=2))

    if missing and not args.allow_missing:
        sample = ", ".join(missing[:8])
        suffix = "" if len(missing) <= 8 else f" (+{len(missing) - 8} more)"
        raise SystemExit(f"missing required Stage 3 UI assets: {sample}{suffix}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
