#!/usr/bin/env python3
"""Synthetic tests for the Stage 3 SLF bridge parser and resolver."""
from __future__ import annotations

import tempfile
from pathlib import Path

from extract_slf_ui import DIRENTRY, FILE_OK, LIBHEADER, build_lookup, find_loose_source, index_slf, resolve_target


def pad(text: bytes, size: int) -> bytes:
    return text + b"\0" * (size - len(text))


def write_fixture(path: Path):
    payloads = [
        ("Buttons\\inventory_buttons.sti", b"INVENTORY"),
        ("Chrome\\taskbar.sti", b"TASKBAR"),
        ("Other\\duplicate.sti", b"A"),
        ("Elsewhere\\duplicate.sti", b"B"),
    ]

    offset = LIBHEADER.size
    blobs = []
    rows = []
    for name, data in payloads:
        blobs.append(data)
        rows.append(
            DIRENTRY.pack(
                pad(name.encode("latin-1"), 256),
                offset,
                len(data),
                FILE_OK,
                0,
                0,
                0,
                0,
            )
        )
        offset += len(data)

    header = LIBHEADER.pack(
        pad(b"fixture.slf", 256),
        pad(b"", 256),
        len(rows),
        len(rows),
        0,
        1,
        0,
        0,
    )
    path.write_bytes(header + b"".join(blobs) + b"".join(rows))


def main():
    with tempfile.TemporaryDirectory() as td:
        slf = Path(td) / "fixture.slf"
        write_fixture(slf)

        entries = index_slf(slf)
        assert len(entries) == 4

        exact, basenames = build_lookup(entries)

        hit, mode = resolve_target("Buttons/inventory_buttons.sti", exact, basenames)
        assert hit[0].replace("\\", "/") == "Buttons/inventory_buttons.sti"
        assert mode == "exact"

        hit, mode = resolve_target("taskbar.sti", exact, basenames)
        assert hit[0].replace("\\", "/") == "Chrome/taskbar.sti"
        assert mode == "unique-basename"

        hit, mode = resolve_target("missing.sti", exact, basenames)
        assert hit is None and mode == "missing"

        try:
            resolve_target("duplicate.sti", exact, basenames)
        except ValueError as exc:
            assert "ambiguous basename" in str(exc)
        else:
            raise AssertionError("duplicate basename should be rejected")

        # Loose VFS data must override the base SLF source, with the declared
        # layer order deciding which installed loose copy wins.
        root = Path(td) / "game"
        low = root / "Data-1.13" / "INTERFACE"
        high = root / "Data-UI" / "INTERFACE"
        low.mkdir(parents=True)
        high.mkdir(parents=True)
        (low / "backpack_buttons.sti").write_bytes(b"LOW")
        (high / "backpack_buttons.sti").write_bytes(b"HIGH")

        hit, layer = find_loose_source(
            root,
            ["Data-UI", "Data-Vengeance", "Data-1.13", "Data"],
            "INTERFACE",
            "backpack_buttons.sti",
        )
        assert hit is not None
        assert hit.read_bytes() == b"HIGH"
        assert layer == "Data-UI"

        (high / "backpack_buttons.sti").unlink()
        hit, layer = find_loose_source(
            root,
            ["Data-UI", "Data-Vengeance", "Data-1.13", "Data"],
            "INTERFACE",
            "backpack_buttons.sti",
        )
        assert hit is not None
        assert hit.read_bytes() == b"LOW"
        assert layer == "Data-1.13"

    print("SLF bridge synthetic checks passed")


if __name__ == "__main__":
    main()
