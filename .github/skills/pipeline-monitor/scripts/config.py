from __future__ import annotations

import importlib.util
from pathlib import Path

_SHARED_FILE = Path(__file__).resolve().parents[2] / "devops-setup" / "scripts" / "config.py"
_spec = importlib.util.spec_from_file_location("_shared_devops_config", _SHARED_FILE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load shared config from {_SHARED_FILE}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

for _name in dir(_mod):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_mod, _name)
