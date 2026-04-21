import os, warnings
warnings.filterwarnings('ignore')
import urllib3; urllib3.disable_warnings()
import winrm

s = winrm.Session('10.168.244.176', auth=('_ft_auto_admin', 'W3lcome1'),
                  transport='ntlm', server_cert_validation='ignore')

ps = r"""
$paths = @(
    "P:\FT\QTP\win32_release\2026.3.0.120\QTP\Addins\TePackage",
    "P:\FT\QTP\win32_release\2026.3.0.120\QTP\Addins\TePackage\Dat",
    "P:\FT\QTP\win32_release\2026.3.0.120\QTP\Addins\TePackage\Dat\TePassport.reg",
    "P:\FT\QTP\win32_release\2026.3.0.120\QTP\Addins\TePackage\bin"
)
foreach ($p in $paths) {
    if (Test-Path $p) { Write-Output "EXISTS: $p" }
    else              { Write-Output "MISSING: $p" }
}

# Also list the Addins folder to see what addins are present
Write-Output ""
Write-Output "=== Addins present in build 120 ==="
Get-ChildItem "P:\FT\QTP\win32_release\2026.3.0.120\QTP\Addins" -Directory | Select-Object -ExpandProperty Name
"""

r = s.run_ps(ps)
print(r.std_out.decode('utf-8', 'replace'))
if r.std_err:
    print('ERR:', r.std_err.decode('utf-8', 'replace')[:500])
