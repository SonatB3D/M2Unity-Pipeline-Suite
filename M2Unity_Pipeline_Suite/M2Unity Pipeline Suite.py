# -*- coding: utf-8 -*-
"""Launcher for M2Unity Pipeline Suite."""
from __future__ import print_function
import os
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)

try:
    import importlib
    import m2unity_pipeline_suite_v1_0
    importlib.reload(m2unity_pipeline_suite_v1_0)
except Exception:
    import m2unity_pipeline_suite_v1_0

m2unity_pipeline_suite_v1_0.show()
