#!/usr/bin/env python3
"""
Generate the first native Vengeance custom A3 art pack.

No legacy pixels are recoloured.  Every B1TC frame is drawn from scratch here.
The pack deliberately preserves JA2 tile-type frame counts so existing map
sub-indices remain valid.  Base terrain and visual-only decoration slots are
replaced; structure/JSD-bearing walls, trees and doors remain authored until
their visual/structure identities are explicitly decoupled.

B1TC v1 layout:
  magic "B1TC", u16 version, u16 frame count
  frame directory: i16 x, i16 y, u16 w, u16 h, u32 offset, u32 rgba_bytes
  raw RGBA pixels
"""
from __future__ import annotations

import math
import random
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Data-Maps-Tiles" / "Tilesets" / "38"
OUT.mkdir(parents=True, exist_ok=True)

RGBA = tuple[int, int, int, int]


class Canvas:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self.p = bytearray(w * h * 4)

    def put(self, x: int, y: int, c: RGBA):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 4
            self.p[i:i+4] = bytes(c)

    def get(self, x: int, y: int) -> RGBA:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 4
            return tuple(self.p[i:i+4])  # type: ignore
        return (0, 0, 0, 0)

    def blend(self, x: int, y: int, c: RGBA):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        a = c[3] / 255.0
        old = self.get(x, y)
        oa = old[3] / 255.0
        outa = a + oa * (1.0 - a)
        if outa <= 0:
            return
        out = []
        for k in range(3):
            v = (c[k] * a + old[k] * oa * (1.0 - a)) / outa
            out.append(max(0, min(255, int(v))))
        self.put(x, y, (out[0], out[1], out[2], max(0, min(255, int(outa * 255)))))

    def line(self, x0: int, y0: int, x1: int, y1: int, c: RGBA, width: int = 1):
        dx = abs(x1-x0); sx = 1 if x0 < x1 else -1
        dy = -abs(y1-y0); sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            r = max(0, width // 2)
            for yy in range(y0-r, y0+r+1):
                for xx in range(x0-r, x0+r+1):
                    self.blend(xx, yy, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy; x0 += sx
            if e2 <= dx:
                err += dx; y0 += sy

    def ellipse(self, cx: int, cy: int, rx: int, ry: int, c: RGBA):
        if rx <= 0 or ry <= 0:
            return
        for y in range(cy-ry, cy+ry+1):
            fy = (y-cy) / float(ry)
            if abs(fy) > 1:
                continue
            span = int(rx * math.sqrt(max(0.0, 1.0 - fy*fy)))
            for x in range(cx-span, cx+span+1):
                self.blend(x, y, c)

    def polygon(self, pts: list[tuple[int,int]], c: RGBA):
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0,min(ys)), min(self.h-1,max(ys))+1):
            xs = []
            for i in range(len(pts)):
                x1,y1 = pts[i]
                x2,y2 = pts[(i+1)%len(pts)]
                if y1 == y2:
                    continue
                if y >= min(y1,y2) and y < max(y1,y2):
                    x = x1 + (y-y1) * (x2-x1) / float(y2-y1)
                    xs.append(x)
            xs.sort()
            for i in range(0, len(xs)-1, 2):
                xa = max(0, int(math.ceil(xs[i])))
                xb = min(self.w-1, int(math.floor(xs[i+1])))
                for x in range(xa, xb+1):
                    self.blend(x, y, c)


def clamp(v: int) -> int:
    return max(0, min(255, v))


def shade(c: tuple[int,int,int], d: int, a: int = 255) -> RGBA:
    return (clamp(c[0]+d), clamp(c[1]+d), clamp(c[2]+d), a)


def diamond_contains(x: int, y: int, w: int = 40, h: int = 20) -> bool:
    cx = (w-1) / 2.0
    cy = (h-1) / 2.0
    return abs(x-cx)/(w/2.0) + abs(y-cy)/(h/2.0) <= 1.0


