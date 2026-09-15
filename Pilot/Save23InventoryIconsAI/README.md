# SaveGame23 inventory icon replacement

This pack changes only the 94 unique item IDs extracted from SaveGame23.sav. Large BigItems STIs are replaced only for graphics referenced by those items. In shared MDGUNS/MDP sprite sheets, only those specific subimages are changed; all other subimages are round-trip verified pixel-for-pixel identical.

Every changed icon has a small red AI stamp in its bottom-left corner.

Nothing is deployed automatically. Run INSTALL_SAVE23_ICONS.ps1 to install incrementally with backups; use -Revert to restore originals.
