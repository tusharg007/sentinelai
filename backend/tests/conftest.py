"""Ensure the backend package root is on sys.path for pytest."""
import sys
from pathlib import Path

# Add backend/ directory to sys.path so 'from app.*' imports work
_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)
