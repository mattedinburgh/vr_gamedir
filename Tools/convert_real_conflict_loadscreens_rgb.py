#!/usr/bin/env python3
"""Normalize existing Vengeance documentary loadscreens to true-colour RGB PNG.

This is intentionally offline: it converts the already curated/licensed pack in place
without contacting Wikimedia or changing the selected photographs.
"""

from pathlib import Path
from PIL import Image

ROOT = Path("Data-Vengeance/Loadscreens/RealConflict")
MIN_IMAGES = 100


def main() -> int:
    files = sorted(ROOT.glob("*/*_1920x1080.png"))
    if len(files) < MIN_IMAGES:
        raise SystemExit(
            f"Refusing normalization: found only {len(files)} loadscreen PNGs; "
            f"expected at least {MIN_IMAGES}."
        )

    converted = 0
    for path in files:
        with Image.open(path) as src:
            src.load()
            if src.mode == "RGB":
                img = src.copy()
            else:
                img = src.convert("RGB")

        img.save(path, format="PNG", optimize=True, compress_level=9)

        with Image.open(path) as verify:
            if verify.mode != "RGB":
                raise RuntimeError(
                    f"{path} remained mode {verify.mode}; expected RGB"
                )
            if verify.size != (1920, 1080):
                raise RuntimeError(
                    f"{path} has size {verify.size}; expected 1920x1080"
                )

        converted += 1
        print(f"[{converted:03d}/{len(files)}] RGB {path}")

    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        text = text.replace(
            "Edits are limited to crop, resize, restrained tonal grading, and palette quantization.",
            "Edits are limited to crop, resize, and restrained tonal grading."
        )
        if "true-colour RGB PNG" not in text:
            text += (
                "\n## Engine format\n\n"
                "All generated loading screens are stored as **true-colour RGB PNG**. "
                "Indexed/paletted PNG is deliberately avoided because the Vengeance "
                "PNG loader routes it through the sprite/ETRLE path.\n"
            )
        readme.write_text(text, encoding="utf-8")

    print(f"Normalized and verified {converted} loading screens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
