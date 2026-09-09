"""Run once via Tools > Execute Python Script after building the Editor target.

Creates only /Game/ALMNSY assets. Existing assets are reused without mutation;
an existing completed map is opened, never rebuilt or overwritten automatically.
Set ALMNSY_BUILD_VERSION=v02 before launch for a separate map iteration.
"""
from pathlib import Path
import collections
import json
import math
import os
import sys
import traceback
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts' / 'Level01'))
from layout import ROOMS, ENEMIES, INTERACTIONS, SEALS, PLAYER_START

VERSION = os.environ.get('ALMNSY_BUILD_VERSION', 'v01')
if not (VERSION.startswith('v') and VERSION[1:].isdigit()):
    raise ValueError('ALMNSY_BUILD_VERSION must be v01, v02, etc.')
BASE = '/Game/ALMNSY'
MAP = f'{BASE}/Levels/Level01/ALMNSY_Level01_FirstPlayable_{VERSION}'
ART = ROOT / 'SourceArt' / 'Level01'
REPORT = ROOT / 'Saved' / 'ALMNSY' / f'Build_{VERSION}.json'
ASSETS = ue.AssetToolsHelpers.get_asset_tools()
EAL = ue.EditorAssetLibrary
ACTORS = ue.get_editor_subsystem(ue.EditorActorSubsystem)
LEVEL = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
MEL = ue.MaterialEditingLibrary
MESHS = {}
MATS = {}
BATCHES = collections.defaultdict(list)
COUNT = collections.Counter()


def require(value, message):
    if not value: raise RuntimeError(message)
    return value


def vec(p): return ue.Vector(*p)
def rot(p): return ue.Rotator(pitch=p[0], yaw=p[1], roll=p[2])


def spawn(cls, label, position=(0,0,0), rotation=(0,0,0), folder='Gameplay'):
    actor = require(ACTORS.spawn_actor_from_class(cls, vec(position), rot(rotation)), f'Could not spawn {label}')
    actor.set_actor_label(label)
    actor.set_folder_path(f'ALMNSY/{folder}')
    COUNT['actors'] += 1
    return actor


def save(asset):
    require(EAL.save_loaded_asset(asset, only_if_is_dirty=False), f'Could not save {asset.get_name()}')


def texture(name): return require(ue.load_asset(f'{BASE}/Textures/{name}'), f'Missing texture {name}')


def import_sources():
    if not (ART / 'Meshes' / 'SM_PointedArch.json').exists():
        from generate_sources import generate
        generate()
    tasks=[]
    for sub, dest in [('Textures','Textures'),('Audio','Audio')]:
        for source in sorted((ART/sub).iterdir()):
            if EAL.does_asset_exist(f'{BASE}/{dest}/{source.stem}'): continue
            task=ue.AssetImportTask()
            task.set_editor_property('filename',str(source))
            task.set_editor_property('destination_path',f'{BASE}/{dest}')
            task.set_editor_property('destination_name',source.stem)
            task.set_editor_property('automated',True)
            task.set_editor_property('replace_existing',False)
            task.set_editor_property('save',True)
            tasks.append(task)
    ASSETS.import_asset_tasks(tasks)
    for task in tasks:
        require(task.get_editor_property('imported_object_paths'), f'Import failed: {task.filename}')
        for path in task.get_editor_property('imported_object_paths'):
            asset=ue.load_asset(path)
            if path.endswith('_ORM'):
                asset.set_editor_property('srgb',False)
                asset.set_editor_property('compression_settings',ue.TextureCompressionSettings.TC_MASKS)
            if asset.get_name()=='S_HouseAmbience': asset.set_editor_property('looping',True)
            save(asset)
    for source in sorted((ART/'Meshes').glob('*.json')):
        name=source.stem
        dest='Props' if name in {'SM_Goblet','SM_Plate','SM_Bowl','SM_Urn','SM_CandleHolder','SM_Candle','SM_Flame',
            'SM_TemporarySaif','SM_WoodenHorse','SM_Storybook'} else 'Architecture'
        path=f'{BASE}/Environment/{dest}/{name}'
        mesh=ue.load_asset(path)
        if not mesh:
            data=json.loads(source.read_text())
            mesh=require(ue.ALMNSYEditorLibrary.create_mesh(path,[vec(v) for v in data['vertices']],
                data['triangles'],[ue.Vector2D(*v) for v in data['uvs']],data['complex_collision']),f'Mesh build failed: {name}')
            save(mesh)
        MESHS[name]=mesh


