"""Diagnose why the pipeline won't trigger by checking CI lint."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".github", "skills", "devops-setup", "scripts"))
import config
import requests
import json

url = f"{config.GITLAB_URL.rstrip('/')}/api/v4/projects/{config.PROJECT_ID}/ci/lint"
headers = {"PRIVATE-TOKEN": config.GITLAB_TOKEN}
r = requests.get(url, headers=headers, params={"ref": config.BRANCH, "dry_run": "true", "include_jobs": "true"}, verify=False)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Valid: {data.get('valid')}")
if data.get("errors"):
    print("Errors:")
    for e in data["errors"]:
        print(f"  - {e}")
if data.get("warnings"):
    print("Warnings:")
    for w in data["warnings"]:
        print(f"  - {w}")

# Check workflow rules in merged yaml
if data.get("merged_yaml"):
    try:
        import yaml
        merged = yaml.safe_load(data["merged_yaml"])
        if "workflow" in merged:
            print(f"\nWorkflow rules: {json.dumps(merged['workflow'], indent=2)}")
        job_names = [k for k in merged if not k.startswith(".") and isinstance(merged.get(k), dict) and "stage" in merged.get(k, {})]
        print(f"\nJobs found: {len(job_names)}")
        for j in job_names[:20]:
            print(f"  - {j}")
    except Exception as exc:
        print(f"Could not parse merged_yaml: {exc}")

# Also check project CI settings
proj_url = f"{config.GITLAB_URL.rstrip('/')}/api/v4/projects/{config.PROJECT_ID}"
r2 = requests.get(proj_url, headers=headers, verify=False)
if r2.ok:
    proj = r2.json()
    print(f"\nProject CI config path: {proj.get('ci_config_path', '(default)')}")
    print(f"Default branch: {proj.get('default_branch')}")
    print(f"Jobs enabled: {proj.get('jobs_enabled')}")
    print(f"Shared runners: {proj.get('shared_runners_enabled')}")

# List recent pipelines
pipes_url = f"{config.GITLAB_URL.rstrip('/')}/api/v4/projects/{config.PROJECT_ID}/pipelines"
r3 = requests.get(pipes_url, headers=headers, params={"per_page": 5}, verify=False)
if r3.ok:
    pipes = r3.json()
    print(f"\nRecent pipelines ({len(pipes)}):")
    for p in pipes:
        print(f"  ID={p['id']}  status={p['status']}  ref={p['ref']}  source={p.get('source','?')}")
