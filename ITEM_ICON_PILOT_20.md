# Vengeance Reloaded — 20-item icon pilot

Branch: `art/item-icons-pilot-20`

This pilot changes **actual in-game item sprites**, not review-board mockups.

## Scope

The 20 pilot weapons are:

1. Glock 17
2. Beretta 92FS
3. Mini-Uzi
4. Uzi
5. IMI Uzi MP2
6. FMK-3
7. Marlin Camp Carbine 9
8. HK MP5KA4
9. Beretta Cx4 Storm
10. Ruger Mini-14
11. Colt M16A1
12. Colt M16A4
13. Colt M4 Commando
14. SKS
15. M24
16. SPAS-15
17. Type 85
18. Steyr AUG HBAR
19. AKM
20. HK G3A3

## In-game asset layers changed

Inventory:
- `Data-AIMv53/Interface/MDGUNS.sti`
- `Data-AIMv53/Interface/MDP4ITEMS.sti`
- `Data-AIMv53/Interface/MDP6ITEMS.STI`

World / ground:
- `Data-AIMv53/tilesets/0/smguns.sti`
- `Data-AIMv53/tilesets/0/SMP4ITEMS.STI`
- `Data-AIMv53/tilesets/0/SMP6ITEMS.STI`

## Art method

For the pilot, the existing higher-detail Vengeance BigItems artwork is used as the source art, resampled into the native inventory/world sprite dimensions and remapped into the destination STI palettes. This preserves the engine's existing sprite dimensions and offsets while pulling more detail from the higher-resolution item art.

A small red **AI** mark is written into the top-right of every pilot sprite that was changed. Inventory icons use a larger 5-pixel-high mark; tiny world sprites use a compact 3-pixel-high mark.

No item IDs, graphic numbers, frame dimensions, offsets, attachment definitions, gameplay values, penetration, weapon stats, or inventory geometry are changed.

## Status

Pilot only. Do not merge to `master` until reviewed in-game.
