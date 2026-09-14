#!/usr/bin/env python3
"""
San Mona C5 graphics-only remaster generator.

Invariant: this tool NEVER edits map DAT files, JSD structure metadata, XML mappings,
or gameplay code. It reads existing STI art and emits same-name B1TC siblings into
Tilesets/18. Vengeance keeps the original logical STI/JSD identity and therefore
collision, LOS, penetration, destruction, map placement and scripting.

B1TC v1:
  magic 'B1TC', u16 version, u16 frame_count
  repeated frame directory <hhHHII>: offsetX, offsetY, width, height, dataOffset, dataLength
  raw RGBA8 pixels
"""
from __future__ import annotations

from pathlib import Path
import json, math, random, struct
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Data-Maps-Tiles" / "Tilesets" / "18"
PREVIEW = ROOT / "san_mona_preview"

STCI_ETRLE_COMPRESSED = 0x0020
STCI_ZLIB_COMPRESSED = 0x0010
STCI_INDEXED = 0x0008

# Output basename -> existing repo STI used as visual source.
# The logical output name is the one C5/tileset 18 already requests.
SOURCES = {
    "Cobble_Road": ("Data-Maps-Tiles/Tilesets/18/Cobble_Road.sti", "road"),
    "Cobble_Road_Pieces": ("Data-Maps-Tiles/Tilesets/18/Cobble_Road_Pieces.sti", "road"),
    "Pave_b": ("Data-Maps-Tiles/Tilesets/18/Pave_b.sti", "paving"),
    "Streetlamp": ("Data-Maps-Tiles/Tilesets/18/Streetlamp.sti", "metal"),
    "BUILD_24": ("Data-Maps-Tiles/Tilesets/51/BUILD_24.STI", "stucco"),
    "SLANT_12": ("Data-Maps-Tiles/Tilesets/51/SLANT_12.STI", "roof"),
    "FURN_MIX": ("Data-Maps-Tiles/Tilesets/51/FURN_MIX.STI", "interior"),
    "LAWLESS": ("Data-Maps-Tiles/Tilesets/9/LAWLESS.STI", "urban"),
    "LAWLESS2": ("Data-Maps-Tiles/Tilesets/53/LAWLESS2.STI", "urban"),
    "LAWLESS4": ("Data-Maps-Tiles/Tilesets/53/LAWLESS4.STI", "urban"),
    "W_DEC06": ("Data-Maps-Tiles/Tilesets/53/W_DEC06.STI", "decal"),
    "W_DEC09": ("Data-Maps-Tiles/Tilesets/53/W_DEC09.STI", "decal"),
}

