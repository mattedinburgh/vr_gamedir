# Map Visual Overhaul Workstream — 2026

Status: ACTIVE — METHODOLOGY RESET 2026-09-15

## Non-negotiable gameplay rule
The default programme is graphics-only. Preserve map architecture, tile placement and gameplay identity including collision, penetration, destruction, LOS/pathing and save/map compatibility unless a separate gameplay change is explicitly approved.

Strategic/campaign systems are out of scope unless explicitly requested.

## Art rule
- Ground, walls, roofs and other major structural surfaces are redesigned visually rather than reusing the old visible pixels.
- Generic reusable props such as chairs, bins, crates and barrels may be reused when appropriate.
- Every sector should receive a plausible Latin / South American visual identity derived from its role and lore.
- Avoid generic clean-HD treatment; retain age, wear, improvised repairs, local materials and lived-in detail.
- Validate assets in the real map/in-game pipeline.
- Graphics deployment is incremental.
- Visual quality is the gating objective; automation and technical elegance are subordinate to a convincing in-engine result.

## Methodology reset
The previous scatter/debris-kit + broad colour-grading approach is retired as the default production method. It may remain only as a small finishing technique.

The stream now defaults to:
1. semantic design intent;
2. coherent hand-authored prefabs/compositions;
3. graph/zone planning where appropriate;
4. deterministic constraint-based placement;
5. engine-native map operations using Vengeance/JA2 world primitives;
6. material-family STI/B1TC remastering;
7. local automapping/WFC only for suitable micro-detail;
8. automated gameplay/data validation plus mandatory human visual approval.

No single procedural algorithm is expected to fit forests, farms, towns, military compounds, industrial sectors and quest locations.

## Prototype kill gate
Before major engineering effort or production scaling, a methodology must demonstrate a clearly improved real in-engine prototype on a representative sector/view.

If the rendered result is not clearly better, coherent, on-art-direction, non-stamped and gameplay-safe, change or kill the method before adding more infrastructure.

## Existing infrastructure to preserve
Keep:
- canonical JSD preservation;
- STI/B1TC contract validation and serialization read-back;
- automatic tactical/overhead map preview capture;
- rollback/deployment tooling;
- protected campaign-data audits;
- map classification/manifest tooling;
- binary safety and regression QA.

These are supporting infrastructure rather than the map-design methodology.

## Detailed methodology
See `MAP_VISUAL_METHODOLOGY_RESET_2026-09-15.md` for the complete methodology matrix, engine-native map compiler direction, semantic IR, prefab system, constraint/graph approaches, Tiled bridge concept, WFC scope, runtime overlays, bespoke-remake rules, sector-class routing, QA hierarchy and immediate next steps.

Source-side factory and authoring tools live on the matching `mattedinburgh/vr_source@maps/visual-overhaul-2026` branch.
