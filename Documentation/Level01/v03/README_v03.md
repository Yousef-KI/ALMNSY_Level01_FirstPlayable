# ALMNSY v03 refinement implementation

Implemented against **639c17d1811b0ea7a869c906fa05bfeeb4901b00** in
`Yousef-KI/ALMNSY_Level01_FirstPlayable`. This is a refinement of the existing
chapter, with the same route, story restrictions, encounter IDs and progression.
The user reports that the base v02 compiles, generates and plays in UE 5.8.
**v03 has not been compiled, generated, rendered or played in Unreal here.**

## Generate and open v03

Apply the supplied patch using `APPLY_CHANGES.txt`, close Unreal Editor, and run
from the project directory:

```powershell
.\Scripts\BuildAndOpen_v03.ps1
```

For an installation outside the detected locations:

```powershell
.\Scripts\BuildAndOpen_v03.ps1 -EngineRoot "D:\Epic Games\UE_5.8"
```

This builds `ALMNSY_Level01Editor` and opens Unreal with the v03 Python builder.
Allow navigation and shaders to finish. Use **Play > Selected Viewport**, with
**Default Player Start**. Alternatively, after a successful C++ build, save current
editor work and execute `Scripts/Build_ALMNSY_v03.py` through Tools > Execute Python
Script.

New map:
`/Game/ALMNSY/Levels/Level01/ALMNSY_Level01_FirstPlayable_v03`

New generated asset root: `/Game/ALMNSY/Versions/v03`.
Generation result: `Saved/ALMNSY/Build_v03.json`.
The patch contains source and assembly, not a pre-generated `.umap` or packaged
executable. No additional plugins, paid assets, Blender or Python packages are
needed to run the editor builder.

## Preservation and recovery

Existing `Content/`, `Config/` and `SourceArt/Level01/` files have no changes from
the exact base. Startup-map settings remain as supplied; v03 must be opened
explicitly. The v03 builder refuses dirty editor packages and opens an existing
v03 map without regenerating it. New assets use a separate namespace. v03 saves
to `ALMNSY_Level01_v03_Checkpoint`; the old default save name remains unchanged.

Shared source changes are limited to virtual extension hooks, an optional builder
fighter class, per-director save namespace, v03-aware HUD hints and the built-in
AnimGraphRuntime module dependency. Original fighter behavior remains in its
original class; refined behavior is in a derived v03 class. Shared code still
requires compilation and a v02 regression playtest. File preservation alone does
not prove runtime compatibility.

If generation stops, retain the log and partial v03 assets for diagnosis. The
builder deliberately does not repair an existing partial map automatically. Fix
the reported error, then preserve the partial map/assets under a different name
using Unreal's Content Browser and fix redirectors before a fresh generation.
Do not delete or rename v02. To return to the verified source baseline, use a clean
branch/worktree at the exact base; do not reset over uncommitted local work.

## Environment and presentation changes

- Rebuilt pointed arch has a 180 cm structural depth, closed legs/voussoirs,
  raised archivolts and a keystone. The outer trim reaches approximately 201 cm
  depth. It retains an open, walkable center with complex collision.
- Pillars have stepped bases/capitals, layered bands and carved projecting forms.
  Stone blocks, chairs and relief seals have actual thickness and beveled edges.
  Thin fabric is still intentional; architecture is not represented by cloth planes.
- Fixed the edge-on side-wall fabric/seal rotation. Added recessed gallery framing,
  lattice panels, paintings, cornices, ceiling ribs and suspended chandeliers.
- Corrected all 14 side chairs to face the table and added two inward-facing end
  chairs. The chair model has separate-looking solid posts, rails and seat parts.
  Dining cloth skirts, three deliberate carpet sections and bronze details improve
  the hall composition without filling its combat lanes.
- Nine surface families provide color, variable roughness, normals and height.
  Stone avoids repeating brick wallpaper; architectural world projections control
  stretching. Cloth has weave; carpets have geometric borders; wood has grain;
  bronze has patina. Variation is subtle and reusable, with an original painting.
- Reduced broad fill and warm-source strength, restricted shadow-casting point
  lights, set fixed exposure, and balanced cool moon/sky light with warm highlights.
  Fog, restrained bloom and small memory particles support the intended mood.
  These settings are art targets, not a verified rendered result.
