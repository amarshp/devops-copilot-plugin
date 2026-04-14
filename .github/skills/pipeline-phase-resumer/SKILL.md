---
name: pipeline-phase-resumer
description: 'Create a fast-path GitLab CI pipeline that resumes from any logical phase by reusing a prior pipeline''s persistent workspace. Use when: you want to run only Addins, only Setup, or any downstream phase without re-running compilation; when you have a known-good reference pipeline whose outputs are still on the persistent runner workspace; when you need to iterate quickly on a late-stage failure without paying the full build cost each time.'
argument-hint: 'Phase to resume from (or say "discover" to explore available phases); optional reference pipeline ID; optional project ID, runner tag, and repo prefix for cross-project use'
---

# Pipeline Phase Resumer

## Project Context And Execution Model
- Read `DEVOPS_PROJECT_CONTEXT.md` before running this skill.
- If the file is missing or does not define the phase-resume goal, project in scope, writable paths, and read-only boundaries, ask clarifying questions first and update it.
- Keep `.github/` read-only during normal plugin usage unless the user explicitly asked to modify the plugin itself.
- Commands and scripts under `.github/skills/` are reference implementations and templates. Only run them if this repo proves they are the correct runnable assets here.
- If the repo needs custom resume automation, create or adapt project-local scripts outside `.github/`.

## What It Does

Creates a `fast_<phase>/` pipeline variant that:

1. Keeps the mandatory gate jobs (NET USE, env-setup, compute-version, compile-setup, LocalMirror)
2. Adds lightweight **bootstrap validator** jobs that confirm the reference workspace is intact on disk
3. Skips every phase **before** the target phase by replacing real compile-gate `needs:` with bootstrap validators
4. Runs the target phase (and all phases after it) exactly as the original pipeline would

The reference workspace is identified by three variables set in the generated `.gitlab-ci.yml`:

```yaml
FAST_RESUME_REFERENCE_BUILD_NUMBER:  "12"
FAST_RESUME_REFERENCE_BUILD_VERSION: "2026.3.12.0"
FAST_RESUME_REFERENCE_DESTDIR:       "E:/FT/QTP/win32_release/2026.3.12.0"
```

Update all three together whenever you want to point at a different reference build.

---

## When to Use

- You have a full pipeline that ran successfully up to (or past) a phase boundary
- The persistent runner still holds the compiled workspace from that run
- You want to iterate on a late-stage job (e.g. Addins, Setup, Publish) without paying the full compile cost
- You want a dedicated "mini pipeline" that teammates can trigger to test just one phase

---

## Prerequisites

- A persistent runner workspace for the jobs you plan to resume
- A reference pipeline that completed through the phase you want to skip past
- `DEVOPS_PROJECT_CONTEXT.md` updated with the project, runner, repo prefix, and resume scope
- Setup complete for any required GitLab access, tokens, and project identifiers
- A verified push/run path outside `.github/` for pipeline execution helpers such as `push_dummy.py`

---

## CLI Reference

All commands below are reference patterns under `run.py`. Use them only if the current repo proves this is the correct runnable entry point.

### `discover` — Scan any pipeline to see its phases (no prior knowledge needed)

```bash
python .github/skills/pipeline-phase-resumer/run.py discover <pipeline_dir>
```

Outputs:
- Logical phase groups (inferred from stage name prefixes)
- Gate job candidates (BomCheck pattern, sorted by downstream count)
- Which phases are already in the registry vs. need to be added

Use this as your **first command** when working with an unfamiliar pipeline or when you don't know what phase keys are valid.

### `check-prereqs` — Validate inputs before generate

```bash
python .github/skills/pipeline-phase-resumer/run.py check-prereqs <pipeline_dir> \
    --phase <phase> \
    [--env-file .env] \
    [--ref-build-number N] \
    [--ref-build-version X.Y.Z.W] \
    [--ref-destdir "E:/..."]
```

Outputs a structured PASS / WARN / FAIL report plus an ACTION PLAN for every failure.
Exit 0 if ready, exit 1 if any FAIL. Run this before `generate` to catch problems early.

### `analyze` — Show gate/include/patch detail for a registered phase

```bash
python .github/skills/pipeline-phase-resumer/run.py analyze <pipeline_dir> --phase <phase>
```

Outputs:
- Gate jobs that will be replaced by bootstrap validators
- Stage files included in the fast pipeline (✓ present / ✗ MISSING)
- Needs patches (which file, old gate → new bootstrap name)
- Workspace validation paths

### `generate` — Produce the fast_<phase> pipeline directory

```bash
python .github/skills/pipeline-phase-resumer/run.py generate \
    --source-dir <src_dir> \
    --output-dir <out_dir> \
    --phase <phase> \
    --ref-build-number <N> \
    --ref-build-version <X.Y.Z.W> \
    --ref-destdir "<path>" \
    [--repo-prefix uft_build]   \    # folder name at repo root (default: uft_build)
    [--runner-tag  ec2-runner]       # GitLab runner tag (default: ec2-runner)
```

The `--repo-prefix` and `--runner-tag` flags enable **cross-project usage**: set them to
match the target project's folder structure and runner tag.

