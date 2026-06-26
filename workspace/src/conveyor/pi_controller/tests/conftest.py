from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for rel in [ROOT, ROOT.parent / "modbus_client"]:
    path = str(rel)
    if path not in sys.path:
        sys.path.insert(0, path)
