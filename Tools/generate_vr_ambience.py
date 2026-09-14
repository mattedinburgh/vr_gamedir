#!/usr/bin/env python3
"""Generate an original, low-fi ambient sound library for Vengeance Reloaded.

The sounds are deliberately restrained and game-like: mono 22.05 kHz PCM WAV,
short seamless-ish beds plus sparse one-shots.  They are synthesized from
noise, oscillators and envelopes so the repository has no third-party audio
licensing dependency.
"""

from __future__ import annotations
import math
import os
import random
import wave
from array import array

SR = 22050
OUT = os.path.join("Data-Vengeance", "Sounds", "VR_Ambience")
TAU = math.tau


def clamp(v: float) -> float:
    return -1.0 if v < -1.0 else (1.0 if v > 1.0 else v)


def write_wav(name: str, samples: list[float]) -> None:
    os.makedirs(OUT, exist_ok=True)
    peak = max(0.001, max(abs(x) for x in samples))
    gain = min(0.92 / peak, 1.0)
    pcm = array("h", (int(clamp(x * gain) * 32767) for x in samples))
    path = os.path.join(OUT, name)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def fade_edges(x: list[float], seconds: float = 0.05) -> None:
    n = min(int(seconds * SR), len(x) // 4)
    for i in range(n):
        g = math.sin((i + 1) / n * math.pi / 2) ** 2
        x[i] *= g
        x[-1 - i] *= g


def noise_bed(rng: random.Random, n: int, smooth: float, high: float = 0.0) -> list[float]:
    out = [0.0] * n
    lp = 0.0
    for i in range(n):
        white = rng.uniform(-1.0, 1.0)
        lp += smooth * (white - lp)
        out[i] = lp + high * white
    return out


def add_tone(x: list[float], freq: float, amp: float, wobble: float = 0.0, wobble_hz: float = 0.2) -> None:
    phase = 0.0
    for i in range(len(x)):
        t = i / SR
        f = freq * (1.0 + wobble * math.sin(TAU * wobble_hz * t))
        phase += TAU * f / SR
        x[i] += amp * math.sin(phase)


def add_pulsed_noise(x: list[float], rng: random.Random, period: float, width: float, amp: float, smooth: float = 0.04) -> None:
    lp = 0.0
    for i in range(len(x)):
        t = i / SR
        p = (t % period) / period
        env = math.exp(-((p - 0.35) / width) ** 2)
        white = rng.uniform(-1.0, 1.0)
        lp += smooth * (white - lp)
        x[i] += amp * env * lp


def add_chirp(x: list[float], start: float, dur: float, f0: float, f1: float, amp: float, harmonic: float = 0.2) -> None:
    a = max(0, int(start * SR))
    b = min(len(x), int((start + dur) * SR))
    phase = 0.0
    for i in range(a, b):
        u = (i - a) / max(1, b - a - 1)
        env = math.sin(math.pi * u) ** 1.6
        f = f0 + (f1 - f0) * u
        phase += TAU * f / SR
        x[i] += amp * env * (math.sin(phase) + harmonic * math.sin(2.02 * phase))


def add_impact(x: list[float], start: float, freqs: tuple[float, ...], amp: float, decay: float) -> None:
    a = int(start * SR)
    for i in range(a, len(x)):
        t = (i - a) / SR
        if t > decay * 8:
            break
        env = math.exp(-t / decay)
        v = 0.0
        for j, f in enumerate(freqs):
            v += math.sin(TAU * f * t + j * 0.7) / (1 + j * 0.5)
        x[i] += amp * env * v / len(freqs)


def base_loop(seed: int, seconds: float, smooth: float, level: float, high: float = 0.0) -> list[float]:
    rng = random.Random(seed)
    n = int(seconds * SR)
    nse = noise_bed(rng, n, smooth=smooth, high=high)
    x = [level * v for v in nse]
    return x


def make_loops() -> None:
    seconds = 9.0

    # Rural
    x = base_loop(10, seconds, 0.006, 0.36, 0.025)
    add_pulsed_noise(x, random.Random(11), 5.2, 0.20, 0.08, 0.015)
    add_chirp(x, 1.2, .32, 1900, 2800, .08)
    add_chirp(x, 6.1, .28, 2400, 1700, .06)
    fade_edges(x); write_wav("rural_day.wav", x)

    x = base_loop(12, seconds, 0.004, 0.22, 0.015)
    add_tone(x, 4200, .012, .05, .8)
    add_tone(x, 5100, .008, .06, 1.1)
    fade_edges(x); write_wav("rural_night.wav", x)

    # Forest
    x = base_loop(20, seconds, 0.01, 0.34, 0.02)
    add_pulsed_noise(x, random.Random(21), 3.8, .18, .12, .02)
    add_chirp(x, 2.0, .26, 1500, 2600, .08)
    add_chirp(x, 6.5, .22, 3100, 2300, .06)
    fade_edges(x); write_wav("forest_day.wav", x)

    x = base_loop(22, seconds, 0.008, 0.22, 0.01)
    add_tone(x, 3600, .014, .07, .6)
    add_tone(x, 4700, .012, .08, 1.0)
    fade_edges(x); write_wav("forest_night.wav", x)

    # Jungle
    x = base_loop(30, seconds, 0.012, 0.37, 0.028)
    add_pulsed_noise(x, random.Random(31), 2.9, .22, .14, .025)
    add_chirp(x, .9, .30, 2200, 3600, .09)
    add_chirp(x, 4.1, .24, 3200, 2100, .08)
    add_chirp(x, 7.1, .34, 1700, 3000, .08)
    fade_edges(x); write_wav("jungle_day.wav", x)

    x = base_loop(32, seconds, 0.01, 0.28, 0.018)
    add_tone(x, 3900, .018, .10, .7)
    add_tone(x, 5200, .015, .09, 1.15)
    add_pulsed_noise(x, random.Random(33), 2.4, .15, .08, .02)
    fade_edges(x); write_wav("jungle_night.wav", x)

    # Farm
    x = base_loop(40, seconds, 0.005, 0.28, 0.02)
    add_tone(x, 90, .018, .03, .08)
    add_chirp(x, 1.7, .30, 1800, 2600, .07)
    add_impact(x, 5.8, (420, 690, 980), .025, .18)
    fade_edges(x); write_wav("farm_day.wav", x)

    x = base_loop(41, seconds, 0.004, 0.18, 0.01)
    add_tone(x, 4300, .014, .07, .8)
    add_tone(x, 5200, .01, .08, 1.05)
    fade_edges(x); write_wav("farm_night.wav", x)

    # City
    x = base_loop(50, seconds, 0.02, 0.20, 0.05)
    add_tone(x, 52, .025, .10, .05)
    add_tone(x, 96, .015, .08, .08)
    add_pulsed_noise(x, random.Random(51), 4.5, .22, .08, .08)
    fade_edges(x); write_wav("city_day.wav", x)

    x = base_loop(52, seconds, 0.014, 0.16, 0.035)
    add_tone(x, 50, .022, .08, .05)
    add_tone(x, 100, .012, .06, .09)
    fade_edges(x); write_wav("city_night.wav", x)

    # San Mona: city plus distant low club pulse.
    x = base_loop(60, seconds, 0.018, 0.20, 0.04)
    add_tone(x, 58, .03, .06, .08)
    add_pulsed_noise(x, random.Random(61), 3.2, .16, .07, .08)
    fade_edges(x); write_wav("sanmona_day.wav", x)

    x = base_loop(62, seconds, 0.012, 0.16, 0.03)
    for beat in [0.5, 1.1, 2.5, 3.1, 4.5, 5.1, 6.5, 7.1, 8.5]:
        add_impact(x, beat, (48, 72), .035, .11)
    add_tone(x, 52, .02, .04, .07)
    fade_edges(x); write_wav("sanmona_night.wav", x)

    # Coast
    x = base_loop(70, seconds, 0.025, 0.28, 0.055)
    add_pulsed_noise(x, random.Random(71), 3.6, .27, .26, .035)
    fade_edges(x); write_wav("coast_day.wav", x)

    x = base_loop(72, seconds, 0.02, 0.24, 0.04)
    add_pulsed_noise(x, random.Random(73), 4.0, .29, .22, .03)
    fade_edges(x); write_wav("coast_night.wav", x)

    # Desert
    x = base_loop(80, seconds, 0.003, 0.30, 0.015)
    add_pulsed_noise(x, random.Random(81), 5.8, .30, .12, .008)
    fade_edges(x); write_wav("desert_day.wav", x)

    x = base_loop(82, seconds, 0.0025, 0.18, 0.008)
    add_tone(x, 4300, .006, .08, .7)
    fade_edges(x); write_wav("desert_night.wav", x)

    # Swamp
    x = base_loop(90, seconds, 0.018, 0.28, 0.03)
    add_tone(x, 130, .012, .18, .25)
    add_pulsed_noise(x, random.Random(91), 2.7, .18, .10, .03)
    fade_edges(x); write_wav("swamp_day.wav", x)

    x = base_loop(92, seconds, 0.015, 0.25, 0.02)
    add_tone(x, 120, .018, .20, .24)
    add_tone(x, 3900, .012, .09, .8)
    add_tone(x, 4900, .010, .09, 1.1)
    fade_edges(x); write_wav("swamp_night.wav", x)

    # Industrial
    x = base_loop(100, seconds, 0.012, 0.15, 0.025)
    add_tone(x, 50, .07, .02, .06)
    add_tone(x, 100, .025, .03, .09)
    add_tone(x, 180, .012, .05, .13)
    fade_edges(x); write_wav("industrial_day.wav", x)

    x = base_loop(101, seconds, 0.010, 0.12, 0.018)
    add_tone(x, 50, .06, .02, .06)
    add_tone(x, 100, .022, .03, .09)
    fade_edges(x); write_wav("industrial_night.wav", x)

    # Military
    x = base_loop(110, seconds, 0.01, 0.14, 0.018)
    add_tone(x, 60, .038, .04, .06)
    add_tone(x, 120, .014, .04, .09)
    fade_edges(x); write_wav("military_day.wav", x)

    x = base_loop(111, seconds, 0.008, 0.10, 0.012)
    add_tone(x, 60, .032, .03, .06)
    add_tone(x, 120, .012, .03, .09)
    fade_edges(x); write_wav("military_night.wav", x)

    # Airport
    x = base_loop(120, seconds, 0.015, 0.15, 0.03)
    add_tone(x, 72, .035, .10, .08)
    add_tone(x, 144, .012, .08, .11)
    add_pulsed_noise(x, random.Random(121), 6.5, .35, .12, .02)
    fade_edges(x); write_wav("airport_day.wav", x)

    x = base_loop(122, seconds, 0.012, 0.11, 0.02)
    add_tone(x, 72, .028, .08, .08)
    fade_edges(x); write_wav("airport_night.wav", x)

    # Underground / mine / sewer
    x = base_loop(130, seconds, 0.02, 0.10, 0.004)
    add_tone(x, 38, .04, .03, .05)
    add_tone(x, 76, .012, .04, .08)
    add_impact(x, 3.1, (540, 790), .018, .25)
    add_impact(x, 7.2, (420, 660), .016, .24)
    fade_edges(x); write_wav("underground.wav", x)

    x = base_loop(131, seconds, 0.025, 0.12, 0.006)
    add_tone(x, 42, .035, .02, .05)
    add_impact(x, 2.4, (620, 870), .019, .28)
    add_impact(x, 6.0, (510, 760), .017, .26)
    fade_edges(x); write_wav("mine.wav", x)

    x = base_loop(132, seconds, 0.03, 0.14, 0.008)
    add_tone(x, 47, .03, .03, .05)
    add_pulsed_noise(x, random.Random(133), 2.8, .26, .08, .04)
    fade_edges(x); write_wav("sewer.wav", x)

    # Dam
    x = base_loop(140, seconds, 0.035, 0.23, 0.05)
    add_tone(x, 52, .035, .03, .07)
    add_pulsed_noise(x, random.Random(141), 2.2, .35, .20, .05)
    fade_edges(x); write_wav("dam_day.wav", x)

    x = base_loop(142, seconds, 0.03, 0.18, 0.035)
    add_tone(x, 52, .032, .03, .07)
    add_pulsed_noise(x, random.Random(143), 2.4, .35, .17, .05)
    fade_edges(x); write_wav("dam_night.wav", x)


def oneshot(name: str, seconds: float, seed: int) -> tuple[list[float], random.Random]:
    return [0.0] * int(seconds * SR), random.Random(seed)


def make_one_shots() -> None:
    x, r = oneshot("bird_chirp_01.wav", 1.2, 200)
    add_chirp(x, .12, .34, 1700, 3300, .55)
    add_chirp(x, .56, .28, 2500, 1800, .35)
    fade_edges(x); write_wav("bird_chirp_01.wav", x)

    x, r = oneshot("bird_chirp_02.wav", 1.4, 201)
    add_chirp(x, .10, .24, 3100, 4100, .42)
    add_chirp(x, .43, .20, 3900, 2500, .38)
    add_chirp(x, .76, .30, 2200, 3500, .34)
    fade_edges(x); write_wav("bird_chirp_02.wav", x)

    x, r = oneshot("crow_call.wav", 1.6, 202)
    add_chirp(x, .20, .40, 650, 440, .42, .35)
    add_chirp(x, .82, .36, 620, 410, .32, .35)
    fade_edges(x); write_wav("crow_call.wav", x)

    x, r = oneshot("insect_burst.wav", 2.0, 203)
    add_tone(x, 4200, .16, .10, 6.0)
    add_tone(x, 5200, .09, .08, 7.2)
    fade_edges(x); write_wav("insect_burst.wav", x)

    x, r = oneshot("frog_call.wav", 1.7, 204)
    for s in (.20, .48, .92):
        add_chirp(x, s, .18, 180, 125, .38, .28)
    fade_edges(x); write_wav("frog_call.wav", x)

    x, r = oneshot("leaf_rustle.wav", 2.2, 205)
    n = noise_bed(r, len(x), .06, .12)
    for i, v in enumerate(n):
        t = i / SR
        env = math.sin(math.pi * min(1.0, t / 1.1)) ** 2 if t < 1.1 else math.sin(math.pi * max(0.0, (2.2 - t) / 1.1)) ** 2
        x[i] += .22 * env * v
    fade_edges(x); write_wav("leaf_rustle.wav", x)

    x, r = oneshot("farm_bird.wav", 1.8, 206)
    add_chirp(x, .12, .18, 980, 1600, .40)
    add_chirp(x, .38, .16, 1200, 1800, .34)
    add_chirp(x, .70, .22, 1000, 1450, .28)
    fade_edges(x); write_wav("farm_bird.wav", x)

    x, r = oneshot("animal_low.wav", 2.3, 207)
    add_chirp(x, .25, 1.45, 105, 82, .32, .45)
    fade_edges(x); write_wav("animal_low.wav", x)

    x, r = oneshot("distant_dog.wav", 2.1, 208)
    add_chirp(x, .22, .24, 420, 300, .26, .35)
    add_chirp(x, .82, .22, 460, 310, .20, .35)
    fade_edges(x); write_wav("distant_dog.wav", x)

    x, r = oneshot("metal_gate.wav", 2.0, 209)
    add_impact(x, .20, (220, 370, 610, 990), .34, .18)
    add_impact(x, .46, (180, 310, 570), .18, .28)
    fade_edges(x); write_wav("metal_gate.wav", x)

    x, r = oneshot("metal_clank.wav", 1.5, 210)
    add_impact(x, .18, (330, 520, 910, 1430), .42, .12)
    fade_edges(x); write_wav("metal_clank.wav", x)

    x, r = oneshot("generator_cough.wav", 2.3, 211)
    n = noise_bed(r, len(x), .02, .04)
    for i, v in enumerate(n):
        t = i / SR
        env = math.exp(-((t - 1.0) / .7) ** 2)
        x[i] += .20 * env * v + .08 * env * math.sin(TAU * 65 * t)
    fade_edges(x); write_wav("generator_cough.wav", x)

    x, r = oneshot("radio_squelch.wav", 1.15, 212)
    n = noise_bed(r, len(x), .08, .35)
    for i, v in enumerate(n):
        t = i / SR
        env = math.sin(math.pi * min(1.0, t / .18)) if t < .18 else math.exp(-(t - .18) / .35)
        x[i] += .27 * env * v
    fade_edges(x); write_wav("radio_squelch.wav", x)

    x, r = oneshot("car_pass.wav", 3.3, 213)
    n = noise_bed(r, len(x), .03, .04)
    phase = 0.0
    for i, v in enumerate(n):
        t = i / SR
        u = t / 3.3
        env = math.sin(math.pi * u) ** 1.5
        freq = 80 + 45 * (1 - u)
        phase += TAU * freq / SR
        x[i] += env * (.12 * math.sin(phase) + .10 * v)
    fade_edges(x); write_wav("car_pass.wav", x)

    x, r = oneshot("horn_distant.wav", 1.5, 214)
    for f, a in ((430, .18), (560, .12)):
        phase = 0.0
        for i in range(len(x)):
            t = i / SR
            env = math.exp(-((t - .65) / .42) ** 4)
            phase += TAU * f / SR
            x[i] += a * env * math.sin(phase)
    fade_edges(x); write_wav("horn_distant.wav", x)

    x, r = oneshot("crowd_murmur.wav", 3.0, 215)
    n = noise_bed(r, len(x), .025, .10)
    for i, v in enumerate(n):
        t = i / SR
        env = math.sin(math.pi * t / 3.0) ** 1.2
        x[i] += .17 * env * v
    add_tone(x, 190, .018, .15, .7)
    add_tone(x, 270, .014, .13, .9)
    fade_edges(x); write_wav("crowd_murmur.wav", x)

    x, r = oneshot("club_bass.wav", 2.2, 216)
    for beat in (.20, .72, 1.22, 1.72):
        add_impact(x, beat, (48, 72), .20, .10)
    fade_edges(x); write_wav("club_bass.wav", x)

    x, r = oneshot("jet_distant.wav", 4.0, 217)
    n = noise_bed(r, len(x), .012, .08)
    for i, v in enumerate(n):
        t = i / SR
        u = t / 4.0
        env = math.sin(math.pi * u) ** 1.3
        x[i] += env * (.13 * v + .05 * math.sin(TAU * (62 + 8 * u) * t))
    fade_edges(x); write_wav("jet_distant.wav", x)

    x, r = oneshot("water_splash.wav", 1.8, 218)
    n = noise_bed(r, len(x), .07, .20)
    for i, v in enumerate(n):
        t = i / SR
        env = math.exp(-((t - .38) / .30) ** 2) + .35 * math.exp(-((t - .85) / .50) ** 2)
        x[i] += .26 * env * v
    fade_edges(x); write_wav("water_splash.wav", x)

    x, r = oneshot("wave_break.wav", 2.7, 219)
    n = noise_bed(r, len(x), .05, .16)
    for i, v in enumerate(n):
        t = i / SR
        env = math.exp(-((t - 1.15) / .75) ** 2)
        x[i] += .23 * env * v
    fade_edges(x); write_wav("wave_break.wav", x)

    x, r = oneshot("wind_gust.wav", 3.0, 220)
    n = noise_bed(r, len(x), .012, .025)
    for i, v in enumerate(n):
        t = i / SR
        env = math.sin(math.pi * t / 3.0) ** 1.6
        x[i] += .26 * env * v
    fade_edges(x); write_wav("wind_gust.wav", x)

    x, r = oneshot("drip.wav", 1.5, 221)
    add_impact(x, .18, (820, 1180), .25, .10)
    add_impact(x, .44, (530, 760), .08, .22)
    add_impact(x, .72, (410, 620), .04, .30)
    fade_edges(x); write_wav("drip.wav", x)

    x, r = oneshot("stone_tick.wav", 1.4, 222)
    add_impact(x, .22, (620, 940, 1280), .20, .08)
    add_impact(x, .39, (410, 690), .06, .18)
    fade_edges(x); write_wav("stone_tick.wav", x)

    x, r = oneshot("electrical_tick.wav", 1.2, 223)
    add_impact(x, .18, (980, 1640, 2480), .12, .035)
    add_impact(x, .52, (1120, 1880, 2720), .08, .025)
    fade_edges(x); write_wav("electrical_tick.wav", x)


if __name__ == "__main__":
    make_loops()
    make_one_shots()
    print("Generated Vengeance ambience library in", OUT)
