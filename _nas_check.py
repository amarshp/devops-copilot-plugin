"""Check NAS info dir and what's consuming the 778GB."""
import sys, warnings, os
warnings.filterwarnings('ignore')
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.github', 'skills', 'runner-inspector', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.github', 'skills', 'devops-setup', 'scripts'))
from winrm_explorer import run_cmd

# 1. Check build/info - where DllDependancyGraph writes UFT_Duplicate.csv
print("=== U:\\2026.3.0.120\\build\\info dir ===")
print(run_cmd(
    'if (Test-Path "U:\\2026.3.0.120\\build\\info") {'
    '  Get-ChildItem "U:\\2026.3.0.120\\build\\info" -ErrorAction SilentlyContinue'
    '  | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize'
    '} else { "build\\info not found" }',
    silent=True
))

# 2. Check what Apr 20 files exist on U:
print("=== U:\\2026.3.0.120 files modified Apr 20 ===")
print(run_cmd(
    'Get-ChildItem "U:\\2026.3.0.120" -Recurse -File -ErrorAction SilentlyContinue'
    ' | Where-Object { $_.LastWriteTime -gt [datetime]"2026-04-19" }'
    ' | Select-Object FullName, Length, LastWriteTime'
    ' | Sort-Object Length -Descending | Select-Object -First 20 | Format-Table -AutoSize',
    silent=True
))

# 3. Top 10 folders by size on U:\ root to find what's consuming 778GB
print("=== U:\\ top folders (size) ===")
print(run_cmd(
    'Get-ChildItem "U:\\" -Directory -ErrorAction SilentlyContinue'
    ' | ForEach-Object {'
    '  $d = $_'
    '  $sz = (Get-ChildItem $d.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum'
    '  [PSCustomObject]@{ Name=$d.Name; SizeMB=[math]::Round($sz/1MB,0); Modified=$d.LastWriteTime }'
    '} | Sort-Object SizeMB -Descending | Format-Table -AutoSize',
    silent=True
))

print("\n=== DONE ===")
