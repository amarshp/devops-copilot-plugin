import requests, os, sys
from dotenv import load_dotenv
load_dotenv()
import urllib3
urllib3.disable_warnings()

token = os.environ.get('GITLAB_TOKEN') or os.environ.get('GL_TOKEN')
url = os.environ.get('GITLAB_URL','https://gitlab.otxlab.net')
pid = os.environ.get('GITLAB_PROJECT_ID','128090')

H = {'PRIVATE-TOKEN': token}
TARGET_PIPELINE = 11225066

# Check timing of jobs to find overlap
for jid in [47756527, 47756528, 47756531]:
    r = requests.get(f'{url}/api/v4/projects/{pid}/jobs/{jid}', headers=H, verify=False).json()
    name = r.get('name','?')
    start = r.get('started_at','')[:19]
    fin = r.get('finished_at','')[:19]
    status = r.get('status','?')
    stage = r.get('stage','?')
    print(f'{name} (id={jid}) stage={stage} status={status} started={start} finished={fin}')