def material(name, tex=None, color=(1,1,1), rough=.8, metal=0, world=False, emission=0, cloth=False):
    path=f'{BASE}/Materials/MI_{name}'
    old=ue.load_asset(path)
    if old: MATS[name]=old; return old
    master_path=f'{BASE}/Materials/M_{name}'
    mat=ue.load_asset(master_path)
    if not mat:
        mat=ASSETS.create_asset('M_'+name,f'{BASE}/Materials',ue.Material,ue.MaterialFactoryNew())
        mat.set_editor_property('two_sided',cloth)
        def expr(cls,**kwargs):
            e=MEL.create_material_expression(mat,cls)
            for k,v in kwargs.items(): e.set_editor_property(k,v)
            return e
        def connect(a,b,pin,output=''):
            require(MEL.connect_material_expressions(a,output,b,pin),f'Material link failed: {name}/{pin}')
        def binary(cls,a,b):
            e=expr(cls); connect(a,e,'A'); connect(b,e,'B'); return e
        def mask(a,channels):
            e=expr(ue.MaterialExpressionComponentMask,r='r' in channels,g='g' in channels,b='b' in channels,a=False)
            connect(a,e,'Input'); return e
        tint=expr(ue.MaterialExpressionConstant3Vector,constant=ue.LinearColor(*color))
        result=tint
        rough_texture=None
        if tex:
            t=texture(f'T_{tex}_BaseColor')
            orm=ue.load_asset(f'{BASE}/Textures/T_{tex}_ORM')
            if world:
                position=expr(ue.MaterialExpressionWorldPosition)
                scale=expr(ue.MaterialExpressionConstant,r=320.)
                uv3=binary(ue.MaterialExpressionDivide,position,scale)
                normal=expr(ue.MaterialExpressionPixelNormalWS)
                absolute=expr(ue.MaterialExpressionAbs); connect(normal,absolute,'Input')
                weights=[mask(absolute,c) for c in ('r','g','b')]
                norm=binary(ue.MaterialExpressionAdd,binary(ue.MaterialExpressionAdd,weights[0],weights[1]),weights[2])
                samples=[];rough_samples=[]
                for projection,w in zip(('gb','rb','rg'),weights):
                    sample=expr(ue.MaterialExpressionTextureSample,texture=t)
                    uv=mask(uv3,projection)
                    connect(uv,sample,'Coordinates')
                    weight=binary(ue.MaterialExpressionDivide,w,norm)
                    samples.append(binary(ue.MaterialExpressionMultiply,sample,weight))
                    if orm:
                        rs=expr(ue.MaterialExpressionTextureSample,texture=orm,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_MASKS)
                        connect(uv,rs,'Coordinates')
                        rough_samples.append(binary(ue.MaterialExpressionMultiply,mask(rs,'g'),weight))
                result=binary(ue.MaterialExpressionAdd,binary(ue.MaterialExpressionAdd,samples[0],samples[1]),samples[2])
                if rough_samples: rough_texture=binary(ue.MaterialExpressionAdd,binary(ue.MaterialExpressionAdd,rough_samples[0],rough_samples[1]),rough_samples[2])
            else:
                result=expr(ue.MaterialExpressionTextureSample,texture=t)
                if orm:
                    rough_texture=mask(expr(ue.MaterialExpressionTextureSample,texture=orm,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_MASKS),'g')
            result=binary(ue.MaterialExpressionMultiply,result,tint)
        require(MEL.connect_material_property(result,'',ue.MaterialProperty.MP_BASE_COLOR),f'Base color failed: {name}')
        rr=expr(ue.MaterialExpressionConstant,r=rough)
        if rough_texture:
            # Retain material-family roughness while adding small surface variation.
            variation=binary(ue.MaterialExpressionMultiply,rough_texture,expr(ue.MaterialExpressionConstant,r=.18))
            rr=binary(ue.MaterialExpressionAdd,variation,expr(ue.MaterialExpressionConstant,r=max(.05,rough-.09)))
        mm=expr(ue.MaterialExpressionConstant,r=metal)
        MEL.connect_material_property(rr,'',ue.MaterialProperty.MP_ROUGHNESS)
        MEL.connect_material_property(mm,'',ue.MaterialProperty.MP_METALLIC)
        if emission:
            emit=binary(ue.MaterialExpressionMultiply,tint,expr(ue.MaterialExpressionConstant,r=emission))
            MEL.connect_material_property(emit,'',ue.MaterialProperty.MP_EMISSIVE_COLOR)
        MEL.recompile_material(mat); save(mat)
    mi=ASSETS.create_asset('MI_'+name,f'{BASE}/Materials',ue.MaterialInstanceConstant,ue.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi,mat); save(mi); MATS[name]=mi
    return mi


