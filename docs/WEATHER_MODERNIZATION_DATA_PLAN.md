# Weather Modernization Data Plan — Inactive

Branch: `design/weather-modernization-inactive-2026-09-13`  
Base: `install/all-2026-09-12`  
Status: **INACTIVE / DATA DESIGN ONLY**

This branch is paired with the same inactive branch in `mattedinburgh/vr_source`.

## Planned data work

When implementation begins, add a dedicated weather configuration rather than silently changing existing gameplay data.

Proposed file:
`Data-Vengeance/Weather_Settings.ini`

Initial master switch:
```ini
[Weather System]
ENABLE_ADVANCED_WEATHER = FALSE
ENABLE_LOCAL_WEATHER = TRUE
ENABLE_WEATHER_AI_EFFECTS = TRUE
ENABLE_WEATHER_SMOKE_EFFECTS = TRUE
ENABLE_WEATHER_WEAPON_EFFECTS = TRUE
ENABLE_FOG = TRUE
ENABLE_DUST_STORMS = TRUE
```

While this branch remains inactive:
- do not point deployment scripts at it,
- do not enable advanced weather in the playable install,
- do not replace existing rain assets,
- do not change scripted-sector weather behaviour,
- do not modify live balance values.

The authoritative architecture and balance proposal is documented in:
`vr_source/docs/WEATHER_MODERNIZATION_DESIGN.md`.
