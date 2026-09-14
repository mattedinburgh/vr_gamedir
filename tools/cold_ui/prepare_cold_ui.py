#!/usr/bin/env python3
"""
Prepare a non-live cold-colour UI overlay for JA2 Vengeance.

Safety properties:
- Source assets are never modified.
- Output goes to a separate overlay root (default: build/Data-UI-ColdPilot).
- STI indexed images are recoloured by palette only; ETRLE pixel data,
  subimage dimensions, offsets, transparency runs, and app data remain byte-identical.
- Incremental by default. Use --force only for a clean rebuild.
- Nothing edits vfs_config.Vengeance.ini or deploys to a game directory.
"""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
import shutil
import struct
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

STCI_INDEXED = 0x0008
STCI_RGB = 0x0004
STCI_ETRLE_COMPRESSED = 0x0020
STCI_HEADER_SIZE = 64
PROFILE_VERSION = "cold-ui-v4"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clamp8(v: float) -> int:
    return max(0, min(255, int(round(v))))


def cold_rgb(rgb: Tuple[int, int, int], strength: float, policy: str = "chrome") -> Tuple[int, int, int]:
    """Shift UI chrome toward cold navy/steel/cyan while protecting semantic colours.

    policy controls how aggressively an asset is themed:
    - chrome: panel/button/frame material; full treatment
    - mixed: chrome plus embedded artwork; conservative treatment
    - semantic: warning/status/state artwork; minimal treatment
    - preserve: leave colour untouched
    """
    r8, g8, b8 = rgb
    if r8 == 0 and g8 == 0 and b8 == 0:
        return rgb

    r, g, b = r8 / 255.0, g8 / 255.0, b8 / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    local = max(0.0, min(1.0, strength))
    policy_key = str(policy).strip().lower()
    policy_factor = {
        "chrome": 1.00,
        "mixed": 0.58,
        "semantic": 0.18,
        "preserve": 0.00,
    }.get(policy_key, 0.58)
    local *= policy_factor
    if local <= 0.0:
        return rgb

    # Preserve only clearly semantic colours. Warm brown/orange/gold chrome is
    # intentionally NOT protected: converting that material language is the point
    # of the cold-theme pass.
    if s >= 0.65 and v >= 0.35 and (h <= 0.03 or h >= 0.97):  # warning red
        local *= 0.10
    elif s >= 0.55 and v >= 0.25 and 0.25 <= h <= 0.45:       # status green
        local *= 0.12
    elif s >= 0.75 and v >= 0.80 and 0.13 <= h <= 0.19:       # true bright warning yellow
        # Yellow warning affordances must remain immediately recognisable.
        # The first research-informed policy test showed 0.15 still cooled
        # them too aggressively relative to neutral panel chrome.
        local *= 0.08

    # Existing blues/cyans already belong to the intended language.
    if s >= 0.25 and 0.48 <= h <= 0.72:
        local *= 0.22

    # Highly saturated magenta/purple is usually semantic/art content, not chrome.
    if s >= 0.60 and 0.78 <= h <= 0.95:
        local *= 0.18

    warmness = max(0.0, r - b)
    neutrality = 1.0 - s
    local *= min(1.0, 0.72 + 0.35 * warmness + 0.18 * neutrality)

    # Cold target preserves luminance but changes the material read:
    # dark navy -> gunmetal -> steel-blue -> icy grey.
    if lum < 0.16:
        tr = lum * 0.42
        tg = lum * 0.72 + 0.004
        tb = lum * 1.15 + 0.022
    elif lum > 0.82:
        tr = lum * 0.84
        tg = lum * 0.95
        tb = min(1.0, lum * 1.06 + 0.006)
    else:
        tr = max(0.0, lum * 0.58 - 0.008)
        tg = min(1.0, lum * 0.86 + 0.010)
        tb = min(1.0, lum * 1.18 + 0.035)

    nr = r * (1.0 - local) + tr * local
    ng = g * (1.0 - local) + tg * local
    nb = b * (1.0 - local) + tb * local
    return clamp8(nr * 255), clamp8(ng * 255), clamp8(nb * 255)


