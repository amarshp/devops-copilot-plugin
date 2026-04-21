"""Check runner workspace for April 20 activity and SetupBuilder sizes."""
import sys, warnings, os
warnings.filterwarnings('ignore')
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.github', 'skills', 'runner-inspector', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.github', 'skills', 'devops-setup', 'scripts'))
from winrm_explorer import run_cmd

# 1. Files/folders modified on April 20 anywhere on C:\
print("=== C:\\GitLab-Runner\\builds dirs modified Apr 20 ===")
print(run_cmd(
    'Get-ChildItem "C:\\GitLab-Runner\\builds" -Recurse -Depth 3 -Directory -ErrorAction SilentlyContinue'
    ' | Where-Object { $_.LastWriteTime -gt [datetime]"2026-04-19" }'
    ' | Select-Object FullName, LastWriteTime | Format-Table -AutoSize',
    silent=True
))

# 2. Apr 13 SetupBuilder subfolders sizes
print("=== U:\\2026.3.0.120\\SetupBuilder folder structure ===")
print(run_cmd(
    'Get-ChildItem "U:\\2026.3.0.120\\SetupBuilder" -Recurse -Depth 2 -Directory -ErrorAction SilentlyContinue'
    ' | Select-Object FullName, LastWriteTime | Format-Table -AutoSize',
    silent=True
))

# 3. Check if the Apr 20 job wrote to a DIFFERENT workspace path
print("=== U:\\2026.3.0.120\\build\\logs files from Apr 20 ===")
print(run_cmd(
    'Get-ChildItem "U:\\2026.3.0.120\\build\\logs" -ErrorAction SilentlyContinue'
    ' | Where-Object { $_.LastWriteTime -gt [datetime]"2026-04-19" }'
    ' | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize',
    silent=True
))

# 4. Total size of U:\2026.3.0.120\SetupBuilder (all subdirs, not just Output)
print("=== U:\\2026.3.0.120\\SetupBuilder total size ===")
print(run_cmd(
    'if (Test-Path "U:\\2026.3.0.120\\SetupBuilder") {'
    '  $files = Get-ChildItem "U:\\2026.3.0.120\\SetupBuilder" -Recurse -ErrorAction SilentlyContinue;'
    '  $sz = ($files | Measure-Object -Property Length -Sum).Sum;'
    '  "Total: {0:N0} MB  ({1} files)" -f ($sz/1MB), $files.Count'
    '} else { "Not found" }',
    silent=True
))

print("\n=== DONE ===")
