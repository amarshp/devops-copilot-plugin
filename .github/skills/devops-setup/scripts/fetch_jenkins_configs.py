"""
fetch_xml.py — Discover Jenkins jobs by parsing config.xml files (BFS),
               save a registry, and download every job's config.xml.

Strategy: Config XML BFS
  Starting from the root job, downloads its config.xml and parses it for
  sub-job references (<jobName>, <projects>, build job: '...'). Each
  referenced job is then fetched from Jenkins, its XML is parsed for further
  references, and so on — BFS continues until no new jobs are found.

  This discovers jobs that are invisible to the downstreamProjects API:
  MultiJob phases, parameterized trigger targets, and Groovy build steps.

Reads credentials from .env in the project root (one folder above this file):
  JENKINS_ROOT_URL   Full URL of the root pipeline job
  JENKINS_URL        Base URL of the Jenkins server (e.g. http://host:8080)
  JENKINS_USER       Jenkins username
  JENKINS_TOKEN      Jenkins API token

All output is written to the project root (relative to CWD):
  fetch_xml/config_xml/       Downloaded config.xml for every discovered job
  fetch_xml/jenkins_graph_xml.json  Job registry: name, url, class, level
  fetch_xml/levels_xml.txt    Jobs grouped by XML-reference depth
  fetch_xml/unresolved_jobs.txt  Job names referenced in XMLs but not on Jenkins
"""

import json
import os
import re
import sys
import time
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from dotenv import load_dotenv

# tree.py lives in the project root (one level up)
sys.path.insert(0, str(Path(__file__).parent.parent))
from tree import write_tree  # noqa: E402

# ── Output paths (relative to the current working directory) ──────────────

_OUT_DIR         = Path("fetch_xml")
CONFIG_DIR       = _OUT_DIR / "config_xml"
REGISTRY         = _OUT_DIR / "jenkins_graph_xml.json"
LEVELS_FILE      = _OUT_DIR / "levels_xml.txt"
UNRESOLVED_FILE  = _OUT_DIR / "unresolved_jobs.txt"


# ── XML reference patterns ─────────────────────────────────────────────────

# MultiJob plugin:  <jobName>SomeJob</jobName>
_RE_JOBNAME   = re.compile(r"<jobName>\s*([^<\s][^<]*?)\s*</jobName>")
# Parameterized Trigger plugin:  <projects>Job1, Job2</projects>
_RE_PROJECTS  = re.compile(r"<projects>\s*([^<]+?)\s*</projects>")
# Groovy pipeline:  build job: 'SomeName'
_RE_BUILD_JOB = re.compile(r"""build\s+job\s*:\s*['"]([^'"]+)['"]""")


def _extract_refs(xml_text: str) -> list[str]:
    """Return all job names referenced in a config.xml, in document order.

    Collects matches from all patterns together with their character positions,
    then sorts by position so the result reflects the order jobs appear in the
    XML — not the order the regex patterns are applied.
    """
    # (char_position, name) — gathered from all patterns before sorting
    all_matches: list[tuple[int, str]] = []

    for m in _RE_JOBNAME.finditer(xml_text):
        all_matches.append((m.start(), m.group(1).strip()))

    for m in _RE_PROJECTS.finditer(xml_text):
        for part in m.group(1).split(","):
            part = part.strip()
            if part:
                all_matches.append((m.start(), part))

    for m in _RE_BUILD_JOB.finditer(xml_text):
        all_matches.append((m.start(), m.group(1).strip()))

    # Sort by position in the document to preserve XML-defined order
    all_matches.sort(key=lambda x: x[0])

    seen: set[str] = set()
    refs: list[str] = []
    for _, name in all_matches:
        if name and name not in seen:
            seen.add(name)
            refs.append(name)

    return refs


def _looks_like_job(name: str) -> bool:
    """Filter out strings that are clearly not job names."""
    if not name:
        return False
    if " " in name:           # "FAILURE", "ABORTED", prose text
        return False
    if name.startswith("$"):  # ${VARIABLE}
        return False
    if name.startswith("*") or name.startswith("/"):  # */master branch specs
        return False
    if name in {"FAILURE", "UNSTABLE", "ABORTED", "SUCCESS", "true", "false"}:
        return False
    return True


# ── HTTP helpers ───────────────────────────────────────────────────────────

_thread_local = threading.local()


def _get_session(auth):
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.auth = auth
        _thread_local.session = s
    return _thread_local.session


