"""Optional source regeneration: numpy + Pillow. Builder imports committed PNG/WAV.
Periodic multi-scale surfaces, height-derived normals and roughness. No baked lighting.
"""
from pathlib import Path
import math
import io
import wave
import numpy as np
from PIL import Image, ImageDraw

OUT=Path(__file__).resolve().parents[2]/'SourceArt/Level01_v03'
N=1024


def save_png(im,path):
    buffer=io.BytesIO();im.save(buffer,format='PNG')
    temporary=path.with_suffix('.png.tmp');temporary.write_bytes(buffer.getvalue());temporary.replace(path)


def noise(cells, seed):
    rng=np.random.default_rng(seed);grid=rng.random((cells,cells)).astype(np.float32)
    u=np.arange(N,dtype=np.float32)*cells/N;i=u.astype(int);f=u-i;f=f*f*(3-2*f)
    a=grid[i[:,None]%cells,i[None,:]%cells]*(1-f[None,:])+grid[i[:,None]%cells,(i[None,:]+1)%cells]*f[None,:]
    b=grid[(i[:,None]+1)%cells,i[None,:]%cells]*(1-f[None,:])+grid[(i[:,None]+1)%cells,(i[None,:]+1)%cells]*f[None,:]
    return a*(1-f[:,None])+b*f[:,None]


