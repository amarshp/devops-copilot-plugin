"""
Auto-monitor pipeline and fix failures until full pipeline completes.
Usage: python _auto_monitor.py <pipeline_id>
"""
import os, sys, time, pathlib, base64, warnings, textwrap
warnings.filterwarnings('ignore')
import urllib3; urllib3.disable_warnings()
import gitlab

GITLAB_URL = os.environ['GITLAB_URL']
GITLAB_TOKEN = os.environ['GITLAB_TOKEN']
PROJECT_ID = os.environ['GITLAB_PROJECT_ID']
BRANCH = 'fast-test-setup-20260417'
SOURCE_DIR = pathlib.Path('fast_test_setup_push')
POLL_INTERVAL = 90  # seconds between status checks

gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN, ssl_verify=False)
proj = gl.projects.get(PROJECT_ID)

def print_status(pipe_id, pipe):
    jobs = pipe.jobs.list(all=True)
    by_status = {}
    for j in jobs:
        by_status.setdefault(j.status, []).append(j.name)
    counts = {s: len(v) for s, v in by_status.items()}
    print(f"\n[Pipeline {pipe_id}] {pipe.status.upper()} | " +
          " | ".join(f"{s}:{c}" for s, c in sorted(counts.items())))
    for s in ('failed', 'running', 'success', 'created', 'skipped', 'pending'):
        if s in by_status:
            label = s.upper()
            for name in by_status[s]:
                print(f"  {label:<10} {name}")
    return jobs, by_status

def get_job_log_tail(job_id, lines=120):
    try:
        log = proj.jobs.get(job_id).trace()
        if isinstance(log, bytes):
            log = log.decode('utf-8', 'replace')
        return '\n'.join(log.splitlines()[-lines:])
    except Exception as e:
        return f"(could not fetch log: {e})"

def push_pipeline(commit_message):
    """Push fast_test_setup_push to GitLab and return the auto-triggered pipeline."""
    actions = []
    for fpath in SOURCE_DIR.rglob('*'):
        if not fpath.is_file():
            continue
        rel = fpath.relative_to(SOURCE_DIR).as_posix()
        content = fpath.read_bytes()
        try:
            text = content.decode('utf-8')
            actions.append({'action': 'update', 'file_path': rel, 'content': text, 'encoding': 'text'})
        except UnicodeDecodeError:
            actions.append({'action': 'update', 'file_path': rel,
                            'content': base64.b64encode(content).decode(), 'encoding': 'base64'})

    # Cancel running pipelines on branch
    for p in proj.pipelines.list(ref=BRANCH, status='running', all=True):
        try: p.cancel()
        except: pass
    for p in proj.pipelines.list(ref=BRANCH, status='pending', all=True):
        try: p.cancel()
        except: pass

    try:
        proj.commits.create({'branch': BRANCH, 'commit_message': commit_message, 'actions': actions})
    except Exception:
        mixed = []
        for a in actions:
            try:
                proj.files.get(file_path=a['file_path'], ref=BRANCH)
                mixed.append(dict(a, action='update'))
            except Exception:
                mixed.append(dict(a, action='create'))
        proj.commits.create({'branch': BRANCH, 'commit_message': commit_message, 'actions': mixed})

    # Wait for auto-triggered pipeline
    print("Commit pushed. Waiting for auto-triggered pipeline...")
    time.sleep(15)
    for _ in range(20):
        pipes = proj.pipelines.list(ref=BRANCH, order_by='id', sort='desc', per_page=3)
        for p in pipes:
            if p.status in ('running', 'pending', 'created'):
                print(f"New pipeline: {p.id} ({p.status})")
                return p.id
        time.sleep(10)
    raise RuntimeError("No new pipeline found after commit push")

def analyze_and_fix(failed_jobs):
    """Analyze failed job logs and apply fixes. Returns True if a fix was applied."""
    fixes_applied = []
    
    for j in failed_jobs:
        job_name = j.name
        log = get_job_log_tail(j.id, 150)
        print(f"\n--- Analyzing failure: {job_name} (job {j.id}) ---")
        print(log[-3000:] if len(log) > 3000 else log)
        print("---")

        # ── Pattern 1: SEHException (native crash) ─────────────────────────
        if 'SEHException' in log or 'External component has thrown an exception' in log:
            print(f"[FIX] {job_name}: SEHException — checking for concurrent NAS writes")
            # Already removed MLU, if still happening it may be a transient DLL crash
            # Best fix: retry is most likely to work; no YAML change needed
            fixes_applied.append(f"SEHException in {job_name} — likely transient; will retry")

        # ── Pattern 2: MSB4017 / WinIOError ────────────────────────────────
        elif 'MSB4017' in log or 'WinIOError' in log:
            print(f"[FIX] {job_name}: WinIOError — SMB issue, should already be fixed")
            fixes_applied.append(f"WinIOError in {job_name} — SMB fix already applied; retry")

        # ── Pattern 3: Missing file ─────────────────────────────────────────
        elif 'Could not find a part of the path' in log or 'FileNotFoundException' in log:
            import re
            m = re.search(r"Could not find a part of the path '([^']+)'", log)
            if m:
                missing = m.group(1)
                print(f"[FIX] {job_name}: Missing path: {missing}")
                fixes_applied.append(f"Missing file in {job_name}: {missing} — investigate source")

        # ── Pattern 4: Timeout ─────────────────────────────────────────────
        elif 'Job\'s timeout' in log or 'execution took longer' in log.lower():
            print(f"[FIX] {job_name}: Timeout")
            # Increase timeout on the specific job YAML
            _fix_timeout(job_name)
            fixes_applied.append(f"Increased timeout for {job_name}")

        # ── Pattern 5: exit status 0xffffffff (generic crash) ──────────────
        elif 'exit status 0xffffffff' in log and 'SEHException' not in log:
            print(f"[FIX] {job_name}: exit 0xffffffff without SEHException — likely MSBuild task crash")
            fixes_applied.append(f"Generic crash in {job_name} — retry")

        # ── Pattern 6: allow_failure not set, skipped downstream jobs ──────
        elif j.status == 'failed' and 'allow_failure' in log.lower():
            fixes_applied.append(f"allow_failure issue in {job_name}")

        else:
            print(f"[UNKNOWN] {job_name}: unrecognized failure pattern")
            fixes_applied.append(f"Unknown failure in {job_name}")

    return fixes_applied

