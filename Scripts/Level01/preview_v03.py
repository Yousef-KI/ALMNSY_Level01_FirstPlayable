"""Optional source inspection figures, NOT Unreal renders (Pillow/matplotlib/numpy)."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Documentation/Level01/v03';OUT.mkdir(parents=True,exist_ok=True)
ART=ROOT/'SourceArt/Level01_v03'


def figures():
    palette=Image.new('RGB',(1200,680),(24,27,30));d=ImageDraw.Draw(palette)
    d.text((20,16),'v03 SOURCE SURFACES — base color only; not an Unreal screenshot',fill=(228,214,185))
    for i,kind in enumerate(['Stone','Limestone','Wood','Carpet','Cloth','Bronze','Ceramic','Parchment']):
        im=Image.open(ART/f'Textures/T_{kind}_BaseColor.png').convert('RGB');im.thumbnail((275,275))
        x=20+(i%4)*298;y=50+(i//4)*305;palette.paste(im,(x,y));d.text((x,y+280),kind,fill=(228,214,185))
    palette.save(OUT/'SourceSurfaces.png')
    fig=plt.figure(figsize=(14,6),facecolor='#181b1e')
    for i,(name,title) in enumerate([('SM_PointedArch','Continuous 180cm arch depth'),('SM_CarvedPillar','Solid stepped column capital'),('SM_Chair','Beveled chair; front is +X')]):
        m=json.loads((ART/f'Meshes/{name}.json').read_text());v=np.array(m['vertices']);t=np.array(m['triangles']).reshape(-1,3);tri=v[t]
        normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normals/=np.maximum(1e-9,np.linalg.norm(normals,axis=1))[:,None]
        light=np.array([.4,-.7,1]);light/=np.linalg.norm(light);intensity=.3+.7*np.maximum(0,normals@light)
        colors=np.array([.65,.53,.37])[None,:]*intensity[:,None]
        ax=fig.add_subplot(1,3,i+1,projection='3d',facecolor='#181b1e')
        ax.add_collection3d(Poly3DCollection(tri,facecolors=colors,edgecolors='none'))
        mn=v.min(0);mx=v.max(0);ax.set_xlim(mn[0],mx[0]);ax.set_ylim(mn[1],mx[1]);ax.set_zlim(mn[2],mx[2]);ax.set_box_aspect(mx-mn)
        ax.view_init(elev=15,azim=-62);ax.set_axis_off();ax.set_title(title,color='#e4d6b9',fontsize=11)
    fig.suptitle('SOURCE MESH INSPECTION • no engine materials or lighting',color='#e4d6b9',fontsize=15)
    fig.savefig(OUT/'SourceMeshKit.png',dpi=130,facecolor=fig.get_facecolor(),bbox_inches='tight');plt.close(fig)
    data=np.genfromtxt(OUT/'SwordTrajectories.csv',delimiter=',',skip_header=1)
    fig,axes=plt.subplots(1,3,figsize=(12,4),subplot_kw={'projection':'3d'})
    for combo,ax in enumerate(axes):
        rows=data[data[:,0]==combo];hand=rows[:,2:5];direction=rows[:,5:8];direction/=np.linalg.norm(direction,axis=1)[:,None];tip=hand+direction*90
        ax.plot(*hand.T,color='#b18341',label='hand');ax.plot(*tip.T,color='#33597c',label='blade tip')
        for j in range(28,59,6):ax.plot(*np.stack([hand[j],tip[j]]).T,color='#913c35',alpha=.6)
        ax.set_title(['Forehand cut','Returning cut','Overhead cut'][combo]);ax.set_xlabel('Right');ax.set_ylabel('Forward');ax.set_zlabel('Height');ax.legend(fontsize=7)
    fig.suptitle('Authored targets in centimetres • red = active window • IK/collision need Unreal validation')
    fig.tight_layout();fig.savefig(OUT/'SourceSwordArcs.png',dpi=130);plt.close(fig)


if __name__=='__main__':figures()