def _get_json(url: str, auth, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            r = _get_session(auth).get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] Cannot connect to {url}. Check VPN/network.")
            raise SystemExit(1)
        except requests.exceptions.ReadTimeout:
            print(f"[WARN] Timeout attempt {attempt}/{retries}: {url}", flush=True)
            if attempt == retries:
                return None
            time.sleep(2 * attempt)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None   # job does not exist or was deleted
            print(f"[WARN] HTTP {e.response.status_code}: {url}")
            return None
    return None


def _get_xml(url: str, auth, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            r = _get_session(auth).get(url, timeout=30)
            if r.status_code == 200:
                return r.text
            return None
        except requests.exceptions.ReadTimeout:
            if attempt == retries:
                return None
            time.sleep(2 * attempt)
        except Exception:
            return None
    return None


# ── Name → URL resolution ──────────────────────────────────────────────────

def _name_to_api_url(name: str, jenkins_url: str) -> str:
    """
    Convert a job name to its Jenkins API endpoint URL.
    Handles folder paths: "FolderA/MyJob" → ".../job/FolderA/job/MyJob/api/json"
    """
    parts = name.strip("/").split("/")
    path  = "/job/".join(parts)
    return f"{jenkins_url}/job/{path}/api/json"


def _resolve_name(name: str, jenkins_url: str, auth) -> dict | None:
    """
    Resolve a job name to its full metadata using the Jenkins API.
    Returns {name, url, _class} or None if the job does not exist.
    """
    api_url = _name_to_api_url(name, jenkins_url)
    data    = _get_json(api_url, auth)
    if not data:
        return None
    return {
        "name":   data.get("fullName") or data.get("name") or name,
        "url":    data.get("url", "").rstrip("/"),
        "_class": data.get("_class", ""),
    }


# ── Helpers ────────────────────────────────────────────────────────────────

def _fmt_time(seconds) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


def _safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name) + ".xml"


# ── Unresolved job tree renderer ─────────────────────────────────────────────

def _render_unresolved_trees(unresolved: list[str], adjacency: dict[str, list]) -> str:
    """
    For each unresolved job name, find all root-to-job paths via the adjacency
    list and render them as a merged trie tree.
    """
    from collections import OrderedDict

    # Build reverse adjacency: child → [parents]
    reverse: dict[str, list[str]] = {}
    for parent, children in adjacency.items():
        for child in children:
            reverse.setdefault(child, []).append(parent)

    def find_all_paths(target: str) -> list[list[str]]:
        """Return all root-to-target paths (each path = list of names)."""
        paths: list[list[str]] = []
        stack: list[list[str]] = [[target]]
        while stack:
            path = stack.pop()
            node = path[0]
            parents = reverse.get(node, [])
            if not parents:
                paths.append(path)
            else:
                for p in parents:
                    if p not in path:   # guard against cycles
                        stack.append([p] + path)
        return paths

    class _Node:
        def __init__(self):
            self.children: OrderedDict[str, "_Node"] = OrderedDict()

    def build_trie(paths: list[list[str]]) -> _Node:
        root = _Node()
        for path in paths:
            cur = root
            for step in path:
                if step not in cur.children:
                    cur.children[step] = _Node()
                cur = cur.children[step]
        return root

    def walk(node: _Node, prefix: str = "") -> list[str]:
        lines: list[str] = []
        items = list(node.children.items())
        for i, (name, child) in enumerate(items):
            last = (i == len(items) - 1)
            connector = "└── " if last else "├── "
            lines.append(prefix + connector + name)
            extension = "    " if last else "│   "
            lines.extend(walk(child, prefix + extension))
        return lines

    sections: list[str] = [
        "Unresolved Jobs — Parent-to-Child Tree Flows",
        "=" * 50,
        "",
    ]
    for name in sorted(unresolved):
        paths = find_all_paths(name)
        sections.append(f"[UNRESOLVED] {name}")
        sections.append("-" * (len(name) + 14))
        trie = build_trie(paths)
        sections.extend(walk(trie))
        sections.append("")

    return "\n".join(sections)


# ── Core XML BFS ───────────────────────────────────────────────────────────

