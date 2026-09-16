#!/usr/bin/env python3
"""Audit Vengeance militia equipment pools against opposing army pools.

This tool is intentionally read-only. It treats the XML choice tables as the
authoritative loadout data and produces a reproducible progression-by-progression
comparison instead of relying on manual spot checks.

Use:
    python Tools/AuditMilitiaArmyEquipment.py
    python Tools/AuditMilitiaArmyEquipment.py --check

--check additionally fails on malformed choice tables, missing progression bands,
invalid choice counts, unknown gun IDs, or unknown item IDs.
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import statistics
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
INV = ROOT / "Data-AIMv53" / "TableData" / "Inventory"
ITEMS = ROOT / "Data-AIMv53" / "TableData" / "Items"

TIER_PAIRS = (
    ("green", "admin", "GunChoices_Militia_Green.xml", "GunChoices_Enemy_Admin.xml",
     "ItemChoices_Militia_Green.xml", "ItemChoices_Enemy_Admin.xml"),
    ("regular", "regular", "GunChoices_Militia_Regular.xml", "GunChoices_Enemy_Regular.xml",
     "ItemChoices_Militia_Regular.xml", "ItemChoices_Enemy_Regular.xml"),
    ("elite", "elite", "GunChoices_Militia_Elite.xml", "GunChoices_Enemy_Elite.xml",
     "ItemChoices_Militia_Elite.xml", "ItemChoices_Enemy_Elite.xml"),
)

EXPECTED_PROGRESS = [f"{i}%" for i in range(0, 101, 10)]


def parse_int(text: str | None, default: int = 0) -> int:
    try:
        return int((text or "").strip())
    except ValueError:
        return default


def load_item_names() -> dict[int, str]:
    names: dict[int, str] = {}
    path = ITEMS / "Items.xml"
    root = ET.parse(path).getroot()
    for node in root.iter():
        idx_node = node.find("uiIndex")
        if idx_node is None:
            continue
        idx = parse_int(idx_node.text, -1)
        if idx < 0:
            continue
        name = ""
        for tag in ("szItemName", "szLongItemName", "szBRName", "szItemDesc"):
            candidate = node.findtext(tag)
            if candidate and candidate.strip():
                name = candidate.strip()
                break
        names[idx] = name or f"item-{idx}"
    return names


def load_weapons() -> dict[int, dict[str, float | str]]:
    weapons: dict[int, dict[str, float | str]] = {}
    root = ET.parse(ITEMS / "Weapons.xml").getroot()
    for node in root.findall("WEAPON"):
        idx = parse_int(node.findtext("uiIndex"), -1)
        if idx < 0:
            continue

        def number(tag: str) -> float:
            try:
                return float((node.findtext(tag) or "0").strip())
            except ValueError:
                return 0.0

        weapons[idx] = {
            "name": (node.findtext("szWeaponName") or f"weapon-{idx}").strip(),
            "range": number("usRange"),
            "impact": number("ubImpact"),
            "accuracy": number("nAccuracy"),
            "aim": number("ubAimLevels"),
            "handling": number("Handling"),
            "deadliness": number("ubDeadliness"),
        }
    return weapons


def choice_ids(node: ET.Element) -> list[int]:
    count = parse_int(node.findtext("ubChoices"), 0)
    result: list[int] = []
    for i in range(1, count + 1):
        value = parse_int(node.findtext(f"bItemNo{i}"), 0)
        if value:
            result.append(value)
    return result


def load_gun_choices(path: pathlib.Path) -> list[dict[str, object]]:
    root = ET.parse(path).getroot()
    rows = []
    for node in root.findall("ENEMYGUNCHOICES"):
        rows.append({
            "index": parse_int(node.findtext("uiIndex"), -1),
            "name": (node.findtext("name") or "").strip(),
            "count": parse_int(node.findtext("ubChoices"), 0),
            "ids": choice_ids(node),
        })
    return rows


def load_item_choices(path: pathlib.Path) -> list[dict[str, object]]:
    root = ET.parse(path).getroot()
    rows = []
    for node in root.findall("ENEMYITEMCHOICES"):
        rows.append({
            "index": parse_int(node.findtext("uiIndex"), -1),
            "name": (node.findtext("name") or "").strip(),
            "count": parse_int(node.findtext("ubChoices"), 0),
            "ids": choice_ids(node),
        })
    return rows


def weighted_average(ids: list[int], weapons: dict[int, dict[str, float | str]], key: str) -> float:
    values = [float(weapons[i][key]) for i in ids if i in weapons]
    return statistics.fmean(values) if values else 0.0


def fmt_names(ids: list[int], weapons: dict[int, dict[str, float | str]], limit: int = 5) -> str:
    counts = collections.Counter(ids)
    ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    labels = []
    for item_id, count in ordered[:limit]:
        name = str(weapons.get(item_id, {}).get("name", f"#{item_id}"))
        labels.append(f"{name}" + (f" x{count}" if count > 1 else ""))
    if len(ordered) > limit:
        labels.append(f"+{len(ordered) - limit} more")
    return ", ".join(labels)


def validate_gun_table(path: pathlib.Path, rows: list[dict[str, object]], weapons: dict[int, dict[str, float | str]]) -> list[str]:
    errors: list[str] = []
    names = [str(r["name"]) for r in rows]
    if names != EXPECTED_PROGRESS:
        errors.append(f"{path.name}: progression bands are {names}, expected {EXPECTED_PROGRESS}")
    for row in rows:
        ids = list(row["ids"])
        if len(ids) != int(row["count"]):
            errors.append(f"{path.name} {row['name']}: ubChoices={row['count']} but {len(ids)} non-zero choices found")
        missing = sorted({i for i in ids if i not in weapons})
        if missing:
            errors.append(f"{path.name} {row['name']}: unknown weapon IDs {missing}")
    return errors


def validate_item_table(path: pathlib.Path, rows: list[dict[str, object]], item_names: dict[int, str]) -> list[str]:
    errors: list[str] = []
    seen_indices: set[int] = set()
    for row in rows:
        idx = int(row["index"])
        if idx in seen_indices:
            errors.append(f"{path.name}: duplicate category uiIndex {idx}")
        seen_indices.add(idx)
        ids = list(row["ids"])
        if len(ids) != int(row["count"]):
            errors.append(f"{path.name} {row['name']}: ubChoices={row['count']} but {len(ids)} non-zero choices found")
        missing = sorted({i for i in ids if i not in item_names})
        if missing:
            errors.append(f"{path.name} {row['name']}: unknown item IDs {missing}")
    return errors


def print_gun_comparison(label: str, militia_rows: list[dict[str, object]],
                         enemy_rows: list[dict[str, object]],
                         weapons: dict[int, dict[str, float | str]]) -> None:
    print(f"\n## {label.title()} weapon progression")
    print("| Progress | Militia weighted pool | Army weighted pool | Δ range | Δ accuracy | Δ impact | Δ aim |")
    print("|---|---|---|---:|---:|---:|---:|")
    enemy_by_name = {str(r["name"]): r for r in enemy_rows}
    for m in militia_rows:
        e = enemy_by_name.get(str(m["name"]))
        if not e:
            continue
        mids = list(m["ids"])
        eids = list(e["ids"])
        dr = weighted_average(mids, weapons, "range") - weighted_average(eids, weapons, "range")
        da = weighted_average(mids, weapons, "accuracy") - weighted_average(eids, weapons, "accuracy")
        di = weighted_average(mids, weapons, "impact") - weighted_average(eids, weapons, "impact")
        dm = weighted_average(mids, weapons, "aim") - weighted_average(eids, weapons, "aim")
        print(
            f"| {m['name']} | {fmt_names(mids, weapons)} | {fmt_names(eids, weapons)} | "
            f"{dr:+.1f} | {da:+.1f} | {di:+.1f} | {dm:+.2f} |"
        )


def print_item_comparison(label: str, militia_rows: list[dict[str, object]],
                          enemy_rows: list[dict[str, object]]) -> None:
    print(f"\n## {label.title()} support-pool breadth")
    print("| Category | Militia choices | Army choices | Difference |")
    print("|---|---:|---:|---:|")
    enemy_by_index = {int(r["index"]): r for r in enemy_rows}
    for m in militia_rows:
        e = enemy_by_index.get(int(m["index"]))
        if not e:
            continue
        mc = int(m["count"])
        ec = int(e["count"])
        if mc != ec:
            print(f"| {m['name']} | {mc} | {ec} | {mc - ec:+d} |")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail on malformed or unresolved choice-table data")
    args = parser.parse_args()

    weapons = load_weapons()
    item_names = load_item_names()
    errors: list[str] = []

    print("# Militia vs Army Equipment Audit")
    print("Weighted duplicates are preserved because they are selection probability, not redundant data.")
    print("Weapon deltas are militia minus the opposing army tier; negative values indicate a weaker weighted pool on that metric.")

    for militia_label, enemy_label, mg, eg, mi, ei in TIER_PAIRS:
        mg_path, eg_path = INV / mg, INV / eg
        mi_path, ei_path = INV / mi, INV / ei
        mg_rows, eg_rows = load_gun_choices(mg_path), load_gun_choices(eg_path)
        mi_rows, ei_rows = load_item_choices(mi_path), load_item_choices(ei_path)

        errors.extend(validate_gun_table(mg_path, mg_rows, weapons))
        errors.extend(validate_gun_table(eg_path, eg_rows, weapons))
        errors.extend(validate_item_table(mi_path, mi_rows, item_names))
        errors.extend(validate_item_table(ei_path, ei_rows, item_names))

        print_gun_comparison(f"{militia_label} militia vs {enemy_label} army", mg_rows, eg_rows, weapons)
        print_item_comparison(f"{militia_label} militia vs {enemy_label} army", mi_rows, ei_rows)

    if errors:
        print("\n## Audit errors", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1 if args.check else 0

    print("\nAudit integrity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