- Final gate now frames layered domes, towers, distant ridges and sparse lights,
  with localized wind. The vista is scenery; it adds no new route or lore reveal.
- Recorded assembly contains 2,168 environment instances, 60 environment lights
  and 31 physics props. These counts do not establish a frame-rate result.

## Combat and animation

Manny remains the temporary player. The three sword actions are an authored
kinematic forehand, reverse cut and overhead cut, driven by a persistent native
animation proxy and analytic arm IK. They do not play the old unarmed attack clips.
Locomotion continues underneath with smoothly blended arm/torso poses. Existing
hit, fall and death sequences blend through the same proxy; sequence changes use
a short transition. The sword attaches to the configurable right-hand bone.

This is procedural first-pass sword choreography, **not three imported or baked
`AN_` sword animation assets**. Grip, elbow shape, twist bones and foot planting
still need evaluation on the actual Manny skeleton. Bone mappings and pose scale
are editable for future replacement; this is not a general retargeting system.

| Rule | v03 implementation |
| --- | --- |
| Three swing durations | 0.75 / 0.78 / 0.95 seconds |
| Damage interval | 28–58% of the current swing |
| Attack queue | Up to two additional inputs, accepted at 8–90% |
| Chain transition | 72%; stops after the third swing |
| Movement recovery | 60%; startup and most of the cut remain committed |
| Dodge cancel | From 55%; cuts off remaining attack damage immediately |
| Dodge buffer | 0.24 seconds; early input survives to a legal cancel point |
| Dodge | 360 cm over 0.52 seconds; 0.90 second cooldown |
| Dodge invulnerability | Elapsed 0.04–0.27 seconds only |
| Guard coverage | Forward cone, at most 60 degrees from facing |
| Normal block | 20% damage passes through |
| Parry | First 0.16 seconds of a guard press; 0.55 second rearm cooldown |

The 55% dodge threshold is near the end of the damaging cut, slightly before the
58% damage-window end. Cancelling gives up that final damage interval. This is
intentional; movement returns at 60% if the attack continues. A buffered dodge
uses recent directional input or moves backward if there is none. Capsule sweeps
stop it at solid collision; this is a grounded quickstep, not a root-motion roll.
The animation lowers the hips and solves the legs toward their animated foot
positions during the quickstep.

Blade sweeps sample the visible blade's current and previous base/middle/tip,
restrict damage to the active interval, enforce one hit per target per swing and
check line of sight. Physics props receive impulses. Frame-crossing windows are
handled so a long frame does not silently skip the complete damage interval;
mesh-pose/tick contact alignment remains an engine playtest item.

Guard must be held. Parry consumes its opportunity once per press and briefly
staggers the attacking guard; rear attacks bypass frontal defense. Holding guard
can transition out of late attack recovery at the same cancel threshold. There is
no stamina, lock-on, heavy player attack or advanced guard-break system.

Enemies keep the original placed encounters. Their tell/recovery is slower than
the player's, heavy attacks are slower again, and at most two guards in a group
commit simultaneously. Hits add short sound, particles and a small camera pulse.
No global hit-stop was added. Death marks a guard dead before updating chapter
progress, plays its death sequence, holds the corpse, then uses a masked memory
dissolve after 4.5 seconds and removes it at 7 seconds. Player death still reloads
the latest checkpoint through the existing director.

## Controls

| Action | Keyboard/mouse | Gamepad |
| --- | --- | --- |
| Move / look | WASD / mouse | Left / right stick |
| Jump | Space | A / bottom face button |
| Light attack / queue | Left mouse | Right bumper |
| Guard / timed parry | Hold / tap right mouse | Hold / tap left bumper |
| Dodge | Left Ctrl | B / right face button |
| Sprint | Hold Left Shift | No binding in this pass |
| Interact | E | X / left face button |

Controller naming follows the existing project's Xbox bindings. In-game hints
switch for v03; unchanged v02 fighters retain the original hints.

## Static verification completed

Run `python Scripts/Level01/validate_v03.py` from the repository root to reproduce
the checks (Python, Pillow and g++ are needed for this optional source validator).
The editor builder itself does not need these validation dependencies.

- Python syntax; `git diff --check`; generated-header order; source/path references;
  retained UE 5.8 compatibility fixes and protected-path comparison to exact base.
