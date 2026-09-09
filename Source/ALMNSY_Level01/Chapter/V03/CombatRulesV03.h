#pragma once

// Engine-independent rules used by gameplay AND the executable boundary tests.
// Attack thresholds are normalized; defense/dodge/buffer values are seconds.
namespace ALMNSYV03
{
    constexpr float ActiveStart = .28f;
    constexpr float ActiveEnd = .58f;
    constexpr float MoveAt = .60f;
    constexpr float DodgeCancelAt = .55f;
    constexpr float ChainAt = .72f;
    constexpr float QueueFrom = .08f;
    constexpr float QueueUntil = .90f;
    constexpr float DodgeBuffer = .24f;
    constexpr float DodgeDuration = .52f;
    constexpr float DodgeCooldown = .90f;
    constexpr float DodgeDistance = 360.f;
    constexpr float InvulnerableFrom = .04f;
    constexpr float InvulnerableTo = .27f;
    constexpr float ParryWindow = .16f;
    constexpr float ParryCooldown = .55f;
    constexpr float FrontalDot = .50f; // +/-60 degrees, not rear protection.
    constexpr float DamageThroughBlock = .20f;
    inline bool CanQueue(float Phase) { return Phase >= QueueFrom && Phase <= QueueUntil; }
    inline bool CanCancel(float Phase) { return Phase >= DodgeCancelAt; }
    inline bool Active(float Phase) { return Phase >= ActiveStart && Phase <= ActiveEnd; }
    inline bool DodgeSafe(float Elapsed) { return Elapsed >= InvulnerableFrom && Elapsed <= InvulnerableTo; }
    inline bool Parry(float Elapsed, float FacingDot) { return Elapsed >= 0 && Elapsed <= ParryWindow && FacingDot >= FrontalDot; }
    inline float Duration(int Combo) { return Combo == 2 ? .95f : Combo == 1 ? .78f : .75f; }
}
