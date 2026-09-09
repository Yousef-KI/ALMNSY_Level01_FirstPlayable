"""Engine-independent integrity and spatial checks; NOT a UE compile or playtest.

Runs the actual environment assembly functions with recording backends, checks
source geometry/references, and flood-fills a conservative 50cm collision grid.
The optional Pillow preview is a plan view, explicitly not an Unreal screenshot.
"""
from pathlib import Path
import ast
import collections
import json
import math
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from layout import ROOMS, ENEMIES, INTERACTIONS, SEALS, PLAYER_START, walkable


def capture():
    instances=[];lights=[];physics=[]
    def instance(mesh,mat,p,scale=(1,1,1),rotation=(0,0,0),collision=True):
        instances.append(dict(mesh=mesh,material=mat,position=p,scale=scale,rotation=rotation,collision=collision))
    def static(mesh,mat,name,p,scale=(1,1,1),rotation=(0,0,0),physics=False):
        instance(mesh,mat,p,scale,rotation,not physics)
        if physics: physics_objects.append(name)
    physics_objects=[]
    class Stub:
        def __getattr__(self,_):return self
        def __call__(self,*args,**kwargs):return self
    ns=dict(ROOMS=ROOMS,instance=instance,static=static,vec=lambda p:p,ue=Stub(),MATS=collections.defaultdict(Stub),
        spawn=Stub(),point=lambda *a,**k:lights.append(('point',a,k)),rect=lambda *a,**k:lights.append(('rect',a,k)))
    tree=ast.parse((ROOT/'Scripts/Build_ALMNSY_Level01.py').read_text())
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in
              {'box','candles','arch','architecture','grand_hall','dressing'}]
    exec(compile(ast.Module(body=selected,type_ignores=[]),'assembly_recording','exec'),ns)
    ns['architecture']();ns['grand_hall']();ns['dressing']()
    return instances,lights,physics_objects


