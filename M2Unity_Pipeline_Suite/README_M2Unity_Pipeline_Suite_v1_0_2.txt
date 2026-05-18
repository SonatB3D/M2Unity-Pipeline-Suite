M2UNITY PIPELINE SUITE
Maya to Unity Mesh Preflight, Cleanup, Collider Proxy, Validation, Reporting and FBX Export Toolkit

Public Release README
Developer: Sonat Birdane

============================================================
1. OVERVIEW
============================================================

M2Unity Pipeline Suite is a professional Autodesk Maya toolset designed to prepare static mesh assets before they are imported into Unity.

It is not only an FBX exporter. It is a Maya-to-Unity preflight assistant that helps artists, technical artists and asset creators analyze, clean, validate, document and export Unity-ready static mesh assets.

The core workflow is:

    Analyze Selected Assets
    Apply Safe Fixes
    Revalidate
    Export FBX + Reports

M2Unity Pipeline Suite focuses on common issues that appear when moving assets from Maya to Unity, including:

    Naming problems
    Missing or incorrect render mesh prefixes
    Maya import / scene prefixes added in front of asset names
    Unfrozen transforms
    Construction history
    Incorrect pivots
    Grid alignment problems
    Incorrect dimensions
    Near-zero thickness geometry
    Missing Unity collider proxy meshes
    Collider proxy naming mismatches
    Trigger proxy naming mismatches
    High-poly collider proxy meshes
    LOD naming and sequence issues
    Material slot issues
    UV readiness issues
    Optional lightmap UV requirements
    Socket / locator readiness issues
    FBX export consistency
    JSON and HTML QA reports
    Unity AssetPostprocessor C# generation

The goal is to reduce repetitive cleanup work, catch problems before they reach Unity, and make the Maya-to-Unity static mesh export process feel like a controlled studio pipeline.

============================================================
2. WHAT IS NEW IN v1.0.2 ROLE WORKFLOW HOTFIX
============================================================

This version introduces a cleaner Unity-oriented role workflow.

Main changes:

    Render meshes, collider proxies and trigger proxies are handled as separate roles.
    Safe Fix no longer converts base render meshes into collider meshes.
    Role conversion is now done from dedicated Naming / Role Utility buttons.
    Old Unreal UCX meshes can be converted into Unity COL_ or TRG_ proxy meshes.
    Analyze now finds matched COL_ and TRG_ proxy meshes.
    Export refreshes collider proxy matching before exporting.
    Matched COL_ and TRG_ proxy meshes are exported in the same FBX as the render mesh.
    Collider Required blocks export if no matched COL_ or TRG_ proxy exists.
    The generated Unity C# AssetPostprocessor converts COL_ objects to MeshCollider proxies and TRG_ objects to trigger MeshCollider proxies.
    The Maya shelf button is installed into M2U_Tools so related tools stay together.
    The interface header includes the developer credit and a short subtitle.
    The icon text has been corrected to M2Unity.

Recommended role naming:

    Mesh_Table
    COL_Mesh_Table_01
    COL_Mesh_Table_02
    TRG_Mesh_Table_Interaction

Meaning:

    Mesh_       = visible render mesh
    COL_Mesh_   = collider proxy mesh
    TRG_Mesh_   = trigger proxy mesh

============================================================
3. KEY FEATURES
============================================================

M2Unity Pipeline Suite includes the following major systems:

    Modern PySide-based Maya interface
    Dashboard status cards
    Wizard-style workflow
    Unity-specific production presets
    M2Unity readiness score
    Ready / Warning / Blocked status system
    Rule severity system: off, warning, blocking
    Scene import prefix cleanup for Maya-imported names
    Render mesh prefix validation
    Dedicated role naming utility
    Render mesh role assignment: Mesh_
    Collider proxy role assignment: COL_Mesh_
    Trigger proxy role assignment: TRG_Mesh_
    Old UCX collision mesh conversion to Unity collider proxy naming
    Safe Fix system with optional backups
    Freeze transform validation
    Construction history validation
    Polycount validation
    Zero-thickness warning
    Dimension validation
    Pivot validation
    Grid readiness validation
    Pivot preview locator generation
    Collider proxy matching
    Collider required / optional / forbidden modes
    Collider proxy validation
    Collider proxy face-count warning
    Simple box collider proxy creation
    Collider preview colorizing
    Select / isolate asset and matching collider proxies
    LOD readiness checks
    Material slot readiness checks
    UV readiness checks
    Optional lightmap UV checks
    Socket / locator readiness checks
    JSON report export
    HTML QA report export
    Unity AssetPostprocessor C# generation
    FBX export with matched collider and trigger proxies
    Maya shelf installer
    M2U_Tools shelf integration
    Custom M2Unity icon support