def ground_frame(seed: int, kind: str) -> tuple[int,int,int,int,bytes]:
    rng = random.Random(seed)
    w,h = 40,20
    cv = Canvas(w,h)
    palettes = {
        "dry":      ((150,111,58),(184,141,78),(110,76,43)),
        "soil":     ((119,82,48),(150,105,61),(83,58,39)),
        "grass":    ((74,112,42),(112,142,58),(48,78,34)),
        "lush":     ((55,104,38),(92,139,53),(36,69,31)),
        "scrub":    ((84,105,44),(127,133,59),(62,74,38)),
        "field":    ((107,77,43),(139,101,55),(68,58,36)),
        "trail":    ((140,103,61),(171,132,78),(94,67,44)),
        "water":    ((42,103,116),(77,139,146),(28,71,91)),
        "deepwater":((27,69,91),(52,104,119),(18,49,70)),
    }
    base,hi,lo = palettes[kind]

    for y in range(h):
        for x in range(w):
            if not diamond_contains(x,y,w,h):
                continue
            # directional light + deterministic texture
            light = int((9-y) * 0.65 + (20-x) * 0.10)
            noise = rng.randint(-9,9)
            cc = (
                clamp(base[0]+light+noise),
                clamp(base[1]+light+noise),
                clamp(base[2]+light+noise),
                255,
            )
            cv.put(x,y,cc)

    # border definition
    cv.line(20,0,39,9,shade(lo,-8,210))
    cv.line(39,9,20,19,shade(lo,-12,220))
    cv.line(20,19,0,9,shade(lo,-6,210))

    if kind in ("grass","lush","scrub"):
        n = {"grass":42,"lush":62,"scrub":34}[kind]
        for _ in range(n):
            x=rng.randrange(3,37); y=rng.randrange(3,17)
            if not diamond_contains(x,y):
                continue
            col = shade(hi, rng.randint(-12,12), rng.randint(150,230))
            cv.line(x,y,x+rng.choice([-1,0,1]),max(0,y-rng.randint(1,3)),col)
        if kind == "scrub":
            for _ in range(7):
                x=rng.randrange(5,35); y=rng.randrange(5,16)
                if diamond_contains(x,y):
                    cv.ellipse(x,y,2,1,shade((107,83,48),rng.randint(-8,8),220))

    elif kind == "field":
        for k in range(-16,25,7):
            cv.line(max(1,k),18,min(39,k+28),4,shade(lo,-4,210),1)
            cv.line(max(1,k+2),18,min(39,k+30),4,shade(hi,-6,145),1)

    elif kind == "trail":
        for ofs in (-4,4):
            cv.line(6+ofs,14,28+ofs,3,shade(lo,-12,185),2)
            cv.line(8+ofs,14,30+ofs,3,shade(hi,-18,80),1)
        for _ in range(8):
            x=rng.randrange(6,34); y=rng.randrange(5,15)
            if diamond_contains(x,y):
                cv.ellipse(x,y,1,1,shade(lo,-5,180))

    elif kind in ("water","deepwater"):
        for yy in (5,9,13):
            phase=rng.randint(-3,3)
            cv.line(7+phase,yy,19+phase,yy-2,shade(hi,6,105))
            cv.line(21-phase,yy+1,33-phase,yy-1,shade(hi,1,90))
        if kind == "water":
            for _ in range(5):
                x=rng.randrange(8,33); y=rng.randrange(5,15)
                if diamond_contains(x,y):
                    cv.ellipse(x,y,2,1,(73,116,49,170))
                    cv.put(x,y,shade((142,167,89),5,190))
    else:
        for _ in range(16):
            x=rng.randrange(4,36); y=rng.randrange(3,17)
            if diamond_contains(x,y):
                col = hi if rng.random() < .45 else lo
                cv.ellipse(x,y,1,1,shade(col,rng.randint(-15,15),rng.randint(90,190)))

    return (0,0,w,h,bytes(cv.p))


def transparent_frame(w: int, h: int, ox: int, oy: int) -> tuple[Canvas, tuple[int,int,int,int]]:
    return Canvas(w,h),(ox,oy,w,h)


