#include "Chapter/ALMNSYChapter.h"
#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputAction.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

AALMNSYFighter::AALMNSYFighter()
{
    PrimaryActorTick.bCanEverTick = true;
    AIControllerClass = AAIController::StaticClass();
    AutoPossessAI = EAutoPossessAI::Disabled;
    GetCharacterMovement()->MaxWalkSpeed = 360.f;
    GetCharacterMovement()->bUseRVOAvoidance = true;
    GetCameraBoom()->TargetArmLength = 380.f;
    GetCameraBoom()->SocketOffset = FVector(0, 45, 35);
    GetCameraBoom()->bEnableCameraLag = true;
    GetMesh()->SetRelativeLocationAndRotation(FVector(0, 0, -96), FRotator(0, -90, 0));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GetMesh()->SetCanEverAffectNavigation(false);
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Manny(TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"));
    GetMesh()->SetSkeletalMesh(Manny.Object);
    static ConstructorHelpers::FObjectFinder<UBlendSpace> MoveBS(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run"));
    Locomotion = MoveBS.Object;
    static ConstructorHelpers::FObjectFinder<UAnimSequence> A1(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_01"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> A2(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> A3(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_03"));
    Attacks = {A1.Object, A2.Object, A3.Object};
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Hit(TEXT("/Game/Characters/Mannequins/Anims/Rifle/HitReact/MM_HitReact_Front_Lgt_01"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Death(TEXT("/Game/Characters/Mannequins/Anims/Death/MM_Death_Front_01"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Idle(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle"));
    HitAnimation = Hit.Object;
    DeathAnimation = Death.Object;
    IdleAnimation = Idle.Object;
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Fall(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Fall_Loop"));
    FallAnimation = Fall.Object;
    static ConstructorHelpers::FObjectFinder<UInputAction> MoveIA(TEXT("/Game/Input/Actions/IA_Move"));
    static ConstructorHelpers::FObjectFinder<UInputAction> LookIA(TEXT("/Game/Input/Actions/IA_Look"));
    static ConstructorHelpers::FObjectFinder<UInputAction> MouseIA(TEXT("/Game/Input/Actions/IA_MouseLook"));
    static ConstructorHelpers::FObjectFinder<UInputAction> JumpIA(TEXT("/Game/Input/Actions/IA_Jump"));
    MoveAction = MoveIA.Object;
    LookAction = LookIA.Object;
    MouseLookAction = MouseIA.Object;
    JumpAction = JumpIA.Object;
    Sword = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TemporarySaif"));
    Sword->SetupAttachment(GetMesh(), TEXT("hand_r"));
    Sword->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Sword->SetCanEverAffectNavigation(false);
    Sword->SetRelativeRotation(FRotator(0, 0, -90));
    TellLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("AttackTell"));
    TellLight->SetupAttachment(RootComponent);
    TellLight->SetRelativeLocation(FVector(0, 0, 65));
    TellLight->SetLightColor(FLinearColor(1.f, .28f, .055f));
    TellLight->SetAttenuationRadius(210.f);
    TellLight->SetCastShadows(false);
    TellLight->SetIntensity(0.f);
}

void AALMNSYFighter::BeginPlay()
{
    Super::BeginPlay();
    Home = GetActorLocation();
    Health = bEnemy ? (bHeavy ? 170.f : 75.f) : MaxHealth;
    MaxHealth = Health;
    if (bEnemy)
    {
        if (!GetController()) SpawnDefaultController();
        GetCharacterMovement()->MaxWalkSpeed = bHeavy ? 205.f : 275.f;
        if (bHeavy) GetMesh()->SetRelativeScale3D(FVector(1.15f));
        if (auto* M = LoadObject<UMaterialInterface>(nullptr, bHeavy ?
            TEXT("/Game/ALMNSY/Materials/MI_Guard_Bronze") : TEXT("/Game/ALMNSY/Materials/MI_Guard_Charcoal")))
            for (int32 I = 0; I < GetMesh()->GetNumMaterials(); ++I) GetMesh()->SetMaterial(I, M);
        Equip();
    }
    if (bStoryCharacter)
    {
        GetCharacterMovement()->DisableMovement();
        GetMesh()->PlayAnimation(IdleAnimation, true);
    }
    if (!bArmed) Sword->SetVisibility(false);
    SwingSound = LoadObject<USoundBase>(nullptr, TEXT("/Game/ALMNSY/Audio/S_Swing"));
    HitSound = LoadObject<USoundBase>(nullptr, TEXT("/Game/ALMNSY/Audio/S_Impact"));
    StepSound = LoadObject<USoundBase>(nullptr, TEXT("/Game/ALMNSY/Audio/S_Step"));
    if (!bStoryCharacter) AnimateLocomotion();
}

void AALMNSYFighter::Equip()
{
    bArmed = true;
    if (auto* Mesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/ALMNSY/Environment/Props/SM_TemporarySaif"))) Sword->SetStaticMesh(Mesh);
    if (auto* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/ALMNSY/Materials/MI_AgedMetal"))) Sword->SetMaterial(0, M);
    Sword->SetVisibility(true);
}

void AALMNSYFighter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &AALMNSYFighter::Attack);
    Input->BindKey(EKeys::Gamepad_RightShoulder, IE_Pressed, this, &AALMNSYFighter::Attack);
    Input->BindKey(EKeys::E, IE_Pressed, this, &AALMNSYFighter::Interact);
    Input->BindKey(EKeys::Gamepad_FaceButton_Left, IE_Pressed, this, &AALMNSYFighter::Interact);
    Input->BindKey(EKeys::LeftControl, IE_Pressed, this, &AALMNSYFighter::Evade);
    Input->BindKey(EKeys::Gamepad_FaceButton_Right, IE_Pressed, this, &AALMNSYFighter::Evade);
    Input->BindKey(EKeys::LeftShift, IE_Pressed, this, &AALMNSYFighter::SprintOn);
    Input->BindKey(EKeys::LeftShift, IE_Released, this, &AALMNSYFighter::SprintOff);
}

void AALMNSYFighter::AnimateLocomotion()
{
    if (bMovingAnimation || bStoryCharacter) return;
    GetMesh()->PlayAnimation(Locomotion, true);
    GetMesh()->SetPlayRate(1.f);
    bMovingAnimation = true;
}

void AALMNSYFighter::Tick(float Dt)
{
    Super::Tick(Dt);
    const float Now = GetWorld()->GetTimeSeconds();
    if (bDead || bStoryCharacter) return;
    if (bEnemy && Now >= NextThink) { NextThink = Now + .2f; Think(Now); }
    if (bAttacking)
    {
        const float Phase = (Now - AttackStarted) / AttackLength;
        TellLight->SetIntensity(bEnemy && Phase < .40f ? 450.f : 0.f);
        if (Phase >= .38f && Phase <= .64f) TraceAttack();
        if (Phase >= 1.f)
        {
            bAttacking = false;
            GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            GetCharacterMovement()->bOrientRotationToMovement = true;
            if (bQueued && !bEnemy) { bQueued = false; Combo = (Combo + 1) % 3; StartAttack(); }
            else { Combo = 0; AnimateLocomotion(); }
        }
    }
    else if (Now >= RecoverAt)
    {
        if (GetCharacterMovement()->IsFalling())
        {
            if (!bAirAnimation) { GetMesh()->PlayAnimation(FallAnimation, true); bAirAnimation = true; bMovingAnimation = false; }
        }
        else
        {
            bAirAnimation = false;
            AnimateLocomotion();
            if (auto* Anim = GetMesh()->GetSingleNodeInstance())
            {
                FVector Input = FVector::ZeroVector;
                if (Locomotion)
                    for (int32 Axis = 0; Axis < 3; ++Axis)
                        if (Locomotion->GetBlendParameter(Axis).DisplayName.Contains(TEXT("Speed"))) Input[Axis] = GetVelocity().Size2D();
                Anim->SetBlendSpaceInput(Input);
            }
        }
        TellLight->SetIntensity(Now < HitFlashUntil ? 900.f : 0.f);
    }
    if (IsPlayerControlled() && GetVelocity().Size2D() > 90.f && GetCharacterMovement()->IsMovingOnGround() && Now - LastStep > .42f)
    {
        LastStep = Now;
        if (StepSound) UGameplayStatics::PlaySoundAtLocation(this, StepSound, GetActorLocation(), .16f);
    }
    if (GetActorLocation().Z < -900.f) Die();
}

void AALMNSYFighter::Attack()
{
    if (!bArmed || bDead || bStoryCharacter) return;
    if (auto* D = AALMNSYChapterDirector::Find(GetWorld()); D && D->bComplete) return;
    if (bAttacking) { bQueued = true; return; }
    if (GetWorld()->GetTimeSeconds() < RecoverAt || GetCharacterMovement()->IsFalling()) return;
    StartAttack();
}

void AALMNSYFighter::StartAttack()
{
    bAttacking = true;
    bMovingAnimation = false;
    Struck.Empty();
    AttackStarted = GetWorld()->GetTimeSeconds();
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->DisableMovement();
    GetCharacterMovement()->bOrientRotationToMovement = false;
    UAnimSequence* Sequence = Attacks.IsValidIndex(Combo) ? Attacks[Combo].Get() : nullptr;
    const float Rate = bHeavy ? .70f : 1.05f;
    AttackLength = Sequence ? FMath::Max(.5f, Sequence->GetPlayLength() / Rate) : .85f;
    if (Sequence)
    {
        GetMesh()->PlayAnimation(Sequence, false);
        GetMesh()->SetPlayRate(Rate);
    }
    if (SwingSound) UGameplayStatics::PlaySoundAtLocation(this, SwingSound, GetActorLocation(), .25f);
}

void AALMNSYFighter::TraceAttack()
{
    // Authored timing window + forward volume. One damage event per actor per swing.
    const FVector Start = GetActorLocation() + FVector(0, 0, 65);
    const FVector End = Start + GetActorForwardVector() * (bHeavy ? 160.f : 140.f);
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_Pawn);
    Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ALMNSYMelee), false, this);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByObjectType(Hits, Start, End, FQuat::Identity, Objects, FCollisionShape::MakeSphere(58.f), Query);
    for (const FHitResult& H : Hits)
    {
        AActor* Other = H.GetActor();
        if (!Other || Struck.Contains(Other)) continue;
        FHitResult Wall;
        if (GetWorld()->LineTraceSingleByChannel(Wall, Start, Other->GetActorLocation(), ECC_Visibility, Query) && Wall.GetActor() != Other) continue;
        Struck.Add(Other);
        if (auto* Fighter = Cast<AALMNSYFighter>(Other))
        {
            if (Fighter->bEnemy == bEnemy || Fighter->bStoryCharacter) continue;
            UGameplayStatics::ApplyDamage(Fighter, bEnemy ? (bHeavy ? 32.f : 17.f) : (Combo == 2 ? 42.f : 30.f), GetController(), this, nullptr);
        }
        else if (auto* C = H.GetComponent(); C && C->IsSimulatingPhysics())
        {
            C->AddImpulseAtLocation((GetActorForwardVector() * 230.f + FVector(0, 0, 100.f)) * C->GetMass(), H.ImpactPoint);
            if (HitSound) UGameplayStatics::PlaySoundAtLocation(this, HitSound, H.ImpactPoint, .25f);
        }
    }
}

void AALMNSYFighter::Think(float Now)
{
    auto* AI = Cast<AAIController>(GetController());
    auto* Player = Cast<AALMNSYFighter>(UGameplayStatics::GetPlayerPawn(this, 0));
    auto* D = AALMNSYChapterDirector::Find(GetWorld());
    if (!AI || !Player || Player->bDead || !D || !D->bSword || D->bComplete)
    { if (AI) AI->StopMovement(); return; }
    // Encounters remain dormant until previous spaces are cleared. No surprise spawns.
    if (Encounter > 0 && !D->Cleared(Encounter - 1)) return;
    const float Distance = FVector::Dist2D(GetActorLocation(), Player->GetActorLocation());
    if (!bAlert && Distance < 1450.f && AI->LineOfSightTo(Player)) bAlert = true;
    if (!bAlert || Now < RecoverAt || bAttacking) return;
    if (FVector::Dist2D(Home, Player->GetActorLocation()) > 3400.f)
    { AI->MoveToLocation(Home, 80.f); bAlert = false; return; }
    if (Distance < (bHeavy ? 205.f : 185.f) && AI->LineOfSightTo(Player))
    {
        AI->StopMovement();
        if (Now >= NextAttack)
        {
            SetActorRotation(FRotator(0, (Player->GetActorLocation() - GetActorLocation()).Rotation().Yaw, 0));
            NextAttack = Now + (bHeavy ? 3.4f : 2.5f) + FMath::FRandRange(0.f, .5f);
            Attack();
        }
    }
    // Path following adds capsule radii to this distance. Keep its stopping
    // distance inside the weak guard's 185cm attack threshold.
    else AI->MoveToActor(Player, 55.f, true, true, true, nullptr, true);
}

float AALMNSYFighter::TakeDamage(float Damage, const FDamageEvent& Event, AController* Instigator, AActor* Causer)
{
    const float Now = GetWorld()->GetTimeSeconds();
    if (bDead || bStoryCharacter || Damage <= 0.f || Now < InvulnerableUntil) return 0.f;
    if (auto* D = AALMNSYChapterDirector::Find(GetWorld()); D && D->bComplete) return 0.f;
    Health = FMath::Max(0.f, Health - Damage);
    InvulnerableUntil = Now + (bEnemy ? .16f : .6f);
    bAlert = true;
    HitFlashUntil = Now + .16f;
    if (HitSound) UGameplayStatics::PlaySoundAtLocation(this, HitSound, GetActorLocation(), .4f);
    if (Health <= 0.f) { Die(); return Damage; }
    if (!bHeavy || !bAttacking)
    {
        bAttacking = false;
        bQueued = false;
        bMovingAnimation = false;
        RecoverAt = Now + .35f;
        GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        GetCharacterMovement()->bOrientRotationToMovement = true;
        GetCharacterMovement()->StopMovementImmediately();
        if (auto* AI = Cast<AAIController>(GetController())) AI->StopMovement();
        if (HitAnimation) GetMesh()->PlayAnimation(HitAnimation, false);
    }
    return Damage;
}

void AALMNSYFighter::Die()
{
    if (bDead) return;
    bDead = true; Health = 0.f; bAttacking = false;
    TellLight->SetIntensity(0);
    GetCharacterMovement()->DisableMovement();
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (auto* AI = Cast<AAIController>(GetController())) AI->StopMovement();
    if (DeathAnimation) GetMesh()->PlayAnimation(DeathAnimation, false);
    auto* D = AALMNSYChapterDirector::Find(GetWorld());
    if (bEnemy)
    {
        if (D) D->GuardFell(GuardId);
        SetLifeSpan(12.f);
    }
    else if (D)
    {
        D->Say(FText::FromString(TEXT("The memory slips away…")), 3.f);
        FTimerHandle Handle;
        GetWorldTimerManager().SetTimer(Handle, D, &AALMNSYChapterDirector::RestartCheckpoint, 3.f, false);
    }
}

void AALMNSYFighter::FellOutOfWorld(const UDamageType& DamageType) { Die(); }

void AALMNSYFighter::Restore(const FTransform& Transform, bool Armed)
{
    SetActorTransform(Transform, false, nullptr, ETeleportType::TeleportPhysics);
    Health = MaxHealth;
    if (GetController()) GetController()->SetControlRotation(Transform.Rotator());
    if (Armed) Equip();
    InvulnerableUntil = GetWorld()->GetTimeSeconds() + 1.5f;
}

void AALMNSYFighter::Evade()
{
    const float Now = GetWorld()->GetTimeSeconds();
    if (bDead || bAttacking || bStoryCharacter || Now < EvadeReady || GetCharacterMovement()->IsFalling()) return;
    if (auto* D = AALMNSYChapterDirector::Find(GetWorld()); D && D->bComplete) return;
    EvadeReady = Now + 1.2f; InvulnerableUntil = Now + .3f;
    const FVector Direction = GetLastMovementInputVector().IsNearlyZero() ? GetActorForwardVector() : GetLastMovementInputVector().GetSafeNormal2D();
    LaunchCharacter(Direction * 730.f + FVector(0, 0, 65), true, true);
}
void AALMNSYFighter::Interact()
{
    if (bDead || bAttacking) return;
    if (auto* D = AALMNSYChapterDirector::Find(GetWorld()); D && !D->bComplete)
        if (auto* I = D->NearestInteraction()) I->Use(this);
}
void AALMNSYFighter::SprintOn() { if (!bEnemy) GetCharacterMovement()->MaxWalkSpeed = 540.f; }
void AALMNSYFighter::SprintOff() { if (!bEnemy) GetCharacterMovement()->MaxWalkSpeed = 360.f; }
