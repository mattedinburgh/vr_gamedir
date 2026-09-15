# San Mona C5 — native VHD2 scratch structural pilot

Branch pairing:
- source: `mattedinburgh/vr_source@feature/vhd-renderer`
- gamedir: `mattedinburgh/vr_gamedir@feature/vhd-renderer-test`

## Production rules

C5 is a graphics-first VHD2 pilot. `c5.dat` is not modified by this asset pass.

For structural families (ground, roads, walls, roofs, major building surfaces):
- create visible RGB artwork from scratch at native 2x;
- do not upscale, repaint, sharpen, texture-overlay, or otherwise reuse legacy structural pixels as artwork;
- legacy STI/JSD may be inspected only to preserve the technical contract: frame count, frame geometry/transparent footprint, offsets, region order, appdata, anchors, JSD/structure semantics, collision, destruction and other gameplay identity;
- preserve map positions, rooms, roads/alleys, walls, doors, windows, roofs, pathfinding, LOS, cover and save compatibility.

Small generic props (chairs, bins, crates, barrels, buckets, similar clutter) may remain legacy/reused where appropriate.

## Art direction

San Mona C5 should read as a dry, neglected late-20th-century Latin American vice/commercial strip:
- sun-faded ochre/turquoise/salmon/cream stucco;
- exposed brick under failed render;
- corrugated metal repairs and patched roofs;
- improvised utilities, tanks, wiring, drainage and shutters;
- dusty municipal paving with piecemeal repairs, oil and grime;
- informal commerce and lived-in clutter;
- sparse hardy vegetation in the central strip, not lush rural/tropical farming.

Avoid generic HD cleanliness, Mediterranean postcard styling, and rural crop/scarecrow motifs in central C5.

## Native asset path

At 2x the VHD resolver looks for same-identity replacements below:

`Data-Maps-Tiles/VHD2/TILESETS/18/`

The first structural pilot families are:
1. `Cobble_Road.b1tc`
2. `Cobble_Road_Pieces.b1tc`
3. `Pave_b.b1tc`
4. `BUILD_24.b1tc`
5. `SLANT_12.b1tc`

These are validated in the unchanged C5 map through the self-hosted MapEditor render sandbox before the next family batch is promoted.
