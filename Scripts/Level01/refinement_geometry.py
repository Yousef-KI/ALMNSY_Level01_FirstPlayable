"""Original v03 kit. Does not write to SourceArt/Level01 or existing UE assets.

Centimetres; +Z up, chair faces +X. Every architectural part is a closed solid.
Reuses the baseline serializer and small props, then replaces the problem kit.
"""
from pathlib import Path
import json
import math
import generate_sources as legacy

OUT = Path(__file__).resolve().parents[2] / 'SourceArt/Level01_v03'


class Mesh(legacy.Mesh):
    def prism(self, polygon, depth, y=0):
        # polygon is clockwise in the X/Z plane: front normal points -Y.
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(polygon,polygon[1:]+polygon[:1]))
        if area < 0: polygon=list(reversed(polygon))
        front=[(x,y-depth/2,z) for x,z in polygon]
        back=[(x,y+depth/2,z) for x,z in polygon]
        self.face(front,[(x/180,z/180) for x,z in polygon])
        self.face(list(reversed(back)),[(x/180,z/180) for x,z in reversed(polygon)])
        for i in range(len(polygon)):
            j=(i+1)%len(polygon)
            self.face([front[i],back[i],back[j],front[j]])

    def ring(self, radius, thickness, z, height, segments=32):
        self.lathe([(radius-thickness,z),(radius,z),(radius,z+height),
                    (radius-thickness,z+height),(radius-thickness,z)],segments)

    def beveled_box(self, p, s, bevel=3):
        x,y,z=p; a,b,c=[v/2 for v in s]; d=min(bevel,a/3,b/3,c/3)
        rings=[]
        for zz,inset in [(-c,d),(-c+d,0),(c-d,0),(c,d)]:
            rings.append([(x-a+inset,y-b+d,z+zz),(x-a+d,y-b+inset,z+zz),
                (x+a-d,y-b+inset,z+zz),(x+a-inset,y-b+d,z+zz),
                (x+a-inset,y+b-d,z+zz),(x+a-d,y+b-inset,z+zz),
                (x-a+d,y+b-inset,z+zz),(x-a+inset,y+b-d,z+zz)])
        # End rings have duplicate corner vertices; use rectangular caps instead.
        self.face([(x-a+d,y-b+d,z-c),(x-a+d,y+b-d,z-c),
                   (x+a-d,y+b-d,z-c),(x+a-d,y-b+d,z-c)])
        self.face([(x-a+d,y-b+d,z+c),(x+a-d,y-b+d,z+c),
                   (x+a-d,y+b-d,z+c),(x-a+d,y+b-d,z+c)])
        for lo,hi in zip(rings,rings[1:]):
            for i in range(8):
                j=(i+1)%8
                points=[lo[i],lo[j],hi[j],hi[i]]
                points=[v for k,v in enumerate(points) if v!=points[k-1]]
                if len(points)>=3:self.face(points)


def arch_mesh():
    m=Mesh()
    for sign in [-1,1]:m.box((sign*340,0,175),(80,180,350))
    # Shared analytic inner/outer boundaries. No gaps or wedge inversions.
    for sign in [-1,1]:
        def curve(t,outer=False):
            x=-300+300*t*t; z=350+510*t-160*t*t
            dx,dz=600*t,510-320*t
            n=math.hypot(dx,dz)
            if outer:x-=80*dz/n;z+=80*dx/n
            return (sign*x,z)
        for i in range(24):
            a,b=i/24,(i+1)/24
            m.prism([curve(a),curve(b),curve(b,True),curve(a,True)],180)
        # Raised archivolt, still a real 12cm deep extrusion, set on the front.
        for i in range(24):
            a,b=i/24,(i+1)/24
            p,q=curve(a,True),curve(b,True)
            m.prism([p,q,(q[0]*1.035,q[1]+10),(p[0]*1.035,p[1]+10)],24,-99)
    m.prism([(-28,774),(0,700),(28,774),(0,803)],180)
    m.save('SM_PointedArch',True)