============================================================
4. SUPPORTED SOFTWARE
============================================================

Target Maya version:

    Autodesk Maya 2024 and newer

The interface is designed with PySide compatibility handling for modern Maya versions. Maya 2024 commonly uses PySide2. Newer Maya versions may use PySide6. The tool includes fallback handling for both.

Required Maya components:

    Python 3 environment
    maya.cmds
    Maya FBX plug-in for FBX export

Recommended Unity usage:

    Unity project using FBX model assets
    Assets/Editor folder available if using the generated AssetPostprocessor C# script

The generated Unity C# script is not executed inside Maya. It is intended to be copied into a Unity project under an Editor folder, for example:

    Assets/Editor/M2Unity_ModelPostprocessor.cs

Example-only path:

    D:/ExampleUnityProject/Assets/Editor/M2Unity_ModelPostprocessor.cs

============================================================
5. PACKAGE CONTENTS
============================================================

A typical public release package includes:

    m2unity_pipeline_suite_v1_0.py
        Main Maya tool.

    M2Unity Pipeline Suite.py
        Simple launcher script for Maya.

    M2Unity_Pipeline_Suite_v1_0_Easy_Installer.py
        Easy installer. It lets the user choose an installation folder and creates or updates the Maya shelf button.

    reinstall_m2unity_pipeline_suite_shelf_button.py
        Reinstalls or updates the Maya shelf button without reinstalling the whole tool.

    m2unity_pipeline_suite_icon.png
        Shelf button icon.

    README_M2Unity_Pipeline_Suite.txt
        General documentation.

    FUNCTIONS_M2Unity_Pipeline_Suite.txt
        Detailed function and option reference.

    LICENCE_TERMS_M2Unity_Pipeline_Suite.txt
        Licence and usage terms.

============================================================
6. INSTALLATION
============================================================

Recommended installation method:

    Use the Easy Installer.

Steps:

    1. Extract the package to any temporary folder.

    2. Open Autodesk Maya.

    3. Open:

           Windows > General Editors > Script Editor

    4. Switch to the Python tab.

    5. Open or drag the Easy Installer script into the Python tab:

           M2Unity_Pipeline_Suite_v1_0_Easy_Installer.py

    6. Run the script.

    7. Choose the folder where the tool should be installed.

    8. The installer copies the required files to the selected folder.

    9. The installer creates or updates the Maya shelf:

           M2U_Tools

    10. A shelf button named:

           M2Unity Pipeline Suite

        will be added to the M2U_Tools shelf.

After installation, users do not need to run the installer again. The tool can be launched from the M2U_Tools shelf.

Example-only install folder:

    C:/Example/MayaTools/M2Unity_Pipeline_Suite

Do not rely on example paths as required locations. They are only shown to explain the folder structure.

============================================================
7. LAUNCHING THE TOOL
============================================================

After installation, launch the tool from:

    Maya Shelf > M2U_Tools > M2Unity Pipeline Suite

If the shelf button is removed or Maya preferences are reset, run:

    reinstall_m2unity_pipeline_suite_shelf_button.py

This recreates the shelf button without reinstalling the whole package.

The tool can also be launched from Maya Script Editor with:

    import m2unity_pipeline_suite_v1_0
    m2unity_pipeline_suite_v1_0.show()

============================================================
8. QUICK START WORKFLOW
============================================================

Basic recommended workflow:

    1. Select one or more static render meshes in Maya.

    2. Open M2Unity Pipeline Suite.

    3. Choose a preset, for example Unity Static Prop.

    4. Click:

           Analyze Selected Assets

    5. Review the dashboard, asset table and detail panel.

    6. If needed, use the Naming / Role Utility buttons:

           Set Selected as Render Mesh
           Set Selected as Collider Proxy
           Set Selected as Trigger Proxy
           Remove M2Unity Role Prefixes

    7. If the render meshes need cleanup, click:

           Apply Safe Fixes

    8. Click:

           Revalidate

    9. Click:

           Export FBX + Reports

    10. Review the generated HTML report.

    11. If using the generated Unity postprocessor, copy the generated C# file into:

           Assets/Editor/

    12. Import the exported FBX files into Unity.

============================================================
9. RECOMMENDED UNITY ROLE NAMING
============================================================

M2Unity uses explicit role prefixes so the tool can understand what each selected mesh is intended to do.

Render mesh:

    Mesh_Chair
    Mesh_Table
    Mesh_Rock_LOD0

Collider proxy mesh:

    COL_Mesh_Chair_01
    COL_Mesh_Table_01
    COL_Mesh_Table_02

