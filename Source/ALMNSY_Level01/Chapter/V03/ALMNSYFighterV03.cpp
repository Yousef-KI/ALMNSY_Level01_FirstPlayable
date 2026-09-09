#include "Chapter/V03/ALMNSYFighterV03.h"
#include "Chapter/V03/CombatRulesV03.h"
#include "Chapter/V03/ALMNSYAnimV03.h"
#include "AIController.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

using namespace ALMNSYV03;

namespace
{
    void Burst(UWorld* World, const FVector& Location, bool Warm)
    {
        const FTransform Transform(Location);
        auto* Effect=World->SpawnActorDeferred<AALMNSYMemoryEffect>(AALMNSYMemoryEffect::StaticClass(),Transform,
            nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if (Effect) { Effect->bWarm=Warm; Effect->FinishSpawning(Transform); }
    }
}

AALMNSYFighterV03::AALMNSYFighterV03()
{
    GetCameraBoom()->TargetArmLength=355;
    GetCameraBoom()->CameraLagSpeed=13;
    GetCameraBoom()->bUseCameraLagSubstepping=true;
}
float AALMNSYFighterV03::Now() const { return GetWorld()->GetTimeSeconds(); }
void AALMNSYFighterV03::AnimateLocomotion() { /* v03 uses one persistent native anim graph. */ }
void AALMNSYFighterV03::BeginPlay()
{
    Super::BeginPlay();
    HomeLocation=GetActorLocation();
    Sword->AttachToComponent(GetMesh(),FAttachmentTransformRules::SnapToTargetNotIncludingScale,RightHand);
    Sword->SetRelativeRotation(FRotator::ZeroRotator);
    Sword->SetRelativeLocation(FVector::ZeroVector);
    if (!bStoryCharacter) GetMesh()->SetAnimInstanceClass(UALMNSYAnimV03::StaticClass());
    const TCHAR* Names[]={TEXT("S_Swing"),TEXT("S_Impact"),TEXT("S_Block"),TEXT("S_Parry"),TEXT("S_Memory"),TEXT("S_Death")};
    TObjectPtr<USoundBase>* Targets[]={&SwordSwing,&SwordHit,&SwordBlock,&SwordParry,&MemorySound,&DeathSound};
    for (int32 I=0;I<6;++I) *Targets[I]=LoadObject<USoundBase>(nullptr,*(FString(TEXT("/Game/ALMNSY/Versions/v03/Audio/"))+Names[I]));
    FootstepSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/ALMNSY/Audio/S_Step"));
    if (bEnemy)
    {
        const TCHAR* Path=bHeavy?TEXT("/Game/ALMNSY/Versions/v03/Materials/MI_Guard_Bronze"):TEXT("/Game/ALMNSY/Versions/v03/Materials/MI_Guard_Charcoal");
        if (auto* Material=LoadObject<UMaterialInterface>(nullptr,Path))
            for (int32 I=0;I<GetMesh()->GetNumMaterials();++I)
            {
                GetMesh()->SetMaterial(I,Material);
                if (auto* MID=GetMesh()->CreateDynamicMaterialInstance(I)) { MID->SetScalarParameterValue(TEXT("MemoryFade"),-.1f);DeathMaterials.Add(MID); }
            }
    }
}
void AALMNSYFighterV03::Equip()
{
    bArmed=true;
    if (auto* BladeAsset=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/ALMNSY/Versions/v03/Environment/Props/SM_TemporarySaif"))) Sword->SetStaticMesh(BladeAsset);
    if (auto* Mat=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/ALMNSY/Versions/v03/Materials/MI_AgedMetal"))) Sword->SetMaterial(0,Mat);
    Sword->SetVisibility(true);
}
void AALMNSYFighterV03::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindKey(EKeys::RightMouseButton,IE_Pressed,this,&AALMNSYFighterV03::GuardPressed);
    Input->BindKey(EKeys::RightMouseButton,IE_Released,this,&AALMNSYFighterV03::GuardReleased);
    Input->BindKey(EKeys::Gamepad_LeftShoulder,IE_Pressed,this,&AALMNSYFighterV03::GuardPressed);
    Input->BindKey(EKeys::Gamepad_LeftShoulder,IE_Released,this,&AALMNSYFighterV03::GuardReleased);
}
void AALMNSYFighterV03::Restore(const FTransform& Transform,bool Armed)
{
    Super::Restore(Transform,Armed);DamageSafeUntil=Now()+1.5f;
}
void AALMNSYFighterV03::DoMove(float Right,float Forward)
{
    if (!Controller) return;
    const FRotationMatrix Matrix(FRotator(0,Controller->GetControlRotation().Yaw,0));
    MoveIntent=(Matrix.GetUnitAxis(EAxis::X)*Forward+Matrix.GetUnitAxis(EAxis::Y)*Right).GetSafeNormal2D();
    LastMoveAt=Now();
    if (bDead || bDodging || bHitReacting || (bAttacking && AttackPhase<MoveAt)) return;
    Super::DoMove(Right,Forward);
}
bool AALMNSYFighterV03::CanJumpInternal_Implementation() const
{ return !bDead && !bAttacking && !bDodging && !bGuarding && !bHitReacting && Super::CanJumpInternal_Implementation(); }
void AALMNSYFighterV03::SprintOn() { bSprintHeld=true; }
void AALMNSYFighterV03::SprintOff() { bSprintHeld=false; }
void AALMNSYFighterV03::Attack()
{
    if (!bArmed || bDead || bStoryCharacter || bDodging || Now()<StaggerUntil || GetCharacterMovement()->IsFalling()) return;
    if (auto* D=AALMNSYChapterDirector::Find(GetWorld());D && D->bComplete)return;
    if (bAttacking)
    {
        if (CanQueue(AttackPhase))QueuedAttacks=FMath::Min(QueuedAttacks+1,2-ComboIndex);
        return;
    }
    if (Now()<AttackReadyAt)return;
    ComboIndex=0;QueuedAttacks=0;BeginSwing();
}
void AALMNSYFighterV03::BeginSwing()
{
    bAttacking=true;bGuarding=false;bHitReacting=false;AttackPhase=0;LastSwingPhase=0;
    SwingStarted=Now();SwingDuration=Duration(ComboIndex)*(bEnemy?(bHeavy?1.6f:1.25f):1.f);
    HitActors.Empty();
    GetCharacterMovement()->StopMovementImmediately();
    // Deliberately remain in MOVE_Walking: gravity and later recovery input work.
    GetCharacterMovement()->bOrientRotationToMovement=false;
    LastBladeBase=Sword->GetComponentTransform().TransformPosition(FVector(0,0,14));
    LastBladeTip=Sword->GetComponentTransform().TransformPosition(FVector(10,0,90));
    if (auto* AI=Cast<AAIController>(Controller))AI->StopMovement();
}
void AALMNSYFighterV03::StopAction()
{
    bAttacking=false;QueuedAttacks=0;bGuarding=false;
    GetCharacterMovement()->bOrientRotationToMovement=true;
    TellLight->SetIntensity(0);
}
void AALMNSYFighterV03::Evade()
{
    if (bDead || bEnemy || bStoryCharacter || bDodging || Now()<DodgeReadyAt || Now()<StaggerUntil || GetCharacterMovement()->IsFalling())return;
    if (auto* D=AALMNSYChapterDirector::Find(GetWorld());D && D->bComplete)return;
    if (bAttacking && !CanCancel(AttackPhase)) { DodgeBufferedUntil=Now()+DodgeBuffer;return; }
    BeginDodge();
}
void AALMNSYFighterV03::BeginDodge()
{
    StopAction();bDodging=true;DodgePhase=0;DodgeStarted=Now();DodgeReadyAt=Now()+DodgeCooldown;
    DodgeBufferedUntil=-100;
    DodgeDirection=Now()-LastMoveAt<.10f && !MoveIntent.IsNearlyZero()?MoveIntent:-GetActorForwardVector();
    DodgeLocalDirection=GetActorTransform().InverseTransformVectorNoScale(DodgeDirection);
    GetCharacterMovement()->StopMovementImmediately();
}
void AALMNSYFighterV03::GuardPressed()
{
    if (bDead || !bArmed || bEnemy || bStoryCharacter)return;
    bGuardHeld=true;
    if (!bDodging && (!bAttacking || CanCancel(AttackPhase)) && Now()>=StaggerUntil)BeginGuard();
}
void AALMNSYFighterV03::GuardReleased() { bGuardHeld=false;bGuarding=false; }
void AALMNSYFighterV03::BeginGuard()
{
    if (bGuarding)return;
    StopAction();bGuarding=true;
    GuardStarted=Now()>=ParryReadyAt?Now():-100.f;
    bParryConsumed=false;ParryReadyAt=Now()+ParryCooldown;
}
void AALMNSYFighterV03::Tick(float Dt)
{
    // Skip the v02 combat tick intentionally; retain ACharacter movement ticking.
    AALMNSY_Level01Character::Tick(Dt);
    const float Time=Now();
    if (bStoryCharacter)return;
    if (bDead)
    {
        DeathElapsed=Time-DeathStarted;
        if (bEnemy && DeathElapsed>4.5f)
        {
            if (!bDeathEffectStarted) { bDeathEffectStarted=true;Burst(GetWorld(),GetActorLocation()-FVector(0,0,35),false); }
            const float Fade=FMath::Clamp((DeathElapsed-4.5f)/2.2f,0.f,1.1f);
            for (const auto& MID:DeathMaterials)if(MID)MID->SetScalarParameterValue(TEXT("MemoryFade"),Fade);
            if (Fade>.75f)Sword->SetVisibility(false);
        }
        return;
    }
    if (auto* D=AALMNSYChapterDirector::Find(GetWorld());D && D->bComplete)
    { StopAction();bDodging=false;return; }
    bHitReacting=Time<StaggerUntil;
    if (bEnemy && Time>=NextDecision) { NextDecision=Time+.12f;ThinkV03(Time); }
    if (bAttacking)
    {
        AttackPhase=FMath::Clamp((Time-SwingStarted)/SwingDuration,0.f,1.f);
        if (LastSwingPhase<ActiveStart && AttackPhase>=ActiveStart && SwordSwing)
            UGameplayStatics::PlaySoundAtLocation(this,SwordSwing,GetActorLocation(),.30f);
        // Include a frame that crosses the entire active interval at low FPS.
        if (AttackPhase>=ActiveStart && LastSwingPhase<=ActiveEnd)SweepBlade();
        else
        {
            LastBladeBase=Sword->GetComponentTransform().TransformPosition(FVector(0,0,14));
            LastBladeTip=Sword->GetComponentTransform().TransformPosition(FVector(10,0,90));
        }
        LastSwingPhase=AttackPhase;
        TellLight->SetIntensity(bEnemy && AttackPhase<ActiveStart?320.f:0.f);
        if (!bEnemy && CanCancel(AttackPhase) && Time<=DodgeBufferedUntil)BeginDodge();
        else if (!bEnemy && bGuardHeld && CanCancel(AttackPhase))BeginGuard();
        else if (!bEnemy && AttackPhase>=ChainAt && QueuedAttacks>0 && ComboIndex<2)
        { --QueuedAttacks;++ComboIndex;BeginSwing(); }
        else if (AttackPhase>=1.f)
        { StopAction();AttackReadyAt=Time+(bEnemy?(bHeavy?.65f:.42f):.06f); }
    }
    if (bDodging)
    {
        const float Before=DodgePhase;DodgePhase=FMath::Clamp((Time-DodgeStarted)/DodgeDuration,0.f,1.f);
        // Half cosine travel starts/ends smoothly. Swept capsule stops at walls.
        auto Ease=[](float T){return .5f-.5f*FMath::Cos(PI*T);};
        FHitResult Hit;
        SetActorLocation(GetActorLocation()+DodgeDirection*DodgeDistance*(Ease(DodgePhase)-Ease(Before)),true,&Hit);
        if (DodgePhase>=1.f){bDodging=false;if(bGuardHeld)BeginGuard();}
    }
    if (bGuardHeld && !bGuarding && !bAttacking && !bDodging && !bHitReacting)BeginGuard();
    auto* Move=GetCharacterMovement();
    const bool Locked=bDodging || bHitReacting || (bAttacking && AttackPhase<MoveAt);
    Move->MaxWalkSpeed=Locked?0.f:bGuarding?145.f:bEnemy?(bHeavy?205.f:275.f):bSprintHeld?540.f:360.f;
    Move->bOrientRotationToMovement=!bGuarding && !bDodging && (!bAttacking || AttackPhase>=MoveAt);
    if (bGuarding && Controller)
        SetActorRotation(FMath::RInterpTo(GetActorRotation(),FRotator(0,Controller->GetControlRotation().Yaw,0),Dt,12));
    if (!bAttacking)TellLight->SetIntensity(Time<HitPulseUntil?430.f:0);
    const float Pulse=FMath::Clamp((CameraKickUntil-Time)/.12f,0.f,1.f);
    GetCameraBoom()->TargetArmLength=FMath::FInterpTo(GetCameraBoom()->TargetArmLength,355.f-Pulse*9.f,Dt,22.f);
    if (IsPlayerControlled() && GetVelocity().Size2D()>100 && Move->IsMovingOnGround() && Time-LastFootstep>.37f)
    { LastFootstep=Time;if(FootstepSound)UGameplayStatics::PlaySoundAtLocation(this,FootstepSound,GetActorLocation(),.13f); }
    if (GetActorLocation().Z < -900)DieV03();
}
void AALMNSYFighterV03::SweepBlade()
{
    const FVector Base=Sword->GetComponentTransform().TransformPosition(FVector(0,0,14));
    const FVector Tip=Sword->GetComponentTransform().TransformPosition(FVector(10,0,90));
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ALMNSYV03Blade),false,this);
    TArray<FHitResult> Hits;
    // Three swept points plus the current blade segment; no giant forward punch sphere.
    for (float Alpha : {0.f,.5f,1.f})
    {
        TArray<FHitResult> Slice;
        GetWorld()->SweepMultiByObjectType(Slice,FMath::Lerp(LastBladeBase,LastBladeTip,Alpha),FMath::Lerp(Base,Tip,Alpha),
            FQuat::Identity,Objects,FCollisionShape::MakeSphere(18.f),Query);Hits.Append(Slice);
    }
    TArray<FHitResult> Segment;
    GetWorld()->SweepMultiByObjectType(Segment,Base,Tip,FQuat::Identity,Objects,FCollisionShape::MakeSphere(18.f),Query);Hits.Append(Segment);
    LastBladeBase=Base;LastBladeTip=Tip;
    for (const auto& Hit:Hits)
    {
        auto* Other=Hit.GetActor();if(!Other || HitActors.Contains(Other))continue;
        FHitResult Wall;
        if (GetWorld()->LineTraceSingleByChannel(Wall,GetActorLocation()+FVector(0,0,35),Hit.ImpactPoint,ECC_Visibility,Query) && Wall.GetActor()!=Other)continue;
        if (auto* Fighter=Cast<AALMNSYFighter>(Other))
        {
            if (Fighter->bDead || Fighter->bStoryCharacter || Fighter->bEnemy==bEnemy)continue;
            HitActors.Add(Other);
            const float Applied=UGameplayStatics::ApplyDamage(Fighter,bEnemy?(bHeavy?32.f:17.f):(ComboIndex==2?42.f:30.f),Controller,this,nullptr);
            if (Applied>0) { Feedback(Hit.ImpactPoint,false);CameraKickUntil=Now()+.12f; }
        }
        else if (auto* C=Hit.GetComponent();C && C->IsSimulatingPhysics())
        {
            HitActors.Add(Other);C->AddImpulseAtLocation((GetActorForwardVector()*240+FVector(0,0,90))*C->GetMass(),Hit.ImpactPoint);
            Feedback(Hit.ImpactPoint,false);
        }
    }
}
void AALMNSYFighterV03::ThinkV03(float Time)
{
    auto* AI=Cast<AAIController>(Controller);auto* P=Cast<AALMNSYFighter>(UGameplayStatics::GetPlayerPawn(this,0));
    auto* D=AALMNSYChapterDirector::Find(GetWorld());
    if (!AI || !P || P->bDead || !D || !D->bSword || D->bComplete || (Encounter>0 && !D->Cleared(Encounter-1)))
    { if(AI)AI->StopMovement();return; }
    if (Time<StaggerUntil || bAttacking)return;
    const float Dist=FVector::Dist2D(GetActorLocation(),P->GetActorLocation());
    if (!bAlerted && Dist<1450 && AI->LineOfSightTo(P))bAlerted=true;
    if (!bAlerted)return;
    if (FVector::Dist2D(HomeLocation,P->GetActorLocation())>3400)
    { AI->MoveToLocation(HomeLocation,60);bAlerted=false;return; }
    if (Dist<155 && AI->LineOfSightTo(P))
    {
        AI->StopMovement();
        SetActorRotation(FRotator(0,(P->GetActorLocation()-GetActorLocation()).Rotation().Yaw,0));
        // At most two attackers committing at once. Others remain readable nearby.
        int32 Committing=0;
        for(TActorIterator<AALMNSYFighterV03> It(GetWorld());It;++It)
            if(It->bEnemy && !It->bDead && It->bAttacking && It->Encounter==Encounter)++Committing;
        if(Time>=AttackReadyAt && Committing<2)Attack();
    }
    else AI->MoveToActor(P,35.f,true,true,true,nullptr,true);
}
void AALMNSYFighterV03::Feedback(const FVector& Location,bool Parried,bool Blocked)
{
    auto* Sound=Parried?SwordParry.Get():Blocked?SwordBlock.Get():SwordHit.Get();
    if(Sound)UGameplayStatics::PlaySoundAtLocation(this,Sound,Location,Parried?.5f:.3f);
    Burst(GetWorld(),Location,!Parried);HitPulseUntil=Now()+.10f;
}
float AALMNSYFighterV03::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    const float Time=Now();
    if(bDead || bStoryCharacter || Damage<=0 || Time<DamageSafeUntil || (bDodging && DodgeSafe(Time-DodgeStarted)))return 0;
    if(auto* D=AALMNSYChapterDirector::Find(GetWorld());D && D->bComplete)return 0;
    auto* Attacker=Cast<AALMNSYFighterV03>(Causer);
    const bool Melee=Attacker && Attacker->bEnemy!=bEnemy;
    const float Facing=Melee?FVector::DotProduct(GetActorForwardVector(),(Causer->GetActorLocation()-GetActorLocation()).GetSafeNormal2D()):-1.f;
    if(bGuarding && Melee && Facing>=FrontalDot)
    {
        if(!bParryConsumed && Parry(Time-GuardStarted,Facing))
        {
            bParryConsumed=true;Attacker->Stagger(1.1f);Feedback(Sword->GetComponentLocation(),true);CameraKickUntil=Time+.1f;
            return 0; // No global i-frames: a rear attacker can still connect.
        }
        Damage*=DamageThroughBlock;Feedback(Sword->GetComponentLocation(),false,true);
    }
    else
    {
        DamageSafeUntil=Time+(bEnemy?.15f:.5f);
        Stagger(bHeavy?.17f:.29f);
    }
    bAlerted=true;Health=FMath::Max(0.f,Health-Damage);HitPulseUntil=Time+.10f;
    if(Health<=0)DieV03();
    return Damage;
}
void AALMNSYFighterV03::Stagger(float Seconds)
{
    if(bDead)return;
    StopAction();bDodging=false;DodgeBufferedUntil=-100;StaggerUntil=Now()+Seconds;bHitReacting=true;
    GetCharacterMovement()->StopMovementImmediately();
    if(auto* AI=Cast<AAIController>(Controller))AI->StopMovement();
}
void AALMNSYFighterV03::DieV03()
{
    if(bDead)return;
    StopAction();bDead=true;bDodging=false;bGuardHeld=false;Health=0;DeathStarted=Now();DeathElapsed=0;
    GetCharacterMovement()->DisableMovement();GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(auto* AI=Cast<AAIController>(Controller))AI->StopMovement();
    if(DeathSound)UGameplayStatics::PlaySoundAtLocation(this,DeathSound,GetActorLocation(),.35f);
    auto* D=AALMNSYChapterDirector::Find(GetWorld());
    if(bEnemy)
    {
        if(D)D->GuardFell(GuardId); // Progress immediately; visual body is independent.
        SetLifeSpan(7.f);
    }
    else if(D)
    {
        D->Say(FText::FromString(TEXT("The memory slips away…")),3.f);
        FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,D,&AALMNSYChapterDirector::RestartCheckpoint,3.f,false);
    }
}
void AALMNSYFighterV03::FellOutOfWorld(const UDamageType& DamageType) { DieV03(); }
void AALMNSYFighterV03::Interact()
{
    if(bDead || bAttacking || bDodging || bHitReacting)return;
    auto* D=AALMNSYChapterDirector::Find(GetWorld());if(!D || D->bComplete)return;
    if(auto* I=D->NearestInteraction())
    {
        auto* Before=D->Saved.Get();I->Use(this);
        if(Before!=D->Saved.Get())
        { Burst(GetWorld(),I->GetActorLocation()+FVector(0,0,145),false);if(MemorySound)UGameplayStatics::PlaySoundAtLocation(this,MemorySound,I->GetActorLocation(),.4f); }
    }
}
