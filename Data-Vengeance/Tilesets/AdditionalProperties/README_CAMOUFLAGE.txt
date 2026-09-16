Vengeance Reloaded camouflage-only tile metadata.

Derived from the modern JA2 1.13 AdditionalProperties dataset, restricted to tile basenames present in the Vengeance/Vengeance-map/1.13 runtime stack and to five combat-visibility fields only:
- bWoodCamoAffinity
- bDesertCamoAffinity
- bUrbanCamoAffinity
- bSnowCamoAffinity
- bCamoStanceModifer

Unrelated sound, stealth-difficulty, trap, window and terrain-ID properties are intentionally excluded.
Tiles without non-zero detailed camouflage metadata retain the legacy Vengeance terrain fallback.
Source reference: 1dot13/source master, gamedir/Base/tilesets/AdditionalProperties
Port date: 2026-09-15
