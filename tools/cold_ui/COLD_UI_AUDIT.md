# Cold UI GitHub Audit

## Current Vengeance stack

`vfs_config.Vengeance.ini` mounts profiles in this order:

`SlfLibs, Vanilla, v113, vengcore, pcm, ui, weapsounds, VoiceTaunts, music, UserProf`

The `ui` profile points to `Data-UI`. Its readme identifies it as the Kaerar replacement UI. This gives us an existing override layer that is safer to theme than altering base Vengeance assets directly.

## Active loose UI assets found

The current `Data-UI` layer contains 28 theme-relevant loose assets:

- 21 under `Data-UI/INTERFACE`
- 7 under `Data-UI/LAPTOP`

Major panels include tactical bottom bars, inventory bottom panel, sector inventory, map inventory/border/bottom, overhead interface, laptop shell, and Bobby Ray grids.

Vengeance also supplies additional loose assets in `Data-Vengeance/Interface` and `Data-Vengeance/Laptop`, including options, prebattle, map backgrounds and Bobby Ray backgrounds. Those are Stage 2.

## Engine/source confirmation

Vengeance source explicitly loads the loose interface assets from `INTERFACE\\...` and laptop assets from `LAPTOP\\...`. Examples include:

- `inventory_bottom_panel_1024x768.STI`
- `bottom_bar_1024x768.sti`
- `map_screen_bottom_1024x768.sti`
- `gunbackground.sti`
- `gunsgrid.sti`
- `laptop3.png`

The current 1.13 source uses the same broad UI loading/layout model in the areas checked, including Bobby Ray. This means we can preserve the proven layout and change the presentation layer rather than redesigning the interface logic.

## STCI safety finding

The Vengeance STCI loader defines a 64-byte STCI header and, for indexed images, a separate RGB palette followed by subimage metadata and image data. Representative current files checked from GitHub are indexed + ETRLE-compressed. The pilot tool therefore changes only palette bytes for indexed STI assets.

This is intentionally conservative: no resizing, no frame reordering, no changed offsets.

## Source-side colours

Some UI colours are hard-coded in source and will need a second pass after the asset pilot is visually approved. Examples found include:

- warm inventory/item status-bar RGB constants in `Tactical/Interface Items.cpp`
- tactical/map font colour indices
- Bobby Ray text colour constants
- extended-panel colour settings in `Data-Vengeance/Extended_Panels.INI`

Those are not changed yet because the correct final values should be chosen against the actual cold assets, not in isolation.

## Known gap requiring a bridge later

Several interface assets referenced by source are not loose files in `vr_gamedir` or the current GitHub mirror, for example base button/arrow/bar assets such as `map_border_buttons.sti`, `map_screen_bottom_arrows.sti`, `inventory_buttons.sti`, `Bars.sti`, and some laptop button sheets.

They are inherited from the base SLF/VFS data. For a truly complete cold theme, those must later be extracted from the user's installed base data through a bridge/extraction step, then added as explicit cold overrides. That is intentionally deferred until after the GitHub-first pilot.
