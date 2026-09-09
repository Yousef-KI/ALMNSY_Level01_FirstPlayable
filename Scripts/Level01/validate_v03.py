"""Static source/spatial/native-rule checks. This never claims an Unreal playtest."""
from pathlib import Path
from types import SimpleNamespace
import ast
import collections
import json
import math
import re
import subprocess
import sys
import tempfile
import shutil

ROOT=Path(__file__).resolve().parents[2]
BASE='639c17d1811b0ea7a869c906fa05bfeeb4901b00'
ART=ROOT/'SourceArt/Level01_v03'
OUT=ROOT/'Documentation/Level01/v03'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from layout import ROOMS,ENEMIES,INTERACTIONS,SEALS,PLAYER_START,walkable
from refinement_layout import hall_details,route_details,vista,chair_yaw


class Stub:
    def __getattr__(self,_):return self
    def __call__(self,*a,**k):return self


def capture():
    instances=[];lights=[]
    def record(mesh,mat,p,scale=(1,1,1),rotation=(0,0,0),collision=True,physics=False):
        instances.append(dict(mesh=mesh,material=mat,p=p,scale=scale,rotation=rotation,collision=collision,physics=physics))
    def static(mesh,mat,name,p,scale=(1,1,1),rotation=(0,0,0),physics=False):record(mesh,mat,p,scale,rotation,not physics,physics)
    ns=dict(ROOMS=ROOMS,static=static,ue=Stub(),spawn=Stub(),vec=lambda p:p,MATS=collections.defaultdict(Stub))
    tree=ast.parse((ROOT/'Scripts/Build_ALMNSY_Level01.py').read_text())
    names={'architecture','grand_hall','dressing','box','arch','candles'}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'baseline_layout','exec'),ns)
    backend=SimpleNamespace(**{k:v for k,v in ns.items() if not k.startswith('__')})
    refined=dict(b=backend,OLD_INSTANCE=record,OLD_POINT=lambda *a,**k:lights.append(('point',a,k)),
                 OLD_RECT=lambda *a,**k:lights.append(('rect',a,k)))
    tree=ast.parse((ROOT/'Scripts/Build_ALMNSY_v03.py').read_text())
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'instance','point','rect'}],type_ignores=[]),'v03_layout','exec'),refined)
    for name in ['instance','point','rect']:
        ns[name]=refined[name];setattr(backend,name,refined[name])
    ns['architecture']();ns['grand_hall']();ns['dressing']()
    hall_details(backend);route_details(backend);vista(backend)
    return instances,lights


