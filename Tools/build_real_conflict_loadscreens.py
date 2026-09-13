#!/usr/bin/env python3
"""Build redistribution-safe documentary loading screens for Vengeance Reloaded.

Sources are Wikimedia Commons files whose metadata explicitly marks them as
Public Domain or CC0. The script keeps the historical photograph intact apart
from crop/resize and restrained tonal grading needed for a consistent 16:9 UI.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import random
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageEnhance, ImageOps

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "VengeanceReloaded-LoadscreenBuilder/1.0"

POOL_CODES = {
    "TOWN_MILITARY": "TM",
    "JUNGLE_MILITARY": "JM",
    "RURAL_MILITARY": "RM",
    "AIRFIELD": "AF",
    "ARMOR": "AR",
    "COAST_TOWN": "CT",
    "INFRASTRUCTURE": "IN",
    "RUINS_MILITARY": "RU",
    "JUNGLE": "JG",
}

AIR_TERMS = ("helicopter", "airport", "airfield", "airborne", "parachut", "chinook", "black hawk", "aircraft")
ARMOR_TERMS = ("lav-", "lav ", "tank", "armored", "armoured", "sheridan", "apc")
INFRA_TERMS = ("dam", "bridge", "power", "oil", "pipeline", "refinery")
RUIN_TERMS = ("destroyed", "damage", "damaged", "ruin", "attack", "burned", "burnt", "wreck")
TOWN_TERMS = ("town", "city", "street", "restaurant", "building", "barracks", "guard", "patrol")
JUNGLE_TERMS = ("jungle", "forest", "river", "rural", "road", "village", "mountain")


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def retry_delay(response: requests.Response, attempt: int) -> float:
    """Respect Wikimedia throttling while keeping the build bounded."""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(45.0, max(1.0, float(retry_after)))
        except ValueError:
            pass
    return min(30.0, float(2 ** attempt))


def api_get(session: requests.Session, params: dict) -> dict:
    params = dict(params)
    params["format"] = "json"
    params["maxlag"] = "5"
    for attempt in range(6):
        r = session.get(COMMONS_API, params=params, timeout=60)
        if r.ok:
            data = r.json()
            if "error" not in data:
                return data
            if data.get("error", {}).get("code") not in ("maxlag", "ratelimited"):
                raise RuntimeError(data["error"])
        if attempt == 5:
            r.raise_for_status()
        time.sleep(retry_delay(r, attempt))
    raise RuntimeError("unreachable")


def category_files(session: requests.Session, category: str) -> list[str]:
    title = category if category.startswith("Category:") else f"Category:{category}"
    out: list[str] = []
    cont = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": title,
            "cmnamespace": 6,
            "cmlimit": "500",
        }
        if cont:
            params["cmcontinue"] = cont
        data = api_get(session, params)
        out.extend(x["title"][5:] for x in data.get("query", {}).get("categorymembers", []))
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
    return out


def image_info(session: requests.Session, filename: str) -> dict | None:
    data = api_get(
        session,
        {
            "action": "query",
            "prop": "imageinfo",
            "titles": "File:" + filename,
            "iiprop": "url|size|mime|extmetadata",
        },
    )
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None
    page = next(iter(pages.values()))
    info = (page.get("imageinfo") or [None])[0]
    if not info:
        return None
    info["page_title"] = page.get("title", "File:" + filename)
    return info


def image_info_batch(session: requests.Session, filenames: list[str]) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for start in range(0, len(filenames), 10):
        batch = filenames[start:start + 10]
        data = api_get(
            session,
            {
                "action": "query",
                "prop": "imageinfo",
                "titles": "|".join("File:" + name for name in batch),
                "iiprop": "url|size|mime|extmetadata",
                "iiurlwidth": "1920",
            },
        )
        for page in data.get("query", {}).get("pages", {}).values():
            title = page.get("title", "")
            info = (page.get("imageinfo") or [None])[0]
            if title.startswith("File:") and info:
                results[title[5:]] = info
        time.sleep(0.5)
    return results


def meta_value(info: dict, key: str) -> str:
    return clean_html(info.get("extmetadata", {}).get(key, {}).get("value", ""))


def is_redistribution_safe(info: dict) -> bool:
    lic = (meta_value(info, "LicenseShortName") + " " + meta_value(info, "UsageTerms")).lower()
    return "public domain" in lic or "cc0" in lic or "creative commons zero" in lic


def excluded_title(filename: str, terms: list[str]) -> bool:
    name = filename.lower().replace("_", " ")
    return any(term.lower() in name for term in terms)


def choose_pool(default_pool: str, filename: str) -> str:
    name = filename.lower().replace("_", " ")
    if any(t in name for t in AIR_TERMS):
        return "AF"
    if any(t in name for t in ARMOR_TERMS):
        return "AR"
    if any(t in name for t in INFRA_TERMS):
        return "IN"
    if any(t in name for t in RUIN_TERMS):
        return "RU"
    if any(t in name for t in TOWN_TERMS):
        return "TM"
    if any(t in name for t in JUNGLE_TERMS):
        return "JM"
    return POOL_CODES.get(default_pool, default_pool[:2].upper())


def download_image(session: requests.Session, urls: list[str]) -> bytes:
    """Download from thumbnail/redirect/original mirrors, with throttling."""
    last_error: Exception | None = None
    for url in dict.fromkeys(u for u in urls if u):
        for attempt in range(5):
            try:
                r = session.get(url, timeout=120, allow_redirects=True)
                if r.ok and r.content:
                    return r.content
                if attempt == 4:
                    r.raise_for_status()
                time.sleep(retry_delay(r, attempt))
            except Exception as exc:
                last_error = exc
                if attempt < 4:
                    time.sleep(min(20.0, float(2 ** attempt)))
    if last_error:
        raise last_error
    raise RuntimeError("No usable image URL")


def prepare_image(data: bytes, width: int, height: int) -> Image.Image:
    with Image.open(io.BytesIO(data)) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")

    img = ImageOps.fit(
        img,
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    img = ImageEnhance.Color(img).enhance(0.92)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    img = ImageEnhance.Sharpness(img).enhance(1.03)
    return img.quantize(
        colors=256,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.FLOYDSTEINBERG,
    )


def source_page(filename: str) -> str:
    safe = quote(filename.replace(" ", "_"), safe="()_-.,")
    return "https://commons.wikimedia.org/wiki/File:" + safe


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="Tools/real_conflict_loadscreens.json")
    ap.add_argument("--root", default="Data-Vengeance/Loadscreens/RealConflict")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    root = Path(args.root)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    width = int(cfg.get("target_width", 1920))
    height = int(cfg.get("target_height", 1080))
    min_width = int(cfg.get("min_width", 1200))
    min_height = int(cfg.get("min_height", 700))
    max_total = int(cfg.get("max_total", 160))
    max_per_category = int(cfg.get("max_per_category", 300))
    max_candidates = int(cfg.get("max_candidates", max_total * 8))
    exclude_terms = cfg.get("exclude_title_terms", [])

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    candidates: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    for seed in cfg.get("seed_files", []):
        fn = seed["file"]
        key = fn.casefold()
        if key not in seen:
            seen.add(key)
            candidates.append((fn, seed.get("primary_pool", "RURAL_MILITARY"), seed.get("note", "seed")))

    for cat in cfg.get("categories", []):
        try:
            names = sorted(category_files(session, cat["name"]))
        except Exception as exc:
            print(f"WARN category {cat['name']}: {exc}", file=sys.stderr)
            continue

        accepted = 0
        for fn in names:
            if accepted >= max_per_category or len(candidates) >= max_candidates:
                break
            key = fn.casefold()
            if key in seen or excluded_title(fn, exclude_terms):
                continue
            seen.add(key)
            candidates.append((fn, cat.get("primary_pool", "RURAL_MILITARY"), "Category:" + cat["name"]))
            accepted += 1

    # Preserve curated seeds first, then deterministically mix category results so
    # one very large category cannot monopolize the finished pack.
    seed_count = len(cfg.get("seed_files", []))
    tail = candidates[seed_count:]
    random.Random(0x4A4132).shuffle(tail)
    candidates = candidates[:seed_count] + tail

    pool_counts: dict[str, int] = defaultdict(int)
    records: list[dict[str, str]] = []
    accepted_total = 0

    # Resolve metadata in small batches. Wikimedia explicitly recommends
    # thumbnail delivery instead of repeated full-original downloads.
    infos = image_info_batch(session, [filename for filename, _, _ in candidates])

    for filename, default_pool, origin in candidates:
        if accepted_total >= max_total:
            break

        try:
            info = infos.get(filename)
            if not info or not is_redistribution_safe(info):
                continue
            if info.get("mime") not in ("image/jpeg", "image/png"):
                continue
            if int(info.get("width", 0)) < min_width or int(info.get("height", 0)) < min_height:
                continue

            aspect = float(info["width"]) / float(info["height"])
            if aspect < 1.15 or aspect > 2.25:
                continue

            pool = choose_pool(default_pool, filename)
            next_seq = pool_counts[pool] + 1

            # Prefer Wikimedia's generated thumbnail, then Special:Redirect,
            # finally the original. The redirect path is substantially more
            # reliable for older DoD scans whose thumbnail URL intermittently
            # returns 429/5xx from upload.wikimedia.org.
            redirect_name = quote(filename.replace(" ", "_"), safe="()_-.,")
            redirect_url = (
                "https://commons.wikimedia.org/wiki/Special:Redirect/file/"
                + redirect_name
                + f"?width={width}"
            )
            raw = download_image(
                session,
                [info.get("thumburl", ""), redirect_url, info.get("url", "")],
            )
            time.sleep(0.55)
            img = prepare_image(raw, width, height)

            dest_dir = root / pool
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{pool}_{next_seq:03d}_{width}x{height}.png"
            img.save(dest, format="PNG", optimize=True, compress_level=9)
            pool_counts[pool] = next_seq

            records.append({
                "pool": pool,
                "game_file": str(dest).replace("\\", "/"),
                "source_file": filename,
                "source_page": source_page(filename),
                "original_url": info["url"],
                "license": meta_value(info, "LicenseShortName"),
                "license_url": meta_value(info, "LicenseUrl"),
                "author": meta_value(info, "Artist"),
                "date": meta_value(info, "DateTimeOriginal") or meta_value(info, "DateTime"),
                "description": meta_value(info, "ImageDescription"),
                "origin": origin,
                "original_size": f"{info.get('width')}x{info.get('height')}",
            })
            accepted_total += 1
            print(f"[{accepted_total:03d}/{max_total}] {pool}: {filename}")
        except Exception as exc:
            print(f"WARN file {filename}: {exc}", file=sys.stderr)

    if not records:
        raise SystemExit("No redistribution-safe images were produced.")

    minimum_total = int(cfg.get("minimum_total", 80))
    if len(records) < minimum_total:
        raise SystemExit(
            f"Only {len(records)} redistribution-safe images were produced; "
            f"minimum required is {minimum_total}. Refusing to publish a partial pack."
        )

    with (root / "SOURCES.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    readme = [
        "# Vengeance Reloaded - Real Conflict Loading Screens",
        "",
        "These loading screens are derived from real archival photographs.",
        "Only Wikimedia Commons files whose metadata explicitly reports Public Domain or CC0 are included.",
        "The builder refuses to publish a partial pack below the configured minimum image count.",
        "Edits are limited to crop, resize, restrained tonal grading, and palette quantization.",
        "",
        f"Generated screens: **{len(records)}**",
        "",
        "## Pools",
        "",
    ]
    for pool, count in sorted(pool_counts.items()):
        readme.append(f"- **{pool}**: {count}")
    readme += [
        "",
        "Full source, author and licensing metadata is in SOURCES.csv.",
        "",
        "Pool codes: TM town/military; JM jungle/military; RM rural/military; AF airfield/airborne; "
        "AR armor; CT coast/town; IN infrastructure; RU ruins/military; JG jungle.",
        "",
    ]
    (root / "README.md").write_text("\n".join(readme), encoding="utf-8")

    print(f"Produced {len(records)} loading screens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
