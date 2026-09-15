# Vengeance inventory icon pilot — 20 items

This folder contains real, game-loadable STI replacements for twenty inventory icons.
They are generated from the current Vengeance assets with the original object geometry,
offsets and transparency silhouette preserved.

Nothing here is deployed automatically.

## Install into a local Vengeance game copy

From the repository/game root in PowerShell:

    .\Pilot\InventoryIcons20\INSTALL_PILOT.ps1

The installer is incremental: it copies only STI files whose SHA-256 differs and backs
up the originals first.

To revert:

    .\Pilot\InventoryIcons20\INSTALL_PILOT.ps1 -Revert

CONTACT_SHEET.png and Previews are inspection renders only. The game-ready files are
under Data-AIMv53/BigItems inside this pilot folder.