def crop_overlay(seed: int) -> tuple[int,int,int,int,bytes]:
    rng=random.Random(seed)
    w,h=40,34; ox,oy=0,-14
    cv=Canvas(w,h)
    # 3 diagonal cultivated rows of small broadleaf crops
    for row in range(3):
        y0=29-row*6
        for n in range(6):
            x=4+n*6+row*2+rng.randint(-1,1)
            y=y0-n//2+rng.randint(-1,1)
            cv.line(x,y,x,y-6,(69,99,36,230))
            cv.ellipse(x-2,y-5,3,1,(73+rng.randint(-8,8),127+rng.randint(-8,8),48,235))
            cv.ellipse(x+2,y-4,3,1,(91,143+rng.randint(-8,8),53,230))
    return ox,oy,w,h,bytes(cv.p)


def ruts_overlay(seed: int) -> tuple[int,int,int,int,bytes]:
    rng=random.Random(seed)
    w,h=40,20; cv=Canvas(w,h)
    for ofs in (-4,4):
        cv.line(5+ofs,15,27+ofs,3,(68,48,34,185),2)
        if seed % 2:
            cv.line(9+ofs,13,23+ofs,5,(46,89,101,145),1)
    for _ in range(4):
        x=rng.randrange(8,33); y=rng.randrange(6,15)
        cv.ellipse(x,y,2,1,(52,92,98,95))
    return 0,0,w,h,bytes(cv.p)


def weeds_overlay(seed: int) -> tuple[int,int,int,int,bytes]:
    rng=random.Random(seed)
    w,h=44,36; ox,oy=-2,-16; cv=Canvas(w,h)
    for _ in range(26):
        x=rng.randrange(3,w-3); y=rng.randrange(19,h-2)
        height=rng.randrange(4,14)
        col=rng.choice([(52,91,35,230),(72,115,42,235),(94,129,48,225),(112,104,48,220)])
        cv.line(x,y,x+rng.choice([-2,-1,0,1,2]),y-height,col)
        if rng.random()<.28:
            cv.put(x,y-height,(163,117,48,230))
    return ox,oy,w,h,bytes(cv.p)


