"""
GitLab CI/CD Pipeline Analyzer
Parses .gitlab-ci.yml + included files, builds dependency graph, identifies phases & bottlenecks.
"""

import yaml
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict, deque

# Top-level GitLab CI keywords (not job definitions)
GITLAB_KEYWORDS = {
    'stages', 'variables', 'include', 'default', 'workflow',
    'image', 'services', 'before_script', 'after_script',
    'cache', 'pages',
}


@dataclass
class JobInfo:
    """Represents a single GitLab CI job."""
    name: str
    stage: str = ""
    needs: List[Dict[str, Any]] = field(default_factory=list)
    extends: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    has_dotenv: bool = False
    dotenv_file: str = ""
    artifacts_paths: List[str] = field(default_factory=list)
    source_file: str = ""
    resource_group: str = ""
    timeout: str = ""
    tags: List[str] = field(default_factory=list)
    rules: List[Any] = field(default_factory=list)


@dataclass
class PhaseInfo:
    """A group of jobs forming a logical phase in the pipeline."""
    id: int
    name: str
    jobs: List[str]
    stages_covered: List[str]
    exit_job: str           # bottleneck job at end of this phase
    cross_phase_needs: Dict[str, List[str]]  # job -> [prior-phase jobs it needs]
    dotenv_sources: List[str]  # jobs producing dotenv that this phase consumes


@dataclass
class AnalysisResult:
    """Complete analysis of a GitLab CI pipeline."""
    pipeline_dir: str
    ci_file: str
    stages: List[str]
    total_jobs: int
    jobs: Dict[str, JobInfo]
    dep_graph: Dict[str, List[str]]   # job -> [jobs it depends on]
    rev_graph: Dict[str, List[str]]   # job -> [jobs that depend on it]
    topo_order: List[str]
    bottlenecks: List[Tuple[str, int]]  # (job_name, downstream_count)
    phases: List[PhaseInfo]
    dotenv_producers: List[str]
    include_files: List[str]

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = []
        lines.append(f"Pipeline: {self.ci_file}")
        lines.append(f"Stages: {len(self.stages)}  |  Jobs: {self.total_jobs}  |  Phases: {len(self.phases)}")
        lines.append(f"Dotenv producers: {', '.join(self.dotenv_producers) or 'none'}")
        lines.append("")

        lines.append("=== DEPENDENCY CHAIN (topological order) ===")
        for job_name in self.topo_order:
            job = self.jobs[job_name]
            deps = self.dep_graph.get(job_name, [])
            dep_str = " <- " + ", ".join(deps) if deps else " (root)"
            lines.append(f"  [{job.stage}]  {job_name}{dep_str}")
        lines.append("")

        lines.append("=== BOTTLENECKS (jobs with most downstream dependents) ===")
        for bn_name, count in self.bottlenecks[:10]:
            lines.append(f"  {bn_name}: {count} downstream jobs depend on this")
        lines.append("")

        lines.append("=== PHASES ===")
        for phase in self.phases:
            lines.append(f"\n--- Phase {phase.id}: {phase.name} ---")
            lines.append(f"  Exit job (bottleneck): {phase.exit_job}")
            lines.append(f"  Stages: {', '.join(phase.stages_covered)}")
            lines.append(f"  Jobs ({len(phase.jobs)}):")
            for j in phase.jobs:
                lines.append(f"    - {j}")
            if phase.cross_phase_needs:
                lines.append(f"  Cross-phase dependencies:")
                for j, deps in phase.cross_phase_needs.items():
                    lines.append(f"    {j} needs [{', '.join(deps)}] from prior phase(s)")
            if phase.dotenv_sources:
                lines.append(f"  Dotenv consumed from prior phases: {', '.join(phase.dotenv_sources)}")

        lines.append("")
        lines.append("=== SKIP-AHEAD CAPABILITY ===")
        for i, phase in enumerate(self.phases):
            if i == 0:
                lines.append(f"  RUN_FROM_PHASE=1 ({phase.name}): Full pipeline run")
            else:
                skipped = [p.name for p in self.phases[:i]]
                lines.append(f"  RUN_FROM_PHASE={i+1} ({phase.name}): Skip {', '.join(skipped)}")
                if phase.dotenv_sources:
                    lines.append(f"    -> Bootstrap job re-reads: {', '.join(phase.dotenv_sources)}")

        return "\n".join(lines)


