#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "ALMNSYEditorLibrary.generated.h"

class UStaticMesh;
class ANavMeshBoundsVolume;
class UMaterialInterface;

/** Editor-only asset authoring. Not linked into the packaged game. */
UCLASS()
class ALMNSYEDITORTOOLS_API UALMNSYEditorLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="ALMNSY|Build")
    static UStaticMesh* CreateMesh(const FString& PackagePath, const TArray<FVector>& Vertices,
        const TArray<int32>& Triangles, const TArray<FVector2D>& UVs, bool bComplexCollision);
    UFUNCTION(BlueprintCallable, Category="ALMNSY|Build")
    static ANavMeshBoundsVolume* AddNavigationBounds(FVector Location, FVector Extent);
    UFUNCTION(BlueprintCallable, Category="ALMNSY|Build")
    static void BuildNavigation();
    UFUNCTION(BlueprintCallable, Category="ALMNSY|Build")
    static AActor* CreateInstances(UStaticMesh* Mesh, UMaterialInterface* Material,
        const TArray<FTransform>& Transforms, bool bCollision, const FString& Label);
};
