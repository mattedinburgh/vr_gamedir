# San Mona Visual Reference Library — Latin America, c. 1980–1984

Purpose: historical/environmental art direction for the San Mona graphics-only remaster.

## Non-negotiable implementation rule

This library informs **pixels only**. It does not authorize changes to map geometry, tile placement, JSD, collision, LOS, penetration, destruction, quests, NPCs, doors, pathfinding, or scripts.

## Visual direction

San Mona should read as a poor, hot, Latin-American / Central-American vice-commercial district from roughly the early-to-mid 1980s, not as a generic dusty town and not as a modern tourist district.

Primary cues to study from the references:
- low-rise stucco and masonry facades with uneven maintenance;
- sun-faded ochre, cream, dirty white, muted turquoise/green and hand-painted commercial colour;
- corrugated metal, flat concrete/tar roofs, patched repairs and exposed utility detail;
- narrow commercial frontage, painted/sign-heavy shop facades and market spill-out;
- worn paving, cobbles, patched road edges, dust and drainage staining;
- practical dark-painted metal street furniture rather than polished modern fixtures;
- visually dense market/service clutter, but only where the original tile already represents such an object;
- conflict wear/bullet damage used selectively, not as a universal texture.

## Production resolution standard

All B1TC output frames preserve the exact native width, height, offset and alpha footprint of the original STI frame.

For new/redrawn art:
- working master target: **4× native linear resolution**;
- final output: downsample to exact original native dimensions;
- no enlargement of collision/visual footprint in the game.

The generated C5 manifest records, per family:
- frame count;
- native width/height range;
- 4× working-master width/height range;
- frame offsets.

## Archival reference set

1. **San Pedro Sacatepéquez, Guatemala — street scene, 1983/84**
   - Source: https://commons.wikimedia.org/wiki/File:SanPedroSacatepequez2.JPG
   - Original: 857×657
   - Licence: CC BY 3.0
   - Use for: small-town street proportions, facade wear, street-edge treatment.

2. **Guatemala City — market district street, 22 Jan 1980**
   - Source: https://commons.wikimedia.org/wiki/File:Guatemala_City-22-Marktviertel-Strasse-1980-gje.jpg
   - Original: 2656×1736
   - Licence: CC BY-SA
   - Use for: dense commercial frontage, market/street visual density, signage.

3. **Guatemala City — evening street, 22 Jan 1980**
   - Source: https://commons.wikimedia.org/wiki/File:Guatemala_City-04-Strasse_am_Abend-1980-gje.jpg
   - Original: 1776×2264
   - Licence: Creative Commons per source page
   - Use for: facade colours, street lamps, night/evening ambience cues.

4. **Guatemala City — shop-sign street scene, 1980**
   - Source: https://commons.wikimedia.org/wiki/File:Guate_Wrangler.jpg
   - Original: 1314×926
   - Licence: Creative Commons per source page
   - Use for: hand-painted/commercial signage and shop-front density.

5. **Estelí, Nicaragua — street scene with conflict damage, 1984**
   - Source: https://commons.wikimedia.org/wiki/File:Nicaragua_en_1984_-_25.jpg
   - Original: 3000×2000
   - Licence: CC BY 2.0
   - Use for: masonry/stucco wear, sidewalk/street edge, selective bullet/conflict damage.

6. **San Pedro Sula, Honduras — municipal district, 1980**
   - Source: https://commons.wikimedia.org/wiki/File:SanPedroSulaMunicpPalace.jpg
   - Original: 2575×2031
   - Licence: GFDL per source page
   - Use for: regional civic/urban palette and paved-street context.

7. **Mexico City — street market, 30 Jan 1980**
   - Source: https://commons.wikimedia.org/wiki/File:Mexico_City-Markt-12-Gewuerzkraemerin-1980-gje.jpg
   - Original: 2717×1803
   - Licence: CC BY-SA 4.0
   - Use for: market colour, awnings, practical clutter, produce/service visual density.

8. **Mexico City — historic street, 7 Oct 1980**
   - Source: https://commons.wikimedia.org/wiki/File:022244_R2-011_CALLE_DE_MADERO_DE_EJE_CENTRAL_AL_Z%C3%93CALO_OCTUBRE_07_1980_(38010188905).jpg
   - Original: 1500×2237
   - Licence: CC0
   - Use for: period street furniture, facade rhythm, signs and street surface.

## Usage policy

- Do not copy a single photograph literally into a tile.
- Use multiple references to infer material, colour, wear, signage and environmental character.
- Preserve the original JA2 silhouette/geometry.
- Prefer period-authentic imperfection over exaggerated "post-apocalyptic" grime.
- San Mona is a functioning vice town: poor and worn, but inhabited, commercial and colourful.
