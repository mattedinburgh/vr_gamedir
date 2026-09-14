# Cold UI Pilot — Vengeance

This directory prepares the cold steel-blue UI direction without making it live.

## Safety

- The active `vfs_config.Vengeance.ini` is **not changed**.
- Existing `Data-UI` and `Data-Vengeance` assets are **not modified**.
- Generated files go to a separate overlay such as `build/Data-UI-ColdPilot`.
- GitHub CI validates the repository-backed Stage 1/2 assets automatically. Stage 3 is validated locally because it reads the user's own original JA2 SLF archives; those proprietary assets are never committed.
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

**Stage 2**: Vengeance-only panels not already supplied by `Data-UI`. Lore/content artwork (map, cinematic options background, laptop desktop art) is preserved byte-for-byte; surrounding interface chrome is themed.

**Stage 3**: inherited base-JA2 interface/laptop chrome extracted read-only from the user's own `Interface.slf` and `Laptop.slf`. The strict bridge refuses ambiguous filename matches, reports hashes, and fails on missing allow-listed assets.

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


## Stage 3: strict base-SLF bridge

The source audit found UI chrome that Vengeance loads from the original JA2 SLF archives rather than from loose files in `vr_gamedir`. The bridge reads only the allow-listed files from the user's own installation:

```powershell
python tools/cold_ui/extract_slf_ui.py --game-root "C:\path\to\Jagged Alliance 2"
python tools/cold_ui/prepare_cold_ui.py --stage 3 --write --previews
```

The v2 extractor:

- validates SLF directory/data bounds before reading;
- matches exact archive paths first;
- permits basename fallback only when it is unique;
- fails on ambiguous matches;
- fails on missing required assets unless explicitly run with `--allow-missing`;
- records SHA-256 hashes for archives and extracted files;
- verifies every staged write.

It never changes the SLF archives.

## One-command Windows pipeline

The repository root now contains `COLD_UI.ps1`.

Build the complete Stage 3 overlay without touching the live VFS:

```powershell
.\COLD_UI.ps1 -Mode Build -GameRoot "C:\VENGENCE\Jagged Alliance 2"
```

Incrementally copy only new/changed cold UI assets into `Data-UI-Cold`, but leave them inactive:

```powershell
.\COLD_UI.ps1 -Mode Deploy -GameRoot "C:\VENGENCE\Jagged Alliance 2"
```

Build, incrementally deploy and activate the dedicated VFS layer after the existing `ui` profile:

```powershell
.\COLD_UI.ps1 -Mode Activate -GameRoot "C:\VENGENCE\Jagged Alliance 2"
```

Disable the VFS layer while preserving deployed files:

```powershell
.\COLD_UI.ps1 -Mode Rollback -GameRoot "C:\VENGENCE\Jagged Alliance 2"
```

Disable it and delete the dedicated overlay directory:

```powershell
.\COLD_UI.ps1 -Mode Rollback -RemoveOverlay -GameRoot "C:\VENGENCE\Jagged Alliance 2"
```

Deployment is incremental by default and keeps a state file so stale files previously deployed by this pipeline can be removed safely. `-Force` is available for clean recovery/revalidation.

The activation edit is deliberately narrow: it adds/removes only the `coldui` profile and `datacoldui_dir` location. A pre-activation VFS backup is also kept for emergency recovery.
