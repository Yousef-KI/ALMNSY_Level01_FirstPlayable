#pragma once
#include "CoreMinimal.h"
#include "Chapter/ALMNSYChapter.h"
#include "ALMNSYFighterV03.generated.h"

class UMaterialInstanceDynamic;
class UInstancedStaticMeshComponent;

/** v03-only shell. The v02 fighter and its saved Blueprint defaults stay intact. */
UCLASS()
class ALMNSY_LEVEL01_API AALMNSYFighterV03 : public AALMNSYFighter
{
    GENERATED_BODY()
public:
    AALMNSYFighterV03();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    virtual void DoMove(float Right, float Forward) override;
    virtual void Attack() override;
    virtual void Evade() override;
    virtual void Equip() override;
    virtual void Restore(const FTransform& Transform, bool Armed) override;
    virtual void Interact() override;
    virtual void SprintOn() override;
    virtual void SprintOff() override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    virtual void FellOutOfWorld(const UDamageType& DamageType) override;
    void GuardPressed();
    void GuardReleased();
    void Stagger(float Seconds);
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") bool bGuarding = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") bool bDodging = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") float AttackPhase = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") float DodgePhase = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") int32 ComboIndex = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") bool bHitReacting = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") float DeathElapsed = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") FVector DodgeLocalDirection = FVector::ZeroVector;
    // Visual identity is replaceable: change these mappings for a new skeleton.
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName RightUpperArm = "upperarm_r";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName RightForearm = "lowerarm_r";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName RightHand = "hand_r";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName Spine = "spine_03";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName Pelvis = "pelvis";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName LeftThigh = "thigh_l";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName LeftCalf = "calf_l";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName LeftFoot = "foot_l";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName RightThigh = "thigh_r";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName RightCalf = "calf_r";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") FName RightFoot = "foot_r";
    UPROPERTY(EditDefaultsOnly, Category="Animation|Skeleton") float PoseScale = 1.f;
protected:
    virtual void AnimateLocomotion() override;
    virtual bool CanJumpInternal_Implementation() const override;
private:
    void BeginSwing();
    void BeginDodge();
    void BeginGuard();
    void StopAction();
    void SweepBlade();
    void ThinkV03(float Now);
    void DieV03();
    void Feedback(const FVector& Location, bool Parried, bool Blocked=false);
    float Now() const;
    float SwingStarted = -100, SwingDuration = .75f, DodgeStarted = -100, DodgeReadyAt = 0;
    float DodgeBufferedUntil = -100, GuardStarted = -100, ParryReadyAt = 0, StaggerUntil = 0;
    float DamageSafeUntil = 0, NextDecision = 0, AttackReadyAt = 0, DeathStarted = 0, LastFootstep = 0;
    float LastMoveAt = -100, HitPulseUntil = 0, LastSwingPhase = 0, CameraKickUntil = 0;
    int32 QueuedAttacks = 0;
    bool bGuardHeld = false, bParryConsumed = false, bAlerted = false, bSprintHeld = false, bDeathEffectStarted = false;
    FVector MoveIntent = FVector::ZeroVector, DodgeDirection = FVector::ZeroVector, HomeLocation;
    FVector LastBladeBase = FVector::ZeroVector, LastBladeTip = FVector::ZeroVector;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> DeathMaterials;
    UPROPERTY() TObjectPtr<USoundBase> SwordSwing;
    UPROPERTY() TObjectPtr<USoundBase> SwordHit;
    UPROPERTY() TObjectPtr<USoundBase> SwordBlock;
    UPROPERTY() TObjectPtr<USoundBase> SwordParry;
    UPROPERTY() TObjectPtr<USoundBase> MemorySound;
    UPROPERTY() TObjectPtr<USoundBase> DeathSound;
    UPROPERTY() TObjectPtr<USoundBase> FootstepSound;
};

/** Small instanced fragments. No Niagara dependency, collision, or expensive emitters. */
UCLASS()
class ALMNSY_LEVEL01_API AALMNSYMemoryEffect : public AActor
{
    GENERATED_BODY()
public:
    AALMNSYMemoryEffect();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    UPROPERTY(EditAnywhere, Category="Effect") bool bAmbient = false;
    UPROPERTY(EditAnywhere, Category="Effect") bool bWarm = false;
private:
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Fragments;
    float Age = 0;
};