def recolour_sti(data: bytes, strength: float, policy: str = "chrome") -> Tuple[bytes, Dict[str, object]]:
    if len(data) < STCI_HEADER_SIZE or data[:4] != b"STCI":
        raise ValueError("not an STCI file")

    flags = struct.unpack_from("<I", data, 16)[0]
    height, width = struct.unpack_from("<HH", data, 20)
    depth = data[44]

    meta: Dict[str, object] = {
        "format": "STI",
        "flags": flags,
        "width_header": width,
        "height_header": height,
        "depth": depth,
        "policy": policy,
    }

    if not (flags & STCI_INDEXED):
        meta["action"] = "copied-unmodified-rgb-sti"
        return data, meta

    colours = struct.unpack_from("<I", data, 24)[0]
    subimages = struct.unpack_from("<H", data, 28)[0]
    meta["palette_colours"] = colours
    meta["subimages"] = subimages

    if colours <= 0 or colours > 256:
        raise ValueError(f"unexpected STI palette size: {colours}")

    palette_off = STCI_HEADER_SIZE
    palette_end = palette_off + colours * 3
    if palette_end > len(data):
        raise ValueError("truncated STI palette")

    out = bytearray(data)
    changed = 0

    for idx in range(colours):
        off = palette_off + idx * 3
        old = tuple(out[off:off + 3])

        # Index 0 commonly participates in transparency conventions. Preserve it exactly.
        if idx == 0:
            continue

        new = cold_rgb(old, strength, policy)
        if new != old:
            out[off:off + 3] = bytes(new)
            changed += 1

    # Safety invariant: palette bytes are the only bytes permitted to change.
    before_non_palette = data[:palette_off] + data[palette_end:]
    after_bytes = bytes(out)
    after_non_palette = after_bytes[:palette_off] + after_bytes[palette_end:]
    meta["action"] = "palette-retint"
    meta["palette_entries_changed"] = changed
    meta["non_palette_sha256_before"] = sha256_bytes(before_non_palette)
    meta["non_palette_sha256_after"] = sha256_bytes(after_non_palette)
    meta["structural_bytes_identical"] = before_non_palette == after_non_palette
    if not meta["structural_bytes_identical"]:
        raise ValueError("STI structural bytes changed outside the palette; refusing output")
    return after_bytes, meta


def decode_sti_subimages(data: bytes):
    """Decode indexed ETRLE STI frames for review previews only."""
    Image = require_pillow()
    if len(data) < STCI_HEADER_SIZE or data[:4] != b"STCI":
        raise ValueError("not an STCI file")

    flags = struct.unpack_from("<I", data, 16)[0]
    if not (flags & STCI_INDEXED) or not (flags & STCI_ETRLE_COMPRESSED):
        return []

    colours = struct.unpack_from("<I", data, 24)[0]
    subimages = struct.unpack_from("<H", data, 28)[0]
    if colours <= 0 or colours > 256:
        raise ValueError(f"unexpected STI palette size: {colours}")

    palette_off = STCI_HEADER_SIZE
    table_off = palette_off + colours * 3
    pixel_base = table_off + subimages * 16
    if pixel_base > len(data):
        raise ValueError("truncated STI metadata")

    palette = [
        tuple(data[palette_off + i * 3: palette_off + i * 3 + 3])
        for i in range(colours)
    ]

    frames = []
    for idx in range(subimages):
        off = table_off + idx * 16
        data_off, data_len, offset_x, offset_y, height, width = struct.unpack_from("<IIhhHH", data, off)
        start = pixel_base + data_off
        end = start + data_len
        if start < pixel_base or end > len(data):
            raise ValueError(f"STI frame {idx} has invalid data bounds")

        rgba = bytearray(width * height * 4)
        p = start
        x = 0
        y = 0

        while p < end and y < height:
            token = data[p]
            p += 1
            if token == 0:
                y += 1
                x = 0
                continue

            run = token & 0x7F
            if token & 0x80:
                x += run
                continue

            for _ in range(run):
                if p >= end:
                    raise ValueError(f"STI frame {idx} literal run exceeds data")
                pal_idx = data[p]
                p += 1
                if y < height and x < width and pal_idx < len(palette):
                    r, g, b = palette[pal_idx]
                    px = (y * width + x) * 4
                    rgba[px:px + 4] = bytes((r, g, b, 255))
                x += 1

        image = Image.frombytes("RGBA", (width, height), bytes(rgba))
        frames.append({
            "image": image,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "width": width,
            "height": height,
        })

    return frames


