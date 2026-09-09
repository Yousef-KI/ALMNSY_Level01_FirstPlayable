#include "Chapter/ALMNSYChapter.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "Camera/PlayerCameraManager.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

AALMNSYChapterDirector::AALMNSYChapterDirector()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = .2f;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("ChapterRoot"));
}
FString AALMNSYChapterDirector::SaveSlot() { return TEXT("ALMNSY_Level01_v01_Checkpoint"); }
AALMNSYChapterDirector* AALMNSYChapterDirector::Find(const UWorld* World)
{
    for (TActorIterator<AALMNSYChapterDirector> It(World); It; ++It) return *It;
    return nullptr;
}
void AALMNSYChapterDirector::BeginPlay()
{
    Super::BeginPlay();
    Saved = Cast<UALMNSYChapterSave>(UGameplayStatics::LoadGameFromSlot(SaveSlot(), 0));
    if (Saved && Saved->Version == 1)
    {
        bSword = Saved->bSword; bMemory = Saved->bMemory;
        for (const FName Id : Saved->Fallen) Fallen.Add(Id);
        for (TActorIterator<AALMNSYFighter> It(GetWorld()); It; ++It)
            if (It->bEnemy && Fallen.Contains(It->GuardId)) It->Destroy();
    }
    else Saved = nullptr;
    Say(FText::FromString(TEXT("ALMNSY\nThe house that remembers")), 5.f);
    if (auto* Ambience = LoadObject<USoundBase>(nullptr, TEXT("/Game/ALMNSY/Audio/S_HouseAmbience")))
        UGameplayStatics::SpawnSound2D(this, Ambience, .16f);
}
void AALMNSYChapterDirector::Tick(float Dt)
{
    Super::Tick(Dt);
    if (bComplete && FinishedAt >= 0 && GetWorld()->GetTimeSeconds() - FinishedAt > 2.f)
    {
        if (auto* PC = UGameplayStatics::GetPlayerController(this, 0))
            if (PC->PlayerCameraManager) PC->PlayerCameraManager->StartCameraFade(0, 1, 3, FLinearColor::Black, false, true);
        FinishedAt = -1.f;
    }
}
bool AALMNSYChapterDirector::Cleared(int32 Group) const
{
    if (Group < 0) return true;
    for (TActorIterator<AALMNSYFighter> It(GetWorld()); It; ++It)
        if (It->bEnemy && It->Encounter <= Group && !It->bDead && !Fallen.Contains(It->GuardId)) return false;
    return true;
}
void AALMNSYChapterDirector::GuardFell(FName Id)
{
    Fallen.Add(Id);
    if (Cleared(2)) Say(FText::FromString(TEXT("At last, the house is quiet.")));
    else if (Cleared(1)) Say(FText::FromString(TEXT("A lamp still burns beyond the passage.")));
    if (auto* P = Cast<AALMNSYFighter>(UGameplayStatics::GetPlayerPawn(this, 0)))
        P->Health = FMath::Min(P->MaxHealth, P->Health + 12.f);
}
void AALMNSYChapterDirector::Say(const FText& Text, float Seconds)
{ Subtitle = Text; SubtitleUntil = GetWorld()->GetTimeSeconds() + Seconds; }
void AALMNSYChapterDirector::Checkpoint(const FTransform& Transform)
{
    auto* Snapshot = Cast<UALMNSYChapterSave>(UGameplayStatics::CreateSaveGameObject(UALMNSYChapterSave::StaticClass()));
    Snapshot->Respawn = Transform; Snapshot->bSword = bSword; Snapshot->bMemory = bMemory;
    Snapshot->Fallen = Fallen.Array();
    if (UGameplayStatics::SaveGameToSlot(Snapshot, SaveSlot(), 0)) Saved = Snapshot;
    else Say(FText::FromString(TEXT("Checkpoint could not be saved. Check available disk space.")), 7.f);
}
void AALMNSYChapterDirector::RestorePlayer()
{
    if (auto* Player = Cast<AALMNSYFighter>(UGameplayStatics::GetPlayerPawn(this, 0)))
    {
        if (Saved) Player->Restore(Saved->Respawn, bSword);
        else Checkpoint(Player->GetActorTransform());
    }
}
void AALMNSYChapterDirector::RestartCheckpoint()
{
    UGameplayStatics::SetGamePaused(this, false);
    UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
}
void AALMNSYChapterDirector::NewChapter()
{ UGameplayStatics::DeleteGameInSlot(SaveSlot(), 0); RestartCheckpoint(); }
void AALMNSYChapterDirector::Finish()
{
    if (bComplete || !bSword || !bMemory || !Cleared(2)) return;
    bComplete = true; FinishedAt = GetWorld()->GetTimeSeconds();
    Say(FText::FromString(TEXT("Somewhere, a page turns.")), 5.f);
    if (auto* P = Cast<AALMNSYFighter>(UGameplayStatics::GetPlayerPawn(this, 0)))
    { P->GetCharacterMovement()->StopMovementImmediately(); P->GetCharacterMovement()->DisableMovement(); }
}
AALMNSYInteraction* AALMNSYChapterDirector::NearestInteraction() const
{
    auto* P = UGameplayStatics::GetPlayerPawn(this, 0);
    if (!P) return nullptr;
    AALMNSYInteraction* Best = nullptr; float BestDistance = 260.f;
    for (TActorIterator<AALMNSYInteraction> It(GetWorld()); It; ++It)
    {
        const float Distance = FVector::Dist(P->GetActorLocation(), It->GetActorLocation() + FVector(0, 0, 85));
        if (Distance >= BestDistance) continue;
        FCollisionQueryParams Q(SCENE_QUERY_STAT(ALMNSYInteraction), false, P);
        Q.AddIgnoredActor(*It);
        FHitResult Hit;
        if (GetWorld()->LineTraceSingleByChannel(Hit, P->GetActorLocation(), It->GetActorLocation() + FVector(0, 0, 120), ECC_Visibility, Q)) continue;
        BestDistance = Distance; Best = *It;
    }
    return Best;
}
FText AALMNSYChapterDirector::Objective() const
{
    if (bComplete) return FText::FromString(TEXT("CHAPTER I · COMPLETE"));
    if (!bSword) return FText::FromString(TEXT("Follow the lamps. Find the figure in the ruined chamber."));
    if (!Cleared(0)) return FText::FromString(TEXT("Pass the forgotten guard."));
    if (!Cleared(1)) return FText::FromString(TEXT("Cross the inner chambers."));
    if (!Cleared(2)) return FText::FromString(TEXT("Remember at the lamp. Enter the ceremonial hall."));
    if (!bMemory) return FText::FromString(TEXT("Find what was left in the quiet study."));
    return FText::FromString(TEXT("Approach the story gate."));
}