Trigger proxy mesh:

    TRG_Mesh_Door_Interaction
    TRG_Mesh_Chest_OpenZone

Old Unreal-style UCX meshes can be converted into Unity collider proxies using:

    Set Selected as Collider Proxy

Example conversion:

    UCX_SM_Table_01

becomes:

    COL_Mesh_Table_01

The role conversion is intentionally separate from Safe Fix. This prevents the tool from accidentally renaming visible render meshes into collider proxy meshes.

============================================================
10. COLLIDER PROXY WORKFLOW
============================================================

Unity does not automatically treat COL_ names exactly like Unreal treats UCX_ names. M2Unity uses COL_ and TRG_ naming as a tool-side convention.

The intended workflow is:

    Mesh_Table                 visible render mesh
    COL_Mesh_Table_01          collider proxy mesh
    COL_Mesh_Table_02          collider proxy mesh
    TRG_Mesh_Table_Zone        trigger proxy mesh

When Analyze runs, M2Unity searches the scene for matching COL_ and TRG_ proxy meshes.

When Export runs, M2Unity refreshes the matching process and includes matching proxies in the same FBX as the render mesh.

When the generated Unity AssetPostprocessor is used:

    COL_ objects become MeshCollider proxy objects.
    TRG_ objects become MeshCollider objects with isTrigger enabled.
    Renderers on COL_ and TRG_ objects are disabled.

Important:

    COL_ and TRG_ objects are imported into Unity as regular objects unless a postprocessor or a manual Unity setup converts them into colliders.

============================================================
11. PRESETS
============================================================

M2Unity Pipeline Suite includes Unity-specific presets.

Unity Static Prop

    General-purpose static mesh export preset.
    Recommended for props, furniture, rocks, modular pieces and simple environment assets.
    Collider proxies are optional by default.

Unity Environment Kit

    Recommended for modular environment assets.
    Collider proxy requirement is blocking.
    Grid checks and pivot checks are stricter.
    Lightmap UV is required.

Unity Mobile Optimized

    Recommended for low-poly or mobile-focused assets.
    Polycount limit is lower.
    Material slot count is stricter.
    Collider proxies are optional.

Unity LOD / Prefab Ready

    Recommended for assets where LOD naming and prefab readiness are important.
    LOD readiness is treated more strictly.
    Socket / locator readiness remains available for attachment points.

Unity Collider Strict

    Recommended when every exported render mesh must have a matching collider or trigger proxy.
    Collider proxy requirement is blocking.
    Collider proxy validation is stricter.
    Collider face count defaults are intended for conservative Unity collider use.

============================================================
12. WIZARD FLOW BUTTONS
============================================================

Analyze Selected Assets

    Scans selected Maya render mesh transforms and validates them against the active preset and current UI settings.

    It checks naming, geometry, transforms, history, pivot, grid, dimensions, collider proxies, material slots, UV readiness, LOD readiness and socket readiness.

Apply Safe Fixes

    Applies enabled safe cleanup operations to analyzed render meshes.

    Depending on options, it can:

        Create backup duplicates
        Hide backups
        Sanitize names
        Add the required render mesh prefix
        Remove Maya scene/import prefixes before Mesh_
        Sync related COL_ or TRG_ proxy names when needed
        Freeze transforms
        Delete construction history
        Move pivots
        Snap assets to grid
        Unlock transform attributes
        Make selected assets visible

    Apply Safe Fixes does not intentionally convert render meshes into collider proxies. Role conversion is handled by the Naming / Role Utility buttons.

Revalidate

    Runs analysis again on the current selected render meshes.

Export FBX + Reports

    Exports eligible assets to FBX and generates optional reports.

    Depending on export options, it can create:

        FBX files
        M2Unity_Pipeline_Report.json
        M2Unity_Pipeline_Report.html
        M2Unity_ModelPostprocessor.cs

Clear Results

    Clears the UI-side analysis and export results. It does not modify scene objects.

Reset to Defaults

    Restores friendly Unity defaults. It does not modify scene objects.

============================================================
13. UNITY ASSETPOSTPROCESSOR C# SCRIPT
============================================================

When enabled, the tool writes:

    M2Unity_ModelPostprocessor.cs

This script is intended for Unity, not Maya.

Recommended location inside a Unity project:

    Assets/Editor/M2Unity_ModelPostprocessor.cs

The generated script applies conservative model import settings and postprocesses imported objects.

