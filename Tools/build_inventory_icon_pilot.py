#!/usr/bin/env python3
"""
Build a 20-icon Vengeance inventory-art pilot from the real Data-AIMv53/BigItems STIs.

Design goals
------------
* Preserve each STI's subimage dimensions, offsets, object count and app-data.
* Preserve transparency silhouette exactly, so attachment overlays stay aligned.
* Improve legibility/material read at native JA2 scale: cleaner local contrast,
  restrained cool highlights, more distinct metal/polymer/wood values.
* Output to Pilot/InventoryIcons20 only. This script NEVER overwrites live art.
* Generate a manifest, PNG inspection renders, and an incremental installer.

The transformation is deliberately conservative. It upgrades the existing
Vengeance art rather than replacing silhouettes with unrelated modern renders.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont

STCI_INDEXED = 0x0008
STCI_ETRLE_COMPRESSED = 0x0020
HEADER_SIZE = 64
PALETTE_SIZE = 256 * 3
SUBIMAGE_SIZE = 16

PILOT = [
    ("GUN01.STI", "Glock 17", "polymer"),
    ("GUN02.STI", "Glock 18", "polymer"),
    ("GUN03.STI", "Beretta 92F", "steel"),
    ("GUN04.STI", "Beretta 93R", "steel"),
    ("GUN05.STI", ".38 Special", "revolver"),
    ("GUN06.STI", "Barracuda", "revolver"),
    ("GUN07.STI", "Desert Eagle .357", "bright_metal"),
    ("GUN08.STI", "Colt M1911A1", "steel"),
    ("GUN09.STI", "HK MP5KA4", "polymer"),
    ("GUN10.STI", "Ingram MAC-10", "steel"),
    ("GUN11.STI", "Thompson M1A1", "wood"),
    ("GUN110.STI", "Colt M4 Commando", "polymer"),
    ("GUN13.STI", "HK 53A3", "polymer"),
    ("GUN14.STI", "AKS-74U", "wood"),
    ("GUN15.STI", "FN P90", "polymer"),
    ("GUN16.STI", "Type 85", "steel"),
    ("GUN17.STI", "SKS", "wood"),
    ("GUN18.STI", "Dragunov SVD", "wood"),
    ("GUN19.STI", "M24", "precision"),
    ("GUN20.STI", "Steyr AUG-A2", "olive_polymer"),
]

PROFILE = {
    "polymer":       dict(contrast=1.10, saturation=0.86, cool=0.035, warm=0.00, highlight=0.055),
    "steel":         dict(contrast=1.11, saturation=0.82, cool=0.045, warm=0.00, highlight=0.070),
    "revolver":      dict(contrast=1.12, saturation=0.84, cool=0.030, warm=0.00, highlight=0.085),
    "bright_metal":  dict(contrast=1.13, saturation=0.80, cool=0.025, warm=0.00, highlight=0.120),
    "wood":          dict(contrast=1.10, saturation=1.02, cool=0.010, warm=0.035, highlight=0.055),
    "precision":     dict(contrast=1.11, saturation=0.88, cool=0.035, warm=0.010, highlight=0.065),
    "olive_polymer": dict(contrast=1.10, saturation=0.91, cool=0.020, warm=0.010, highlight=0.055),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_sti(raw: bytes) -> dict:
    if len(raw) < HEADER_SIZE or raw[:4] != b"STCI":
        raise ValueError("not an STCI file")
    original_size, stored_size, transparent, flags = struct.unpack_from("<IIII", raw, 4)
    height, width = struct.unpack_from("<HH", raw, 20)
    colours = struct.unpack_from("<I", raw, 24)[0]
    nsub = struct.unpack_from("<H", raw, 28)[0]
    depth = raw[44]
    app_size = struct.unpack_from("<I", raw, 45)[0]

    if not (flags & STCI_INDEXED):
        raise ValueError("pilot expects indexed STI")
    if not (flags & STCI_ETRLE_COMPRESSED):
        raise ValueError("pilot expects ETRLE-compressed STI")
    if colours != 256 or depth != 8:
        raise ValueError(f"unexpected indexed format: colours={colours}, depth={depth}")

    palette_off = HEADER_SIZE
    sub_off = palette_off + PALETTE_SIZE
    data_off = sub_off + nsub * SUBIMAGE_SIZE
    app_off = data_off + stored_size
    if app_off + app_size > len(raw):
        raise ValueError("truncated STI")

    pal = np.frombuffer(raw[palette_off:sub_off], dtype=np.uint8).reshape(256, 3).copy()
    subs = []
    for i in range(nsub):
        off = sub_off + i * SUBIMAGE_SIZE
        data_offset, data_len, ox, oy, h, w = struct.unpack_from("<IIhhHH", raw, off)
        subs.append({
            "data_offset": data_offset,
            "data_len": data_len,
            "offset_x": ox,
            "offset_y": oy,
            "height": h,
            "width": w,
        })
    pix = raw[data_off:app_off]
    app = raw[app_off:app_off + app_size]
    return {
        "header": bytearray(raw[:HEADER_SIZE]),
        "original_size": original_size,
        "stored_size": stored_size,
        "transparent": transparent,
        "flags": flags,
        "canvas_h": height,
        "canvas_w": width,
        "palette": pal,
        "subs": subs,
        "pix": pix,
        "app": app,
    }


def decode_subimage(sti: dict, sub: dict) -> np.ndarray:
    w, h = sub["width"], sub["height"]
    out = np.zeros((h, w), dtype=np.uint8)
    p = sub["data_offset"]
    end = p + sub["data_len"]
    src = sti["pix"]
    for y in range(h):
        x = 0
        while p < end:
            code = src[p]
            p += 1
            if code == 0:
                break
            run = code & 0x7F
            if run == 0:
                continue
            if code & 0x80:
                x += run
            else:
                if p + run > end:
                    raise ValueError("bad ETRLE literal run")
                out[y, x:x + run] = np.frombuffer(src[p:p + run], dtype=np.uint8)
                p += run
                x += run
            if x > w:
                raise ValueError("ETRLE row overflow")
    return out


def indices_to_rgba(idx: np.ndarray, palette: np.ndarray) -> Image.Image:
    rgb = palette[idx]
    alpha = np.where(idx == 0, 0, 255).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])
    return Image.fromarray(rgba, "RGBA")


def enhance_rgba(im: Image.Image, profile_name: str) -> Image.Image:
    p = PROFILE[profile_name]
    a0 = np.array(im.getchannel("A"), dtype=np.uint8)
    rgb = im.convert("RGB")

    scale = 4
    big = rgb.resize((rgb.width * scale, rgb.height * scale), Image.Resampling.LANCZOS)
    big = ImageEnhance.Contrast(big).enhance(p["contrast"])
    big = ImageEnhance.Color(big).enhance(p["saturation"])
    big = big.filter(ImageFilter.UnsharpMask(radius=1.15 * scale, percent=85, threshold=2))
    rgb = big.resize(im.size, Image.Resampling.LANCZOS)

    arr = np.asarray(rgb, dtype=np.float32) / 255.0
    h, w, _ = arr.shape
    yy, xx = np.mgrid[0:h, 0:w]
    if w > 1 and h > 1:
        light = 1.0 + p["highlight"] * (1.15 - 0.65 * xx / (w - 1) - 0.50 * yy / (h - 1))
        arr *= light[..., None]

    lum = arr.mean(axis=2)
    cool = p["cool"] * (0.35 + 0.65 * lum)
    warm = p["warm"] * (0.25 + 0.75 * lum)
    arr[..., 2] += cool
    arr[..., 0] += warm
    arr[..., 1] += 0.35 * warm

    if profile_name == "olive_polymer":
        arr[..., 1] += 0.022 * (1.0 - lum)
        arr[..., 0] += 0.008 * (1.0 - lum)
    elif profile_name == "wood":
        mid = np.clip(1.0 - np.abs(lum - 0.45) * 2.1, 0, 1)
        arr[..., 0] += 0.028 * mid
        arr[..., 1] += 0.010 * mid
    elif profile_name == "bright_metal":
        hi = np.clip((lum - 0.45) * 1.8, 0, 1)
        arr += hi[..., None] * 0.035

    arr = np.clip(arr, 0, 1)
    out = np.dstack([(arr * 255.0 + 0.5).astype(np.uint8), a0])
    out[a0 == 0, :3] = 0
    return Image.fromarray(out, "RGBA")


def make_palette_and_indices(images: List[Image.Image]) -> Tuple[np.ndarray, List[np.ndarray]]:
    opaque = []
    arrays = []
    for im in images:
        a = np.asarray(im, dtype=np.uint8)
        arrays.append(a)
        px = a[a[..., 3] > 0, :3]
        if len(px):
            opaque.append(px)

    if not opaque:
        pal = np.zeros((256, 3), dtype=np.uint8)
        return pal, [np.zeros(a.shape[:2], dtype=np.uint8) for a in arrays]

    sample = np.concatenate(opaque, axis=0)
    if len(sample) > 65000:
        step = int(math.ceil(len(sample) / 65000))
        sample = sample[::step]

    sample_img = Image.fromarray(sample.reshape((-1, 1, 3)), "RGB")
    q = sample_img.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    flatpal = q.getpalette()[:255 * 3]
    colors = np.array(flatpal, dtype=np.uint8).reshape(-1, 3)
    if len(colors) < 255:
        colors = np.vstack([colors, np.zeros((255 - len(colors), 3), dtype=np.uint8)])

    palette = np.zeros((256, 3), dtype=np.uint8)
    palette[1:] = colors[:255]

    indexed = []
    color32 = palette[1:].astype(np.int32)
    for a in arrays:
        h, w = a.shape[:2]
        idx = np.zeros((h, w), dtype=np.uint8)
        mask = a[..., 3] > 0
        px = a[..., :3][mask].astype(np.int32)
        if len(px):
            out = np.empty(len(px), dtype=np.uint8)
            for s in range(0, len(px), 4096):
                chunk = px[s:s + 4096]
                d = ((chunk[:, None, :] - color32[None, :, :]) ** 2).sum(axis=2)
                out[s:s + len(chunk)] = np.argmin(d, axis=1).astype(np.uint8) + 1
            idx[mask] = out
        indexed.append(idx)
    return palette, indexed


def encode_etrle(idx: np.ndarray) -> bytes:
    h, w = idx.shape
    out = bytearray()
    for y in range(h):
        row = idx[y]
        x = 0
        while x < w:
            transparent = row[x] == 0
            run = 1
            while x + run < w and run < 127 and (row[x + run] == 0) == transparent:
                run += 1
            if transparent:
                out.append(0x80 | run)
            else:
                out.append(run)
                out.extend(row[x:x + run].tobytes())
            x += run
        out.append(0)
    return bytes(out)


def write_sti(sti: dict, palette: np.ndarray, indexed: List[np.ndarray]) -> bytes:
    chunks = [encode_etrle(x) for x in indexed]
    header = bytearray(sti["header"])
    total_stored = sum(len(c) for c in chunks)
    struct.pack_into("<I", header, 8, total_stored)

    subheaders = bytearray()
    data_offset = 0
    for old, c, idx in zip(sti["subs"], chunks, indexed):
        h, w = idx.shape
        if (h, w) != (old["height"], old["width"]):
            raise ValueError("geometry changed")
        subheaders.extend(struct.pack(
            "<IIhhHH",
            data_offset, len(c),
            old["offset_x"], old["offset_y"],
            old["height"], old["width"]
        ))
        data_offset += len(c)

    return bytes(header) + palette.astype(np.uint8).tobytes() + bytes(subheaders) + b"".join(chunks) + sti["app"]


def checkerboard(size: Tuple[int, int]) -> Image.Image:
    w, h = size
    out = Image.new("RGB", size, (25, 29, 33))
    d = ImageDraw.Draw(out)
    s = 8
    for y in range(0, h, s):
        for x in range(0, w, s):
            if ((x // s) + (y // s)) % 2:
                d.rectangle((x, y, x + s - 1, y + s - 1), fill=(31, 36, 41))
    return out


def render_frame(im: Image.Image, box: Tuple[int, int]) -> Image.Image:
    bg = checkerboard(box)
    if im.width == 0 or im.height == 0:
        return bg
    scale = min((box[0] - 12) / im.width, (box[1] - 12) / im.height)
    scale = max(1.0, scale)
    new = (max(1, int(im.width * scale)), max(1, int(im.height * scale)))
    disp = im.resize(new, Image.Resampling.NEAREST)
    x = (box[0] - disp.width) // 2
    y = (box[1] - disp.height) // 2
    bg.paste(disp, (x, y), disp)
    return bg


def save_contact_sheet(rows: list, path: Path) -> None:
    cell_w, cell_h = 480, 160
    sheet = Image.new("RGB", (cell_w * 2, cell_h * len(rows)), (17, 20, 23))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, (name, before, after) in enumerate(rows):
        y = i * cell_h
        sheet.paste(render_frame(before, (cell_w, cell_h - 22)), (0, y + 22))
        sheet.paste(render_frame(after, (cell_w, cell_h - 22)), (cell_w, y + 22))
        draw.text((8, y + 5), f"{name} — CURRENT", font=font, fill=(205, 214, 221))
        draw.text((cell_w + 8, y + 5), f"{name} — PILOT", font=font, fill=(220, 228, 235))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    srcdir = root / "Data-AIMv53" / "BigItems"
    outroot = root / "Pilot" / "InventoryIcons20"
    outdir = outroot / "Data-AIMv53" / "BigItems"
    pngdir = outroot / "Previews"
    outdir.mkdir(parents=True, exist_ok=True)
    pngdir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "pilot": "Vengeance inventory icons — 20 item pilot",
        "source": "Data-AIMv53/BigItems",
        "deployment": "NOT DEPLOYED; use INSTALL_PILOT.ps1 manually",
        "items": [],
    }
    sheet_rows = []

    for filename, name, profile in PILOT:
        src = srcdir / filename
        if not src.exists():
            raise FileNotFoundError(src)
        raw = src.read_bytes()
        sti = parse_sti(raw)
        old_indices = [decode_subimage(sti, s) for s in sti["subs"]]
        before = [indices_to_rgba(x, sti["palette"]) for x in old_indices]
        after = [enhance_rgba(im, profile) for im in before]
        newpal, newidx = make_palette_and_indices(after)
        rebuilt = write_sti(sti, newpal, newidx)

        check = parse_sti(rebuilt)
        if len(check["subs"]) != len(sti["subs"]):
            raise ValueError(f"{filename}: object count changed")
        for a, b in zip(sti["subs"], check["subs"]):
            for key in ("offset_x", "offset_y", "height", "width"):
                if a[key] != b[key]:
                    raise ValueError(f"{filename}: {key} changed")
        check_idx = [decode_subimage(check, s) for s in check["subs"]]
        if any(x.shape != y.shape for x, y in zip(newidx, check_idx)):
            raise ValueError(f"{filename}: round-trip shape mismatch")

        dst = outdir / filename
        dst.write_bytes(rebuilt)
        for j, (b, a) in enumerate(zip(before, after)):
            suffix = "" if len(before) == 1 else f"_{j:02d}"
            b.save(pngdir / f"{Path(filename).stem}{suffix}_CURRENT.png")
            a.save(pngdir / f"{Path(filename).stem}{suffix}_PILOT.png")

        manifest["items"].append({
            "file": filename,
            "name": name,
            "profile": profile,
            "subimages": len(sti["subs"]),
            "source_sha256": sha256_bytes(raw),
            "pilot_sha256": sha256_bytes(rebuilt),
            "source_bytes": len(raw),
            "pilot_bytes": len(rebuilt),
            "geometry": [{
                "width": s["width"], "height": s["height"],
                "offset_x": s["offset_x"], "offset_y": s["offset_y"]
            } for s in sti["subs"]],
        })
        sheet_rows.append((name, before[0], after[0]))
        print(f"built {filename}: {name}")

    save_contact_sheet(sheet_rows, outroot / "CONTACT_SHEET.png")
    (outroot / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    readme = """# Vengeance inventory icon pilot — 20 items

