# Situational Voice Pipeline 2026

This stream adds emotion- and context-aware combat speech without replacing Vengeance Reloaded's existing voice system.

## Canonical language policy

1. Spoken combat shouts, warnings, pain calls, retreat calls and other intelligible battle speech are English.
2. On-screen semantic popups/subtitles are English.
3. Player mercenaries keep their authored/profile voices.
4. Existing non-lexical screams, gasps, pain sounds and exertion sounds can remain when they contain no intelligible non-English speech.
5. Special authored character material may remain only when it is intentionally character-specific and does not contradict the English battle-speech requirement.
6. Never insert a new actor's emotional clips into an existing actor folder. One soldier must not change performer when wounded or panicked.

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

Up to 64 files can exist for one event/emotion bank. Immediate repeats should be avoided.

## Actor-pack methodology

New performers ship as complete new voice IDs. A new voice ID is not production-ready until:
- ALERT.ogg exists because the current engine uses it to discover a voice folder,
- every baseline event in `baseline_events.txt` is recorded or intentionally waived,
- required high-priority emotional variants are present,
- all clips pass `validate_voice_pack.py`.

Do not copy one new actor across many legacy voice IDs merely to inflate variety.

## Recording format

Archive/master:
- mono WAV
- 48 kHz
- 24-bit PCM
- dry voice, no music/reverb
- retain the original unprocessed master

Game delivery:
- mono OGG Vorbis
- 44.1 kHz
- nominal 128 kbps
- no clipping
- trim excessive silence but keep natural breaths/attacks
- do not hard-normalize every scream to identical loudness

## Performance model

Core states:
- controlled
- angry
- distressed
- panicked

Direction should describe situation + emotion + intensity. Examples:
- "hit by gunfire, serious wound, distressed, calling to nearby squad"
- "unexpected CQB contact, panicked but still intelligible"
- "retreat order, angry/defiant, not terrified"

Avoid theatrical shouting by default. Severe pain may be weak, breathless, shocked or strained rather than always loud.

## Vocal safety

Record normal tactical material first, emotional material second, and vocally stressful screams last. Limit high-strain scream/death-effort blocks, use breaks, and stop on pain or hoarseness.

## Production workflow

1. Run `build_voice_inventory.py` against the current game tree.
2. Review coverage and select the next recording batch.
3. Record one performer into a dedicated masters folder.
4. Name masters exactly per the event/emotion contract.
5. Run `deploy_voice_pack.py` to encode/copy into a staging voice folder.
6. Run `validate_voice_pack.py --complete --production`.
7. Review clips in game with voice-taunt debug logging enabled.
8. Fix only observed gaps/pickups.
9. Merge the validated actor pack into this branch.
10. Integrate source + gamedir streams together only after both are validated.

## Directory

`Tools/VoicePipeline/`
- `README.md` - production methodology
- `baseline_events.txt` - supported event list
- `build_voice_inventory.py` - inventories existing OGGs
- `prepare_recording_batch.py` - creates an English recording call sheet
- `validate_voice_pack.py` - validates naming, format and completeness
- `deploy_voice_pack.py` - converts/stages approved masters
