"""
tree.py — Render a Jenkins job registry as a hierarchical pipeline tree.

Used by fetch_jenkins_configs.py (Step 3b).

write_tree(registry, output_path)
  registry    — dict loaded from jenkins_graph_xml.json
                  { "root": <url>, "jobs": { <name>: { "downstream_jobs": [...], ... } } }
  output_path — pathlib.Path where the text tree is written
"""

from __future__ import annotations

from pathlib import Path


def write_tree(registry: dict, output_path: Path) -> None:
    """Write a hierarchical text tree of the Jenkins job graph to *output_path*."""

    jobs: dict = registry.get("jobs", {})
    root_url: str = registry.get("root", "")

    # Find root node(s): jobs with no upstream parents
    all_children: set[str] = set()
    for meta in jobs.values():
        for child in meta.get("downstream_jobs", []):
            all_children.add(child)

    roots = [name for name in jobs if name not in all_children]
    if not roots:
        # Fallback: pick the job whose URL matches the root URL
        for name, meta in jobs.items():
            if meta.get("url", "").rstrip("/") == root_url.rstrip("/"):
                roots = [name]
                break
    if not roots:
        roots = sorted(jobs.keys())[:1]

    lines: list[str] = ["Pipeline Tree", "=" * 60, ""]

    def _walk(name: str, prefix: str, visited: set[str]) -> None:
        meta = jobs.get(name, {})
        children = meta.get("downstream_jobs", [])
        lines.append(prefix + name)
        if name in visited:
            # Cycle guard — don't recurse again
            return
        visited = visited | {name}
        for i, child in enumerate(children):
            last = i == len(children) - 1
            connector = "└── " if last else "├── "
            child_prefix = (prefix.replace("├── ", "│   ")
                                   .replace("└── ", "    ")) + connector
            _walk(child, child_prefix, visited)

    for root in sorted(roots):
        _walk(root, "", set())

    lines.append("")
    lines.append(f"Total jobs: {len(jobs)}")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote {output_path.name}  ({len(jobs)} jobs, root(s): {', '.join(sorted(roots))})")
