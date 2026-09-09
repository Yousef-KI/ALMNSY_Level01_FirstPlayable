#include "Chapter/ALMNSYChapter.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Components/InputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "InputMappingContext.h"
#include "Kismet/GameplayStatics.h"

TSharedRef<SWidget> UALMNSYChapterHUD::RebuildWidget()
{
    if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this, TEXT("ChapterWidgetTree"));
    UCanvasPanel* Root = WidgetTree->ConstructWidget<UCanvasPanel>();
    WidgetTree->RootWidget = Root;
    auto Text = [&](const TCHAR* Label, FVector2D Position, FVector2D Size, int32 FontSize, FVector2D Anchor)
    {
        auto* T = WidgetTree->ConstructWidget<UTextBlock>();
        T->SetText(FText::FromString(Label)); T->SetAutoWrapText(true);
        T->SetColorAndOpacity(FSlateColor(FLinearColor(.88f, .81f, .65f)));
        T->SetShadowColorAndOpacity(FLinearColor(0, 0, 0, .95f)); T->SetShadowOffset(FVector2D(1, 2));
        FSlateFontInfo Font = T->GetFont(); Font.Size = FontSize; T->SetFont(Font);
        auto* Slot = Root->AddChildToCanvas(T);
        Slot->SetAnchors(FAnchors(Anchor.X, Anchor.Y)); Slot->SetAlignment(Anchor);
        Slot->SetPosition(Position); Slot->SetSize(Size);
        return T;
    };
    Text(TEXT("ALMNSY  /  CHAPTER I"), FVector2D(40, 28), FVector2D(510, 35), 22, FVector2D::ZeroVector);
    ObjectiveText = Text(TEXT(""), FVector2D(40, 108), FVector2D(560, 60), 17, FVector2D::ZeroVector);
    HealthBar = WidgetTree->ConstructWidget<UProgressBar>();
    HealthBar->SetFillColorAndOpacity(FLinearColor(.5f, .095f, .075f));
    auto* BarSlot = Root->AddChildToCanvas(HealthBar);
    BarSlot->SetPosition(FVector2D(40, 78)); BarSlot->SetSize(FVector2D(240, 9));
    SubtitleText = Text(TEXT(""), FVector2D(0, -125), FVector2D(760, 110), 25, FVector2D(.5f, 1.f));
    SubtitleText->SetJustification(ETextJustify::Center);
    PromptText = Text(TEXT(""), FVector2D(0, -80), FVector2D(750, 36), 19, FVector2D(.5f, 1.f));
    PromptText->SetJustification(ETextJustify::Center);
    StateText = Text(TEXT(""), FVector2D::ZeroVector, FVector2D(850, 200), 30, FVector2D(.5f, .5f));
    StateText->SetJustification(ETextJustify::Center);
    Text(TEXT("WASD move · Mouse look · Space jump · Shift run · LMB attack · Ctrl evade · E interact · Esc pause"),
        FVector2D(0, -20), FVector2D(1080, 28), 13, FVector2D(.5f, 1.f))->SetJustification(ETextJustify::Center);
    SetVisibility(ESlateVisibility::HitTestInvisible);
    return Super::RebuildWidget();
}
void UALMNSYChapterHUD::NativeTick(const FGeometry& Geometry, float Dt)
{
    Super::NativeTick(Geometry, Dt);
    auto* D = AALMNSYChapterDirector::Find(GetWorld());
    auto* P = Cast<AALMNSYFighter>(GetOwningPlayerPawn());
    if (!D || !P || !HealthBar) return;
    HealthBar->SetPercent(P->MaxHealth > 0 ? P->Health / P->MaxHealth : 0);
    ObjectiveText->SetText(D->Objective());
    SubtitleText->SetText(GetWorld()->GetTimeSeconds() < D->SubtitleUntil ? D->Subtitle : FText::GetEmpty());
    auto* I = D->NearestInteraction();
    PromptText->SetText(I && !P->bDead && !D->bComplete ? FText::FromString(TEXT("[E / X]  ") + I->Prompt.ToString()) : FText::GetEmpty());
    StateText->SetText(D->bComplete ? FText::FromString(TEXT("CHAPTER I\nTHE HOUSE REMEMBERS\n\nN — begin again")) :
        P->bDead ? FText::FromString(TEXT("A MEMORY LOST")) :
        UGameplayStatics::IsGamePaused(this) ? FText::FromString(TEXT("PAUSED\nEsc — continue · R — checkpoint\nN — new chapter (resets save)")) : FText::GetEmpty());
}

void AALMNSYChapterController::BeginPlay()
{
    Super::BeginPlay();
    if (!IsLocalController()) return;
    SetInputMode(FInputModeGameOnly());
    if (auto* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
    {
        for (const TCHAR* Path : {TEXT("/Game/Input/IMC_Default"), TEXT("/Game/Input/IMC_MouseLook")})
            if (auto* Context = LoadObject<UInputMappingContext>(nullptr, Path)) Subsystem->AddMappingContext(Context, 0);
    }
    ChapterHUD = CreateWidget<UALMNSYChapterHUD>(this, UALMNSYChapterHUD::StaticClass());
    if (ChapterHUD) ChapterHUD->AddToViewport();
}
void AALMNSYChapterController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::Escape, IE_Pressed, this, &AALMNSYChapterController::TogglePause).bExecuteWhenPaused = true;
    InputComponent->BindKey(EKeys::Gamepad_Special_Right, IE_Pressed, this, &AALMNSYChapterController::TogglePause).bExecuteWhenPaused = true;
    InputComponent->BindKey(EKeys::N, IE_Pressed, this, &AALMNSYChapterController::NewChapter).bExecuteWhenPaused = true;
    InputComponent->BindKey(EKeys::R, IE_Pressed, this, &AALMNSYChapterController::RestartCheckpoint).bExecuteWhenPaused = true;
}
void AALMNSYChapterController::TogglePause() { SetPause(!IsPaused()); }
void AALMNSYChapterController::NewChapter()
{
    if (auto* D = AALMNSYChapterDirector::Find(GetWorld()); D && (D->bComplete || IsPaused())) D->NewChapter();
}
void AALMNSYChapterController::RestartCheckpoint()
{
    if (IsPaused()) if (auto* D = AALMNSYChapterDirector::Find(GetWorld())) D->RestartCheckpoint();
}
