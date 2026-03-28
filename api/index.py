"""
Vercel serverless entrypoint.

Adds the project root to sys.path and imports the FastAPI app from the root
app_main.py (renamed from api.py to avoid package/module name collision with
this api/ directory).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib.util

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("_carbon_api", os.path.join(_root, "api.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Vercel looks for `app` in the module exposed by this file
app = _mod.app
