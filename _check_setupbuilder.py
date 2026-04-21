import os, warnings
warnings.filterwarnings('ignore')
import urllib3; urllib3.disable_warnings()
import winrm

s = winrm.Session('10.168.244.176', auth=('_ft_auto_admin', 'W3lcome1'),
                  transport='ntlm', server_cert_validation='ignore')

ps = r"""
# Check destination directories that MLUSetup / AllSetup would write to
$paths = @(
    "U:\2026.3.0.120\SetupBuilder",
    "U:\2026.3.0.120\SetupBuilder\Output",
    "U:\2026.3.0.120\SetupBuilder\Output\UFT",
    "U:\2026.3.0.120\SetupBuilder\Output\UFT\MSIBuildProperties",
    "U:\2026.3.0.120\SetupBuilder\Output\UFT\MSIBuildProperties\RegFiles",
    "U:\2026.3.0.120\SetupBuilder\Input",
    "U:\2026.3.0.120\SetupBuilder\Input\UFT_MLU"
)
foreach ($p in $paths) {
    if (Test-Path $p) { Write-Output "EXISTS: $p" }
    else              { Write-Output "MISSING: $p" }
}

Write-Output ""
Write-Output "=== SetupBuilder top-level dirs ==="
if (Test-Path "U:\2026.3.0.120\SetupBuilder") {
    Get-ChildItem "U:\2026.3.0.120\SetupBuilder" -Directory | Select-Object -ExpandProperty Name
} else {
    Write-Output "(SetupBuilder dir does not exist)"
}
"""

r = s.run_ps(ps)
print(r.std_out.decode('utf-8', 'replace'))
if r.std_err and 'CLIXML' not in r.std_err.decode('utf-8', 'replace'):
    print('ERR:', r.std_err.decode('utf-8', 'replace')[:300])
