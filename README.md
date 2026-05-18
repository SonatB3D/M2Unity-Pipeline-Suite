# M2Unity Pipeline Suite

**M2Unity Pipeline Suite** is a Maya-to-Unity asset preparation toolkit designed to help artists, technical artists, indie developers, and small production teams prepare cleaner static mesh assets before importing them into Unity.

The tool focuses on **preflight validation**, **safe cleanup**, **Unity-oriented naming**, **collider and trigger proxy preparation**, **FBX export support**, and **report-based quality control**. It is not only an FBX exporter. It is a production-minded helper that checks common asset issues earlier in the pipeline, before they become Unity import problems.

**Developer: Sonat Birdane**

---

## Presentation

The following images provide a visual overview of **M2Unity Pipeline Suite**, including its core workflow, documentation structure, feature set, and GitHub release presentation.

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-01.png" alt="M2Unity Pipeline Suite Presentation Slide 01" width="100%">
  <br>
  <sub>Slide 01 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-02.png" alt="M2Unity Pipeline Suite Presentation Slide 02" width="100%">
  <br>
  <sub>Slide 02 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-03.png" alt="M2Unity Pipeline Suite Presentation Slide 03" width="100%">
  <br>
  <sub>Slide 03 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-04.png" alt="M2Unity Pipeline Suite Presentation Slide 04" width="100%">
  <br>
  <sub>Slide 04 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-05.png" alt="M2Unity Pipeline Suite Presentation Slide 05" width="100%">
  <br>
  <sub>Slide 05 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-06.png" alt="M2Unity Pipeline Suite Presentation Slide 06" width="100%">
  <br>
  <sub>Slide 06 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-07.png" alt="M2Unity Pipeline Suite Presentation Slide 07" width="100%">
  <br>
  <sub>Slide 07 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-08.png" alt="M2Unity Pipeline Suite Presentation Slide 08" width="100%">
  <br>
  <sub>Slide 08 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-09.png" alt="M2Unity Pipeline Suite Presentation Slide 09" width="100%">
  <br>
  <sub>Slide 09 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-10.png" alt="M2Unity Pipeline Suite Presentation Slide 10" width="100%">
  <br>
  <sub>Slide 10 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-11.png" alt="M2Unity Pipeline Suite Presentation Slide 11" width="100%">
  <br>
  <sub>Slide 11 — 2000 x 1125 px</sub>
</p>

<p align="center">
  <img src="M2Unity_Pipeline_Suite_Presentation_imgs/slide-12.png" alt="M2Unity Pipeline Suite Presentation Slide 12" width="100%">
  <br>
  <sub>Slide 12 — 2000 x 1125 px</sub>
</p>

## What Is M2Unity Pipeline Suite?

M2Unity Pipeline Suite is a Maya utility created to improve the static mesh handoff process between **Autodesk Maya** and **Unity**.

In many game asset workflows, problems such as naming mistakes, unfrozen transforms, bad pivots, construction history, collider mismatch, incorrect proxy naming, material slot issues, or unclear export structure are discovered too late inside the engine. This tool moves many of those checks into Maya, where they can be reviewed and fixed before export.

The main goal is simple:

> Prepare assets more safely, more consistently, and more transparently before they reach Unity.

---

## Main Purpose

M2Unity Pipeline Suite helps with:

- Checking selected Maya meshes before Unity export
- Detecting common static mesh preparation issues
- Applying safer cleanup operations with backups
- Separating visible render meshes from collider and trigger proxy meshes
- Preparing Unity-friendly naming contracts
- Exporting FBX files with matched proxy objects
- Generating JSON and HTML reports for review
- Creating an optional Unity C# postprocessor helper
- Supporting a more repeatable Maya-to-Unity asset pipeline

---

## Key Features

### Static Mesh Preflight Validation

The tool analyzes selected Maya assets and checks for common production issues, including:

- Naming consistency
- Transform state
- Construction history
- Pivot position
- Grid alignment
- Mesh dimensions
- Geometry preparation concerns
- LOD naming structure
- Material slot organization
- UV and lightmap-related review points
- Socket and helper object organization

This helps users catch potential problems before the asset is exported and imported into Unity.

---

### Unity-Oriented Role Naming

M2Unity Pipeline Suite uses a clear role-based naming workflow:

```txt
Mesh_    = Visible render mesh
COL_     = Collider proxy mesh
TRG_     = Trigger proxy mesh

Example:

Mesh_Table
COL_Mesh_Table_01
TRG_Mesh_Table_Interaction

This makes the asset structure easier to read, easier to validate, and easier to process inside Unity.

Collider and Trigger Proxy Workflow

The tool supports Unity-friendly collider and trigger proxy preparation.

Collider proxy objects can be named with the COL_ prefix, while trigger proxy objects can be named with the TRG_ prefix. During export and Unity-side processing, these objects can be handled separately from the visible render mesh.

This workflow is useful for:

Static props
Environment assets
Interactive objects
Collision proxy preparation
Trigger volume preparation
Cleaner Unity import organization
Safe Fix Workflow

M2Unity Pipeline Suite includes conservative cleanup support through its Safe Fix workflow.

The tool is designed to help users fix common preparation issues while keeping the process more transparent. It encourages review and backup instead of blindly modifying production assets.

Safe Fix operations may help with issues such as:

Cleaning construction history
Preparing transforms
Improving naming consistency
Supporting cleaner mesh export preparation
Reducing repetitive manual cleanup work

Users should always review the results after using any automatic cleanup tool.

Preset-Based Validation

The tool includes workflow presets for different Unity asset preparation needs.

Available preset concepts include:

Unity Static Prop
Unity Environment Kit
Unity Mobile Optimized
Unity LOD / Prefab Ready
Unity Collider Strict

These presets help users start with practical validation settings depending on the type of asset they are preparing.

Rule Severity System

Validation rules can be treated with different severity levels:

Off
Warning
Blocking

This allows users to decide which issues should only be reviewed and which issues should stop the export process.

This is especially useful for teams or creators who want a stricter asset preparation workflow before publishing or integrating content into a Unity project.

M2Unity Score and Export Status

The tool can evaluate the current asset state and provide a clearer readiness result.

Possible export states include:

Ready
Warning
Blocked

This gives users a quick understanding of whether the selected asset is safe to export or still requires review.

Report Generation

M2Unity Pipeline Suite can generate review reports to make the export process more transparent.

Supported report outputs include:

M2Unity_Pipeline_Report.json
M2Unity_Pipeline_Report.html

These reports help document what was checked, what was found, and what may need attention before or after export.

Unity C# Postprocessor Helper

The tool can optionally generate a Unity-side C# helper script:

M2Unity_ModelPostprocessor.cs

This helper is designed to support Unity import behavior for exported assets that use the M2Unity naming workflow.

The generated helper can assist with:

Detecting COL_ collider proxy objects
Detecting TRG_ trigger proxy objects
Converting proxy objects into MeshCollider-based objects
Marking trigger proxies appropriately
Disabling proxy renderers during import

The generated script should be reviewed before use and placed inside a Unity Assets/Editor folder when needed.

Recommended Workflow

A typical workflow looks like this:

1. Select the asset or asset group in Maya
2. Run M2Unity Pipeline Suite
3. Analyze the selected meshes
4. Review warnings and blocking issues
5. Apply Safe Fix operations if needed
6. Assign or correct Mesh_ / COL_ / TRG_ roles
7. Revalidate the scene
8. Export FBX
9. Review the generated JSON / HTML report
10. Import into Unity
11. Optionally use the generated Unity C# postprocessor helper

This workflow is designed to reduce manual mistakes and make the asset handoff process more predictable.

Installation

The recommended installation method is to use the included Easy Installer inside Maya.

General installation flow:

1. Extract the package
2. Open Autodesk Maya
3. Open the Maya Script Editor
4. Run the Easy Installer script
5. Choose the install location when prompted
6. Launch the tool from the M2U_Tools shelf

After installation, users do not need to run the installer again during normal use. The tool can be opened from the M2U_Tools shelf.

A shelf repair or reinstall script may be included for cases where Maya preferences are reset or the shelf is manually removed.

Package Contents

Depending on the release package, the project may include:

Main Maya tool script
Launcher script
Easy installer script
Shelf repair script
Tool icon
README file
FUNCTIONS documentation
LICENCE file
Additional PDF or text documentation
Example reports or presentation images

The exact package structure may vary by release version.

Who Is This Tool For?

M2Unity Pipeline Suite is useful for:

Maya users preparing assets for Unity
Game artists
Technical artists
Indie developers
Environment artists
Asset store creators
Small production teams
Users who want cleaner FBX handoff workflows
Users who want report-based asset preparation checks

It is especially useful when working with repeated static mesh export tasks where consistency matters.

What This Tool Is Not

M2Unity Pipeline Suite is not a replacement for professional QA.

It does not guarantee that every asset will be perfect, optimized, or production-ready in every possible Unity project. It is a helper tool designed to support better preparation, faster review, and more consistent export behavior.

Users are responsible for reviewing their assets, checking the generated reports, testing exports, and confirming the final result inside Unity.

Safety Notes

Before using automatic cleanup or export operations:

Back up your Maya scene
Test the workflow on duplicate files first
Review all warnings and blocked checks
Inspect the exported FBX file
Review generated JSON and HTML reports
Review generated Unity C# scripts before using them in production
Confirm the final imported result inside Unity

This tool was developed by a single developer, so unexpected bugs or edge cases may exist. Use it carefully and always verify important production files before release or delivery.

Licence Summary

M2Unity Pipeline Suite may be used for personal, educational, portfolio, internal, and commercial production workflows, depending on the included licence terms.

The tool may not be resold, re-uploaded, redistributed, rebranded, bundled, or presented under false authorship without permission.

Please read the included LICENCE file before using, modifying, sharing, or distributing any part of the tool.

Suggested GitHub Tagline
A Maya-to-Unity preflight and export assistant for game-ready static mesh assets.
Project Status

This is an early public release of M2Unity Pipeline Suite.

The current version focuses on Maya-side static mesh preparation, validation, role naming, collider proxy workflow, reporting, and Unity handoff support.

Future development may expand the Unity-side companion workflow, prefab setup support, post-import validation, and additional production pipeline automation features.

Final Note

M2Unity Pipeline Suite was created to make the Maya-to-Unity static mesh workflow cleaner, safer, and easier to review.

It is designed to help users catch problems earlier, reduce repetitive manual work, and create a more organized bridge between Maya asset preparation and Unity project integration.

## Screenshots

The following screenshots show the main interface, validation workflow, collider proxy tools, export output, generated reports, and Unity-oriented asset preparation structure of **M2Unity Pipeline Suite**.

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity.png" alt="M2Unity Pipeline Suite Dashboard Screenshot" width="100%">
  <br>
  <sub>Dashboard / Wizard — 1217 x 866 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity2.png" alt="M2Unity Pipeline Suite Rules Asset Scope and Naming Screenshot" width="100%">
  <br>
  <sub>Rules: Asset Scope and Naming — 1217 x 869 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity3.png" alt="M2Unity Pipeline Suite Geometry and Dimension Rules Screenshot" width="100%">
  <br>
  <sub>Rules: Geometry and Dimensions — 1217 x 869 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity4.png" alt="M2Unity Pipeline Suite Pivot Grid and Unity Readiness Screenshot" width="100%">
  <br>
  <sub>Rules: Pivot, Grid and Unity Readiness — 1217 x 873 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity5.png" alt="M2Unity Pipeline Suite Advanced Readiness Screenshot" width="100%">
  <br>
  <sub>Rules: LOD, Material Slot and UV Readiness — 1217 x 873 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity6.png" alt="M2Unity Pipeline Suite Safe Fix Options Screenshot" width="100%">
  <br>
  <sub>Prep / Fix: Safe Fix Options — 1217 x 873 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity7.png" alt="M2Unity Pipeline Suite Collider Proxy Rules Screenshot" width="100%">
  <br>
  <sub>Collider Proxy: Rules and Role Utility — 1217 x 873 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity8.png" alt="M2Unity Pipeline Suite Help Tab Screenshot" width="100%">
  <br>
  <sub>Help: Recommended Workflow and Naming Rules — 1217 x 873 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity9.png" alt="M2Unity Pipeline Suite Analysis Results in Maya Screenshot" width="100%">
  <br>
  <sub>Analysis Results and Asset Status Table — 1546 x 873 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity10.png" alt="M2Unity Pipeline Suite Detailed Result Log Screenshot" width="100%">
  <br>
  <sub>Detailed Validation Log — 1152 x 648 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity11.png" alt="M2Unity Pipeline Suite Naming Rule Result Screenshot" width="100%">
  <br>
  <sub>Role Naming and Mesh Prefix Workflow — 1152 x 648 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity12.png" alt="M2Unity Pipeline Suite Collider Proxy Selection Screenshot" width="100%">
  <br>
  <sub>Collider Proxy Matching Workflow — 1152 x 648 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity13.png" alt="M2Unity Pipeline Suite Collider Proxy Rename Screenshot" width="100%">
  <br>
  <sub>Collider Proxy Rename Result — 1152 x 648 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity14.png" alt="M2Unity Pipeline Suite Exported Files Screenshot" width="100%">
  <br>
  <sub>Exported FBX, JSON, HTML and C# Output Files — 1152 x 648 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity15.png" alt="M2Unity Pipeline Suite Unity Output Object Structure Screenshot" width="100%">
  <br>
  <sub>Unity-Oriented Mesh and Collider Object Structure — 1152 x 648 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity16.png" alt="M2Unity Pipeline Suite HTML Report Overview Screenshot" width="100%">
  <br>
  <sub>Generated HTML Report Overview — 1846 x 930 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity17.png" alt="M2Unity Pipeline Suite HTML Report Core Checks Screenshot" width="100%">
  <br>
  <sub>Generated HTML Report: Core Checks — 1846 x 930 px</sub>
</p>

<p align="center">
  <img src="M2Unity_pipeline_suite_images/m2unity18.png" alt="M2Unity Pipeline Suite HTML Report Readiness Checks Screenshot" width="100%">
  <br>
  <sub>Generated HTML Report: LOD, Material, UV and Socket Readiness — 1846 x 930 px</sub>
</p>
</p>
  <sub>Screenshot 18</sub>
</p>
