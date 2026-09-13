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

