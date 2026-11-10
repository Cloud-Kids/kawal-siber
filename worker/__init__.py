"""
KAWAL SIBER Security Worker Package.
"""
import sys
from pathlib import Path

# Ensure backend package is importable when running worker locally
_backend_dir = Path(__file__).resolve().parent.parent / "backend"
if _backend_dir.exists() and str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))


