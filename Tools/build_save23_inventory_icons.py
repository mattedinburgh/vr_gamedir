#!/usr/bin/env python3
"""
Build the inventory-art replacement pack for the 94 unique item IDs extracted
from Matt's SaveGame23.sav.

Rules:
* Only graphics referenced by those 94 items are changed.
* BigItems: only the referenced individual STI files are rebuilt.
* Medium inventory sheets: only selected subimages are altered; every other
  subimage is verified pixel-for-pixel identical after rebuild.
* Every changed icon receives a small red "AI" stamp at the bottom-left.
* Dimensions, offsets, object counts and transparency are preserved.
* Output is staged under Pilot/Save23InventoryIconsAI and is never installed
  automatically.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from build_inventory_icon_pilot import (
    parse_sti,
    decode_subimage,
    indices_to_rgba,
    make_palette_and_indices,
    write_sti,
    sha256_bytes,
)

SAVE_ITEM_IDS = [
    2, 8, 17, 19, 22, 37, 38, 71, 72, 73, 94, 96, 132, 134, 139, 145,
    146, 151, 164, 165, 170, 177, 183, 196, 199, 203, 205, 208, 210, 211,
    212, 213, 214, 222, 235, 241, 242, 243, 246, 283, 294, 345, 401, 474,
    545, 546, 593, 596, 600, 632, 633, 692, 713, 726, 731, 759, 810, 811,
    812, 1003, 1027, 1029, 1057, 1078, 1089, 1090, 1091, 1097, 1098, 1172,
    1178, 1183, 1204, 1525, 1570, 1576, 1618, 1646, 1647, 1663, 1709, 2117,
    2144, 2145, 2420, 2462, 2502, 2515, 2520, 2612, 2618, 2699, 2700, 2801,
]

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

PROFILES = {
    "weapon_polymer": dict(contrast=1.14, saturation=0.88, cool=0.045, warm=0.000, highlight=0.075, sharp=100),
    "weapon_steel":   dict(contrast=1.15, saturation=0.82, cool=0.052, warm=0.000, highlight=0.090, sharp=105),
    "weapon_wood":    dict(contrast=1.14, saturation=1.04, cool=0.010, warm=0.050, highlight=0.075, sharp=100),
    "blade":          dict(contrast=1.17, saturation=0.84, cool=0.050, warm=0.000, highlight=0.115, sharp=110),
    "ammo":           dict(contrast=1.15, saturation=1.03, cool=0.015, warm=0.040, highlight=0.100, sharp=105),
    "optic":          dict(contrast=1.16, saturation=0.92, cool=0.060, warm=0.000, highlight=0.110, sharp=110),
    "explosive":      dict(contrast=1.14, saturation=1.00, cool=0.018, warm=0.022, highlight=0.070, sharp=100),
    "fabric":         dict(contrast=1.13, saturation=0.95, cool=0.020, warm=0.010, highlight=0.050, sharp=90),
    "medical":        dict(contrast=1.13, saturation=0.97, cool=0.032, warm=0.000, highlight=0.060, sharp=95),
    "metal":          dict(contrast=1.16, saturation=0.85, cool=0.050, warm=0.000, highlight=0.100, sharp=105),
    "container":      dict(contrast=1.13, saturation=0.97, cool=0.022, warm=0.012, highlight=0.060, sharp=95),
    "organic":        dict(contrast=1.13, saturation=1.05, cool=0.000, warm=0.028, highlight=0.050, sharp=90),
    "neutral":        dict(contrast=1.13, saturation=0.95, cool=0.028, warm=0.005, highlight=0.060, sharp=95),
}

WOOD_WEAPON_CUES = (
    "sks", "dragunov", "svd", "thompson", "m1a1", "mini-14", "mini 14",
    "marlin", "m2 carbine", "m1 carbine",
)
STEEL_WEAPON_CUES = (
    "1911", "m1911", "beretta", "revolver", "desert eagle", "mat-49",
    "type 85", "wildey", "remington", "street sweeper",
)
POLYMER_WEAPON_CUES = (
    "glock", "mp5", "hk 53", "hk53", "m4", "m16", "aug", "uzi",
    "cx4", "storm", "sig sg", "sg550",
)
OPTIC_CUES = ("scope", "sight", "laser", "goggle", "binoc", "night vision", "thermal")
FABRIC_CUES = ("vest", "pants", "trousers", "shirt", "rig", "pack", "pouch", "holster", "sling", "bandolier", "harness")
METAL_CUES = ("wire", "tube", "rod", "cutters", "crowbar", "key", "plate", "plating", "detector", "carabiner")
MEDICAL_CUES = ("medical", "first aid", "medic", "booster", "drug", "cleaning kit", "camo")
CONTAINER_CUES = ("canteen", "bottle", "jar", "can", "tank")
ORGANIC_CUES = ("leaves", "claw", "blood", "herb")


def txt(node: ET.Element, tag: str, default: str = "") -> str:
    c = node.find(tag)
    return c.text.strip() if c is not None and c.text else default


def num(node: ET.Element, tag: str, default: int = 0) -> int:
    try:
        return int(txt(node, tag, str(default)), 0)
    except ValueError:
        return default


def load_selected_items(path: Path) -> List[dict]:
    wanted = set(SAVE_ITEM_IDS)
    root = ET.parse(path).getroot()
    found = {}
    for node in root.findall(".//ITEM"):
        item_id = num(node, "uiIndex", -1)
        if item_id not in wanted:
            continue
        found[item_id] = {
            "id": item_id,
            "name": txt(node, "szLongItemName") or txt(node, "szItemName") or f"Item {item_id}",
            "short": txt(node, "szItemName"),
            "class": num(node, "usItemClass", 0),
            "graphic_type": num(node, "ubGraphicType", 0),
            "graphic_num": num(node, "ubGraphicNum", 0),
        }
    missing = sorted(wanted - set(found))
    if missing:
        raise RuntimeError(f"Save item IDs missing from Items.xml: {missing}")
    return [found[i] for i in SAVE_ITEM_IDS]


def big_filename(gt: int, gn: int) -> str:
    if gt == 0:
        return f"gun{gn:02d}.sti" if gn < 10 else f"gun{gn}.sti"
    return f"p{gt}item{gn:02d}.sti" if gn < 10 else f"p{gt}item{gn}.sti"


def profile_for(items: Sequence[dict]) -> str:
    names = " | ".join(x["name"].lower() for x in items)
    classes = 0
    for x in items:
        classes |= x["class"]

    if classes & (IC_GUN | IC_LAUNCHER):
        if any(c in names for c in WOOD_WEAPON_CUES):
            return "weapon_wood"
        if any(c in names for c in STEEL_WEAPON_CUES):
            return "weapon_steel"
        if any(c in names for c in POLYMER_WEAPON_CUES):
            return "weapon_polymer"
        return "weapon_steel"
    if classes & (IC_BLADE | IC_THROWING_KNIFE | IC_THROWN | IC_PUNCH):
        return "blade"
    if classes & IC_AMMO:
        return "ammo"
    if classes & (IC_GRENADE | IC_BOMB):
        return "explosive"
    if classes & (IC_ARMOUR | IC_LBEGEAR):
        return "fabric"
    if classes & IC_FACE or any(c in names for c in OPTIC_CUES):
        return "optic"
    if classes & IC_MEDKIT:
        return "medical"
    if classes & IC_KEY or any(c in names for c in METAL_CUES):
        return "metal"
    if classes & IC_KIT or any(c in names for c in MEDICAL_CUES):
        return "medical"
    if any(c in names for c in FABRIC_CUES):
        return "fabric"
    if any(c in names for c in CONTAINER_CUES):
        return "container"
    if any(c in names for c in ORGANIC_CUES):
        return "organic"
    return "neutral"


def enhance(im: Image.Image, profile: str) -> Image.Image:
    p = PROFILES[profile]
    alpha = np.asarray(im.getchannel("A"), dtype=np.uint8)
    rgb = im.convert("RGB")
    scale = 4
    big = rgb.resize((max(1, rgb.width * scale), max(1, rgb.height * scale)), Image.Resampling.LANCZOS)
    big = ImageEnhance.Contrast(big).enhance(p["contrast"])
    big = ImageEnhance.Color(big).enhance(p["saturation"])
    big = big.filter(ImageFilter.UnsharpMask(radius=1.10 * scale, percent=int(p["sharp"]), threshold=2))
    rgb = big.resize(rgb.size, Image.Resampling.LANCZOS)

    arr = np.asarray(rgb, dtype=np.float32) / 255.0
    h, w, _ = arr.shape
    if h > 1 and w > 1:
        yy, xx = np.mgrid[0:h, 0:w]
        arr *= (1.0 + p["highlight"] * (1.08 - 0.55 * xx / (w - 1) - 0.48 * yy / (h - 1)))[..., None]

    lum = np.clip(arr.mean(axis=2), 0, 1)
    arr[..., 2] += p["cool"] * (0.25 + 0.75 * lum)
    arr[..., 0] += p["warm"] * (0.25 + 0.75 * lum)
    arr[..., 1] += p["warm"] * 0.34

    if profile == "weapon_wood":
        mid = np.clip(1.0 - np.abs(lum - 0.46) * 2.2, 0, 1)
        arr[..., 0] += 0.035 * mid
        arr[..., 1] += 0.012 * mid
    elif profile in ("weapon_steel", "metal", "blade"):
        hi = np.clip((lum - 0.42) * 1.75, 0, 1)
        arr[..., 2] += hi * 0.028
        arr += hi[..., None] * 0.014
    elif profile == "ammo":
        mid = np.clip(1.0 - np.abs(lum - 0.55) * 2.0, 0, 1)
        arr[..., 0] += mid * 0.030
        arr[..., 1] += mid * 0.018
    elif profile == "optic":
        arr[..., 2] += np.clip(1.0 - lum, 0, 1) * 0.025

    arr = np.clip(arr, 0, 1)
    rgba = np.dstack([(arr * 255.0 + 0.5).astype(np.uint8), alpha])
    rgba[alpha == 0, :3] = 0
    return Image.fromarray(rgba, "RGBA")


AI_A = ("010", "101", "111", "101", "101")
AI_I = ("111", "010", "010", "010", "111")


def ai_pixels(h: int, w: int, scale: int | None = None):
    if scale is None:
        scale = 2 if h >= 32 and w >= 32 else 1
    if w < 7 * scale + 1 or h < 5 * scale + 1:
        scale = 1
    if w < 7 or h < 5:
        return [], []
    x0 = 1 if w > 8 * scale else 0
    y0 = max(0, h - 5 * scale - 1)
    fg, sh = [], []

    def add(bits, gx0):
        for gy, row in enumerate(bits):
            for gx, bit in enumerate(row):
                if bit != "1":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        x = gx0 + gx * scale + sx
                        y = y0 + gy * scale + sy
                        if 0 <= x < w and 0 <= y < h:
                            fg.append((y, x))
                        if 0 <= x + 1 < w and 0 <= y + 1 < h:
                            sh.append((y + 1, x + 1))

    add(AI_A, x0)
    add(AI_I, x0 + 4 * scale)
    return fg, sh


def stamp_rgba(im: Image.Image) -> Image.Image:
    arr = np.array(im, dtype=np.uint8, copy=True)
    fg, sh = ai_pixels(arr.shape[0], arr.shape[1])
    for y, x in sh:
        arr[y, x] = (48, 0, 0, 255)
    for y, x in fg:
        arr[y, x] = (238, 28, 28, 255)
    return Image.fromarray(arr, "RGBA")


def nearest_palette_indices(rgb: np.ndarray, palette: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    src = rgb.astype(np.int32)
    pal = palette[allowed].astype(np.int32)
    out = np.empty(len(src), dtype=np.uint8)
    for start in range(0, len(src), 4096):
        chunk = src[start:start + 4096]
        d = ((chunk[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
        out[start:start + len(chunk)] = allowed[np.argmin(d, axis=1)]
    return out


def reserve_stamp_colours(palette: np.ndarray, decoded: Sequence[np.ndarray]) -> Tuple[np.ndarray, int, int]:
    pal = palette.copy()
    used = set()
    for x in decoded:
        used.update(int(v) for v in np.unique(x))
    unused = [i for i in range(1, 256) if i not in used]

    def nearest(target):
        q = pal[1:].astype(np.int32)
        t = np.array(target, dtype=np.int32)
        return 1 + int(np.argmin(((q - t) ** 2).sum(axis=1)))

    if len(unused) >= 2:
        red_idx, shadow_idx = unused[0], unused[1]
        pal[red_idx] = (238, 28, 28)
        pal[shadow_idx] = (48, 0, 0)
    elif len(unused) == 1:
        red_idx = unused[0]
        pal[red_idx] = (238, 28, 28)
        shadow_idx = nearest((48, 0, 0))
    else:
        red_idx = nearest((238, 28, 28))
        shadow_idx = nearest((48, 0, 0))
    return pal, red_idx, shadow_idx


def rebuild_big(src: Path, dst: Path, profile: str) -> dict:
    raw = src.read_bytes()
    sti = parse_sti(raw)
    old = [decode_subimage(sti, s) for s in sti["subs"]]
    imgs = [stamp_rgba(enhance(indices_to_rgba(x, sti["palette"]), profile)) for x in old]
    pal, idx = make_palette_and_indices(imgs)
    rebuilt = write_sti(sti, pal, idx)
    check = parse_sti(rebuilt)
    if len(check["subs"]) != len(sti["subs"]):
        raise RuntimeError(f"{src.name}: subimage count changed")
    for a, b in zip(sti["subs"], check["subs"]):
        for k in ("offset_x", "offset_y", "height", "width"):
            if a[k] != b[k]:
                raise RuntimeError(f"{src.name}: {k} changed")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(rebuilt)
    return {
        "source_sha256": sha256_bytes(raw),
        "output_sha256": sha256_bytes(rebuilt),
        "subimages": len(sti["subs"]),
    }


def rebuild_medium(src: Path, dst: Path, selected: Dict[int, str]) -> dict:
    raw = src.read_bytes()
    sti = parse_sti(raw)
    old = [decode_subimage(sti, s) for s in sti["subs"]]
    invalid = sorted(i for i in selected if i < 0 or i >= len(old))
    if invalid:
        raise RuntimeError(f"{src.name}: graphic indices outside sheet: {invalid}")

    palette, red_idx, shadow_idx = reserve_stamp_colours(sti["palette"], old)
    allowed = np.array([i for i in range(1, 256) if i not in (red_idx, shadow_idx)], dtype=np.uint8)
    if len(allowed) == 0:
        raise RuntimeError(f"{src.name}: no palette colours available")

    new = [x.copy() for x in old]
    for sub_idx, profile in selected.items():
        rgba = enhance(indices_to_rgba(old[sub_idx], sti["palette"]), profile)
        arr = np.asarray(rgba, dtype=np.uint8)
        mask = arr[..., 3] > 0
        px = arr[..., :3][mask]
        q = nearest_palette_indices(px, palette, allowed)
        idx = np.zeros(old[sub_idx].shape, dtype=np.uint8)
        idx[mask] = q

        fg, sh = ai_pixels(idx.shape[0], idx.shape[1])
        for y, x in sh:
            idx[y, x] = shadow_idx
        for y, x in fg:
            idx[y, x] = red_idx
        new[sub_idx] = idx

    rebuilt = write_sti(sti, palette, new)
    check = parse_sti(rebuilt)
    decoded = [decode_subimage(check, s) for s in check["subs"]]
    if len(decoded) != len(old):
        raise RuntimeError(f"{src.name}: subimage count changed")

    changed = set(selected)
    for i, (before, after) in enumerate(zip(old, decoded)):
        if i not in changed and not np.array_equal(before, after):
            raise RuntimeError(f"{src.name}: untouched subimage {i} changed")
    for a, b in zip(sti["subs"], check["subs"]):
        for k in ("offset_x", "offset_y", "height", "width"):
            if a[k] != b[k]:
                raise RuntimeError(f"{src.name}: {k} changed")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(rebuilt)
    return {
        "source_sha256": sha256_bytes(raw),
        "output_sha256": sha256_bytes(rebuilt),
        "subimages": len(old),
        "changed_subimages": sorted(changed),
        "untouched_subimages_verified": len(old) - len(changed),
        "red_palette_index": red_idx,
        "shadow_palette_index": shadow_idx,
    }


def write_installer(outroot: Path) -> None:
    ps1 = r'''param([switch]$Revert)
$ErrorActionPreference = "Stop"
$PackRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$GameRoot = Resolve-Path (Join-Path $PackRoot "..\..")
$Payload = Join-Path $PackRoot "Data-AIMv53"
$Live = Join-Path $GameRoot "Data-AIMv53"
$Backup = Join-Path $PackRoot "_backup\Data-AIMv53"

if ($Revert) {
  if (-not (Test-Path $Backup)) { throw "No Save23 icon backup exists." }
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
  if (-not (Test-Path $dst)) { throw "Live asset missing: $rel" }
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
  } else {
    Write-Host "unchanged $rel"
  }
}
Write-Host "Save23 icon install complete: $changed changed file(s)."
'''
    (outroot / "INSTALL_SAVE23_ICONS.ps1").write_text(ps1, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    items = load_selected_items(root / "Data-AIMv53" / "TableData" / "Items" / "Items.xml")
    by_graphic: Dict[Tuple[int, int], List[dict]] = defaultdict(list)
    for x in items:
        by_graphic[(x["graphic_type"], x["graphic_num"])].append(x)

    outroot = root / "Pilot" / "Save23InventoryIconsAI"
    outdata = outroot / "Data-AIMv53"
    bigdir = root / "Data-AIMv53" / "BigItems"
    intfdir = root / "Data-AIMv53" / "Interface"
    actual_big = {p.name.lower(): p for p in bigdir.iterdir() if p.is_file() and p.suffix.lower() == ".sti"}
    actual_intf = {p.name.lower(): p for p in intfdir.iterdir() if p.is_file()}

    manifest = {
        "source": "SaveGame23.sav extracted inventory",
        "unique_item_ids": len(items),
        "unique_graphics": len(by_graphic),
        "ai_mark": "red AI, bottom-left of every changed icon",
        "deployment": "NOT DEPLOYED; run INSTALL_SAVE23_ICONS.ps1 manually",
        "items": items,
        "big_items": [],
        "medium_sheets": [],
    }

    # Individual large inventory art.
    for (gt, gn), refs in sorted(by_graphic.items()):
        name = big_filename(gt, gn)
        src = actual_big.get(name.lower())
        if src is None:
            raise FileNotFoundError(f"Missing referenced BigItems asset {name}")
        profile = profile_for(refs)
        info = rebuild_big(src, outdata / "BigItems" / src.name, profile)
        manifest["big_items"].append({
            "file": src.name,
            "graphic_type": gt,
            "graphic_num": gn,
            "profile": profile,
            "items": [{"id": x["id"], "name": x["name"]} for x in refs],
            **info,
        })

    # Shared medium sheets: change only save-referenced subimages.
    by_type: Dict[int, Dict[int, str]] = defaultdict(dict)
    for (gt, gn), refs in by_graphic.items():
        by_type[gt][gn] = profile_for(refs)

    sheet_name = {
        0: "MDGUNS.sti",
        1: "MDP1ITEMS.sti",
        2: "MDP2ITEMS.STI",
        3: "MDP3ITEMS.STI",
        4: "MDP4ITEMS.sti",
        5: "MDP5ITEMS.sti",
        6: "MDP6ITEMS.STI",
        7: "MDP7ITEMS.STI",
    }
    for gt, selected in sorted(by_type.items()):
        wanted = sheet_name[gt]
        src = actual_intf.get(wanted.lower())
        if src is None:
            raise FileNotFoundError(f"Missing interface sheet {wanted}")
        info = rebuild_medium(src, outdata / "Interface" / src.name, selected)
        manifest["medium_sheets"].append({
            "file": src.name,
            "graphic_type": gt,
            "changed_count": len(selected),
            **info,
        })

    outroot.mkdir(parents=True, exist_ok=True)
    (outroot / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (outroot / "README.md").write_text(
        "# SaveGame23 inventory icon replacement\n\n"
        "This pack changes only the 94 unique item IDs extracted from SaveGame23.sav. "
        "Large BigItems STIs are replaced only for graphics referenced by those items. "
        "In shared MDGUNS/MDP sprite sheets, only those specific subimages are changed; "
        "all other subimages are round-trip verified pixel-for-pixel identical.\n\n"
        "Every changed icon has a small red AI stamp in its bottom-left corner.\n\n"
        "Nothing is deployed automatically. Run INSTALL_SAVE23_ICONS.ps1 to install "
        "incrementally with backups; use -Revert to restore originals.\n",
        encoding="utf-8",
    )
    write_installer(outroot)

    print(f"Save23 pack built: {len(items)} unique items, {len(by_graphic)} unique graphics")
    print(f"Large STIs: {len(manifest['big_items'])}; medium sheets: {len(manifest['medium_sheets'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
