"""
Vercel serverless entrypoint.

Imports the FastAPI app from carbon_api.py (renamed from api.py to avoid
name collision with this api/ package directory).
"""
import sys
import os

# Ensure project root is on the path when Vercel changes CWD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from carbon_api import app  # noqa: E402, F401
