VR A3 CUSTOM ART PACK V1
========================
Generated from scratch by Tools/GenerateCustomA3Tiles.py.

Base terrain frame counts intentionally match TileDat.cpp:
  VR_A3_TEX1      35  warm dry soil
  VR_A3_TEX2      35  compact brown soil
  VR_A3_TEX3      35  low green grass
  VR_A3_TEX4      35  lush tropical grass
  VR_A3_TEX5      35  mixed scrub
  VR_A3_TEX6      37  cultivated field soil
  VR_A3_TEX7      49  rutted rural trail
  VR_A3_WATER     50  shallow tropical water
  VR_A3_DEEPWATER 37  deep water

Visual-only 10-frame families:
  CROPS, RUTS, PROPS, ROCKS, WOOD, WEEDS, IRRIGATION, JUNK

These B1TC files replace pixels in A3 only through the sector visual profile.
Legacy walls, trees, doors and other JSD-bearing structure families are retained
until their pixel identity and collision/JSD identity are deliberately separated.
