"""Deterministic first-pass art, geometry and sound. Python standard library only.

Source meshes use Unreal centimetres, Z up, X forward. Native editor tooling
builds mesh assets directly from JSON, avoiding importer axis/scale ambiguity.
OBJ companions are editable exchange files; no Blender or external assets needed.
"""
from pathlib import Path
import json
import math
import random
import struct
import wave
import zlib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "SourceArt" / "Level01"


class Mesh:
    def __init__(self):
        self.v, self.t, self.uv = [], [], []

    def face(self, points, uv=None):
        start = len(self.v)
        self.v.extend(points)
        self.uv.extend(uv or [(0, 0), (1, 0), (1, 1), (0, 1)][:len(points)])
        for i in range(1, len(points) - 1):
            self.t.extend([start, start + i, start + i + 1])

    def box(self, center, size):
        x, y, z = center
        a, b, c = [s / 2 for s in size]
        p = [(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
             (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
        for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.face([p[i] for i in f])

    def lathe(self, profile, segments=32):
        for j in range(len(profile)-1):
            r0, z0 = profile[j]; r1, z1 = profile[j+1]
            for i in range(segments):
                a, b = 2*math.pi*i/segments, 2*math.pi*(i+1)/segments
                if r0 == 0:
                    self.face([(0,0,z0),(r1*math.cos(b),r1*math.sin(b),z1),(r1*math.cos(a),r1*math.sin(a),z1)],
                              [(i/segments,z0/100),((i+1)/segments,z1/100),(i/segments,z1/100)])
                    continue
                if r1 == 0:
                    self.face([(r0*math.cos(a),r0*math.sin(a),z0),(r0*math.cos(b),r0*math.sin(b),z0),(0,0,z1)],
                              [(i/segments,z0/100),((i+1)/segments,z0/100),(i/segments,z1/100)])
                    continue
                self.face([(r0*math.cos(a),r0*math.sin(a),z0),
                           (r0*math.cos(b),r0*math.sin(b),z0),
                           (r1*math.cos(b),r1*math.sin(b),z1),
                           (r1*math.cos(a),r1*math.sin(a),z1)],
                          [(i/segments,z0/100),((i+1)/segments,z0/100),
                           ((i+1)/segments,z1/100),(i/segments,z1/100)])

    def save(self, name, complex_collision=False):
        folder = OUT / "Meshes"; folder.mkdir(parents=True, exist_ok=True)
        data = dict(vertices=self.v, triangles=self.t, uvs=self.uv, complex_collision=complex_collision)
        (folder / (name + ".json")).write_text(json.dumps(data, separators=(",", ":")))
        lines = ["# ALMNSY original procedural source; centimetres, Z up", "o " + name]
        lines += ["v %.5f %.5f %.5f" % tuple(v) for v in self.v]
        lines += ["vt %.5f %.5f" % tuple(uv) for uv in self.uv]
        lines += ["f " + " ".join(f"{k+1}/{k+1}" for k in self.t[i:i+3]) for i in range(0,len(self.t),3)]
        (folder / (name + ".obj")).write_text("\n".join(lines) + "\n")


def meshes():
    # Small bevels catch moonlight without the cost of dense sculpted blocks.
    m = Mesh()
    rings = [(-50,47),(-47,50),(47,50),(50,47)]
    for (z0,r0),(z1,r1) in zip(rings,rings[1:]):
        for i in range(4):
            q=[(-1,-1),(1,-1),(1,1),(-1,1)]
            a,b=q[i],q[(i+1)%4]
            m.face([(a[0]*r0,a[1]*r0,z0),(b[0]*r0,b[1]*r0,z0),
                    (b[0]*r1,b[1]*r1,z1),(a[0]*r1,a[1]*r1,z1)])
    m.face([(-47,47,-50),(47,47,-50),(47,-47,-50),(-47,-47,-50)])
    m.face([(-47,-47,50),(47,-47,50),(47,47,50),(-47,47,50)])
    m.save("SM_StoneBlock")
    m=Mesh(); m.box((0,0,0),(100,100,100)); m.save("SM_ConstructionBlock")
    m=Mesh()
    m.box((-337.5,0,175),(75,110,350)); m.box((337.5,0,175),(75,110,350))
    inner=[]
    for i in range(17):
        t=i/16
        inner.append((-300*(1-t)**2-600*(1-t)*t, 350*(1-t)**2+1160*(1-t)*t+700*t*t))
    points=inner+ [(-x,z) for x,z in inner[-2::-1]]
    for (x0,z0),(x1,z1) in zip(points,points[1:]):
        # Extruded voussoir strip, actual open centre; collision uses the triangles.
        dx,dz=x1-x0,z1-z0; length=math.hypot(dx,dz)
        ox,oz=-dz/length*75,dx/length*75
        a=(x0,z0); b=(x1,z1); c=(x1+ox,z1+oz); d=(x0+ox,z0+oz)
        for yy,order in [(-55,(a,b,c,d)),(55,(d,c,b,a))]:
            m.face([(x,yy,z) for x,z in order])
        for p,q in [(a,b),(b,c),(c,d),(d,a)]:
            m.face([(p[0],-55,p[1]),(p[0],55,p[1]),(q[0],55,q[1]),(q[0],-55,q[1])])
    m.save("SM_PointedArch",True)
    m=Mesh(); m.lathe([(0,0),(115,0),(115,24),(105,36),(105,65),(88,82),(78,110),
        (68,160),(63,820),(70,860),(94,880),(104,915),(110,960),(115,975),(115,1000),(0,1000)])
    # Rings form restrained carved bands.
    for z in [170,195,790,815]:
        m.lathe([(67,z),(72,z+3),(72,z+10),(67,z+14)],32)
    m.save("SM_CarvedPillar")
    m=Mesh(); m.box((0,0,100),(100,100,12))
    for x in [-38,38]:
        for y in [-38,38]: m.box((x,y,47),(10,10,94))
    m.box((0,0,75),(86,86,8)); m.save("SM_Table",True)
    m=Mesh(); m.box((0,0,48),(52,52,9)); m.box((-23,0,96),(7,52,85))
    for x in [-20,20]:
        for y in [-20,20]: m.box((x,y,23),(7,7,46))
    m.box((-18,0,138),(10,56,8)); m.save("SM_Chair",True)
    profiles={
        "SM_Goblet":[(0,0),(7,0),(8,2),(3,4),(2,15),(7,18),(10,27),(9,31),(8,30),(7,24),(0,20)],
        "SM_Plate":[(0,0),(13,0),(17,3),(18,5),(16,6),(11,3),(0,2)],
        "SM_Bowl":[(0,0),(7,0),(16,10),(18,16),(16,17),(13,9),(0,3)],
        "SM_Urn":[(0,0),(20,0),(22,5),(19,12),(35,30),(38,48),(26,73),(14,80),(14,92),(19,96),(18,100),(12,100),(10,88),(0,85)],
        "SM_CandleHolder":[(0,0),(12,0),(12,4),(5,9),(3,30),(11,34),(12,38),(0,38)],
        "SM_Candle":[(0,0),(4,0),(4,24),(3,26),(0,25)],
        "SM_Flame":[(0,0),(3,3),(2,9),(0,17)],
        "SM_MemoryPedestal":[(0,0),(50,0),(50,12),(35,20),(30,80),(52,98),(54,105),(0,105)]}
    for name,profile in profiles.items():
        m=Mesh(); m.lathe(profile,24); m.save(name)
    m=Mesh()
    # Blade extends from hand at origin along local Z; slightly curved saif silhouette.
    for i in range(12):
        z0,z1=12+i*6.5,12+(i+1)*6.5
        x0,x1=(i/12)**2*12,((i+1)/12)**2*12
        w0,w1=3*(1-i/14),3*(1-(i+1)/14)
        m.face([(x0-w0,-.6,z0),(x0+w0,-.6,z0),(x1+w1,-.6,z1),(x1-w1,-.6,z1)])
        m.face([(x0+w0,.6,z0),(x0-w0,.6,z0),(x1-w1,.6,z1),(x1+w1,.6,z1)])
        for s in [-1,1]: m.face([(x0+s*w0,-.6,z0),(x1+s*w1,-.6,z1),(x1+s*w1,.6,z1),(x0+s*w0,.6,z0)])
    m.box((0,0,10),(20,3,3)); m.box((0,0,0),(3,3,18)); m.save("SM_TemporarySaif")
    m=Mesh()
    for i in range(8):
        a=i*math.pi/4; b=a+math.pi/8; c=a+math.pi/4
        m.face([(0,0,3),(46*math.cos(a),46*math.sin(a),3),(20*math.cos(b),20*math.sin(b),3),
                (46*math.cos(c),46*math.sin(c),3)])
    m.save("SM_EightPointSeal")
    m=Mesh(); m.box((0,0,3),(45,34,6)); m.save("SM_Storybook")
    m=Mesh(); m.box((0,0,0),(25,9,15)); m.box((11,0,11),(7,8,20)); m.box((14,0,23),(15,9,7))
    for x in [-8,8]:
        for y in [-3,3]: m.box((x,y,-12),(3,3,15))
    m.save("SM_WoodenHorse",True)
    m=Mesh()
    for x in range(12):
        for y in range(8):
            def p(a,b): return (a/12*100-50,b/8*100-50,1.8*math.sin(a*.8)*math.sin(b*.7))
            m.face([p(x,y),p(x+1,y),p(x+1,y+1),p(x,y+1)],
                   [(x/12,y/8),((x+1)/12,y/8),((x+1)/12,(y+1)/8),(x/12,(y+1)/8)])
    m.save("SM_WovenCloth",True)


def png(path, width, height, raw):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    rows=b''.join(b'\0'+raw[y*width*3:(y+1)*width*3] for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
                     chunk(b'IDAT',zlib.compress(rows,8))+chunk(b'IEND',b''))


def textures():
    folder=OUT/'Textures'; folder.mkdir(parents=True,exist_ok=True)
    n=512
    def hashnoise(x,y):
        h=(x*374761393+y*668265263+19)&0xffffffff
        h=((h^(h>>13))*1274126177)&0xffffffff
        return (h&65535)/65535
    def smoothnoise(x,y,size):
        fx,fy=x/size,y/size;ix,iy=math.floor(fx),math.floor(fy)
        u,v=fx-ix,fy-iy;u=u*u*(3-2*u);v=v*v*(3-2*v)
        a=hashnoise(ix,iy)*(1-u)+hashnoise(ix+1,iy)*u
        b=hashnoise(ix,iy+1)*(1-u)+hashnoise(ix+1,iy+1)*u
        return a*(1-v)+b*v
    palettes={'Stone':(145,128,100),'Limestone':(175,163,138),'Wood':(64,37,24),
              'Carpet':(95,20,28),'Cloth':(108,24,34),'Bronze':(122,82,36),
              'Ceramic':(87,115,119),'Parchment':(191,172,127)}
    for kind,color in palettes.items():
        pixels=bytearray(); orm=bytearray()
        for y in range(n):
            for x in range(n):
                grain=hashnoise(x,y)-.5
                patch=smoothnoise(x,y,42)-.5
                v=1+grain*.10+patch*.22
                c=color
                if kind in ('Stone','Limestone'):
                    row=y//128; tx=(x+(row%2)*128)%256
                    seam=min(tx,256-tx,y%128,128-y%128)
                    if seam<2: v*=.54
                    elif seam<5: v*=1.09
                    v*=1+.07*math.sin(x*.04+math.sin(y*.025))
                elif kind=='Wood':
                    v*=.87+.13*math.sin(x*.16+4*math.sin(y*.005))+.04*math.sin(x*.9)
                elif kind in ('Carpet','Cloth'):
                    v*=.88+.12*((x+y)%2)
                    if kind=='Carpet':
                        border=min(x,y,n-1-x,n-1-y)
                        dx,dy=abs(x-n/2),abs(y-n/2)
                        radius=math.hypot(dx,dy)
                        theta=math.atan2(y-n/2,x-n/2)
                        star=112*(.77+.23*math.cos(8*theta))
                        if border<7 or (29<border<34) or abs(dx+dy-175)<3 or abs(radius-star)<3 or abs(radius-36)<2:
                            c=(153,111,61)
                        if 10<border<25:
                            along=x if min(y,n-1-y)<25 else y
                            if abs((along%24)-12)+abs(border-17)<7:c=(163,119,65)
                elif kind=='Bronze':
                    patina=max(0,min(1,(smoothnoise(x,y,25)-.63)*5))
                    c=tuple(color[i]*(1-patina)+(65,92,71)[i]*patina for i in range(3))
                elif kind=='Parchment':
                    edge=min(x,y,n-1-x,n-1-y)
                    v*=min(1,.45+edge/42)
                    if y%39<3 and 65<x<445: v*=.62
                pixels.extend(max(0,min(255,int(k*v))) for k in c)
                rough=.87 if kind not in ('Bronze','Ceramic') else .42
                orm.extend((255,max(0,min(255,int((rough+grain*.12)*255))),220 if kind=='Bronze' else 0))
        png(folder/f'T_{kind}_BaseColor.png',n,n,bytes(pixels))
        png(folder/f'T_{kind}_ORM.png',n,n,bytes(orm))
    # Intentionally damaged pictorial clue, no major lore text.
    data=bytearray()
    for y in range(n):
        for x in range(n):
            c=(43,51,59)
            if (x-260)**2+(y-135)**2<70**2: c=(183,160,111)
            if 125<x<390 and 230<y<430: c=(93,64,46)
            if 202<x<312 and 290<y<430: c=(23,29,38)
            if abs(x-(270+20*math.sin(y*.018)))<8: c=(33,28,25)
            v=.90+hashnoise(x,y)*.15
            data.extend(int(k*v) for k in c)
    png(folder/'T_ForgottenHouse_BaseColor.png',n,n,bytes(data))


def audio():
    folder=OUT/'Audio'; folder.mkdir(parents=True,exist_ok=True)
    rate=22050
    for name,duration in [('Swing',.4),('Impact',.28),('Step',.15),('HouseAmbience',16)]:
        rng=random.Random(17); values=[]; low=0
        for i in range(int(rate*duration)):
            t=i/rate; white=rng.uniform(-1,1); low=.98*low+.02*white
            if name=='Swing': value=white*.12*math.sin(math.pi*t/duration)**2
            elif name=='Impact': value=(math.sin(2*math.pi*147*t)*.35+white*.18)*math.exp(-t*24)
            elif name=='Step': value=(low*.8+white*.13)*math.exp(-t*38)
            else:
                # Integer periodic tones and fade both ends avoid loop seam clicks.
                fade=min(1,t/1.5,(duration-t)/1.5)
                value=fade*(low*.45+math.sin(2*math.pi*55*t)*.04+math.sin(2*math.pi*82.5*t)*.025)
            values.append(struct.pack('<h',int(max(-1,min(1,value))*32767)))
        with wave.open(str(folder/f'S_{name}.wav'),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(b''.join(values))


def generate():
    meshes(); textures(); audio()
    print(f'Original procedural source assets generated in {OUT}')


if __name__=='__main__': generate()
