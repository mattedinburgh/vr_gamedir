# Map Visual Overhaul — Methodology Reset 2026-09-15

## Why this reset exists

The previous A3/Map Factory approach accumulated technically useful infrastructure but spent too much effort improving a weak production method before proving that the rendered result was artistically good enough.

The stream must now optimize for **visible authored quality first**, and only then for scale.

The failed pattern was:

1. infer open grids;
2. scatter small debris/vegetation/object kits;
3. apply broad sector grading/material tinting;
4. build extensive safety/serialization/QA machinery around the result;
5. only late in the cycle judge whether the actual map looked professionally redesigned.

That approach is retired as the default map-remaster methodology.

## What remains valuable

Keep and reuse:

- canonical JSD/structure preservation;
- STI/B1TC compatibility and contract validation;
- B1TC read-back/serialization validation;
- automatic six-view tactical screenshots;
- engine-rendered overhead previews;
- deterministic map preview capture;
- protected campaign-data auditing;
- isolated map branch/deployment;
- rollback tooling;
- sector classification/archetypes;
- map manifest/production queue;
- binary safety checks;
- map comparison and regression QA.

These are infrastructure, not the design method.

## Retired as primary methodology

Do not use these as the principal way to redesign a sector:

- semi-random debris-kit placement;
- scatter-first procedural dressing;
- blanket green/warm/cool sector grading;
- global colour treatment presented as a map redesign;
- hard-coded per-sector runtime aliases as the long-term content-authoring model;
- large implementation efforts before a visually convincing prototype exists.

They may still be used as small finishing tools after the actual sector design is good.

## New production principle

The default architecture is:

```
DESIGN INTENT
    |
semantic sector specification
hand-authored composition library
art direction / reference
    |
    v
LAYOUT / GENERATION
    |
zone or graph planning
constraint-based placement
optional local automapping / WFC
    |
    v
ENGINE-NATIVE MAP OPERATIONS
    |
LoadWorld()
modify live world through JA2/Vengeance map primitives
SaveWorld()
    |
    v
VISUAL ART
    |
STI/B1TC remaster
sector/material variants
visual-only overlays where safe
    |
    v
QA
    |
protected-data comparison
connectivity / pathing checks
same-camera tactical screenshots
human visual acceptance
```

The Vengeance engine remains the authoritative reader/writer of map data wherever practical.

## Methodologies available to the stream

### 1. Pure asset replacement

Replace visible STI/B1TC imagery while preserving existing map placement and canonical structural/JSD data.

Best for:
- sectors whose layout is already good;
- roofs, walls, floors, roads, ground, vegetation and furniture;
- low-risk visual modernization.

Limit:
- cannot fix a weak spatial composition by itself.

### 2. Manual Vengeance / 1.13-style Map Editor remaster

Use the actual editor for bespoke sector design.

Best for:
- hero sectors;
- towns;
- important quest areas;
- unique industrial/military locations;
- sectors where visual composition matters more than automation.

Use complete-building and smart-construction concepts rather than individual-object micro-editing where possible.

### 3. Engine-native scripted map compiler

Preferred technical foundation.

Target model:

```
LoadWorld("A3.dat")
ProtectCampaignCriticalData()
ApplySemanticDesignRecipe()
ValidateWorld()
SaveWorld("A3_NEW.dat")
RenderQAViews()
```

Automation should call the same engine/world primitives used by the editor rather than primarily patching DAT bytes externally.

Desired commands/concepts include:

- PLACE_BUILDING(template, anchor, orientation)
- PLACE_COMPOUND(template, anchor)
- PAINT_TERRAIN(region, material)
- PLACE_ROAD(path)
- PLACE_FIELD(region, crop_style)
- PLACE_PROP_CLUSTER(template, anchor)
- APPLY_WEATHERING(region, profile)
- PROTECT_REGION / PROTECT_OBJECT
- VALIDATE_CONNECTIVITY
- VALIDATE_PROTECTED_DATA

### 4. Semantic intermediate representation

Represent the intended map in human-readable data before compiling it to JA2 structures.

Example:

```yaml
sector: A3
identity: rural_tropical_farm

protected:
  quest_buildings: true
  entry_points: true
  exits: true
  npc_placements: true

zones:
  - type: farmstead
  - type: crop_field
  - type: service_road
  - type: scrub

style:
  climate: humid_tropical
  wealth: poor
  maintenance: improvised
  architecture: rural_latin
```

The semantic layer must express **intent**, not merely tile IDs.

### 5. Modern external editor bridge

Prototype a modern editor front end, with Tiled as the first candidate.

Potential architecture:

```
Vengeance map
   |
semantic export
   |
Tiled layers / objects / properties
   |
VR JSON / recipe
   |
Vengeance native importer
   |
SaveWorld()
```

Useful layer concepts:

- GROUND
- ROADS
- STRUCTURES
- ROOFS
- OBJECTS
- PROTECTED
- QUEST
- ENTRY_POINTS
- WATER
- DECOR

Use the external editor for visual authoring and metadata; Vengeance remains authoritative for final serialization and validation.

### 6. Hand-authored prefab / composition library

This becomes a primary design method.

A prefab must be a coherent environmental composition, not a handful of unrelated debris tiles.

Examples:

- poor rural farmhouse;
- farmyard;
- roadside repair shop;
- market frontage;
- military checkpoint;
- checkpoint chicane;
- improvised barracks;
- fuel/service area;
- small industrial yard;
- slum courtyard;
- mine administration cluster;
- drainage/irrigation segment;
- rural crossroads;
- ruined building compound.

A prefab can contain:

- building shell;
- approach/path;
- surrounding terrain;
- fences;
- functional props;
- environmental storytelling;
- vegetation;
- wear/damage state;
- optional variants;
- orientation rules;
- placement constraints.

