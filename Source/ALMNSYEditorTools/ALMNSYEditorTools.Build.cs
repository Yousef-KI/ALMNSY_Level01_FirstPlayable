using UnrealBuildTool;

public class ALMNSYEditorTools : ModuleRules
{
    public ALMNSYEditorTools(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new [] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new [] {
            "UnrealEd", "MeshDescription", "StaticMeshDescription", "AssetRegistry", "NavigationSystem"
        });
    }
}
