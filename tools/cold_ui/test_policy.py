#!/usr/bin/env python3
"""Sanity checks for the research-informed cold UI colour policy."""

import json
import math
from pathlib import Path

from prepare_cold_ui import cold_rgb


def delta(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def main():
    strength = 0.72

    warning_red = (220, 35, 35)
    status_green = (40, 190, 70)
    warning_yellow = (245, 215, 35)
    warm_chrome = (201, 172, 133)
    neutral_chrome = (135, 125, 110)

    # Semantic colours may move slightly with the palette, but must remain far
    # more stable than decorative warm/neutral panel material.
    red_shift = delta(warning_red, cold_rgb(warning_red, strength, "chrome"))
    green_shift = delta(status_green, cold_rgb(status_green, strength, "chrome"))
    yellow_shift = delta(warning_yellow, cold_rgb(warning_yellow, strength, "chrome"))
    warm_shift = delta(warm_chrome, cold_rgb(warm_chrome, strength, "chrome"))
    neutral_shift = delta(neutral_chrome, cold_rgb(neutral_chrome, strength, "chrome"))

    assert warm_shift > red_shift * 3.0, (warm_shift, red_shift)
    assert warm_shift > green_shift * 3.0, (warm_shift, green_shift)
    assert neutral_shift > yellow_shift * 2.0, (neutral_shift, yellow_shift)

    chrome = cold_rgb(warm_chrome, strength, "chrome")
    mixed = cold_rgb(warm_chrome, strength, "mixed")
    semantic = cold_rgb(warm_chrome, strength, "semantic")
    preserved = cold_rgb(warm_chrome, strength, "preserve")

    assert delta(warm_chrome, chrome) > delta(warm_chrome, mixed)
    assert delta(warm_chrome, mixed) > delta(warm_chrome, semantic)
    assert preserved == warm_chrome

    manifest_path = Path(__file__).with_name("manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    allowed = {"chrome", "mixed", "semantic", "preserve"}
    for entry in manifest["assets"]:
        policy = entry.get("policy", "chrome")
        assert policy in allowed, (entry.get("source"), policy)

    print("cold UI policy checks passed")


if __name__ == "__main__":
    main()
