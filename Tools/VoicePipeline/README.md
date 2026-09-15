# Situational Voice Pipeline 2026

This stream adds emotional/context-aware combat voice deployment without replacing Vengeance Reloaded's existing voice system.

## Canonical language policy

1. Player mercenaries use their authored/profile voice. In practice this is English operational speech unless the character already has established bilingual/custom material.
2. Enemy Army uses Spanish/local voice packs.
3. Militia uses Spanish/local voice packs.
4. Ordinary local civilians use Spanish/local voice packs.
5. Special civilian groups keep their authored group voice. Do not infer language from CIV_TEAM alone.
6. Non-lexical screams, gasps and exertion sounds belong to the actor/voice identity rather than to a language rule.
7. On-screen semantic popups remain English.

Never insert a new actor's emotional clips into an existing actor folder. A soldier must not change performer when wounded or panicked.

## Runtime naming contract

Legacy files continue to work unchanged:

    GOT_HIT_GUNFIRE.ogg
    GOT_HIT_GUNFIRE 0.ogg
    GOT_HIT_GUNFIRE 1.ogg

New state-specific files use:

    GOT_HIT_GUNFIRE__controlled.ogg
    GOT_HIT_GUNFIRE__controlled 0.ogg
    GOT_HIT_GUNFIRE__angry.ogg
    GOT_HIT_GUNFIRE__distressed.ogg
    GOT_HIT_GUNFIRE__panicked.ogg

The source selector chooses the requested emotional bank if present and falls back safely:

- panicked -> distressed -> controlled -> legacy
- distressed -> controlled -> legacy
- angry -> controlled -> legacy
- controlled -> legacy

Up to 64 files can exist for one event/emotion bank (base + numbered variants). Immediate repeats are avoided.

## Actor-pack methodology

New performers ship as complete new voice IDs, for example:

    Voice/Army/Male/Regular/10/
    Voice/Army/Female/Regular/03/
    Voice/Militia/Male/Regular/02/

A new voice ID is not production-ready until:
- ALERT.ogg exists (the current engine uses it to discover a voice folder),
- every baseline event listed in `baseline_events.txt` is recorded or intentionally waived,
- required high-priority emotional variants are present,
- all clips pass `validate_voice_pack.py`.

Do not copy one new actor across many legacy voice IDs merely to increase count. Reuse across Army/Militia is allowed only when intentionally representing the same performer/persona and the design calls for that repetition.

## Recording format

Archive/master:
- mono WAV
- 48 kHz
- 24-bit PCM
- dry voice, no music/reverb
- retain original unprocessed master

Game delivery:
- mono OGG Vorbis
- 44.1 kHz
- nominal 128 kbps (existing game material varies roughly 96-160 kbps)
- no clipping
- trim excessive silence but keep natural breaths/attacks
- do not hard-normalize every scream to identical loudness

The deployment script uses ffmpeg when available and never destroys masters.

## Performance model

Core states:
- controlled
- angry
- distressed
- panicked

Direction should describe situation + emotion + intensity, e.g.:
- "hit by gunfire, serious wound, distressed, calling to nearby squad"
- "unexpected CQB contact, panicked but still intelligible"
- "retreat order, angry/defiant, not terrified"

Avoid theatrical shouting by default. Severe pain can be weak, breathless, shocked or strained rather than always loud.

## Vocal safety

Record normal tactical material first, then emotional material, and vocally stressful screams last. Limit high-strain scream/death-effort blocks, use breaks, and stop on pain/hoarseness. Do not demand repeated maximum-effort screams.

## Production workflow

1. Run `build_voice_inventory.py` against the current game tree.
2. Review coverage and select the next recording batch from `recording_manifest.csv`.
3. Record one performer into a dedicated masters folder.
4. Name masters exactly per manifest event/emotion contract.
5. Run `deploy_voice_pack.py` to encode/copy into a staging voice folder.
6. Run `validate_voice_pack.py --complete`.
7. Review clips in game with voice-taunt debug logging enabled.
8. Fix only observed gaps/pickups.
9. Merge the validated actor pack into this branch.
10. Integrate into the play branch only after source + gamedir streams are paired.

## Debugging

With voice-taunt debug enabled, the source branch logs:
- soldier id
- taunt/event id
- requested emotion
- selected fallback emotion
- emotional/legacy source
- variant count
- final file

This is the primary QA evidence for wrong-language, wrong-emotion and repetition bugs.

## Directory

`Tools/VoicePipeline/`
- `README.md` - this file
- `baseline_events.txt` - full supported event list
- `recording_manifest.csv` - first production script/gap-fill sheet
- `build_voice_inventory.py` - inventories existing OGGs without external Python libraries
- `validate_voice_pack.py` - validates naming, format and completeness
- `deploy_voice_pack.py` - converts/stages approved masters