def validate_geometry():
    summary={}
    for file in sorted((ROOT/'SourceArt/Level01/Meshes').glob('*.json')):
        m=json.loads(file.read_text());v=m['vertices'];tri=m['triangles']
        assert len(v)==len(m['uvs']) and len(tri)%3==0,file
        assert all(0<=k<len(v) for k in tri),file
        assert all(math.isfinite(x) for p in v for x in p),file
        for i in range(0,len(tri),3):
            a,b,c=[v[k] for k in tri[i:i+3]]
            u=[b[k]-a[k] for k in range(3)];w=[c[k]-a[k] for k in range(3)]
            cross=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]]
            assert sum(x*x for x in cross)>1e-12, f'Degenerate triangle: {file.name} #{i//3}'
        summary[file.stem]=dict(vertices=len(v),triangles=len(tri)//3)
    return summary


def collision_grid(instances):
    # Conservative AABBs for solid meshes at standing height. Open arches use
    # the separate leg bounds, never the full bounds across their openings.
    bounds=[]
    def add(p,dimensions,yaw=0):
        x,y,z=p;dx,dy,dz=dimensions
        if z+dz/2<=8 or z-dz/2>=190:return
        r=math.radians(yaw)
        hx=(abs(math.cos(r))*dx+abs(math.sin(r))*dy)/2+48
        hy=(abs(math.sin(r))*dx+abs(math.cos(r))*dy)/2+48
        bounds.append((x-hx,x+hx,y-hy,y+hy))
    for item in instances:
        if not item['collision']:continue
        mesh=item['mesh'];p=item['position'];s=item['scale'];yaw=item['rotation'][1]
        if mesh in ('SM_StoneBlock','SM_ConstructionBlock'):add(p,[100*k for k in s],yaw)
        elif mesh=='SM_PointedArch':
            r=math.radians(yaw)
            for sign in [-1,1]:
                dx=sign*337.5*s[0]
                add((p[0]+dx*math.cos(r),p[1]+dx*math.sin(r),p[2]+175*s[2]),(75*s[0],110*s[1],350*s[2]),yaw)
        elif mesh=='SM_CarvedPillar':add((p[0],p[1],p[2]+500*s[2]),(230*s[0],230*s[1],1000*s[2]))
        elif mesh=='SM_Urn':add((p[0],p[1],p[2]+50*s[2]),(76*s[0],76*s[1],100*s[2]))
        elif mesh=='SM_Chair':add((p[0],p[1],p[2]+70*s[2]),(56*s[0],56*s[1],140*s[2]),yaw)
    for _,kind,p,_,_,_ in INTERACTIONS:
        if kind!='Memory':add((p[0],p[1],52),(108,108,105))
    blocked=set()
    for a,b,c,d in bounds:
        for ix in range(math.floor(a/50),math.ceil(b/50)+1):
            for iy in range(math.floor(c/50),math.ceil(d/50)+1):
                if a<=ix*50<=b and c<=iy*50<=d:blocked.add((ix,iy))
    valid={(x,y) for x in range(1,568) for y in range(-50,51) if walkable(x*50,y*50) and (x,y) not in blocked}
    start=(round(PLAYER_START[0]/50),round(PLAYER_START[1]/50))
    seen={start};q=collections.deque([start])
    while q:
        x,y=q.popleft()
        for node in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
            if node in valid and node not in seen:seen.add(node);q.append(node)
    destinations={'story':(7300,150),'shrine':(16300,100),'study':(24600,150),
                  'end':(27600,0),'optional_alcove':(5150,1400)}
    for name,(x,y) in destinations.items():
        assert (round(x/50),round(y/50)) in seen,f'Unreachable interaction approach: {name}'
    for name,group,tough,(x,y,z) in ENEMIES:
        assert (round(x/50),round(y/50)) in seen,f'Guard trapped in static layout: {name}'
    for _,_,_,p,_,_ in INTERACTIONS:
        assert (round(p[0]/50),round(p[1]/50)) in seen,'Checkpoint overlaps static obstacle'
    return valid,blocked,seen


def references():
    native='\n'.join(p.read_text() for p in (ROOT/'Source/ALMNSY_Level01/Chapter').glob('*.cpp'))
    paths=set(re.findall(r'"(/Game/[^"\s]+)"',native))
    original=[];generated=[]
    for path in paths:
        if path.startswith('/Game/ALMNSY/'):
            generated.append(path)
        else:
            assert (ROOT/'Content'/ (path[len('/Game/'):]+'.uasset')).is_file(),f'Missing dependency: {path}'
            original.append(path)
    for source in ROOT.glob('Source/**/*.h'):
        if 'Chapter' not in str(source) and 'EditorTools' not in str(source):continue
        includes=re.findall(r'#include "([^"]+)"',source.read_text())
        assert includes[-1].endswith('.generated.h'),source
    return dict(existing_dependencies=sorted(original),generated_runtime_dependencies=sorted(generated))


def preview(instances,valid,blocked,seen):
    try:from PIL import Image,ImageDraw,ImageFont
    except ImportError:return
    out=ROOT/'Documentation/Level01';out.mkdir(parents=True,exist_ok=True)
    im=Image.new('RGB',(1600,570),(17,21,28));draw=ImageDraw.Draw(im)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16) if Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf').exists() else ImageFont.load_default()
    draw.text((36,24),'ALMNSY / CHAPTER I — SOURCE LAYOUT VALIDATION',font=font,fill=(219,201,169))
    draw.text((36,52),'Plan view of generated geometry · not an Unreal render or playtest',font=font,fill=(153,164,180))
    scale=.052
    def p(x,y):return (42+x*scale,302+y*scale)
    for name,a,b,w,h,roof in ROOMS:
        draw.rectangle([p(a,-w),p(b,w)],fill=(78,65,52),outline=(179,154,114),width=2)
    for x,y in blocked:
        if walkable(x*50,y*50):
            px,py=p(x*50,y*50);draw.rectangle((px-1,py-1,px+1,py+1),fill=(24,28,34))
    for x,y in seen:
        if y==0:
            px,py=p(x*50,y*50);draw.point((px,py),fill=(117,148,149))
    for name,g,heavy,(x,y,z) in ENEMIES:
        px,py=p(x,y);r=6 if heavy else 4
        draw.ellipse((px-r,py-r,px+r,py+r),fill=(200,70,63))
    for label,kind,(x,y,z),_,_,_ in INTERACTIONS:
        px,py=p(x,y);draw.rectangle((px-4,py-4,px+4,py+4),fill=(96,190,215))
    for label,x in [('ARRIVAL',400),('STORY',6800),('FIRST GUARD',8900),('INNER CHAMBER',12500),('SHRINE',15600),('GRAND HALL',18500),('STUDY',23800),('GATE',26700)]:
        px,_=p(x,0);draw.text((px,460),label,font=font,fill=(219,201,169))
    draw.text((36,520),'10 placed guards · 2 heavy variants · 3 combat groups · 5 interactions · continuous floor route',font=font,fill=(153,164,180))
    im.save(out/'SourceLayout.png')
    samples=[]
    for name in ['Stone','Limestone','Wood','Carpet','Cloth','Bronze','Ceramic','Parchment']:
        tile=Image.open(ROOT/f'SourceArt/Level01/Textures/T_{name}_BaseColor.png').resize((220,220))
        samples.append((name,tile))
    atlas=Image.new('RGB',(1000,600),(17,21,28));d=ImageDraw.Draw(atlas)
    for i,(name,tile) in enumerate(samples):
        x=22+(i%4)*246;y=20+(i//4)*290
        atlas.paste(tile,(x,y));d.text((x,y+230),name,font=font,fill=(219,201,169))
    atlas.save(out/'SourceMaterialPalette.png')


def main():
    for p in (ROOT/'Scripts').rglob('*.py'):ast.parse(p.read_text())
    assert len({e[0] for e in ENEMIES})==len(ENEMIES)
    assert 8<=len(ENEMIES)<=12 and sum(e[2] for e in ENEMIES)==2
    for x,group,_,_ in SEALS:
        assert all(e[3][0]<x for e in ENEMIES if e[1]<=group), 'Gate requires a guard locked behind itself'
    geometry=validate_geometry();refs=references()
    instances,lights,physics=capture()
    assert len(physics)>=6
    assert all(i['mesh'] in geometry for i in instances)
    valid,blocked,seen=collision_grid(instances)
    result=dict(status='STATIC_CHECKS_PASSED_NOT_ENGINE_TESTED',mesh_count=len(geometry),meshes=geometry,
        instance_count=len(instances),light_count=len(lights),physics_props=len(physics),
        reachable_grid_cells=len(seen),references=refs,
        unverified=['UnrealHeaderTool and C++ compilation','Editor Python API execution','NavMesh build',
                    'Actual Chaos collision','PIE checkpoint/death/completion','visuals and FPS','packaged build'])
    dest=ROOT/'Documentation/Level01';dest.mkdir(parents=True,exist_ok=True)
    (dest/'StaticValidation.json').write_text(json.dumps(result,indent=2)+'\n')
    preview(instances,valid,blocked,seen)
    print(json.dumps({k:v for k,v in result.items() if k not in ('meshes','references')},indent=2))


if __name__=='__main__':main()