def read_sti(path: Path):
    b = path.read_bytes()
    if len(b) < 64 or b[:4] != b"STCI":
        raise ValueError(f"{path}: not STCI")
    original, stored, transparent, flags = struct.unpack_from("<IIII", b, 4)
    height, width = struct.unpack_from("<HH", b, 20)
    colors = struct.unpack_from("<I", b, 24)[0]
    sub_count = struct.unpack_from("<H", b, 28)[0]
    depth = b[44]
    appdata_size = struct.unpack_from("<I", b, 45)[0]
    if not (flags & STCI_INDEXED) or depth != 8:
        raise ValueError(f"{path}: only 8-bit indexed STI supported (flags={flags:#x}, depth={depth})")
    if flags & STCI_ZLIB_COMPRESSED:
        raise ValueError(f"{path}: zlib STI not supported")
    if colors <= 0 or colors > 256:
        raise ValueError(f"{path}: invalid palette size {colors}")

    pos = 64
    pal = []
    for _ in range(colors):
        r,g,bl = b[pos:pos+3]; pos += 3
        pal.append((r,g,bl,255))
    while len(pal) < 256:
        pal.append((0,0,0,255))

    subs = []
    if flags & STCI_ETRLE_COMPRESSED:
        for _ in range(sub_count):
            data_off, data_len, ox, oy, h, w = struct.unpack_from("<IIhhHH", b, pos)
            pos += 16
            subs.append((data_off,data_len,ox,oy,w,h))
        data_base = pos
        frames = []
        for data_off,data_len,ox,oy,w,h in subs:
            src = memoryview(b)[data_base+data_off:data_base+data_off+data_len]
            rgba = bytearray(w*h*4)
            si = 0
            for y in range(h):
                x = 0
                while x < w and si < len(src):
                    code = int(src[si]); si += 1
                    if code == 0:
                        break
                    run = code & 0x7f
                    if code & 0x80:
                        x += run
                        continue
                    for _ in range(run):
                        if si >= len(src) or x >= w: break
                        idx = int(src[si]); si += 1
                        r,g,bl,a = pal[idx]
                        p = (y*w+x)*4
                        rgba[p:p+4] = bytes((r,g,bl,a))
                        x += 1
                # consume explicit row terminator if row ended exactly at width
                if x >= w and si < len(src) and int(src[si]) == 0:
                    si += 1
            frames.append((ox,oy,w,h,bytes(rgba)))
        return frames, {"width":width,"height":height,"flags":flags,"subimages":sub_count,
                        "original_size":original,"stored_size":stored,"appdata_size":appdata_size}

    # Non-ETRLE indexed STI: treat as one full frame.
    data = b[pos:pos+stored]
    if len(data) < width*height:
        raise ValueError(f"{path}: short raw image")
    rgba = bytearray(width*height*4)
    for i,idx in enumerate(data[:width*height]):
        r,g,bl,a = pal[idx]
        rgba[i*4:i*4+4] = bytes((r,g,bl,a))
    return [(0,0,width,height,bytes(rgba))], {"width":width,"height":height,"flags":flags,
                                             "subimages":1,"original_size":original,
                                             "stored_size":stored,"appdata_size":appdata_size}

def clamp(v):
    return max(0,min(255,int(v)))

def luminance(r,g,b):
    return 0.299*r + 0.587*g + 0.114*b

def saturation_span(r,g,b):
    return max(r,g,b)-min(r,g,b)

