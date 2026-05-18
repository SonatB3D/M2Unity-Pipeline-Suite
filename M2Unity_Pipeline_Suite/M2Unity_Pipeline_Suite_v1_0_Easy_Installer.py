# -*- coding: utf-8 -*-
"""
M2Unity Pipeline Suite v1.0.2 - Easy Maya Installer

Run inside Maya Script Editor > Python tab. The installer asks for an install
folder, copies the tool files there, and adds/updates the M2Unity Pipeline Suite
button on the M2U_Tools shelf. After installation, users open the tool from
the shelf and do not need this installer again.
"""
from __future__ import print_function
import os
import sys
import shutil
import json
import time

SHELF_NAME = "M2U_Tools"
LEGACY_SHELF_NAMES = ["M2Unity_Tools"]
BUTTON_LABEL = "M2Unity Pipeline Suite"
BUTTON_ANNOTATION_MARKER = "M2UNITY_PIPELINE_SUITE_BUTTON"
ICON_NAME = "m2unity_pipeline_suite_icon.png"
VERSION_LABEL = "v1.0.2"
REQUIRED_FILES = [
    "m2unity_pipeline_suite_v1_0.py",
    "M2Unity Pipeline Suite.py",
    "README_M2Unity_Pipeline_Suite.txt",
    "FUNCTIONS_M2Unity_Pipeline_Suite.txt",
    "LICENCE_TERMS_M2Unity_Pipeline_Suite.txt",
    "m2unity_pipeline_suite_icon.png",
    "reinstall_m2unity_pipeline_suite_shelf_button.py",
]


def _require_maya():
    try:
        import maya.cmds as cmds
        import maya.mel as mel
        return cmds, mel
    except Exception:
        raise RuntimeError("This installer must be run inside Autodesk Maya Script Editor > Python tab.")


def _source_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def _choose_install_folder(cmds):
    start_dir = os.path.join(os.path.expanduser("~"), "Documents", "maya", "scripts")
    if not os.path.isdir(start_dir):
        start_dir = os.path.expanduser("~")
    result = cmds.fileDialog2(caption="Choose M2Unity Pipeline Suite Install Folder", fileMode=3, startingDirectory=start_dir, okCaption="Install Here")
    if not result:
        return None
    install_dir = result[0]
    if os.path.basename(os.path.normpath(install_dir)).lower() not in ["m2unity_pipeline_suite", "m2unity pipeline suite"]:
        install_dir = os.path.join(install_dir, "M2Unity_Pipeline_Suite")
    if not os.path.isdir(install_dir):
        os.makedirs(install_dir)
    return install_dir


def _copy_tool_files(install_dir):
    src_dir = _source_dir()
    copied = []
    missing = []
    for name in REQUIRED_FILES:
        src = os.path.join(src_dir, name)
        dst = os.path.join(install_dir, name)
        if not os.path.isfile(src):
            missing.append(name)
            continue
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)
        copied.append(dst)
    return copied, missing


def _ensure_shelf(cmds, mel):
    try:
        shelf_top = mel.eval("$tmp=$gShelfTopLevel")
    except Exception:
        shelf_top = None
    if not cmds.shelfLayout(SHELF_NAME, exists=True):
        if shelf_top:
            cmds.shelfLayout(SHELF_NAME, parent=shelf_top)
        else:
            cmds.shelfLayout(SHELF_NAME)
    return SHELF_NAME


def _remove_old_button(cmds, shelf):
    removed = 0
    for child in cmds.shelfLayout(shelf, q=True, childArray=True) or []:
        try:
            label = cmds.shelfButton(child, q=True, label=True)
            ann = cmds.shelfButton(child, q=True, annotation=True) or ""
            if label == BUTTON_LABEL or BUTTON_ANNOTATION_MARKER in ann:
                cmds.deleteUI(child)
                removed += 1
        except Exception:
            pass
    return removed


def _build_shelf_command(install_dir):
    safe_dir = install_dir.replace("\\", "/").replace("'", "\\'")
    return "import sys, importlib\ntool_dir = r'%s'\nif tool_dir not in sys.path:\n    sys.path.insert(0, tool_dir)\nimport m2unity_pipeline_suite_v1_0\ntry:\n    importlib.reload(m2unity_pipeline_suite_v1_0)\nexcept Exception:\n    pass\nm2unity_pipeline_suite_v1_0.show()\n" % safe_dir


def _install_shelf_button(cmds, mel, install_dir):
    shelf = _ensure_shelf(cmds, mel)
    removed = _remove_old_button(cmds, shelf)
    for legacy_shelf in LEGACY_SHELF_NAMES:
        try:
            if cmds.shelfLayout(legacy_shelf, exists=True):
                removed += _remove_old_button(cmds, legacy_shelf)
        except Exception:
            pass
    icon_path = os.path.join(install_dir, ICON_NAME)
    cmds.shelfButton(
        parent=shelf,
        label=BUTTON_LABEL,
        annotation=BUTTON_ANNOTATION_MARKER + " - Open M2Unity Pipeline Suite " + VERSION_LABEL,
        command=_build_shelf_command(install_dir),
        sourceType="python",
        image1=icon_path if os.path.isfile(icon_path) else "commandButton.png",
        imageOverlayLabel="M2Unity",
        overlayLabelColor=(1.0, 1.0, 1.0),
        overlayLabelBackColor=(0.05, 0.08, 0.12, 0.75),
    )
    try:
        mel.eval('saveAllShelves $gShelfTopLevel;')
    except Exception:
        pass
    return removed


def _write_install_record(install_dir):
    path = os.path.join(install_dir, "m2unity_pipeline_suite_install.json")
    data = {
        "tool": "M2Unity Pipeline Suite",
        "version": VERSION_LABEL,
        "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "install_dir": install_dir,
        "shelf": SHELF_NAME,
    }
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
    return path


def run_installer():
    cmds, mel = _require_maya()
    install_dir = _choose_install_folder(cmds)
    if not install_dir:
        print("M2Unity Pipeline Suite installation cancelled.")
        return
    copied, missing = _copy_tool_files(install_dir)
    removed = _install_shelf_button(cmds, mel, install_dir)
    record = _write_install_record(install_dir)
    message = (
        "M2Unity Pipeline Suite %s installed successfully.\n\n"
        "Install folder:\n%s\n\n"
        "Shelf:\n%s\n\n"
        "Button:\n%s\n\n"
        "Updated old buttons removed: %s\n"
        "Files installed: %s\n"
        "Install record:\n%s" % (VERSION_LABEL, install_dir, SHELF_NAME, BUTTON_LABEL, removed, len(copied), record)
    )
    if missing:
        message += "\n\nMissing package files:\n" + "\n".join(missing)
    try:
        cmds.confirmDialog(title="M2Unity Pipeline Suite Installer", message=message, button=["OK"], icon="information")
    except Exception:
        pass
    print(message)


run_installer()