- All 24 mesh sources checked for finite coordinates, valid indices/UVs,
  nondegenerate triangles and positive solid volume. Thickness bounds checked.
  This is not a complete manifold, shading or Chaos collision proof.
- Surface images decoded to detect truncated data; committed files are complete.
- Static assembly reproduced with a recording backend. A conservative 50 cm grid
  around standing-height obstacles reaches 25,482 cells and 20 guard/checkpoint/
  interaction approach destinations. All 16 dining chairs face inward.
  Unlocked doorway geometry is tested; dynamic seals and Recast path following
  still require runtime validation.
- The actual engine-independent combat/choreography headers compile with g++
  warnings treated as errors. Boundary and frame-step assertions pass at simulated
  12, 30, 60 and 144 FPS, including buffered dodge/cancel and frontal defense.
  This does **not** compile the Unreal classes, UHT output or animation proxy.

See `StaticValidation.json` and `SwordTrajectories.csv`. Optional source previews
(`SourceMeshKit.png`, `SourceSurfaces.png`, `SourceSwordArcs.png`) are generated
outside Unreal and are explicitly not gameplay screenshots. Reproduce them with
`Scripts/Level01/preview_v03.py` (NumPy, Pillow and Matplotlib).

## Required local UE 5.8 tests and known limitations

1. Build the Editor target/UHT, then generate v03. Inspect Python import/material
   graph calls, custom shader compilation and `Build_v03.json`. The native anim
   proxy and Unreal Python material APIs have been source-reviewed but are unrun.
2. Open v02 once after compilation: verify its movement, original combat, save and
   map assets remain usable. Open v03 separately and verify save isolation.
3. Play v03 from an unarmed start through sword acquisition, every encounter,
   shrine, study clue and final gate. No new exposition or route should appear.
4. At 30 and 60 FPS, inspect the three visible cuts, hand grip, active-contact
   timing, combo transitions, hit reactions and jump/fall/landing blends. Test
   dodge buffering just before the threshold, wall sweeps, recovery movement and
   repeated inputs. Tune the procedural poses after seeing them in-engine.
5. Attack guarding player from front, side and behind; test early, timely, late
   and held parry inputs. Verify no repeated parry from one held press and no
   protection from rear attacks. Test mixed light/heavy groups.
6. Kill guards, verify seals open immediately despite delayed corpse removal,
   and die before/after each checkpoint. Relaunch and verify saved progress.
7. Inspect navmesh through arches and around the table, push several tabletop
   props, check camera clearance, foot placement and collision at all doorways.
8. Judge exposure and readable silhouettes in the hall/side rooms/end vista at
   the target resolution. Measure CPU/GPU time on the target PC; reduce shadows,
   fog or material cost if needed. No FPS, visual-reference fidelity or 25–40
   minute playtime claim is made by this delivery.
9. Make an actual packaged build after the preceding checks pass. Packaging and
   cook-time inclusion of dynamically referenced assets have not been tested.

Known first-pass limits include synthetic audio, procedural rather than scanned
surfaces, simplified painting/ornament, kinematic sword poses and simple collision
for props. There are no authored breakable-object fracture assets, final hero,
cinematics or custom voice recordings. No runtime bug-free claim is possible
without the local tests above.

## Changed-file guide

- `Scripts/Build_ALMNSY_v03.py`, `BuildAndOpen_v03.ps1`: isolated build/assembly.
- `Scripts/Level01/refinement_*.py`: geometry, material/audio sources and dressing.
- `SourceArt/Level01_v03/`: new OBJ/JSON, PNG and WAV sources plus provenance.
- `Source/ALMNSY_Level01/Chapter/V03/`: refined fighter, rule/pose headers, native
  animation proxy and lightweight memory effect.
- `ALMNSYChapter.h`, `ALMNSYProgression.cpp`, `ALMNSYChapterUI.cpp`, module Build.cs
  and baseline builder: the bounded shared hooks described above.
- `Scripts/Level01/validate_v03.py`, `test_combat_v03.cpp`, `preview_v03.py` and this
  documentation directory: reproducible checks and source previews.

The delivery's `CHANGED_FILES.txt` gives the exact per-file list. `FINAL_COMMIT.txt`
and `PatchVerification.json` identify the final local commit and clean application
test. No GitHub push was attempted for this refinement package.
