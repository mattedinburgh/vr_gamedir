#!/usr/bin/env python3
"""Cross-check the cold UI theming manifest against the Stage 3 SLF allow-list."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath


def norm(value: str) -> str:
    return str(PurePosixPath(value.replace("\\", "/"))).lower()


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    bridge = json.loads((root / "slf_bridge_manifest.json").read_text(encoding="utf-8"))

    expected = {}
    for archive in bridge["archives"]:
        mount = archive["mount"]
        for target in archive["targets"]:
            mount_path = f"{mount}/{target}"
            key = norm(mount_path)
            if key in expected:
                raise AssertionError(f"duplicate Stage 3 bridge target: {mount_path}")
            expected[key] = mount_path

    actual = {}
    for entry in manifest["assets"]:
        if int(entry.get("stage", 1)) != 3:
            continue
        mount_path = entry["mount_path"]
        key = norm(mount_path)
        if key in actual:
            raise AssertionError(f"duplicate Stage 3 theming target: {mount_path}")

        source = norm(entry["source"])
        required_source = norm(f"build/cold-ui-base-extract/{mount_path}")
        assert source == required_source, (
            f"Stage 3 source mismatch for {mount_path}: {entry['source']} != "
            f"build/cold-ui-base-extract/{mount_path}"
        )
        actual[key] = mount_path

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    assert not missing, f"SLF targets missing from theming manifest: {missing}"
    assert not extra, f"Stage 3 theming assets absent from SLF allow-list: {extra}"
    assert len(expected) == 34, f"unexpected Stage 3 target count: {len(expected)}"

    print(f"Stage 3 manifest consistency checks passed ({len(expected)} assets)")


if __name__ == "__main__":
    main()