Goal: build a reusable library of roughly 100-150 high-quality compositions over time rather than thousands of low-level scatter rules.

### 7. Constraint-based placement

The generator should place whole authored compositions according to explicit constraints.

Example farmstead constraints:

- minimum distance from map edge;
- road or path connection;
- no overlap with protected geometry;
- accessible entrance;
- rear-yard connectivity;
- preserve major entry-to-sector routes;
- sensible relationship between house, field, well, shed and road;
- no blocking of campaign-critical grids.

Use deterministic search/constraint solving rather than random placement.

### 8. Graph / zone grammar

For larger redesigns, generate the semantic topology before spatial placement.

Example:

```
main road
   |
farm entrance
   |
farmyard --- farmhouse
   |            |
shed         garden
   |
crop fields
   |
irrigation ditch
```

Useful for:
- villages;
- compounds;
- military bases;
- farms;
- industrial areas;
- mines;
- town blocks.

This defines relationships first and geometry second.

### 9. Wave Function Collapse / automapping

Use only at the local-detail level unless explicitly proven otherwise.

Good uses:
- crop-row variation;
- paving;
- roof-damage patterns;
- wall deterioration;
- vegetation transitions;
- junk-yard fill;
- rubble;
- field-edge irregularity;
- slum micro-detail.

Do not let WFC decide:
- quest topology;
- primary roads;
- major building locations;
- strategic exits;
- campaign-critical structures.

### 10. Runtime visual overlays

Use deterministic display-only overlays for details that do not need map nodes.

Possible uses:
- grime;
- wall staining;
- cracks;
- tyre marks;
- dust;
- roof patching;
- water damage;
- small decorative vegetation;
- puddle/wetness appearance.

Seed by sector/grid/underlying tile so results are deterministic.

This is a finishing layer, not the level-design system.

### 11. Bespoke/full sector reconstruction

Use selectively for important sectors.

Allowed only as an explicit sector-level decision.

When used:
- preserve/transplant protected quest and campaign data;
- validate NPCs, exits, schedules, items and door data;
- validate tactical connectivity and pathing;
- run human visual QA before integration.

## Sector-class methodology

There is no universal generator.

| Sector class | Default method |
| --- | --- |
| Forest / wilderness | semantic zones + local automapping/WFC + new assets |
| Farm / countryside | authored farm modules + constraint placement |
| Generic roadside | road-aware modules + procedural finishing |
| Town outskirts | prefab buildings + graph/zone rules |
| Dense town | manually authored blocks + automated details |
| Military | handcrafted tactical compounds + constraint placement |
| Industrial | authored industrial modules + constraint placement |
| Important quest sector | manual/hybrid bespoke remake |
| Underground | mostly manual + controlled detail pass |
| Existing strong layout | asset replacement + overlays only |

## Prototype kill gate

No methodology receives major engineering effort until it passes a visible prototype.

Minimum prototype:

- one representative sector;
- one representative 25-30% tactical screen area or equivalent multi-view sample;
- real in-engine render;
- enough implementation to demonstrate the actual visual method.

Acceptance questions:

1. Is it clearly better than the original?
2. Is the composition coherent?
3. Does it match the agreed art direction?
4. Does it avoid a stamped/procedural look?
5. Does it still read as Jagged Alliance / Vengeance?
6. Does it work in the real game pipeline?
7. Are the gameplay invariants intact?

If the answer is no, kill or change the method before building more tooling around it.

## QA hierarchy

QA must be split into three levels.

### A. Gameplay/data safety — mandatory
- protected campaign data unchanged unless explicitly approved;
- exits/entry points valid;
- pathing/connectivity valid;
- structural/JSD contracts valid;
- map loads/saves through the real engine;
- no strategic/campaign-layer changes.

### B. Visual regression — useful but insufficient
- brightness/darkness;
- saturation;
- colour cast;
- missing sprites;
- broken alpha;
- obvious clipping;
- corrupt frames.

These metrics cannot determine whether the map is good.

### C. Human art-direction gate — mandatory
Same-camera comparison:
- original;
- candidate;
- close tactical views;
- sector overview.

A candidate does not progress merely because automated QA passes.

## Art methodology

Avoid global remaster filters.

Work by material/family:

- corrugated metal;
- plaster;
- masonry;
- dirt;
- road/asphalt;
- wood;
- concrete;
- vegetation;
- fencing;
- furniture;
- industrial machinery;
- decals/weathering.

Each family can have authored variants such as:
- new;
- faded;
- patched;
- rusted;
- soot-damaged;
- wet;
- neglected.

Structural replacements retain compatible geometry unless a gameplay/layout change has been explicitly approved.

## Immediate stream direction

1. Freeze the scatter/grade-first A3 method as a production approach.
2. Keep the current map safety, preview, B1TC/JSD and rollback infrastructure.
3. Prototype an engine-native scripted map operation path using existing LoadWorld/live-world/SaveWorld capabilities.
4. Prototype a semantic map representation.
5. Build the first coherent prefab/composition library.
6. Prototype an external-editor bridge, initially Tiled -> semantic representation -> Vengeance.
7. Use A3 as a methodology test sector only after the new pipeline can produce one convincing in-engine visual sample.
8. Do not scale to production waves until the prototype kill gate passes.
9. Keep strategic/campaign systems completely out of scope unless explicitly requested.

## Definition of success

The stream is successful when it can produce sectors that look **authored, coherent and materially improved**, while retaining Vengeance gameplay/campaign compatibility, and can then scale that quality through reusable semantic tools and compositions.

Automation is subordinate to quality. A technically elegant generator that produces mediocre maps fails this stream.