def generate():
    previous=legacy.OUT
    try:
        legacy.OUT=OUT
        legacy.meshes()
        arch_mesh()
        m=Mesh()
        # Octagonal plinth, tapered shaft, deep stepped capital. Total 1000cm.
        m.lathe([(0,0),(112,0),(112,24),(103,36),(103,68),(88,84),(77,122),
            (69,160),(60,790),(66,820),(88,845),(98,900),(110,930),(113,977),(113,1000),(0,1000)],32)
        for z,r in [(146,75),(172,72),(780,68),(815,75)]:m.ring(r,7,z,12)
        # Carved facets on capital instead of flat decorative planes.
        for i in range(8):
            a=i*math.pi/4;x,y=88*math.cos(a),88*math.sin(a)
            m.beveled_box((x,y,892),(24,24,70),5)
        m.save('SM_CarvedPillar',True)
        m=Mesh();m.beveled_box((0,0,0),(100,100,100),3);m.save('SM_StoneBlock')
        m=Mesh()
        for angle in range(8):
            a=angle*math.pi/4
            p=[(0,0),(46*math.cos(a),46*math.sin(a)),
               (20*math.cos(a+math.pi/8),20*math.sin(a+math.pi/8)),
               (46*math.cos(a+math.pi/4),46*math.sin(a+math.pi/4))]
            # Relief lies in XY, stands 9cm proud; closed sides cast real shadows.
            base=len(m.v);tmp=Mesh();tmp.prism(p,9)
            m.v.extend((x,z,-y+5) for x,y,z in tmp.v);m.uv.extend(tmp.uv);m.t.extend(i+base for i in tmp.t)
        m.save('SM_EightPointSeal',True)
        m=Mesh();m.beveled_box((0,0,48),(56,56,10),2)
        for x in [-21,21]:
            for y in [-21,21]:m.beveled_box((x,y,23),(7,7,46),1)
        for y in [-24,24]:m.beveled_box((-24,y,97),(9,9,95),2)
        m.beveled_box((-24,0,134),(10,58,12),2)
        for y in [-14,0,14]:m.beveled_box((-24,y,104),(6,7,48),1)
        for y in [-21,21]:m.box((0,y,21),(46,5,5))
        m.save('SM_Chair',True)
        m=Mesh();m.beveled_box((0,0,0),(100,100,30),3);m.save('SM_Cornice',True)
        m=Mesh();m.ring(100,8,0,16)
        for i in range(12):
            a=i*math.pi/6;x,y=94*math.cos(a),94*math.sin(a)
            m.beveled_box((x,y,24),(8,8,44),1)
        m.save('SM_Chandelier',True)
        m=Mesh()
        # Small cut lattice screen: solid struts with real openings.
        for x in [-50,50]:m.box((x,0,0),(7,14,110))
        for z in [-50,50]:m.box((0,0,z),(100,14,7))
        for x in [-30,-10,10,30]:m.box((x,0,0),(4,10,100))
        for z in [-30,-10,10,30]:m.box((0,0,z),(100,10,4))
        m.save('SM_Lattice',True)
        m=Mesh();m.lathe([(0,0),(180,0),(176,38),(165,62),(142,85),(110,107),(62,123),(0,130)],32)
        m.save('SM_VistaDome',True)
        m=Mesh()
        for i in range(9):
            x=-400+i*100;h=180+100*math.sin(i*1.72)+80*math.cos(i*.65)
            m.prism([(x,0),(x+100,0),(x+100,h+60),(x,h)],240)
        m.save('SM_VistaRidge',True)
        # Rebuild the temporary blade as closed extrusions; no inverted side face.
        m=Mesh()
        for i in range(12):
            a,b=i/12,(i+1)/12
            x0,x1=12*a*a,12*b*b;z0,z1=14+76*a,14+76*b
            w0,w1=3*(1-a*.95),3*(1-b*.95)
            m.prism([(x0-w0,z0),(x0+w0,z0),(x1+w1,z1),(x1-w1,z1)],1.2)
        m.beveled_box((0,0,11),(20,4,4),.8)
        m.lathe([(0,-10),(2,-10),(2,9),(0,9)],12)
        m.save('SM_TemporarySaif')
    finally:legacy.OUT=previous
    print('v03 closed mesh kit:', OUT)


if __name__=='__main__':generate()