def _discover_jobs(root_url: str, jenkins_url: str, auth) -> tuple[list, dict, list]:
    """
    BFS starting from root_url.  Each level is the set of jobs referenced in
    the config XMLs of the previous level's jobs.

    Returns:
      all_jobs   — list of {name, url, _class, level}
      adjacency  — {source_name: [child_name, ...]} in XML discovery order
      unresolved — list of names referenced in XMLs but not found on Jenkins
    """
    # ── Bootstrap: fetch root job metadata ───────────────────────────────
    print(f"  Fetching root job metadata: {root_url}", flush=True)
    root_data = _get_json(f"{root_url}/api/json?tree=name,fullName,url,_class", auth)
    if not root_data:
        print("  [WARN] Could not reach root job. Check URL/credentials.", flush=True)
        return [], {}, []

    root_name = root_data.get("fullName") or root_data.get("name", root_url)
    root_url  = root_data.get("url", root_url).rstrip("/")

    # visited: name → {name, url, _class, level}
    visited:    dict[str, dict]  = {}
    adjacency:  dict[str, list]  = {}
    unresolved: list[str]        = []

    # BFS queue: list of (parent_name, child_name) pairs to process next level
    # Level 0 is the root itself
    visited[root_name] = {"name": root_name, "url": root_url, "_class": root_data.get("_class", ""), "level": 0}

    # Queue holds jobs to download XML for, with their assigned level
    xml_queue: deque[tuple[str, int]] = deque()   # (name, level)
    xml_queue.append((root_name, 0))

    already_queued: set[str] = {root_name}

    while xml_queue:
        # Drain the current level into a batch
        batch: list[tuple[str, int]] = []
        current_level = xml_queue[0][1]
        while xml_queue and xml_queue[0][1] == current_level:
            batch.append(xml_queue.popleft())

        print(f"  Level {current_level}: downloading {len(batch)} XML(s)  "
              f"(visited so far: {len(visited)})", flush=True)

        # ── Download XMLs in parallel ─────────────────────────────────────
        def _fetch_xml_for(item: tuple[str, int]):
            name, lvl = item
            job       = visited[name]
            xml       = _get_xml(f"{job['url']}/config.xml", auth)
            return name, lvl, xml

        xml_results: list[tuple[str, int, str | None]] = []
        with ThreadPoolExecutor(max_workers=16) as pool:
            for name, lvl, xml in pool.map(_fetch_xml_for, batch):
                xml_results.append((name, lvl, xml))

        # Save XMLs and collect all child names referenced in them
        # child_names_by_parent: parent_name → [child_name, ...]
        child_names_by_parent: dict[str, list[str]] = {}

        for name, lvl, xml in xml_results:
            if xml:
                path = CONFIG_DIR / _safe_filename(name)
                path.write_text(xml, encoding="utf-8")

                raw_refs = _extract_refs(xml)
                children = [r for r in raw_refs if _looks_like_job(r) and r != name]
                if children:
                    child_names_by_parent[name] = children
            else:
                print(f"    [WARN] Could not download config.xml for {name}", flush=True)

        # Collect every unique child name across this whole level
        all_child_names: list[str] = []
        seen_this_level: set[str]  = set()
        for children in child_names_by_parent.values():
            for child in children:
                if child not in seen_this_level:
                    seen_this_level.add(child)
                    all_child_names.append(child)

        # Filter to only names not yet visited or queued
        new_names = [n for n in all_child_names if n not in visited and n not in already_queued]

        # ── Resolve new names to Jenkins URLs in parallel ─────────────────
        if new_names:
            print(f"    Resolving {len(new_names)} new job name(s) via API ...", flush=True)

            def _resolve(name: str):
                return name, _resolve_name(name, jenkins_url, auth)

            with ThreadPoolExecutor(max_workers=16) as pool:
                for name, meta in pool.map(_resolve, new_names):
                    if meta:
                        child_level = current_level + 1
                        visited[name] = {
                            "name":   meta["name"],
                            "url":    meta["url"],
                            "_class": meta["_class"],
                            "level":  child_level,
                        }
                        # Use resolved fullName as canonical name
                        if meta["name"] != name:
                            # remap any references that used the short name
                            visited[meta["name"]] = visited.pop(name)
                            name = meta["name"]
                        xml_queue.append((name, child_level))
                        already_queued.add(name)
                    else:
                        unresolved.append(name)
                        already_queued.add(name)   # don't retry

        # ── Record adjacency using resolved names ─────────────────────────
        for parent, children in child_names_by_parent.items():
            resolved_children = []
            for child in children:
                # Use resolved fullName if available
                canonical = visited.get(child, {}).get("name", child)
                if canonical not in resolved_children:
                    resolved_children.append(canonical)
            if resolved_children:
                adjacency[parent] = resolved_children

    return list(visited.values()), adjacency, unresolved


# ── Entry point ────────────────────────────────────────────────────────────

