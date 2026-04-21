"""Get total size of SetupBuilder tree on NAS."""
import sys, warnings, os
warnings.filterwarnings('ignore')
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.github', 'skills', 'runner-inspector', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.github', 'skills', 'devops-setup', 'scripts'))
from winrm_explorer import run_cmd

result = run_cmd(
    '$root = "U:\\2026.3.0.120\\SetupBuilder"\n'
    'if (Test-Path $root) {\n'
    '  $items = Get-ChildItem $root -Recurse -ErrorAction SilentlyContinue\n'
    '  $sz = ($items | Measure-Object -Property Length -Sum).Sum\n'
    '  $cnt = $items.Count\n'
    '  "Total SetupBuilder: $([math]::Round($sz/1MB,0)) MB ($cnt files)"\n'
    '} else { "Not found" }',
    silent=True
)
print(result)
