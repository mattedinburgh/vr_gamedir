# Cold UI Pilot — Vengeance

This directory prepares the cold steel-blue UI direction without making it live.

## Safety

- The active `vfs_config.Vengeance.ini` is **not changed**.
- Existing `Data-UI` and `Data-Vengeance` assets are **not modified**.
- Generated files go to a separate overlay such as `build/Data-UI-ColdPilot`.
- The workflow is manual-only (`workflow_dispatch`) and uploads an artifact; it does not deploy, copy into a game install, or commit generated binaries.
- Item/weapon icons are intentionally outside this UI-first pilot.

## Why palette-first

Most JA2 UI STI files are indexed STCI images. Their 256-colour palette sits separately from ETRLE-compressed image/subimage data. The preparation tool changes palette RGB entries only, preserving:

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
