"""Read-only disk usage check on EC2 runner via WinRM."""
import sys, warnings, os
warnings.filterwarnings('ignore')

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.github', 'skills', 'runner-inspector', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.github', 'skills', 'devops-setup', 'scripts'))

from winrm_explorer import run_cmd

def section(title, cmd):
    print(f'\n=== {title} ===')
    result = run_cmd(cmd, silent=True)
    print(result)

# run_cmd already runs inside a PowerShell session (run_ps) — pass PS code directly, no extra wrapper

# 1. U: drive free space
section('U: drive space',
    '$d = Get-PSDrive U -ErrorAction SilentlyContinue\n'
    'if ($d) { "Used: {0:N0} GB   Free: {1:N0} GB" -f ($d.Used/1GB), ($d.Free/1GB) }\n'
    'else { "U: not mounted" }'
)

# 2. Top-level folders under U:\2026.3.0.120
section('U:\\2026.3.0.120 folder list',
    'Get-ChildItem "U:\\2026.3.0.120" -Directory -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime'
)

# 3. SetupBuilder/Output size
section('SetupBuilder\\Output size (may take a minute)',
    'if (Test-Path "U:\\2026.3.0.120\\SetupBuilder\\Output") {\n'
    '  $files = Get-ChildItem "U:\\2026.3.0.120\\SetupBuilder\\Output" -Recurse -ErrorAction SilentlyContinue\n'
    '  $sz = ($files | Measure-Object -Property Length -Sum).Sum\n'
    '  "SetupBuilder\\Output: {0:N0} MB  ({1} files)" -f ($sz/1MB), $files.Count\n'
    '} else { "SetupBuilder\\Output not found" }'
)

# 4. build/logs size
section('build\\logs size',
    'if (Test-Path "U:\\2026.3.0.120\\build\\logs") {\n'
    '  $files = Get-ChildItem "U:\\2026.3.0.120\\build\\logs" -Recurse -ErrorAction SilentlyContinue\n'
    '  $sz = ($files | Measure-Object -Property Length -Sum).Sum\n'
    '  "build\\logs: {0:N0} MB  ({1} files)" -f ($sz/1MB), $files.Count\n'
    '} else { "build\\logs not found" }'
)

# 5. C:\GitLab-Runner\builds top-level
section('C:\\GitLab-Runner\\builds',
    'if (Test-Path "C:\\GitLab-Runner\\builds") {\n'
    '  Get-ChildItem "C:\\GitLab-Runner\\builds" -Directory -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime\n'
    '} else { "builds dir not found" }'
)

print('\n=== DONE ===')