def textures():
    out=OUT/'Textures';out.mkdir(parents=True,exist_ok=True)
    yy,xx=np.mgrid[:N,:N].astype(np.float32);u,v=xx/N,yy/N
    broad=noise(4,11);mid=noise(24,7);fine=noise(128,41)
    grain=np.random.default_rng(9).random((N,N)).astype(np.float32)
    palettes={'Stone':(117,103,82),'Limestone':(151,139,115),'Wood':(57,32,19),
        'Cloth':(69,14,23),'Carpet':(73,15,23),'Bronze':(108,72,32),
        'Ceramic':(65,85,79),'Parchment':(170,148,104),'Wax':(174,145,101)}
    for kind,rgb in palettes.items():
        c=np.ones((N,N,3),np.float32)*np.array(rgb)
        h=.5+(.5-broad)*.12+(mid-.5)*.08+(fine-.5)*.04
        variation=.81+.23*broad+.15*mid+.045*(grain-.5)
        rough=np.full((N,N),.78,np.float32)+.16*(mid-.5)+.07*(grain-.5)
        if kind in ('Stone','Limestone'):
            pores=np.maximum(0,(.08-grain)*8)*(fine<.52)
            veins=np.exp(-np.square((np.sin(u*math.tau*3+mid*3+v*math.tau*2))/.055))
            variation*=1-pores*.28-veins*.07
            h-=pores*.08+veins*.02
        elif kind=='Wood':
            fibers=np.sin(u*math.tau*48+np.sin(v*math.tau*2)*2+mid*3)
            growth=np.sin(u*math.tau*7+np.sin(v*math.tau)*.5)
            variation*=.86+.13*fibers+.11*growth
            h+=fibers*.018+growth*.025;rough-=.12
        elif kind in ('Cloth','Carpet'):
            weave=(np.sin(xx*math.pi/2)*np.sin(yy*math.pi/2))
            h+=weave*.018;rough+=.1
            variation*=.92+.06*weave
            if kind=='Carpet':
                # Nested borders and small repeating floral/geometric knot motifs.
                edge=np.minimum.reduce([u,v,1-u,1-v])
                border=(np.abs(edge-.027)<.003)|(np.abs(edge-.10)<.004)|(np.abs(edge-.135)<.002)
                knot=np.abs(np.sin(u*math.tau*18)*np.sin(v*math.tau*18))>.84
                knot&=((edge>.035)&(edge<.092))
                dx,dy=u-.5,v-.5;radius=np.hypot(dx,dy);theta=np.arctan2(dy,dx)
                medallion=np.abs(radius-(.24+.043*np.cos(theta*8)))<.003
                inner=np.abs(np.sin(u*math.tau*7)+np.cos(v*math.tau*9))<.025
                ornament=border|knot|medallion|(inner&(edge>.15))
                c[ornament]=(134,99,53);h+=ornament*.008
                variation*=.78+.22*np.minimum(1,edge*14)
        elif kind=='Bronze':
            patina=np.clip((mid-.57)*6,0,.75)
            c=c*(1-patina[:,:,None])+np.array((39,63,49))*patina[:,:,None]
            rough=.30+.37*patina+.13*fine
        elif kind=='Ceramic':rough=.24+.15*mid;h*=.1
        elif kind=='Parchment':
            edge=np.minimum.reduce([u,v,1-u,1-v]);variation*=np.minimum(1,.57+edge*4)
            ink=(np.mod(yy,63)<2)&(u>.12)&(u<.86)&(mid>.25)
            c[ink]*=.39;h*=.35
        elif kind=='Wax':rough=.48+.12*mid;h*=.25
        c=np.clip(c*variation[:,:,None],0,255).astype(np.uint8)
        dx=(np.roll(h,-1,axis=1)-np.roll(h,1,axis=1))*4
        dy=(np.roll(h,-1,axis=0)-np.roll(h,1,axis=0))*4
        normal=np.dstack([-dx,dy,np.ones_like(h)]);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
        ao=np.clip(.85+.15*fine,0,1);metal=np.full_like(h,.86 if kind=='Bronze' else 0)
        save_png(Image.fromarray(c),out/f'T_{kind}_BaseColor.png')
        save_png(Image.fromarray(np.uint8(np.clip(np.dstack([ao,rough,metal]),0,1)*255)),out/f'T_{kind}_ORM.png')
        save_png(Image.fromarray(np.uint8((normal*.5+.5)*255)),out/f'T_{kind}_Normal.png')
        save_png(Image.fromarray(np.uint8(np.clip(h,0,1)*255)),out/f'T_{kind}_Height.png')
    painting=Image.new('RGB',(N,N),(28,34,41));d=ImageDraw.Draw(painting)
    d.ellipse((620,100,805,285),fill=(147,130,93))
    rng=np.random.default_rng(22)
    for layer in range(3):
        col=[(65,69,67),(68,57,42),(31,29,25)][layer]
        for x in range(-60,N,85):
            z=int(rng.integers(430+layer*100,680+layer*90));w=int(rng.integers(55,110))
            d.rectangle((x,z,x+w,N),fill=col)
            d.ellipse((x,z-w//2,x+w,z+w//2),fill=col)
            if layer==2:
                d.rectangle((x+20,z+40,x+30,z+65),fill=(147,105,57))
    c=np.asarray(painting).astype(np.float32)*(.82+.18*broad[:,:,None])
    save_png(Image.fromarray(np.uint8(c)),out/'T_ForgottenHouse_BaseColor.png')


def audio():
    out=OUT/'Audio';out.mkdir(parents=True,exist_ok=True);rate=22050
    for name,duration in [('Swing',.45),('Impact',.32),('Block',.48),('Parry',.8),('Memory',1.7),('Death',1.2),('Wind',12)]:
        t=np.arange(int(rate*duration))/rate;noise=np.random.default_rng(8).uniform(-1,1,len(t))
        if name=='Swing':s=noise*.15*np.sin(np.pi*t/duration)**2*(.6+.4*np.sin(t*900))
        elif name in ('Block','Parry'):
            s=sum(np.sin(2*np.pi*f*t)*a for f,a in [(784,.15),(1319,.075),(2173,.04)])*np.exp(-t*(7 if name=='Parry' else 14))+noise*.04*np.exp(-t*45)
        elif name=='Impact':s=(noise*.20+np.sin(2*np.pi*173*t)*.24)*np.exp(-t*21)
        elif name=='Memory':s=(np.sin(t*2*np.pi*392)*.08+np.sin(t*2*np.pi*587)*.04)*np.sin(np.pi*t/duration)**2
        elif name=='Death':s=noise*.07*np.exp(-t*3)+np.sin(2*np.pi*(100*t-24*t*t))*.08*np.exp(-t*5)
        else:
            s=np.convolve(noise,np.ones(160)/160,mode='same')*.6*np.minimum(1,np.minimum(t,duration-t))
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(np.int16(np.clip(s,-1,1)*32767).tobytes())
        temporary=out/f'S_{name}.wav.tmp';temporary.write_bytes(buffer.getvalue());temporary.replace(out/f'S_{name}.wav')


if __name__=='__main__':textures();audio()