def materials():
    material('Sandstone','Stone',world=True)
    material('PaleStone','Limestone',world=True)
    material('DarkStone','Stone',color=(.46,.48,.51),world=True)
    material('DarkWood','Wood',rough=.68,world=True)
    material('Burgundy','Cloth',cloth=True)
    material('Carpet','Carpet',cloth=True)
    material('Bronze','Bronze',rough=.42,metal=.82,world=True)
    material('Ceramic','Ceramic',rough=.28)
    material('Parchment','Parchment')
    material('Painting','ForgottenHouse')
    material('Wax',color=(.72,.57,.35),rough=.65)
    material('AgedMetal',color=(.36,.40,.43),rough=.32,metal=.86)
    material('Guard_Charcoal',color=(.10,.065,.05),rough=.6,metal=.35)
    material('Guard_Bronze',color=(.26,.12,.045),rough=.52,metal=.65)
    material('Flame',color=(1,.30,.055),emission=7)
    material('Memory',color=(.25,.58,1),emission=2)
    material('Moon',color=(.45,.61,.83),emission=1.5)


def instance(mesh, material_name, position, scale=(1,1,1), rotation=(0,0,0), collision=True):
    t=ue.MathLibrary.make_transform(vec(position),rot(rotation),vec(scale))
    BATCHES[(mesh,material_name,collision)].append(t)
    COUNT['instances']+=1


def box(material_name, position, dimensions, rotation=(0,0,0), collision=True, bevel=False):
    instance('SM_StoneBlock' if bevel else 'SM_ConstructionBlock',material_name,position,
             tuple(d/100 for d in dimensions),rotation,collision)


def static(mesh, mat, name, pos, scale=(1,1,1), rotation=(0,0,0), physics=False):
    a=spawn(ue.StaticMeshActor,name,pos,rotation,'PhysicsProps' if physics else 'Furniture')
    c=a.static_mesh_component
    c.set_mobility(ue.ComponentMobility.MOVABLE if physics else ue.ComponentMobility.STATIC)
    c.set_static_mesh(MESHS[mesh]); c.set_material(0,MATS[mat]); a.set_actor_scale3d(vec(scale))
    c.set_collision_profile_name('PhysicsActor' if physics else 'BlockAll')
    if physics:
        c.set_editor_property('can_ever_affect_navigation',False)
        c.set_collision_response_to_channel(ue.CollisionChannel.ECC_CAMERA,ue.CollisionResponseType.ECR_IGNORE)
        c.set_mass_override_in_kg('', .45, True)
        c.set_linear_damping(.3); c.set_angular_damping(.5); c.set_simulate_physics(True)
        COUNT['physics_props']+=1
    return a


