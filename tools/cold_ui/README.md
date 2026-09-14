# Cold UI Pilot — Vengeance

This directory prepares the cold steel-blue UI direction without making it live.

## Safety

- The active `vfs_config.Vengeance.ini` is **not changed**.
- Existing `Data-UI` and `Data-Vengeance` assets are **not modified**.
- Generated files go to a separate overlay such as `build/Data-UI-ColdPilot`.
- The workflow is manual-only (`workflow_dispatch`) and uploads an artifact; it does not deploy, copy into a game install, or commit generated binaries.
- Item/weapon icons are intentionally outside this UI-first pilot.

## Research-informed methodology

The pilot now follows a hybrid approach chosen after reviewing current 1.13 documentation/source, historical 1.13 interface packs, JA2-Stracciatella scaling/layout work, and community reports about high-resolution UI size.

1. **Theme through a VFS override layer first.** This is the established 1.13 modding pattern and keeps rollback trivial.
2. **Preserve layout geometry.** Replacing art is low-risk; scaling every control, font and mouse region is a separate engine project.
3. **Use semantic-aware theming, not a blind global tint.** Assets are classified as `chrome`, `mixed`, or `semantic`. Warning/status/state colours receive much less transformation than panel material.
4. **Keep display scaling separate from art resolution.** Higher-resolution source art does not create extra on-screen detail unless the engine also draws it larger. Renderer/output scaling is therefore treated as a later readability option, not mixed into this visual pass.
5. **Only consider dynamic/responsive UI after the skin is stable.** JA2-Stracciatella demonstrates that a dynamic tactical bottom bar is feasible, but that is a coordinate/layout subsystem change rather than an art replacement.

## Why palette-first

Most JA2 UI STI files are indexed STCI images. In v4 the palette transform is asset-policy-aware rather than uniformly aggressive. Their 256-colour palette sits separately from ETRLE-compressed image/subimage data. The preparation tool changes palette RGB entries only, preserving:

- sprite/subimage dimensions,
- X/Y offsets,
- ETRLE pixel runs,
- transparency structure,
- app data,
- file/item positioning.

This is the safest way to make the existing Vengeance UI colder without changing geometry.

## Stages

**Stage 1**: the active `Data-UI` / Kaerar replacement layer: inventory, tactical bottom panels, map panels, sector inventory, laptop shell and Bobby Ray grids.

**Stage 2**: Vengeance-only panels not already supplied by `Data-UI`: map background, options, prebattle, laptop desktop and category backgrounds.

## Local audit

Audit only; writes no themed assets:

```powershell
python tools/cold_ui/prepare_cold_ui.py --stage 1
```

Prepare the separate overlay:

```powershell
python -m pip install pillow
python tools/cold_ui/prepare_cold_ui.py --stage 1 --write --previews
```

Incremental generation is the default. Only changed/new source assets are regenerated.

For a clean recovery rebuild:

```powershell
python tools/cold_ui/prepare_cold_ui.py --stage 1 --write --force
```

## Going live later

Do **not** mount the generated overlay yet. After visual review, the intended activation is a separate VFS profile mounted after the existing `ui` profile. That activation change is deliberately not part of this branch preparation step.


## Real asset review previews

The pilot can now decode the actual indexed ETRLE STI frames and produce side-by-side **current vs cold-pilot** PNG sheets:

```powershell
python tools/cold_ui/prepare_cold_ui.py --stage 1 --previews
```

This does not activate or deploy anything. Preview files are written under `build/cold-ui-preview`.

For every indexed STI recolour, the report records hashes of all bytes outside the palette and requires them to remain identical. This explicitly verifies that frame geometry, offsets, compressed pixel runs, transparency and app data were not changed by the palette pass.


## Stage 3: base-SLF bridge (prepared, not run)

The source audit found UI chrome that Vengeance loads from the original JA2 SLF archives rather than from loose files in `vr_gamedir`. A read-only extractor is prepared for those files:

```powershell
python tools/cold_ui/extract_slf_ui.py --game-root "C:\path\to\Jagged Alliance 2"
python tools/cold_ui/prepare_cold_ui.py --stage 3 --write --previews
```

The extractor reads `Data/Interface.slf` and `Data/Laptop.slf` and copies only the allow-listed UI files into `build/cold-ui-base-extract`. It does not modify the SLF archives, the installed game, or VFS configuration.

Stage 3 is deliberately separate from the GitHub-only Stage 1/2 work so the project remains reproducible and the bridge is used only where GitHub has no loose source asset.
