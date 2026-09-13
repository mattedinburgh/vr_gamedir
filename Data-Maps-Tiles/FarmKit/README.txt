REUSABLE TRUE-COLOUR FARM CROP LIBRARY
=======================================
Format: B1TC v1 RGBA
Tile anchor: JA2 40x20 ground tile; taller sprites use negative Y offsets.
Purpose: reusable crop art for future rural/farm sectors. Not tied to A3 coordinates.

CROPS_LOW_ROWS.b1tc            24 frames 40x24 y=-4  seedlings / short grain / sparse rows
CROPS_MEDIUM_ROWS.b1tc         24 frames 40x36 y=-16 mature medium-height crops
CROPS_THICK_TALL.b1tc          24 frames 40x48 y=-28 dense tall crop wall / strongest visual mass
CROPS_TROPICAL_BROADLEAF.b1tc  20 frames 40x44 y=-24 lush broad-leaf tropical crops
CROPS_DRY_DEAD.b1tc            18 frames 40x40 y=-20 dry/dead harvest-season crops
CROPS_TRAMPLED.b1tc            18 frames 40x26 y=-6  flattened/broken/trampled crop patches
CROPS_ROW_TRANSITIONS.b1tc     24 frames 40x48 y=-28 row edges, gaps, partial-density transitions

All are transparent RGBA multi-frame sprites. No JSD is bundled, so they are visual-only by default.
Future sectors can optionally attach JSD or explicit concealment/LOS rules where thick crops should have gameplay effect.
Keep this directory as the master library; sector profiles should map/copy only the families they need into a tileset slot.
