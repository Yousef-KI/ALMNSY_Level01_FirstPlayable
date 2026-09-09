#include "Chapter/V03/ALMNSYFighterV03.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

AALMNSYMemoryEffect::AALMNSYMemoryEffect()
{
    PrimaryActorTick.bCanEverTick=true;
    Fragments=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("MemoryFragments"));RootComponent=Fragments;
    Fragments->SetCollisionEnabled(ECollisionEnabled::NoCollision);Fragments->SetCanEverAffectNavigation(false);
    Fragments->SetCastShadow(false);Fragments->SetMobility(EComponentMobility::Movable);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Cube"));Fragments->SetStaticMesh(Shape.Object);
}
void AALMNSYMemoryEffect::BeginPlay()
{
    Super::BeginPlay();
    if(auto* Mat=LoadObject<UMaterialInterface>(nullptr,bWarm?TEXT("/Game/ALMNSY/Versions/v03/Materials/MI_Flame"):TEXT("/Game/ALMNSY/Versions/v03/Materials/MI_Memory")))Fragments->SetMaterial(0,Mat);
    for(int32 I=0;I<12;++I)Fragments->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.008f)));
    if(!bAmbient)SetLifeSpan(.8f);
}
void AALMNSYMemoryEffect::Tick(float Dt)
{
    Super::Tick(Dt);Age+=Dt;
    for(int32 I=0;I<12;++I)
    {
        const float A=I*2.39996f;
        const float T=bAmbient?FMath::Fmod(Age*.16f+I/12.f,1.f):Age/.8f;
        const float Radius=bAmbient?22.f:(30.f+I*3)*T;
        FVector P(FMath::Cos(A+Age*.15f)*Radius,FMath::Sin(A+Age*.15f)*Radius,bAmbient?T*85.f:75.f*T-60.f*T*T);
        const float Size=bAmbient?.007f*FMath::Sin(PI*T):.014f*(1-T);
        Fragments->UpdateInstanceTransform(I,FTransform(FRotator(Age*30,I*19,0),P,FVector(FMath::Max(.0001f,Size))),false,I==11,false);
    }
}
