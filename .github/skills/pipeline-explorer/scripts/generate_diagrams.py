#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_tree_lines(tree_text: str) -> list[tuple[int, str]]:
    lines = []
    for raw in tree_text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if " " in line or " " in line:
            idx = line.find(" ") if " " in line else line.find(" ")
            depth = idx // 4 + 1
            name = line[idx + 4 :].replace(" [new]", "").strip()
            lines.append((depth, name))
        else:
            lines.append((0, line.strip().replace(" [new]", "")))
    return lines


def to_mermaid(nodes: list[tuple[int, str]]) -> str:
    out = ["flowchart TD"]
    stack = []
    for depth, name in nodes:
        node_id = f"n{len(out)}"
        label = name.replace('"', "'")
        out.append(f"    {node_id}[\"{label}\"]")
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if stack:
            out.append(f"    {stack[-1][1]} --> {node_id}")
        stack.append((depth, node_id))
    return "\n".join(out) + "\n"


def to_svg(nodes: list[tuple[int, str]]) -> str:
    # Simple text-based SVG tree for portability.
    y_step = 24
    x_step = 26
    width = 1600
    height = max(200, (len(nodes) + 2) * y_step)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
    ]

    for i, (depth, name) in enumerate(nodes, 1):
        x = 20 + depth * x_step
        y = i * y_step
        safe = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts.append(f'<text x="{x}" y="{y}" font-size="13" fill="#1f2937">{safe}</text>')

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Mermaid and SVG diagrams from pipeline tree text")
    parser.add_argument("--tree", required=True, help="Input tree text file (e.g. fetch_xml/pipeline_tree.txt)")
    parser.add_argument("--output-dir", default="plugin_artifacts/diagrams", help="Output directory")
    args = parser.parse_args()

    tree_path = Path(args.tree)
    text = tree_path.read_text(encoding="utf-8", errors="replace")
    nodes = parse_tree_lines(text)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mermaid = to_mermaid(nodes)
    svg = to_svg(nodes)

    mermaid_path = out_dir / "pipeline.mmd"
    svg_path = out_dir / "pipeline.svg"

    mermaid_path.write_text(mermaid, encoding="utf-8")
    svg_path.write_text(svg, encoding="utf-8")

    print(f"Wrote {mermaid_path}")
    print(f"Wrote {svg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