Typical responsibilities:

    Disable camera import
    Disable light import
    Disable animation import for static mesh assets
    Preserve hierarchy
    Import normals
    Calculate tangents using a Unity-friendly tangent mode
    Generate secondary UVs when configured by the script
    Convert COL_ objects into MeshCollider proxy objects
    Convert TRG_ objects into trigger MeshCollider proxy objects
    Disable renderers on COL_ and TRG_ proxy objects

Important:

    Review generated editor scripts before adding them to a production Unity project.
    Team pipelines may require custom importer behavior.
    The generated script is a helper, not a replacement for all studio import rules.

============================================================
14. REPORTS
============================================================

M2Unity can write two report formats.

JSON report:

    M2Unity_Pipeline_Report.json

Use this for technical debugging, automation, data comparison or pipeline integration.

HTML report:

    M2Unity_Pipeline_Report.html

Use this for artist-friendly QA review.

The reports can include:

    Tool name and build
    Timestamp
    Active settings
    Export summary
    Per-asset status
    M2Unity Score
    Warnings
    Blocking issues
    Fix plan
    Fixed actions
    Collider proxy matches
    Collider target candidates
    Polycount
    Dimensions
    Core validation checks
    LOD validation
    Material validation
    UV validation
    Socket validation
    Export status
    Number of included collider proxy objects

============================================================
15. BEST PRACTICES
============================================================

Recommended asset naming:

    Mesh_Table
    COL_Mesh_Table_01
    COL_Mesh_Table_02
    TRG_Mesh_Table_Interaction

Recommended process:

    Use role utility buttons before final analysis.
    Keep collider proxy meshes simple and low-poly.
    Use multiple simple collider proxies instead of one overly complex collider mesh when possible.
    Keep render mesh transforms clean and frozen.
    Delete unnecessary construction history before final export.
    Keep material slot counts reasonable.
    Use consistent material names.
    Use stable LOD suffixes such as _LOD0, _LOD1 and _LOD2.
    Keep pivots consistent with the intended placement behavior in Unity.
    Use HTML reports for visual QA before sending files to Unity.
    Copy the Unity postprocessor only into projects where that behavior is expected.

============================================================
16. IMPORTANT LIMITATIONS
============================================================

M2Unity Pipeline Suite is a Maya-side preparation and export tool. It does not guarantee final in-engine behavior for every Unity project.

Known boundaries:

    The tool does not execute Unity import operations from inside Maya.
    The generated Unity C# script must be placed manually into a Unity project.
    Collider proxy conversion in Unity depends on the generated or custom Unity postprocessor.
    COL_ and TRG_ are tool conventions, not built-in Unity collision naming rules.
    UV overlap detection is conservative.
    Safe Fix does not resize geometry automatically.
    Safe Fix does not rebuild topology.
    Safe Fix does not optimize all meshes automatically.
    Collider mesh performance must still be reviewed by the user.
    Studio-specific Unity import settings may require custom edits to the generated C# script.

Always keep backups of important Maya scenes before using automated cleanup tools.

============================================================
17. TROUBLESHOOTING
============================================================

Problem:

    No assets are analyzed.

Check:

    Make sure visible render meshes are selected.
    COL_ and TRG_ proxy objects are ignored as base assets by default.
    Select Mesh_ render assets for Analyze.

Problem:

    Collider Required blocks the asset.

Check:

    Confirm that matching COL_ or TRG_ proxy meshes exist.
    Example:

        Mesh_Table
        COL_Mesh_Table_01

Problem:

    An old UCX collider mesh is not being treated as a Unity collider proxy.

Fix:

    Select the old UCX mesh and click:

        Set Selected as Collider Proxy

Problem:

    Export creates FBX but Unity does not convert COL_ objects to colliders.

Check:

    Make sure M2Unity_ModelPostprocessor.cs is copied into a Unity Editor folder.
    Example:

        Assets/Editor/M2Unity_ModelPostprocessor.cs

Problem:

    The shelf button is missing.

Fix:

    Run:

        reinstall_m2unity_pipeline_suite_shelf_button.py

Problem:

    The FBX export fails.

Check:

    Make sure the Maya FBX plug-in is available and loaded.
    Confirm that the selected export folder is writable.

============================================================
18. SUMMARY
============================================================

M2Unity Pipeline Suite v1.0.2 is designed to help Maya users prepare cleaner Unity-ready static mesh assets.

The tool combines:

    Preflight validation
    Safe cleanup
    Role-based naming
    Collider and trigger proxy matching
    FBX export
    JSON / HTML reporting
    Unity AssetPostprocessor generation

The main production rule is simple:

    Mesh_      for visible render meshes
    COL_Mesh_  for collider proxy meshes
    TRG_Mesh_  for trigger proxy meshes

Use the tool to catch common Maya-to-Unity asset problems before they become import and setup problems inside Unity.
