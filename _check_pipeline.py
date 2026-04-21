"""Check pipeline status for a given pipeline ID."""
import sys
sys.path.insert(0, '.github/skills/devops-setup/scripts')
import warnings
warnings.filterwarnings('ignore')
import config as cfg_mod
import gitlab

gl = gitlab.Gitlab(cfg_mod.GITLAB_URL, private_token=cfg_mod.GITLAB_TOKEN, ssl_verify=False)
project = gl.projects.get(cfg_mod.PROJECT_ID)

pipeline_id = int(sys.argv[1]) if len(sys.argv) > 1 else 11172142
pipe = project.pipelines.get(pipeline_id)
print(f"Pipeline {pipeline_id}: {pipe.status}  url={pipe.web_url}")

jobs = pipe.jobs.list(get_all=True)
failed = [j for j in jobs if j.status == 'failed']
running = [j for j in jobs if j.status == 'running']
pending = [j for j in jobs if j.status in ('pending', 'created')]
success = [j for j in jobs if j.status == 'success']

print(f"\n  success: {len(success)}  running: {len(running)}  pending: {len(pending)}  failed: {len(failed)}")
for j in sorted(jobs, key=lambda x: x.id):
    print(f"  {j.status:12} {j.name}")