def rocks_overlay(seed: int) -> tuple[int,int,int,int,bytes]:
    rng=random.Random(seed)
    w,h=40,24; ox,oy=0,-4; cv=Canvas(w,h)
    for _ in range(7):
        x=rng.randrange(5,35); y=rng.randrange(10,21)
        rx=rng.randrange(2,5); ry=max(1,rx//2)
        base=rng.choice([(101,94,76),(120,113,91),(83,82,69)])
        cv.ellipse(x+1,y+1,rx,ry,(28,26,23,80))
        cv.ellipse(x,y,rx,ry,(*base,235))
        cv.line(x-rx+1,y-1,x+1,y-ry,shade(base,24,155))
    return ox,oy,w,h,bytes(cv.p)


def irrigation_overlay(seed: int) -> tuple[int,int,int,int,bytes]:
    rng=random.Random(seed)
    w,h=40,20; cv=Canvas(w,h)
    # wet diagonal ditch, transparent outside
    cv.line(3,15,31,1,(51,77,46,150),4)
    cv.line(4,14,32,2,(44,104,119,205),2)
    cv.line(5,13,31,3,(94,145,148,95),1)
    for _ in range(6):
        x=rng.randrange(5,34); y=max(1,min(18,15-(x-3)//2+rng.randint(-2,2)))
        cv.line(x,y,x+rng.choice([-1,0,1]),y-rng.randrange(2,5),(65,113,46,210))
    return 0,0,w,h,bytes(cv.p)


def wood_overlay(seed: int) -> tuple[int,int,int,int,bytes]:
    rng=random.Random(seed)
    w,h=48,30; ox,oy=-4,-10; cv=Canvas(w,h)
    count=4+rng.randrange(4)
    for n in range(count):
        y=20-n*2
        x=5+rng.randrange(4)
        col=rng.choice([(112,75,43),(93,62,38),(133,91,49)])
        cv.line(x,y,38+rng.randrange(5),y-10+rng.randrange(3),(*col,235),2)
        cv.line(x+1,y-1,34,y-9,shade(col,22,130),1)
    if seed%3==0:
        cv.polygon([(7,19),(17,14),(27,17),(17,22)],(105,76,49,220))
    return ox,oy,w,h,bytes(cv.p)


def prop_overlay(seed: int) -> tuple[int,int,int,int,bytes]:
    rng=random.Random(seed)
    w,h=48,48; ox,oy=-4,-28; cv=Canvas(w,h)
    kind=seed%10
    shadow=(20,18,16,80)
    if kind in (0,1):  # crates
        x=10; y=26
        cv.polygon([(x,y),(x+12,y-6),(x+23,y-1),(x+11,y+6)],shadow)
        cv.polygon([(x,y-8),(x+12,y-14),(x+23,y-9),(x+11,y-3)],(132,91,49,240))
        cv.polygon([(x,y-8),(x+11,y-3),(x+11,y+8),(x,y+3)],(99,65,40,240))
        cv.polygon([(x+11,y-3),(x+23,y-9),(x+23,y+2),(x+11,y+8)],(112,75,44,240))
        cv.line(x+3,y-7,x+14,y-12,(178,129,73,150))
    elif kind in (2,3):  # barrels
        x=20; y=27
        body=(154,58,43,240) if kind==2 else (50,84,136,240)
        cv.ellipse(x,y-12,6,3,shade(body[:3],18,240))
        cv.polygon([(14,y-12),(26,y-12),(26,y+3),(14,y+3)],body)
        cv.ellipse(x,y+3,6,3,shade(body[:3],-22,235))
        for yy in (y-8,y-1): cv.line(14,yy,26,yy,shade(body[:3],-35,180))
    elif kind==4: # sacks
        for yy in range(2):
            for xx in range(3):
                x=9+xx*9+yy*3; y=28-yy*6
                cv.ellipse(x,y,6,3,(151,124,82,235))
                cv.line(x-4,y-1,x+3,y-2,(187,156,105,130))
    elif kind==5: # tyres
        for n in range(3):
            x=13+n*7; y=30-n*3
            cv.ellipse(x,y,7,4,(39,39,37,235))
            cv.ellipse(x,y,3,2,(0,0,0,0))
    elif kind==6: # pallet
        for n in range(5):
            cv.line(6+n*7,26-n//2,31+n*2,16-n//2,(124,88,51,235),2)
    elif kind==7: # pump
        cv.polygon([(19,31),(29,31),(31,35),(17,35)],(110,105,87,235))
        cv.line(24,31,24,12,(55,91,70,245),4)
        cv.ellipse(24,12,4,3,(65,104,79,245))
        cv.line(27,17,36,19,(55,91,70,235),2)
    elif kind==8: # small tank
        cv.ellipse(24,24,13,6,(134,137,126,230))
        cv.polygon([(11,18),(37,18),(37,25),(11,25)],(118,122,115,230))
        cv.line(16,28,16,34,(87,76,59,230),2); cv.line(32,28,32,34,(87,76,59,230),2)
    else: # windmill/utility landmark
        cv.line(24,36,24,12,(92,74,51,240),2)
        cv.line(15,36,24,12,(92,74,51,220),1); cv.line(33,36,24,12,(92,74,51,220),1)
        cv.ellipse(24,11,3,3,(116,94,63,240))
        for a in range(0,360,45):
            x=24+int(math.cos(math.radians(a))*10)
            y=11+int(math.sin(math.radians(a))*10)
            cv.line(24,11,x,y,(129,104,69,220))
    return ox,oy,w,h,bytes(cv.p)


def junk_overlay(seed: int) -> tuple[int,int,int,int,bytes]:
    # rotate through the hand-authored prop family with a little extra ground clutter
    ox,oy,w,h,data=prop_overlay(seed+20)
    cv=Canvas(w,h); cv.p[:] = data
    rng=random.Random(seed+991)
    for _ in range(8):
        x=rng.randrange(5,w-5); y=rng.randrange(max(5,h-12),h-2)
        cv.line(x,y,x+rng.randrange(-4,5),y+rng.randrange(-2,3),(74,58,42,135))
    return ox,oy,w,h,bytes(cv.p)


def repeat_frames(builder, count: int, seed_base: int) -> list[tuple[int,int,int,int,bytes]]:
    return [builder(seed_base+i) for i in range(count)]


def write_b1tc(path: Path, frames: list[tuple[int,int,int,int,bytes]]):
    header = bytearray(b"B1TC")
    header += struct.pack("<HH",1,len(frames))
    directory = bytearray()
    payload = bytearray()
    offset = 8 + 16*len(frames)
    for ox,oy,w,h,pix in frames:
        expected=w*h*4
        if len(pix)!=expected:
            raise ValueError(f"{path.name}: pixel data {len(pix)} != {expected}")
        directory += struct.pack("<hhHHII",ox,oy,w,h,offset,len(pix))
        payload += pix
        offset += len(pix)
    path.write_bytes(bytes(header+directory+payload))


BASE = [
    ("VR_A3_TEX1.b1tc",35,"dry",1000),
    ("VR_A3_TEX2.b1tc",35,"soil",2000),
    ("VR_A3_TEX3.b1tc",35,"grass",3000),
    ("VR_A3_TEX4.b1tc",35,"lush",4000),
    ("VR_A3_TEX5.b1tc",35,"scrub",5000),
    ("VR_A3_TEX6.b1tc",37,"field",6000),
    ("VR_A3_TEX7.b1tc",49,"trail",7000),
    ("VR_A3_WATER.b1tc",50,"water",8000),
    ("VR_A3_DEEPWATER.b1tc",37,"deepwater",9000),
]

for name,count,kind,seed in BASE:
    write_b1tc(OUT/name,[ground_frame(seed+i,kind) for i in range(count)])

write_b1tc(OUT/"VR_A3_CROPS.b1tc", repeat_frames(crop_overlay,10,11000))
write_b1tc(OUT/"VR_A3_RUTS.b1tc", repeat_frames(ruts_overlay,10,12000))
write_b1tc(OUT/"VR_A3_PROPS.b1tc", repeat_frames(prop_overlay,10,13000))
write_b1tc(OUT/"VR_A3_ROCKS.b1tc", repeat_frames(rocks_overlay,10,14000))
write_b1tc(OUT/"VR_A3_WOOD.b1tc", repeat_frames(wood_overlay,10,15000))
write_b1tc(OUT/"VR_A3_WEEDS.b1tc", repeat_frames(weeds_overlay,10,16000))
write_b1tc(OUT/"VR_A3_IRRIGATION.b1tc", repeat_frames(irrigation_overlay,10,17000))
write_b1tc(OUT/"VR_A3_JUNK.b1tc", repeat_frames(junk_overlay,10,18000))

manifest = """VR A3 CUSTOM ART PACK V1
========================
Generated from scratch by Tools/GenerateCustomA3Tiles.py.

Base terrain frame counts intentionally match TileDat.cpp:
  VR_A3_TEX1      35  warm dry soil
  VR_A3_TEX2      35  compact brown soil
  VR_A3_TEX3      35  low green grass
  VR_A3_TEX4      35  lush tropical grass
  VR_A3_TEX5      35  mixed scrub
  VR_A3_TEX6      37  cultivated field soil
  VR_A3_TEX7      49  rutted rural trail
  VR_A3_WATER     50  shallow tropical water
  VR_A3_DEEPWATER 37  deep water

Visual-only 10-frame families:
  CROPS, RUTS, PROPS, ROCKS, WOOD, WEEDS, IRRIGATION, JUNK

These B1TC files replace pixels in A3 only through the sector visual profile.
Legacy walls, trees, doors and other JSD-bearing structure families are retained
until their pixel identity and collision/JSD identity are deliberately separated.
"""
(OUT/"VR_A3_CUSTOM_PACK_README.txt").write_text(manifest,encoding="utf-8")
print("Generated",len(list(OUT.glob("VR_A3_*.b1tc"))),"B1TC files in",OUT)
