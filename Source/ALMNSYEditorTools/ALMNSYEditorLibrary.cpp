#include "ALMNSYEditorLibrary.h"
#include "Modules/ModuleManager.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Builders/CubeBuilder.h"
#include "Editor.h"
#include "Engine/Model.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSourceData.h"
#include "Engine/World.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "PhysicsEngine/BodySetup.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavigationSystem.h"
#include "Misc/PackageName.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, ALMNSYEditorTools)

UStaticMesh* UALMNSYEditorLibrary::CreateMesh(const FString& PackagePath, const TArray<FVector>& Vertices,
    const TArray<int32>& Triangles, const TArray<FVector2D>& UVs, bool bComplexCollision)
{
    // Never mutate a prior asset. Builder selects a fresh version namespace on every run.
    if (!PackagePath.StartsWith(TEXT("/Game/ALMNSY/")) || Vertices.Num() != UVs.Num() || Triangles.Num() % 3 != 0) return nullptr;
    const FString AssetName = FPackageName::GetLongPackageAssetName(PackagePath);
    if (LoadObject<UStaticMesh>(nullptr, *(PackagePath + TEXT(".") + AssetName))) return nullptr;
    for (int32 I : Triangles) if (!Vertices.IsValidIndex(I)) return nullptr;
    UPackage* Package = CreatePackage(*PackagePath);
    auto* Mesh = NewObject<UStaticMesh>(Package, *AssetName, RF_Public | RF_Standalone);
    FMeshDescription Description;
    FStaticMeshAttributes Attributes(Description);
    Attributes.Register();
    auto Positions = Attributes.GetVertexPositions();
    auto TexCoords = Attributes.GetVertexInstanceUVs();
    TexCoords.SetNumChannels(1);
    TArray<FVertexID> Ids;
    for (const FVector& V : Vertices)
    {
        FVertexID Id = Description.CreateVertex(); Ids.Add(Id); Positions[Id] = FVector3f(V);
    }
    const FPolygonGroupID Group = Description.CreatePolygonGroup();
    Attributes.GetPolygonGroupMaterialSlotNames()[Group] = TEXT("Surface");
    for (int32 T = 0; T < Triangles.Num(); T += 3)
    {
        TArray<FVertexInstanceID> Face;
        for (int32 Corner = 0; Corner < 3; ++Corner)
        {
            const int32 I = Triangles[T + Corner];
            const FVertexInstanceID Instance = Description.CreateVertexInstance(Ids[I]);
            TexCoords.Set(Instance, 0, FVector2f(UVs[I])); Face.Add(Instance);
        }
        Description.CreatePolygon(Group, Face);
    }
    auto& Source = Mesh->AddSourceModel();
    Source.BuildSettings.bRecomputeNormals = true;
    Source.BuildSettings.bRecomputeTangents = true;
    Source.BuildSettings.bGenerateLightmapUVs = false;
    Mesh->GetStaticMaterials().Add(FStaticMaterial(nullptr, TEXT("Surface")));
    Mesh->CreateMeshDescription(0, MoveTemp(Description));
    Mesh->CommitMeshDescription(0);
    Mesh->Build(false);
    Mesh->CreateBodySetup();
    auto* Body = Mesh->GetBodySetup();
    Body->CollisionTraceFlag = bComplexCollision ? CTF_UseComplexAsSimple : CTF_UseSimpleAndComplex;
    if (!bComplexCollision)
    {
        FKConvexElem Convex;
        Convex.VertexData = Vertices; Convex.UpdateElemBox();
        Body->AggGeom.ConvexElems.Add(Convex);
    }
    Body->InvalidatePhysicsData(); Body->CreatePhysicsMeshes();
    Mesh->PostEditChange(); Mesh->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Mesh);
    return Mesh;
}

ANavMeshBoundsVolume* UALMNSYEditorLibrary::AddNavigationBounds(FVector Location, FVector Extent)
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return nullptr;
    auto* Bounds = World->SpawnActor<ANavMeshBoundsVolume>();
    Bounds->Brush = NewObject<UModel>(Bounds, NAME_None, RF_Transactional);
    Bounds->Brush->Initialize(nullptr, true);
    auto* Builder = NewObject<UCubeBuilder>(Bounds);
    Builder->X = Extent.X * 2; Builder->Y = Extent.Y * 2; Builder->Z = Extent.Z * 2;
    Bounds->BrushBuilder = Builder;
    Builder->Build(World, Bounds);
    Bounds->SetActorLocation(Location);
    Bounds->SetActorLabel(TEXT("ALMNSY_ChapterNavigation"));
    Bounds->PostEditChange();
    if (auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World)) Nav->OnNavigationBoundsUpdated(Bounds);
    return Bounds;
}
void UALMNSYEditorLibrary::BuildNavigation()
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (auto* Nav = World ? FNavigationSystem::GetCurrent<UNavigationSystemV1>(World) : nullptr) Nav->Build();
}

AActor* UALMNSYEditorLibrary::CreateInstances(UStaticMesh* Mesh, UMaterialInterface* Material,
    const TArray<FTransform>& Transforms, bool bCollision, const FString& Label)
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World || !Mesh) return nullptr;
    AActor* Actor = World->SpawnActor<AActor>();
    auto* Instances = NewObject<UHierarchicalInstancedStaticMeshComponent>(Actor, TEXT("ArchitecturalInstances"), RF_Transactional);
    Actor->SetRootComponent(Instances); Actor->AddInstanceComponent(Instances);
    Instances->SetStaticMesh(Mesh); Instances->SetMaterial(0, Material);
    Instances->SetMobility(EComponentMobility::Static);
    Instances->SetCollisionEnabled(bCollision ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
    Instances->SetCollisionProfileName(bCollision ? TEXT("BlockAll") : TEXT("NoCollision"));
    Instances->SetCanEverAffectNavigation(bCollision);
    Instances->RegisterComponent();
    for (const FTransform& T : Transforms) Instances->AddInstance(T, true);
    Actor->SetActorLabel(Label); Actor->SetFolderPath(TEXT("ALMNSY/Architecture"));
    Actor->MarkPackageDirty();
    return Actor;
}
