# Experimental Enemy Loadout Planner

Status: **work branch only; not active in the game**

Branch: `work/enemy-loadout-planner-2026-09-13`

This document records the equipment-generation rules being implemented before
anything is merged into `install/all-2026-09-12`.

## Design order

1. Campaign progress + sector + enemy class
2. Squad composition
3. Soldier role
4. Weapon family
5. Role-appropriate attachments
6. LBE/load-carrying profile
7. Ammo / grenades / support equipment
8. Traits and AI behaviour

The current live system largely starts from equipment coolness and independently
rolls weapon/LBE/attachments.  The experimental planner reverses that order.

## Roles

- Rifleman
- Assault
- Automatic rifleman / LMG
- Marksman
- Sniper
- Grenadier
- AT specialist
- Medic
- Radio operator
- Squad leader
- Scout
- Mortar / fire support

## Squad-composition rules

The planner protects a rifle core and uses explicit caps.

- automatic weapon: about 1 per 5-7 soldiers
- grenadier: about 1 per 4-6 once organized troops appear
- marksman: about 1 per 6-8
- dedicated sniper: elite/specialist and late, much rarer than marksman
- AT: capped specialist role
- medic/radio: professionalization roles
- mortar: sector/group support, not a normal independent per-soldier lottery

For established 8+ soldier groups the planner reserves controlled optional
specialist slots so groups vary without becoming support-weapon soup.

Small squads demote lower-priority specialist roles back to optional status
before they are allowed to squeeze out the rifle core.

## Progression

### 0-20%
Irregular/security style.  Mostly simple fighting loads and minimal optics.

### 20-40%
Organized troops.  Automatic rifleman, assault and grenadier roles begin to
appear.  Basic sights and role-specific LBE become plausible.

### 40-60%
Professional combined-arms squads.  Marksman, medic, radio and AT become
available.  One variable specialist slot is normally reserved in larger groups.

### 60-80%
Veteran response forces.  Improvement comes increasingly from condition,
optics, ammo, armour, smoke, night gear and specialist density rather than
replacing every rifle.

### 80-100%
Elite/counter-insurgency forces.  Optimized role packages and coherent support
equipment.  Late elite groups can reserve two variable specialist slots.

## LBE profiles

The source planner currently defines these intent profiles:

- Light
- Standard rifle
- Assault
- Automatic weapon
- Grenadier
- Medic
- Radio
- Heavy support

These are **intent categories**, not hardcoded item IDs yet.

Existing Vengeance data already contains useful specialized pocket layouts,
including 40 mm grenade and MG-belt leg rigs.  The future selector should score
available LBE by the actual load required instead of picking a random LBE by
coolness.

Backpacks are not automatically better.  They should be uncommon for ordinary
assault/rifle roles and more likely for radio, medic, sniper observation and
heavy-support roles.

## Attachment policy

Current live NAS behaviour uses a broad coolness pool and global random
attachment selection.  The planner instead defines an attachment budget and an
optic intent.

### Rifleman
Irons -> reflex/1x -> low-power optic.  No automatic high-magnification scope.

### Assault
Reflex/1x, laser, handling/recoil accessories.  Little magnification.

### Automatic rifleman / MG
Bipod first, then sensible control/low-power optic.  No random sniper optics.

### Marksman
Low-power/4x-class optic progressing toward proper marksman glass; bipod where
appropriate.

### Sniper
Dedicated magnified optic + bipod.  Suppressor only where weapon/mission
supports it.

### Grenadier
Practical combat optic and launcher-compatible package.

### AT
Simple rifle setup; the heavy specialist weapon is already the role's main
equipment burden.

### Medic / radio / leader
Compact practical weapon setup, smoke and role equipment rather than maximum
weapon modification.

### Scout
Light fighting load; reflex/laser/night-compatible equipment.  Suppressors may
be allowed for elite scouts.

## Attachment budgets

The planner treats the budget as a maximum useful package, never a requirement
to fill every slot.

- very early / low equipment: 0-1
- organized troops: up to 2
- veteran regulars: up to 3
- elite late specialists: up to 4 where useful

Role determines *which* attachment is useful; progress/equipment rating
determines how often and how good.

## Suppressors

Suppressors remain specialist equipment.  They are not a generic late-game
coolness upgrade.  Current planner policy restricts them to scout/sniper roles,
primarily elite late-game troops.

## Current data pools observed

`EnemyItemChoices.xml` currently exposes:

- Scopes: 9 global entries
- Weapon Attachments: 33 global entries
- LBE: 20 global entries

