#!/usr/bin/env python3
"""
Analyze JA2/Vengeance map tile usage without modifying the map.

Reads the saved visual layers from a .dat sector and reports logical tile-type
counts for land, objects, structures, shadows, roofs and on-roof layers.

This is intentionally read-only. It is useful for prioritising graphics-only
remaster work: high-use families should be improved before low-use families.
"""
from __future__ import annotations

import argparse
import json
import struct
from collections import Counter
from pathlib import Path

# gTileSurfaceName order from vr_source/TileEngine/TileDat.cpp.
TILE_TYPES = [
    "TEXTURE1","TEXTURE2","TEXTURE3","TEXTURE4","TEXTURE5","TEXTURE6","TEXTURE7","WATER1","DEEP WATER",
    "FIRSTCLIFFHANG","FIRSTCLIFF","FIRSTCLIFFSHADOW",
    "OSTRUCT1","OSTRUCT2","OSTRUCT3","OSTRUCT4","OSTRUCT5","OSTRUCT6","OSTRUCT7","OSTRUCT8",
    "OFSTRUCT1","OFSTRUCT2","PLACEHOLDER1","PLACEHOLDER2",
    "SHADOW1","SHADOW2","SHADOW3","SHADOW4","SHADOW5","SHADOW6","SHADOW7","SHADOW8",
    "FSHADOW1","FSHADOW2","PLACEHOLDER3","PLACEHOLDER4",
    "WALL1","WALL2","WALL3","WALL4",
    "DOOR1","DOOR2","DOOR3","DOOR4",
    "DOORSH1","DOORSH2","DOORSH3","DOORSH4",
    "SLANTFLATPIECE","ANOTHERDEBRIS","ROADPIECES","WINDOW4",
    "DECORATIONS1","DECORATIONS2","DECORATIONS3","DECORATIONS4",
    "WALLDECAL1","WALLDECAL2","WALLDECAL3","WALLDECAL4",
    "FLOOR1","FLOOR2","FLOOR3","FLOOR4",
    "ROOF1","ROOF2","ROOF3","ROOF4","SROOF1","SROOF2",
    "ONROOF1","ONROOF2","MOCKF1",
    "ISTRUCT1","ISTRUCT2","ISTRUCT3","ISTRUCT4","FIRSTCISTRUCT",
    "FIRSTROAD","ROCKS","WOOD","WEEDS","GRASS","SAND","MISC",
    "ANIOSTRUCT","FENCESTRUCT","FENCESHADOW",
    "FIRSTVEHICLE","SECONDVEHICLE","FIRSTVEHICLESHADOW","SECONDVEHICLESHADOW",
    "MISC2","FIRSTDEBRISSTRUCT","SECONDDEBRISSTRUCT",
    "FIRSTDEBRISSTRUCTSHADOW","SECONDDEBRISSTRUCTSHADOW",
    "NINTHOSTRUCT","TENTHOSTRUCT","NINTHOSTRUCTSHADOW","TENTHOSTRUCTSHADOW",
    "FIRSTEXPLODEDEBRIS","SECONDEXPLODEDEBRIS",
    "FIRSTLARGEEXPLODEDEBRIS","SECONDLARGEEXPLODEDEBRIS",
    "FIRSTLARGEEXPLODEDEBRISSHADOW","SECONDLARGEEXPLODEDEBRISSHADOW",
    "FIFTHISTRUCT","SIXTHISTRUCT","SEVENTHISTRUCT","EIGHTISTRUCT",
    "FIRSTHIGHROOF","SECONDHIGHROOF",
    "WALLDECAL5","WALLDECAL6","WALLDECAL7","WALLDECAL8",
    "HUMANBLOOD","CREATUREBLOOD","FIRSTSWITCHES",
]

LAYERS = ("land", "object", "struct", "shadow", "roof", "onroof")


def tile_name(index: int) -> str:
    return TILE_TYPES[index] if 0 <= index < len(TILE_TYPES) else f"TYPE_{index}"


def parse_map(path: Path) -> dict:
    data = path.read_bytes()
    off = 0

    def need(n: int) -> None:
        if off + n > len(data):
            raise ValueError(f"{path}: truncated at offset {off}, need {n} bytes")

    if len(data) < 21:
        raise ValueError(f"{path}: file too small")

    major = struct.unpack_from("<f", data, off)[0]
    off += 4
    minor = data[off] if major >= 4.0 else 0
    if major >= 4.0:
        off += 1

    rows = cols = 160
    if major >= 7.0:
        rows, cols = struct.unpack_from("<ii", data, off)
        off += 8

    flags, tileset = struct.unpack_from("<ii", data, off)
    off += 8
    soldier_size = struct.unpack_from("<i", data, off)[0]
    off += 4

    world = rows * cols
    off += world * 2  # height values
    if off + world * 4 > len(data):
        raise ValueError(f"{path}: truncated before layer-count table")

    counts = [[0] * 6 for _ in range(world)]
    for i in range(world):
        c = data[off]
        off += 1
        counts[i][0] = c & 0x0F
        c = data[off]
        off += 1
        counts[i][1] = c & 0x0F
        counts[i][2] = (c >> 4) & 0x0F
        c = data[off]
        off += 1
        counts[i][3] = c & 0x0F
        counts[i][4] = (c >> 4) & 0x0F
        c = data[off]
        off += 1
        counts[i][5] = c & 0x0F

    usage = {layer: Counter() for layer in LAYERS}
    subindex_usage = {layer: Counter() for layer in LAYERS}

    for layer_idx, layer in enumerate(LAYERS):
        for grid in range(world):
            for _ in range(counts[grid][layer_idx]):
                if off >= len(data):
                    raise ValueError(f"{path}: truncated in {layer} layer")
                tile_type = data[off]
                off += 1
                if layer == "object":
                    if off + 2 > len(data):
                        raise ValueError(f"{path}: truncated object subindex")
                    subindex = struct.unpack_from("<H", data, off)[0]
                    off += 2
                else:
                    if off >= len(data):
                        raise ValueError(f"{path}: truncated {layer} subindex")
                    subindex = data[off]
                    off += 1

                name = tile_name(tile_type)
                usage[layer][name] += 1
                subindex_usage[layer][f"{name}:{subindex}"] += 1

    return {
        "file": str(path),
        "version": {"major": major, "minor": minor},
        "dimensions": {"rows": rows, "cols": cols, "world_tiles": world},
        "flags": flags,
        "tileset": tileset,
        "soldier_record_size": soldier_size,
        "layers": {
            layer: {
                "total": sum(usage[layer].values()),
                "tile_types": dict(usage[layer].most_common()),
                "type_subindices": dict(subindex_usage[layer].most_common()),
            }
            for layer in LAYERS
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("map", type=Path, help="Path to sector .dat")
    ap.add_argument("--json", type=Path, dest="json_out", help="Optional JSON output path")
    ap.add_argument("--top", type=int, default=20, help="Rows per layer to print")
    args = ap.parse_args()

    result = parse_map(args.map)

    print(
        f"{args.map.name}: v{result['version']['major']:.2f}."
        f"{result['version']['minor']} {result['dimensions']['rows']}x"
        f"{result['dimensions']['cols']} tileset={result['tileset']}"
    )
    for layer in LAYERS:
        info = result["layers"][layer]
        print(f"\n[{layer}] total={info['total']}")
        for name, count in list(info["tile_types"].items())[: args.top]:
            print(f"{count:7d}  {name}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
