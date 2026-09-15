#!/usr/bin/env python3
"""
Build a whole-catalogue Vengeance inventory-art replacement set.

Scope
-----
* Every unique BigItems STI referenced by Data-AIMv53/TableData/Items/Items.xml.
* All medium inventory sprite sheets: MDGUNS + MDP1ITEMS..MDP7ITEMS.
* Every converted icon receives a tiny red "AI" mark in the lower-left corner.
* Original STI dimensions, subimage count and per-subimage X/Y offsets are preserved.
* Output is staged under Generated/AllInventoryIconsAI and is NOT copied live
  unless INSTALL_ALL_ICONS.ps1 is run explicitly.

The visual pass is intentionally conservative at JA2 native scale. It improves local
contrast, edge definition and material separation. Real-world named items receive
material-aware treatment (wood/steel/polymer/glass/fabric/brass/etc.) inferred from
the item catalogue rather than a one-size-fits-all sharpen filter.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

from build_inventory_icon_pilot import (
    parse_sti,
    decode_subimage,
    indices_to_rgba,
    make_palette_and_indices,
    write_sti,
    sha256_bytes,
)

IC_GUN = 0x00000002
IC_BLADE = 0x00000004
IC_THROWING_KNIFE = 0x00000008
IC_LAUNCHER = 0x00000010
IC_THROWN = 0x00000040
IC_PUNCH = 0x00000080
IC_GRENADE = 0x00000100
IC_BOMB = 0x00000200
IC_AMMO = 0x00000400
IC_ARMOUR = 0x00000800
IC_MEDKIT = 0x00001000
IC_KIT = 0x00002000
IC_FACE = 0x00008000
IC_KEY = 0x00010000
IC_LBEGEAR = 0x00020000

PROFILES: Dict[str, Dict[str, float]] = {
    "weapon_polymer": dict(contrast=1.13, saturation=0.88, cool=0.040, warm=0.000, highlight=0.070, sharp=95),
    "weapon_steel":   dict(contrast=1.14, saturation=0.82, cool=0.050, warm=0.000, highlight=0.085, sharp=100),
    "weapon_wood":    dict(contrast=1.13, saturation=1.04, cool=0.010, warm=0.045, highlight=0.070, sharp=95),
    "blade":          dict(contrast=1.16, saturation=0.84, cool=0.045, warm=0.000, highlight=0.110, sharp=105),
    "ammo":           dict(contrast=1.14, saturation=1.02, cool=0.015, warm=0.035, highlight=0.095, sharp=100),
    "optic":          dict(contrast=1.15, saturation=0.92, cool=0.055, warm=0.000, highlight=0.105, sharp=105),
    "explosive":      dict(contrast=1.13, saturation=1.00, cool=0.015, warm=0.020, highlight=0.065, sharp=95),
    "fabric":         dict(contrast=1.12, saturation=0.94, cool=0.018, warm=0.010, highlight=0.045, sharp=85),
    "medical":        dict(contrast=1.12, saturation=0.96, cool=0.030, warm=0.000, highlight=0.055, sharp=90),
    "metal":          dict(contrast=1.15, saturation=0.84, cool=0.045, warm=0.000, highlight=0.095, sharp=100),
    "container":      dict(contrast=1.12, saturation=0.96, cool=0.020, warm=0.010, highlight=0.055, sharp=90),
    "organic":        dict(contrast=1.12, saturation=1.04, cool=0.000, warm=0.025, highlight=0.045, sharp=85),
    "neutral":        dict(contrast=1.12, saturation=0.94, cool=0.025, warm=0.005, highlight=0.055, sharp=90),
}

WOOD_WEAPON_CUES = (
    "sks", "dragunov", "svd", "thompson", "m1a1", "m1 garand", "mosin",
    "winchester", "marlin", "mini-14", "mini 14", "carcano", "enfield",
    "mauser", "kar98", "kar 98", "m2 carbine", "m1 carbine", "ruger 10/22",
)
STEEL_WEAPON_CUES = (
    "1911", "m1911", "beretta 92", "beretta 93", "revolver", "desert eagle",
    "mac-10", "mac 10", "mat-49", "mat 49", "type 85", "ppsh", "sten",
    "mp40", "tokarev", "makarov", "wildey", "remington m870",
)
POLYMER_WEAPON_CUES = (
    "glock", "mp5", "hk 53", "hk53", "p90", "m4", "m16", "aug", "uzi",
    "cx4", "storm", "g36", "fn scar", "scar-", "famas", "sig sg", "sg550",
)

OPTIC_CUES = ("scope", "sight", "laser", "goggle", "binoc", "night vision", "thermal", "reflex", "acog", "aimpoint")
FABRIC_CUES = ("vest", "pants", "trousers", "shirt", "jacket", "rig", "pack", "pouch", "holster", "sling", "bandolier", "backpack", "harness")
METAL_CUES = ("wire", "tube", "rod", "cutters", "crowbar", "key", "plate", "plating", "detector")
MEDICAL_CUES = ("medical", "first aid", "medkit", "booster", "drug", "syringe", "bandage")
CONTAINER_CUES = ("canteen", "bottle", "jar", "can", "tank", "drum")
ORGANIC_CUES = ("leaves", "claw", "blood", "meat", "skin", "herb")


def text_of(node: ET.Element, tag: str, default: str = "") -> str:
    child = node.find(tag)
    return child.text.strip() if child is not None and child.text else default


def int_of(node: ET.Element, tag: str, default: int = 0) -> int:
    try:
        return int(text_of(node, tag, str(default)), 0)
    except ValueError:
        return default


def load_catalogue(path: Path) -> List[dict]:
    root = ET.parse(path).getroot()
    out = []
    for item in root.findall(".//ITEM"):
        item_id = int_of(item, "uiIndex", -1)
        item_class = int_of(item, "usItemClass", 0)
        if item_id < 0 or item_class == 0:
            continue
        out.append({
            "id": item_id,
            "name": text_of(item, "szLongItemName") or text_of(item, "szItemName") or f"Item {item_id}",
            "short": text_of(item, "szItemName"),
            "class": item_class,
            "graphic_type": int_of(item, "ubGraphicType", 0),
            "graphic_num": int_of(item, "ubGraphicNum", 0),
        })
    return out


def expected_big_name(graphic_type: int, graphic_num: int) -> str:
    if graphic_type == 0:
        return f"gun{graphic_num:02d}.sti" if graphic_num < 10 else f"gun{graphic_num}.sti"
    return f"p{graphic_type}item{graphic_num:02d}.sti" if graphic_num < 10 else f"p{graphic_type}item{graphic_num}.sti"


def choose_profile(items: Sequence[dict]) -> str:
    names = " | ".join(i["name"].lower() for i in items)
    classes = 0
    for i in items:
        classes |= i["class"]

    if classes & (IC_GUN | IC_LAUNCHER):
        if any(x in names for x in WOOD_WEAPON_CUES):
            return "weapon_wood"
        if any(x in names for x in STEEL_WEAPON_CUES):
            return "weapon_steel"
        if any(x in names for x in POLYMER_WEAPON_CUES):
            return "weapon_polymer"
        return "weapon_steel"
    if classes & (IC_BLADE | IC_THROWING_KNIFE | IC_PUNCH | IC_THROWN):
        return "blade"
    if classes & IC_AMMO:
        return "ammo"
    if classes & (IC_GRENADE | IC_BOMB):
        return "explosive"
    if classes & (IC_ARMOUR | IC_LBEGEAR):
        return "fabric"
    if classes & IC_MEDKIT:
        return "medical"
    if classes & IC_FACE or any(x in names for x in OPTIC_CUES):
        return "optic"
    if classes & IC_KEY or any(x in names for x in METAL_CUES):
        return "metal"
    if classes & IC_KIT or any(x in names for x in MEDICAL_CUES):
        return "medical"
    if any(x in names for x in FABRIC_CUES):
        return "fabric"
    if any(x in names for x in CONTAINER_CUES):
        return "container"
    if any(x in names for x in ORGANIC_CUES):
        return "organic"
    return "neutral"


def improve_rgba(im: Image.Image, profile_name: str) -> Image.Image:
    p = PROFILES[profile_name]
    alpha = np.asarray(im.getchannel("A"), dtype=np.uint8)

    rgb = im.convert("RGB")
    scale = 4
    big = rgb.resize((max(1, rgb.width * scale), max(1, rgb.height * scale)), Image.Resampling.LANCZOS)
    big = ImageEnhance.Contrast(big).enhance(p["contrast"])
    big = ImageEnhance.Color(big).enhance(p["saturation"])
    big = big.filter(ImageFilter.UnsharpMask(radius=1.05 * scale, percent=int(p["sharp"]), threshold=2))
    rgb = big.resize(rgb.size, Image.Resampling.LANCZOS)

    arr = np.asarray(rgb, dtype=np.float32) / 255.0
    h, w, _ = arr.shape

    if h > 1 and w > 1:
        yy, xx = np.mgrid[0:h, 0:w]
        light = 1.0 + p["highlight"] * (1.10 - 0.58 * xx / (w - 1) - 0.52 * yy / (h - 1))
        arr *= light[..., None]

    lum = np.clip(arr.mean(axis=2), 0, 1)
    cool = p["cool"] * (0.25 + 0.75 * lum)
    warm = p["warm"] * (0.25 + 0.75 * lum)
    arr[..., 2] += cool
    arr[..., 0] += warm
    arr[..., 1] += warm * 0.34

    if profile_name == "weapon_wood":
        mid = np.clip(1.0 - np.abs(lum - 0.46) * 2.2, 0, 1)
        arr[..., 0] += 0.030 * mid
        arr[..., 1] += 0.010 * mid
    elif profile_name in ("weapon_steel", "metal", "blade"):
        hi = np.clip((lum - 0.42) * 1.75, 0, 1)
        arr[..., 2] += hi * 0.025
        arr += hi[..., None] * 0.012
    elif profile_name == "ammo":
        mid = np.clip(1.0 - np.abs(lum - 0.55) * 2.0, 0, 1)
        arr[..., 0] += mid * 0.025
        arr[..., 1] += mid * 0.014
    elif profile_name == "optic":
        dark = np.clip(1.0 - lum, 0, 1)
        arr[..., 2] += 0.022 * dark
    elif profile_name == "fabric":
        arr *= (0.985 + 0.015 * lum[..., None])

    arr = np.clip(arr, 0, 1)
    rgba = np.dstack([(arr * 255.0 + 0.5).astype(np.uint8), alpha])
    rgba[alpha == 0, :3] = 0
    return Image.fromarray(rgba, "RGBA")


GLYPH_A = ("010", "101", "111", "101", "101")
GLYPH_I = ("111", "010", "010", "010", "111")


def add_ai_mark(im: Image.Image) -> Image.Image:
    out = im.copy()
    draw = ImageDraw.Draw(out)
    h, w = out.height, out.width
    scale = 2 if h >= 32 and w >= 32 else 1
    mark_w = 7 * scale
    mark_h = 5 * scale
    if w < mark_w + 1 or h < mark_h + 1:
        scale = 1
        mark_w = 7
        mark_h = 5
    if w < mark_w or h < mark_h:
        return out

    x0 = 1 if w > mark_w + 1 else 0
    y0 = max(0, h - mark_h - 1)
    shadow = (48, 0, 0, 255)
    red = (238, 28, 28, 255)

    def glyph(bits: Sequence[str], x: int, y: int) -> None:
        for gy, row in enumerate(bits):
            for gx, bit in enumerate(row):
                if bit != "1":
                    continue
                xx = x + gx * scale
                yy = y + gy * scale
                draw.rectangle((xx + 1, yy + 1, xx + scale, yy + scale), fill=shadow)
        for gy, row in enumerate(bits):
            for gx, bit in enumerate(row):
                if bit != "1":
                    continue
                xx = x + gx * scale
                yy = y + gy * scale
                draw.rectangle((xx, yy, xx + scale - 1, yy + scale - 1), fill=red)

    glyph(GLYPH_A, x0, y0)
    glyph(GLYPH_I, x0 + 4 * scale, y0)
    return out


def validate_geometry(before: dict, after: dict, filename: str) -> None:
    if len(before["subs"]) != len(after["subs"]):
        raise ValueError(f"{filename}: subimage count changed")
    for a, b in zip(before["subs"], after["subs"]):
        for key in ("offset_x", "offset_y", "height", "width"):
            if a[key] != b[key]:
                raise ValueError(f"{filename}: {key} changed")


def rebuild_sti(src: Path, dst: Path, profile: str, mark_ai: bool = True) -> dict:
    raw = src.read_bytes()
    sti = parse_sti(raw)
    before_idx = [decode_subimage(sti, s) for s in sti["subs"]]
    before_rgba = [indices_to_rgba(x, sti["palette"]) for x in before_idx]

    after_rgba = []
    for im in before_rgba:
        new = improve_rgba(im, profile)
        if mark_ai:
            new = add_ai_mark(new)
        after_rgba.append(new)

    palette, after_idx = make_palette_and_indices(after_rgba)
    rebuilt = write_sti(sti, palette, after_idx)
    check = parse_sti(rebuilt)
    validate_geometry(sti, check, src.name)
    [decode_subimage(check, s) for s in check["subs"]]

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(rebuilt)
    return {
        "source_sha256": sha256_bytes(raw),
        "output_sha256": sha256_bytes(rebuilt),
        "source_bytes": len(raw),
        "output_bytes": len(rebuilt),
        "subimages": len(sti["subs"]),
    }


def write_installer(outroot: Path) -> None:
    ps1 = r'''param(
  [switch]$Revert
)
$ErrorActionPreference = "Stop"
$PackRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$GameRoot = Resolve-Path (Join-Path $PackRoot "..\..")
$Payload = Join-Path $PackRoot "Data-AIMv53"
$Live = Join-Path $GameRoot "Data-AIMv53"
$Backup = Join-Path $PackRoot "_backup\Data-AIMv53"

if ($Revert) {
  if (-not (Test-Path $Backup)) { throw "No icon backup exists." }
  Get-ChildItem $Backup -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($Backup.Length).TrimStart("\")
    $dst = Join-Path $Live $rel
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
    Copy-Item $_.FullName $dst -Force
    Write-Host "restored $rel"
  }
  exit 0
}

$changed = 0
Get-ChildItem $Payload -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Substring($Payload.Length).TrimStart("\")
  $dst = Join-Path $Live $rel
  if (-not (Test-Path $dst)) {
    Write-Warning "Live asset missing, skipped: $rel"
    return
  }
  $srcHash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
  $dstHash = (Get-FileHash $dst -Algorithm SHA256).Hash
  if ($srcHash -ne $dstHash) {
    $bak = Join-Path $Backup $rel
    if (-not (Test-Path $bak)) {
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $bak) | Out-Null
      Copy-Item $dst $bak
    }
    Copy-Item $_.FullName $dst -Force
    $changed++
    Write-Host "installed $rel"
  }
}
Write-Host "Inventory icon replacement complete: $changed changed file(s)."
'''
    (outroot / "INSTALL_ALL_ICONS.ps1").write_text(ps1, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    items_xml = root / "Data-AIMv53" / "TableData" / "Items" / "Items.xml"
    big_dir = root / "Data-AIMv53" / "BigItems"
    interface_dir = root / "Data-AIMv53" / "Interface"
    outroot = root / "Generated" / "AllInventoryIconsAI"
    out_data = outroot / "Data-AIMv53"

    catalog = load_catalogue(items_xml)
    by_graphic: Dict[Tuple[int, int], List[dict]] = defaultdict(list)
    for item in catalog:
        by_graphic[(item["graphic_type"], item["graphic_num"])].append(item)

    actual_big = {p.name.lower(): p for p in big_dir.iterdir() if p.is_file() and p.suffix.lower() == ".sti"}

    manifest = {
        "description": "Whole-game Vengeance inventory icon improvement set with red AI marker",
        "item_records": len(catalog),
        "unique_referenced_graphics": len(by_graphic),
        "big_items": [],
        "interface_sheets": [],
        "missing_big_items": [],
    }

    changed = 0
    for (gt, gn), refs in sorted(by_graphic.items()):
        expected = expected_big_name(gt, gn)
        src = actual_big.get(expected.lower())
        if src is None:
            manifest["missing_big_items"].append({
                "graphic_type": gt,
                "graphic_num": gn,
                "expected": expected,
                "items": [{"id": x["id"], "name": x["name"]} for x in refs],
            })
            continue
        profile = choose_profile(refs)
        dst = out_data / "BigItems" / src.name
        info = rebuild_sti(src, dst, profile, mark_ai=True)
        manifest["big_items"].append({
            "file": src.name,
            "graphic_type": gt,
            "graphic_num": gn,
            "profile": profile,
            "items": [{"id": x["id"], "name": x["name"]} for x in refs],
            **info,
        })
        changed += 1
        if changed % 100 == 0:
            print(f"converted {changed} BigItems assets")

    sheet_names = [
        "MDGUNS.sti",
        "MDP1ITEMS.sti",
        "MDP2ITEMS.STI",
        "MDP3ITEMS.STI",
        "MDP4ITEMS.sti",
        "MDP5ITEMS.sti",
        "MDP6ITEMS.STI",
        "MDP7ITEMS.STI",
    ]
    lower_interface = {p.name.lower(): p for p in interface_dir.iterdir() if p.is_file()}
    for sheet in sheet_names:
        src = lower_interface.get(sheet.lower())
        if src is None:
            raise FileNotFoundError(f"missing interface sheet: {sheet}")
        dst = out_data / "Interface" / src.name
        info = rebuild_sti(src, dst, "neutral", mark_ai=True)
        manifest["interface_sheets"].append({"file": src.name, **info})
        print(f"converted interface sheet {src.name} ({info['subimages']} subimages)")

    outroot.mkdir(parents=True, exist_ok=True)
    (outroot / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    write_installer(outroot)
    (outroot / "README.md").write_text(
        "# Whole-game Vengeance inventory icon replacement\n\n"
        "Generated game-ready STI assets for every referenced BigItems graphic plus "
        "the MDGUNS/MDP1..7 inventory sheets. Every converted icon carries a tiny "
        "red AI stamp in its lower-left corner. Geometry and offsets are preserved.\n\n"
        "Nothing is installed automatically. Run INSTALL_ALL_ICONS.ps1 from this "
        "folder to install incrementally with automatic backups. Use -Revert to restore.\n",
        encoding="utf-8",
    )

    print(
        f"done: {len(manifest['big_items'])} BigItems files, "
        f"{len(manifest['interface_sheets'])} interface sheets, "
        f"{len(manifest['missing_big_items'])} missing referenced BigItems"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
