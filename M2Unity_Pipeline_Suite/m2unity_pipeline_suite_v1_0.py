# -*- coding: utf-8 -*-
"""
M2Unity Pipeline Suite v1.0
Professional Maya-to-Unity preflight, prep, validation, report and FBX export tool.

Built as a unified successor to:
    - M2U Studio Custom
    - M2U Asset Prep Assistant

Core workflow:
    Analyze Selected Assets -> Review Fix Plan -> Apply Safe Fixes -> Revalidate -> Export FBX + Reports

Usage in Maya Script Editor:
    import m2unity_pipeline_suite_v1_0
    m2unity_pipeline_suite_v1_0.show()

Or run this file directly in Maya's Python tab.

Notes:
    - Maya Y is treated as height/up.
    - Front Axis is limited to X/Z to keep pivot targets deterministic.
    - COL_/TRG_ collider proxy transforms are ignored as base assets by default.
    - Destructive operations are opt-in and backups are enabled by default.
    - UV overlap detection is intentionally conservative in v1.0; UV readiness checks report
      UV set existence, UV count and sampled 0-1 range issues.
"""
from __future__ import print_function

import os
import re
import json
import time
import traceback
import io

try:
    from html import escape as html_escape
except Exception:
    try:
        from cgi import escape as html_escape
    except Exception:
        def html_escape(value):
            return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

try:
    import maya.cmds as cmds
    import maya.mel as mel
    import maya.OpenMayaUI as omui
except Exception:
    cmds = None
    mel = None
    omui = None

# Qt compatibility: Maya 2022-2025 normally exposes PySide2. Some future builds may expose PySide6.
QT_MODE = None
try:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance
    QT_MODE = "PySide2"
except Exception:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
        from shiboken6 import wrapInstance
        QT_MODE = "PySide6"
    except Exception:
        QtCore = None
        QtGui = None
        QtWidgets = None
        wrapInstance = None


M2U_PIPELINE_BUILD_ID = "v1.0.2_unity_role_workflow"
M2U_PIPELINE_WINDOW_TITLE = "M2Unity Pipeline Suite v1.0.2"


# ---------------------------------------------------------
# Presets
# ---------------------------------------------------------

def _deepcopy_json(data):
    return json.loads(json.dumps(data))


BASE_PRESET = {
    "profile_name": "Custom",
    "front_axis": "+Z",
    "ignore_ucx_as_base": True,  # Internal key retained for backward compatibility; now means ignore COL_/TRG_ collider proxy meshes.
    "include_descendant_meshes": True,

    "naming_enabled": True,
    "required_prefix": "Mesh_",
    "naming_severity": "warning",
    "sanitize_names": True,

    "max_polycount": 12000,
    "polycount_severity": "blocking",

    "freeze_required": True,
    "freeze_severity": "blocking",
    "history_required": True,
    "history_severity": "warning",
    "zero_thickness_enabled": True,
    "zero_thickness_tolerance_cm": 0.001,
    "zero_thickness_severity": "warning",

    "dimension_enabled": False,
    "expected_width_cm": 100.0,
    "expected_height_cm": 200.0,
    "expected_depth_cm": 100.0,
    "dimension_tolerance_cm": 0.5,
    "dimension_severity": "blocking",

    "pivot_enabled": True,
    "pivot_target": "Bottom Center",
    "pivot_tolerance_cm": 0.5,
    "pivot_severity": "warning",

    "grid_enabled": True,
    "grid_step_cm": 100.0,
    "grid_check_bounds_snap": True,
    "grid_check_size_multiple": True,
    "grid_severity": "warning",

    "collision_enabled": True,
    "collision_requirement": "Collider optional",
    "collision_match_mode": "Base asset name",
    "custom_collision_target": "",
    "accept_multiple_ucx_parts": True,
    "validate_ucx_meshes": True,
    "ucx_mesh_validation_severity": "warning",
    "collision_severity": "warning",
    "collider_prefixes": "COL_,TRG_",
    "max_collider_faces": 255,

    "lod_enabled": True,
    "lod_severity": "warning",
    "socket_enabled": True,
    "socket_severity": "warning",
    "material_enabled": True,
    "material_prefixes": "M_,MAT_,MI_",
    "max_material_slots": 8,
    "material_severity": "warning",
    "uv_enabled": True,
    "require_lightmap_uv": False,
    "lightmap_uv_names": "uv2,UV2,lightmap,Lightmap,UV1,uv1,map2",
    "uv_sample_limit": 2000,
    "uv_severity": "warning",

    "make_backup": True,
    "hide_backups": True,
    "fix_rename": True,
    "sync_ucx_names_on_rename": True,
    "fix_freeze": True,
    "fix_history": True,
    "fix_pivot": True,
    "fix_unlock_attrs": False,
    "fix_make_visible": False,
    "snap_bounds_min": False,
    "snap_pivot_to_grid": False,

    "export_ready_assets": True,
    "export_warning_assets": True,
    "skip_blocked_assets": True,
    "write_json_report": True,
    "write_html_report": True,
    "write_unreal_import_script": True,  # Internal key retained; writes a Unity AssetPostprocessor .cs file.
    "triangulate_export": False,
}


PRESETS = {}
PRESETS["Unity Static Prop"] = _deepcopy_json(BASE_PRESET)
PRESETS["Unity Static Prop"].update({
    "profile_name": "Unity Static Prop",
    "collision_requirement": "Collider optional",
    "dimension_enabled": False,
    "grid_step_cm": 100.0,
    "max_polycount": 12000,
    "pivot_target": "Bottom Center",
    "require_lightmap_uv": False,
})

PRESETS["Unity Environment Kit"] = _deepcopy_json(BASE_PRESET)
PRESETS["Unity Environment Kit"].update({
    "profile_name": "Unity Environment Kit",
    "collision_requirement": "Collider required",
    "collision_severity": "blocking",
    "grid_step_cm": 100.0,
    "grid_check_size_multiple": True,
    "grid_severity": "blocking",
    "dimension_enabled": False,
    "pivot_target": "Bottom Center",
    "pivot_severity": "blocking",
    "require_lightmap_uv": True,
})

PRESETS["Unity Mobile Optimized"] = _deepcopy_json(BASE_PRESET)
PRESETS["Unity Mobile Optimized"].update({
    "profile_name": "Unity Mobile Optimized",
    "collision_requirement": "Collider optional",
    "max_polycount": 5000,
    "polycount_severity": "warning",
    "max_material_slots": 3,
    "material_severity": "warning",
    "grid_step_cm": 100.0,
})

PRESETS["Unity LOD / Prefab Ready"] = _deepcopy_json(BASE_PRESET)
PRESETS["Unity LOD / Prefab Ready"].update({
    "profile_name": "Unity LOD / Prefab Ready",
    "collision_requirement": "Collider optional",
    "lod_enabled": True,
    "lod_severity": "blocking",
    "socket_enabled": True,
    "socket_severity": "warning",
    "max_polycount": 25000,
})

PRESETS["Unity Collider Strict"] = _deepcopy_json(BASE_PRESET)
PRESETS["Unity Collider Strict"].update({
    "profile_name": "Unity Collider Strict",
    "collision_requirement": "Collider required",
    "collision_severity": "blocking",
    "validate_ucx_meshes": True,
    "ucx_mesh_validation_severity": "blocking",
    "max_polycount": 15000,
    "max_collider_faces": 255,
})

PRESET_NAMES = [
    "Unity Static Prop",
    "Unity Environment Kit",
    "Unity Mobile Optimized",
    "Unity LOD / Prefab Ready",
    "Unity Collider Strict",
]

FRONT_AXES = ["+X", "-X", "+Z", "-Z"]
SEVERITIES = ["off", "warning", "blocking"]
COLLISION_REQUIREMENTS = ["Off", "Collider required", "Collider optional", "No custom collider allowed"]
MATCH_MODES = ["Base asset name", "Exact custom target name"]
PIVOT_TARGETS = [
    "Center",
    "Bottom Center",
    "Bottom Front Center",
    "Bottom Back Center",
    "Bottom Left Center",
    "Bottom Right Center",
    "Bottom Front Left",
    "Bottom Front Right",
    "Bottom Back Left",
    "Bottom Back Right",
    "Front Center",
    "Back Center",
    "Left Center",
    "Right Center",
    "Top Center",
    "Top Front Center",
    "Top Back Center",
    "Top Left Center",
    "Top Right Center",
    "Top Front Left",
    "Top Front Right",
    "Top Back Left",
    "Top Back Right",
]


# ---------------------------------------------------------
# Maya / Qt helpers
# ---------------------------------------------------------

def maya_main_window():
    if omui is None or wrapInstance is None or QtWidgets is None:
        return None
    try:
        ptr = omui.MQtUtil.mainWindow()
        if ptr is None:
            return None
        return wrapInstance(int(ptr), QtWidgets.QWidget)
    except Exception:
        return None


def safe_message_box(title, message, icon="info"):
    if QtWidgets is None:
        try:
            cmds.warning("{0}: {1}".format(title, message))
        except Exception:
            print("{0}: {1}".format(title, message))
        return
    box = QtWidgets.QMessageBox(maya_main_window())
    box.setWindowTitle(title)
    box.setText(message)
    if icon == "warning":
        box.setIcon(QtWidgets.QMessageBox.Warning)
    elif icon == "error":
        box.setIcon(QtWidgets.QMessageBox.Critical)
    else:
        box.setIcon(QtWidgets.QMessageBox.Information)
    box.exec_()


# ---------------------------------------------------------
# Core engine
# ---------------------------------------------------------