def geometry():
    meshes={};report={}
    for path in sorted((ART/'Meshes').glob('*.json')):
        m=json.loads(path.read_text());v=m['vertices'];tri=m['triangles'];uv=m['uvs'];volume=0
        assert len(uv)==len(v) and len(tri)%3==0,path
        assert all(len(p)==3 and all(math.isfinite(x) for x in p) for p in v),path
        assert all(0<=i<len(v) for i in tri),path
        for j in range(0,len(tri),3):
            a,b,c=[v[i] for i in tri[j:j+3]];u=[b[k]-a[k] for k in range(3)];w=[c[k]-a[k] for k in range(3)]
            cross=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]]
            assert sum(x*x for x in cross)>1e-12,(path,j)
            volume+=sum(a[k]*cross[k] for k in range(3))/6
        extent=[max(p[k] for p in v)-min(p[k] for p in v) for k in range(3)]
        if path.stem!='SM_WovenCloth':assert min(extent)>.5 and volume>0,path
        meshes[path.stem]=m
        report[path.stem]={'triangles':len(tri)//3,'extent_cm':extent,'signed_volume_cm3':round(volume,2)}
    assert meshes['SM_PointedArch']['complex_collision'],'No convex doorway collision'
    assert report['SM_PointedArch']['extent_cm'][1]>=180
    assert report['SM_EightPointSeal']['extent_cm'][2]>=9
    assert report['SM_CarvedPillar']['extent_cm'][0]>=200
    return meshes,report


def spatial(instances,meshes):
    bounds=[]
    def add(x,y,z,dx,dy,dz,yaw):
        if z+dz/2<=8 or z-dz/2>=190:return
        r=math.radians(yaw);hx=(abs(math.cos(r))*dx+abs(math.sin(r))*dy)/2+48;hy=(abs(math.sin(r))*dx+abs(math.cos(r))*dy)/2+48
        bounds.append((x-hx,x+hx,y-hy,y+hy))
    for i in instances:
        assert i['mesh'] in meshes,i['mesh']
        if not i['collision']:continue
        x,y,z=i['p'];sx,sy,sz=i['scale'];yaw=i['rotation'][1]
        if i['mesh']=='SM_PointedArch':
            for sign in [-1,1]:
                dx=sign*340*sx;r=math.radians(yaw)
                add(x+dx*math.cos(r),y+dx*math.sin(r),z+175*sz,80*sx,180*sy,350*sz,yaw)
        else:
            v=meshes[i['mesh']]['vertices'];mins=[min(p[k] for p in v) for k in range(3)];maxs=[max(p[k] for p in v) for k in range(3)]
            # Solid placement rotation is yaw-only; pitched decorative pieces are non-colliding.
            assert i['rotation'][0]==0 and i['rotation'][2]==0,i
            add(x,y,z+(mins[2]+maxs[2])/2*sz,(maxs[0]-mins[0])*sx,(maxs[1]-mins[1])*sy,(maxs[2]-mins[2])*sz,yaw)
    for _,kind,p,_,_,_ in INTERACTIONS:
        if kind!='Memory':add(p[0],p[1],52,108,108,105,0)
    blocked=set()
    for a,b,c,d in bounds:
        for x in range(max(0,math.floor(a/50)),min(569,math.ceil(b/50)+1)):
            for y in range(max(-52,math.floor(c/50)),min(53,math.ceil(d/50)+1)):
                if a<=x*50<=b and c<=y*50<=d:blocked.add((x,y))
    valid={(x,y) for x in range(1,568) for y in range(-50,51) if walkable(x*50,y*50) and (x,y) not in blocked}
    start=(round(PLAYER_START[0]/50),round(PLAYER_START[1]/50));seen={start};queue=collections.deque([start])
    while queue:
        x,y=queue.popleft()
        for n in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
            if n in valid and n not in seen:seen.add(n);queue.append(n)
    destinations={n:(p[0],p[1]) for n,_,_,p in ENEMIES}
    destinations.update({n+'_checkpoint':(p[0],p[1]) for n,_,_,p,_,_ in INTERACTIONS})
    destinations.update(story=(7300,150),shrine=(16300,100),study=(24600,150),end=(27600,0),alcove=(5150,1400))
    for name,(x,y) in destinations.items():assert (round(x/50),round(y/50)) in seen,f'Unreachable {name}'
    chairs=[i for i in instances if i['mesh']=='SM_Chair' and 19000<i['p'][0]<22000 and abs(i['p'][1])<=300]
    assert len(chairs)==16
    for c in chairs:
        yaw=math.radians(c['rotation'][1]);to_table=(0,-c['p'][1]) if c['p'][1] else (20400-c['p'][0],0)
        facing=(math.cos(yaw)*to_table[0]+math.sin(yaw)*to_table[1])/math.hypot(*to_table)
        assert facing>.999,c
    assert len({e[0] for e in ENEMIES})==10
    for x,group,_,_ in SEALS:
        assert all(p[0]<x for _,g,_,p in ENEMIES if g<=group),'Gate requires a guard beyond itself'
    return {'reachable_cells':len(seen),'checked_destinations':len(destinations),'inward_facing_chairs':len(chairs)},seen


def sources():
    for path in (ROOT/'Scripts').rglob('*.py'):ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    protected=subprocess.check_output(['git','diff',BASE,'--name-only','--','Content','Config','SourceArt/Level01'],cwd=ROOT,text=True)
    assert not protected,'Protected baseline assets/config/source art were changed: '+protected
    actor=(ROOT/'Source/ALMNSY_Level01/Chapter/V03/ALMNSYFighterV03.cpp').read_text()
    anim=(ROOT/'Source/ALMNSY_Level01/Chapter/V03/ALMNSYAnimV03.cpp').read_text()
    old=(ROOT/'Source/ALMNSY_Level01/Chapter/ALMNSYFighter.cpp').read_text()
    assert 'SetBlendSpacePosition' in old and 'SetBlendSpaceInput' not in old
    assert 'Engine/Model.h' not in (ROOT/'Source/ALMNSYEditorTools/ALMNSYEditorLibrary.cpp').read_text()
    assert 'SetMovementMode(MOVE_Walking)' not in actor,'Recovery must not unfreeze death/completion'
    swing=actor.split('void AALMNSYFighterV03::BeginSwing()')[1].split('void AALMNSYFighterV03::StopAction()')[0]
    assert 'DisableMovement' not in swing
    assert actor.index('bDead=true')<actor.index('D->GuardFell(GuardId)')
    assert 'Facing>=FrontalDot' in actor and 'CanCancel(AttackPhase)' in actor
    assert 'P->Attacks' not in anim and 'SwingPose' in anim,'No reused punching sequences in v03 sword graph'
    progression=(ROOT/'Source/ALMNSY_Level01/Chapter/ALMNSYProgression.cpp').read_text()
    assert 'لقد كبرت' in progression and 'I->Use(this)' in actor
    for path in (ROOT/'Source/ALMNSY_Level01/Chapter').rglob('*.h'):
        if 'UCLASS' in path.read_text():assert re.findall(r'#include "([^"]+)"',path.read_text())[-1].endswith('.generated.h'),path
    refs=set(re.findall(r'TEXT\("(/Game/[^"\s]+)"\)',actor+old))
    for ref in refs:
        if ref.endswith('/'):continue
        if '/Versions/v03/' not in ref:assert (ROOT/'Content'/ (ref[len('/Game/'):]+'.uasset')).is_file(),ref
        elif '/Audio/' in ref:assert (ART/'Audio'/(ref.rsplit('/',1)[1]+'.wav')).is_file(),ref
        elif '/Environment/' in ref:assert (ART/'Meshes'/(ref.rsplit('/',1)[1]+'.json')).is_file(),ref
    for sound in ['Swing','Impact','Block','Parry','Memory','Death','Wind']:assert (ART/f'Audio/S_{sound}.wav').is_file()
    # Images can be decoded, normal/height/ORM maps exist for every PBR family.
    from PIL import Image
    for kind in ['Stone','Limestone','Wood','Cloth','Carpet','Bronze','Ceramic','Parchment','Wax']:
        for suffix in ['BaseColor','ORM','Normal','Height']:
            with Image.open(ART/f'Textures/T_{kind}_{suffix}.png') as im:assert im.size==(1024,1024);im.load()
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    return {'protected_v02_paths_unchanged':True,'python_syntax':'passed','compatibility_regressions_checked':True}


def combat():
    compiler=shutil.which('g++') or shutil.which('clang++')
    assert compiler,'A C++17 compiler is required for the engine-independent rule tests'
    with tempfile.TemporaryDirectory(prefix='almnsy-v03-rules-') as temp:
        exe=Path(temp)/'combat_rules'
        subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I'+str(ROOT/'Source/ALMNSY_Level01'),
            str(ROOT/'Scripts/Level01/test_combat_v03.cpp'),'-o',str(exe)],check=True)
        output=subprocess.check_output([str(exe)],text=True)
        (OUT/'SwordTrajectories.csv').write_text('combo,phase,hand_x,hand_y,hand_z,blade_x,blade_y,blade_z\n'+output)
    return 'passed: native rule header + sword choreography at 12/30/60/144 fps'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    meshes,geometry_report=geometry();instances,lights=capture();space,seen=spatial(instances,meshes)
    report={'status':'STATICALLY_VERIFIED_NOT_UNREAL_PLAYTESTED','base_commit':BASE,'source_checks':sources(),
        'geometry':geometry_report,'spatial':space,'instances':len(instances),'environment_lights':len(lights),
        'physics_props':sum(i['physics'] for i in instances),'native_combat_rules':combat(),
        'requires_local_ue58':['UHT/C++ project build','material shader compilation','v03 editor generation','skeletal IK and sword grip',
            'actual Chaos/NavMesh traversal','sword contact at 30/60 FPS','dodge collision/cancel','frontal and rear block/parry',
            'death/checkpoint/relaunch/save isolation','lighting/exposure/FPS','full route/completion','packaged build']}
    (OUT/'StaticValidation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='geometry'},indent=2))


if __name__=='__main__':main()
