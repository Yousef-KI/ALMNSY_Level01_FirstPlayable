#pragma once
#include <cmath>
#include "CombatRulesV03.h"

// Editable first-pass sword choreography, evaluated in skeletal-component space.
// Manny faces +Y before the mesh's -90 degree actor rotation. X is his right.
// These are full swing arcs, not offsets on top of the old punching animations.
namespace ALMNSYV03
{
    struct Point { float X,Y,Z; };
    struct SwordPose { Point Hand,Blade;float Torso; };
    inline float Saturate(float T){return T<0?0:T>1?1:T;}
    inline float Ease(float T){T=Saturate(T);return T*T*(3-2*T);}
    inline Point Mix(Point A,Point B,float T){return {A.X+(B.X-A.X)*T,A.Y+(B.Y-A.Y)*T,A.Z+(B.Z-A.Z)*T};}
    inline SwordPose Mix(SwordPose A,SwordPose B,float T){return {Mix(A.Hand,B.Hand,T),Mix(A.Blade,B.Blade,T),A.Torso+(B.Torso-A.Torso)*T};}
    inline SwordPose ReadyPose(){return {{27,32,116},{.30f,.68f,.65f},0};}
    inline SwordPose GuardPose(){return {{18,48,132},{-.35f,.05f,.94f},-8};}
    inline SwordPose SwingPose(int Combo,float Phase)
    {
        const auto Ready=ReadyPose();SwordPose Start,End;
        if(Combo==2) {Start={{24,24,173},{0,-.55f,.84f},-12};End={{-5,66,101},{0,.92f,-.39f},15};}
        else if(Combo==1) {Start={{-43,25,125},{-.94f,.3f,-.15f},28};End={{53,42,144},{.85f,.45f,.26f},-24};}
        else {Start={{58,5,145},{.88f,-.30f,.36f},-28};End={{-51,46,110},{-.83f,.50f,-.2f},25};}
        if(Phase<ActiveStart)return Mix(Ready,Start,Ease(Phase/ActiveStart));
        if(Phase<=ActiveEnd)
        {
            const float T=Ease((Phase-ActiveStart)/(ActiveEnd-ActiveStart));
            auto Pose=Mix(Start,End,T);
            // Forward-bowed contact path keeps the blade in front of the body.
            Pose.Hand.Y+=22.f*std::sin(T*3.14159265f);
            Pose.Blade.Y+=.5f*std::sin(T*3.14159265f);
            return Pose;
        }
        return Mix(End,Ready,Ease((Phase-ActiveEnd)/(1-ActiveEnd)));
    }
}