AALMNSYInteraction::AALMNSYInteraction()
{
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Pedestal = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Pedestal"));
    Pedestal->SetupAttachment(RootComponent);
    Pedestal->SetCollisionProfileName(TEXT("BlockAll"));
    Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("MemoryGlow"));
    Glow->SetupAttachment(RootComponent); Glow->SetRelativeLocation(FVector(0, 0, 150));
    Glow->SetIntensity(350.f); Glow->SetAttenuationRadius(480.f);
    Glow->SetLightColor(FLinearColor(.35f, .65f, 1.f)); Glow->SetCastShadows(false);
}
void AALMNSYInteraction::Use(AALMNSYFighter* Player)
{
    auto* D = AALMNSYChapterDirector::Find(GetWorld());
    if (!D || !Player || D->bComplete) return;
    if (!D->Cleared(RequiredEncounter))
    { D->Say(FText::FromString(TEXT("The memory cannot settle while the guards remain."))); return; }
    if (Kind == "Story")
    {
        if (D->bSword) { D->Say(FText::FromString(TEXT("The figure says nothing more."))); return; }
        D->Say(FText::FromString(TEXT("لقد كبرت\nYou have grown.")), 6.f);
        D->bSword = true; Player->Equip();
        D->Checkpoint(FTransform(FRotator::ZeroRotator, RespawnLocation));
    }
    else if (Kind == "Shrine")
    {
        Player->Health = Player->MaxHealth;
        D->Say(FText::FromString(TEXT("Memory held. Your strength returns.")));
        D->Checkpoint(FTransform(FRotator::ZeroRotator, RespawnLocation));
    }
    else if (Kind == "Memory")
    {
        D->bMemory = true;
        D->Say(FText::FromString(TEXT("I used to leave it in this chair…")), 5.f);
        D->Checkpoint(FTransform(FRotator::ZeroRotator, RespawnLocation));
    }
    else if (Kind == "Fragment") D->Say(FText::FromString(TEXT("A child's horse. One side worn smooth by a thumb.")), 5.f);
    else if (Kind == "End")
    {
        if (!D->bMemory) D->Say(FText::FromString(TEXT("Something familiar waits in the study.")));
        else D->Finish();
    }
}

AALMNSYSeal::AALMNSYSeal()
{
    PrimaryActorTick.bCanEverTick = true;
    Door = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PhysicalDoor"));
    RootComponent = Door;
    Door->SetMobility(EComponentMobility::Movable);
    Door->SetCollisionProfileName(TEXT("BlockAll"));
    // Bounds stay traversable for AI; the physical panel blocks movement until lifted.
    Door->SetCanEverAffectNavigation(false);
}
void AALMNSYSeal::BeginPlay() { Super::BeginPlay(); Closed = GetActorLocation(); }
void AALMNSYSeal::Tick(float Dt)
{
    Super::Tick(Dt);
    auto* D = AALMNSYChapterDirector::Find(GetWorld());
    if (!D) return;
    const bool Open = D->Cleared(RequiredEncounter) && (!bRequiresSword || D->bSword) && (!bRequiresMemory || D->bMemory);
    OpenAlpha = FMath::FInterpConstantTo(OpenAlpha, Open ? 1.f : 0.f, Dt, .55f);
    SetActorLocation(Closed + FVector(0, 0, 780.f * OpenAlpha));
    Door->SetCollisionEnabled(OpenAlpha > .95f ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics);
}

AALMNSYChapterGameMode::AALMNSYChapterGameMode()
{
    DefaultPawnClass = AALMNSYFighter::StaticClass();
    PlayerControllerClass = AALMNSYChapterController::StaticClass();
}
void AALMNSYChapterGameMode::StartPlay()
{
    Super::StartPlay();
    if (auto* D = AALMNSYChapterDirector::Find(GetWorld())) D->RestorePlayer();
}
