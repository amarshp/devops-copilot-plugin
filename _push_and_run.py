"""Direct GitLab API push + pipeline trigger for fast_test_setup_push."""
import os, sys, pathlib, base64, warnings
warnings.filterwarnings('ignore')
import urllib3; urllib3.disable_warnings()
import gitlab

GITLAB_URL = os.environ['GITLAB_URL']
GITLAB_TOKEN = os.environ['GITLAB_TOKEN']
PROJECT_ID = os.environ['GITLAB_PROJECT_ID']
BRANCH = 'fast-test-setup-20260417'
SOURCE_DIR = pathlib.Path('fast_test_setup_push')

commit_message = sys.argv[1] if len(sys.argv) > 1 else 'pipeline update'

gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN, ssl_verify=False)
proj = gl.projects.get(PROJECT_ID)

# Cancel any running pipelines on the branch
for pipe in proj.pipelines.list(ref=BRANCH, status='running', all=True):
    print(f'Cancelling pipeline {pipe.id}...')
    pipe.cancel()
for pipe in proj.pipelines.list(ref=BRANCH, status='pending', all=True):
    print(f'Cancelling pipeline {pipe.id}...')
    pipe.cancel()

# Build actions list from all files in source dir
actions = []
for fpath in SOURCE_DIR.rglob('*'):
    if not fpath.is_file():
        continue
    rel = fpath.relative_to(SOURCE_DIR).as_posix()
    content = fpath.read_bytes()
    try:
        text = content.decode('utf-8')
        actions.append({'action': 'create', 'file_path': rel, 'content': text, 'encoding': 'text'})
    except UnicodeDecodeError:
        actions.append({'action': 'create', 'file_path': rel,
                        'content': base64.b64encode(content).decode(), 'encoding': 'base64'})

# Try update first, fall back to create for each file individually if bulk fails
# Use a single commit with all files
print(f'Pushing {len(actions)} files to branch {BRANCH}...')

# First try all as 'update', fall back to 'create' for new files
update_actions = [dict(a, action='update') for a in actions]
try:
    proj.commits.create({
        'branch': BRANCH,
        'commit_message': commit_message,
        'actions': update_actions,
    })
    print('Commit (update) succeeded.')
except Exception as e:
    print(f'Update failed ({e}), retrying with create...')
    try:
        proj.commits.create({
            'branch': BRANCH,
            'commit_message': commit_message,
            'actions': actions,
        })
        print('Commit (create) succeeded.')
    except Exception as e2:
        # Try mixed: update existing, create new
        print(f'Create also failed ({e2}), trying mixed actions...')
        mixed = []
        for a in actions:
            try:
                proj.files.get(file_path=a['file_path'], ref=BRANCH)
                mixed.append(dict(a, action='update'))
            except Exception:
                mixed.append(dict(a, action='create'))
        proj.commits.create({
            'branch': BRANCH,
            'commit_message': commit_message,
            'actions': mixed,
        })
        print('Commit (mixed) succeeded.')

# The commit push auto-triggers a pipeline via workflow:rules (push event).
# Do NOT call pipelines.create() here — that would fire a second pipeline
# on a potentially wrong runner.
print('Commit pushed. Pipeline will auto-trigger via workflow:rules (push event).')
print(f'Check: {GITLAB_URL}/{proj.path_with_namespace}/-/pipelines?ref={BRANCH}')
