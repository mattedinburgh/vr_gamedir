#!/usr/bin/env python3
"""
Generate additive original music cues for Vengeance: Reloaded.

Design goals:
- Add to the existing JA2/Vengeance music bank; never replace an existing cue.
- Use the next contiguous legacy music slots so the existing VS2013 selector
  discovers the tracks automatically.
- Keep cues sparse enough for tactical SFX and long combat sessions.
- Add restrained Arulco/Latin colour: nylon-string guitar, marimba-like mallets,
  cajon-like hand percussion, shaker and occasional Phrygian tension.

Generated slots:
  NOTHING Z10.ogg  - Dust Over Omerta
  NOTHING Z11.ogg  - Drassen Before Dawn
  NOTHING Z12.ogg  - San Mona 2:17 AM
  TENSOR T.ogg      - Radio Silence
  BATTLE P.ogg      - No Clean Exit II
  BATTLE Q.ogg      - Road to Meduna
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Data-Music" / "Music"
OUT.mkdir(parents=True, exist_ok=True)


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69.0) / 12.0)


def stereo(n: int) -> np.ndarray:
    return np.zeros((2, n), dtype=np.float32)


def lp(x: np.ndarray, cutoff: float) -> np.ndarray:
    return sosfilt(butter(2, cutoff, btype="low", fs=SR, output="sos"), x).astype(np.float32)


def hp(x: np.ndarray, cutoff: float) -> np.ndarray:
    return sosfilt(butter(2, cutoff, btype="high", fs=SR, output="sos"), x).astype(np.float32)


def panner(sig: np.ndarray, p: float = 0.0) -> np.ndarray:
    a = (p + 1.0) * np.pi / 4.0
    return np.vstack((sig * np.cos(a), sig * np.sin(a))).astype(np.float32)


def add(buf: np.ndarray, sig: np.ndarray, start: float, gain: float = 1.0, pan: float = 0.0) -> None:
    i = int(start * SR)
    if i >= buf.shape[1]:
        return
    if sig.ndim == 1:
        sig = panner(sig, pan)
    j = min(buf.shape[1], i + sig.shape[1])
    if j > i:
        buf[:, i:j] += sig[:, : j - i] * gain


def nylon(note: int, dur: float = 1.7, seed: int = 0) -> np.ndarray:
    f = hz(note)
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    s = np.zeros(n, np.float32)
    for k, amp in enumerate([1.0, .57, .36, .24, .15, .10, .065, .04], start=1):
        decay = .82 / (1 + .22 * (k - 1)) + .06
        phase = (seed * .731 + k * .39) % (2 * np.pi)
        s += (amp * np.sin(2 * np.pi * (f * k * (1 + .00018 * k * k)) * t + phase)
              * np.exp(-t / decay)).astype(np.float32)
    rg = np.random.default_rng(seed + 31)
    click = hp(rg.normal(0, 1, n).astype(np.float32), 2400) * np.exp(-t / .018) * .08
    body = np.sin(2 * np.pi * 92 * t).astype(np.float32) * np.exp(-t / .15) * .025
    s = lp(s + click + body, 7200)
    return s / max(.001, float(np.max(np.abs(s))))


def guitar_harmonic(note: int, dur: float = 1.6, seed: int = 0) -> np.ndarray:
    f = hz(note)
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    rg = np.random.default_rng(seed)
    s = (np.sin(2 * np.pi * 2 * f * t)
         + .38 * np.sin(2 * np.pi * 4 * f * t)
         + .18 * np.sin(2 * np.pi * 6 * f * t)).astype(np.float32)
    s *= np.exp(-t / .85)
    s += hp(rg.normal(0, .02, n).astype(np.float32), 3500) * np.exp(-t / .03)
    return s / max(.001, float(np.max(np.abs(s))))


def marimba(note: int, dur: float = 1.35, seed: int = 0) -> np.ndarray:
    f = hz(note)
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    s = np.zeros(n, np.float32)
    for ratio, amp in zip([1.0, 3.98, 9.05, 10.9], [1.0, .23, .08, .045]):
        s += (amp * np.sin(2 * np.pi * f * ratio * t + .13 * ratio)
              * np.exp(-t / (.48 / (ratio ** .18)))).astype(np.float32)
    rg = np.random.default_rng(seed + 9)
    s += lp(rg.normal(0, 1, n).astype(np.float32), 3300) * np.exp(-t / .012) * .10
    return s / max(.001, float(np.max(np.abs(s))))


def bass(note: int, dur: float = .85, seed: int = 0) -> np.ndarray:
    f = hz(note)
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    s = np.zeros(n, np.float32)
    for k, amp in [(1, 1.0), (2, .38), (3, .17), (4, .08)]:
        s += (amp * np.sin(2 * np.pi * f * k * t + k * .25)
              * np.exp(-t / (.50 / (k ** .25)))).astype(np.float32)
    rg = np.random.default_rng(seed)
    s += lp(rg.normal(0, 1, n).astype(np.float32), 1000) * np.exp(-t / .025) * .04
    s = lp(s, 1800)
    return s / max(.001, float(np.max(np.abs(s))))


def cajon_bass(seed: int = 0, dur: float = .42) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    rg = np.random.default_rng(seed)
    f = 74 - 16 * np.minimum(t / .12, 1)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase).astype(np.float32) * np.exp(-t / .14)
    noise = lp(rg.normal(0, 1, n).astype(np.float32), 700) * np.exp(-t / .045)
    return body * .85 + noise * .16


def cajon_slap(seed: int = 0, dur: float = .22) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    rg = np.random.default_rng(seed)
    noise = hp(rg.normal(0, 1, n).astype(np.float32), 1300) * np.exp(-t / .035)
    tone = (np.sin(2 * np.pi * 240 * t) + .5 * np.sin(2 * np.pi * 410 * t)).astype(np.float32)
    return noise * .42 + tone * np.exp(-t / .055) * .22


def shaker(seed: int = 0, dur: float = .16) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    rg = np.random.default_rng(seed)
    return hp(rg.normal(0, 1, n).astype(np.float32), 4800) * np.exp(-t / .038) * .20


def wood(seed: int = 0, dur: float = .20, pitch: float = 980) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    s = np.sin(2 * np.pi * pitch * t) + .55 * np.sin(2 * np.pi * pitch * 1.62 * t)
    return (s * np.exp(-t / .055)).astype(np.float32)


def tom(seed: int = 0, dur: float = .5, pitch: float = 92) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    rg = np.random.default_rng(seed)
    f = pitch + 38 * np.exp(-t / .035)
    phase = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(phase).astype(np.float32) * np.exp(-t / .15)
    s += lp(rg.normal(0, 1, n).astype(np.float32), 900) * np.exp(-t / .025) * .08
    return s


def brush(seed: int = 0, dur: float = .32) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    rg = np.random.default_rng(seed)
    return hp(rg.normal(0, 1, n).astype(np.float32), 1800) * np.exp(-t / .11) * .08


def pad(note: int, dur: float, brightness: float = .5) -> np.ndarray:
    f = hz(note)
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    s = (.72 * np.sin(2 * np.pi * f * t)
         + .18 * np.sin(2 * np.pi * f * 2 * t + .4)
         + .10 * np.sin(2 * np.pi * f * .5 * t + .9)).astype(np.float32)
    s *= (.76 + .24 * np.sin(2 * np.pi * .055 * t + note * .17)).astype(np.float32)
    env = np.ones(n, np.float32)
    a, r = min(n, int(.8 * SR)), min(n, int(1.2 * SR))
    env[:a] *= np.linspace(0, 1, a, dtype=np.float32)
    env[-r:] *= np.linspace(1, 0, r, dtype=np.float32)
    return lp(s * env, 800 + 2800 * brightness)


def air(dur: float, seed: int = 0, cut: float = 1100) -> np.ndarray:
    n = int(dur * SR)
    rg = np.random.default_rng(seed)
    x = lp(rg.normal(0, 1, n).astype(np.float32), cut)
    e = np.sin(np.pi * np.linspace(0, 1, n, dtype=np.float32)) ** 2
    return x * e * .10


def radio_grit(dur: float, seed: int = 0) -> np.ndarray:
    n = int(dur * SR)
    rg = np.random.default_rng(seed)
    t = np.arange(n, dtype=np.float32) / SR
    x = hp(lp(rg.normal(0, 1, n).astype(np.float32), 4200), 480)
    gate = (np.sin(2 * np.pi * 7.3 * t) > .83).astype(np.float32)
    return x * (.025 + .035 * gate)


def strum(buf: np.ndarray, chord, start: float, vel: float = .08, pan: float = 0.0,
          down: bool = True, seed: int = 0) -> None:
    notes = list(chord if down else reversed(chord))
    for j, note in enumerate(notes):
        jitter = np.random.default_rng(seed + j).uniform(-.006, .006)
        add(buf, nylon(note, 1.65, seed + j), start + j * .025 + jitter,
            vel * (.96 - .06 * j), pan + (j - (len(notes) - 1) / 2) * .04)


def arp(buf: np.ndarray, notes, start: float, beat: float, pattern,
        vel: float = .055, pan: float = 0.0, seed: int = 0) -> None:
    for j, idx in enumerate(pattern):
        add(buf, nylon(notes[idx % len(notes)], 1.25, seed + j),
            start + j * (beat / 2), vel, pan + (.12 if j % 2 else -.12))


def master(buf: np.ndarray, reverb: float = .16, grit: float = 0.0) -> np.ndarray:
    dry = buf.copy()
    for delay, gain in [(.071, .20), (.109, .14), (.173, .10), (.263, .065), (.401, .035)]:
        k = int(delay * SR)
        buf[:, k:] += dry[:, :-k] * gain * reverb / .16
    if grit:
        buf = np.tanh(buf * (1 + grit * 2)) / np.tanh(1 + grit * 2)
    k = int(.013 * SR)
    left, right = buf[0].copy(), buf[1].copy()
    buf[0, k:] += right[:-k] * .025
    buf[1, k:] += left[:-k] * .025
    buf[0], buf[1] = hp(buf[0], 28), hp(buf[1], 28)
    buf = np.tanh(buf * 1.18).astype(np.float32)
    peak = float(np.max(np.abs(buf)))
    if peak:
        buf *= np.float32(.90 / peak)
    return buf


def loop_tail(buf: np.ndarray, sec: float = 2.2) -> np.ndarray:
    n = min(int(sec * SR), buf.shape[1] // 8)
    f = np.linspace(0, 1, n, dtype=np.float32)
    buf[:, -n:] = buf[:, -n:] * (1 - f) + buf[:, :n] * f
    return buf


def write_wav(path: Path, buf: np.ndarray) -> None:
    pcm = (np.clip(buf.T, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def render_omerta():
    bpm, bars = 80, 32
    beat = 60 / bpm
    dur = bars * 4 * beat
    b = stereo(int(dur * SR))
    for n, g, p in [(38, .050, -.25), (45, .032, .25), (50, .018, 0)]:
        add(b, pad(n, dur, .20), 0, g, p)
    chords = [[50,57,62,65], [48,55,60,64], [46,53,58,62], [48,55,60,64]]
    roots = [38,36,34,36]
    for bar in range(bars):
        t, sec = bar * 4 * beat, bar // 8
        if sec >= 1 or bar % 4 == 0:
            strum(b, chords[bar % 4], t + .05, .040 + sec * .005, -.18, seed=1000+bar)
        if sec in (1,2,3) and bar % 2 == 0:
            arp(b, chords[bar % 4], t + 1.8*beat, beat, [0,1,2,3], .025, .20, 1300+bar)
        if bar % 2 == 0:
            add(b, bass(roots[bar % 4], seed=bar), t, .038, -.05)
        if bar in [3,6,10,14,17,22,26,29]:
            motif = [62,65,64,60] if bar % 2 else [57,60,62,57]
            for j,n in enumerate(motif):
                add(b, marimba(n, .95, bar*10+j), t + (1+j*.55)*beat, .030, .25 if j%2 else .05)
        if sec >= 2:
            add(b, cajon_bass(bar), t, .033)
            add(b, cajon_slap(bar), t + 2*beat, .024, .06)
            for q in [1.5, 3.5]:
                add(b, shaker(bar*10+int(q*2)), t+q*beat, .020, .35 if q<2 else -.3)
        if bar in [7,15,23]:
            add(b, air(5, bar, 750), t+1.5*beat, .13, .5 if bar%2 else -.5)
    return master(loop_tail(b, 2.5), .13, .03)


def render_drassen():
    bpm, bars = 84, 32
    beat = 60 / bpm
    dur = bars * 4 * beat
    b = stereo(int(dur * SR))
    for n,g,p in [(43,.043,-.2),(50,.025,.2),(55,.015,0)]:
        add(b, pad(n,dur,.28), 0,g,p)
    chords=[[55,58,62,67],[53,57,60,65],[51,55,58,63],[53,57,60,65]]
    roots=[43,41,39,41]
    for bar in range(bars):
        t,sec=bar*4*beat,bar//8
        arp(b,chords[bar%4],t+.05,beat,[0,2,1,3,2,1,3,2],.029+.004*(sec>1),-.20,2100+bar)
        if bar%2==0:
            add(b,bass(roots[bar%4],seed=bar),t,.040,-.05)
        motif=[67,70,74,72,67,65]
        if bar%2==1:
            for j,n in enumerate(motif):
                if (bar+j)%3:
                    add(b,marimba(n,.80,bar*20+j),t+(j*.5+.5)*beat,.026,.24 if j%2 else .08)
        if sec>=1:
            add(b,cajon_bass(200+bar),t,.027)
            add(b,cajon_slap(200+bar),t+2*beat,.019,.05)
            for e in range(4):
                add(b,shaker(3000+bar*4+e),t+(e+.5)*beat,.015,.35 if e%2 else -.35)
        if bar in [8,16,24]:
            for j,n in enumerate([79,74,70]):
                add(b,guitar_harmonic(n,1.8,500+bar+j),t+j*.65,.027,.45-j*.3)
            add(b,air(4,500+bar,1300),t,.10,-.5)
    return master(loop_tail(b,2.5),.15,.02)


def render_sanmona():
    bpm,bars=92,36
    beat=60/bpm
    dur=bars*4*beat
    b=stereo(int(dur*SR))
    for n,g,p in [(45,.038,-.18),(52,.020,.18),(57,.010,0)]:
        add(b,pad(n,dur,.18),0,g,p)
    prog=[[57,60,64,69],[55,59,62,67],[53,57,60,65],[52,56,59,64]]
    roots=[45,43,41,40]
    for bar in range(bars):
        t=bar*4*beat
        if bar%4!=2:
            strum(b,prog[bar%4],t+.45*beat,.034,-.28,seed=4000+bar)
            strum(b,prog[bar%4],t+2.55*beat,.027,.15,False,4200+bar)
        root=roots[bar%4]
        for q,n in enumerate([root,root+7,root+10,root+7]):
            add(b,bass(n,.62,bar*8+q),t+q*beat,.038,-.05)
        add(b,cajon_bass(5000+bar),t,.038)
        add(b,cajon_slap(5100+bar),t+2*beat,.030,.08)
        for q in [1,3]:
            add(b,brush(5200+bar*4+q),t+q*beat,.55,.15 if q==1 else -.2)
        for e in range(8):
            if (bar+e)%5!=0:
                add(b,shaker(5300+bar*8+e),t+e*.5*beat,.012,.4 if e%2 else -.4)
        if bar in [2,6,10,14,19,23,28,32]:
            motif=[69,68,64,60] if bar%2 else [64,65,64,59]
            for j,n in enumerate(motif):
                add(b,marimba(n,.95,5400+bar+j),t+(1+j*.62)*beat,.026,.35 if j%2 else .05)
        if bar in [8,17,26,35]:
            for j,ch in enumerate(prog):
                strum(b,ch,t+j*.75*beat,.030,-.12+.08*j,seed=5600+bar+j)
            add(b,air(3.5,5700+bar,900),t,.10,.55)
    return master(loop_tail(b,2.3),.11,.045)


def render_tensor():
    bpm,bars=78,32
    beat=60/bpm
    dur=bars*4*beat
    b=stereo(int(dur*SR))
    for n,g,p in [(40,.052,-.22),(47,.026,.2),(41,.020,.28),(52,.010,-.3)]:
        add(b,pad(n,dur,.12),0,g,p)
    pulse=[40,40,41,40,47,41,38,40]
    for bar in range(bars):
        t,sec=bar*4*beat,bar//8
        for e in range(8):
            if (e+bar)%5!=1:
                add(b,bass(pulse[(bar+e)%8]-12,.32,6000+bar*8+e),
                    t+e*.5*beat,.027+.005*sec,-.08)
        for off in [1.25,2.75]:
            if (bar+int(off*4))%3:
                add(b,wood(6100+bar,pitch=900+90*(bar%4)),t+off*beat,.020,.55 if off<2 else -.55)
        if bar%2:
            add(b,radio_grit(4*beat,6200+bar),t,.45)
        if bar in [5,11,18,22,27,30]:
            for j,n in enumerate([64,65,59,64]):
                add(b,guitar_harmonic(n,1.7,6300+bar+j),t+(j*.7+.5)*beat,.018,.5-j*.32)
        if sec>=2:
            add(b,cajon_bass(6400+bar),t,.024)
            if bar%2==0:
                add(b,cajon_slap(6500+bar),t+2*beat,.018,.1)
        if bar in [7,15,23]:
            add(b,air(6,6600+bar,650),t+beat,.20,-.55 if bar%2 else .55)
    return master(loop_tail(b,2.8),.18,.055)


def render_battle():
    bpm,bars=108,40
    beat=60/bpm
    dur=bars*4*beat
    b=stereo(int(dur*SR))
    for n,g,p in [(38,.034,-.2),(45,.019,.2),(50,.010,0)]:
        add(b,pad(n,dur,.14),0,g,p)
    basspat=[38,38,41,38,45,43,41,37]
    motif=[62,65,61,62,69,67,65,61]
    for bar in range(bars):
        t,sec=bar*4*beat,bar//8
        for e,n in enumerate(basspat):
            if (bar+e)%7!=2:
                add(b,bass(n,.38,7000+bar*8+e),t+e*.5*beat,.037,-.06)
        add(b,cajon_bass(7100+bar),t,.052)
        add(b,tom(7200+bar,pitch=86),t+2*beat,.036,-.20)
        if bar%2==0:
            add(b,cajon_slap(7300+bar),t+2.5*beat,.028,.18)
        for e in [1,3,5,7]:
            if (bar+e)%4:
                add(b,shaker(7400+bar*8+e),t+e*.5*beat,.014,.42 if e%4==1 else -.42)
        if bar%3!=2:
            for j,n in enumerate(motif):
                if j in [0,2,4,7] or (bar+j)%5==0:
                    add(b,marimba(n,.62,7500+bar*8+j),t+j*.5*beat,.024,.30 if j%2 else -.10)
        if bar%4 in (1,3):
            arp(b,[50,57,62,65],t+.10,beat,[0,1,2,1,3,2,1,0],.018+.004*(sec>=3),-.30,7600+bar)
        if bar in [8,16,24,32]:
            chords=[[50,57,62,65],[48,55,60,64],[46,53,58,62],[49,56,61,64]]
            for j,ch in enumerate(chords):
                strum(b,ch,t+j*.5*beat,.028,-.15+.08*j,seed=7700+bar+j)
            add(b,air(3.5,7800+bar,1200),t,.10,.5)
        if sec>=4 and bar%2:
            add(b,tom(7900+bar,pitch=112),t+3.25*beat,.027,.25)
    return master(loop_tail(b,2.0),.10,.065)


def render_meduna():
    bpm,bars=98,40
    beat=60/bpm
    dur=bars*4*beat
    b=stereo(int(dur*SR))
    for n,g,p in [(37,.045,-.24),(44,.022,.22),(49,.012,0),(50,.008,.3)]:
        add(b,pad(n,dur,.16),0,g,p)
    roots=[37,37,38,44,42,38,37,49]
    for bar in range(bars):
        t,sec=bar*4*beat,bar//8
        for e in range(8):
            n=roots[(bar+e)%len(roots)]
            if (bar*2+e)%6!=0:
                add(b,bass(n,.46,8100+bar*8+e),t+e*.5*beat,.034,-.05)
        for off in [0,1.5,2.0,3.25]:
            add(b,wood(8200+bar+int(off*10),pitch=760+80*((bar+int(off))%4)),
                t+off*beat,.018,.45 if off%2 else -.35)
        add(b,tom(8300+bar,pitch=72),t,.038,-.20)
        if bar%2==1:
            add(b,cajon_slap(8400+bar),t+2*beat,.019,.15)
        if bar%4==2:
            for j,n in enumerate([61,60,58,56]):
                add(b,nylon(n,1.0,8500+bar+j),t+(1+j*.48)*beat,.022,-.28+.18*j)
        if bar in [5,9,13,18,22,27,31,35,38]:
            for j,n in enumerate([61,65,64,58]):
                add(b,marimba(n,.75,8600+bar+j),t+(j*.58+.6)*beat,.020,.35 if j%2 else -.08)
        if bar in [7,15,23,31]:
            add(b,air(5,8700+bar,800),t+beat,.15,.55 if bar%2 else -.55)
        if sec>=3 and bar%2==0:
            add(b,radio_grit(4*beat,8800+bar),t,.28)
    return master(loop_tail(b,2.1),.14,.075)


TRACKS = [
    ("NOTHING Z10.ogg", render_omerta, "Dust Over Omerta"),
    ("NOTHING Z11.ogg", render_drassen, "Drassen Before Dawn"),
    ("NOTHING Z12.ogg", render_sanmona, "San Mona 2:17 AM"),
    ("TENSOR T.ogg", render_tensor, "Radio Silence"),
    ("BATTLE P.ogg", render_battle, "No Clean Exit II"),
    ("BATTLE Q.ogg", render_meduna, "Road to Meduna"),
]


def encode_ogg(audio: np.ndarray, destination: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to encode OGG assets")
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "track.wav"
        write_wav(wav, audio)
        subprocess.run(
            [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav),
             "-c:a", "libvorbis", "-q:a", "6", str(destination)],
            check=True,
        )


def main() -> None:
    created = []
    skipped = []
    for filename, renderer, title in TRACKS:
        dest = OUT / filename
        if dest.exists():
            skipped.append(filename)
            print(f"KEEP existing: {filename}")
            continue
        print(f"GENERATE {filename} — {title}")
        encode_ogg(renderer(), dest)
        created.append(filename)
    print(f"Created {len(created)} additive cue(s): {created}")
    print(f"Preserved {len(skipped)} existing cue(s): {skipped}")


if __name__ == "__main__":
    main()
