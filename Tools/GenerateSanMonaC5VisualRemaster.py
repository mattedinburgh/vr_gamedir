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
    """Redraw material while preserving exact alpha, dimensions and offsets."""
    ox,oy,w,h,pix = frame
    src = Image.frombytes("RGBA",(w,h),pix)
    out = Image.new("RGBA",(w,h),(0,0,0,0))
    sp=src.load(); dp=out.load(); rng=random.Random(seed)

    # Stable palette per frame.  Structural darks/details remain recognisable;
    # broad material surfaces are repainted rather than merely recoloured.
    # A single file is one architectural material family. Keep it coherent across
    # all frames/orientations; variation belongs between tile families, not between
    # adjacent pieces of the same wall.
    stucco_base=(181,150,101)  # sun-faded ochre plaster

    for y in range(h):
        for x in range(w):
            r,g,b,a=sp[x,y]
            if not a: continue
            lum=luminance(r,g,b); sat=saturation_span(r,g,b)
            local=((x*17+y*29+(seed&255))%13)-6

            if kind == "stucco":
                # BUILD_24 contains plaster panels plus dark frames/bars/openings.
                # Repaint only broad neutral mid/high-value wall material; preserve
                # dark joinery/openings and strongly coloured details.
                wallish = lum > 58 and sat < 72
                if wallish:
                    shade=(lum-118)*0.43
                    rr=stucco_base[0]+shade+local
                    gg=stucco_base[1]+shade+local
                    bb=stucco_base[2]+shade+local
                    # lower-wall grime / sun bleaching
                    if y > h*0.70: rr-=10; gg-=11; bb-=9
                    if y < h*0.20: rr+=5; gg+=5; bb+=4
                    dp[x,y]=(clamp(rr),clamp(gg),clamp(bb),a)
                else:
                    # Preserve bars, windows, damage and trim, just clean the palette.
                    dp[x,y]=(clamp(r*1.02+4),clamp(g*1.01+3),clamp(b*0.96+2),a)

            elif kind == "roof":
                # SLANT_12 contains both corrugated sheet and its wooden/dark support
                # frame. Redraw the sheet only. Dark support pixels keep their
                # original material identity instead of becoming orange.
                sheetish = (lum > 92) or (lum > 55 and g >= r*0.92 and g >= b*0.90)
                if sheetish:
                    shade=(lum-112)*0.48
                    rr=137+shade+local*0.55
                    gg=79+shade*0.42+local*0.20
                    bb=55+shade*0.30
                    dp[x,y]=(clamp(rr),clamp(gg),clamp(bb),a)
                else:
                    # preserve timber/steel understructure; only improve separation
                    dp[x,y]=(clamp(r*0.97+3),clamp(g*0.94+3),clamp(b*0.91+3),a)

            elif kind == "road":
                # Dusty brown-grey cobbles, keeping the original stone relief.
                shade=(lum-100)*0.70
                rr=104+shade+local*0.55
                gg=91+shade+local*0.45
                bb=72+shade*0.85
                dp[x,y]=(clamp(rr),clamp(gg),clamp(bb),a)

            elif kind == "paving":
                shade=(lum-112)*0.68
                rr=132+shade+local*0.45
                gg=121+shade+local*0.40
                bb=103+shade*0.85
                dp[x,y]=(clamp(rr),clamp(gg),clamp(bb),a)

            elif kind == "metal":
                # Street lamps: neutral dark metal with readable highlights.
                dp[x,y]=(clamp(lum*0.86+16),clamp(lum*0.88+17),clamp(lum*0.91+19),a)

            elif kind == "decal":
                # Keep sign identity/text legible; deepen blacks and strengthen colour.
                if lum < 65:
                    dp[x,y]=(clamp(r*0.78),clamp(g*0.78),clamp(b*0.78),a)
                else:
                    dp[x,y]=(clamp(r*1.12+5),clamp(g*1.08+4),clamp(b*1.03+2),a)

            elif kind == "interior":
                # Furniture remains itself; richer wood/cloth and clearer shading.
                dp[x,y]=(clamp(r*1.07+3),clamp(g*1.02+2),clamp(b*0.93+1),a)

            else: # urban props
                dp[x,y]=(clamp(r*1.08+2),clamp(g*1.03+2),clamp(b*0.96+1),a)

    p=out.load()
    def opaque(xx,yy):
        return 0 <= xx < w and 0 <= yy < h and p[xx,yy][3] > 0

    if kind == "stucco":
        # Add restrained material features only to wall-like pixels.  These are
        # visual marks inside the existing sprite; alpha/footprint never changes.
        candidates=[]
        for yy in range(2,h-2):
            for xx in range(2,w-2):
                r0,g0,b0,a0=sp[xx,yy]
                if a0 and luminance(r0,g0,b0)>65 and saturation_span(r0,g0,b0)<70:
                    candidates.append((xx,yy))
        if candidates:
            draw=ImageDraw.Draw(out,"RGBA")
            for _ in range(min(3,max(1,len(candidates)//600))):
                x,y=rng.choice(candidates); pts=[(x,y)]
                for __ in range(rng.randint(3,7)):
                    x+=rng.choice((-1,0,1)); y+=rng.choice((0,1,1,2))
                    if opaque(x,y): pts.append((x,y))
                if len(pts)>2: draw.line(pts,fill=(64,52,43,115),width=1)
            # A few tiny exposed-brick chips, not whole random patches.
            for _ in range(min(6,max(1,len(candidates)//450))):
                x,y=rng.choice(candidates)
                if opaque(x,y):
                    r1,g1,b1,a1=p[x,y]; p[x,y]=(clamp(r1-35),clamp(g1-45),clamp(b1-42),a1)

    elif kind == "roof":
        # Corrugation/rust is painted inside the existing roof silhouette.
        for yy in range(h):
            for xx in range(w):
                if not opaque(xx,yy): continue
                r,g,b,a=p[xx,yy]
                sr,sg,sb,sa=sp[xx,yy]
                sl=luminance(sr,sg,sb)
                sheetish=(sl > 92) or (sl > 55 and sg >= sr*0.92 and sg >= sb*0.90)
                if not sheetish: continue
                if ((xx + yy*2 + (seed&7)) % 7)==0:
                    p[xx,yy]=(clamp(r+11),clamp(g-6),clamp(b-7),a)
                if ((xx*5 + yy*3 + seed) % 97)==0:
                    p[xx,yy]=(clamp(r+22),clamp(g-11),clamp(b-12),a)

    elif kind in ("road","paving"):
        # Reinforce existing masonry with subtle joints/dirt, contained by alpha.
        for yy in range(h):
            for xx in range(w):
                if not opaque(xx,yy): continue
                r,g,b,a=p[xx,yy]
                period=9 if kind=="road" else 11
                joint=((xx+yy+(seed&7))%period==0 and (xx-yy+(seed>>4))%5==0)
                if joint:
                    p[xx,yy]=(clamp(r-16),clamp(g-15),clamp(b-13),a)
                elif ((xx*37+yy*61+seed)%241)==0:
                    p[xx,yy]=(clamp(r-18),clamp(g-16),clamp(b-13),a)

    # Fine clarity only; never resize or alter alpha.
    rgb=out.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.6,percent=115,threshold=2))
    alpha=out.getchannel("A")
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
    manifest={"sector":"C5","tileset":18,"mode":"graphics-only","assets":[]}
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

This first pass focuses on existing San Mona road/paving/streetscape plus selected
building/roof/interior/urban families whose matching STI source is present in the
repository. Missing inherited base-game families are deliberately left untouched
until they are extracted exactly; nothing is guessed.
""",encoding="utf-8")
    print("generated",len(manifest["assets"]),"visual families")

if __name__=="__main__":
    main()
