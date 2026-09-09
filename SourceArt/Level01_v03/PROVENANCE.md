# v03 source art

These files were generated specifically for this refinement in this repository.
The supplied images informed composition, palette and architectural depth; they
were not traced into meshes, embedded as textures or converted into reference-sheet
geometry. No marketplace downloads, external ALMNSY projects or paid assets are used.

- `Meshes/*.json`: editable mesh data consumed by the project's existing Unreal
  editor mesh importer. `Meshes/*.obj`: matching portable geometry/UV exports.
- `Textures/*.png`: nine 1024 px surface families, each with BaseColor, ORM
  (occlusion/roughness/metallic), Normal and Height; one original procedural painting.
  BaseColor is sRGB; other maps are linear. Architecture uses world projections
  and a height-gradient normal; smaller objects use their mesh UVs.
- `Audio/*.wav`: seven synthesized first-pass effects/ambience, with no recorded
  speech or sampled commercial audio.

Reproduction, from the repository root:

```text
python Scripts/Level01/refinement_geometry.py
python Scripts/Level01/refinement_surfaces.py
```

Geometry regeneration uses the standard library and reuses the local baseline
generator for retained props. Surface/audio regeneration additionally needs NumPy
and Pillow. Unreal generation uses the committed files and needs neither package.
Regeneration writes only `SourceArt/Level01_v03`; do not run it over hand-edited
v03 sources without committing those edits first.

Manny, locomotion and the existing hit/fall/death animation resources remain the
supplied project's Epic template assets, subject to their existing terms. Their
files are unchanged. No custom hero, Blender source, FBX or authored sword animation
sequence is claimed. Sword motion is implemented in `SwordMotionV03.h` and the
native animation layer. This is replaceable first-pass choreography.
