#pragma once

#include "CoreMinimal.h"
#include "ALMNSY_Level01Character.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SaveGame.h"
#include "Blueprint/UserWidget.h"
#include "ALMNSYChapter.generated.h"

class UAnimSequence;
class UBlendSpace;
class UStaticMeshComponent;
class UPointLightComponent;
class UTextBlock;
class UProgressBar;
class USoundBase;

/** The only persistent state; a checkpoint is an atomic snapshot of progress. */
UCLASS()
class ALMNSY_LEVEL01_API UALMNSYChapterSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(SaveGame) int32 Version = 1;
    UPROPERTY(SaveGame) FTransform Respawn;
    UPROPERTY(SaveGame) bool bSword = false;
    UPROPERTY(SaveGame) bool bMemory = false;
    UPROPERTY(SaveGame) TArray<FName> Fallen;
};

/** Same Manny shell for player and guards. No dependency on template combat BPs. */
UCLASS()
class ALMNSY_LEVEL01_API AALMNSYFighter : public AALMNSY_Level01Character
{
    GENERATED_BODY()
public:
    AALMNSYFighter();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* Instigator, AActor* Causer) override;
    virtual void FellOutOfWorld(const UDamageType& DamageType) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") bool bEnemy = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") bool bHeavy = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") bool bStoryCharacter = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") int32 Encounter = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") FName GuardId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") float MaxHealth = 120.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") float Health = 120.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") bool bArmed = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") bool bDead = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") bool bAttacking = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") TObjectPtr<UStaticMeshComponent> Sword;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") TObjectPtr<UPointLightComponent> TellLight;
    UPROPERTY(EditDefaultsOnly, Category="Animation") TObjectPtr<UBlendSpace> Locomotion;
    UPROPERTY(EditDefaultsOnly, Category="Animation") TArray<TObjectPtr<UAnimSequence>> Attacks;
    UPROPERTY(EditDefaultsOnly, Category="Animation") TObjectPtr<UAnimSequence> HitAnimation;
    UPROPERTY(EditDefaultsOnly, Category="Animation") TObjectPtr<UAnimSequence> DeathAnimation;
    UPROPERTY(EditDefaultsOnly, Category="Animation") TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditDefaultsOnly, Category="Animation") TObjectPtr<UAnimSequence> FallAnimation;
    void Equip();
    void Restore(const FTransform& Transform, bool Armed);
    void Attack();
    void Evade();
    void Interact();
    void SprintOn();
    void SprintOff();
private:
    void StartAttack();
    void TraceAttack();
    void AnimateLocomotion();
    void Think(float Now);
    void Die();
    float AttackStarted = -100.f;
    float AttackLength = .8f;
    float RecoverAt = 0.f;
    float InvulnerableUntil = 0.f;
    float NextThink = 0.f;
    float NextAttack = 0.f;
    float EvadeReady = 0.f;
    float LastStep = 0.f;
    float HitFlashUntil = 0.f;
    int32 Combo = 0;
    bool bQueued = false;
    bool bAlert = false;
    bool bMovingAnimation = false;
    bool bAirAnimation = false;
    FVector Home;
    TSet<TWeakObjectPtr<AActor>> Struck;
    UPROPERTY() TObjectPtr<USoundBase> SwingSound;
    UPROPERTY() TObjectPtr<USoundBase> HitSound;
    UPROPERTY() TObjectPtr<USoundBase> StepSound;
};

/** Placed, editable story/shrine/relic interactions, with proximity + LOS checks. */
UCLASS()
class ALMNSY_LEVEL01_API AALMNSYInteraction : public AActor
{
    GENERATED_BODY()
public:
    AALMNSYInteraction();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") FName Kind = "Shrine";
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") FText Prompt;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") int32 RequiredEncounter = -1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") FVector RespawnLocation;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") TObjectPtr<UStaticMeshComponent> Pedestal;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") TObjectPtr<UPointLightComponent> Glow;
    void Use(AALMNSYFighter* Player);
};

/** A visible physical seal; lifts only when its explicit progression rule is met. */
UCLASS()
class ALMNSY_LEVEL01_API AALMNSYSeal : public AActor
{
    GENERATED_BODY()
public:
    AALMNSYSeal();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") int32 RequiredEncounter = -1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") bool bRequiresSword = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Chapter") bool bRequiresMemory = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") TObjectPtr<UStaticMeshComponent> Door;
private:
    FVector Closed;
    float OpenAlpha = 0.f;
};

UCLASS()
class ALMNSY_LEVEL01_API AALMNSYChapterDirector : public AActor
{
    GENERATED_BODY()
public:
    AALMNSYChapterDirector();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    static AALMNSYChapterDirector* Find(const UWorld* World);
    static FString SaveSlot();
    bool Cleared(int32 Group) const;
    void GuardFell(FName Id);
    void Checkpoint(const FTransform& Transform);
    void RestorePlayer();
    void RestartCheckpoint();
    void NewChapter();
    void Finish();
    void Say(const FText& Text, float Seconds = 4.f);
    AALMNSYInteraction* NearestInteraction() const;
    FText Objective() const;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") bool bSword = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") bool bMemory = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Chapter") bool bComplete = false;
    FText Subtitle;
    float SubtitleUntil = 0.f;
    TSet<FName> Fallen;
    UPROPERTY() TObjectPtr<UALMNSYChapterSave> Saved;
private:
    float FinishedAt = -1.f;
};

/** Native UMG layout keeps Arabic text shaping and avoids debug-only HUD output. */
UCLASS()
class ALMNSY_LEVEL01_API UALMNSYChapterHUD : public UUserWidget
{
    GENERATED_BODY()
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<UTextBlock> ObjectiveText;
    UPROPERTY() TObjectPtr<UTextBlock> SubtitleText;
    UPROPERTY() TObjectPtr<UTextBlock> PromptText;
    UPROPERTY() TObjectPtr<UTextBlock> StateText;
    UPROPERTY() TObjectPtr<UProgressBar> HealthBar;
};

UCLASS()
class ALMNSY_LEVEL01_API AALMNSYChapterController : public APlayerController
{
    GENERATED_BODY()
protected:
    virtual void BeginPlay() override;
    virtual void SetupInputComponent() override;
private:
    void TogglePause();
    void NewChapter();
    void RestartCheckpoint();
    UPROPERTY() TObjectPtr<UALMNSYChapterHUD> ChapterHUD;
};

UCLASS()
class ALMNSY_LEVEL01_API AALMNSYChapterGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AALMNSYChapterGameMode();
    virtual void StartPlay() override;
};
