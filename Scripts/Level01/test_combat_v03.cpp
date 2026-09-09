#include "Chapter/V03/CombatRulesV03.h"
#include "Chapter/V03/SwordMotionV03.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace ALMNSYV03;
int main()
{
    static_assert(ActiveStart<DodgeCancelAt && DodgeCancelAt<ActiveEnd && ActiveEnd<MoveAt && MoveAt<ChainAt);
    assert(!CanCancel(0) && !CanCancel(.3f) && CanCancel(.56f));
    assert(CanQueue(.12f) && CanQueue(.85f) && !CanQueue(.96f));
    assert(Parry(.10f,1) && !Parry(.17f,1) && !Parry(.1f,-1) && !Parry(.1f,.49f));
    assert(!DodgeSafe(0) && DodgeSafe(.10f) && !DodgeSafe(.30f));
    assert(DodgeCooldown>DodgeDuration && ParryCooldown>ParryWindow);
    // An input slightly before the legal cancel survives at common frame rates.
    for(int Fps:{12,30,60,144})for(int Combo=0;Combo<3;++Combo)
    {
        const float Length=Duration(Combo),InputAt=Length*(DodgeCancelAt-.15f);
        const float Expires=InputAt+DodgeBuffer;bool Buffered=false,Executed=false;
        for(int Frame=0;Frame<Fps*2;++Frame)
        {
            float Time=float(Frame)/Fps,Phase=Time/Length;
            if(Time>=InputAt)Buffered=true;
            if(Buffered && !Executed && Time<=Expires && CanCancel(Phase))
            { assert(Phase>=DodgeCancelAt);Executed=true; }
        }
        assert(Executed);
        assert(Length*MoveAt<Length); // movement recovery precedes clip end
    }
    // Choreography is finite, has three different swings, and returns to guard.
    for(int Combo=0;Combo<3;++Combo)for(int Frame=0;Frame<=100;++Frame)
    {
        const float Phase=Frame/100.f;auto P=SwingPose(Combo,Phase);
        assert(std::isfinite(P.Hand.X) && std::isfinite(P.Hand.Y) && std::isfinite(P.Hand.Z));
        assert(P.Hand.Z>90 && P.Hand.Z<180);
        assert(P.Blade.X*P.Blade.X+P.Blade.Y*P.Blade.Y+P.Blade.Z*P.Blade.Z>.05f);
        std::cout<<Combo<<','<<Phase<<','<<P.Hand.X<<','<<P.Hand.Y<<','<<P.Hand.Z<<','<<P.Blade.X<<','<<P.Blade.Y<<','<<P.Blade.Z<<'\n';
    }
    assert(SwingPose(0,.42f).Torso!=SwingPose(1,.42f).Torso);
    assert(std::abs(SwingPose(2,1).Hand.Z-ReadyPose().Hand.Z)<.001f);
    std::cerr<<"Combat timing, defense direction, dodge buffering and sword trajectory checks passed.\n";
}