class M2UPipelineEngine(object):
    def __init__(self):
        self.preview_materials = []
        self.preview_material_assignments = {}

    # ------------------------------
    # Name helpers
    # ------------------------------
    def short_name(self, node):
        return (node or "").split("|")[-1]

    def strip_namespace(self, name):
        return (name or "").split(":")[-1]

    def clean_asset_name(self, node_or_name):
        return self.strip_namespace(self.short_name(node_or_name))

    def is_ucx_name(self, node_or_name):
        # Internal method name retained for compatibility with the original M2U codebase.
        # In M2Unity, COL_ and TRG_ nodes are treated as collider proxy meshes, not base assets.
        clean = self.clean_asset_name(node_or_name)
        return clean.startswith("COL_") or clean.startswith("TRG_") or clean.startswith("UCX_")

    def safe_node_name(self, name):
        cleaned = self.strip_namespace(self.short_name(name))
        cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", cleaned)
        cleaned = cleaned.strip("_")
        if not cleaned:
            cleaned = "Mesh_UnnamedAsset"
        if cleaned[0].isdigit():
            cleaned = "Mesh_" + cleaned
        return cleaned

    def safe_filename(self, name):
        clean = self.clean_asset_name(name)
        clean = re.sub(r"[^A-Za-z0-9._-]+", "_", clean)
        clean = clean.strip("._")
        return clean or "UnnamedAsset"

    def strip_lod_suffix(self, name):
        return re.sub(r"_LOD[0-9]+$", "", self.clean_asset_name(name), flags=re.IGNORECASE)

    # ------------------------------
    # Scene helpers
    # ------------------------------
    def get_mesh_shapes_under_transform(self, transform, include_descendants=True):
        direct_shapes = cmds.listRelatives(transform, shapes=True, noIntermediate=True, fullPath=True) or []
        desc_shapes = []
        if include_descendants:
            desc_shapes = cmds.listRelatives(transform, allDescendents=True, type="mesh", fullPath=True) or []
        all_shapes = []
        seen = set()
        for shape in direct_shapes + desc_shapes:
            if not shape or shape in seen:
                continue
            try:
                if cmds.nodeType(shape) != "mesh":
                    continue
                if cmds.getAttr(shape + ".intermediateObject"):
                    continue
            except Exception:
                continue
            seen.add(shape)
            all_shapes.append(shape)
        return all_shapes

    def _transform_has_mesh(self, transform, include_descendants=True):
        return bool(self.get_mesh_shapes_under_transform(transform, include_descendants=include_descendants))

    def get_selected_transforms(self, settings):
        selected = cmds.ls(selection=True, long=True, type="transform") or []
        valid = []
        seen = set()
        for obj in selected:
            if obj in seen:
                continue
            if settings.get("ignore_ucx_as_base") and self.is_ucx_name(obj):
                continue
            if self._transform_has_mesh(obj, settings.get("include_descendant_meshes", True)):
                valid.append(obj)
                seen.add(obj)
        return valid

    def get_world_bbox(self, transform):
        bb = cmds.exactWorldBoundingBox(transform)
        return {
            "minX": bb[0], "minY": bb[1], "minZ": bb[2],
            "maxX": bb[3], "maxY": bb[4], "maxZ": bb[5],
        }

    def get_bbox_sizes(self, transform):
        bb = self.get_world_bbox(transform)
        return (
            abs(bb["maxX"] - bb["minX"]),
            abs(bb["maxY"] - bb["minY"]),
            abs(bb["maxZ"] - bb["minZ"]),
        )

    def get_bbox_center(self, transform):
        bb = self.get_world_bbox(transform)
        return (
            (bb["minX"] + bb["maxX"]) * 0.5,
            (bb["minY"] + bb["maxY"]) * 0.5,
            (bb["minZ"] + bb["maxZ"]) * 0.5,
        )

    def get_pivot_position(self, transform):
        pos = cmds.xform(transform, q=True, ws=True, rp=True)
        return (pos[0], pos[1], pos[2])

    def _orientation_points_from_axis(self, bb, front_axis):
        cx = (bb["minX"] + bb["maxX"]) * 0.5
        cy = (bb["minY"] + bb["maxY"]) * 0.5
        cz = (bb["minZ"] + bb["maxZ"]) * 0.5
        if front_axis == "+X":
            return {
                "front": (bb["maxX"], cy, cz),
                "back": (bb["minX"], cy, cz),
                "left": (cx, cy, bb["minZ"]),
                "right": (cx, cy, bb["maxZ"]),
                "front_left": (bb["maxX"], cy, bb["minZ"]),
                "front_right": (bb["maxX"], cy, bb["maxZ"]),
                "back_left": (bb["minX"], cy, bb["minZ"]),
                "back_right": (bb["minX"], cy, bb["maxZ"]),
            }
        if front_axis == "-X":
            return {
                "front": (bb["minX"], cy, cz),
                "back": (bb["maxX"], cy, cz),
                "left": (cx, cy, bb["maxZ"]),
                "right": (cx, cy, bb["minZ"]),
                "front_left": (bb["minX"], cy, bb["maxZ"]),
                "front_right": (bb["minX"], cy, bb["minZ"]),
                "back_left": (bb["maxX"], cy, bb["maxZ"]),
                "back_right": (bb["maxX"], cy, bb["minZ"]),
            }
        if front_axis == "+Z":
            return {
                "front": (cx, cy, bb["maxZ"]),
                "back": (cx, cy, bb["minZ"]),
                "left": (bb["maxX"], cy, cz),
                "right": (bb["minX"], cy, cz),
                "front_left": (bb["maxX"], cy, bb["maxZ"]),
                "front_right": (bb["minX"], cy, bb["maxZ"]),
                "back_left": (bb["maxX"], cy, bb["minZ"]),
                "back_right": (bb["minX"], cy, bb["minZ"]),
            }
        if front_axis == "-Z":
            return {
                "front": (cx, cy, bb["minZ"]),
                "back": (cx, cy, bb["maxZ"]),
                "left": (bb["minX"], cy, cz),
                "right": (bb["maxX"], cy, cz),
                "front_left": (bb["minX"], cy, bb["minZ"]),
                "front_right": (bb["maxX"], cy, bb["minZ"]),
                "back_left": (bb["minX"], cy, bb["maxZ"]),
                "back_right": (bb["maxX"], cy, bb["maxZ"]),
            }
        raise ValueError("Unsupported front axis: {0}".format(front_axis))

    def _with_y(self, point, y_value):
        return (point[0], y_value, point[2])

    def get_target_pivot_position(self, transform, pivot_target, front_axis):
        bb = self.get_world_bbox(transform)
        cx = (bb["minX"] + bb["maxX"]) * 0.5
        cy = (bb["minY"] + bb["maxY"]) * 0.5
        cz = (bb["minZ"] + bb["maxZ"]) * 0.5
        bottom_y = bb["minY"]
        top_y = bb["maxY"]
        orientation = self._orientation_points_from_axis(bb, front_axis)
        target_map = {
            "Center": (cx, cy, cz),
            "Bottom Center": (cx, bottom_y, cz),
            "Bottom Front Center": self._with_y(orientation["front"], bottom_y),
            "Bottom Back Center": self._with_y(orientation["back"], bottom_y),
            "Bottom Left Center": self._with_y(orientation["left"], bottom_y),
            "Bottom Right Center": self._with_y(orientation["right"], bottom_y),
            "Bottom Front Left": self._with_y(orientation["front_left"], bottom_y),
            "Bottom Front Right": self._with_y(orientation["front_right"], bottom_y),
            "Bottom Back Left": self._with_y(orientation["back_left"], bottom_y),
            "Bottom Back Right": self._with_y(orientation["back_right"], bottom_y),
            "Front Center": orientation["front"],
            "Back Center": orientation["back"],
            "Left Center": orientation["left"],
            "Right Center": orientation["right"],
            "Top Center": (cx, top_y, cz),
            "Top Front Center": self._with_y(orientation["front"], top_y),
            "Top Back Center": self._with_y(orientation["back"], top_y),
            "Top Left Center": self._with_y(orientation["left"], top_y),
            "Top Right Center": self._with_y(orientation["right"], top_y),
            "Top Front Left": self._with_y(orientation["front_left"], top_y),
            "Top Front Right": self._with_y(orientation["front_right"], top_y),
            "Top Back Left": self._with_y(orientation["back_left"], top_y),
            "Top Back Right": self._with_y(orientation["back_right"], top_y),
        }
        return target_map.get(pivot_target, (cx, cy, cz))

    def get_polycount_for_transform(self, transform, include_descendants=True):
        mesh_shapes = self.get_mesh_shapes_under_transform(transform, include_descendants=include_descendants)
        total_faces = 0
        for shape in mesh_shapes:
            try:
                total_faces += cmds.polyEvaluate(shape, face=True) or 0
            except Exception:
                pass
        return total_faces

    def has_freeze_issue(self, transform):
        try:
            tx = cmds.getAttr(transform + ".translateX")
            ty = cmds.getAttr(transform + ".translateY")
            tz = cmds.getAttr(transform + ".translateZ")
            rx = cmds.getAttr(transform + ".rotateX")
            ry = cmds.getAttr(transform + ".rotateY")
            rz = cmds.getAttr(transform + ".rotateZ")
            sx = cmds.getAttr(transform + ".scaleX")
            sy = cmds.getAttr(transform + ".scaleY")
            sz = cmds.getAttr(transform + ".scaleZ")
            return not (
                abs(tx) < 1e-6 and abs(ty) < 1e-6 and abs(tz) < 1e-6 and
                abs(rx) < 1e-6 and abs(ry) < 1e-6 and abs(rz) < 1e-6 and
                abs(sx - 1.0) < 1e-6 and abs(sy - 1.0) < 1e-6 and abs(sz - 1.0) < 1e-6
            )
        except Exception:
            return False

    def has_history_issue(self, transform):
        history = cmds.listHistory(transform, pruneDagObjects=True) or []
        filtered = []
        ignored_types = set([
            "mesh", "shadingEngine", "groupId", "transform", "objectSet", "materialInfo",
            "dagPose", "hyperLayout", "hyperView", "displayLayer", "renderLayer",
        ])
        for node in history:
            if node == transform:
                continue
            try:
                node_type = cmds.nodeType(node)
            except Exception:
                continue
            if node_type in ignored_types:
                continue
            filtered.append(node)
        return len(filtered) > 0, filtered

    def _is_multiple_of_step(self, value, step, epsilon=1e-4):
        if step <= 0.0:
            return False
        ratio = value / step
        return abs(ratio - round(ratio)) <= epsilon

    def _snap_value(self, value, step):
        if step <= 0.0:
            return value
        return round(value / step) * step

    def _format_float_list(self, values):
        return ", ".join(["{0:.3f}".format(v) for v in values])

    def _is_transform_visible_in_hierarchy(self, transform):
        try:
            if not cmds.objExists(transform):
                return False
            nodes = [transform] + (cmds.listRelatives(transform, allParents=True, fullPath=True) or [])
            for node in nodes:
                try:
                    if cmds.attributeQuery("visibility", node=node, exists=True):
                        if not cmds.getAttr(node + ".visibility"):
                            return False
                except Exception:
                    pass
            return True
        except Exception:
            return True

    def _get_locked_transform_attrs(self, transform):
        locked = []
        attrs = [
            "translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ",
            "scaleX", "scaleY", "scaleZ",
            "visibility",
        ]
        for attr in attrs:
            plug = transform + "." + attr
            try:
                if cmds.objExists(plug) and cmds.getAttr(plug, lock=True):
                    locked.append(attr)
            except Exception:
                pass
        return locked

    def _unlock_transform_attrs(self, transform):
        unlocked = []
        attrs = [
            "translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ",
            "scaleX", "scaleY", "scaleZ",
            "visibility",
        ]
        for attr in attrs:
            plug = transform + "." + attr
            try:
                if cmds.objExists(plug) and cmds.getAttr(plug, lock=True):
                    cmds.setAttr(plug, lock=False)
                    unlocked.append(attr)
            except Exception:
                pass
        return unlocked

    def _unique_name(self, base_name):
        if not cmds.objExists(base_name):
            return base_name
        index = 1
        while True:
            candidate = "{0}_{1:03d}".format(base_name, index)
            if not cmds.objExists(candidate):
                return candidate
            index += 1

    def _add_issue(self, result, severity, message):
        if severity == "blocking":
            result["blocking_issues"].append(message)
        elif severity == "warning":
            result["warnings"].append(message)

    def _make_check(self, status, reason, severity="info"):
        return {"status": status, "reason": reason, "severity": severity}

    # ------------------------------
    # Unity Collider Proxy Workflow
    # ------------------------------
    def _get_collision_target_name(self, asset_name, settings):
        if settings.get("collision_match_mode") == "Exact custom target name":
            return self.clean_asset_name(settings.get("custom_collision_target", ""))
        return self.clean_asset_name(asset_name)

    def _collision_compare_key(self, name):
        clean = self.clean_asset_name(name).strip()
        clean = self._strip_import_scene_prefix_before_any_role_prefix(clean)
        return clean.lower()

    def _collider_prefixes(self, settings=None):
        settings = settings or {}
        raw = settings.get("collider_prefixes", "COL_,TRG_") or "COL_,TRG_"
        prefixes = []
        for item in raw.split(','):
            p = item.strip()
            if not p:
                continue
            if not p.endswith('_'):
                p += '_'
            if p not in prefixes:
                prefixes.append(p)
        if not prefixes:
            prefixes = ["COL_", "TRG_"]
        return prefixes

    def _base_prefix_candidates(self, required_prefix=None):
        prefixes = []
        for p in [required_prefix, "Mesh_", "MESH_", "mesh_", "SM_", "S_", "SK_"]:
            if p and p not in prefixes:
                prefixes.append(p)
        return prefixes

    def _role_prefix_candidates(self, settings=None, required_prefix=None):
        prefixes = []
        for p in self._collider_prefixes(settings) + ["UCX_"] + self._base_prefix_candidates(required_prefix):
            if p and p not in prefixes:
                prefixes.append(p)
        return sorted(prefixes, key=len, reverse=True)

    def _strip_import_scene_prefix_before_any_role_prefix(self, name, settings=None, required_prefix=None):
        """Remove Maya import/scene prefixes before Mesh_, COL_, TRG_ or UCX_.

        Examples:
            Scene01_Mesh_Table -> Mesh_Table
            ImportedScene_COL_Mesh_Table_01 -> COL_Mesh_Table_01
            Props_UCX_SM_Chair_01 -> UCX_SM_Chair_01
        """
        clean = self.clean_asset_name(name)
        if not clean:
            return clean
        clean_key = clean.lower()
        for p in self._role_prefix_candidates(settings, required_prefix):
            if clean_key.startswith(p.lower()):
                return clean
        hits = []
        for p in self._role_prefix_candidates(settings, required_prefix):
            pos = clean_key.find(p.lower())
            if pos > 0:
                hits.append((pos, p))
        if not hits:
            return clean
        pos, _ = sorted(hits, key=lambda item: item[0])[0]
        return clean[pos:]

    def _has_base_prefix(self, name, required_prefix=None):
        clean = self._strip_import_scene_prefix_before_any_role_prefix(name, required_prefix=required_prefix)
        clean_key = clean.lower()
        return any(clean_key.startswith(p.lower()) for p in self._base_prefix_candidates(required_prefix))

    def _is_collider_proxy_name(self, name, settings=None):
        clean = self._strip_import_scene_prefix_before_any_role_prefix(name, settings=settings)
        clean_key = clean.lower()
        prefixes = self._collider_prefixes(settings) + ["UCX_"]
        return any(clean_key.startswith(p.lower()) for p in prefixes)

    def _remove_collider_proxy_prefix(self, name, settings=None):
        clean = self._strip_import_scene_prefix_before_any_role_prefix(name, settings=settings)
        prefixes = sorted(self._collider_prefixes(settings) + ["UCX_"], key=len, reverse=True)
        for p in prefixes:
            if clean.lower().startswith(p.lower()):
                return clean[len(p):]
        return clean

    def _sanitize_required_base_prefix(self, prefix, settings=None):
        prefix = (prefix or "Mesh_").strip() or "Mesh_"
        if not prefix.endswith('_'):
            prefix += '_'
        # COL_/TRG_/UCX_ and COL_Mesh_/TRG_Mesh_ style prefixes are reserved for
        # collider/trigger proxy meshes. The render/base prefix is never allowed to
        # become a collider prefix, even if the user types it into the Required Prefix box.
        low = prefix.lower()
        reserved = [p.lower() for p in (self._collider_prefixes(settings) + ["UCX_"])]
        if any(low == r or low.startswith(r) for r in reserved):
            return "Mesh_"
        return prefix

    def _strip_import_scene_prefix_before_base_prefix(self, name, required_prefix=None):
        """Remove Maya import/scene prefixes before the render-mesh prefix.

        Example: HouseScene_Mesh_Chair -> Mesh_Chair
        Example: imported:Mesh_Table -> Mesh_Table (namespace is already stripped elsewhere)
        """
        clean = self.clean_asset_name(name)
        if not clean:
            return clean
        clean_key = clean.lower()
        if self._has_base_prefix(clean, required_prefix):
            return self._strip_import_scene_prefix_before_any_role_prefix(clean, required_prefix=required_prefix)
        hits = []
        for p in self._base_prefix_candidates(required_prefix):
            pos = clean_key.find(p.lower())
            if pos > 0:
                hits.append((pos, p))
        if not hits:
            return clean
        pos, _ = sorted(hits, key=lambda item: item[0])[0]
        return clean[pos:]

    def _strip_known_asset_role_prefixes(self, name, settings=None):
        """Return the neutral asset stem used by the role utility.

        This intentionally strips Unity role prefixes and common Unreal prefixes so an
        old UCX_SM_Table_01 object can become COL_Mesh_Table_01 in one click.
        """
        clean = self.safe_node_name(name)
        clean = self._strip_import_scene_prefix_before_any_role_prefix(clean, settings=settings)
        changed = True
        while changed:
            changed = False
            for p in self._role_prefix_candidates(settings, required_prefix="Mesh_"):
                if clean.lower().startswith(p.lower()):
                    clean = clean[len(p):]
                    clean = clean.strip("_")
                    changed = True
                    break
        clean = clean.strip("_") or "UnnamedAsset"
        return clean

    def role_name_for_asset(self, current_name, role, settings=None):
        base = self._strip_known_asset_role_prefixes(current_name, settings=settings)
        if role == "render":
            return "Mesh_" + base
        if role == "collider":
            return "COL_Mesh_" + base
        if role == "trigger":
            return "TRG_Mesh_" + base
        if role == "remove":
            return base
        return self.safe_node_name(current_name)

    def get_selected_mesh_transforms_any(self):
        """Return selected mesh transforms without filtering out COL_/TRG_/UCX_ names."""
        selected = cmds.ls(selection=True, long=True) or []
        valid = []
        seen = set()
        for obj in selected:
            transform = obj
            try:
                node_type = cmds.nodeType(obj)
            except Exception:
                node_type = None
            if node_type == "mesh":
                parents = cmds.listRelatives(obj, parent=True, fullPath=True) or []
                if not parents:
                    continue
                transform = parents[0]
            elif node_type != "transform":
                parents = cmds.listRelatives(obj, parent=True, fullPath=True) or []
                if parents:
                    transform = parents[0]
            if not transform or transform in seen:
                continue
            if self._transform_has_mesh(transform, include_descendants=True):
                valid.append(transform)
                seen.add(transform)
        return valid

    def rename_selected_as_role(self, role, settings=None):
        """Artist-controlled role naming for selected transforms.

        This is intentionally separate from Safe Fix. It may operate on UCX_, COL_
        and TRG_ meshes because users often convert Unreal collision meshes into
        Unity collider/trigger proxies.
        """
        selected = self.get_selected_mesh_transforms_any()
        actions = []
        renamed_paths = []
        for transform in selected:
            if not transform or not cmds.objExists(transform):
                continue
            old_name = self.clean_asset_name(transform)
            desired = self.role_name_for_asset(old_name, role, settings=settings)
            desired = self.safe_node_name(desired)
            if desired == old_name:
                renamed_paths.append(transform)
                actions.append("Already named: {0}".format(old_name))
                continue
            final_name = desired if not cmds.objExists(desired) else self._unique_name(desired)
            try:
                renamed = cmds.rename(transform, final_name)
                renamed_paths.append(renamed)
                actions.append("Renamed {0} -> {1}".format(old_name, self.clean_asset_name(renamed)))
            except Exception as exc:
                actions.append("Rename failed for {0}: {1}".format(old_name, exc))
        try:
            if renamed_paths:
                cmds.select(renamed_paths, replace=True)
        except Exception:
            pass
        return actions

    def get_collision_target_candidates(self, target_name, required_prefix=None):
        """Build practical Unity collider/trigger proxy target candidates.

        M2Unity expects render meshes such as Mesh_Table and proxy meshes such as
        COL_Mesh_Table_01 or TRG_Mesh_Table_Interaction. The matcher also tolerates
        Maya import scene prefixes, old SM_ names and LOD suffixes.
        """
        clean = self.clean_asset_name(target_name).strip()
        clean = self._strip_import_scene_prefix_before_any_role_prefix(clean, required_prefix=required_prefix)
        if self._is_collider_proxy_name(clean):
            clean = self._remove_collider_proxy_prefix(clean)
        if not clean:
            return []

        def add_unique(items, value):
            value = (value or "").strip("_")
            if value and value not in items:
                items.append(value)

        candidates = []
        prefix_list = self._base_prefix_candidates(required_prefix)
        seed_items = [clean, self.strip_lod_suffix(clean)]
        for item in seed_items:
            add_unique(candidates, item)
            item_no_scene = self._strip_import_scene_prefix_before_any_role_prefix(item, required_prefix=required_prefix)
            add_unique(candidates, item_no_scene)
            for prefix in prefix_list:
                if prefix and item_no_scene.upper().startswith(prefix.upper()):
                    stripped = item_no_scene[len(prefix):]
                    add_unique(candidates, stripped)
                    add_unique(candidates, self.strip_lod_suffix(stripped))
        return candidates

    def find_ucx_matches(self, target_name, accept_multiple_parts=True, required_prefix=None, settings=None):
        """Find Unity collider proxy meshes.

        Internal method name is retained to minimize risk in the original code path.
        The matching behavior is Unity-oriented: COL_ creates MeshCollider proxies,
        TRG_ creates trigger-capable proxy meshes in the generated postprocessor.
        """
        transforms = cmds.ls(type="transform", long=True) or []
        matches = []
        seen_paths = set()
        target_candidates = self.get_collision_target_candidates(target_name, required_prefix=required_prefix)
        target_keys = [self._collision_compare_key(x) for x in target_candidates]
        prefixes = [p.lower() for p in self._collider_prefixes(settings)]
        base_patterns = []
        for prefix in prefixes:
            for k in target_keys:
                if k:
                    base_patterns.append("{0}{1}".format(prefix, k))

        for node in transforms:
            if not node or node in seen_paths:
                continue
            short_clean = self.clean_asset_name(node)
            match_clean = self._strip_import_scene_prefix_before_any_role_prefix(short_clean, settings=settings, required_prefix=required_prefix)
            short_key = self._collision_compare_key(match_clean)
            if short_key in target_keys:
                continue
            if not any(short_key.startswith(prefix) for prefix in prefixes):
                continue
            if not self._transform_has_mesh(node, include_descendants=True):
                continue

            for base_pattern in base_patterns:
                exact_match = short_key == base_pattern
                multi_match = accept_multiple_parts and short_key.startswith(base_pattern + "_")
                if exact_match or multi_match:
                    matches.append({"name": short_clean, "path": node})
                    seen_paths.add(node)
                    break

        matches.sort(key=lambda item: item["name"].lower())
        return matches

    def validate_ucx_mesh(self, transform, settings):
        proxy_name = self.clean_asset_name(transform)
        checks = {}
        has_mesh = self._transform_has_mesh(transform, include_descendants=True)
        if has_mesh:
            checks["Has Mesh Shape"] = self._make_check("Pass", "Mesh shape found")
        else:
            checks["Has Mesh Shape"] = self._make_check("Fail", "No non-intermediate mesh shape found")

        if not settings.get("freeze_required"):
            checks["Freeze Transform"] = self._make_check("Pass", "Freeze check disabled")
        elif self.has_freeze_issue(transform):
            checks["Freeze Transform"] = self._make_check("Fail", "Transform values are not frozen")
        else:
            checks["Freeze Transform"] = self._make_check("Pass", "Transform values are frozen")

        if not settings.get("history_required"):
            checks["History"] = self._make_check("Pass", "History check disabled")
        else:
            history_issue, history_nodes = self.has_history_issue(transform)
            if history_issue:
                checks["History"] = self._make_check("Fail", "Construction history found: {0}".format(", ".join(history_nodes[:5])))
            else:
                checks["History"] = self._make_check("Pass", "No construction history found")

        face_count = self.get_polycount_for_transform(transform, include_descendants=True)
        max_faces = int(settings.get("max_collider_faces", 255) or 255)
        if face_count <= max_faces:
            checks["Collider Proxy Face Count"] = self._make_check("Pass", "{0} / {1} faces".format(face_count, max_faces))
        else:
            checks["Collider Proxy Face Count"] = self._make_check("Fail", "{0} / {1} faces. Keep Unity collider proxies simple, especially when convex is used.".format(face_count, max_faces))

        if not settings.get("zero_thickness_enabled") or not has_mesh:
            checks["Zero Thickness"] = self._make_check("Pass", "Zero thickness check disabled or no mesh")
        else:
            width, height, depth = self.get_bbox_sizes(transform)
            zero_tol = max(0.0, settings.get("zero_thickness_tolerance_cm", 0.001))
            thin_axes = []
            if width <= zero_tol:
                thin_axes.append("width")
            if height <= zero_tol:
                thin_axes.append("height")
            if depth <= zero_tol:
                thin_axes.append("depth")
            if thin_axes:
                checks["Zero Thickness"] = self._make_check("Fail", "Near-zero axis: {0} | W/H/D: {1}".format(", ".join(thin_axes), self._format_float_list([width, height, depth])))
            else:
                checks["Zero Thickness"] = self._make_check("Pass", "W/H/D: {0}".format(self._format_float_list([width, height, depth])))

        if self._is_transform_visible_in_hierarchy(transform):
            checks["Visibility"] = self._make_check("Pass", "Visible in hierarchy")
        else:
            checks["Visibility"] = self._make_check("Fail", "Transform or parent hierarchy is hidden")

        locked_attrs = self._get_locked_transform_attrs(transform)
        if locked_attrs:
            checks["Locked Attributes"] = self._make_check("Fail", "Locked attrs: {0}".format(", ".join(locked_attrs)))
        else:
            checks["Locked Attributes"] = self._make_check("Pass", "No locked transform attributes")

        failed_checks = [name for name, data in checks.items() if data.get("status") == "Fail"]
        return {
            "name": proxy_name,
            "path": transform,
            "status": "Fail" if failed_checks else "Pass",
            "failed_checks": failed_checks,
            "checks": checks,
        }

    # ------------------------------
    # Material / UV / LOD / Socket
    # ------------------------------
    def get_materials_for_transform(self, transform, include_descendants=True):
        shapes = self.get_mesh_shapes_under_transform(transform, include_descendants=include_descendants)
        materials = []
        seen = set()
        for shape in shapes:
            try:
                shading_engines = cmds.listConnections(shape, type="shadingEngine") or []
            except Exception:
                shading_engines = []
            for sg in shading_engines:
                mat = None
                try:
                    mats = cmds.listConnections(sg + ".surfaceShader") or []
                    if mats:
                        mat = mats[0]
                except Exception:
                    mat = None
                name = self.clean_asset_name(mat or sg)
                if name and name not in seen:
                    seen.add(name)
                    materials.append(name)
        return materials

    def check_materials(self, transform, settings):
        checks = {}
        if not settings.get("material_enabled"):
            return {"status": "Skipped", "checks": {"Material Slots": self._make_check("Pass", "Material check disabled")}, "warnings": []}
        materials = self.get_materials_for_transform(transform, settings.get("include_descendant_meshes", True))
        prefixes = [p.strip() for p in (settings.get("material_prefixes") or "").split(",") if p.strip()]
        max_slots = settings.get("max_material_slots", 0)
        warnings = []
        if not materials:
            checks["Material Slots"] = self._make_check("Fail", "No material assignments found")
            warnings.append("No material assignments found")
        else:
            checks["Material Slots"] = self._make_check("Pass", "{0} material slot(s): {1}".format(len(materials), ", ".join(materials)))
        if max_slots > 0 and len(materials) > max_slots:
            checks["Material Slot Count"] = self._make_check("Fail", "{0} slots exceeds max {1}".format(len(materials), max_slots))
            warnings.append("Too many material slots: {0} > {1}".format(len(materials), max_slots))
        else:
            checks["Material Slot Count"] = self._make_check("Pass", "{0} / {1}".format(len(materials), max_slots))
        bad_names = []
        default_materials = []
        for mat in materials:
            if mat.lower() in ["lambert1", "initialshadinggroup", "initialparticlese"]:
                default_materials.append(mat)
            if prefixes and not any(mat.startswith(prefix) for prefix in prefixes):
                bad_names.append(mat)
        if default_materials:
            checks["Default Material"] = self._make_check("Fail", "Default material detected: {0}".format(", ".join(default_materials)))
            warnings.append("Default material detected: {0}".format(", ".join(default_materials)))
        else:
            checks["Default Material"] = self._make_check("Pass", "No default material detected")
        if bad_names:
            checks["Material Naming"] = self._make_check("Fail", "Names without prefix: {0}".format(", ".join(bad_names)))
            warnings.append("Material names do not match prefixes: {0}".format(", ".join(bad_names)))
        else:
            checks["Material Naming"] = self._make_check("Pass", "Material prefixes OK")
        return {"status": "Fail" if warnings else "Pass", "checks": checks, "warnings": warnings, "materials": materials}

    def _sample_uvs_for_shape(self, shape, sample_limit):
        result = {"uv_count": 0, "outside_01_count": 0, "sampled": 0, "error": ""}
        try:
            uv_count = cmds.polyEvaluate(shape, uvcoord=True) or 0
            result["uv_count"] = int(uv_count)
            if uv_count <= 0:
                return result
            uv_components = cmds.ls(shape + ".map[*]", flatten=True) or []
            if sample_limit and len(uv_components) > sample_limit:
                uv_components = uv_components[:sample_limit]
            result["sampled"] = len(uv_components)
            if not uv_components:
                return result
            values = cmds.polyEditUV(uv_components, q=True) or []
            outside = 0
            for i in range(0, len(values), 2):
                try:
                    u = float(values[i])
                    v = float(values[i + 1])
                    if u < -1e-5 or u > 1.00001 or v < -1e-5 or v > 1.00001:
                        outside += 1
                except Exception:
                    pass
            result["outside_01_count"] = outside
        except Exception as exc:
            result["error"] = str(exc)
        return result

    def check_uvs(self, transform, settings):
        checks = {}
        warnings = []
        if not settings.get("uv_enabled"):
            return {"status": "Skipped", "checks": {"UV": self._make_check("Pass", "UV check disabled")}, "warnings": []}
        shapes = self.get_mesh_shapes_under_transform(transform, settings.get("include_descendant_meshes", True))
        lightmap_names = [x.strip() for x in (settings.get("lightmap_uv_names") or "").split(",") if x.strip()]
        require_lightmap = settings.get("require_lightmap_uv")
        sample_limit = int(settings.get("uv_sample_limit") or 2000)
        uv_sets_by_shape = {}
        outside_total = 0
        uv_total = 0
        errors = []
        found_lightmap = False
        for shape in shapes:
            try:
                uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
            except Exception:
                uv_sets = []
            uv_sets_by_shape[self.clean_asset_name(shape)] = uv_sets
            if any(uv in lightmap_names for uv in uv_sets):
                found_lightmap = True
            if not uv_sets:
                warnings.append("Missing UV set on {0}".format(self.clean_asset_name(shape)))
            sample = self._sample_uvs_for_shape(shape, sample_limit)
            uv_total += sample.get("uv_count", 0)
            outside_total += sample.get("outside_01_count", 0)
            if sample.get("error"):
                errors.append("{0}: {1}".format(self.clean_asset_name(shape), sample.get("error")))
        if uv_total <= 0:
            checks["UV Coordinates"] = self._make_check("Fail", "No UV coordinates found")
            warnings.append("No UV coordinates found")
        else:
            checks["UV Coordinates"] = self._make_check("Pass", "{0} UV coordinate(s) found".format(uv_total))
        if outside_total > 0:
            checks["UV 0-1 Range"] = self._make_check("Fail", "{0} sampled UV coordinate(s) outside 0-1".format(outside_total))
            warnings.append("Sampled UVs outside 0-1: {0}".format(outside_total))
        else:
            checks["UV 0-1 Range"] = self._make_check("Pass", "Sampled UVs are inside 0-1")
        if require_lightmap and not found_lightmap:
            checks["Lightmap UV"] = self._make_check("Fail", "Required lightmap UV set not found")
            warnings.append("Required lightmap UV set not found")
        else:
            checks["Lightmap UV"] = self._make_check("Pass", "Lightmap UV found or not required")
        checks["UV Overlap"] = self._make_check("Info", "Overlap calculation is advisory/manual in v1.0")
        if errors:
            checks["UV Sampling Errors"] = self._make_check("Info", "; ".join(errors[:3]))
        return {"status": "Fail" if warnings else "Pass", "checks": checks, "warnings": warnings, "uv_sets_by_shape": uv_sets_by_shape}

    def find_lod_group(self, transform):
        asset_name = self.clean_asset_name(transform)
        base = self.strip_lod_suffix(asset_name)
        transforms = cmds.ls(type="transform", long=True) or []
        lod_items = []
        pattern = re.compile(r"^{0}_LOD([0-9]+)$".format(re.escape(base)), re.IGNORECASE)
        for node in transforms:
            name = self.clean_asset_name(node)
            match = pattern.match(name)
            if match and self._transform_has_mesh(node, include_descendants=True):
                lod_items.append({"lod": int(match.group(1)), "name": name, "path": node})
        lod_items.sort(key=lambda item: item["lod"])
        return base, lod_items

    def check_lods(self, transform, settings):
        checks = {}
        warnings = []
        if not settings.get("lod_enabled"):
            return {"status": "Skipped", "checks": {"LOD": self._make_check("Pass", "LOD check disabled")}, "warnings": []}
        base, lod_items = self.find_lod_group(transform)
        if not lod_items:
            checks["LOD Group"] = self._make_check("Pass", "No LOD naming detected. Single mesh workflow is valid.")
            return {"status": "Pass", "checks": checks, "warnings": [], "lod_items": []}
        lods = [item["lod"] for item in lod_items]
        if lods[0] != 0:
            checks["LOD0"] = self._make_check("Fail", "LOD group exists but LOD0 is missing")
            warnings.append("LOD0 is missing")
        else:
            checks["LOD0"] = self._make_check("Pass", "LOD0 found")
        polycounts = []
        for item in lod_items:
            polycounts.append((item["lod"], self.get_polycount_for_transform(item["path"], True)))
        decreasing = True
        for i in range(1, len(polycounts)):
            if polycounts[i][1] > polycounts[i - 1][1]:
                decreasing = False
                break
        if decreasing:
            checks["LOD Polycount"] = self._make_check("Pass", ", ".join(["LOD{0}: {1}".format(lod, count) for lod, count in polycounts]))
        else:
            checks["LOD Polycount"] = self._make_check("Fail", "Polycount should decrease or stay equal across LODs: {0}".format(", ".join(["LOD{0}: {1}".format(lod, count) for lod, count in polycounts])))
            warnings.append("LOD polycount is not decreasing")
        try:
            pivots = [self.get_pivot_position(item["path"]) for item in lod_items]
            ref = pivots[0]
            pivot_ok = all(abs(p[0] - ref[0]) < 0.001 and abs(p[1] - ref[1]) < 0.001 and abs(p[2] - ref[2]) < 0.001 for p in pivots)
            if pivot_ok:
                checks["LOD Pivot Consistency"] = self._make_check("Pass", "LOD pivots are consistent")
            else:
                checks["LOD Pivot Consistency"] = self._make_check("Fail", "LOD pivots differ")
                warnings.append("LOD pivots differ")
        except Exception as exc:
            checks["LOD Pivot Consistency"] = self._make_check("Info", "Skipped: {0}".format(exc))
        return {"status": "Fail" if warnings else "Pass", "checks": checks, "warnings": warnings, "lod_items": lod_items}

    def find_sockets(self, transform):
        sockets = []
        descendants = cmds.listRelatives(transform, allDescendents=True, fullPath=True, type="transform") or []
        for node in descendants:
            name = self.clean_asset_name(node)
            shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
            has_locator = False
            for shape in shapes:
                try:
                    if cmds.nodeType(shape) == "locator":
                        has_locator = True
                except Exception:
                    pass
            if name.startswith("SOCKET_") or name.startswith("Socket_") or has_locator:
                sockets.append({"name": name, "path": node, "has_locator_shape": has_locator})
        sockets.sort(key=lambda item: item["name"])
        return sockets

    def check_sockets(self, transform, settings):
        checks = {}
        warnings = []
        if not settings.get("socket_enabled"):
            return {"status": "Skipped", "checks": {"Sockets": self._make_check("Pass", "Socket check disabled")}, "warnings": []}
        sockets = self.find_sockets(transform)
        bad_names = []
        locked = []
        for sock in sockets:
            if not sock["name"].startswith("SOCKET_"):
                bad_names.append(sock["name"])
            lock_attrs = self._get_locked_transform_attrs(sock["path"])
            if lock_attrs:
                locked.append("{0}: {1}".format(sock["name"], ", ".join(lock_attrs)))
        if not sockets:
            checks["Sockets"] = self._make_check("Pass", "No sockets found. This is valid for simple static meshes.")
        else:
            checks["Sockets"] = self._make_check("Pass", "{0} socket/locator node(s): {1}".format(len(sockets), ", ".join([s["name"] for s in sockets])))
        if bad_names:
            checks["Socket Naming"] = self._make_check("Fail", "Use SOCKET_* naming: {0}".format(", ".join(bad_names)))
            warnings.append("Socket names should use SOCKET_* prefix")
        else:
            checks["Socket Naming"] = self._make_check("Pass", "Socket names OK")
        if locked:
            checks["Socket Locked Attrs"] = self._make_check("Fail", "; ".join(locked[:3]))
            warnings.append("Socket locked attributes found")
        else:
            checks["Socket Locked Attrs"] = self._make_check("Pass", "No locked socket transform attributes")
        return {"status": "Fail" if warnings else "Pass", "checks": checks, "warnings": warnings, "sockets": sockets}

    # ------------------------------
    # Validation
    # ------------------------------
    def validate_asset(self, transform, settings):
        asset_name = self.clean_asset_name(transform)
        result = {
            "asset_name": asset_name,
            "asset_path": transform,
            "profile": settings.get("profile_name", "Custom"),
            "warnings": [],
            "blocking_issues": [],
            "ready_for_export": True,
            "status": "Ready",
            "m2u_score": 100,
            "checks": {},
            "fix_plan": [],
            "manual_review": [],
            "fixed_actions": [],
            "errors": [],
            "dimensions": {},
            "collision": {"target_name": asset_name, "matches": []},
            "ucx_mesh_validation": [],
            "material_validation": {},
            "uv_validation": {},
            "lod_validation": {},
            "socket_validation": {},
            "export": {"status": "not_run", "message": ""},
        }
        include_desc = settings.get("include_descendant_meshes", True)

        # Naming
        required_prefix = self._sanitize_required_base_prefix(settings.get("required_prefix"), settings)
        sanitized = self.safe_node_name(asset_name)
        import_prefix_stripped = self._strip_import_scene_prefix_before_base_prefix(sanitized, required_prefix)
        missing_prefix = bool(required_prefix) and not self._has_base_prefix(asset_name, required_prefix)
        needs_sanitize = sanitized != asset_name
        has_import_scene_prefix = import_prefix_stripped != sanitized
        if not settings.get("naming_enabled") or settings.get("naming_severity") == "off":
            result["checks"]["Naming"] = self._make_check("Pass", "Naming rule disabled")
        elif missing_prefix or needs_sanitize or has_import_scene_prefix:
            reasons = []
            if missing_prefix:
                reasons.append("missing prefix {0}".format(required_prefix))
            if needs_sanitize:
                reasons.append("contains invalid characters or namespace")
            if has_import_scene_prefix:
                reasons.append("scene/import prefix before base mesh prefix")
            result["checks"]["Naming"] = self._make_check("Fail", ", ".join(reasons))
            self._add_issue(result, settings.get("naming_severity", "warning"), "Naming issue: {0}".format(", ".join(reasons)))
            if settings.get("fix_rename") or settings.get("sanitize_names"):
                result["fix_plan"].append("Rename/sanitize asset name")
        else:
            result["checks"]["Naming"] = self._make_check("Pass", "Name matches pipeline rule")

        # Polycount
        polycount = self.get_polycount_for_transform(transform, include_desc)
        max_poly = settings.get("max_polycount", 0)
        if max_poly < 0:
            result["checks"]["Polycount"] = self._make_check("Fail", "Max polycount cannot be negative")
            self._add_issue(result, "blocking", "Max polycount cannot be negative")
        elif polycount <= max_poly:
            result["checks"]["Polycount"] = self._make_check("Pass", "{0} / {1}".format(polycount, max_poly))
        else:
            result["checks"]["Polycount"] = self._make_check("Fail", "{0} / {1}".format(polycount, max_poly))
            self._add_issue(result, settings.get("polycount_severity", "blocking"), "Polycount exceeds maximum: {0} > {1}".format(polycount, max_poly))
        result["polycount"] = polycount

        # Freeze
        if not settings.get("freeze_required"):
            result["checks"]["Freeze Transform"] = self._make_check("Pass", "Freeze check disabled")
        elif self.has_freeze_issue(transform):
            result["checks"]["Freeze Transform"] = self._make_check("Fail", "Transform values are not frozen")
            self._add_issue(result, settings.get("freeze_severity", "blocking"), "Freeze Transform requirement not satisfied")
            if settings.get("fix_freeze"):
                result["fix_plan"].append("Freeze Transform")
        else:
            result["checks"]["Freeze Transform"] = self._make_check("Pass", "Transform values are frozen")

        # History
        if not settings.get("history_required"):
            result["checks"]["History"] = self._make_check("Pass", "History check disabled")
        else:
            history_issue, history_nodes = self.has_history_issue(transform)
            if history_issue:
                preview = ", ".join(history_nodes[:5])
                result["checks"]["History"] = self._make_check("Fail", "Construction history found: {0}".format(preview))
                self._add_issue(result, settings.get("history_severity", "warning"), "Construction history found: {0}".format(preview))
                if settings.get("fix_history"):
                    result["fix_plan"].append("Delete Construction History")
            else:
                result["checks"]["History"] = self._make_check("Pass", "No construction history found")

        # Zero thickness
        if not settings.get("zero_thickness_enabled"):
            result["checks"]["Zero Thickness"] = self._make_check("Pass", "Zero thickness check disabled")
        else:
            width, height, depth = self.get_bbox_sizes(transform)
            result["dimensions"] = {"width_cm": width, "height_cm": height, "depth_cm": depth}
            zero_tol = max(0.0, settings.get("zero_thickness_tolerance_cm", 0.001))
            thin_axes = []
            if width <= zero_tol:
                thin_axes.append("width")
            if height <= zero_tol:
                thin_axes.append("height")
            if depth <= zero_tol:
                thin_axes.append("depth")
            if thin_axes:
                result["checks"]["Zero Thickness"] = self._make_check("Fail", "Near-zero axis: {0}".format(", ".join(thin_axes)))
                self._add_issue(result, settings.get("zero_thickness_severity", "warning"), "Near-zero thickness axis detected: {0}".format(", ".join(thin_axes)))
                result["manual_review"].append("Check zero-thickness geometry manually")
            else:
                result["checks"]["Zero Thickness"] = self._make_check("Pass", "W/H/D: {0}".format(self._format_float_list([width, height, depth])))

        # Dimension
        if not settings.get("dimension_enabled"):
            result["checks"]["Dimensions"] = self._make_check("Pass", "Dimension check disabled")
        else:
            width, height, depth = self.get_bbox_sizes(transform)
            result["dimensions"] = {"width_cm": width, "height_cm": height, "depth_cm": depth}
            expected = [settings.get("expected_width_cm", 0.0), settings.get("expected_height_cm", 0.0), settings.get("expected_depth_cm", 0.0)]
            actual = [width, height, depth]
            tolerance = max(0.0, settings.get("dimension_tolerance_cm", 0.5))
            deltas = [abs(actual[i] - expected[i]) for i in range(3)]
            if all(delta <= tolerance for delta in deltas):
                result["checks"]["Dimensions"] = self._make_check("Pass", "Actual W/H/D: {0}".format(self._format_float_list(actual)))
            else:
                result["checks"]["Dimensions"] = self._make_check("Fail", "Actual {0} | Expected {1} | Delta {2}".format(self._format_float_list(actual), self._format_float_list(expected), self._format_float_list(deltas)))
                self._add_issue(result, settings.get("dimension_severity", "blocking"), "Dimensions do not match expected size")
                result["manual_review"].append("Resize asset or adjust profile dimensions")

        # Pivot
        if not settings.get("pivot_enabled"):
            result["checks"]["Pivot"] = self._make_check("Pass", "Pivot check disabled")
        else:
            try:
                actual = self.get_pivot_position(transform)
                expected_pivot = self.get_target_pivot_position(transform, settings.get("pivot_target"), settings.get("front_axis"))
                tolerance = max(0.0, settings.get("pivot_tolerance_cm", 0.5))
                deltas = [abs(actual[0] - expected_pivot[0]), abs(actual[1] - expected_pivot[1]), abs(actual[2] - expected_pivot[2])]
                if all(delta <= tolerance for delta in deltas):
                    result["checks"]["Pivot"] = self._make_check("Pass", settings.get("pivot_target"))
                else:
                    result["checks"]["Pivot"] = self._make_check("Fail", "Actual ({0}), expected ({1}), delta ({2})".format(self._format_float_list(actual), self._format_float_list(expected_pivot), self._format_float_list(deltas)))
                    self._add_issue(result, settings.get("pivot_severity", "warning"), "Pivot does not match target: {0}".format(settings.get("pivot_target")))
                    if settings.get("fix_pivot"):
                        result["fix_plan"].append("Move pivot to {0}".format(settings.get("pivot_target")))
            except Exception as exc:
                result["checks"]["Pivot"] = self._make_check("Fail", str(exc))
                self._add_issue(result, settings.get("pivot_severity", "warning"), "Pivot check error: {0}".format(exc))

        # Grid
        if not settings.get("grid_enabled"):
            result["checks"]["Grid"] = self._make_check("Pass", "Grid check disabled")
        else:
            step = settings.get("grid_step_cm", 10.0)
            if step <= 0.0:
                result["checks"]["Grid"] = self._make_check("Fail", "Grid step must be greater than zero")
                self._add_issue(result, "blocking", "Grid step must be greater than zero")
            else:
                bb = self.get_world_bbox(transform)
                width, height, depth = self.get_bbox_sizes(transform)
                grid_messages = []
                failed = False
                if settings.get("grid_check_size_multiple"):
                    failed_size = []
                    for label, value in [("width", width), ("height", height), ("depth", depth)]:
                        if not self._is_multiple_of_step(value, step):
                            failed_size.append("{0}={1:.3f}".format(label, value))
                    if failed_size:
                        failed = True
                        grid_messages.append("size not multiple of {0}: {1}".format(step, ", ".join(failed_size)))
                        result["manual_review"].append("Asset size is not a grid multiple; moving cannot fix size")
                if settings.get("grid_check_bounds_snap"):
                    failed_bounds = []
                    for label in ["minX", "minY", "minZ", "maxX", "maxY", "maxZ"]:
                        if not self._is_multiple_of_step(bb[label], step):
                            failed_bounds.append("{0}={1:.3f}".format(label, bb[label]))
                    if failed_bounds:
                        failed = True
                        grid_messages.append("bounds not snapped: {0}".format(", ".join(failed_bounds[:6])))
                        if settings.get("snap_bounds_min") or settings.get("snap_pivot_to_grid"):
                            result["fix_plan"].append("Snap asset position to grid")
                if failed:
                    result["checks"]["Grid"] = self._make_check("Fail", " | ".join(grid_messages))
                    self._add_issue(result, settings.get("grid_severity", "warning"), "Grid rule failed: {0}".format(" | ".join(grid_messages)))
                else:
                    result["checks"]["Grid"] = self._make_check("Pass", "Bounds and size match grid step {0}".format(step))

        # Visibility / locked attributes
        if self._is_transform_visible_in_hierarchy(transform):
            result["checks"]["Visibility"] = self._make_check("Pass", "Visible in hierarchy")
        else:
            result["checks"]["Visibility"] = self._make_check("Fail", "Transform or parent hierarchy is hidden")
            result["warnings"].append("Transform or parent hierarchy is hidden")
            if settings.get("fix_make_visible"):
                result["fix_plan"].append("Make selected asset visible")
        locked_attrs = self._get_locked_transform_attrs(transform)
        if locked_attrs:
            result["checks"]["Locked Attributes"] = self._make_check("Fail", "Locked attrs: {0}".format(", ".join(locked_attrs)))
            result["warnings"].append("Locked transform attributes: {0}".format(", ".join(locked_attrs)))
            if settings.get("fix_unlock_attrs"):
                result["fix_plan"].append("Unlock transform attributes")
        else:
            result["checks"]["Locked Attributes"] = self._make_check("Pass", "No locked transform attributes")

        # Collision
        if not settings.get("collision_enabled") or settings.get("collision_requirement") == "Off":
            result["checks"]["Collision"] = self._make_check("Pass", "Collision check disabled")
        else:
            target_name = self._get_collision_target_name(asset_name, settings)
            result["collision"]["target_name"] = target_name
            result["collision"]["searched_targets"] = self.get_collision_target_candidates(target_name, required_prefix=settings.get("required_prefix")) if target_name else []
            matches = self.find_ucx_matches(target_name, settings.get("accept_multiple_ucx_parts", True), required_prefix=settings.get("required_prefix"), settings=settings) if target_name else []
            result["collision"]["matches"] = matches
            if (matches and self._should_sync_ucx_names_on_rename(settings)):
                preview_name = self._preview_renamed_asset_name(asset_name, settings)
                if preview_name != asset_name:
                    result["fix_plan"].append("Sync matching collider proxy names to renamed base asset")
            requirement = settings.get("collision_requirement")
            if requirement == "Collider required" and not matches:
                result["checks"]["Collision"] = self._make_check("Fail", "Collider proxy required but no match found for {0}".format(target_name))
                self._add_issue(result, settings.get("collision_severity", "warning"), "Missing required collider proxy for target: {0}".format(target_name))
                result["manual_review"].append("Create COL_ collider proxy mesh or use Create Box Collider helper")
            elif requirement == "No custom collider allowed" and matches:
                result["checks"]["Collision"] = self._make_check("Fail", "Custom collider proxy is not allowed but {0} match(es) found".format(len(matches)))
                self._add_issue(result, settings.get("collision_severity", "warning"), "Custom collider proxy is not allowed")
            else:
                result["checks"]["Collision"] = self._make_check("Pass", "{0} matching collider proxy mesh(es) found".format(len(matches)))
            if matches and settings.get("validate_ucx_meshes") and settings.get("ucx_mesh_validation_severity") != "off":
                for match in matches:
                    ucx_result = self.validate_ucx_mesh(match.get("path"), settings)
                    result["ucx_mesh_validation"].append(ucx_result)
                    if ucx_result.get("status") == "Fail":
                        self._add_issue(
                            result,
                            settings.get("ucx_mesh_validation_severity", "warning"),
                            "Collider proxy validation failed for {0}: {1}".format(ucx_result.get("name"), ", ".join(ucx_result.get("failed_checks", [])))
                        )

        # LOD / Material / UV / Socket
        result["lod_validation"] = self.check_lods(transform, settings)
        if result["lod_validation"].get("status") == "Fail":
            self._add_issue(result, settings.get("lod_severity", "warning"), "; ".join(result["lod_validation"].get("warnings", [])))
        result["material_validation"] = self.check_materials(transform, settings)
        if result["material_validation"].get("status") == "Fail":
            self._add_issue(result, settings.get("material_severity", "warning"), "; ".join(result["material_validation"].get("warnings", [])))
        result["uv_validation"] = self.check_uvs(transform, settings)
        if result["uv_validation"].get("status") == "Fail":
            self._add_issue(result, settings.get("uv_severity", "warning"), "; ".join(result["uv_validation"].get("warnings", [])))
        result["socket_validation"] = self.check_sockets(transform, settings)
        if result["socket_validation"].get("status") == "Fail":
            self._add_issue(result, settings.get("socket_severity", "warning"), "; ".join(result["socket_validation"].get("warnings", [])))

        # Status and score
        result["ready_for_export"] = len(result["blocking_issues"]) == 0
        if result["blocking_issues"]:
            result["status"] = "Blocked"
        elif result["warnings"]:
            result["status"] = "Warning"
        else:
            result["status"] = "Ready"
        result["m2u_score"] = self.calculate_score(result)
        return result

    def calculate_score(self, result):
        score = 100
        blocking = len(result.get("blocking_issues", []))
        warnings = len(result.get("warnings", []))
        score -= blocking * 18
        score -= warnings * 5
        # Additional penalty for failed checks, capped.
        failed_checks = 0
        for data in result.get("checks", {}).values():
            if isinstance(data, dict) and data.get("status") == "Fail":
                failed_checks += 1
        score -= failed_checks * 3
        if score < 0:
            score = 0
        if score > 100:
            score = 100
        return int(score)

    def analyze_selected_assets(self, settings):
        transforms = self.get_selected_transforms(settings)
        results = []
        for transform in transforms:
            try:
                results.append(self.validate_asset(transform, settings))
            except Exception as exc:
                results.append({
                    "asset_name": self.clean_asset_name(transform),
                    "asset_path": transform,
                    "status": "Error",
                    "ready_for_export": False,
                    "m2u_score": 0,
                    "warnings": [],
                    "blocking_issues": [str(exc)],
                    "checks": {},
                    "fix_plan": [],
                    "manual_review": [],
                    "errors": [traceback.format_exc()],
                    "export": {"status": "not_run", "message": ""},
                })
        return results

    # ------------------------------
    # Fixes
    # ------------------------------
    def _create_backup(self, transform, settings):
        if not settings.get("make_backup"):
            return None
        backup_name = self._unique_name(self.clean_asset_name(transform) + "_M2U_BACKUP")
        try:
            duplicate = cmds.duplicate(transform, name=backup_name, returnRootsOnly=True)[0]
            if settings.get("hide_backups"):
                try:
                    cmds.setAttr(duplicate + ".visibility", False)
                except Exception:
                    pass
            return duplicate
        except Exception:
            return None

    def _preview_renamed_asset_name(self, current_name, settings):
        clean = self.safe_node_name(current_name) if settings.get("sanitize_names") else self.clean_asset_name(current_name)
        prefix = self._sanitize_required_base_prefix(settings.get("required_prefix"), settings)

        # Maya imports can prefix objects with the source scene name. If a valid render
        # mesh prefix exists later in the name, keep the real asset name and drop the
        # imported scene prefix.
        clean = self._strip_import_scene_prefix_before_base_prefix(clean, prefix)

        # Safety guard: base/render assets must never be renamed to COL_/TRG_/UCX_.
        # Those prefixes are reserved only for separate Unity collider proxy meshes.
        if self._is_collider_proxy_name(clean, settings):
            clean = self._remove_collider_proxy_prefix(clean, settings)

        if settings.get("fix_rename") and prefix and not self._has_base_prefix(clean, prefix):
            clean = prefix + clean
        return clean

    def _rename_asset(self, transform, settings):
        current = self.clean_asset_name(transform)
        clean = self._preview_renamed_asset_name(current, settings)
        clean = self._unique_name(clean)
        if clean != current:
            return cmds.rename(transform, clean)
        return transform

    def _should_sync_ucx_names_on_rename(self, settings):
        return bool(
            settings.get("sync_ucx_names_on_rename", True)
            and settings.get("fix_rename", True)
            and settings.get("collision_enabled", True)
            and settings.get("collision_requirement") == "Collider required"
            and settings.get("collision_match_mode") == "Base asset name"
        )

    def _expected_synced_ucx_name(self, ucx_name, old_base_name, new_base_name, settings):
        proxy_clean = self.clean_asset_name(ucx_name)
        proxy_key = self._collision_compare_key(proxy_clean)
        candidates = self.get_collision_target_candidates(old_base_name, required_prefix=settings.get("required_prefix"))
        candidates = sorted(candidates, key=lambda item: len(item or ""), reverse=True)
        for candidate in candidates:
            candidate_key = self._collision_compare_key(candidate)
            for prefix in self._collider_prefixes(settings):
                pattern = "{0}{1}".format(prefix.lower(), candidate_key)
                if proxy_key == pattern:
                    return "{0}{1}".format(prefix, new_base_name)
                if proxy_key.startswith(pattern + "_"):
                    original_pattern_len = len("{0}{1}".format(prefix, candidate))
                    suffix = proxy_clean[original_pattern_len:]
                    return "{0}{1}{2}".format(prefix, new_base_name, suffix)
        return None

    def _sync_ucx_names_to_base(self, old_base_name, new_base_name, old_ucx_matches, settings):
        actions = []
        if not self._should_sync_ucx_names_on_rename(settings):
            return actions
        if not old_ucx_matches:
            return actions
        if old_base_name == new_base_name:
            return actions

        for match in old_ucx_matches:
            path = match.get("path") if isinstance(match, dict) else match
            if not path or not cmds.objExists(path):
                continue
            old_ucx_name = self.clean_asset_name(path)
            desired = self._expected_synced_ucx_name(old_ucx_name, old_base_name, new_base_name, settings)
            if not desired or desired == old_ucx_name:
                continue
            safe_desired = self.safe_node_name(desired)
            final_name = self._unique_name(safe_desired)
            try:
                renamed = cmds.rename(path, final_name)
                actions.append("Synced collider proxy name {0} -> {1}".format(old_ucx_name, self.clean_asset_name(renamed)))
            except Exception as exc:
                actions.append("Collider proxy name sync failed for {0}: {1}".format(old_ucx_name, exc))
        return actions

    def apply_safe_fixes(self, results, settings):
        fixed_results = []
        for result in results:
            transform = result.get("asset_path")
            if not transform or not cmds.objExists(transform):
                result.setdefault("errors", []).append("Asset no longer exists in scene")
                fixed_results.append(result)
                continue
            actions = []
            try:
                backup = self._create_backup(transform, settings)
                if backup:
                    actions.append("Created backup: {0}".format(self.clean_asset_name(backup)))

                if settings.get("fix_unlock_attrs"):
                    unlocked = self._unlock_transform_attrs(transform)
                    if unlocked:
                        actions.append("Unlocked attrs: {0}".format(", ".join(unlocked)))

                if settings.get("fix_make_visible"):
                    try:
                        cmds.setAttr(transform + ".visibility", True)
                        actions.append("Made asset visible")
                    except Exception:
                        pass

                old_name = self.clean_asset_name(transform)
                old_ucx_matches = []
                if self._should_sync_ucx_names_on_rename(settings):
                    try:
                        old_ucx_matches = self.find_ucx_matches(
                            old_name,
                            settings.get("accept_multiple_ucx_parts", True),
                            required_prefix=settings.get("required_prefix"),
                            settings=settings
                        )
                    except Exception:
                        old_ucx_matches = []

                transform = self._rename_asset(transform, settings)
                new_name = self.clean_asset_name(transform)
                if new_name != old_name:
                    actions.append("Renamed {0} -> {1}".format(old_name, new_name))
                    actions.extend(self._sync_ucx_names_to_base(old_name, new_name, old_ucx_matches, settings))

                if settings.get("fix_history"):
                    history_issue, _ = self.has_history_issue(transform)
                    if history_issue:
                        try:
                            cmds.delete(transform, constructionHistory=True)
                            actions.append("Deleted construction history")
                        except Exception as exc:
                            actions.append("History delete failed: {0}".format(exc))

                if settings.get("fix_freeze"):
                    if self.has_freeze_issue(transform):
                        try:
                            cmds.makeIdentity(transform, apply=True, translate=True, rotate=True, scale=True, normal=False)
                            actions.append("Freeze Transform applied")
                        except Exception as exc:
                            actions.append("Freeze failed: {0}".format(exc))

                if settings.get("fix_pivot") and settings.get("pivot_enabled"):
                    try:
                        target = self.get_target_pivot_position(transform, settings.get("pivot_target"), settings.get("front_axis"))
                        cmds.xform(transform, ws=True, pivots=target)
                        actions.append("Pivot moved to {0}".format(settings.get("pivot_target")))
                    except Exception as exc:
                        actions.append("Pivot move failed: {0}".format(exc))

                if settings.get("grid_enabled") and (settings.get("snap_bounds_min") or settings.get("snap_pivot_to_grid")):
                    step = settings.get("grid_step_cm", 10.0)
                    if step > 0.0:
                        if settings.get("snap_bounds_min"):
                            bb = self.get_world_bbox(transform)
                            target_min = [self._snap_value(bb["minX"], step), self._snap_value(bb["minY"], step), self._snap_value(bb["minZ"], step)]
                            delta = [target_min[0] - bb["minX"], target_min[1] - bb["minY"], target_min[2] - bb["minZ"]]
                            try:
                                cmds.move(delta[0], delta[1], delta[2], transform, relative=True, worldSpace=True)
                                actions.append("Snapped bounds min to grid")
                            except Exception as exc:
                                actions.append("Bounds snap failed: {0}".format(exc))
                        elif settings.get("snap_pivot_to_grid"):
                            pivot = self.get_pivot_position(transform)
                            target = [self._snap_value(pivot[0], step), self._snap_value(pivot[1], step), self._snap_value(pivot[2], step)]
                            delta = [target[0] - pivot[0], target[1] - pivot[1], target[2] - pivot[2]]
                            try:
                                cmds.move(delta[0], delta[1], delta[2], transform, relative=True, worldSpace=True)
                                actions.append("Snapped pivot to grid")
                            except Exception as exc:
                                actions.append("Pivot snap failed: {0}".format(exc))

                refreshed = self.validate_asset(transform, settings)
                refreshed["fixed_actions"] = actions
                fixed_results.append(refreshed)
            except Exception as exc:
                result.setdefault("errors", []).append(traceback.format_exc())
                result.setdefault("fixed_actions", []).append("Fix failed: {0}".format(exc))
                fixed_results.append(result)
        return fixed_results

    # ------------------------------
    # Visual helpers
    # ------------------------------
    def create_pivot_preview(self, transform, settings):
        target = self.get_target_pivot_position(transform, settings.get("pivot_target"), settings.get("front_axis"))
        name = self._unique_name("M2U_PIVOT_PREVIEW_{0}".format(self.clean_asset_name(transform)))
        loc = cmds.spaceLocator(name=name)[0]
        cmds.xform(loc, ws=True, t=target)
        try:
            cmds.setAttr(loc + ".localScaleX", 12)
            cmds.setAttr(loc + ".localScaleY", 12)
            cmds.setAttr(loc + ".localScaleZ", 12)
        except Exception:
            pass
        return loc

    def delete_pivot_preview_locators(self):
        """Delete only M2U-created pivot preview locators."""
        deleted = 0
        try:
            nodes = cmds.ls("M2U_PIVOT_PREVIEW_*", long=True, type="transform") or []
            for node in nodes:
                if not node or not cmds.objExists(node):
                    continue
                if not self.clean_asset_name(node).startswith("M2U_PIVOT_PREVIEW_"):
                    continue
                try:
                    cmds.delete(node)
                    deleted += 1
                except Exception:
                    pass
        except Exception:
            pass
        return deleted

    def _get_shading_groups_for_transform(self, node):
        shading_groups = []
        seen = set()
        try:
            shapes = self.get_mesh_shapes_under_transform(node, include_descendants=True)
            for shape in shapes:
                groups = cmds.listConnections(shape, type="shadingEngine") or []
                for group in groups:
                    if group and group not in seen:
                        shading_groups.append(group)
                        seen.add(group)
        except Exception:
            pass
        return shading_groups

    def _remember_preview_material_assignment(self, node):
        try:
            if not node or not cmds.objExists(node):
                return
            key = cmds.ls(node, long=True)[0]
            if key in self.preview_material_assignments:
                return
            self.preview_material_assignments[key] = self._get_shading_groups_for_transform(node)
        except Exception:
            pass

    def reset_collision_preview_materials(self, result):
        """Restore Collider Proxy preview materials captured during this Maya session."""
        restored = 0
        matches = result.get("collision", {}).get("matches", []) or []
        for match in matches:
            path = match.get("path")
            if not path or not cmds.objExists(path):
                continue
            try:
                key = cmds.ls(path, long=True)[0]
            except Exception:
                key = path
            groups = self.preview_material_assignments.get(key)
            if not groups:
                continue
            for sg in groups:
                if sg and cmds.objExists(sg):
                    try:
                        cmds.sets(path, e=True, forceElement=sg)
                        restored += 1
                        break
                    except Exception:
                        pass
        return restored

    def _get_or_create_material(self, name, rgb):
        if cmds.objExists(name):
            return name
        mat = cmds.shadingNode("lambert", asShader=True, name=name)
        try:
            cmds.setAttr(mat + ".color", rgb[0], rgb[1], rgb[2], type="double3")
        except Exception:
            pass
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=mat + "SG")
        try:
            cmds.connectAttr(mat + ".outColor", sg + ".surfaceShader", force=True)
        except Exception:
            pass
        return mat

    def _assign_material(self, node, material_name):
        sg = material_name + "SG"
        if not cmds.objExists(sg):
            return
        try:
            cmds.sets(node, e=True, forceElement=sg)
        except Exception:
            pass

    def colorize_collision_preview(self, result):
        green = self._get_or_create_material("M2Unity_Collider_OK_Green", (0.2, 0.8, 0.2))
        red = self._get_or_create_material("M2Unity_Collider_Error_Red", (0.9, 0.15, 0.1))
        matches = result.get("collision", {}).get("matches", []) or []
        failed_names = set()
        for ucx in result.get("ucx_mesh_validation", []) or []:
            if ucx.get("status") == "Fail":
                failed_names.add(ucx.get("name"))
        for match in matches:
            mat = red if match.get("name") in failed_names else green
            self._remember_preview_material_assignment(match.get("path"))
            self._assign_material(match.get("path"), mat)
        return len(matches)

    def select_asset_and_ucx(self, result):
        paths = []
        if result.get("asset_path") and cmds.objExists(result.get("asset_path")):
            paths.append(result.get("asset_path"))
        for match in result.get("collision", {}).get("matches", []) or []:
            path = match.get("path")
            if path and cmds.objExists(path):
                paths.append(path)
        if paths:
            cmds.select(paths, replace=True)
        return paths

    def isolate_asset_and_ucx(self, result):
        paths = self.select_asset_and_ucx(result)
        try:
            panel = cmds.getPanel(withFocus=True)
            if panel and cmds.getPanel(typeOf=panel) == "modelPanel":
                cmds.isolateSelect(panel, state=True)
                cmds.isolateSelect(panel, addSelected=True)
        except Exception:
            pass
        return paths

    def create_box_ucx_for_asset(self, transform, settings):
        asset_name = self.clean_asset_name(transform)
        target_name = self._get_collision_target_name(asset_name, settings) or asset_name
        base_name = "COL_{0}_01".format(target_name)
        proxy_name = self._unique_name(base_name)
        width, height, depth = self.get_bbox_sizes(transform)
        center = self.get_bbox_center(transform)
        cube = cmds.polyCube(name=proxy_name, width=width, height=height, depth=depth)[0]
        cmds.xform(cube, ws=True, t=center)
        try:
            cmds.makeIdentity(cube, apply=True, translate=True, rotate=True, scale=True, normal=False)
            cmds.delete(cube, constructionHistory=True)
        except Exception:
            pass
        return cube

    # ------------------------------
    # Export / reports
    # ------------------------------
    def ensure_fbx_plugin(self):
        try:
            if not cmds.pluginInfo("fbxmaya", q=True, loaded=True):
                cmds.loadPlugin("fbxmaya")
            return True
        except Exception:
            return False

    def export_transform_to_fbx(self, transform, export_path, collision_paths=None, triangulate=False):
        collision_paths = collision_paths or []
        if not self.ensure_fbx_plugin():
            return False, "FBX plugin could not be loaded"
        try:
            old_selection = cmds.ls(selection=True, long=True) or []
            export_nodes = [transform] + [p for p in collision_paths if p and cmds.objExists(p)]
            cmds.select(export_nodes, replace=True)
            try:
                mel.eval('FBXResetExport;')
            except Exception:
                pass
            try:
                mel.eval('FBXExportSmoothingGroups -v true;')
                mel.eval('FBXExportTangents -v true;')
                mel.eval('FBXExportSmoothMesh -v true;')
                mel.eval('FBXExportInstances -v false;')
                mel.eval('FBXExportTriangulate -v {0};'.format('true' if triangulate else 'false'))
                mel.eval('FBXExportUpAxis y;')
            except Exception:
                pass
            export_dir = os.path.dirname(export_path)
            if export_dir and not os.path.isdir(export_dir):
                os.makedirs(export_dir)
            cmds.file(export_path, force=True, options="v=0;", type="FBX export", preserveReferences=True, exportSelected=True)
            if old_selection:
                cmds.select(old_selection, replace=True)
            else:
                cmds.select(clear=True)
            return True, export_path
        except Exception as exc:
            return False, traceback.format_exc()

    def should_export_result(self, result, settings):
        if result.get("status") == "Blocked":
            return not settings.get("skip_blocked_assets", True)
        if result.get("status") == "Warning":
            return settings.get("export_warning_assets", True)
        if result.get("status") == "Ready":
            return settings.get("export_ready_assets", True)
        return False

    def export_results(self, results, settings, export_folder):
        export_summary = {
            "export_folder": export_folder,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "exported_assets": 0,
            "skipped_assets": 0,
            "failed_exports": 0,
            "json_report": "",
            "html_report": "",
            "unity_postprocessor_script": "",
            "report_errors": [],
        }
        for result in results:
            transform = result.get("asset_path")
            if not transform or not cmds.objExists(transform):
                result["export"] = {"status": "failed", "message": "Asset path no longer exists"}
                export_summary["failed_exports"] += 1
                continue

            # Always refresh Collider Proxy matching at export time. This prevents stale analysis
            # from exporting the base mesh alone after the user creates or renames Collider Proxy.
            collision_paths = []
            if settings.get("collision_enabled") and settings.get("collision_requirement") != "Off":
                target_name = self._get_collision_target_name(result.get("asset_name"), settings)
                matches = self.find_ucx_matches(target_name, settings.get("accept_multiple_ucx_parts", True), required_prefix=settings.get("required_prefix"), settings=settings) if target_name else []
                result.setdefault("collision", {})["target_name"] = target_name
                result["collision"]["searched_targets"] = self.get_collision_target_candidates(target_name, required_prefix=settings.get("required_prefix")) if target_name else []
                result["collision"]["matches"] = matches
                collision_paths = [m.get("path") for m in matches if m.get("path") and cmds.objExists(m.get("path"))]
                if settings.get("collision_requirement") == "Collider required" and not collision_paths:
                    result["export"] = {
                        "status": "failed",
                        "message": "Collider proxy required but no matching COL_/TRG_ proxy was found at export time. Searched targets: {0}".format(
                            ", ".join(result["collision"].get("searched_targets", []))
                        ),
                        "included_collider_proxy": 0,
                    }
                    export_summary["failed_exports"] += 1
                    continue

            if not self.should_export_result(result, settings):
                result["export"] = {"status": "skipped", "message": "Skipped by export rules", "included_collider_proxy": len(collision_paths)}
                export_summary["skipped_assets"] += 1
                continue

            asset_file = self.safe_filename(result.get("asset_name")) + ".fbx"
            export_path = os.path.join(export_folder, asset_file).replace("\\", "/")
            success, message = self.export_transform_to_fbx(
                transform,
                export_path,
                collision_paths=collision_paths,
                triangulate=settings.get("triangulate_export"),
            )
            if success:
                result["export"] = {"status": "exported", "message": message, "path": export_path, "included_collider_proxy": len(collision_paths)}
                export_summary["exported_assets"] += 1
            else:
                result["export"] = {"status": "failed", "message": message, "included_collider_proxy": len(collision_paths)}
                export_summary["failed_exports"] += 1

        # Reports must never turn a successful FBX export into a false Export Failed dialog.
        for report_key, enabled_key, writer in [
            ("json_report", "write_json_report", self.write_json_report),
            ("html_report", "write_html_report", self.write_html_report),
        ]:
            if settings.get(enabled_key):
                try:
                    export_summary[report_key] = writer(export_folder, settings, results, export_summary)
                except Exception:
                    export_summary["report_errors"].append("{0}: {1}".format(report_key, traceback.format_exc()))
        if settings.get("write_unreal_import_script"):
            try:
                export_summary["unity_postprocessor_script"] = self.write_unreal_import_script(export_folder, results)
            except Exception:
                export_summary["report_errors"].append("unity_postprocessor_script: {0}".format(traceback.format_exc()))
        return export_summary

    def write_json_report(self, export_folder, settings, results, export_summary):
        path = os.path.join(export_folder, "M2Unity_Pipeline_Report.json")
        payload = {
            "tool": M2U_PIPELINE_WINDOW_TITLE,
            "build": M2U_PIPELINE_BUILD_ID,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "settings": settings,
            "export_summary": export_summary,
            "results": results,
        }
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, sort_keys=True, ensure_ascii=False)
        return path.replace("\\", "/")

    def _html_badge(self, text):
        text = text or "Unknown"
        key = text.lower()
        cls = "badge-info"
        if "ready" in key or "pass" in key or "exported" in key:
            cls = "badge-pass"
        elif "warn" in key or "skipped" in key:
            cls = "badge-warning"
        elif "block" in key or "fail" in key or "error" in key:
            cls = "badge-fail"
        return '<span class="badge {0}">{1}</span>'.format(cls, html_escape(text))

    def _html_check_rows(self, checks):
        rows = []
        for name in sorted((checks or {}).keys()):
            data = checks.get(name) or {}
            rows.append("<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>".format(
                html_escape(name), self._html_badge(data.get("status", "Info")), html_escape(data.get("reason", ""))
            ))
        return "\n".join(rows)

    def write_html_report(self, export_folder, settings, results, export_summary):
        path = os.path.join(export_folder, "M2Unity_Pipeline_Report.html")
        ready = sum(1 for r in results if r.get("status") == "Ready")
        warning = sum(1 for r in results if r.get("status") == "Warning")
        blocked = sum(1 for r in results if r.get("status") == "Blocked")
        cards = []
        for r in results:
            issues = []
            for issue in r.get("blocking_issues", []) or []:
                issues.append('<li class="block">{0}</li>'.format(html_escape(issue)))
            for issue in r.get("warnings", []) or []:
                issues.append('<li class="warn">{0}</li>'.format(html_escape(issue)))
            if not issues:
                issues.append('<li class="ok">No issues found.</li>')
            fix_plan = r.get("fix_plan", []) or []
            fix_html = "".join(["<li>{0}</li>".format(html_escape(x)) for x in fix_plan]) or "<li>No automatic fix planned.</li>"
            fixed_actions = r.get("fixed_actions", []) or []
            fixed_html = "".join(["<li>{0}</li>".format(html_escape(x)) for x in fixed_actions]) or "<li>No fix actions recorded.</li>"
            collisions = r.get("collision", {}).get("matches", []) or []
            coll_html = "".join(["<li>{0}</li>".format(html_escape(c.get("name", ""))) for c in collisions]) or "<li>No matching Collider Proxy mesh.</li>"
            searched = r.get("collision", {}).get("searched_targets", []) or []
            searched_html = "".join(["<li>{0}</li>".format(html_escape(x)) for x in searched]) or "<li>No target candidates recorded.</li>"
            export = r.get("export", {}) or {}
            card_template = '''
            <section class="asset-card">
                <div class="asset-head">
                    <div>
                        <h2>__ASSET__</h2>
                        <p>__PATH__</p>
                    </div>
                    <div class="score"><strong>__SCORE__</strong><span>M2Unity Score</span></div>
                </div>
                <div class="meta">
                    __STATUS__
                    __EXPORT_STATUS__
                    <span>Polycount: __POLYCOUNT__</span>
                    <span>Profile: __PROFILE__</span>
                    <span>Included Collider: __INCLUDED_COL__</span>
                </div>
                <h3>Issues</h3>
                <ul>__ISSUES__</ul>
                <h3>Fix Plan</h3>
                <ul>__FIX_PLAN__</ul>
                <h3>Fixed Actions</h3>
                <ul>__FIXED_ACTIONS__</ul>
                <h3>Collider Proxy Matches</h3>
                <ul>__COLLISION__</ul>
                <h3>Collider Target Candidates</h3>
                <ul>__SEARCHED_TARGETS__</ul>
                <h3>Core Checks</h3>
                <table><thead><tr><th>Check</th><th>Status</th><th>Reason</th></tr></thead><tbody>__CHECKS__</tbody></table>
                <h3>LOD / Material Slot / UV / Socket Readiness</h3>
                <table><thead><tr><th>Check</th><th>Status</th><th>Reason</th></tr></thead><tbody>__LOD____MATERIAL____UV____SOCKET__</tbody></table>
            </section>
            '''
            replacements = {
                "__ASSET__": html_escape(r.get("asset_name", "UnnamedAsset")),
                "__PATH__": html_escape(r.get("asset_path", "")),
                "__SCORE__": html_escape(str(r.get("m2u_score", 0))),
                "__STATUS__": self._html_badge(r.get("status", "Unknown")),
                "__EXPORT_STATUS__": self._html_badge(export.get("status", "not_run")),
                "__POLYCOUNT__": html_escape(str(r.get("polycount", ""))),
                "__PROFILE__": html_escape(r.get("profile", "")),
                "__INCLUDED_COL__": html_escape(str(export.get("included_collider_proxy", 0))),
                "__ISSUES__": "".join(issues),
                "__FIX_PLAN__": fix_html,
                "__FIXED_ACTIONS__": fixed_html,
                "__COLLISION__": coll_html,
                "__SEARCHED_TARGETS__": searched_html,
                "__CHECKS__": self._html_check_rows(r.get("checks", {})),
                "__LOD__": self._html_check_rows((r.get("lod_validation") or {}).get("checks", {})),
                "__MATERIAL__": self._html_check_rows((r.get("material_validation") or {}).get("checks", {})),
                "__UV__": self._html_check_rows((r.get("uv_validation") or {}).get("checks", {})),
                "__SOCKET__": self._html_check_rows((r.get("socket_validation") or {}).get("checks", {})),
            }
            for key, value in replacements.items():
                card_template = card_template.replace(key, value)
            cards.append(card_template)
        html = '''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>M2Unity Pipeline Report</title>
<style>
:root { --bg:#0f1117; --panel:#171b24; --panel2:#1f2530; --text:#e8edf6; --muted:#9aa4b2; --green:#3ddc97; --yellow:#f5c542; --red:#ff5c5c; --blue:#5aa9ff; }
body { margin:0; background:linear-gradient(135deg,#0f1117,#151a24); color:var(--text); font-family:Inter,Segoe UI,Arial,sans-serif; }
header { padding:34px 42px; border-bottom:1px solid #2a3140; background:#10141c; }
h1 { margin:0 0 8px 0; font-size:34px; letter-spacing:-0.03em; }
p { color:var(--muted); }
.summary { display:grid; grid-template-columns:repeat(5,minmax(120px,1fr)); gap:16px; padding:28px 42px; }
.stat { background:var(--panel); border:1px solid #2a3140; border-radius:18px; padding:18px; box-shadow:0 12px 30px rgba(0,0,0,.25); }
.stat strong { font-size:28px; display:block; }
.stat span { color:var(--muted); font-size:13px; }
main { padding:0 42px 50px; }
.asset-card { background:var(--panel); border:1px solid #2a3140; border-radius:22px; padding:22px; margin:22px 0; box-shadow:0 18px 44px rgba(0,0,0,.3); }
.asset-head { display:flex; align-items:flex-start; justify-content:space-between; gap:20px; }
h2 { margin:0; font-size:24px; }
h3 { margin:22px 0 10px; color:#d7deea; font-size:15px; text-transform:uppercase; letter-spacing:.08em; }
.score { background:var(--panel2); border-radius:18px; min-width:110px; padding:14px; text-align:center; }
.score strong { font-size:32px; display:block; }
.score span { color:var(--muted); font-size:12px; }
.meta { display:flex; flex-wrap:wrap; gap:10px; margin-top:14px; }
.meta span { background:#202837; color:#cbd4e1; padding:7px 10px; border-radius:999px; font-size:13px; }
.badge { display:inline-block; padding:7px 10px; border-radius:999px; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.badge-pass { background:rgba(61,220,151,.15); color:var(--green); border:1px solid rgba(61,220,151,.35); }
.badge-warning { background:rgba(245,197,66,.12); color:var(--yellow); border:1px solid rgba(245,197,66,.3); }
.badge-fail { background:rgba(255,92,92,.12); color:var(--red); border:1px solid rgba(255,92,92,.3); }
.badge-info { background:rgba(90,169,255,.12); color:var(--blue); border:1px solid rgba(90,169,255,.3); }
ul { margin:0; padding-left:22px; color:#d9e0ea; }
li { margin:5px 0; }
li.ok { color:var(--green); } li.warn { color:var(--yellow); } li.block { color:var(--red); }
table { width:100%; border-collapse:collapse; overflow:hidden; border-radius:14px; }
th,td { padding:10px 12px; border-bottom:1px solid #2a3140; text-align:left; font-size:13px; vertical-align:top; }
th { color:#f2f5f9; background:#202837; }
td { color:#cbd4e1; }
footer { padding:20px 42px 36px; color:var(--muted); border-top:1px solid #2a3140; }
</style>
</head>
<body>
<header>
<h1>M2Unity Pipeline Suite v1.0.2 Report</h1>
<p>Professional Maya-to-Unity static mesh preflight, cleanup, collider proxy validation and FBX export report.</p>
<p>Generated: __TIMESTAMP__ | Profile: __PROFILE__ | Build: __BUILD__</p>
</header>
<section class="summary">
<div class="stat"><strong>__TOTAL__</strong><span>Total Assets</span></div>
<div class="stat"><strong>__READY__</strong><span>Ready</span></div>
<div class="stat"><strong>__WARNING__</strong><span>Warning</span></div>
<div class="stat"><strong>__BLOCKED__</strong><span>Blocked</span></div>
<div class="stat"><strong>__EXPORTED__</strong><span>Exported</span></div>
</section>
<main>__CARDS__</main>
<footer>M2Unity Pipeline Suite v1.0.2</footer>
</body>
</html>'''
        replacements = {
            "__TIMESTAMP__": html_escape(export_summary.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))),
            "__PROFILE__": html_escape(settings.get("profile_name", "Custom")),
            "__BUILD__": html_escape(M2U_PIPELINE_BUILD_ID),
            "__TOTAL__": str(len(results)),
            "__READY__": str(ready),
            "__WARNING__": str(warning),
            "__BLOCKED__": str(blocked),
            "__EXPORTED__": html_escape(str(export_summary.get("exported_assets", 0))),
            "__CARDS__": "\n".join(cards),
        }
        for key, value in replacements.items():
            html = html.replace(key, value)
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path.replace("\\", "/")

    def write_unreal_import_script(self, export_folder, results):
        """Write a Unity Editor AssetPostprocessor C# helper.

        Internal function name retained for compatibility with the original M2U export path.
        The generated file should be placed under Assets/Editor in a Unity project.
        """
        path = os.path.join(export_folder, "M2Unity_ModelPostprocessor.cs")
        exported = []
        for r in results:
            export = r.get("export", {}) or {}
            if export.get("status") == "exported" and export.get("path"):
                exported.append(os.path.basename(export.get("path")))
        exported_comment = "\n".join(["// - " + item for item in exported]) or "// No FBX exports were recorded when this file was generated."
        script = """// Auto-generated by M2Unity Pipeline Suite v1.0.2
// Place this file inside a Unity project under: Assets/Editor/
// It applies conservative model import defaults and converts COL_/TRG_ proxy meshes
// into MeshCollider components during import.
//
// Exported FBX files at generation time:
{exported_comment}

using UnityEditor;
using UnityEngine;

public class M2Unity_ModelPostprocessor : AssetPostprocessor
{{
    void OnPreprocessModel()
    {{
        if (!assetPath.ToLowerInvariant().EndsWith(".fbx"))
            return;

        ModelImporter importer = (ModelImporter)assetImporter;
        importer.importCameras = false;
        importer.importLights = false;
        importer.importAnimation = false;
        importer.importVisibility = false;
        importer.importBlendShapes = false;
        importer.importNormals = ModelImporterNormals.Import;
        importer.importTangents = ModelImporterTangents.CalculateMikk;
        importer.generateSecondaryUV = true;
        importer.isReadable = false;
        importer.preserveHierarchy = true;
    }}

    void OnPostprocessModel(GameObject root)
    {{
        Transform[] transforms = root.GetComponentsInChildren<Transform>(true);
        foreach (Transform t in transforms)
        {{
            string n = t.name;
            bool isColliderProxy = n.StartsWith("COL_");
            bool isTriggerProxy = n.StartsWith("TRG_");
            if (!isColliderProxy && !isTriggerProxy)
                continue;

            MeshFilter mf = t.GetComponent<MeshFilter>();
            if (mf != null && mf.sharedMesh != null)
            {{
                MeshCollider mc = t.GetComponent<MeshCollider>();
                if (mc == null)
                    mc = t.gameObject.AddComponent<MeshCollider>();

                mc.sharedMesh = mf.sharedMesh;
                mc.convex = true;
                mc.isTrigger = isTriggerProxy;
            }}

            Renderer renderer = t.GetComponent<Renderer>();
            if (renderer != null)
                renderer.enabled = false;
        }}
    }}
}}
""".format(exported_comment=exported_comment)
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(script)
        return path.replace("\\", "/")


