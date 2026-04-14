---
name: j2gl-qc
description: 'Run Jenkins-vs-GitLab QC with log download, comparison, analysis, and status tracking. Use when: comparing migration output, checking if GitLab job reproduces Jenkins behavior, downloading pipeline logs, scanning for MSBuild errors and warnings, updating QC tree status, appending to run history.'
argument-hint: 'job name plus Jenkins/GitLab log evidence paths'
---

# J2GL QC (Quality Control)

Validate that migrated GitLab CI jobs reproduce the equivalent Jenkins behavior. Uses LLM comparison of execution logs; a green GitLab pipeline is NOT a QC pass without log evidence.

## Project Context And Execution Model
- Read `DEVOPS_PROJECT_CONTEXT.md` before running this skill.
- If the file is missing or does not define the QC goal, evidence paths, and read-only boundaries, ask clarifying questions first and update it.
- Keep `.github/` read-only during normal plugin usage unless the user explicitly asked to modify the plugin itself.
- Commands and scripts under `.github/skills/` are reference implementations and templates. Only run them if this repo proves they are the correct runnable assets here.
- If the repo needs custom QC automation, create or adapt project-local scripts outside `.github/`.

## When to Use
- "Run QC on `<job_name>`"
- "Compare Jenkins log vs GitLab log for `<job>`"
- "Download logs from pipeline `<id>` and scan for errors"
- "Update QC status for `<job>` to `qc-pass`"
- After every migration attempt — determines SUCCESS / FAIL / BLOCKED

## Prerequisites
- `COPILOT_TOKEN` set in `.env` (LLM comparison)
- Jenkins log file available locally
- GitLab log downloaded (use pipeline-monitor skill or `qc_bulk_download.py`)

Treat the commands below as reference patterns. Verify that the current repo uses these tools and paths before executing them unchanged.

## Procedure

### Step 1: Download Pipeline Logs
Download and scan logs for all target jobs:

```powershell
python .github/skills/j2gl-qc/scripts/qc_bulk_download.py <PIPELINE_ID>
# or latest:
python .github/skills/j2gl-qc/scripts/qc_bulk_download.py --latest
# filter by name / status:
python .github/skills/j2gl-qc/scripts/qc_bulk_download.py <PIPELINE_ID> --pattern ".Main" --failed-only
# full options:
python .github/skills/j2gl-qc/scripts/qc_bulk_download.py --latest --job "<job_name>" --manifest qc_manifest.json --output-dir pipeline_logs
```

Output: `pipeline_logs/p<id>_<job_name>.log` + `pipeline_logs/qc_manifest_<id>.json`

### Step 2: LLM Log Comparison (single job)
Compare one GitLab log against the reference Jenkins log:

```powershell
python .github/skills/j2gl-qc/scripts/qc_compare_logs.py \
    --job-name "<local GitLab job name>" \
    --jenkins-job-name "<exact Jenkins job name>" \
    --jenkins-log "path/to/jenkins.log" \
    --gitlab-log "pipeline_logs/p<id>_<job_name>.log" \
    --mapping-notes "<brief explanation of how the jobs map>" \
    --output "qc_reports/<JOB>-run-<N>.md"
```

First line of output is always `QC_STATUS: SUCCESS` / `QC_STATUS: FAIL` / `QC_STATUS: BLOCKED`.

### Step 3: Bulk Analysis Report
Generate a multi-section analysis from all downloaded logs:

```powershell
python .github/skills/j2gl-qc/scripts/qc_analyze.py --pipeline-id <PIPELINE_ID>
# or analyze specific log dir:
python .github/skills/j2gl-qc/scripts/qc_analyze.py --log-dir pipeline_logs --all
```

### Step 4: Update QC Status Tracking
Automate QC tree + history updates after getting a QC report.
This also automatically regenerates `MIGRATION_STATUS.md`.

```powershell
python .github/skills/j2gl-qc/scripts/qc_status_tracker.py \
    --job "<job_name>" \
    --report "qc_reports/<JOB>-run-<N>.md" \
    --tree "QC_TREE.md" \
    --history "QC_RUN_HISTORY.md"
```

### Step 5: Regenerate Migration Dashboard (standalone)
Updates `MIGRATION_STATUS.md` with the latest scoreboard, annotated pipeline tree, and run log.
Called automatically by `qc_status_tracker.py` and `push_and_trigger.py`, but can be run manually:

```powershell
python .github/skills/j2gl-qc/scripts/migration_dashboard.py \
    --tree fetch_xml/pipeline_tree.txt \
    --history QC_RUN_HISTORY.md \
    --qc-dir qc_reports \
    --log-dir pipeline_logs \
    --output MIGRATION_STATUS.md
```

Output — `MIGRATION_STATUS.md` contains:
- **Scoreboard**: total jobs, % migrated, % QC passed, run count, current job, latest pipeline status
- **Pipeline tree**: every job annotated with 🟢/🔴/🟡/🔵/⚪ migration + QC status
- **Run log**: per-pipeline table of job results with error counts and recommended fixes

## QC Status Rules
| Status | Meaning |
|--------|--------|
| `QC_STATUS: SUCCESS` | Job may be marked `qc-pass` in QC tree |
| `QC_STATUS: FAIL` | Behavior not equivalent; root cause fix needed |
| `QC_STATUS: BLOCKED` | External dependency prevents judgment (auth, infra, missing runner resource) |

## Stop Conditions
- Infrastructure denial (401/403, missing network share, unavailable secret) → `BLOCKED`, not `FAIL`
- LLM unavailable → fall back to manual log comparison
- Jenkins log not available → record as `BLOCKED` — do not assume SUCCESS

## Evidence Rules
- Every QC attempt must be recorded in run history (date, pipeline ID, job, status, next action)
- Only update QC tree after a QC report file exists with a `QC_STATUS:` first line
- Never backfill history with generic summaries — preserve concrete evidence
