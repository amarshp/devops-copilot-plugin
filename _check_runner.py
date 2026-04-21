import requests, os
requests.packages.urllib3.disable_warnings()
headers = {'PRIVATE-TOKEN': os.environ['GITLAB_TOKEN']}
base = os.environ['GITLAB_URL'] + 'api/v4/projects/128090/'
r = requests.get(base + 'pipelines/11184471/jobs', headers=headers, verify=False, timeout=15, params={'per_page': 100})
data = r.json()
print("Pipeline 11184471 jobs + runners:")
for j in sorted(data, key=lambda x: (x['stage'], x['name'])):
    runner = j.get('runner') or {}
    dur = j.get('duration') or 0
    print(f"  [{j['status']:12}] {j['name']:45} runner={runner.get('description','?'):20} ({dur:.0f}s)")
