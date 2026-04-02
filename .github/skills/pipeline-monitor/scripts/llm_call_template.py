from __future__ import annotations

import importlib.util
from pathlib import Path

_SHARED_FILE = Path(__file__).resolve().parents[2] / "devops-setup" / "scripts" / "llm_call_template.py"
_spec = importlib.util.spec_from_file_location("_shared_llm_template", _SHARED_FILE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load shared llm template from {_SHARED_FILE}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

call_llm = _mod.call_llm
DEFAULT_MODEL = _mod.DEFAULT_MODEL
CopilotClient = getattr(_mod, "CopilotClient", None)
check_model = getattr(_mod, "check_model", None)