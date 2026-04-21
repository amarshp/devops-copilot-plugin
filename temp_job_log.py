import requests, os, urllib3
urllib3.disable_warnings()
from dotenv import load_dotenv; load_dotenv()
token = os.environ.get('GITLAB_TOKEN') or os.environ.get('GL_TOKEN')
url = os.environ.get('GITLAB_URL','https://gitlab.otxlab.net')
pid = os.environ.get('GITLAB_PROJECT_ID','128090')

job_id = 47751304  # UFT.Prepare.AllSetup.UFTSetup.PreFlight
log_r = requests.get(f'{url}/api/v4/projects/{pid}/jobs/{job_id}/trace',
    headers={'PRIVATE-TOKEN':token}, verify=False)
lines = log_r.text.splitlines()
print(f"Total lines: {len(lines)}")
for l in lines:
    print(l)
