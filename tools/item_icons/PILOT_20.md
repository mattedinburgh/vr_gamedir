# Item icon pilot — 20 weapons

This branch modifies the actual in-game inventory STI sheets, not mockups. Selected frames receive native-resolution micro-contrast/detail refinement, clearer steel/wood material separation, sharper silhouettes, and a red 3x5-pixel AI marker at the top-right. Untouched frame payloads are copied byte-for-byte; no deployment is performed.

- Data-AIMv53/Interface/MDGUNS.sti: frames 1, 220, 227, 127, 9, 366, 22, 272, 86, 110, 17, 19, 32, 16, 98, 26
- Data-AIMv53/Interface/MDP4ITEMS.sti: frames 681, 671, 682
- Data-AIMv53/Interface/MDP6ITEMS.STI: frames 76


## Exact pilot roster

| # | Weapon | Graphic set | Frame |
|---:|---|---|---:|
| 1 | Glock 17 | GUN | 1 |
| 2 | Beretta 92FS | GUN | 220 |
| 3 | Mini-Uzi | GUN | 227 |
| 4 | IMI Uzi MP2 | P4 | 681 |
| 5 | Uzi | GUN | 127 |
| 6 | HK MP5KA4 | GUN | 9 |
| 7 | FMK-3 | P4 | 671 |
| 8 | Marlin Camp Carbine 9 | P4 | 682 |
| 9 | Beretta Cx4 Storm | GUN | 366 |
| 10 | Ruger Mini-14 | GUN | 22 |
| 11 | Colt M16A1 | GUN | 272 |
| 12 | Colt M16A4 | GUN | 86 |
| 13 | Colt M4 Commando | GUN | 110 |
| 14 | SKS | GUN | 17 |
| 15 | M24 | GUN | 19 |
| 16 | SPAS-15 | GUN | 32 |
| 17 | Type 85 | GUN | 16 |
| 18 | Steyr AUG HBAR | GUN | 98 |
| 19 | AKM | GUN | 26 |
| 20 | HK G3A3 | P6 | 76 |

## In-game layers modified

- Inventory: `MDGUNS.sti`, `MDP4ITEMS.sti`, `MDP6ITEMS.STI`
- World/ground: `smguns.sti`, `SMP4ITEMS.STI`, `SMP6ITEMS.STI`
- Every changed inventory frame carries a red 3x5-pixel `AI` mark at top-right.
- Every changed world frame carries a smaller red `AI` mark at top-right.
- Material refinement is native-resolution: edge micro-contrast, steel highlights, wood grain separation, and stronger silhouette readability. Untouched frame payloads are preserved.