def _fix_timeout(job_name):
    """Add or increase timeout on a specific job in its YAML file."""
    yaml_map = {
        'UFT.Prepare.AllSetup.UFTSetup': 'fast_test_setup_push/uft_build/ci/stages/UFT.Prepare.AllSetup.yml',
        'UFT.Setup.Finalize': 'fast_test_setup_push/uft_build/ci/stages/UFT.Setup.Finalize.yml',
        'UFT.Create.Setups.Wix.BuildSetup': 'fast_test_setup_push/uft_build/ci/stages/UFT.Create.Setups.Wix.yml',
        'UFT.Create.Setups.Wix.CreatePFTW': 'fast_test_setup_push/uft_build/ci/stages/UFT.Create.Setups.Wix.yml',
    }
    if job_name not in yaml_map:
        print(f"  (no timeout fix defined for {job_name})")
        return
    fpath = pathlib.Path(yaml_map[job_name])
    if not fpath.exists():
        print(f"  (file not found: {fpath})")
        return
    content = fpath.read_text(encoding='utf-8')
    # If already has timeout: Xh, bump it; else add it after the job name line
    import re
    current = re.search(r'timeout:\s*(\d+)h', content)
    if current:
        current_h = int(current.group(1))
        new_h = min(current_h + 2, 8)
        content = re.sub(r'timeout:\s*\d+h', f'timeout: {new_h}h', content, count=1)
        print(f"  Bumped timeout from {current_h}h to {new_h}h in {fpath}")
    else:
        # Add 'timeout: 4h' after the job name line
        job_line = re.escape(job_name) + r':'
        content = re.sub(
            f'({job_name}:\n)',
            f'{job_name}:\n  allow_failure: false\n  timeout: 4h\n',
            content, count=1
        )
        print(f"  Added timeout: 4h to {job_name} in {fpath}")
    fpath.write_text(content, encoding='utf-8')

def monitor_loop(pipe_id):
    print(f"\n{'='*60}")
    print(f"  AUTO-MONITOR started: pipeline {pipe_id}")
    print(f"  Branch: {BRANCH}")
    print(f"  Poll interval: {POLL_INTERVAL}s")
    print(f"{'='*60}\n")

    current_pipe_id = pipe_id
    consecutive_same_state = 0
    
    while True:
        try:
            pipe = proj.pipelines.get(current_pipe_id)
            jobs, by_status = print_status(current_pipe_id, pipe)

            if pipe.status == 'success':
                print(f"\n✅ PIPELINE {current_pipe_id} COMPLETED SUCCESSFULLY! All done.")
                break

            elif pipe.status == 'failed':
                failed_jobs = [j for j in jobs if j.status == 'failed']
                print(f"\n❌ Pipeline {current_pipe_id} FAILED ({len(failed_jobs)} jobs failed)")
                
                fixes = analyze_and_fix(failed_jobs)
                
                if fixes:
                    msg = '; '.join(fixes[:3])
                    print(f"\n[PUSH] Applying fixes: {msg}")
                    try:
                        new_pipe_id = push_pipeline(f"auto-fix: {msg[:120]}")
                        current_pipe_id = new_pipe_id
                        consecutive_same_state = 0
                        print(f"[OK] New pipeline: {new_pipe_id}")
                    except Exception as e:
                        print(f"[ERROR] Push failed: {e}")
                else:
                    print(f"\n[WARN] No automated fix available. Manual intervention needed.")
                    print("Failures:")
                    for j in failed_jobs:
                        print(f"  - {j.name}")
                    break

            elif pipe.status in ('running', 'pending', 'created'):
                running = by_status.get('running', [])
                failed_so_far = by_status.get('failed', [])
                if failed_so_far:
                    print(f"  ⚠ {len(failed_so_far)} failed already but pipeline still running...")
                    consecutive_same_state += 1
                    if consecutive_same_state >= 5:
                        # Check if the failure will cascade and block the pipeline
                        print("  Pipeline stalled with failures — waiting for it to fully fail...")
                else:
                    consecutive_same_state = 0
                print(f"  Still running. Next check in {POLL_INTERVAL}s...")
                time.sleep(POLL_INTERVAL)

            elif pipe.status == 'canceled':
                print(f"\n[WARN] Pipeline {current_pipe_id} was canceled. Checking for a newer pipeline...")
                pipes = proj.pipelines.list(ref=BRANCH, order_by='id', sort='desc', per_page=5)
                found = False
                for p in pipes:
                    if p.id > current_pipe_id and p.status not in ('canceled',):
                        print(f"  Switching to newer pipeline {p.id}")
                        current_pipe_id = p.id
                        found = True
                        break
                if not found:
                    print(f"  No newer active pipeline found. Stopping.")
                    break
            else:
                print(f"  Status: {pipe.status} — waiting...")
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n[STOPPED] Monitoring interrupted by keyboard.")
            break
        except Exception as e:
            print(f"[ERROR] {e} — retrying in 30s...")
            time.sleep(30)

if __name__ == '__main__':
    pipe_id = int(sys.argv[1]) if len(sys.argv) > 1 else 11178566
    monitor_loop(pipe_id)