def render_sti_compare(before: bytes, after: bytes, dst: Path, max_frames: int = 8) -> Dict[str, object]:
    """Write a real before/after PNG assembled from decoded STI frames."""
    Image = require_pillow()
    old_frames = decode_sti_subimages(before)
    new_frames = decode_sti_subimages(after)
    count = min(len(old_frames), len(new_frames), max_frames)
    if count == 0:
        return {"preview": "unsupported-sti-preview"}

    gap = 12
    row_gap = 8
    rows = []
    for i in range(count):
        old = old_frames[i]["image"]
        new = new_frames[i]["image"]
        row_w = old.width + gap + new.width
        row_h = max(old.height, new.height)
        row = Image.new("RGBA", (row_w, row_h), (10, 15, 21, 255))
        row.paste(old, (0, 0), old)
        row.paste(new, (old.width + gap, 0), new)
        rows.append(row)

    sheet_w = max(r.width for r in rows)
    sheet_h = sum(r.height for r in rows) + row_gap * (len(rows) - 1)
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (10, 15, 21, 255))
    y = 0
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height + row_gap

    dst.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dst, format="PNG")
    return {"preview": "written", "preview_frames": count, "preview_size": [sheet_w, sheet_h]}


def render_raster_compare(src: Path, themed: Path, dst: Path) -> Dict[str, object]:
    Image = require_pillow()
    with Image.open(src) as a, Image.open(themed) as b:
        a = a.convert("RGBA")
        b = b.convert("RGBA")
        gap = 12
        h = max(a.height, b.height)
        sheet = Image.new("RGBA", (a.width + gap + b.width, h), (10, 15, 21, 255))
        sheet.paste(a, (0, 0), a)
        sheet.paste(b, (a.width + gap, 0), b)
        dst.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(dst, format="PNG")
        return {"preview": "written", "preview_size": [sheet.width, sheet.height]}


def require_pillow():
    try:
        from PIL import Image  # type: ignore
        return Image
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for PNG/PCX preparation. Install with: python -m pip install pillow"
        ) from exc