What is generated:
- `fast_<phase>/.gitlab-ci.yml` — root pipeline, reuse vars set, only target-phase includes
- `fast_<phase>/ci/stages/fast-resume-bootstrap.yml` — validates cached workspace paths
- All stage files copied verbatim from source; only the gate-boundary files are patched

### `lint` — Validate YAML structure

```bash
python .github/skills/pipeline-phase-resumer/run.py lint --pipeline-dir <out_dir>
```

### `push` (external script)

```powershell
$env:GITLAB_BRANCH = 'fast-resume-<phase>-<date>'
uv run --with python-gitlab --with requests --with pyyaml `
  gitlab_pipeline/push_dummy.py `
  --source-dir <out_dir> `
  --repo-prefix <repo_prefix> `
  -m "fast resume: <phase>"
```

### `QC` (external script)

```powershell
$env:PYTHONUTF8 = 1
uv run --with requests gitlab_pipeline/_qc_compare.py <RESUME_PIPELINE_ID> <REF_PIPELINE_ID>
```

---

## Procedure (agent-guided)

The `phase-resumer` agent walks you through this interactively. For manual runs:

Treat the commands below as reference patterns. Verify the repo layout and available local tooling before executing them unchanged.

### Step 0 — Gather inputs

You need:
- Source pipeline directory (e.g. `migrated_yamls/uft_build`)
- Phase name (run `discover` if unsure)
- Reference build vars: `--ref-build-number`, `--ref-build-version`, `--ref-destdir`
  (from the `uft-build-compute-version` job log of any successful pipeline run)
- Runner tag (default: `ec2-runner`)
- Repo prefix (default: `uft_build`)

### Step 1 — Discover (if phase is unknown)

```bash
python run.py discover <source_dir>
```

### Step 2 — Check prerequisites

```bash
python run.py check-prereqs <source_dir> --phase <phase> --ref-build-number N ...
```

Resolve any FAIL items before proceeding.

### Step 3 — Analyze

```bash
python run.py analyze <source_dir> --phase <phase>
```

### Step 4 — Generate

```bash
python run.py generate --source-dir <src> --output-dir <out> --phase <phase> \
    --ref-build-number N --ref-build-version X.Y.Z.W --ref-destdir "..." \
    [--runner-tag <tag>] [--repo-prefix <prefix>]
```

### Step 5 — Lint

```bash
python run.py lint --pipeline-dir <out>
```

### Step 6 — Push → Run → QC

---

## Key Concepts

### Bootstrap validator job

A lightweight job (a few `if exist` checks) that stands in for every real compilation gate.
It validates that the reference workspace paths exist on disk — it does **not** recompile anything.
Its `stage:` matches the gate it replaces, so the DAG ordering is preserved.

### Cross-phase `needs:` patching

Jobs in the target phase that had `needs: [SomeGate.BomCheck]` are patched to point at
the bootstrap validator instead. All other `needs:` within the target phase are untouched.

### Dynamic vs. registered phases

The `discover` command works on **any** pipeline — no prior registration needed.
The `generate` command requires the phase to be in `PHASE_REGISTRY` (in `scripts/resumer.py`).
If your phase is not registered, use `discover` to find the gate jobs, then add an entry.
The `phase-resumer` agent can draft the registry entry for you.

### Cross-project usage

Set `--runner-tag` and `--repo-prefix` to match the target project. The skill is not
tied to UFT or `ec2-runner` — those are just defaults from the first real use case.

### What can and cannot be skipped

| Safe to skip | Not safe to skip |
|---|---|
| Source provisioning (MultiGit, Git.Src.Provision) | INFRA.Net.Use — network drives don't persist |
| All compile phases before the target phase | uft-build-env-setup — dotenv needed by all jobs |
| BuildNumber.Creator — replaced by reference vars | uft-build-compute-version — emits DestDir |
| Code-signing gates (always skipped in reference) | INFRA.Product.AllDependencies.LocalMirror |

---

## Phase Registry

Pre-configured phases (extend as migration expands):

| Phase key | Description | Gate jobs replaced |
|---|---|---|
| `addins` | All Addins compilation (QTCustSupport → SetupUtils) | `FrontEnd.Infra.BomCheck`, `FrontEnd.ReplayRecoveryUI.BomCheck`, `FrontEnd.ObjectRepository.BomCheck` |
| `setup` | Setup Generation (ALM/BTP → WiX installer) | `UFT.Compile.SetupUtils.BomCheck` |

To add a new phase: edit `PHASE_REGISTRY` in `scripts/resumer.py` following the existing pattern.
Use `discover` to identify the correct gate jobs and stage file list.

---

## File Layout

```
.github/skills/pipeline-phase-resumer/
  SKILL.md            ← this file
  run.py              ← CLI entry point
  scripts/
    __init__.py
    resumer.py        ← core logic: discover, check-prereqs, analyze, generate, lint
```

## Reference: fast_test (Addins phase)

The `fast_test` pipeline in `migrated_yamls/fast_test/` is the canonical real-world example.
It saved **56 minutes per run** (100 min → 44 min, 56% reduction).
See `gitlab_pipeline/fast_test_share/FAST_TEST_RUNBOOK.md` for the full runbook.
