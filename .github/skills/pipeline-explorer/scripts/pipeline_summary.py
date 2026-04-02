#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "devops-setup" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from llm_call_template import call_llm, DEFAULT_MODEL  # noqa: E402


def build_messages(graph: dict, timing: dict | None) -> list[dict[str, str]]:
    system = (
        "You are a CI/CD pipeline analyst. Summarize phases, critical path, bottlenecks, "
        "timing risks, and optimization opportunities in concise markdown."
    )
    user = "Pipeline graph JSON:\n" + json.dumps(graph, indent=2)
    if timing:
        user += "\n\nTiming JSON:\n" + json.dumps(timing, indent=2)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize pipeline graph using LLM")
    parser.add_argument("--graph", required=True)
    parser.add_argument("--timing")
    parser.add_argument("--output")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
    timing = json.loads(Path(args.timing).read_text(encoding="utf-8")) if args.timing else None

    result = call_llm(build_messages(graph, timing), model=args.model).strip()
    if args.output:
        Path(args.output).write_text(result + "\n", encoding="utf-8")
        print(f"Saved summary to {args.output}")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