def run():
    jenkins_root = os.environ.get("JENKINS_ROOT_URL", "").rstrip("/")
    jenkins_url  = os.environ.get("JENKINS_URL", "").rstrip("/")
    user         = os.environ.get("JENKINS_USER",  "")
    token        = os.environ.get("JENKINS_TOKEN", "")

    if not jenkins_root:
        raise RuntimeError("JENKINS_ROOT_URL is not set. Add it to your .env file.")
    # Derive base URL from root URL if not explicitly set
    if not jenkins_url:
        from urllib.parse import urlparse as _urlparse
        _p = _urlparse(jenkins_root)
        jenkins_url = f"{_p.scheme}://{_p.netloc}"
    if not user or not token:
        raise RuntimeError("JENKINS_USER and/or JENKINS_TOKEN are not set.")

    auth = (user, token)

    print("=" * 60)
    print("fetch_xml.py — Config XML BFS Discovery")
    print("=" * 60)

    # ── Prepare output directory ─────────────────────────────────────────
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_DIR.exists():
        removed = 0
        for f in CONFIG_DIR.iterdir():
            if f.is_file():
                f.unlink()
                removed += 1
        if removed:
            print(f"\nCleared {removed} file(s) from {CONFIG_DIR}")

    # ── Step 1: BFS via config XMLs ──────────────────────────────────────
    print("\nSTEP 1 — BFS via config XML references")
    print("-" * 60)
    all_jobs, adjacency, unresolved = _discover_jobs(jenkins_root, jenkins_url, auth)

    edge_count = sum(len(dsts) for dsts in adjacency.values())
    print(f"\nFound {len(all_jobs)} jobs, {edge_count} edges, {len(unresolved)} unresolved.")

    # ── Step 2: Save registry ────────────────────────────────────────────
    print("\nSTEP 2 — Save registry")
    print("-" * 60)

    # Build reverse (upstream) map from the adjacency dict
    upstream: dict[str, list[str]] = {}
    for parent, children in adjacency.items():
        for child in children:
            upstream.setdefault(child, []).append(parent)

    registry = {
        "root":     jenkins_root,
        "strategy": "xml-bfs",
        "jobs": {
            j["name"]: {
                "url":             j["url"],
                "class":           j["_class"],
                "level":           j.get("level", -1),
                "downstream_jobs": adjacency.get(j["name"], []),
                "upstream_jobs":   upstream.get(j["name"], []),
            }
            for j in all_jobs
        },
    }
    REGISTRY.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(f"  Saved {len(all_jobs)} jobs, {edge_count} edges -> {REGISTRY}")

    # Write levels_xml.txt
    levels_by_idx: dict[int, list[str]] = {}
    for j in all_jobs:
        lvl = j.get("level", -1)
        levels_by_idx.setdefault(lvl, []).append(j["name"])
    sections = []
    for lvl, names in sorted(levels_by_idx.items()):
        heading = f"Level {lvl}" if lvl >= 0 else "Level unknown"
        sections.append(f"{heading}\n" + "-" * len(heading) + "\n" + "\n".join(sorted(names)))
    LEVELS_FILE.write_text("\n\n".join(sections), encoding="utf-8")
    print(f"  Wrote {LEVELS_FILE.name}  ({len(levels_by_idx)} level(s), {len(all_jobs)} jobs)")

    # Write unresolved_jobs.txt
    if unresolved:
        plain_list = "Unresolved Jobs — Plain List\n" + "=" * 50 + "\n" + "\n".join(sorted(unresolved))
        tree_text  = _render_unresolved_trees(unresolved, adjacency)
        UNRESOLVED_FILE.write_text(plain_list + "\n\n\n" + tree_text, encoding="utf-8")
        print(f"  Wrote {UNRESOLVED_FILE.name}  ({len(unresolved)} unresolved names)")
        print("\n  Unresolved (referenced in XMLs but not found on Jenkins):")
        for name in sorted(unresolved):
            print(f"    - {name}")
    else:
        UNRESOLVED_FILE.write_text("(none)", encoding="utf-8")
        print(f"  No unresolved jobs.")

    # ── Step 3b: Build pipeline tree ─────────────────────────────────────
    print("\nSTEP 3b — Build pipeline tree")
    print("-" * 60)
    write_tree(registry, _OUT_DIR / "pipeline_tree.txt")

    print(f"\n{'=' * 60}")
    print(f"fetch_xml.py complete.")
    print(f"  Total jobs      : {len(all_jobs)}")
    print(f"  Total edges     : {edge_count}")
    print(f"  Unresolved refs : {len(unresolved)}")
    print("=" * 60)
    return len(all_jobs)


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Load the nearest .env from CWD upward so the skill works in any repo.
    _cwd = Path.cwd()
    for _candidate in [_cwd, *_cwd.parents]:
        _env_file = _candidate / ".env"
        if _env_file.exists():
            load_dotenv(dotenv_path=_env_file)
            break
    run()
