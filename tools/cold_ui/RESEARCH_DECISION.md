# Cold UI research decision — 2026-09-14

## Question

How should Vengeance modernize its interface without destabilizing JA2's old fixed-coordinate UI model?

## Evidence reviewed

- Current JA2 v1.13 documentation: layered VFS/profile overrides are the normal mod architecture; the highest-priority data layer wins for an asset path.
  - https://1dot13.github.io/documentation/modding/
- Current 1.13 source: PNG loading and multi-resolution support exist in parts of the engine, but the UI remains a mixture of fixed assets, fixed coordinates and resolution-specific branches.
  - https://github.com/1dot13/source
- Historical 1.13 Custom Interface Pack: demonstrates that full visual skins were already shipped as interface asset replacements, including New Inventory System support.
  - https://www.moddb.com/mods/ja2-113-mod/downloads/custom-interface-pack-for-ja2-113
- JA2-Stracciatella UI scaling issue #62: higher internal resolutions make the UI too small; scaling is a distinct problem from asset replacement.
  - https://github.com/ja2-stracciatella/ja2-stracciatella/issues/62
- JA2-Stracciatella 0.19 work: a dynamic tactical bottom bar and centred bottom panel were implemented, proving responsive layout is possible but requires dedicated layout code.
  - https://github.com/ja2-stracciatella/ja2-stracciatella/blob/master/changes.md
- JA2-Stracciatella scaling implementation: distinguishes internal resolution from output scaling and offers pixel-perfect/integer scaling as a separate renderer concern.
  - https://github.com/ja2-stracciatella/ja2-stracciatella/blob/master/src/launcher/StracciatellaLauncher.fl
- Community reports repeatedly describe native 1080p/1440p JA2 UI as too small and recommend lower logical resolution plus fullscreen scaling when readability is the goal.
  - https://steamcommunity.com/app/12370/discussions/0/5733664933462475957/
  - https://www.reddit.com/r/JaggedAlliance/comments/r9fncw/

## Decision

### Phase A — now: semantic-aware cold skin

Use a dedicated VFS overlay, preserve original dimensions/offsets/hitboxes, and modernize only the visual material language. The transform is classified per asset:

- **chrome** — steel/navy treatment at full strength;
- **mixed** — backgrounds containing both chrome and artwork, treated conservatively;
- **semantic** — status lights, state markers, warnings; only minimal cooling;
- **preserve** — available for assets that must remain untouched.

This gives a coherent cold UI while keeping ETRLE geometry and gameplay interaction byte-stable.

### Phase B — after visual approval: authored replacements

For the most visible surfaces, replace automated palette work with hand-authored/AI-assisted art while keeping the same sprite dimensions and frame ordering. Use true-colour PNG only where the loader path genuinely supports it; PNG by itself does not make a fixed-size control spatially higher-resolution.

### Phase C — optional later: UI scale/layout subsystem

If larger controls at 1920x1080 are wanted without sacrificing tactical viewport resolution, port the *idea* of Stracciatella's layout abstraction: centralize tactical-panel coordinates, scale mouse regions and fonts with the visual elements, and tile/stretch only designated chrome regions. Do not mix this with the skinning branch.

## Rejected approaches

- **10x every UI asset:** wasted detail unless draw size changes; breaks fixed sprite assumptions and memory expectations.
- **Blind palette cooling:** safe structurally but can corrupt semantic reds/greens and embedded artwork.
- **Immediate full responsive rewrite:** feasible, but disproportionate risk for a colour/material redesign and harder to validate alongside ongoing Vengeance gameplay changes.
- **Edit base Vengeance assets in place:** poor rollback and conflicts with the VFS layering model.