def point(name,p,color=(1,.53,.23),intensity=700,radius=700,shadows=False):
    a=spawn(ue.PointLight,name,p,folder='Lighting')
    c=a.get_component_by_class(ue.PointLightComponent)
    c.set_mobility(ue.ComponentMobility.MOVABLE)
    c.set_light_color(ue.LinearColor(*color)); c.set_intensity(intensity)
    c.set_attenuation_radius(radius); c.set_cast_shadows(shadows)
    c.set_editor_property('source_radius',15.)
    COUNT['lights']+=1
    return a


def rect(name,p,rotation,color,intensity,width=500,height=400,radius=2200):
    a=spawn(ue.RectLight,name,p,rotation,'Lighting')
    c=a.get_component_by_class(ue.RectLightComponent)
    c.set_mobility(ue.ComponentMobility.MOVABLE)
    c.set_light_color(ue.LinearColor(*color)); c.set_intensity(intensity)
    c.set_editor_property('source_width',float(width)); c.set_editor_property('source_height',float(height))
    c.set_attenuation_radius(radius); c.set_cast_shadows(True)
    COUNT['lights']+=1


def candles(x,y,z,light=False):
    for dx,height in [(-22,.8),(0,1.2),(24,.95)]:
        instance('SM_CandleHolder','Bronze',(x+dx,y,z),collision=False)
        instance('SM_Candle','Wax',(x+dx,y,z+38),(1,1,height),collision=False)
        instance('SM_Flame','Flame',(x+dx,y,z+38+25*height),collision=False)
    if light: point(f'Lamp_{x}_{y}',(x,y,z+95),intensity=430,radius=600)


def arch(x,y=0,scale=(1,1,1),yaw=90):
    instance('SM_PointedArch','PaleStone',(x,y,0),scale,(0,yaw,0))


