"""Art-only additions on the unchanged v02 route. All transforms are centimetres.
This module also runs with a recording backend in static spatial validation.
"""
import math


def chair_yaw(position, target=(20400,0,0)):
    return math.degrees(math.atan2(target[1]-position[1],target[0]-position[0]))


def hall_details(b):
    # Shadowed perimeter galleries sit above combat height, not in the lanes.
    for side in [-1,1]:
        y=side*2335
        for z,width,height in [(180,190,22),(790,240,40),(1070,270,45),(1540,290,55)]:
            b.box('PaleStone',(20500,y,z),(5850,width,height),bevel=True)
        for x in [18100,19300,20500,21700,22900]:
            b.box('DarkStone',(x,side*2440,980),(740,60,1330),bevel=True)
            for dx in [-380,380]:b.box('PaleStone',(x+dx,side*2350,950),(45,160,1200),bevel=True)
            b.instance('SM_PointedArch','PaleStone',(x,side*2320,970),(.86,.65,.72),(0,0,0),False)
            b.instance('SM_Lattice','Bronze',(x,side*2350,1330),(4.5,1,4.5),collision=False)
            b.instance('SM_EightPointSeal','Bronze',(x,side*2285,740),(1.3,1.3,1),(90,0,0),False)
        for x in range(17800,23400,250):
            b.box('PaleStone',(x,side*2260,910),(24,45,190),collision=False,bevel=True)
        # Tapestries are accents, not all walls. Hem and hanger have real depth.
        for x in [18600,21000,22600]:
            b.instance('SM_WovenCloth','Carpet',(x,side*2190,1160),(2.8,6.4,1),(90,0,0),False)
            b.box('Bronze',(x,side*2180,1500),(330,20,18),collision=False,bevel=True)
        # Thick framed paintings with a dark recessed backing and corner bosses.
        for x in [18900,20900,22600]:
            for dx in [-185,185]:b.box('Bronze',(x+dx,side*2400,620),(26,55,490),collision=False,bevel=True)
            for z in [375,865]:b.box('Bronze',(x,side*2400,z),(390,55,26),collision=False,bevel=True)
    # Repeated ceiling ribs, central roof opening and suspended candle rings.
    for x in [18300,19500,20700,21900,23100]:
        b.instance('SM_PointedArch','DarkStone',(x,0,1050),(5.4,.75,.65),(0,90,0),False)
    for x in [18700,20700,22600]:
        b.instance('SM_Chandelier','Bronze',(x,0,1120),(1.6,1.6,1),collision=False)
        for y in [-90,90]:b.box('Bronze',(x,y,1390),(6,6,490),collision=False)
        for a in range(8):
            theta=a*math.pi/4
            b.candles(x+145*math.cos(theta),145*math.sin(theta),1160)
    # Better furniture silhouette and properly oriented head chairs.
    for x in [19200,21600]:
        p=(x,0,0)
        b.instance('SM_Chair','DarkWood',p,(1.5,1.5,1.6),(0,chair_yaw(p),0))
    for y in [-205,205]:
        b.box('Bronze',(20400,y,132),(2230,12,20),collision=False,bevel=True)
    for x in [19450,20050,20750,21350]:
        b.box('DarkWood',(x,0,65),(50,310,105),bevel=True)
    # Worn geometric inlay in two broad combat lanes; no added blocking collision.
    for x in range(17900,23400,450):
        for y in [-1300,1300]:
            b.instance('SM_EightPointSeal','DarkStone',(x,y,2),(.8,.8,.08),collision=False)


def route_details(b):
    for _,a,c,w,h,_ in b.ROOMS:
        if w<800:continue
        for side in [-1,1]:
            for x in range(a+450,c-200,1300):
                # Layered stone shoulders reinforce wall depth, clear of traversal.
                b.box('DarkStone',(x,side*(w-45),95),(250,145,190),bevel=True)
                b.box('PaleStone',(x,side*(w-25),h-100),(310,180,50),collision=False,bevel=True)
    for x,y in [(4800,-860),(6450,-740),(12600,1320),(15400,-1300),(24100,880)]:
        b.instance('SM_Urn','Ceramic',(x,y,0),(1.5,1.5,1.7))
    # Warm focal frame behind the remembering figure; no text is added to scenery.
    for z in [150,850]:b.box('Bronze',(7670,790,z),(700,45,28),collision=False,bevel=True)
    for x in [7320,8020]:b.box('PaleStone',(x,800,500),(50,110,730),bevel=True)


def vista(b):
    # Four depth bands: parapet / abandoned roofs / palace / distant mountains.
    # These do not create traversable rooms or new encounters.
    for layer,(xbase,color,scale) in enumerate([(30300,'VistaNear',1),(35200,'VistaMid',1.5),(42200,'VistaFar',2)]):
        for i,y in enumerate([-5400,-3300,-1300,1300,3500,5700]):
            x=xbase+(i%3)*650;h=(900+(i%4)*320)*scale
            b.box(color,(x,y,h/2-450),(1050*scale,900*scale,h),collision=False,bevel=True)
            b.instance('SM_VistaDome',color,(x,y,h-450),(3.2*scale,3.2*scale,3.2*scale),collision=False)
            if i%2==0:
                b.instance('SM_CarvedPillar',color,(x+530*scale,y+250*scale,-450),(.8*scale,.8*scale,h/700),collision=False)
            if layer<2:
                for j in [-1,1]:b.box('DistantLamp',(x-530*scale,y+j*130,h*.45),(10,22,45),collision=False)
    for x,y,s in [(44000,-14000,12),(54000,0,19),(49000,15000,14)]:
        b.instance('SM_VistaRidge','VistaFar',(x,y,-1200),(s,s*.6,s*1.4),(0,90,0),False)
    # Gate relief and lit side lamps frame the outside instead of a bright skybox.
    for side in [-1,1]:
        b.instance('SM_CarvedPillar','DarkStone',(28000,side*1190,0),(1.4,1.4,1.9))
        b.candles(27600,side*1100,170,True)