class GitlabPipelineAnalyzer:
    """Parses and analyzes a GitLab CI/CD pipeline for decoupling opportunities."""

    def __init__(self, pipeline_dir: str):
        self.pipeline_dir = pipeline_dir
        self.stages: List[str] = []
        self.jobs: Dict[str, JobInfo] = {}
        self.templates: Dict[str, dict] = {}  # .hidden-name -> raw yaml dict
        self.pipeline_variables: Dict[str, Any] = {}
        self.include_files: List[str] = []

    def analyze(self, ci_file: str = ".gitlab-ci.yml") -> AnalysisResult:
        """Run full analysis on the pipeline."""
        full_path = os.path.join(self.pipeline_dir, ci_file)
        self._load_and_merge(full_path)
        self._resolve_extends()

        dep_graph = self._build_dep_graph()
        rev_graph = self._build_rev_graph(dep_graph)
        topo_order = self._topological_sort(dep_graph)
        dotenv_producers = self._find_dotenv_producers()
        bottlenecks = self._find_bottlenecks(dep_graph, rev_graph, topo_order)
        phases = self._identify_phases(dep_graph, rev_graph, topo_order, bottlenecks, dotenv_producers)

        return AnalysisResult(
            pipeline_dir=self.pipeline_dir,
            ci_file=ci_file,
            stages=list(self.stages),
            total_jobs=len(self.jobs),
            jobs=dict(self.jobs),
            dep_graph=dict(dep_graph),
            rev_graph=dict(rev_graph),
            topo_order=topo_order,
            bottlenecks=bottlenecks,
            phases=phases,
            dotenv_producers=dotenv_producers,
            include_files=list(self.include_files),
        )

    # ── YAML Loading ─────────────────────────────────────────────────────

    def _load_and_merge(self, filepath: str):
        """Parse a YAML file, process includes, extract jobs."""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Pipeline file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            return

        # Merge stages (union, preserve order)
        if 'stages' in data:
            for s in data['stages']:
                if s not in self.stages:
                    self.stages.append(s)

        # Merge pipeline variables
        if 'variables' in data and isinstance(data['variables'], dict):
            self.pipeline_variables.update(data['variables'])

        # Process includes
        if 'include' in data:
            includes = data['include']
            if isinstance(includes, dict):
                includes = [includes]
            base_dir = os.path.dirname(filepath)
            # Determine root dir (for 'local:' paths relative to repo root)
            root_dir = self.pipeline_dir
            for inc in includes:
                if isinstance(inc, str):
                    inc_path = os.path.join(root_dir, inc)
                elif isinstance(inc, dict) and 'local' in inc:
                    inc_path = os.path.join(root_dir, inc['local'].lstrip('/'))
                else:
                    continue
                # Normalize path
                inc_path = os.path.normpath(inc_path)
                if os.path.isfile(inc_path):
                    rel_path = os.path.relpath(inc_path, self.pipeline_dir)
                    if rel_path not in self.include_files:
                        self.include_files.append(rel_path)
                        self._load_and_merge(inc_path)

        # Extract jobs and templates
        for key, value in data.items():
            if key in GITLAB_KEYWORDS:
                continue
            if not isinstance(value, dict):
                continue

            if key.startswith('.'):
                # Hidden template
                self.templates[key] = value
            else:
                # Real job
                job = self._parse_job(key, value, filepath)
                self.jobs[key] = job

    def _parse_job(self, name: str, raw: dict, source_file: str) -> JobInfo:
        """Parse a raw YAML dict into a JobInfo."""
        job = JobInfo(name=name, source_file=os.path.relpath(source_file, self.pipeline_dir))

        if 'stage' in raw:
            job.stage = raw['stage']

        if 'extends' in raw:
            job.extends = raw['extends']

        if 'needs' in raw:
            job.needs = self._normalize_needs(raw['needs'])

        if 'variables' in raw and isinstance(raw['variables'], dict):
            job.variables = dict(raw['variables'])

        if 'resource_group' in raw:
            job.resource_group = str(raw.get('resource_group', ''))

        if 'timeout' in raw:
            job.timeout = str(raw.get('timeout', ''))

        if 'tags' in raw:
            job.tags = list(raw.get('tags', []))

        if 'rules' in raw:
            job.rules = list(raw.get('rules', []))

        # Check artifacts for dotenv
        artifacts = raw.get('artifacts', {})
        if isinstance(artifacts, dict):
            reports = artifacts.get('reports', {})
            if isinstance(reports, dict) and 'dotenv' in reports:
                job.has_dotenv = True
                job.dotenv_file = reports['dotenv']
            paths = artifacts.get('paths', [])
            if isinstance(paths, list):
                job.artifacts_paths = list(paths)

        return job

    def _normalize_needs(self, needs_raw) -> List[Dict[str, Any]]:
        """Normalize needs: entries to a consistent dict format."""
        result = []
        if not isinstance(needs_raw, list):
            return result
        for entry in needs_raw:
            if isinstance(entry, str):
                result.append({'job': entry, 'artifacts': True, 'optional': False})
            elif isinstance(entry, dict):
                result.append({
                    'job': entry.get('job', ''),
                    'artifacts': entry.get('artifacts', True),
                    'optional': entry.get('optional', False),
                })
        return result

    # ── Extends Resolution ───────────────────────────────────────────────

    def _resolve_extends(self):
        """Resolve extends: references, merging template properties into jobs."""
        for name, job in self.jobs.items():
            if job.extends and job.extends in self.templates:
                tmpl = self.templates[job.extends]
                # Inherit stage if not set
                if not job.stage and 'stage' in tmpl:
                    job.stage = tmpl['stage']
                # Inherit tags if not set
                if not job.tags and 'tags' in tmpl:
                    job.tags = list(tmpl.get('tags', []))
                # Inherit resource_group if not set
                if not job.resource_group and 'resource_group' in tmpl:
                    job.resource_group = str(tmpl.get('resource_group', ''))
                # Inherit timeout if not set
                if not job.timeout and 'timeout' in tmpl:
                    job.timeout = str(tmpl.get('timeout', ''))

    # ── Dependency Graph ─────────────────────────────────────────────────

    def _build_dep_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph: job -> [jobs it depends on]."""
        graph = defaultdict(list)
        for name, job in self.jobs.items():
            if job.needs:
                for need in job.needs:
                    dep_job = need['job']
                    if dep_job in self.jobs:
                        graph[name].append(dep_job)
            # Ensure every job appears even if no deps
            if name not in graph:
                graph[name] = []
        return dict(graph)

    def _build_rev_graph(self, dep_graph: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Build reverse graph: job -> [jobs that depend on it]."""
        rev = defaultdict(list)
        for job, deps in dep_graph.items():
            for dep in deps:
                rev[dep].append(job)
        # Ensure all jobs present
        for job in dep_graph:
            if job not in rev:
                rev[job] = []
        return dict(rev)

    # ── Topological Sort ─────────────────────────────────────────────────

    def _topological_sort(self, dep_graph: Dict[str, List[str]]) -> List[str]:
        """Kahn's algorithm for topological sort, using stage order to break ties."""
        in_degree = defaultdict(int)
        for job in dep_graph:
            in_degree.setdefault(job, 0)
            for dep in dep_graph.get(job, []):
                in_degree[job]  # ensure exists
        for job, deps in dep_graph.items():
            for dep in deps:
                in_degree[job] += 1  # wrong direction, fix below

        # Recompute properly
        in_degree = {job: 0 for job in dep_graph}
        for job, deps in dep_graph.items():
            for dep in deps:
                pass  # dep -> job means job depends on dep
        # Count incoming: for each edge (dep -> job), increment in_degree[job]
        # But our graph is job -> [deps it depends on], so edge is dep -> job
        in_degree = {job: 0 for job in dep_graph}
        for job, deps in dep_graph.items():
            in_degree[job] = len(deps)

        # Stage index for tie-breaking
        stage_idx = {s: i for i, s in enumerate(self.stages)}

        def sort_key(job_name):
            j = self.jobs.get(job_name)
            return (stage_idx.get(j.stage if j else '', 999), job_name)

        queue = sorted([j for j, d in in_degree.items() if d == 0], key=sort_key)
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)
            # Find all jobs that depend on current (i.e., current is in their deps list)
            for job, deps in dep_graph.items():
                if current in deps:
                    in_degree[job] -= 1
                    if in_degree[job] == 0:
                        queue.append(job)
                        queue.sort(key=sort_key)

        # Add any jobs not in graph (shouldn't happen, but safety)
        for job in self.jobs:
            if job not in result:
                result.append(job)

        return result

    # ── Dotenv Detection ─────────────────────────────────────────────────

    def _find_dotenv_producers(self) -> List[str]:
        """Find jobs that produce dotenv artifacts."""
        return [name for name, job in self.jobs.items() if job.has_dotenv]

    # ── Bottleneck Detection ─────────────────────────────────────────────

    def _find_bottlenecks(self, dep_graph, rev_graph, topo_order) -> List[Tuple[str, int]]:
        """Find bottleneck jobs — jobs with the most transitive downstream dependents."""
        all_jobs = set(self.jobs.keys())

        # Compute transitive dependents for each job using reverse BFS
        transitive_count = {}
        for job in all_jobs:
            visited = set()
            queue = deque()
            for dependent in rev_graph.get(job, []):
                if dependent not in visited:
                    visited.add(dependent)
                    queue.append(dependent)
            while queue:
                current = queue.popleft()
                for dependent in rev_graph.get(current, []):
                    if dependent not in visited:
                        visited.add(dependent)
                        queue.append(dependent)
            transitive_count[job] = len(visited)

        # Root jobs (no predecessors) are not interesting bottlenecks
        roots = {j for j, deps in dep_graph.items() if not deps}

        bottlenecks = []
        min_threshold = max(2, len(all_jobs) * 0.1)  # At least 10% of pipeline
        for job in all_jobs - roots:
            count = transitive_count.get(job, 0)
            if count >= min_threshold:
                bottlenecks.append((job, count))

        bottlenecks.sort(key=lambda x: -x[1])
        return bottlenecks

    # ── Phase Identification ─────────────────────────────────────────────

    def _identify_phases(self, dep_graph, rev_graph, topo_order, bottlenecks, dotenv_producers) -> List[PhaseInfo]:
        """Split pipeline into phases at bottleneck boundaries."""
        if not bottlenecks or len(self.jobs) < 4:
            return [self._make_phase(1, "full-pipeline", list(self.jobs.keys()), dep_graph, dotenv_producers, set())]

        # Select non-overlapping phase boundaries from top bottlenecks
        topo_positions = {job: i for i, job in enumerate(topo_order)}
        boundaries = []  # (topo_position, job_name)
        used = set()

        for bn_name, count in bottlenecks:
            pos = topo_positions.get(bn_name, -1)
            if pos < 0:
                continue
            # Minimum gap of 3 jobs between boundaries
            if all(abs(pos - p) >= 3 for p, _ in boundaries):
                # Don't place boundary at the very end (last 2 jobs)
                if pos < len(topo_order) - 2:
                    boundaries.append((pos, bn_name))
                    used.add(bn_name)
            if len(boundaries) >= 5:  # Max 6 phases
                break

        boundaries.sort()

        if not boundaries:
            return [self._make_phase(1, "full-pipeline", topo_order, dep_graph, dotenv_producers, set())]

        # Split topo_order into phases at boundary points
        phases = []
        start_idx = 0
        prior_jobs: Set[str] = set()

        for phase_num, (boundary_pos, bn_job) in enumerate(boundaries, 1):
            phase_jobs = topo_order[start_idx:boundary_pos + 1]
            name = self._suggest_phase_name(phase_jobs, phase_num)
            phase = self._make_phase(phase_num, name, phase_jobs, dep_graph, dotenv_producers, prior_jobs)
            phases.append(phase)
            prior_jobs.update(phase_jobs)
            start_idx = boundary_pos + 1

        # Remaining jobs form the last phase
        if start_idx < len(topo_order):
            remaining = topo_order[start_idx:]
            name = self._suggest_phase_name(remaining, len(phases) + 1)
            phase = self._make_phase(len(phases) + 1, name, remaining, dep_graph, dotenv_producers, prior_jobs)
            phases.append(phase)

        return phases

    def _make_phase(self, phase_id: int, name: str, jobs: List[str],
                    dep_graph: Dict[str, List[str]], dotenv_producers: List[str],
                    prior_phase_jobs: Set[str]) -> PhaseInfo:
        """Create a PhaseInfo for a group of jobs."""
        job_set = set(jobs)

        # Determine stages covered
        stages_covered = []
        for j in jobs:
            job = self.jobs.get(j)
            if job and job.stage and job.stage not in stages_covered:
                stages_covered.append(job.stage)

        # Cross-phase dependencies
        cross_needs = {}
        dotenv_sources = []
        for j in jobs:
            deps = dep_graph.get(j, [])
            external = [d for d in deps if d in prior_phase_jobs]
            if external:
                cross_needs[j] = external
                for d in external:
                    if d in dotenv_producers and d not in dotenv_sources:
                        dotenv_sources.append(d)

        # Exit job: last job in the list (by topo order)
        exit_job = jobs[-1] if jobs else ""

        return PhaseInfo(
            id=phase_id,
            name=name,
            jobs=list(jobs),
            stages_covered=stages_covered,
            exit_job=exit_job,
            cross_phase_needs=cross_needs,
            dotenv_sources=dotenv_sources,
        )

    def _suggest_phase_name(self, jobs: List[str], fallback_num: int) -> str:
        """Suggest a human-readable name for a phase based on its jobs."""
        stages = []
        for j in jobs:
            job = self.jobs.get(j)
            if job and job.stage and job.stage not in stages:
                stages.append(job.stage)

        # Heuristic: use keyword patterns with priority ordering
        all_text = " ".join(stages + jobs).lower()

        # Most specific patterns first
        if 'compile-backend' in all_text:
            return "compile-backends"
        if 'compile-infra' in all_text and 'compile-backend' not in all_text:
            return "compile-infra"
        if 'compile-setup' in all_text or 'local-mirror' in all_text or 'compile-prepare' in all_text:
            return "compile-prepare"
        if 'compile' in all_text:
            return "compile"
        if 'automation-engine' in all_text:
            return "automation-engine"
        if 'publish' in all_text or 'extension-pipeline' in all_text or 'robocopy-final' in all_text or 'robocopy' in all_text:
            return "publish"
        if 'tag' in all_text or 'label' in all_text or 'permission' in all_text:
            return "tag-and-label"
        if 'bomcheck' in all_text and 'compile' not in all_text:
            return "import-and-check"
        if 'get-source' in all_text or 'checkout' in all_text or 'provision' in all_text:
            return "get-source"
        if 'build-number' in all_text or 'compute-version' in all_text:
            return "build-number"
        if 'build-prepare' in all_text or 'net.use' in all_text or 'env-setup' in all_text:
            return "build-setup"
        if 'agents-build' in all_text or 'agents-remote' in all_text:
            return "agents-build"
        return f"phase-{fallback_num}"


def analyze_pipeline(pipeline_dir: str, ci_file: str = ".gitlab-ci.yml") -> AnalysisResult:
    """Convenience function to analyze a pipeline."""
    analyzer = GitlabPipelineAnalyzer(pipeline_dir)
    return analyzer.analyze(ci_file)