def architecture():
    for index,(name,a,b,w,h,roof) in enumerate(ROOMS):
        # Unbevelled continuous floor slabs meet exactly. Decorative tiles sit on top.
        box('DarkStone',((a+b)/2,0,-30),(b-a,2*w,60))
        for x in range(a+250,b,500):
            length=min(500,b-(x-250))
            for y in range(-w+250,w,500):
                width=min(500,w-(y-250))
                box('PaleStone' if (x//500+y//500)%5 else 'Sandstone',
                    (x-250+length/2,y-250+width/2,1),(length-3,width-3,2),collision=False)
        for side in [-1,1]:
            # The optional alcove is the one intentional break in a side wall.
            spans=[(a,b)]
            if name=='RuinedMemoryChamber' and side==1: spans=[(a,4800),(5700,b)]
            for u,v in spans:
                box('Sandstone',((u+v)/2,side*(w+40),h/2),(v-u,80,h))
            for z in [70,h-90]:
                box('PaleStone',((a+b)/2,side*(w-2),z),(b-a,32,36),collision=False)
            for x in range(a+300,b-100,650):
                box('DarkStone',(x,side*(w-10),420),(360,12,560),collision=False)
                # Framing and vertical carved rhythmic details at the walls.
                for dx in [-190,190]: box('PaleStone',(x+dx,side*(w-26),420),(26,45,600),collision=False)
                instance('SM_EightPointSeal','Bronze',(x,side*(w-35),690),(1.6,1.6,1),(90,0,0),False)
            if w>800:
                for x in range(a+600,b-150,1100):
                    instance('SM_WovenCloth','Burgundy',(x,side*(w-60),750),(2.2,4.3,1),(90,0,0),False)
            if name!='GrandHall':
                for x in range(a+550,b-100,1400):
                    box('DarkWood',(x,side*(w-100),200),(180,100,12),collision=False)
                    candles(x,side*(w-100),210,True)
        # Boundary portal: side masonry plus high lintel, no box over the opening.
        opening=760
        for boundary in [a,b]:
            if boundary==0:
                box('Sandstone',(0,0,h/2),(100,2*w,h)); continue
            if boundary==28400: continue
            for side in [-1,1]:
                width=w-opening/2
                box('Sandstone',(boundary,side*(opening/2+width/2),h/2),(100,width,h))
            if h>800: box('Sandstone',(boundary,0,(800+h)/2),(100,opening,h-800))
        arch(a if a else 1900,scale=(1.15,1.1,1.05))
        if roof:
            # Central open clerestory strip admits actual skylight and moonlight.
            for side in [-1,1]:
                rw=w-160
                box('DarkStone',((a+b)/2,side*(160+rw/2),h+40),(b-a,rw,80))
            for x in range(a+350,b,700):
                box('DarkWood',(x,0,h-20),(50,2*w,80),collision=False)
        if name!='GrandHall':
            rect(f'CoolFill_{name}',((a+b)/2,0,h-80),(-90,0,0),(.38,.52,.78),5000 if w<1000 else 10000,
                 350,600,max(1600,w*2))
        if name in ('EntryPassage','StorySanctum','MemoryVestibule','QuietStudy'):
            instance('SM_WovenCloth','Carpet',((a+b)/2,0,5),((b-a-250)/100,3,1),collision=False)
    # A real side room, not a blocked decorative opening.
    box('DarkStone',(5250,1500,-25),(900,1000,50))
    box('Sandstone',(5250,2000,450),(1000,80,900))
    for x in [4760,5740]: box('Sandstone',(x,1540,450),(80,920,900))
    box('DarkStone',(5250,1510,930),(1000,1000,60))
    arch(5250,1100,scale=(1.1,1,1.1),yaw=0)
    point('AlcoveLamp',(5270,1580,260),intensity=650,radius=700)
    # Courtyard fountain and noble ruins, with broad clear approach down centre.
    for y in [-850,850]:
        instance('SM_CarvedPillar','PaleStone',(1250,y,0),(.8,.8,.85))
        instance('SM_Urn','Ceramic',(1750,y,0),(2,2,2))
    for x in [8800,10100]:
        for y in [-1030,1030]: instance('SM_CarvedPillar','PaleStone',(x,y,0),(.9,.9,1))
    for x in [12700,15300]:
        for y in [-1120,1120]: instance('SM_CarvedPillar','Sandstone',(x,y,0),(1,1,1.18))
    # Grounded shallow ceremonial step outside the route, no mandatory jump puzzle.
    for i in range(3): box('PaleStone',(7300,-710+i*35,10+i*10),(900,200-i*40,20+i*20))


def grand_hall():
    for y in [-1770,1770]:
        for x in [18100,19300,20500,21700,22900]:
            instance('SM_CarvedPillar','PaleStone',(x,y,0),(1.12,1.12,1.55))
        for x in [18700,19900,21100,22300]:
            arch(x,y,(1.78,1.25,1.85),0)
        for x in [18300,20100,21900]:
            box('DarkWood',(x,y/1770*2330,115),(430,160,22))
            for dx in [-160,160]: box('DarkWood',(x+dx,y/1770*2330,55),(20,100,110))
            candles(x,y/1770*2300,130,True)
            instance('SM_Urn','Ceramic',(x+150,y/1770*2300,130),(1,1,1),collision=False)
    for x in [17800,23200]: arch(x,0,(5.2,1.2,2),90)
    # Two longitudinal carpets flank the long table; unobstructed combat lanes.
    for y in [-850,850]: instance('SM_WovenCloth','Carpet',(20500,y,5),(51,5.2,1),collision=False)
    # Central table 22m x 4m. Supports are separate; central collision is intentional.
    box('DarkWood',(20400,0,135),(2200,400,30),bevel=True)
    for x in [19450,20050,20750,21350]:
        for y in [-135,135]: box('DarkWood',(x,y,65),(38,38,130),bevel=True)
    instance('SM_WovenCloth','Burgundy',(20400,0,153),(22,2,1),collision=False)
    for x in range(19400,21500,300):
        for y in [-280,280]:
            instance('SM_Chair','DarkWood',(x,y,0),(1.3,1.3,1.5),(0,-90 if y<0 else 90,0))
        candles(x,0,157,x in [19700,20900])
        for side in [-1,1]:
            static('SM_Plate','Ceramic',f'Plate_{x}_{side}',(x,side*150,157),(1.25,1.25,1.25),physics=True)
            static('SM_Goblet','Bronze',f'Goblet_{x}_{side}',(x+55,side*140,157),physics=True)
    for x in [19900,20500,21100]:
        static('SM_Bowl','Ceramic',f'ServingBowl_{x}',(x,75,157),(1.6,1.6,1.6),physics=True)
    for side in [-1,1]:
        for x in [18900,20900,22600]:
            # Picture plane lies on wall, framed separately. No text-sheet geometry.
            box('Bronze',(x,side*2450,620),(360,35,460),collision=False)
            instance('SM_WovenCloth','Painting',(x,side*2426,620),(3.2,4.2,1),(90,0,0),False)
    for x in [18400,20400,22400]:
        rect(f'Moonshaft_{x}',(x,0,1530),(-90,0,0),(.36,.54,.91),21000,600,500,3100)
    for x in [18700,20700,22600]:
        # Suspended bronze fixtures, emissive candles instead of dozens of shadow lights.
        instance('SM_CandleHolder','Bronze',(x,0,1120),(9,9,2),collision=False)
        for y in [-95,95]: candles(x,y,1195)
        point(f'Chandelier_{x}',(x,0,1120),intensity=1800,radius=2100)
    rect('HallEndFocal',(23200,0,900),(0,180,0),(1,.60,.29),16000,900,750,2400)


def dressing():
    # Manuscript dais and an empty place setting suggest a household interrupted.
    instance('SM_Chair','DarkWood',(24780,370,0),(1.6,1.6,1.6),(0,90,0))
    instance('SM_Storybook','Parchment',(24800,330,83),(1.5,1.5,1),collision=False)
    for x in [24000,25300]:
        box('DarkWood',(x,-900,240),(600,180,480))
        for z in [120,240,360]:
            box('Bronze',(x,-790,z),(580,18,10),collision=False)
            for dx in [-220,-100,50,200]: instance('SM_Storybook','Parchment',(x+dx,-775,z+12),(1,1,1),(0,dx%35,0),False)
    instance('SM_WoodenHorse','DarkWood',(5270,1580,107),(2,2,2),collision=False)
    # Gate opens visually into a composed, inaccessible next-world silhouette.
    arch(28000,0,(3.1,1.8,2.2),90)
    box('DarkStone',(28400,0,250),(80,3200,500))
    for x,y,h in [(31000,-2600,1800),(32900,1000,2500),(34500,-900,2900),(36500,2500,2200)]:
        box('DarkStone',(x,y,h/2-300),(1200,900,h),collision=False,bevel=True)
        arch(x,y,(2,2,1.8),90)
    # No invisible blocking plane at the end: the far court has a solid parapet.
    sphere=ue.load_asset('/Engine/BasicShapes/Sphere')
    moon=spawn(ue.StaticMeshActor,'MoonOverUnwrittenCity',(36000,1500,5500),folder='Vista')
    moon.static_mesh_component.set_static_mesh(sphere);moon.static_mesh_component.set_material(0,MATS['Moon'])
    moon.static_mesh_component.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
    moon.set_actor_scale3d(vec((14,14,14)))


def gameplay():
    def bp(name,folder,parent,defaults):
        path=f'{BASE}/Blueprints/{folder}/{name}'
        asset=ue.load_asset(path)
        if not asset:
            factory=ue.BlueprintFactory();factory.set_editor_property('parent_class',parent)
            asset=ASSETS.create_asset(name,f'{BASE}/Blueprints/{folder}',ue.Blueprint,factory)
            ue.BlueprintEditorLibrary.compile_blueprint(asset)
            obj=ue.get_default_object(asset.generated_class())
            for k,v in defaults.items(): obj.set_editor_property(k,v)
            ue.BlueprintEditorLibrary.compile_blueprint(asset);save(asset)
        return asset.generated_class()
    fighter=ue.load_class(None,'/Script/ALMNSY_Level01.ALMNSYFighter')
    gm=ue.load_class(None,'/Script/ALMNSY_Level01.ALMNSYChapterGameMode')
    require(fighter and gm,'Compile ALMNSY_Level01Editor before running this script.')
    hero=bp('BP_ChapterPlayer','Player',fighter,{})
    guard=bp('BP_ForgottenGuard','Enemies',fighter,{'enemy':True})
    heavy=bp('BP_ForgottenHeavyGuard','Enemies',fighter,{'enemy':True,'heavy':True})
    story=bp('BP_StoryFigure','Interactions',fighter,{'story_character':True})
    game_mode=bp('BP_ChapterGameMode','Gameplay',gm,{'default_pawn_class':hero})
    world=ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',game_mode)
    world.get_world_settings().set_editor_property('kill_z',-1200.)
    spawn(ue.PlayerStart,'PlayerStart_Arrival',PLAYER_START)
    spawn(ue.load_class(None,'/Script/ALMNSY_Level01.ALMNSYChapterDirector'),'ChapterDirector')
    spawn(story,'TheFigureWhoRemembers',(7610,460,100),(0,215,0))
    for label,group,tough,position in ENEMIES:
        e=spawn(heavy if tough else guard,label,position,(0,180,0),'Encounters')
        e.set_editor_property('guard_id',label); e.set_editor_property('encounter',group)
    for label,kind,p,checkpoint,group,prompt in INTERACTIONS:
        a=spawn(ue.load_class(None,'/Script/ALMNSY_Level01.ALMNSYInteraction'),label,p)
        for k,v in dict(kind=kind,prompt=ue.Text(prompt),required_encounter=group,respawn_location=vec(checkpoint)).items(): a.set_editor_property(k,v)
        c=a.get_editor_property('pedestal')
        if kind not in ('Memory',):
            c.set_static_mesh(MESHS['SM_MemoryPedestal']);c.set_material(0,MATS['PaleStone'])
        if kind=='Shrine':
            instance('SM_Storybook','Parchment',(p[0],p[1],109),collision=False)
            instance('SM_EightPointSeal','Memory',(p[0],p[1],180),(1,1,1),(0,0,0),False)
        COUNT['interactions']+=1
    for x,group,sword,memory in SEALS:
        a=spawn(ue.load_class(None,'/Script/ALMNSY_Level01.ALMNSYSeal'),f'MemorySeal_{x}',(x,0,350))
        for k,v in dict(required_encounter=group,requires_sword=sword,requires_memory=memory).items(): a.set_editor_property(k,v)
        c=a.get_editor_property('door');c.set_static_mesh(MESHS['SM_ConstructionBlock']);c.set_material(0,MATS['DarkWood'])
        a.set_actor_scale3d(vec((.4,7.5,7)))
    require(ue.ALMNSYEditorLibrary.add_navigation_bounds(vec((14200,0,400)),vec((14300,2650,600))), 'Navigation volume could not be created')


def atmosphere():
    sun=spawn(ue.DirectionalLight,'CoolMoonlight',(0,0,1800),(-48,-32,0),'Lighting')
    c=sun.get_component_by_class(ue.DirectionalLightComponent)
    c.set_mobility(ue.ComponentMobility.MOVABLE);c.set_intensity(.8);c.set_light_color(ue.LinearColor(.40,.56,.88))
    sky=spawn(ue.SkyLight,'NightSkyFill',(0,0,0),folder='Lighting')
    sc=sky.get_component_by_class(ue.SkyLightComponent);sc.set_mobility(ue.ComponentMobility.MOVABLE)
    sc.set_intensity(.7);sc.set_editor_property('real_time_capture',True)
    spawn(ue.SkyAtmosphere,'NightAtmosphere',folder='Lighting')
    fog=spawn(ue.ExponentialHeightFog,'HouseDustAndMoonHaze',(0,0,-50),folder='Lighting')
    f=fog.get_component_by_class(ue.ExponentialHeightFogComponent)
    f.set_editor_property('fog_density',.014);f.set_editor_property('fog_height_falloff',.22)
    f.set_volumetric_fog(True)
    f.set_editor_property('fog_inscattering_luminance',ue.LinearColor(.018,.027,.045))
    post=spawn(ue.PostProcessVolume,'ChapterExposure',folder='Lighting')
    post.set_editor_property('unbound',True)
    settings=post.get_editor_property('settings')
    for key,value in {'auto_exposure_min_brightness':-1.,'auto_exposure_max_brightness':2.,
        'auto_exposure_bias':.6,'bloom_intensity':.25,'vignette_intensity':.28}.items():
        settings.set_editor_property('override_'+key,True);settings.set_editor_property(key,value)
    post.set_editor_property('settings',settings)


def flush():
    for (mesh,mat,collision),transforms in BATCHES.items():
        require(ue.ALMNSYEditorLibrary.create_instances(MESHS[mesh],MATS[mat],transforms,collision,
            f'{mesh}_{mat}_{"Solid" if collision else "Detail"}'),'Instancing failed')
    BATCHES.clear()


def build():
    require(hasattr(ue,'ALMNSYEditorLibrary'),'Editor tools module is not loaded. Build ALMNSY_Level01Editor first.')
    require(not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() and
            not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
            'Save your current work before opening or generating the map; the builder will not save unrelated dirty packages.')
    if EAL.does_asset_exist(MAP):
        require(LEVEL.load_level(MAP),'Could not open the existing chapter map')
        ue.log_warning(f'{MAP} already exists: opened without modifying it. Use ALMNSY_BUILD_VERSION=v02 for a fresh map.')
        return
    import_sources();materials()
    require(LEVEL.new_level(MAP),'Could not create the chapter map')
    architecture();grand_hall();dressing();gameplay();atmosphere();flush()
    ue.ALMNSYEditorLibrary.build_navigation()
    require(LEVEL.save_current_level(),'Failed to save chapter map')
    require(EAL.save_directory(BASE,only_if_is_dirty=True,recursive=True),'Failed to save generated chapter assets')
    # Change startup defaults only after successful generation. Preserve all other settings.
    config=ROOT/'Config'/'DefaultEngine.ini'
    text=config.read_text(encoding='utf-8-sig')
    lines=[]
    for line in text.splitlines():
        if line.startswith(('GameDefaultMap=','EditorStartupMap=')):
            line=line.split('=')[0]+'='+MAP+'.'+MAP.rsplit('/',1)[1]
        lines.append(line)
    config.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(dict(map=MAP,status='generated_not_playtested',counts=dict(COUNT),
        enemies=len(ENEMIES),rooms=len(ROOMS),required_local_checks=['PIE full route','death and restart','nav paths','lighting','packaged build']),indent=2))
    ue.get_editor_subsystem(ue.UnrealEditorSubsystem).set_level_viewport_camera_info(vec((17700,-350,260)),rot((-3,4,0)))
    ue.log(f'ALMNSY generated: {MAP}. Press Play. Report: {REPORT}')


try:
    build()
except Exception:
    ue.log_error('ALMNSY generation did not finish. See traceback below; no playtest success is claimed.\n'+traceback.format_exc())
    raise