This folder contains real, game-loadable STI replacements for twenty inventory icons.
They are generated from the current Vengeance assets with the original object geometry,
offsets and transparency silhouette preserved.

Nothing here is deployed automatically.

## Install into a local Vengeance game copy

From the repository/game root in PowerShell:

    .\\Pilot\\InventoryIcons20\\INSTALL_PILOT.ps1

The installer is incremental: it copies only STI files whose SHA-256 differs and backs
up the originals first.

To revert:

    .\\Pilot\\InventoryIcons20\\INSTALL_PILOT.ps1 -Revert

CONTACT_SHEET.png and Previews are inspection renders only. The game-ready files are
under Data-AIMv53/BigItems inside this pilot folder.
"""
    (outroot / "README.md").write_text(readme, encoding="utf-8")

    installer = r'''param(
  [switch]$Revert
)
$ErrorActionPreference = "Stop"
$PilotRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$GameRoot = Resolve-Path (Join-Path $PilotRoot "..\..")
$PilotItems = Join-Path $PilotRoot "Data-AIMv53\BigItems"
$LiveItems = Join-Path $GameRoot "Data-AIMv53\BigItems"
$Backup = Join-Path $PilotRoot "_backup\Data-AIMv53\BigItems"

if ($Revert) {
  if (-not (Test-Path $Backup)) { throw "No pilot backup exists." }
  Get-ChildItem $Backup -Filter "*.STI" | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $LiveItems $_.Name) -Force
    Write-Host "restored $($_.Name)"
  }
  exit 0
}

New-Item -ItemType Directory -Force -Path $Backup | Out-Null
$copied = 0
Get-ChildItem $PilotItems -Filter "*.STI" | ForEach-Object {
  $dst = Join-Path $LiveItems $_.Name
  if (-not (Test-Path $dst)) { throw "Live icon missing: $dst" }
  $srcHash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
  $dstHash = (Get-FileHash $dst -Algorithm SHA256).Hash
  if ($srcHash -ne $dstHash) {
    $bak = Join-Path $Backup $_.Name
    if (-not (Test-Path $bak)) { Copy-Item $dst $bak }
    Copy-Item $_.FullName $dst -Force
    $copied++
    Write-Host "installed $($_.Name)"
  } else {
    Write-Host "unchanged $($_.Name)"
  }
}
Write-Host "Pilot install complete: $copied changed icon(s)."
'''
    (outroot / "INSTALL_PILOT.ps1").write_text(installer, encoding="utf-8")
    print(f"Pilot built: {len(PILOT)} game-ready STI files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
