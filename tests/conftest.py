"""Pytest configuration. Ensures src is on path when running tests from project root."""

import sys
from pathlib import Path

# Add src to path so pempy can be imported without pip install
src = Path(__file__).resolve().parent.parent / "src"
if src.exists() and str(src) not in sys.path:
    sys.path.insert(0, str(src))