# ---------------------------------------------------------
# UI Widgets
# ---------------------------------------------------------

class M2UStatusCard(QtWidgets.QFrame):
    def __init__(self, title, value="0", parent=None):
        QtWidgets.QFrame.__init__(self, parent)
        self.setObjectName("M2UStatusCard")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        self.value_label = QtWidgets.QLabel(str(value))
        self.value_label.setObjectName("M2UStatusValue")
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setObjectName("M2UStatusTitle")
        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def set_value(self, value):
        self.value_label.setText(str(value))


class M2UPipelineSuiteWindow(QtWidgets.QDialog):
    WINDOW_OBJECT_NAME = "m2unityPipelineSuiteWindow"

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent or maya_main_window())
        self.setObjectName(self.WINDOW_OBJECT_NAME)
        self.setWindowTitle(M2U_PIPELINE_WINDOW_TITLE)
        self.resize(1180, 820)
        self.engine = M2UPipelineEngine()
        self.last_results = []
        self.last_settings = _deepcopy_json(PRESETS["Unity Static Prop"])
        self.current_export_summary = {}
        self._build_ui()
        self._apply_style()
        self.apply_preset("Unity Static Prop")
        self.update_dashboard([])

    # ------------------------------
    # UI build
    # ------------------------------
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        title_row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("M2Unity Pipeline Suite")
        title.setObjectName("M2UTitle")
        developer = QtWidgets.QLabel("Developer: Sonat Birdane")
        developer.setObjectName("M2UDeveloper")
        title_row.addWidget(title)
        title_row.addSpacing(12)
        title_row.addWidget(developer)
        title_row.addStretch(1)
        subtitle = QtWidgets.QLabel("Crafted with care over a few cups of coffee.")
        subtitle.setObjectName("M2USubtitle")
        workflow = QtWidgets.QLabel("Maya → Unity preflight, safe cleanup, validation, collider proxy checks, reports and FBX export.")
        workflow.setObjectName("M2UWorkflow")
        title_box.addLayout(title_row)
        title_box.addWidget(subtitle)
        title_box.addWidget(workflow)
        header.addLayout(title_box)
        header.addStretch(1)
        self.build_label = QtWidgets.QLabel("Build: {0} | Qt: {1}".format(M2U_PIPELINE_BUILD_ID, QT_MODE))
        self.build_label.setObjectName("M2UBuild")
        header.addWidget(self.build_label)
        root.addLayout(header)

        cards = QtWidgets.QGridLayout()
        self.card_selected = M2UStatusCard("Selected")
        self.card_ready = M2UStatusCard("Ready")
        self.card_warning = M2UStatusCard("Warnings")
        self.card_blocked = M2UStatusCard("Blocked")
        self.card_score = M2UStatusCard("Average Score")
        cards.addWidget(self.card_selected, 0, 0)
        cards.addWidget(self.card_ready, 0, 1)
        cards.addWidget(self.card_warning, 0, 2)
        cards.addWidget(self.card_blocked, 0, 3)
        cards.addWidget(self.card_score, 0, 4)
        root.addLayout(cards)

        main_split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root.addWidget(main_split, 1)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        main_split.addWidget(left)

        self.tabs = QtWidgets.QTabWidget()
        left_layout.addWidget(self.tabs, 1)

        self._build_wizard_tab()
        self._build_rules_tab()
        self._build_prep_tab()
        self._build_collision_tab()
        self._build_report_tab()
        self._build_help_tab()

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)
        main_split.addWidget(right)
        main_split.setStretchFactor(0, 3)
        main_split.setStretchFactor(1, 4)

        self.asset_table = QtWidgets.QTableWidget(0, 7)
        self.asset_table.setHorizontalHeaderLabels(["Asset", "Status", "Score", "Poly", "Warnings", "Blocking", "Export"])
        self.asset_table.horizontalHeader().setStretchLastSection(True)
        self.asset_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.asset_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.asset_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.asset_table.itemSelectionChanged.connect(self.on_asset_selection_changed)
        right_layout.addWidget(self.asset_table, 2)

        self.detail_text = QtWidgets.QPlainTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("Run Analyze Selected Assets to see detailed preflight results.")
        right_layout.addWidget(self.detail_text, 2)

    def _build_wizard_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(12)

        preset_row = QtWidgets.QHBoxLayout()
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItems(PRESET_NAMES)
        self.apply_preset_button = QtWidgets.QPushButton("Apply Preset")
        self.apply_preset_button.clicked.connect(lambda: self.apply_preset(self.preset_combo.currentText()))
        preset_row.addWidget(QtWidgets.QLabel("Pipeline Preset"))
        preset_row.addWidget(self.preset_combo, 1)
        preset_row.addWidget(self.apply_preset_button)
        layout.addLayout(preset_row)

        wizard_box = self._card_group("Wizard Flow")
        wizard_layout = QtWidgets.QGridLayout(wizard_box)
        self.btn_analyze = QtWidgets.QPushButton("1  Analyze Selected Assets")
        self.btn_fix = QtWidgets.QPushButton("2  Apply Safe Fixes")
        self.btn_revalidate = QtWidgets.QPushButton("3  Revalidate")
        self.btn_export = QtWidgets.QPushButton("4  Export FBX + Reports")
        self.btn_clear = QtWidgets.QPushButton("Clear Results")
        self.btn_reset_defaults = QtWidgets.QPushButton("Reset to Defaults")
        self.btn_analyze.clicked.connect(self.analyze_selected_assets)
        self.btn_fix.clicked.connect(self.apply_safe_fixes)
        self.btn_revalidate.clicked.connect(self.analyze_selected_assets)
        self.btn_export.clicked.connect(self.export_assets)
        self.btn_clear.clicked.connect(self.clear_results)
        self.btn_reset_defaults.clicked.connect(self.reset_to_defaults)
        for btn in [self.btn_analyze, self.btn_fix, self.btn_revalidate, self.btn_export]:
            btn.setMinimumHeight(42)
            btn.setObjectName("PrimaryButton")
        for btn in [self.btn_clear, self.btn_reset_defaults]:
            btn.setMinimumHeight(36)
        self.btn_clear.setToolTip("Clear the current dashboard, table, detail panel and report path list without modifying the Maya scene.")
        self.btn_reset_defaults.setToolTip("Restore the user-friendly Unity-ready default settings and clear old displayed results. Scene objects are not modified.")
        wizard_layout.addWidget(self.btn_analyze, 0, 0)
        wizard_layout.addWidget(self.btn_fix, 0, 1)
        wizard_layout.addWidget(self.btn_revalidate, 1, 0)
        wizard_layout.addWidget(self.btn_export, 1, 1)
        wizard_layout.addWidget(self.btn_clear, 2, 0)
        wizard_layout.addWidget(self.btn_reset_defaults, 2, 1)
        layout.addWidget(wizard_box)

        queue_box = self._card_group("Export Queue")
        queue_layout = QtWidgets.QFormLayout(queue_box)
        self.export_ready_cb = QtWidgets.QCheckBox("Export Ready Assets")
        self.export_warning_cb = QtWidgets.QCheckBox("Export Warning Assets")
        self.skip_blocked_cb = QtWidgets.QCheckBox("Skip Blocked Assets")
        self.write_json_cb = QtWidgets.QCheckBox("Write JSON Report")
        self.write_html_cb = QtWidgets.QCheckBox("Write HTML Report")
        self.write_unreal_cb = QtWidgets.QCheckBox("Write Unity AssetPostprocessor C#")
        self.triangulate_cb = QtWidgets.QCheckBox("Triangulate FBX Export")
        for w in [self.export_ready_cb, self.export_warning_cb, self.skip_blocked_cb, self.write_json_cb, self.write_html_cb, self.write_unreal_cb, self.triangulate_cb]:
            queue_layout.addRow(w)
        layout.addWidget(queue_box)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Dashboard / Wizard")

    def _build_rules_tab(self):
        tab = QtWidgets.QWidget()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        outer = QtWidgets.QVBoxLayout(tab)
        outer.addWidget(scroll)
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setSpacing(12)
        scroll.setWidget(content)

        scope = self._card_group("Asset Scope")
        f = QtWidgets.QFormLayout(scope)
        self.front_axis_combo = self._combo(FRONT_AXES)
        self.ignore_ucx_cb = QtWidgets.QCheckBox("Ignore COL_/TRG_ As Base Assets")
        self.include_desc_cb = QtWidgets.QCheckBox("Include Descendant Mesh Shapes")
        f.addRow("Front Axis", self.front_axis_combo)
        f.addRow(self.ignore_ucx_cb)
        f.addRow(self.include_desc_cb)
        layout.addWidget(scope)

        naming = self._card_group("Naming")
        f = QtWidgets.QFormLayout(naming)
        self.naming_enabled_cb = QtWidgets.QCheckBox("Enable Naming Rule")
        self.required_prefix_edit = QtWidgets.QLineEdit("Mesh_")
        self.naming_severity_combo = self._combo(SEVERITIES)
        self.sanitize_names_cb = QtWidgets.QCheckBox("Sanitize Asset Names")
        f.addRow(self.naming_enabled_cb)
        f.addRow("Required Prefix", self.required_prefix_edit)
        f.addRow("Severity", self.naming_severity_combo)
        f.addRow(self.sanitize_names_cb)
        layout.addWidget(naming)

        geometry = self._card_group("Geometry")
        f = QtWidgets.QFormLayout(geometry)
        self.max_poly_spin = QtWidgets.QSpinBox(); self.max_poly_spin.setMaximum(999999999)
        self.poly_severity_combo = self._combo(SEVERITIES)
        self.freeze_required_cb = QtWidgets.QCheckBox("Freeze Required")
        self.freeze_severity_combo = self._combo(SEVERITIES)
        self.history_required_cb = QtWidgets.QCheckBox("Clean History Required")
        self.history_severity_combo = self._combo(SEVERITIES)
        self.zero_thickness_cb = QtWidgets.QCheckBox("Zero Thickness Warning")
        self.zero_tol_spin = self._double_spin(0.001, 0, 1000, 6)
        self.zero_severity_combo = self._combo(SEVERITIES)
        f.addRow("Max Polycount", self.max_poly_spin)
        f.addRow("Polycount Severity", self.poly_severity_combo)
        f.addRow(self.freeze_required_cb)
        f.addRow("Freeze Severity", self.freeze_severity_combo)
        f.addRow(self.history_required_cb)
        f.addRow("History Severity", self.history_severity_combo)
        f.addRow(self.zero_thickness_cb)
        f.addRow("Zero Thickness Tolerance", self.zero_tol_spin)
        f.addRow("Zero Thickness Severity", self.zero_severity_combo)
        layout.addWidget(geometry)

        dimension = self._card_group("Dimensions")
        f = QtWidgets.QFormLayout(dimension)
        self.dimension_enabled_cb = QtWidgets.QCheckBox("Enable Dimension Check")
        self.expected_width_spin = self._double_spin(100, 0, 999999)
        self.expected_height_spin = self._double_spin(300, 0, 999999)
        self.expected_depth_spin = self._double_spin(20, 0, 999999)
        self.dimension_tol_spin = self._double_spin(0.5, 0, 999999)
        self.dimension_severity_combo = self._combo(SEVERITIES)
        f.addRow(self.dimension_enabled_cb)
        f.addRow("Expected Width (cm)", self.expected_width_spin)
        f.addRow("Expected Height (cm)", self.expected_height_spin)
        f.addRow("Expected Depth (cm)", self.expected_depth_spin)
        f.addRow("Tolerance (cm)", self.dimension_tol_spin)
        f.addRow("Severity", self.dimension_severity_combo)
        layout.addWidget(dimension)

        pivot = self._card_group("Pivot")
        f = QtWidgets.QFormLayout(pivot)
        self.pivot_enabled_cb = QtWidgets.QCheckBox("Enable Pivot Check")
        self.pivot_target_combo = self._combo(PIVOT_TARGETS)
        self.pivot_tol_spin = self._double_spin(0.5, 0, 999999)
        self.pivot_severity_combo = self._combo(SEVERITIES)
        f.addRow(self.pivot_enabled_cb)
        f.addRow("Pivot Target", self.pivot_target_combo)
        f.addRow("Tolerance (cm)", self.pivot_tol_spin)
        f.addRow("Severity", self.pivot_severity_combo)
        layout.addWidget(pivot)

        grid = self._card_group("Grid")
        f = QtWidgets.QFormLayout(grid)
        self.grid_enabled_cb = QtWidgets.QCheckBox("Enable Grid Check")
        self.grid_step_spin = self._double_spin(10, 0.001, 999999)
        self.grid_bounds_cb = QtWidgets.QCheckBox("Check Bounds Snap")
        self.grid_size_cb = QtWidgets.QCheckBox("Check Size Multiple")
        self.grid_severity_combo = self._combo(SEVERITIES)
        f.addRow(self.grid_enabled_cb)
        f.addRow("Grid Step (cm)", self.grid_step_spin)
        f.addRow(self.grid_bounds_cb)
        f.addRow(self.grid_size_cb)
        f.addRow("Severity", self.grid_severity_combo)
        layout.addWidget(grid)

        advanced = self._card_group("Advanced Unity Readiness")
        f = QtWidgets.QFormLayout(advanced)
        self.lod_enabled_cb = QtWidgets.QCheckBox("Enable LOD Readiness Check")
        self.lod_severity_combo = self._combo(SEVERITIES)
        self.socket_enabled_cb = QtWidgets.QCheckBox("Enable Socket / Locator Readiness")
        self.socket_severity_combo = self._combo(SEVERITIES)
        self.material_enabled_cb = QtWidgets.QCheckBox("Enable Material Slot Readiness")
        self.material_prefixes_edit = QtWidgets.QLineEdit("M_,MI_,MAT_")
        self.max_material_spin = QtWidgets.QSpinBox(); self.max_material_spin.setMaximum(9999)
        self.material_severity_combo = self._combo(SEVERITIES)
        self.uv_enabled_cb = QtWidgets.QCheckBox("Enable UV Readiness Check")
        self.require_lightmap_uv_cb = QtWidgets.QCheckBox("Require Lightmap UV")
        self.lightmap_names_edit = QtWidgets.QLineEdit("lightmap,Lightmap,UV1,uv1,map2")
        self.uv_sample_limit_spin = QtWidgets.QSpinBox(); self.uv_sample_limit_spin.setMaximum(999999); self.uv_sample_limit_spin.setMinimum(100)
        self.uv_severity_combo = self._combo(SEVERITIES)
        f.addRow(self.lod_enabled_cb); f.addRow("LOD Readiness Severity", self.lod_severity_combo)
        f.addRow(self.socket_enabled_cb); f.addRow("Socket / Locator Severity", self.socket_severity_combo)
        f.addRow(self.material_enabled_cb); f.addRow("Material Prefixes", self.material_prefixes_edit)
        f.addRow("Max Material Slots", self.max_material_spin); f.addRow("Material Slot Severity", self.material_severity_combo)
        f.addRow(self.uv_enabled_cb); f.addRow(self.require_lightmap_uv_cb)
        f.addRow("Lightmap UV Names", self.lightmap_names_edit)
        f.addRow("UV Sample Limit", self.uv_sample_limit_spin); f.addRow("UV Readiness Severity", self.uv_severity_combo)
        layout.addWidget(advanced)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Rules")

    def _build_prep_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        safe = self._card_group("Safe Fix Options")
        f = QtWidgets.QFormLayout(safe)
        self.make_backup_cb = QtWidgets.QCheckBox("Duplicate Backup Before Fix")
        self.hide_backups_cb = QtWidgets.QCheckBox("Hide Backups")
        self.fix_rename_cb = QtWidgets.QCheckBox("Rename / Add Prefix If Missing")
        self.sync_ucx_names_cb = QtWidgets.QCheckBox("Sync Collider Proxy Names To Base Prefix When Collider Proxy Required")
        self.sync_ucx_names_cb.setToolTip("Example: Chair_01 + COL_Chair_01 becomes Mesh_Chair_01 + COL_Mesh_Chair_01 when the base prefix is Mesh_.")
        self.fix_freeze_cb = QtWidgets.QCheckBox("Freeze Transform")
        self.fix_history_cb = QtWidgets.QCheckBox("Delete Construction History")
        self.fix_pivot_cb = QtWidgets.QCheckBox("Move Pivot To Target")
        self.fix_unlock_cb = QtWidgets.QCheckBox("Unlock Transform Attributes")
        self.fix_visible_cb = QtWidgets.QCheckBox("Make Selected Assets Visible")
        self.snap_bounds_cb = QtWidgets.QCheckBox("Snap Bounds Min To Grid")
        self.snap_pivot_cb = QtWidgets.QCheckBox("Snap Pivot To Grid")
        for w in [self.make_backup_cb, self.hide_backups_cb, self.fix_rename_cb, self.sync_ucx_names_cb, self.fix_freeze_cb, self.fix_history_cb, self.fix_pivot_cb, self.fix_unlock_cb, self.fix_visible_cb, self.snap_bounds_cb, self.snap_pivot_cb]:
            f.addRow(w)
        layout.addWidget(safe)
        tools = self._card_group("Preview / Artist-Controlled Helpers")
        gl = QtWidgets.QGridLayout(tools)
        self.btn_pivot_preview = QtWidgets.QPushButton("Create Pivot Ghost Preview")
        self.btn_delete_pivot_previews = QtWidgets.QPushButton("Delete Pivot Preview Locators")
        self.btn_create_ucx = QtWidgets.QPushButton("Create Simple Box Collider")
        self.btn_pivot_preview.clicked.connect(self.create_pivot_preview)
        self.btn_delete_pivot_previews.clicked.connect(self.delete_pivot_preview_locators)
        self.btn_create_ucx.clicked.connect(self.create_box_ucx)
        gl.addWidget(self.btn_pivot_preview, 0, 0)
        gl.addWidget(self.btn_delete_pivot_previews, 0, 1)
        gl.addWidget(self.btn_create_ucx, 1, 0)
        layout.addWidget(tools)
        note = QtWidgets.QLabel("Safe Fix never resizes geometry automatically. Size/grid dimension problems are reported for manual review.")
        note.setWordWrap(True)
        note.setObjectName("M2UNote")
        layout.addWidget(note)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Prep / Fix")

    def _build_collision_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        collision = self._card_group("Collider Proxy Rules")
        f = QtWidgets.QFormLayout(collision)
        self.collision_enabled_cb = QtWidgets.QCheckBox("Enable Collider Proxy Check")
        self.collision_requirement_combo = self._combo(COLLISION_REQUIREMENTS)
        self.collision_match_combo = self._combo(MATCH_MODES)
        self.custom_target_edit = QtWidgets.QLineEdit("")
        self.accept_multi_ucx_cb = QtWidgets.QCheckBox("Accept Multiple Collider Proxy Parts")
        self.validate_ucx_cb = QtWidgets.QCheckBox("Validate Matched Collider Proxy Meshes")
        self.ucx_validation_severity_combo = self._combo(SEVERITIES)
        self.collision_severity_combo = self._combo(SEVERITIES)
        f.addRow(self.collision_enabled_cb)
        f.addRow("Requirement", self.collision_requirement_combo)
        f.addRow("Match Mode", self.collision_match_combo)
        f.addRow("Custom Target Name", self.custom_target_edit)
        f.addRow(self.accept_multi_ucx_cb)
        f.addRow(self.validate_ucx_cb)
        f.addRow("Collider Proxy Validation Severity", self.ucx_validation_severity_combo)
        f.addRow("Collider Severity", self.collision_severity_combo)
        layout.addWidget(collision)

        role_box = self._card_group("Naming / Role Utility")
        role_layout = QtWidgets.QGridLayout(role_box)
        self.btn_role_render = QtWidgets.QPushButton("Set Selected as Render Mesh")
        self.btn_role_collider = QtWidgets.QPushButton("Set Selected as Collider Proxy")
        self.btn_role_trigger = QtWidgets.QPushButton("Set Selected as Trigger Proxy")
        self.btn_role_remove = QtWidgets.QPushButton("Remove M2Unity Role Prefixes")
        self.btn_role_render.setToolTip("Rename selected mesh transforms to Mesh_<Name>. This works on normal meshes and old UCX_/COL_/TRG_ meshes.")
        self.btn_role_collider.setToolTip("Rename selected mesh transforms to COL_Mesh_<Name>. Use this to convert old UCX collision meshes into Unity collider proxies.")
        self.btn_role_trigger.setToolTip("Rename selected mesh transforms to TRG_Mesh_<Name>. The generated Unity postprocessor imports these as trigger MeshColliders.")
        self.btn_role_remove.setToolTip("Remove Mesh_, COL_, TRG_, UCX_ and common SM_ style role prefixes from selected mesh transforms.")
        self.btn_role_render.clicked.connect(self.set_selected_as_render_mesh)
        self.btn_role_collider.clicked.connect(self.set_selected_as_collider_proxy)
        self.btn_role_trigger.clicked.connect(self.set_selected_as_trigger_proxy)
        self.btn_role_remove.clicked.connect(self.remove_selected_role_prefixes)
        role_layout.addWidget(self.btn_role_render, 0, 0)
        role_layout.addWidget(self.btn_role_collider, 0, 1)
        role_layout.addWidget(self.btn_role_trigger, 1, 0)
        role_layout.addWidget(self.btn_role_remove, 1, 1)
        layout.addWidget(role_box)

        actions = self._card_group("Collider Visualizer")
        gl = QtWidgets.QGridLayout(actions)
        self.btn_select_ucx = QtWidgets.QPushButton("Select Asset + Matching Collider")
        self.btn_isolate_ucx = QtWidgets.QPushButton("Isolate Asset + Collider")
        self.btn_color_ucx = QtWidgets.QPushButton("Colorize Collider Preview")
        self.btn_reset_ucx_materials = QtWidgets.QPushButton("Reset Collider Preview Materials")
        self.btn_select_ucx.clicked.connect(self.select_current_asset_ucx)
        self.btn_isolate_ucx.clicked.connect(self.isolate_current_asset_ucx)
        self.btn_color_ucx.clicked.connect(self.colorize_current_ucx)
        self.btn_reset_ucx_materials.clicked.connect(self.reset_current_ucx_preview_materials)
        gl.addWidget(self.btn_select_ucx, 0, 0)
        gl.addWidget(self.btn_isolate_ucx, 0, 1)
        gl.addWidget(self.btn_color_ucx, 1, 0)
        gl.addWidget(self.btn_reset_ucx_materials, 1, 1)
        layout.addWidget(actions)
        layout.addStretch(1)
        self.tabs.addTab(tab, "Collider Proxy")

    def _build_report_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        box = self._card_group("Reports")
        v = QtWidgets.QVBoxLayout(box)
        self.report_paths_text = QtWidgets.QPlainTextEdit()
        self.report_paths_text.setReadOnly(True)
        self.report_paths_text.setPlaceholderText("Export reports will appear here after Export FBX + Reports.")
        v.addWidget(self.report_paths_text)
        layout.addWidget(box, 1)
        self.tabs.addTab(tab, "Reports")

    def _build_help_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        help_text = QtWidgets.QPlainTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText(
            "M2Unity Pipeline Suite v1.0.2\n\n"
            "Recommended workflow:\n"
            "1. Select base static mesh transforms in Maya.\n"
            "2. Pick a Unity preset.\n"
            "3. Run Analyze Selected Assets.\n"
            "4. Review naming, transform, pivot, grid, LOD, material, UV and collider proxy checks.\n"
            "5. Apply Safe Fixes if desired.\n"
            "6. Revalidate.\n"
            "7. Export FBX + JSON/HTML report + Unity AssetPostprocessor C#.\n\n"
            "Role naming / Collider proxy naming:\n"
            "Use Mesh_<Name> for visible render meshes.\n"
            "Use COL_Mesh_<Name> or COL_Mesh_<Name>_01, _02, etc. for MeshCollider proxies.\n"
            "Use TRG_Mesh_<Name> for trigger-style proxy meshes.\n"
            "Use the Naming / Role Utility buttons to convert selected meshes, including old UCX_ collision meshes, without running Safe Fix.\n"
            "If Collider Required is active, Analyze and Export look for matched COL_/TRG_ proxy meshes and include them in the same FBX.\n\n"
            "Unity LOD naming:\n"
            "Use Mesh_Asset_LOD0, Mesh_Asset_LOD1, Mesh_Asset_LOD2. Polycount should decrease by LOD level.\n\n"
            "Unity AssetPostprocessor:\n"
            "The generated M2Unity_ModelPostprocessor.cs file is not run inside Maya. Copy it to Assets/Editor in a Unity project.\n\n"
            "Safe Fix policy:\n"
            "The tool can rename, freeze, delete history, move pivot, unlock attrs, make visible and snap transform position. It does not automatically resize or remodel geometry."
        )
        layout.addWidget(help_text)
        self.tabs.addTab(tab, "Help")

    def _card_group(self, title):
        box = QtWidgets.QGroupBox(title)
        box.setObjectName("M2UGroup")
        return box

    def _combo(self, items):
        c = QtWidgets.QComboBox()
        c.addItems(items)
        return c

    def _double_spin(self, value, minimum, maximum, decimals=3):
        s = QtWidgets.QDoubleSpinBox()
        s.setDecimals(decimals)
        s.setMinimum(minimum)
        s.setMaximum(maximum)
        s.setValue(value)
        return s

    def _apply_style(self):
        self.setStyleSheet('''
        QDialog { background: #10131a; color: #e8edf6; }
        QLabel { color: #e8edf6; }
        #M2UTitle { font-size: 28px; font-weight: 800; letter-spacing: -1px; }
        #M2USubtitle { color: #fbbf24; font-size: 12px; font-weight: 600; }
        #M2UDeveloper { color: #98a3b3; font-size: 11px; font-weight: 600; }
        #M2UWorkflow { color: #98a3b3; font-size: 11px; }
        #M2UBuild { color: #98a3b3; }
        #M2UNote { color: #98a3b3; padding: 8px; }
        #M2UStatusCard { background: #171c26; border: 1px solid #2a3242; border-radius: 14px; }
        #M2UStatusValue { font-size: 26px; font-weight: 800; color: #ffffff; }
        #M2UStatusTitle { font-size: 11px; color: #98a3b3; text-transform: uppercase; }
        QGroupBox#M2UGroup { background: #171c26; border: 1px solid #2a3242; border-radius: 14px; margin-top: 12px; padding: 12px; font-weight: 700; }
        QGroupBox#M2UGroup::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #d9e3f2; }
        QTabWidget::pane { border: 1px solid #2a3242; border-radius: 12px; background: #131821; }
        QTabBar::tab { background: #171c26; color: #aeb8c8; padding: 9px 13px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; }
        QTabBar::tab:selected { background: #243044; color: #ffffff; }
        QPushButton { background: #243044; color: #ffffff; border: 1px solid #354158; border-radius: 10px; padding: 8px 12px; }
        QPushButton:hover { background: #2d3c57; }
        QPushButton#PrimaryButton { background: #3468c9; font-weight: 700; }
        QPushButton#PrimaryButton:hover { background: #4078e6; }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit { background: #0f131b; color: #e8edf6; border: 1px solid #30394b; border-radius: 8px; padding: 6px; }
        QCheckBox { color: #e8edf6; spacing: 8px; }
        QTableWidget { background: #0f131b; color: #e8edf6; gridline-color: #2a3242; border: 1px solid #2a3242; border-radius: 10px; }
        QHeaderView::section { background: #202837; color: #ffffff; padding: 8px; border: 0px; }
        QScrollArea { border: 0px; background: transparent; }
        ''')

    # ------------------------------
    # Settings mapping
    # ------------------------------
    def apply_preset(self, preset_name):
        settings = _deepcopy_json(PRESETS.get(preset_name, PRESETS["Unity Static Prop"]))
        self.set_settings_to_ui(settings)
        self.last_settings = settings

    def reset_to_defaults(self):
        """Restore safe, user-friendly Unity-ready defaults without modifying scene objects."""
        default_preset = "Unity Static Prop"
        if hasattr(self, "preset_combo"):
            idx = self.preset_combo.findText(default_preset)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
        settings = _deepcopy_json(PRESETS.get(default_preset, BASE_PRESET))
        self.set_settings_to_ui(settings)
        self.last_settings = settings
        self.clear_results()
        safe_message_box(
            "M2Unity Pipeline Suite",
            "Settings reset to user-friendly defaults. Scene objects were not modified.\n\n"
            "Default profile: Unity Static Prop\n"
            "Prefix: Mesh_\n"
            "Collider Proxy: optional, but validated when present\n"
            "Safe fixes: backup, rename, freeze, history cleanup and pivot fix enabled\n"
            "Reports: JSON, HTML and Unity AssetPostprocessor C# enabled"
        )

    def set_settings_to_ui(self, s):
        self._set_combo(self.front_axis_combo, s.get("front_axis"))
        self.ignore_ucx_cb.setChecked(s.get("ignore_ucx_as_base", True))
        self.include_desc_cb.setChecked(s.get("include_descendant_meshes", True))
        self.naming_enabled_cb.setChecked(s.get("naming_enabled", True))
        self.required_prefix_edit.setText(s.get("required_prefix", "Mesh_"))
        self._set_combo(self.naming_severity_combo, s.get("naming_severity"))
        self.sanitize_names_cb.setChecked(s.get("sanitize_names", True))
        self.max_poly_spin.setValue(int(s.get("max_polycount", 5000)))
        self._set_combo(self.poly_severity_combo, s.get("polycount_severity"))
        self.freeze_required_cb.setChecked(s.get("freeze_required", True))
        self._set_combo(self.freeze_severity_combo, s.get("freeze_severity"))
        self.history_required_cb.setChecked(s.get("history_required", True))
        self._set_combo(self.history_severity_combo, s.get("history_severity"))
        self.zero_thickness_cb.setChecked(s.get("zero_thickness_enabled", True))
        self.zero_tol_spin.setValue(float(s.get("zero_thickness_tolerance_cm", 0.001)))
        self._set_combo(self.zero_severity_combo, s.get("zero_thickness_severity"))
        self.dimension_enabled_cb.setChecked(s.get("dimension_enabled", False))
        self.expected_width_spin.setValue(float(s.get("expected_width_cm", 100.0)))
        self.expected_height_spin.setValue(float(s.get("expected_height_cm", 300.0)))
        self.expected_depth_spin.setValue(float(s.get("expected_depth_cm", 20.0)))
        self.dimension_tol_spin.setValue(float(s.get("dimension_tolerance_cm", 0.5)))
        self._set_combo(self.dimension_severity_combo, s.get("dimension_severity"))
        self.pivot_enabled_cb.setChecked(s.get("pivot_enabled", True))
        self._set_combo(self.pivot_target_combo, s.get("pivot_target"))
        self.pivot_tol_spin.setValue(float(s.get("pivot_tolerance_cm", 0.5)))
        self._set_combo(self.pivot_severity_combo, s.get("pivot_severity"))
        self.grid_enabled_cb.setChecked(s.get("grid_enabled", True))
        self.grid_step_spin.setValue(float(s.get("grid_step_cm", 10.0)))
        self.grid_bounds_cb.setChecked(s.get("grid_check_bounds_snap", True))
        self.grid_size_cb.setChecked(s.get("grid_check_size_multiple", True))
        self._set_combo(self.grid_severity_combo, s.get("grid_severity"))
        self.lod_enabled_cb.setChecked(s.get("lod_enabled", True))
        self._set_combo(self.lod_severity_combo, s.get("lod_severity"))
        self.socket_enabled_cb.setChecked(s.get("socket_enabled", True))
        self._set_combo(self.socket_severity_combo, s.get("socket_severity"))
        self.material_enabled_cb.setChecked(s.get("material_enabled", True))
        self.material_prefixes_edit.setText(s.get("material_prefixes", "M_,MI_,MAT_"))
        self.max_material_spin.setValue(int(s.get("max_material_slots", 8)))
        self._set_combo(self.material_severity_combo, s.get("material_severity"))
        self.uv_enabled_cb.setChecked(s.get("uv_enabled", True))
        self.require_lightmap_uv_cb.setChecked(s.get("require_lightmap_uv", False))
        self.lightmap_names_edit.setText(s.get("lightmap_uv_names", "lightmap,Lightmap,UV1,uv1,map2"))
        self.uv_sample_limit_spin.setValue(int(s.get("uv_sample_limit", 2000)))
        self._set_combo(self.uv_severity_combo, s.get("uv_severity"))
        self.make_backup_cb.setChecked(s.get("make_backup", True))
        self.hide_backups_cb.setChecked(s.get("hide_backups", True))
        self.fix_rename_cb.setChecked(s.get("fix_rename", True))
        self.sync_ucx_names_cb.setChecked(s.get("sync_ucx_names_on_rename", True))
        self.fix_freeze_cb.setChecked(s.get("fix_freeze", True))
        self.fix_history_cb.setChecked(s.get("fix_history", True))
        self.fix_pivot_cb.setChecked(s.get("fix_pivot", True))
        self.fix_unlock_cb.setChecked(s.get("fix_unlock_attrs", False))
        self.fix_visible_cb.setChecked(s.get("fix_make_visible", False))
        self.snap_bounds_cb.setChecked(s.get("snap_bounds_min", False))
        self.snap_pivot_cb.setChecked(s.get("snap_pivot_to_grid", False))
        self.collision_enabled_cb.setChecked(s.get("collision_enabled", True))
        self._set_combo(self.collision_requirement_combo, s.get("collision_requirement"))
        self._set_combo(self.collision_match_combo, s.get("collision_match_mode"))
        self.custom_target_edit.setText(s.get("custom_collision_target", ""))
        self.accept_multi_ucx_cb.setChecked(s.get("accept_multiple_ucx_parts", True))
        self.validate_ucx_cb.setChecked(s.get("validate_ucx_meshes", True))
        self._set_combo(self.ucx_validation_severity_combo, s.get("ucx_mesh_validation_severity"))
        self._set_combo(self.collision_severity_combo, s.get("collision_severity"))
        self.export_ready_cb.setChecked(s.get("export_ready_assets", True))
        self.export_warning_cb.setChecked(s.get("export_warning_assets", True))
        self.skip_blocked_cb.setChecked(s.get("skip_blocked_assets", True))
        self.write_json_cb.setChecked(s.get("write_json_report", True))
        self.write_html_cb.setChecked(s.get("write_html_report", True))
        self.write_unreal_cb.setChecked(s.get("write_unreal_import_script", True))
        self.triangulate_cb.setChecked(s.get("triangulate_export", False))

    def _set_combo(self, combo, value):
        idx = combo.findText(str(value))
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def get_settings_from_ui(self):
        preset_name = self.preset_combo.currentText() if hasattr(self, "preset_combo") else "Custom"
        return {
            "profile_name": preset_name,
            "front_axis": self.front_axis_combo.currentText(),
            "ignore_ucx_as_base": self.ignore_ucx_cb.isChecked(),
            "include_descendant_meshes": self.include_desc_cb.isChecked(),
            "naming_enabled": self.naming_enabled_cb.isChecked(),
            "required_prefix": self.engine._sanitize_required_base_prefix(self.required_prefix_edit.text(), {"collider_prefixes": "COL_,TRG_"}),
            "naming_severity": self.naming_severity_combo.currentText(),
            "sanitize_names": self.sanitize_names_cb.isChecked(),
            "max_polycount": self.max_poly_spin.value(),
            "polycount_severity": self.poly_severity_combo.currentText(),
            "freeze_required": self.freeze_required_cb.isChecked(),
            "freeze_severity": self.freeze_severity_combo.currentText(),
            "history_required": self.history_required_cb.isChecked(),
            "history_severity": self.history_severity_combo.currentText(),
            "zero_thickness_enabled": self.zero_thickness_cb.isChecked(),
            "zero_thickness_tolerance_cm": self.zero_tol_spin.value(),
            "zero_thickness_severity": self.zero_severity_combo.currentText(),
            "dimension_enabled": self.dimension_enabled_cb.isChecked(),
            "expected_width_cm": self.expected_width_spin.value(),
            "expected_height_cm": self.expected_height_spin.value(),
            "expected_depth_cm": self.expected_depth_spin.value(),
            "dimension_tolerance_cm": self.dimension_tol_spin.value(),
            "dimension_severity": self.dimension_severity_combo.currentText(),
            "pivot_enabled": self.pivot_enabled_cb.isChecked(),
            "pivot_target": self.pivot_target_combo.currentText(),
            "pivot_tolerance_cm": self.pivot_tol_spin.value(),
            "pivot_severity": self.pivot_severity_combo.currentText(),
            "grid_enabled": self.grid_enabled_cb.isChecked(),
            "grid_step_cm": self.grid_step_spin.value(),
            "grid_check_bounds_snap": self.grid_bounds_cb.isChecked(),
            "grid_check_size_multiple": self.grid_size_cb.isChecked(),
            "grid_severity": self.grid_severity_combo.currentText(),
            "collision_enabled": self.collision_enabled_cb.isChecked(),
            "collision_requirement": self.collision_requirement_combo.currentText(),
            "collision_match_mode": self.collision_match_combo.currentText(),
            "custom_collision_target": self.custom_target_edit.text(),
            "accept_multiple_ucx_parts": self.accept_multi_ucx_cb.isChecked(),
            "validate_ucx_meshes": self.validate_ucx_cb.isChecked(),
            "ucx_mesh_validation_severity": self.ucx_validation_severity_combo.currentText(),
            "collision_severity": self.collision_severity_combo.currentText(),
            "lod_enabled": self.lod_enabled_cb.isChecked(),
            "lod_severity": self.lod_severity_combo.currentText(),
            "socket_enabled": self.socket_enabled_cb.isChecked(),
            "socket_severity": self.socket_severity_combo.currentText(),
            "material_enabled": self.material_enabled_cb.isChecked(),
            "material_prefixes": self.material_prefixes_edit.text(),
            "max_material_slots": self.max_material_spin.value(),
            "material_severity": self.material_severity_combo.currentText(),
            "uv_enabled": self.uv_enabled_cb.isChecked(),
            "require_lightmap_uv": self.require_lightmap_uv_cb.isChecked(),
            "lightmap_uv_names": self.lightmap_names_edit.text(),
            "uv_sample_limit": self.uv_sample_limit_spin.value(),
            "uv_severity": self.uv_severity_combo.currentText(),
            "make_backup": self.make_backup_cb.isChecked(),
            "hide_backups": self.hide_backups_cb.isChecked(),
            "fix_rename": self.fix_rename_cb.isChecked(),
            "sync_ucx_names_on_rename": self.sync_ucx_names_cb.isChecked(),
            "fix_freeze": self.fix_freeze_cb.isChecked(),
            "fix_history": self.fix_history_cb.isChecked(),
            "fix_pivot": self.fix_pivot_cb.isChecked(),
            "fix_unlock_attrs": self.fix_unlock_cb.isChecked(),
            "fix_make_visible": self.fix_visible_cb.isChecked(),
            "snap_bounds_min": self.snap_bounds_cb.isChecked(),
            "snap_pivot_to_grid": self.snap_pivot_cb.isChecked(),
            "export_ready_assets": self.export_ready_cb.isChecked(),
            "export_warning_assets": self.export_warning_cb.isChecked(),
            "skip_blocked_assets": self.skip_blocked_cb.isChecked(),
            "write_json_report": self.write_json_cb.isChecked(),
            "write_html_report": self.write_html_cb.isChecked(),
            "write_unreal_import_script": self.write_unreal_cb.isChecked(),
            "triangulate_export": self.triangulate_cb.isChecked(),
        }

    # ------------------------------
    # Actions
    # ------------------------------
    def analyze_selected_assets(self):
        if cmds is None:
            safe_message_box("M2Unity Pipeline Suite", "This tool must run inside Autodesk Maya.", "error")
            return
        settings = self.get_settings_from_ui()
        self.last_settings = settings
        results = self.engine.analyze_selected_assets(settings)
        self.last_results = results
        self.populate_results(results)
        self.update_dashboard(results)
        self.detail_text.setPlainText(self.format_all_results(results))
        if not results:
            safe_message_box("M2Unity Pipeline Suite", "No valid static mesh transform selected. Select one or more mesh transforms and analyze again.", "warning")

    def _select_processed_assets_after_fix(self, results):
        """Restore Maya selection to the real processed base assets after Safe Fix.

        Backup creation can leave hidden *_M2U_BACKUP nodes selected. This helper
        selects only current result asset paths, including renamed base meshes.
        """
        if cmds is None:
            return []
        paths = []
        seen = set()
        for result in results or []:
            path = result.get("asset_path")
            if not path or path in seen:
                continue
            try:
                if cmds.objExists(path) and not self.engine.clean_asset_name(path).endswith("_M2U_BACKUP"):
                    paths.append(path)
                    seen.add(path)
            except Exception:
                pass
        if paths:
            try:
                cmds.select(paths, replace=True)
            except Exception:
                pass
        return paths

    def apply_safe_fixes(self):
        if not self.last_results:
            self.analyze_selected_assets()
            if not self.last_results:
                return
        settings = self.get_settings_from_ui()
        results = self.engine.apply_safe_fixes(self.last_results, settings)
        selected_paths = self._select_processed_assets_after_fix(results)
        self.last_results = results
        self.populate_results(results)
        self.update_dashboard(results)
        detail = self.format_all_results(results, include_actions=True)
        if selected_paths:
            detail += "\n\nSelection restored to processed asset(s):\n" + "\n".join(["- {0}".format(self.engine.clean_asset_name(path)) for path in selected_paths])
        self.detail_text.setPlainText(detail)

    def export_assets(self):
        if not self.last_results:
            self.analyze_selected_assets()
            if not self.last_results:
                return
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose M2Unity Export Folder")
        if not folder:
            return
        settings = self.get_settings_from_ui()
        try:
            summary = self.engine.export_results(self.last_results, settings, folder)
            self.current_export_summary = summary
            self.populate_results(self.last_results)
            self.update_dashboard(self.last_results)
            self.detail_text.setPlainText(self.format_all_results(self.last_results, include_export=True))
            paths = []
            for key in ["json_report", "html_report", "unity_postprocessor_script"]:
                if summary.get(key):
                    paths.append("{0}: {1}".format(key, summary.get(key)))
            self.report_paths_text.setPlainText("\n".join(paths) or "No report files were written.")
            safe_message_box("M2Unity Pipeline Suite", "Export completed. Exported: {0} | Skipped: {1} | Failed: {2}".format(summary.get("exported_assets"), summary.get("skipped_assets"), summary.get("failed_exports")))
        except Exception as exc:
            safe_message_box("Export Failed", traceback.format_exc(), "error")

    def clear_results(self):
        """Clear UI-side validation/export results without touching scene objects."""
        self.last_results = []
        self.current_export_summary = {}
        try:
            self.asset_table.clearSelection()
            self.asset_table.setRowCount(0)
        except Exception:
            pass
        self.update_dashboard([])
        self.detail_text.clear()
        self.detail_text.setPlaceholderText("Run Analyze Selected Assets to see detailed preflight results.")
        if hasattr(self, "report_paths_text"):
            self.report_paths_text.clear()
            self.report_paths_text.setPlaceholderText("Export reports will appear here after Export FBX + Reports.")

    def get_current_result(self):
        rows = self.asset_table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        if row < 0 or row >= len(self.last_results):
            return None
        return self.last_results[row]

    def on_asset_selection_changed(self):
        result = self.get_current_result()
        if result:
            self.detail_text.setPlainText(self.format_result(result, include_actions=True, include_export=True))

    def create_pivot_preview(self):
        settings = self.get_settings_from_ui()
        transforms = self.engine.get_selected_transforms(settings)
        created = []
        for t in transforms:
            try:
                created.append(self.engine.create_pivot_preview(t, settings))
            except Exception:
                pass
        safe_message_box("Pivot Preview", "Created {0} pivot preview locator(s).".format(len(created)))

    def delete_pivot_preview_locators(self):
        deleted = self.engine.delete_pivot_preview_locators()
        safe_message_box("Pivot Preview", "Deleted {0} M2U pivot preview locator(s).".format(deleted))

    def _apply_role_rename(self, role, title):
        settings = self.get_settings_from_ui()
        try:
            actions = self.engine.rename_selected_as_role(role, settings=settings)
        except Exception:
            safe_message_box(title, traceback.format_exc(), "error")
            return
        if not actions:
            safe_message_box(title, "No selected mesh transforms found. Select render meshes, collider proxies, trigger proxies or old UCX meshes first.", "warning")
            return
        safe_message_box(title, "\n".join(actions[:30]) + ("\n..." if len(actions) > 30 else ""))

    def set_selected_as_render_mesh(self):
        self._apply_role_rename("render", "Set Selected as Render Mesh")

    def set_selected_as_collider_proxy(self):
        self._apply_role_rename("collider", "Set Selected as Collider Proxy")

    def set_selected_as_trigger_proxy(self):
        self._apply_role_rename("trigger", "Set Selected as Trigger Proxy")

    def remove_selected_role_prefixes(self):
        self._apply_role_rename("remove", "Remove M2Unity Role Prefixes")

    def create_box_ucx(self):
        settings = self.get_settings_from_ui()
        transforms = self.engine.get_selected_transforms(settings)
        created = []
        for t in transforms:
            try:
                created.append(self.engine.create_box_ucx_for_asset(t, settings))
            except Exception as exc:
                cmds.warning("Create collider proxy failed for {0}: {1}".format(t, exc))
        safe_message_box("Create Box Collider", "Created {0} simple COL_ collider proxy mesh(es). Re-run Analyze.".format(len(created)))

    def select_current_asset_ucx(self):
        r = self.get_current_result()
        if not r:
            safe_message_box("Collision", "Select an asset row first.", "warning")
            return
        paths = self.engine.select_asset_and_ucx(r)
        safe_message_box("Collision", "Selected {0} node(s).".format(len(paths)))

    def isolate_current_asset_ucx(self):
        r = self.get_current_result()
        if not r:
            safe_message_box("Collision", "Select an asset row first.", "warning")
            return
        paths = self.engine.isolate_asset_and_ucx(r)
        safe_message_box("Collision", "Isolated {0} node(s) in focused viewport, if a model panel was active.".format(len(paths)))

    def colorize_current_ucx(self):
        r = self.get_current_result()
        if not r:
            safe_message_box("Collision", "Select an asset row first.", "warning")
            return
        count = self.engine.colorize_collision_preview(r)
        safe_message_box("Collider Preview", "Colorized {0} collider proxy mesh(es).".format(count))

    def reset_current_ucx_preview_materials(self):
        r = self.get_current_result()
        if not r:
            safe_message_box("Collision", "Select an asset row first.", "warning")
            return
        count = self.engine.reset_collision_preview_materials(r)
        safe_message_box("Collider Preview", "Restored preview material assignment on {0} collider proxy mesh(es).".format(count))

    # ------------------------------
    # Result formatting
    # ------------------------------
    def update_dashboard(self, results):
        total = len(results)
        ready = sum(1 for r in results if r.get("status") == "Ready")
        warning = sum(1 for r in results if r.get("status") == "Warning")
        blocked = sum(1 for r in results if r.get("status") == "Blocked")
        avg = int(sum(r.get("m2u_score", 0) for r in results) / float(total)) if total else 0
        self.card_selected.set_value(total)
        self.card_ready.set_value(ready)
        self.card_warning.set_value(warning)
        self.card_blocked.set_value(blocked)
        self.card_score.set_value(avg)

    def populate_results(self, results):
        self.asset_table.setRowCount(0)
        for r in results:
            row = self.asset_table.rowCount()
            self.asset_table.insertRow(row)
            values = [
                r.get("asset_name", ""),
                r.get("status", ""),
                str(r.get("m2u_score", 0)),
                str(r.get("polycount", "")),
                str(len(r.get("warnings", []) or [])),
                str(len(r.get("blocking_issues", []) or [])),
                (r.get("export", {}) or {}).get("status", "not_run"),
            ]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if col == 1:
                    status = r.get("status")
                    if status == "Ready":
                        item.setForeground(QtGui.QBrush(QtGui.QColor("#3ddc97")))
                    elif status == "Warning":
                        item.setForeground(QtGui.QBrush(QtGui.QColor("#f5c542")))
                    elif status == "Blocked":
                        item.setForeground(QtGui.QBrush(QtGui.QColor("#ff5c5c")))
                self.asset_table.setItem(row, col, item)

    def format_all_results(self, results, include_actions=False, include_export=False):
        if not results:
            return "No results."
        return "\n\n".join([self.format_result(r, include_actions=include_actions, include_export=include_export) for r in results])

    def format_result(self, r, include_actions=False, include_export=False):
        lines = []
        lines.append("=" * 80)
        lines.append("{0} | Status: {1} | M2Unity Score: {2}/100".format(r.get("asset_name", "UnnamedAsset"), r.get("status", "Unknown"), r.get("m2u_score", 0)))
        lines.append("Path: {0}".format(r.get("asset_path", "")))
        lines.append("Profile: {0}".format(r.get("profile", "")))
        if r.get("dimensions"):
            d = r.get("dimensions")
            lines.append("Dimensions W/H/D: {0:.3f}, {1:.3f}, {2:.3f} cm".format(d.get("width_cm", 0), d.get("height_cm", 0), d.get("depth_cm", 0)))
        lines.append("Polycount: {0}".format(r.get("polycount", "")))
        lines.append("")
        lines.append("Core Checks:")
        for name in sorted((r.get("checks") or {}).keys()):
            c = r.get("checks", {}).get(name, {})
            lines.append("  - {0}: {1} | {2}".format(name, c.get("status"), c.get("reason")))
        for group_name, key in [("LOD", "lod_validation"), ("Material", "material_validation"), ("UV", "uv_validation"), ("Socket", "socket_validation")]:
            data = r.get(key) or {}
            if data:
                lines.append("")
                lines.append(group_name + " Checks:")
                for name in sorted((data.get("checks") or {}).keys()):
                    c = data.get("checks", {}).get(name, {})
                    lines.append("  - {0}: {1} | {2}".format(name, c.get("status"), c.get("reason")))
        lines.append("")
        lines.append("Collider Proxy:")
        coll = r.get("collision", {}) or {}
        lines.append("  Target: {0}".format(coll.get("target_name", "")))
        matches = coll.get("matches", []) or []
        if matches:
            for m in matches:
                lines.append("  - {0}".format(m.get("name")))
        else:
            lines.append("  - No matching collider proxy mesh")
        if r.get("ucx_mesh_validation"):
            lines.append("Collider Proxy Validation:")
            for ucx in r.get("ucx_mesh_validation"):
                lines.append("  - {0}: {1} ({2})".format(ucx.get("name"), ucx.get("status"), ", ".join(ucx.get("failed_checks", []))))
        if r.get("blocking_issues"):
            lines.append("")
            lines.append("Blocking Issues:")
            for issue in r.get("blocking_issues"):
                lines.append("  - {0}".format(issue))
        if r.get("warnings"):
            lines.append("")
            lines.append("Warnings:")
            for issue in r.get("warnings"):
                lines.append("  - {0}".format(issue))
        if r.get("fix_plan"):
            lines.append("")
            lines.append("Fix Plan Preview:")
            for item in r.get("fix_plan"):
                lines.append("  - {0}".format(item))
        if r.get("manual_review"):
            lines.append("")
            lines.append("Manual Review:")
            for item in r.get("manual_review"):
                lines.append("  - {0}".format(item))
        if include_actions and r.get("fixed_actions"):
            lines.append("")
            lines.append("Fixed Actions:")
            for item in r.get("fixed_actions"):
                lines.append("  - {0}".format(item))
        if include_export:
            export = r.get("export", {}) or {}
            lines.append("")
            lines.append("Export:")
            lines.append("  Status: {0}".format(export.get("status", "not_run")))
            lines.append("  Message: {0}".format(export.get("message", "")))
        if r.get("errors"):
            lines.append("")
            lines.append("Errors:")
            for err in r.get("errors"):
                lines.append("  - {0}".format(err))
        return "\n".join(lines)


_UI_INSTANCE = None


def show():
    """Open the M2Unity Pipeline Suite UI and keep a module-level reference alive."""
    global _UI_INSTANCE
    if cmds is None or QtWidgets is None:
        raise RuntimeError("M2Unity Pipeline Suite must run inside Autodesk Maya with PySide2/PySide6 available.")
    try:
        for widget in QtWidgets.QApplication.allWidgets():
            if widget.objectName() == M2UPipelineSuiteWindow.WINDOW_OBJECT_NAME:
                widget.close()
                widget.deleteLater()
    except Exception:
        pass
    _UI_INSTANCE = M2UPipelineSuiteWindow()
    _UI_INSTANCE.show()
    return _UI_INSTANCE


if __name__ == "__main__":
    show()