def remaster_frame(frame, kind, seed):
    """Material-aware redraw while preserving exact alpha, dimensions and offsets."""
    ox,oy,w,h,pix = frame
    src = Image.frombytes("RGBA",(w,h),pix)
    out = Image.new("RGBA",(w,h),(0,0,0,0))
    sp=src.load(); dp=out.load(); rng=random.Random(seed)

    def hnoise(x,y,scale=1):
        # Cheap deterministic texture noise. Low amplitude avoids visible seams
        # between separate road/wall sprites while breaking the flat 1990s palette.
        xx=x//max(1,scale); yy=y//max(1,scale)
        v=((xx*73856093) ^ (yy*19349663) ^ (seed*83492791)) & 255
        return (v-127.5)/127.5

    def material_rgb(base, lum, x, y, contrast=0.55, grain=7.0):
        shade=(lum-112.0)*contrast
        fine=hnoise(x,y,1)*grain
        broad=hnoise(x,y,5)*(grain*0.45)
        return tuple(clamp(c+shade+fine+broad) for c in base)

    # Muted, sun-beaten San Mona palette: poor commercial town rather than
    # saturated theme-park colour. Source luminance remains the lighting guide.
    STUCCO=(166,143,101)
    ROAD=(98,92,80)
    PAVING=(130,122,108)
    ROOF=(119,78,63)
    METAL=(69,72,72)

    for y in range(h):
        for x in range(w):
            r,g,b,a=sp[x,y]
            if not a:
                continue
            lum=luminance(r,g,b)
            sat=saturation_span(r,g,b)

            if kind == "stucco":
                # Neutral mid/high-value regions are plaster; dark/saturated source
                # pixels are openings, bars, trim or damage and keep their identity.
                wallish = lum > 55 and sat < 78
                if wallish:
                    rr,gg,bb=material_rgb(STUCCO,lum,x,y,0.48,7.0)
                    # Capillary grime near ground and mild bleaching near top.
                    t=y/max(1,h-1)
                    if t>0.68:
                        dirt=(t-0.68)/0.32
                        rr=clamp(rr-18*dirt); gg=clamp(gg-17*dirt); bb=clamp(bb-13*dirt)
                    elif t<0.18:
                        rr=clamp(rr+5); gg=clamp(gg+5); bb=clamp(bb+4)
                    dp[x,y]=(rr,gg,bb,a)
                else:
                    # Keep joinery/openings nearly intact but age them slightly.
                    neutral=0.92
                    dp[x,y]=(clamp(r*neutral+5),clamp(g*neutral+4),clamp(b*neutral+3),a)

            elif kind == "roof":
                # Preserve dark timber/support pieces; repaint sheet material.
                sheetish = (lum > 88) or (lum > 52 and sat < 85)
                if sheetish:
                    rr,gg,bb=material_rgb(ROOF,lum,x,y,0.43,6.0)
                    # Fine alternating highlight/dark rib effect, intentionally
                    # subtle because sprite orientations vary across the family.
                    rib=((x+y+(seed&7))%5)
                    if rib==0:
                        rr=clamp(rr+7); gg=clamp(gg+4); bb=clamp(bb+3)
                    elif rib==3:
                        rr=clamp(rr-5); gg=clamp(gg-4); bb=clamp(bb-3)
                    # Sparse rust blooms.
                    n=hnoise(x,y,3)
                    if n>0.72:
                        rr=clamp(rr+20); gg=clamp(gg-10); bb=clamp(bb-12)
                    dp[x,y]=(rr,gg,bb,a)
                else:
                    dp[x,y]=(clamp(r*0.91+5),clamp(g*0.88+4),clamp(b*0.84+4),a)

            elif kind == "road":
                rr,gg,bb=material_rgb(ROAD,lum,x,y,0.66,4.5)
                # Retain original stone relief while making mortar/joints darker.
                if lum < 78:
                    rr=clamp(rr-8); gg=clamp(gg-8); bb=clamp(bb-7)
                # Very sparse ingrained dirt/oil; no large frame-specific patches.
                n=hnoise(x,y,4)
                if n>0.82:
                    rr=clamp(rr-13); gg=clamp(gg-12); bb=clamp(bb-10)
                elif n<-0.86:
                    rr=clamp(rr+7); gg=clamp(gg+6); bb=clamp(bb+5)
                dp[x,y]=(rr,gg,bb,a)

            elif kind == "paving":
                rr,gg,bb=material_rgb(PAVING,lum,x,y,0.60,4.0)
                if hnoise(x,y,6)>0.84:
                    rr=clamp(rr-9); gg=clamp(gg-9); bb=clamp(bb-8)
                dp[x,y]=(rr,gg,bb,a)

            elif kind == "metal":
                # Painted/galvanised street furniture with restrained rust.
                rr,gg,bb=material_rgb(METAL,lum,x,y,0.72,3.5)
                if hnoise(x,y,3)>0.88 and lum<150:
                    rr=clamp(rr+25); gg=clamp(gg-9); bb=clamp(bb-13)
                dp[x,y]=(rr,gg,bb,a)

            elif kind == "decal":
                # Signs remain readable: deepen blacks, fade whites, restrain neon.
                if lum < 55:
                    dp[x,y]=(clamp(r*0.76),clamp(g*0.76),clamp(b*0.76),a)
                elif sat>80:
                    dp[x,y]=(clamp(r*1.03+2),clamp(g*1.00+1),clamp(b*0.96),a)
                else:
                    dp[x,y]=(clamp(r*0.98+6),clamp(g*0.97+5),clamp(b*0.93+3),a)

            elif kind == "interior":
                # Furniture stays recognisable but picks up warmer wood/cloth depth.
                if r>g*1.10 and r>b*1.12:
                    dp[x,y]=(clamp(r*1.02+3),clamp(g*0.95+2),clamp(b*0.88+1),a)
                else:
                    dp[x,y]=(clamp(r*1.00+2),clamp(g*0.98+2),clamp(b*0.94+1),a)

            else: # mixed urban props
                # Preserve object semantics. Add modest contrast/patina only.
                if sat<38 and lum>65:
                    n=hnoise(x,y,2)
                    dp[x,y]=(clamp(r*0.98+n*5+3),clamp(g*0.97+n*4+3),clamp(b*0.94+n*3+2),a)
                else:
                    dp[x,y]=(clamp(r*1.01+1),clamp(g*0.99+1),clamp(b*0.96+1),a)

    p=out.load()

    def opaque(xx,yy):
        return 0 <= xx < w and 0 <= yy < h and sp[xx,yy][3] > 0

    def wall_candidate(xx,yy):
        if not opaque(xx,yy):
            return False
        r0,g0,b0,a0=sp[xx,yy]
        return luminance(r0,g0,b0)>62 and saturation_span(r0,g0,b0)<75

    if kind == "stucco":
        candidates=[(xx,yy) for yy in range(2,h-2) for xx in range(2,w-2) if wall_candidate(xx,yy)]
        if candidates:
            # Hairline plaster cracks: connected, sparse and confined to wall pixels.
            for _ in range(min(4,max(1,len(candidates)//520))):
                x,y=rng.choice(candidates)
                for __ in range(rng.randint(4,10)):
                    if wall_candidate(x,y):
                        rr,gg,bb,aa=p[x,y]
                        p[x,y]=(clamp(rr-43),clamp(gg-39),clamp(bb-31),aa)
                    x += rng.choice((-1,0,1))
                    y += rng.choice((0,1,1,1,2))
            # Small chipped plaster exposing dull brick, never giant random blotches.
            for _ in range(min(7,max(1,len(candidates)//360))):
                x,y=rng.choice(candidates)
                for dx,dy in ((0,0),(1,0),(0,1)):
                    xx=x+dx; yy=y+dy
                    if wall_candidate(xx,yy):
                        rr,gg,bb,aa=p[xx,yy]
                        p[xx,yy]=(clamp(126+(rr-150)*0.18),clamp(75+(gg-130)*0.12),clamp(54+(bb-95)*0.10),aa)
            # Narrow rain/grime streaks beginning below darker features.
            for _ in range(min(3,max(1,w//24))):
                x=rng.randrange(max(1,w))
                y0=rng.randrange(max(1,h//3),max(2,h*2//3))
                for yy in range(y0,min(h,y0+rng.randint(5,14))):
                    if wall_candidate(x,yy):
                        rr,gg,bb,aa=p[x,yy]
                        p[x,yy]=(clamp(rr-10),clamp(gg-11),clamp(bb-10),aa)

    elif kind == "roof":
        # A handful of darker repair/rust flecks, constrained to existing sheet.
        for _ in range(max(1,(w*h)//900)):
            x=rng.randrange(max(1,w)); y=rng.randrange(max(1,h))
            if not opaque(x,y):
                continue
            sr,sg,sb,sa=sp[x,y]
            if luminance(sr,sg,sb)<65:
                continue
            for dx,dy in ((0,0),(1,0),(0,1)):
                xx=x+dx; yy=y+dy
                if opaque(xx,yy):
                    rr,gg,bb,aa=p[xx,yy]
                    p[xx,yy]=(clamp(rr-20),clamp(gg-16),clamp(bb-13),aa)

    elif kind in ("road","paving"):
        # Tiny cracks/wear marks only where pixels already exist.
        crack_count=max(0,min(3,(w*h)//2400))
        for _ in range(crack_count):
            x=rng.randrange(max(1,w)); y=rng.randrange(max(1,h))
            for __ in range(rng.randint(3,7)):
                if opaque(x,y):
                    rr,gg,bb,aa=p[x,y]
                    p[x,y]=(clamp(rr-17),clamp(gg-17),clamp(bb-15),aa)
                x+=rng.choice((-1,0,1)); y+=rng.choice((-1,0,1))

    # Crisp but not oversharpened. Restore source alpha verbatim after filtering.
    rgb=out.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.55,percent=105,threshold=3))
    alpha=src.getchannel("A")
    out=Image.merge("RGBA",(*rgb.split(),alpha))
    return ox,oy,w,h,out.tobytes()

def write_b1tc(path: Path, frames):
    header=bytearray(b"B1TC")+struct.pack("<HH",1,len(frames))
    directory=bytearray(); payload=bytearray()
    offset=8+16*len(frames)
    for ox,oy,w,h,pix in frames:
        if len(pix)!=w*h*4: raise ValueError(f"{path}: bad RGBA length")
        directory += struct.pack("<hhHHII",ox,oy,w,h,offset,len(pix))
        payload += pix; offset += len(pix)
    path.write_bytes(bytes(header+directory+payload))

def contact_sheet(name, original, remastered):
    cells=[]
    for label,frames in (("OLD",original),("NEW",remastered)):
        for i,(ox,oy,w,h,pix) in enumerate(frames):
            im=Image.frombytes("RGBA",(w,h),pix)
            cells.append((f"{label} {i}",im))
    if not cells: return
    thumb_w=max(72,max(im.width for _,im in cells)+8)
    thumb_h=max(72,max(im.height for _,im in cells)+24)
    cols=min(8,max(1,math.ceil(math.sqrt(len(cells)))))
    rows=math.ceil(len(cells)/cols)
    sheet=Image.new("RGB",(cols*thumb_w,rows*thumb_h),(36,35,33))
    d=ImageDraw.Draw(sheet)
    for idx,(label,im) in enumerate(cells):
        cx=(idx%cols)*thumb_w; cy=(idx//cols)*thumb_h
        checker=Image.new("RGBA",(thumb_w,thumb_h-18),(66,64,60,255))
        sheet.paste(checker,(cx,cy+18))
        sheet.paste(im,(cx+(thumb_w-im.width)//2,cy+18+(thumb_h-18-im.height)//2),im)
        d.text((cx+3,cy+3),label,fill=(235,232,224))
    PREVIEW.mkdir(parents=True,exist_ok=True)
    sheet.save(PREVIEW/f"{name}_comparison.png")

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    PREVIEW.mkdir(parents=True,exist_ok=True)
    manifest={"sector":"C5","tileset":18,"mode":"graphics-only","style_version":2,"art_direction":"sun-faded poor South-American vice/commercial district","assets":[]}
    for n,(rel,kind) in SOURCES.items():
        src=ROOT/rel
        if not src.exists():
            print("SKIP missing",src); continue
        frames,meta=read_sti(src)
        new=[remaster_frame(f,kind,0xC50000+i*7919+sum(map(ord,n))) for i,f in enumerate(frames)]
        dst=OUT/f"{n}.b1tc"
        write_b1tc(dst,new)
        contact_sheet(n,frames,new)
        manifest["assets"].append({
            "logical_name":n+".STI","b1tc":dst.name,"source":rel,"kind":kind,
            "frames":len(frames),"frame_geometry":[[f[0],f[1],f[2],f[3]] for f in frames],
            "sti_meta":meta,
        })
        print("generated",dst,len(frames),"frames")

    (OUT/"SAN_MONA_C5_VISUAL_REMASTER.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    (OUT/"SAN_MONA_C5_VISUAL_REMASTER_README.txt").write_text(
"""SAN MONA C5 — GRAPHICS-ONLY REMASTER

Scope invariant:
- C5.dat is NOT modified.
- No JSD is modified.
- No tile index, tile location, collision, LOS, penetration, destruction, door,
  quest, NPC, pathfinding or scripting behavior is modified.
- Only same-name B1TC visual siblings are added to tileset 18.

Vengeance resolves the original logical STI/JSD identity while preferring a B1TC
sibling for pixels. These files therefore alter appearance only.

Style v2 uses material-aware redraw recipes rather than blanket recolouring. It focuses on existing San Mona road/paving/streetscape plus selected
building/roof/interior/urban families whose matching STI source is present in the
repository. Missing inherited base-game families are deliberately left untouched
until they are extracted exactly; nothing is guessed.
""",encoding="utf-8")
    print("generated",len(manifest["assets"]),"visual families")

if __name__=="__main__":
    main()
