---
name: pipeline-decoupler
description: 'Analyze and decouple GitLab CI/CD pipelines for skip-ahead execution. Use when: decoupling pipelines, analyzing job dependencies, splitting monolithic CI/CD, adding skip-ahead capability, reducing pipeline re-run time, identifying bottlenecks in GitLab CI.'
argument-hint: 'Path to pipeline directory or describe the decoupling task'
---

# GitLab CI/CD Pipeline Decoupler

## Project Context And Execution Model
- Read `DEVOPS_PROJECT_CONTEXT.md` before running this skill.
- If the file is missing or does not define the optimization goal, pipeline paths in scope, writable paths, and read-only boundaries, ask clarifying questions first and update it.
- Keep `.github/` read-only during normal plugin usage unless the user explicitly asked to modify the plugin itself.
- Commands and scripts under `.github/skills/` are reference implementations and templates. Only run them if this repo proves they are the correct runnable assets here.
- If the repo needs custom optimization automation, create or adapt project-local scripts outside `.github/`.

## When to Use
- User asks to analyze a GitLab CI/CD pipeline's dependency structure
- User wants to decouple or split a monolithic pipeline into phases
- User wants to add skip-ahead capability (resume from a specific phase)
- User needs to identify bottleneck jobs in a pipeline
- User wants to reduce re-run time after failures in long pipelines
- User is migrating from Jenkins and wants to optimize the GitLab pipeline structure

## Prerequisites
- Reference environment setup pattern: `pip install -r .github/requirements.txt`
- Pipeline must have `.gitlab-ci.yml` with `include: local:` structure

## Setup (first time per project)
Copy the entire `.github/` folder to the target project root. The tool is self-contained:
```

After the plugin is installed, treat `.github/` as plugin source code. Do not edit it during normal plugin usage unless the user explicitly asked to modify the plugin itself.
.github/
├── agents/pipeline-optimizer.agent.md   ← Use for optimization and decoupling guidance
└── skills/pipeline-decoupler/
    ├── SKILL.md                         ← This file (auto-detected skill)
    ├── run.py                           ← CLI entry point
    └── scripts/                         ← Python package
        ├── analyzer.py
        ├── decoupler.py
        └── cli.py
```

## Procedure

### Step 1: Analyze the Pipeline
Run the analyzer to understand the dependency graph, bottlenecks, and natural phase boundaries.

Treat this as a reference command. Verify that the current repo uses this entry point before executing it unchanged.

```bash
python .github/skills/pipeline-decoupler/run.py analyze <pipeline_dir> --json
```

Arguments:
- `<pipeline_dir>`: Directory containing `.gitlab-ci.yml`
- `--ci-file`: Main CI file name (default: `.gitlab-ci.yml`)
- `--json`: Also writes `pipeline_analysis.json` for programmatic use

The analyzer outputs:
- Complete topological ordering of all jobs
- Dependency chain (which job needs which)
- Bottleneck jobs (jobs with most downstream dependents)
- Automatic phase identification with suggested boundaries

### Step 2: Review Phase Boundaries
Examine the identified phases and validate they make sense:
- Each phase should represent a logical unit of work
- Bottleneck jobs at phase boundaries should be real checkpoints
- Cross-phase dependencies identify what bootstrap jobs need to provide

### Step 3: Generate Decoupled Pipeline
Run the decoupler to produce modified pipeline files.

Treat these as reference commands. If the repo has adapted decoupling tooling, prefer that verified local path.

```bash
python .github/skills/pipeline-decoupler/run.py decouple <pipeline_dir> --output-dir <output>
```

Or run both analyze + decouple in one command:
```bash
python .github/skills/pipeline-decoupler/run.py full <pipeline_dir> --output-dir <output>
```

This generates:
- Modified `.gitlab-ci.yml` with `RUN_FROM_PHASE` variable and conditional `include: rules:`
- Bootstrap job files (`ci/phases/bootstrap-phase-N.yml`) for each skippable phase
- `DECOUPLING_PLAN.md` documenting the phases and usage instructions

### Step 4: Apply Cross-Phase Needs Modifications
The `DECOUPLING_PLAN.md` lists all `needs:` entries that require `optional: true` to support skip-ahead. Apply these changes to the original stage YAML files.

For each cross-phase need:
```yaml
# Before
needs:
  - job: some-prior-phase-job
    artifacts: true

# After
needs:
  - job: some-prior-phase-job
    artifacts: true
    optional: true
  - job: bootstrap-phase-N
    artifacts: true
    optional: true
```

### Step 5: Validate
- Review the generated `.gitlab-ci.yml` for correctness
- Ensure all `include:` paths use forward slashes (GitLab requirement)
- Run `gitlab-ci-lint` if available to validate syntax
- Test with `RUN_FROM_PHASE=1` (full run) first, then test skip-ahead

## Key Concepts

### How Skip-Ahead Works
1. `include: rules:` conditionally loads job definition files per phase
2. When phases are skipped, a **bootstrap job** re-reads environment variables from the workspace
3. Cross-phase `needs:` use `optional: true` so they don't fail when upstream jobs don't exist
4. The persistent runner workspace contains outputs from prior successful runs

### Assumptions
- Runners use persistent workspaces (not ephemeral containers)
- Build outputs accumulate on the filesystem (not solely via GitLab artifacts)
- Dotenv artifact files persist on disk between pipeline runs

## Reference Files
- [Pipeline Analyzer](./scripts/analyzer.py) — Core analysis engine
- [Pipeline Decoupler](./scripts/decoupler.py) — Generates skip-ahead modifications
- [CLI](./scripts/cli.py) — Command-line interface
- [Runner](./run.py) — Entry point script