def recolour_raster(src: Path, dst: Path, strength: float, policy: str = "chrome") -> Dict[str, object]:
    Image = require_pillow()
    with Image.open(src) as img:
        meta: Dict[str, object] = {"format": img.format, "mode": img.mode, "size": list(img.size), "policy": policy}

        if img.mode == "P":
            palette = img.getpalette()
            if palette is None:
                raise ValueError(f"{src}: indexed image has no palette")
            palette = list(palette)
            transparent = img.info.get("transparency")
            transparent_index = transparent if isinstance(transparent, int) else None

            changed = 0
            for idx in range(min(256, len(palette) // 3)):
                if idx == transparent_index:
                    continue
                off = idx * 3
                old = tuple(palette[off:off + 3])
                new = cold_rgb(old, strength, policy)
                if new != old:
                    palette[off:off + 3] = list(new)
                    changed += 1

            out = img.copy()
            out.putpalette(palette)
            out.save(dst)
            meta["action"] = "palette-retint"
            meta["palette_entries_changed"] = changed
            return meta

        rgba = img.convert("RGBA")
        pixels = []
        for r, g, b, a in rgba.getdata():
            nr, ng, nb = cold_rgb((r, g, b), strength, policy)
            pixels.append((nr, ng, nb, a))
        rgba.putdata(pixels)

        if src.suffix.lower() == ".pcx":
            rgba.convert("RGB").save(dst, format="PCX")
        else:
            rgba.save(dst)

        meta["action"] = "pixel-retint"
        return meta


def load_state(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="tools/cold_ui/manifest.json")
    ap.add_argument("--source-root", default=".")
    ap.add_argument("--output-root", default="build/Data-UI-ColdPilot")
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--strength", type=float, default=0.72)
    ap.add_argument("--write", action="store_true", help="Actually write the separate pilot overlay.")
    ap.add_argument("--force", action="store_true", help="Ignore incremental state and rebuild selected assets.")
    ap.add_argument("--previews", action="store_true", help="Generate real before/after PNG review sheets without activating the UI.")
    ap.add_argument("--preview-root", default="build/cold-ui-preview")
    ap.add_argument("--report", default="build/cold-ui-report.json")
    args = ap.parse_args()

    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output_root).resolve()
    preview_root = Path(args.preview_root).resolve()
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    state_path = output_root / ".cold_ui_state.json"
    state = {} if args.force else load_state(state_path)
    new_state: Dict[str, object] = dict(state)

    report: Dict[str, object] = {
        "profile_version": PROFILE_VERSION,
        "stage": args.stage,
        "strength": args.strength,
        "write": args.write,
        "previews": args.previews,
        "output_root": str(output_root),
        "preview_root": str(preview_root),
        "assets": [],
    }

    for entry in manifest["assets"]:
        if int(entry.get("stage", 1)) > args.stage:
            continue

        rel = Path(entry["source"])
        mount = Path(entry["mount_path"])
        src = source_root / rel
        dst = output_root / mount

        row: Dict[str, object] = {
            "source": str(rel).replace("\\", "/"),
            "mount_path": str(mount).replace("\\", "/"),
            "stage": entry.get("stage", 1),
            "role": entry.get("role", ""),
            "policy": str(entry.get("policy", "chrome")),
        }

        if not src.exists():
            row["status"] = "missing-source"
            report["assets"].append(row)
            continue

        raw = src.read_bytes()
        input_hash = sha256_bytes(raw)
        state_key = row["source"]
        signature = f"{PROFILE_VERSION}:{args.strength:.4f}:{row['policy']}:{input_hash}"

        if not args.force and state.get(state_key) == signature and dst.exists():
            row["status"] = "incremental-skip"
            row["input_sha256"] = input_hash
            row["output_sha256"] = sha256_bytes(dst.read_bytes())
            report["assets"].append(row)
            continue

        suffix = src.suffix.lower()
        row["input_sha256"] = input_hash

        if not args.write:
            row["status"] = "audit-only"
            if suffix == ".sti":
                themed_bytes, meta = recolour_sti(raw, args.strength, str(row["policy"]))
                row.update(meta)
                if args.previews:
                    preview_dst = preview_root / mount.parent / f"{mount.name}.compare.png"
                    row.update(render_sti_compare(raw, themed_bytes, preview_dst))
                    row["preview_path"] = str(preview_dst)
            report["assets"].append(row)
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        # Preserve-class assets are content/lore rather than chrome. Copy them
        # byte-for-byte instead of round-tripping through an image encoder.
        if str(row["policy"]).lower() == "preserve":
            dst.write_bytes(raw)
            row["action"] = "copied-unmodified-policy"
            row["byte_identical_to_source"] = True
            if args.previews:
                preview_dst = preview_root / mount.parent / f"{mount.name}.compare.png"
                if suffix == ".sti":
                    row.update(render_sti_compare(raw, raw, preview_dst))
                elif suffix in {".png", ".pcx"}:
                    row.update(render_raster_compare(src, src, preview_dst))
                row["preview_path"] = str(preview_dst)
        elif suffix == ".sti":
            out, meta = recolour_sti(raw, args.strength, str(row["policy"]))
            dst.write_bytes(out)
            row.update(meta)
            if args.previews:
                preview_dst = preview_root / mount.parent / f"{mount.name}.compare.png"
                row.update(render_sti_compare(raw, out, preview_dst))
                row["preview_path"] = str(preview_dst)
        elif suffix in {".png", ".pcx"}:
            row.update(recolour_raster(src, dst, args.strength, str(row["policy"])))
            if args.previews:
                preview_dst = preview_root / mount.parent / f"{mount.name}.compare.png"
                row.update(render_raster_compare(src, dst, preview_dst))
                row["preview_path"] = str(preview_dst)
        else:
            shutil.copy2(src, dst)
            row["action"] = "copied-unmodified"

        row["status"] = "written"
        row["output_sha256"] = sha256_bytes(dst.read_bytes())
        new_state[state_key] = signature
        report["assets"].append(row)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.write:
        output_root.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(new_state, indent=2), encoding="utf-8")

    counts: Dict[str, int] = {}
    for row in report["assets"]:
        status = str(row.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1

    print(json.dumps({"summary": counts, "report": str(report_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
