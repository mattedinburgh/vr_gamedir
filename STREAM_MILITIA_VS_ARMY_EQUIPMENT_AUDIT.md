# Militia vs Army Equipment Audit

Status: queued in `items/inventory-loot-2026`
Scope: tactical equipment/loadout balance only. Do not change strategic AI, force generation, patrols, reinforcements, garrisons, or campaign-force sizing.

## Current findings

Militia use separate green / regular / elite gun-choice and item-choice XML tables. Current Vengeance INI quality modifiers are:
- Green militia: 0
- Regular militia: +1 coolness
- Veteran/elite militia: +2 coolness
Enemy admin / regular / elite equipment quality modifiers are all 0.

Despite the militia quality bonuses, the actual source pools diverge materially from army pools as campaign progress rises.

### Weapons

Early game:
- Green militia are roughly comparable to admins.
- Regular militia are essentially identical to regular army at 0% progress.
- Elite militia are close to elite army, but already slightly weaker.

Mid game (~50%):
- Green militia fall behind admins: M1/M2 carbines and older rifles versus enemy AKM / AC-762 / stronger shotgun-heavy pool.
- Regular militia remain reasonably competitive, but enemy regulars get stronger specialist/support choices such as BAR and Tabuk DMR.
- Elite militia fall clearly behind elite army: militia are still dominated by M16A1/FAL-class weapons while enemy elites move to AUG, M16A4 and stronger specialist weapons.

Late game (100%):
- Green militia remain substantially below admin heavy/support capability.
- Regular militia are usable but weaker than enemy regulars in battle-rifle / MG / precision mix.
- Elite militia are materially weaker than elite army. Militia pool: G36C, M4A1, M16A1, FAL, Minimi, Scout/Beretta precision rifles. Enemy elite pool: P90, SG552/550/542, Minimi SPW/Minimi and SSG-P1-class precision.

### Armour and support gear

The larger imbalance is outside primary weapons:
- Regular army gets broader armour pools (Guardian/Zylon/camo), explosives/mines, radios/slings and more launcher options.
- Elite army gets Twaron/Dyneema/SWAT armour, richer grenade selection, mines/remote explosives, radios/slings and MGL support.
- Militia armour largely tops out at Spectra/Guardian.
- Militia grenade-launcher pool is still mainly M79; army gets MGL/Colt launcher options.
- Militia explosive/support kit is much thinner overall.

## Design direction for this stream

Do not make militia equal to the army. Preserve a believable hierarchy:
1. Green militia < admins, but still combat-capable and not pistol fodder.
2. Regular militia ~= lower-end regular army, with fewer specialist weapons and less premium support gear.
3. Elite militia ~= good regular army / lower-end elite army, not equal to top enemy elites.
4. Promotions should visibly improve armour, optics, weapon class, ammo quality and support equipment.
5. Militia should receive coherent squad equipment, not independent random rolls that produce nonsense combinations.
6. Reuse the role-aware loadout-planner principles where safe, but do not modify tactical AI behaviour in this stream.

## Follow-up audit before tuning

Compare every militia tier against its opposing army tier at 0/10/.../100 campaign progress for:
- primary weapon class and NCTH suitability
- optics/attachments compatibility
- armour protection
- ammo type / penetration
- grenades
- launchers
- medical gear
- radios / binoculars / utility
- role coverage at squad level

Then tune XML pools conservatively so militia remain distinctly poorer-equipped than the army while avoiding the current late-game capability cliff.
