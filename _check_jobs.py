"""Quick check of per-job status for a running pipeline."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".github", "skills", "devops-setup", "scripts"))
import config
import gitlab

gl = gitlab.Gitlab(config.GITLAB_URL, private_token=config.GITLAB_TOKEN, ssl_verify=False)
gl.auth()
project = gl.projects.get(config.PROJECT_ID)
pipeline = project.pipelines.get(int(sys.argv[1]))
jobs = pipeline.jobs.list(get_all=True)
print(f"Pipeline {pipeline.id} ({pipeline.status}) — {len(jobs)} jobs\n")
print(f"{'Job':<45} {'Stage':<20} {'Status':<12} {'Duration':>8}")
print("-" * 90)
for j in sorted(jobs, key=lambda x: (x.created_at or "", x.id)):
    dur = f"{j.duration:.0f}s" if j.duration else "-"
    print(f"{j.name:<45} {j.stage:<20} {j.status:<12} {dur:>8}")
