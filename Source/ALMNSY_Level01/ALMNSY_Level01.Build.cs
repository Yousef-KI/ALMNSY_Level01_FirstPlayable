// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class ALMNSY_Level01 : ModuleRules
{
	public ALMNSY_Level01(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"ALMNSY_Level01",
			"ALMNSY_Level01/Variant_Platforming",
			"ALMNSY_Level01/Variant_Platforming/Animation",
			"ALMNSY_Level01/Variant_Combat",
			"ALMNSY_Level01/Variant_Combat/AI",
			"ALMNSY_Level01/Variant_Combat/Animation",
			"ALMNSY_Level01/Variant_Combat/Gameplay",
			"ALMNSY_Level01/Variant_Combat/Interfaces",
			"ALMNSY_Level01/Variant_Combat/UI",
			"ALMNSY_Level01/Variant_SideScrolling",
			"ALMNSY_Level01/Variant_SideScrolling/AI",
			"ALMNSY_Level01/Variant_SideScrolling/Gameplay",
			"ALMNSY_Level01/Variant_SideScrolling/Interfaces",
			"ALMNSY_Level01/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