The new system should continue using compatible Vengeance items, but filter and
score them against role intent rather than copying the full 1.13 equipment
tables.

## Safety / rollout

Nothing in this branch is merged to the playable branch.

The source planner module is intentionally isolated from
`GenerateRandomEquipment()` until:

1. squad-size/reset points are mapped,
2. role quotas are validated,
3. attachment/LBE scoring is implemented,
4. the project compiles cleanly,
5. dry-run output is reviewed.



## Implementation status — isolated work branch

The planner now has executable source-side planning code but remains disconnected
from live soldier creation.

Implemented:

- balanced equipment cells aligned with tactical AI fireteam scale:
  - minimum normal cell 5
  - target 8
  - maximum 10
- class-balanced cells for administrator / regular / elite mixes
- mandatory + optional role tickets with a protected rifle core
- class suitability when assigning role tickets
- deterministic role-ticket consumption independent of creation order
- loadout intent (ammo, smoke, hand grenades, specialist ammunition)
- specialist support profiles:
  - grenade launcher
  - light AT
  - RPG
  - mortar
- role-aware primary-gun ranking from existing Vengeance gun tables
- role-aware optic/attachment scoring
- NAS-compatible attachment package construction on a temporary weapon object
- role-aware LBE scoring and coherent LBE package construction
- deterministic complete equipment recommendations for audit
- structural validation of squad plans and loadout plans

The planner does **not** call `GenerateRandomEquipment()`, does not alter live
inventory generation, and does not consume game RNG from the live path.

## Tactical AI alignment

The existing Vengeance AI already uses fireteam sizes that fit this equipment
design:

- target: 8
- normal maximum: 9
- merged maximum: 10

The loadout-cell planner therefore uses a target of 8 and a 5-10 normal design
range rather than inventing a second squad-size system.

Examples from the current cell splitter:

- 11 -> 6 + 5
- 15 -> 8 + 7
- 16 -> 8 + 8
- 17 -> 9 + 8
- 20 -> 7 + 7 + 6
- 24 -> 8 + 8 + 8
- 30 -> 8 + 8 + 7 + 7

The eventual activation should register each planned equipment-cell identity
with the AI fireteam layer after tactical soldier creation, so equipment and AI
organization remain coherent.

## Current enemy creation integration points

Static defenders eventually pass through:

`AddSoldierInitListEnemyDefenceSoldiers -> CreateDetailedPlacementGivenBasicPlacementInfo -> GenerateRandomEquipment`

Strategic/mobile reinforcements pass through:

`AddEnemiesToBattle -> TacticalCreate*Enemy -> CreateDetailedPlacementGivenBasicPlacementInfo -> GenerateRandomEquipment`

These are the intended future activation points. They have not been changed on
the playable branch.

## Class-specific pools

The planner deliberately reuses the existing Vengeance pools and follows the
same `fSoldierClassSpecificItemTables` fallback semantics as live code.

This preserves authored faction identity instead of replacing the Vengeance
tables with stock 1.13 tables.

A data audit found a stale-looking admin attachment entry:

- `ItemChoices_Enemy_Admin.xml`
- `ubChoices = 20`
- `bItemNo21 = 2859`

Item 2859 is not present in the active Items, Attachments or Weapons XMLs.
Therefore the planner intentionally respects `ubChoices=20` and does **not**
"fix" it to 21. The current count safely excludes that stale entry.

## Specialist equipment separation

Hand grenades and specialist ammunition are now separate planning concepts.

Examples:

- grenadier:
  - ordinary rifle magazines
  - 1-2 hand grenades
  - smoke
  - 4-7 launcher rounds
- AT specialist:
  - ordinary compact fighting load
  - light AT at earlier professional progression
  - RPG later
  - RPG ammunition only when applicable
- mortar:
  - personal weapon load
  - minimal hand grenades
  - dedicated mortar-shell allowance

This avoids the old pattern where the same `bGrenades` counter represents
hand grenades, launcher rounds, rockets or mortar shells depending on unrelated
random rolls.

## Activation boundary

Before this planner is allowed into live gameplay:

1. compile the isolated source branch successfully,
2. add an explicit creation-batch context around static defenders and
   reinforcements,
3. consume preplanned class role tickets during creation,
4. translate the recommendation into actual inventory objects,
5. register planned equipment-cell identity with the tactical AI fireteam
   layer,
6. leave autoresolve on the old path initially,
7. run new-save tactical tests across early/mid/late progression,
8. inspect generated kits and drop economy,
9. only then consider merging to `install/all-2026-09-12`.

