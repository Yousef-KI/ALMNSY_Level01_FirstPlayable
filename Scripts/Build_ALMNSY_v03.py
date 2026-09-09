"""Refine the exact working v02 route into a separate v03 map and asset namespace.
Never writes a v02 package, old material, old Blueprint or startup-map setting.
"""
from pathlib import Path
import importlib.util
import json
import math
import sys
import traceback
import unreal as ue

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts/Level01'))
from refinement_layout import chair_yaw,hall_details,route_details,vista
spec=importlib.util.spec_from_file_location('almnsy_working_baseline',ROOT/'Scripts/Build_ALMNSY_Level01.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
b.BASE='/Game/ALMNSY/Versions/v03'
b.ART=ROOT/'SourceArt/Level01_v03'
b.MAP='/Game/ALMNSY/Levels/Level01/ALMNSY_Level01_FirstPlayable_v03'
b.REPORT=ROOT/'Saved/ALMNSY/Build_v03.json'
OLD_INSTANCE=b.instance
OLD_POINT=b.point
OLD_RECT=b.rect
OLD_GAMEPLAY=b.gameplay


def instance(mesh,mat,p,scale=(1,1,1),rotation=(0,0,0),collision=True):
    if mesh=='SM_Chair' and 19300<=p[0]<=21500 and abs(p[1])==280:
        # Mesh backrest is -X. Each row's +X must point toward the table.
        rotation=(0,90 if p[1]<0 else -90,0)
    if mesh in ('SM_WovenCloth','SM_EightPointSeal') and p[2]>300 and abs(p[1])>300:
        # XY-plane details need roll about X to face +/-Y walls. Pitch had
        # presented their edges to the room in the baseline.
        rotation=(0,0,90 if p[1]>0 else -90)
    if mesh=='SM_WovenCloth' and mat=='Carpet' and p[0]==20500 and abs(p[1])==850:
        for x in [18900,20500,22100]:OLD_INSTANCE(mesh,mat,(x,p[1],p[2]),(15,5.2,1),rotation,False)
        return
    OLD_INSTANCE(mesh,mat,p,scale,rotation,collision)


def point(name,p,color=(1,.53,.23),intensity=700,radius=700,shadows=False):
    # More local pools of light. Only selected hero lamps cast dynamic shadows.
    selected=name.startswith('Chandelier') or name=='AlcoveLamp'
    return OLD_POINT(name,p,color,intensity*.70,radius*.85,selected)


def rect(name,p,rotation,color,intensity,width=500,height=400,radius=2200):
    # Avoid bright broad fill flattening stone relief.
    ratio=.19 if name.startswith('CoolFill') else .40
    result=OLD_RECT(name,p,rotation,color,intensity*ratio,width*.7,height*.65,radius*.85)
    return result


def material(name,tex=None,color=(1,1,1),rough=.8,metal=0,world=False,emission=0,cloth=False,dissolve=False):
    path=f'{b.BASE}/Materials/MI_{name}'
    if b.EAL.does_asset_exist(path):b.MATS[name]=ue.load_asset(path);return
    master=f'{b.BASE}/Materials/M_{name}'
    mat=ue.load_asset(master)
    if mat:
        raise RuntimeError(f'Partial material exists without its instance: {master}. Preserve it and inspect before retrying.')
    mat=b.ASSETS.create_asset('M_'+name,f'{b.BASE}/Materials',ue.Material,ue.MaterialFactoryNew())
    b.require(mat,f'Cannot create {master}');mat.set_editor_property('two_sided',cloth)
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    if dissolve:mat.set_editor_property('used_with_skeletal_mesh',True)
    mel=b.MEL
    def expr(cls,**props):
        e=mel.create_material_expression(mat,cls)
        for k,v in props.items():e.set_editor_property(k,v)
        return e
    def link(a,d,pin,output=''):
        ok=mel.connect_material_expressions(a,output,d,pin)
        # Retain the proven 5.8 unnamed-unary-input fallback. Never redirect B to A.
        if not ok and pin in ('Input','Coordinates'):ok=mel.connect_material_expressions(a,output,d,'')
        b.require(ok,f'v03 material link failed {name}/{pin}')
    def binary(cls,a,c):
        e=expr(cls);link(a,e,'A');link(c,e,'B');return e
    def mask(a,channels):
        e=expr(ue.MaterialExpressionComponentMask,r='r' in channels,g='g' in channels,b='b' in channels,a=False)
        link(a,e,'Input');return e
    def scalar(v):return expr(ue.MaterialExpressionConstant,r=v)
    def output(a,property):b.require(mel.connect_material_property(a,'',property),f'{name}: output failed')
    tint=expr(ue.MaterialExpressionConstant3Vector,constant=ue.LinearColor(*color))
    result=tint;rr=scalar(rough)
    if tex:
        def sample(suffix,uv=None):
            t=b.texture(f'T_{tex}_{suffix}')
            props={'texture':t}
            if suffix in ('ORM','Height'):props['sampler_type']=ue.MaterialSamplerType.SAMPLERTYPE_MASKS
            if suffix=='Normal':props['sampler_type']=ue.MaterialSamplerType.SAMPLERTYPE_NORMAL
            e=expr(ue.MaterialExpressionTextureSample,**props)
            if uv:link(uv,e,'Coordinates')
            return e
        if world:
            pos=expr(ue.MaterialExpressionWorldPosition)
            normal=expr(ue.MaterialExpressionVertexNormalWS)
            absolute=expr(ue.MaterialExpressionAbs);link(normal,absolute,'Input')
            weights=[mask(absolute,c) for c in ('r','g','b')]
            weight_sum=binary(ue.MaterialExpressionAdd,binary(ue.MaterialExpressionAdd,weights[0],weights[1]),weights[2])
            uv3=binary(ue.MaterialExpressionDivide,pos,scalar(220 if tex=='Wood' else 310))
            def weighted(suffix,channel=None):
                parts=[]
                for projection,w in zip(('gb','rb','rg'),weights):
                    s=sample(suffix,mask(uv3,projection))
                    if channel:s=mask(s,channel)
                    parts.append(binary(ue.MaterialExpressionMultiply,s,binary(ue.MaterialExpressionDivide,w,weight_sum)))
                return binary(ue.MaterialExpressionAdd,binary(ue.MaterialExpressionAdd,parts[0],parts[1]),parts[2])
            result=weighted('BaseColor');rr=weighted('ORM','g')
            height=weighted('Height','r')
            # Derivative surface-gradient bump: consistent across triplanar seams.
            # VertexNormalWS avoids a PixelNormalWS -> Normal feedback cycle.
            inputs=[]
            for key in ['P','N','H']:
                item=ue.CustomInput();item.set_editor_property('input_name',key);inputs.append(item)
            bump=expr(ue.MaterialExpressionCustom,inputs=inputs,output_type=ue.CustomMaterialOutputType.CMOT_FLOAT3,
                code='float3 a=ddx(P), b=ddy(P); float3 r1=cross(b,N), r2=cross(N,a); float d=dot(a,r1); return normalize(abs(d)*N-sign(d)*(ddx(H)*r1+ddy(H)*r2));')
            link(pos,bump,'P');link(normal,bump,'N');link(binary(ue.MaterialExpressionMultiply,height,scalar(1.8)),bump,'H')
            mat.set_editor_property('tangent_space_normal',False);output(bump,ue.MaterialProperty.MP_NORMAL)
            random=expr(ue.MaterialExpressionPerInstanceRandom)
            variation=binary(ue.MaterialExpressionAdd,scalar(.88),binary(ue.MaterialExpressionMultiply,random,scalar(.22)))
            result=binary(ue.MaterialExpressionMultiply,result,variation)
        else:
            result=sample('BaseColor')
            if tex!='ForgottenHouse':
                rr=mask(sample('ORM'),'g');output(sample('Normal'),ue.MaterialProperty.MP_NORMAL)
        result=binary(ue.MaterialExpressionMultiply,result,tint)
    output(result,ue.MaterialProperty.MP_BASE_COLOR);output(rr,ue.MaterialProperty.MP_ROUGHNESS)
    output(scalar(metal),ue.MaterialProperty.MP_METALLIC)
    if emission:output(binary(ue.MaterialExpressionMultiply,tint,scalar(emission)),ue.MaterialProperty.MP_EMISSIVE_COLOR)
    if dissolve:
        mat.set_editor_property('blend_mode',ue.BlendMode.BLEND_MASKED)
        fade=expr(ue.MaterialExpressionScalarParameter,parameter_name='MemoryFade',default_value=0.)
        # Spatial erosion is stable in world space; bodies stay still during fade.
        pos=expr(ue.MaterialExpressionWorldPosition)
        noise=expr(ue.MaterialExpressionNoise,scale=.08,levels=2,quality=1)
        link(pos,noise,'Position')
        positive_noise=binary(ue.MaterialExpressionAdd,binary(ue.MaterialExpressionMultiply,noise,scalar(.5)),scalar(.58))
        threshold=binary(ue.MaterialExpressionSubtract,positive_noise,fade)
        output(threshold,ue.MaterialProperty.MP_OPACITY_MASK)
        mat.set_editor_property('opacity_mask_clip_value',.01)
    mel.recompile_material(mat);b.save(mat)
    mi=b.ASSETS.create_asset('MI_'+name,f'{b.BASE}/Materials',ue.MaterialInstanceConstant,ue.MaterialInstanceConstantFactoryNew())
    b.require(mi,f'Cannot create {path}');mel.set_material_instance_parent(mi,mat);b.save(mi);b.MATS[name]=mi


def materials():
    for n,t,c in [('Sandstone','Stone',(1,1,1)),('PaleStone','Limestone',(1,1,1)),
        ('DarkStone','Stone',(.38,.40,.43)),('DarkWood','Wood',(1,1,1))]:material(n,t,color=c,world=True)
    material('Bronze','Bronze',metal=.82,world=True)
    material('Burgundy','Cloth',cloth=True);material('Carpet','Carpet',cloth=True)
    material('Ceramic','Ceramic');material('Parchment','Parchment');material('Painting','ForgottenHouse')
    material('Wax','Wax');material('AgedMetal',color=(.24,.27,.30),rough=.34,metal=.86)
    material('Guard_Charcoal',color=(.075,.045,.032),rough=.65,metal=.25,dissolve=True)
    material('Guard_Bronze',color=(.17,.084,.031),rough=.55,metal=.62,dissolve=True)
    material('Flame',color=(1,.29,.055),emission=5)
    material('Memory',color=(.20,.45,.68),emission=2)
    material('Moon',color=(.28,.36,.50),emission=1)
    for n,c in [('VistaNear',(.035,.029,.025)),('VistaMid',(.061,.071,.086)),('VistaFar',(.085,.11,.15))]:material(n,color=c,rough=1)
    material('DistantLamp',color=(.50,.20,.05),emission=1.8)


def gameplay():
    # Reuse exact actor IDs, encounters, checkpoints, seals and objective logic.
    refined=ue.load_class(None,'/Script/ALMNSY_Level01.ALMNSYFighterV03')
    b.require(refined,'Build the v03 Editor target first')
    OLD_GAMEPLAY(refined)
    for a in b.ACTORS.get_all_level_actors():
        if a.get_class().get_name()=='ALMNSYChapterDirector':a.set_editor_property('save_namespace','v03')
    # Finish the warm/cold contrast at shrine and gate using small native effects.
    effect=ue.load_class(None,'/Script/ALMNSY_Level01.ALMNSYMemoryEffect')
    b.require(effect,'Memory effect class missing')
    for name,kind,p,_,_,_ in b.INTERACTIONS:
        if kind in ('Shrine','Memory','End'):
            fx=b.spawn(effect,'MemoryMotes_'+name,(p[0],p[1],130),folder='Atmosphere')
            fx.set_editor_property('ambient',True)


def atmosphere():
    b.atmosphere()
    for actor in b.ACTORS.get_all_level_actors():
        if isinstance(actor,ue.DirectionalLight):
            c=actor.get_component_by_class(ue.DirectionalLightComponent);c.set_intensity(.16)
        elif isinstance(actor,ue.SkyLight):actor.get_component_by_class(ue.SkyLightComponent).set_intensity(.22)
        elif isinstance(actor,ue.PostProcessVolume):
            settings=actor.get_editor_property('settings')
            # Fixed exposure stops auto exposure brightening every dark corner.
            for k,v in {'auto_exposure_min_brightness':2.0,'auto_exposure_max_brightness':2.0,
                'auto_exposure_bias':0.,'bloom_intensity':.18,'vignette_intensity':.22}.items():
                settings.set_editor_property('override_'+k,True);settings.set_editor_property(k,v)
            actor.set_editor_property('settings',settings)
        elif isinstance(actor,ue.ExponentialHeightFog):
            c=actor.get_component_by_class(ue.ExponentialHeightFogComponent)
            c.set_editor_property('fog_density',.018);c.set_editor_property('fog_height_falloff',.14)
    wind=b.spawn(ue.AmbientSound,'WindAtStoryGate',(28100,0,500),folder='Audio')
    c=wind.get_component_by_class(ue.AudioComponent)
    c.set_sound(ue.load_asset(f'{b.BASE}/Audio/S_Wind'));c.set_volume_multiplier(.16)
    settings=ue.SoundAttenuationSettings();settings.set_editor_property('attenuation_shape_extents',b.vec((900,0,0)))
    settings.set_editor_property('falloff_distance',3500.)
    c.adjust_attenuation(settings)


def build():
    b.require(hasattr(ue,'ALMNSYEditorLibrary'),'Compile the project before running v03')
    b.require(not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
        'Save or discard current editor changes before opening v03')
    if b.EAL.does_asset_exist(b.MAP):
        b.require(b.LEVEL.load_level(b.MAP),'Could not open existing v03')
        ue.log_warning('v03 exists: opened without regeneration. Inspect Saved/ALMNSY/Build_v03.json for completion status.');return
    b.require((b.ART/'Textures/T_Stone_Height.png').is_file(),'Missing committed v03 sources. Apply the complete patch.')
    b.instance=instance;b.point=point;b.rect=rect
    b.import_sources()
    # Import settings are changed ONLY for assets in the new namespace.
    for p in (b.ART/'Textures').glob('*.png'):
        asset=ue.load_asset(f'{b.BASE}/Textures/{p.stem}')
        if p.stem.endswith(('_Height','_Normal')):
            asset.set_editor_property('srgb',False)
            asset.set_editor_property('compression_settings',ue.TextureCompressionSettings.TC_NORMALMAP if p.stem.endswith('_Normal') else ue.TextureCompressionSettings.TC_MASKS)
            b.save(asset)
    wind=ue.load_asset(f'{b.BASE}/Audio/S_Wind');wind.set_editor_property('looping',True);b.save(wind)
    materials()
    b.require(b.LEVEL.new_level(b.MAP),'Cannot create v03')
    b.architecture();b.grand_hall();b.dressing()
    hall_details(b);route_details(b);vista(b);gameplay();atmosphere();b.flush()
    ue.ALMNSYEditorLibrary.build_navigation()
    b.require(b.LEVEL.save_current_level(),'Could not save v03')
    b.require(b.EAL.save_directory(b.BASE,only_if_is_dirty=True,recursive=True),'Could not save v03 assets')
    b.REPORT.parent.mkdir(parents=True,exist_ok=True)
    b.REPORT.write_text(json.dumps({'status':'generated_requires_playtest','map':b.MAP,'base_commit':'639c17d1811b0ea7a869c906fa05bfeeb4901b00',
        'counts':dict(b.COUNT),'v02_modified':False,'save_slot':'ALMNSY_Level01_v03_Checkpoint'},indent=2))
    ue.get_editor_subsystem(ue.UnrealEditorSubsystem).set_level_viewport_camera_info(b.vec((17800,-1000,230)),b.rot((-2,12,0)))
    ue.log('v03 complete. Press Play with Default Player Start. Startup remains v02 for recovery.')


if __name__=='__main__':
    try:build()
    except Exception:
        ue.log_error('v03 did not finish. Preserve partial assets for inspection.\n'+traceback.format_exc());raise
