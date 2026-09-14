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

def rgb_grade(r,g,b,kind):
    # Preserve luminance hierarchy/silhouette; change material/color character only.
    y = 0.299*r + 0.587*g + 0.114*b
    if kind == "road":
        # dusty charcoal/brown cobble with stronger stone separation
        nr = y*0.90 + r*0.18 + 12
        ng = y*0.84 + g*0.12 + 8
        nb = y*0.72 + b*0.10 + 3
    elif kind == "paving":
        nr = y*0.95 + r*0.10 + 10
        ng = y*0.90 + g*0.08 + 8
        nb = y*0.80 + b*0.07 + 5
    elif kind == "stucco":
        # faded ochre/cream plaster, slightly sun-bleached
        nr = y*0.90 + 32
        ng = y*0.76 + 23
        nb = y*0.58 + 14
    elif kind == "roof":
        # weathered red-brown/corrugated material
        nr = y*0.82 + r*0.20 + 24
        ng = y*0.55 + g*0.12 + 12
        nb = y*0.42 + b*0.08 + 8
    elif kind == "metal":
        nr = y*0.78 + 15
        ng = y*0.80 + 16
        nb = y*0.82 + 18
    elif kind == "decal":
        nr = r*1.08 + 6
        ng = g*1.03 + 4
        nb = b*0.94
    elif kind == "interior":
        nr = r*1.05 + 3
        ng = g*1.01 + 2
        nb = b*0.92
    else: # urban
        nr = r*1.05 + y*0.04 + 3
        ng = g*1.00 + y*0.02 + 2
        nb = b*0.93
    return tuple(max(0,min(255,int(v))) for v in (nr,ng,nb))

def inside_alpha(im, x, y, radius=1):
    if x < radius or y < radius or x >= im.width-radius or y >= im.height-radius:
        return False
    p = im.load()
    return all(p[x+dx,y+dy][3] > 0 for dx in range(-radius,radius+1) for dy in range(-radius,radius+1))

def add_material_detail(im: Image.Image, kind: str, seed: int):
    rng = random.Random(seed)
    px = im.load()

    # Fine material variation inside existing opaque silhouette only.
    for y in range(im.height):
        for x in range(im.width):
            r,g,b,a = px[x,y]
            if not a: continue
            n = rng.randint(-5,5)
            if kind in ("stucco","roof","road","paving"):
                r=max(0,min(255,r+n)); g=max(0,min(255,g+n)); b=max(0,min(255,b+n))
                px[x,y]=(r,g,b,a)

    draw = ImageDraw.Draw(im, "RGBA")
    opaque = [(x,y) for y in range(im.height) for x in range(im.width) if px[x,y][3] and inside_alpha(im,x,y,1)]
    if not opaque: return im

    if kind == "stucco":
        # restrained hairline cracks + damp/grime marks, never outside original sprite
        for _ in range(max(1, len(opaque)//500)):
            x,y = rng.choice(opaque)
            pts=[(x,y)]
            for __ in range(rng.randint(2,5)):
                x += rng.choice((-1,0,1)); y += rng.choice((0,1,1,2))
                if 0 <= x < im.width and 0 <= y < im.height and px[x,y][3]:
                    pts.append((x,y))
            if len(pts)>1: draw.line(pts, fill=(65,48,36,75), width=1)
        # lower-edge dirt wash only on opaque pixels
        for x,y in rng.sample(opaque, min(len(opaque), max(1,len(opaque)//25))):
            if y > im.height*0.60:
                r,g,b,a=px[x,y]; px[x,y]=(max(0,r-16),max(0,g-14),max(0,b-11),a)
    elif kind == "roof":
        for x,y in rng.sample(opaque, min(len(opaque), max(1,len(opaque)//18))):
            r,g,b,a=px[x,y]
            px[x,y]=(min(255,r+16),max(0,g-7),max(0,b-8),a)
    elif kind in ("road","paving"):
        # subtle dirt/oil spotting contained in existing opaque tile
        for _ in range(max(1,len(opaque)//900)):
            x,y=rng.choice(opaque)
            rad=rng.randint(1,3)
            for yy in range(max(0,y-rad),min(im.height,y+rad+1)):
                for xx in range(max(0,x-rad),min(im.width,x+rad+1)):
                    if px[xx,yy][3]:
                        r,g,b,a=px[xx,yy]
                        px[xx,yy]=(max(0,r-10),max(0,g-9),max(0,b-7),a)
    return im

def remaster_frame(frame, kind, seed):
    ox,oy,w,h,pix = frame
    im = Image.frombytes("RGBA",(w,h),pix)
    data=[]
    for r,g,b,a in im.getdata():
        if a == 0:
            data.append((0,0,0,0))
        else:
            nr,ng,nb = rgb_grade(r,g,b,kind)
            data.append((nr,ng,nb,a))
    im.putdata(data)
    im = add_material_detail(im,kind,seed)
    # modest clarity; preserve pixel footprint, do not resize.
    rgb = im.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.65, percent=105, threshold=3))
    alpha = im.getchannel("A")
    im = Image.merge("RGBA",(*rgb.split(),alpha))
    return ox,oy,w,h,im.tobytes()

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
