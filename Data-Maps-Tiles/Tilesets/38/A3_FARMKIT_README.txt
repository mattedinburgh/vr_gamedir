A3 TRUE-COLOUR REUSABLE FARM KIT
=================================
Sector: A3 Oronegro tropical farm (tileset 38)
Format: B1TC v1 RGBA, visual-only overlay sprites

Families / frames:
A3_CROP_ROWS.b1tc     24  cultivated row/stubble strips
A3_EDGE_WEEDS.b1tc    24  field-edge weeds, reeds, scrub
A3_MUD_RUTS.b1tc      20  ruts, mud and shallow puddles
A3_FIELD_STONES.b1tc  20  stones, ditch/drainage accents
A3_WOOD_YARD.b1tc     20  pallets, broken fence, planks, crates, troughs
A3_FARM_JUNK.b1tc     24  sacks, tyres, buckets, barrels, tools, wheelbarrows, scrap
A3_IRRIGATION.b1tc    20  wet channels, banks, simple board crossings
A3_LANDMARKS.b1tc     16  scarecrow, hay, tank, sign, crate stack, lean-to, trough

The source-side A3 farm composer places these as reusable multi-tile visual
blocks. No JSD is attached: they deliberately do not alter collision, cover,
LOS, pathfinding, room IDs, quest grids or authored A3 geometry.


Reusable crop master library
----------------------------
A larger sector-agnostic crop set now lives in:
Data-Maps-Tiles/FarmKit/

It includes low, medium, thick/tall, tropical broadleaf, dry/dead, trampled and row-transition crop families.
Use those master B1TC files for future rural sectors instead of creating A3-specific copies unless a tileset profile needs one.
