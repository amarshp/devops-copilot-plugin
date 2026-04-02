---
name: pipeline-monitor
description: 'Monitor GitLab CI/CD pipelines, check job status, watch for completions, and download logs. Use when: checking if a pipeline is running, watching a pipeline, downloading job logs, getting status counts by state, monitoring child pipelines and bridges.'
argument-hint: 'pipeline id or "latest" — describe monitoring goal'
---

# Pipeline Monitor

Consolidated tooling for tracking GitLab pipeline execution. Four scripts replace the 10+ `_check_*`, `_poll_*`, `_watch_*`, and `_download_*` scripts. No more hunting for the right script — use this skill.

## When to Use
- "What is the status of pipeline `<id>`?"
- "Which jobs are failing in the latest pipeline?"
- "Watch pipeline `<id>` and tell me when it finishes"
- "Download the log for job `<job_name>`"
- "Show me the full pipeline hierarchy including child pipelines"

## Prerequisites
- `GITLAB_TOKEN`, `GITLAB_PROJECT_ID`, `GITLAB_BRANCH` set in `.env`
- `pip install -r .github/requirements.txt`

## Commands

### Quick Status Check
```powershell
# Grouped by status:
python .github/skills/pipeline-monitor/scripts/poll_status.py <PIPELINE_ID>

# Status counts only (fast overview):
python .github/skills/pipeline-monitor/scripts/poll_status.py <PIPELINE_ID> --quick

# Latest pipeline on GITLAB_BRANCH:
python .github/skills/pipeline-monitor/scripts/poll_status.py --latest --quick

# JSON output:
python .github/skills/pipeline-monitor/scripts/poll_status.py --latest --json
```

### Full Hierarchy Monitor
Shows root + child pipelines + bridge jobs (for multi-project pipelines):
```powershell
python .github/skills/pipeline-monitor/scripts/monitor.py
# or:
python .github/skills/pipeline-monitor/scripts/monitor.py --pipeline-id <id> --snapshots 10 --interval 20
```

### Download Logs
```powershell
# All success + failed jobs:
python .github/skills/pipeline-monitor/scripts/download_logs.py <PIPELINE_ID>

# Failed jobs only:
python .github/skills/pipeline-monitor/scripts/download_logs.py <PIPELINE_ID> --failed-only

# Single job by name:
python .github/skills/pipeline-monitor/scripts/download_logs.py <PIPELINE_ID> --job "<job_name>"

# Jobs matching a pattern:
python .github/skills/pipeline-monitor/scripts/download_logs.py <PIPELINE_ID> --pattern ".Main"

# Latest pipeline:
python .github/skills/pipeline-monitor/scripts/download_logs.py --latest --failed-only
```

### Watch (continuous, writes alerts file)
Run in background; exits when all jobs reach terminal state:
```powershell
python .github/skills/pipeline-monitor/scripts/watch.py <PIPELINE_ID> --interval 60
python .github/skills/pipeline-monitor/scripts/watch.py --latest --alerts-file my_alerts.txt
```

## Output Files
| File | Contents |
|------|----------|
| `pipeline_logs/p<id>_<job>.log` | Job execution log (ANSI stripped) |
| `pipeline_logs/_alerts_<id>.txt` | Job completion events (from watch.py) |

## Stop Conditions
- HTTP 401/403 → check `GITLAB_TOKEN` permissions (needs `api` or `read_api` scope)
- Pipeline not found → verify `GITLAB_PROJECT_ID` and pipeline ID
- Log download returns empty → job may not have a trace yet (too early or just created)
