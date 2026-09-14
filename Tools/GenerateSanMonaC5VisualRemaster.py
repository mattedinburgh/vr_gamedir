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
    "C5_FLAT_R3": ("Data-Maps-Tiles/Tilesets/0/FLAT_R3.sti", "flatroof"),
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
    """Re-author pixels inside the exact legacy silhouette.

    Geometry is immutable: offsets, dimensions and alpha are copied exactly from
    the source frame.  The source RGB is used only for semantic classification
    (wall/trim, roof/support) and a small amount of lighting guidance.  Material
    texture itself is generated afresh so this is a redraw, not a palette shift.
    """
    ox,oy,w,h,pix = frame
    src = Image.frombytes("RGBA",(w,h),pix)
    out = Image.new("RGBA",(w,h),(0,0,0,0))
    sp=src.load(); dp=out.load(); rng=random.Random(seed)

    def n2(x,y,salt=0):
        # deterministic integer noise, stable between runs and adjacent pixels
        v=(x*73856093) ^ (y*19349663) ^ (seed*83492791) ^ (salt*2654435761)
        v=(v ^ (v>>13))*1274126177
        return ((v ^ (v>>16)) & 255) / 255.0

    def put(x,y,r,g,b,a):
        dp[x,y]=(clamp(r),clamp(g),clamp(b),a)

    for y in range(h):
        for x in range(w):
            r,g,b,a=sp[x,y]
            if not a:
                continue
            lum=luminance(r,g,b)
            sat=saturation_span(r,g,b)
            light=(lum-110.0)*0.16

            if kind == "road":
                # Fresh irregular brown-grey cobbles. Staggered masonry joints are
                # generated independently of the old palette while retaining its
                # silhouette and only a little of its relief lighting.
                cell_h=6
                cell_w=10
                row=y//cell_h
                sx=x + (cell_w//2 if row&1 else 0)
                col=sx//cell_w
                lx=sx%cell_w
                ly=y%cell_h
                joint=(lx==0 or ly==0 or (ly==cell_h-1 and n2(col,row,3)>0.55))
                stone=n2(col,row,7)
                grain=(n2(x,y,11)-0.5)*13
                if joint:
                    put(x,y,62+light*0.35,57+light*0.32,49+light*0.28,a)
                else:
                    base=91 + stone*24
                    put(x,y,base+light+grain,base-8+light+grain*0.7,base-23+light*0.8+grain*0.45,a)

            elif kind == "paving":
                # Large worn pavement slabs with dark seams, grime and occasional
                # hairline cracks. This is new surface detail, not source recolour.
                slab_w=14
                slab_h=8
                row=y//slab_h
                sx=x + (slab_w//2 if row&1 else 0)
                col=sx//slab_w
                lx=sx%slab_w
                ly=y%slab_h
                seam=(lx==0 or ly==0)
                slab=n2(col,row,19)
                grain=(n2(x,y,23)-0.5)*9
                if seam:
                    put(x,y,48+light*0.24,46+light*0.22,41+light*0.20,a)
                else:
                    # Dirty, traffic-polished paving: warm grey-brown rather than
                    # bright clean stone. Keep enough contrast for the slab pattern.
                    base=88 + slab*14
                    dirt=n2(x//3,y//3,29)
                    grime=-16 if dirt>0.80 else (-7 if dirt>0.65 else 0)
                    oil=-25 if n2(x//5,y//5,30)>0.95 else 0
                    dust=6 if n2(x//6,y//4,32)>0.90 else 0
                    put(x,y,base+7+light+grain+grime+oil+dust,
                              base+1+light+grain*0.7+grime+oil+dust*0.6,
                              base-9+light*0.8+grain*0.5+grime+oil+dust*0.25,a)

            elif kind == "stucco":
                # Preserve openings/joinery, completely repaint broad plaster.
                wallish = lum > 58 and sat < 72
                if not wallish:
                    # Trim/openings keep identity but are cleaned and deepened.
                    put(x,y,r*0.94+4,g*0.93+4,b*0.90+4,a)
                    continue
                coarse=(n2(x//4,y//4,31)-0.5)*12
                fine=(n2(x,y,37)-0.5)*7
                sun=7 if y < h*0.22 else 0
                grime=-15 if y > h*0.72 else 0
                # Faded ochre plaster appropriate to San Mona.
                put(x,y,177+light+coarse+fine+sun+grime,
                          145+light*0.82+coarse*0.7+fine*0.6+sun+grime,
                           96+light*0.65+coarse*0.45+fine*0.35+sun*0.6+grime,a)

            elif kind == "roof":
                # Re-author corrugated, oxidised sheet metal while preserving dark
                # rafters/supports. Ridge pattern is generated from geometry.
                sheetish = (lum > 92) or (lum > 55 and g >= r*0.92 and g >= b*0.90)
                if not sheetish:
                    put(x,y,r*0.91+5,g*0.88+4,b*0.84+4,a)
                    continue
                ridge=(x + 2*y + (seed&7)) % 7
                ridge_light=14 if ridge in (0,1) else (-10 if ridge in (4,5) else 0)
                rust=n2(x//3,y//3,41)
                rust_boost=26 if rust>0.86 else (12 if rust>0.72 else 0)
                fine=(n2(x,y,43)-0.5)*8
                put(x,y,122+light+ridge_light+rust_boost+fine,
                           83+light*0.60+ridge_light*0.45-rust_boost*0.18+fine*0.45,
                           62+light*0.45+ridge_light*0.30-rust_boost*0.25+fine*0.30,a)

            elif kind == "flatroof":
                # Dominant C5 flat-roof family: dusty aged concrete/tar. Preserve
                # embedded ladders/rails/metal fixtures as a distinct dark material.
                detailish = lum > 112 or sat > 72
                if detailish:
                    metal_noise=(n2(x,y,79)-0.5)*8
                    put(x,y,43+lum*0.30+metal_noise,
                              47+lum*0.31+metal_noise,
                              49+lum*0.33+metal_noise,a)
                    continue
                coarse=(n2(x//5,y//5,61)-0.5)*12
                fine=(n2(x,y,67)-0.5)*8
                patch=n2(x//9,y//7,71)
                stain=n2(x//4,y//4,73)
                patch_shift=-18 if patch>0.86 else (5 if patch<0.07 else 0)
                water=-15 if stain>0.89 else 0
                edge_dirt=-10 if (x<2 or y<2 or x>w-3 or y>h-3) else 0
                base=98 + light*0.60 + coarse + fine + patch_shift + water + edge_dirt
                put(x,y,base+8,base+3,base-5,a)

            elif kind == "metal":
                # San Mona street furniture: old dark-painted steel, oxidised and
                # repeatedly repaired. Bright pixels near the lamp head become warm
                # dirty glass; the pole itself stays dark rather than modern silver.
                edge=(n2(x,y,47)-0.5)*7
                if lum > 165 and y < h*0.42:
                    put(x,y,190+light*0.45+edge,166+light*0.38+edge,104+light*0.25+edge,a)
                else:
                    rust=10 if n2(x//2,y//3,49)>0.91 else 0
                    put(x,y,34+lum*0.24+edge+rust,
                              38+lum*0.25+edge-rust*0.15,
                              40+lum*0.27+edge-rust*0.28,a)

            elif kind == "decal":
                # Keep lettering/sign identity intact; clean contrast only.
                if lum < 65:
                    put(x,y,r*0.74,g*0.74,b*0.74,a)
                else:
                    put(x,y,r*1.10+6,g*1.07+5,b*1.02+3,a)

            elif kind == "interior":
                # Preserve recognizable furniture while restoring material separation.
                wood=(r > b*1.10 and r > g*0.95)
                if wood:
                    put(x,y,r*1.05+6,g*0.94+4,b*0.82+3,a)
                else:
                    put(x,y,r*1.04+3,g*1.02+3,b*0.98+2,a)

            else: # urban props
                # Identity-preserving cleanup for complex props; these will be
                # hand-authored family-by-family after the core environment pass.
                put(x,y,r*1.05+3,g*1.02+2,b*0.97+2,a)

    p=out.load()
    def opaque(xx,yy):
        return 0 <= xx < w and 0 <= yy < h and p[xx,yy][3] > 0

    if kind == "stucco":
        # Purposeful cracks and chipped plaster. Never paint outside legacy alpha.
        candidates=[]
        for yy in range(2,h-2):
            for xx in range(2,w-2):
                r0,g0,b0,a0=sp[xx,yy]
                if a0 and luminance(r0,g0,b0)>65 and saturation_span(r0,g0,b0)<70:
                    candidates.append((xx,yy))
        if candidates:
            draw=ImageDraw.Draw(out,"RGBA")
            crack_count=min(5,max(1,len(candidates)//420))
            for _ in range(crack_count):
                x,y=rng.choice(candidates)
                pts=[(x,y)]
                for __ in range(rng.randint(4,9)):
                    x += rng.choice((-1,0,0,1))
                    y += rng.choice((0,1,1,2))
                    if opaque(x,y):
                        pts.append((x,y))
                if len(pts)>2:
                    draw.line(pts,fill=(56,47,39,155),width=1)
            # exposed masonry chips clustered near lower/edge wear
            for _ in range(min(14,max(2,len(candidates)//260))):
                x,y=rng.choice(candidates)
                if y < h*0.25 and rng.random()<0.6:
                    continue
                for yy in range(y-1,y+2):
                    for xx in range(x-2,x+3):
                        if opaque(xx,yy) and n2(xx,yy,53)>0.48:
                            rr,gg,bb,aa=p[xx,yy]
                            p[xx,yy]=(clamp(rr-42),clamp(gg-48),clamp(bb-39),aa)

    elif kind == "paving":
        # Sparse cracks crossing slabs without changing occupancy.
        draw=ImageDraw.Draw(out,"RGBA")
        for _ in range(max(1,(w*h)//5500)):
            x=rng.randrange(max(1,w)); y=rng.randrange(max(1,h))
            pts=[]
            for __ in range(rng.randint(3,7)):
                if opaque(x,y): pts.append((x,y))
                x+=rng.choice((-1,0,1,1)); y+=rng.choice((0,1,1))
            if len(pts)>1:
                draw.line(pts,fill=(61,57,50,120),width=1)

    # Sharpen RGB but restore the source alpha byte-for-byte.
    rgb=out.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.55,percent=120,threshold=2))
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
    manifest={"sector":"C5","tileset":18,"mode":"graphics-only","style_version":"2.3","art_direction":"sun-faded poor South-American vice/commercial district","assets":[]}
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

Style v2.3 uses material-aware redraw recipes rather than blanket recolouring. Pavement is darker, traffic-dulled and stained; street lamps are old dark-painted/oxidised steel with warm dirty lamp glass. C5_FLAT_R3 redraws the dominant inherited flat-roof family as aged dusty concrete/tar while preserving ladder/rail pixels as dark metal; the engine keeps the original generic FLAT_R3 structure metadata. It focuses on existing San Mona road/paving/streetscape plus selected
building/roof/interior/urban families whose matching STI source is present in the
repository. Missing inherited base-game families are deliberately left untouched
until they are extracted exactly; nothing is guessed.
""",encoding="utf-8")
    print("generated",len(manifest["assets"]),"visual families")

if __name__=="__main__":
    main()
