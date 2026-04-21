"""
Increase GitLab runner output_limit via WinRM.
Finds config.toml on the runner, adds/updates output_limit to 65536 (64 MB).
"""
import subprocess, sys, os

# WinRM connection details
WINRM_HOST = "10.168.244.176"
WINRM_PORT = 5985
WINRM_USER = "_ft_auto_admin"
WINRM_PASS = "W3lcome1"

try:
    import winrm
except ImportError:
    print("Installing pywinrm...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywinrm"])
    import winrm

session = winrm.Session(
    f"http://{WINRM_HOST}:{WINRM_PORT}/wsman",
    auth=(WINRM_USER, WINRM_PASS),
    transport="ntlm"
)

# Step 1: Find the config.toml
find_cmd = r"""
$paths = @(
    "C:\GitLab-Runner\config.toml",
    "C:\gitlab-runner\config.toml",
    "C:\Program Files\GitLab Runner\config.toml",
    "$env:USERPROFILE\.gitlab-runner\config.toml"
)
foreach ($p in $paths) {
    if (Test-Path $p) { Write-Output $p; break }
}
"""
r = session.run_ps(find_cmd)
config_path = r.std_out.decode().strip()
print(f"config.toml found at: {repr(config_path)}")
if r.std_err:
    print("STDERR:", r.std_err.decode())

if not config_path:
    # Try searching
    r2 = session.run_ps(r"Get-ChildItem C:\ -Recurse -Filter config.toml -ErrorAction SilentlyContinue | Select-Object -First 3 -ExpandProperty FullName")
    print("Search result:", r2.std_out.decode())
    sys.exit(1)

# Step 2: Read current config
r = session.run_ps(f"Get-Content '{config_path}'")
current = r.std_out.decode()
print("\n=== Current config.toml (first 40 lines) ===")
for line in current.splitlines()[:40]:
    print(line)

# Step 3: Check if output_limit already set
if "output_limit" in current:
    print("\noutput_limit already present — updating value to 65536 KB (64 MB)...")
    update_cmd = f"""
$content = Get-Content '{config_path}'
$updated = $content -replace 'output_limit = \\d+', 'output_limit = 65536'
Set-Content '{config_path}' $updated
Write-Output "Done"
"""
else:
    print("\noutput_limit not found — inserting after first [[runners]] line...")
    update_cmd = f"""
$content = Get-Content '{config_path}'
$updated = @()
$inserted = $false
foreach ($line in $content) {{
    $updated += $line
    if (-not $inserted -and $line -match '^\[\[runners\]\]') {{
        $updated += '  output_limit = 65536'
        $inserted = $true
    }}
}}
Set-Content '{config_path}' $updated
Write-Output "Done - inserted output_limit = 65536"
"""

r = session.run_ps(update_cmd)
print(r.std_out.decode())
if r.std_err:
    print("STDERR:", r.std_err.decode())

# Step 4: Verify
r = session.run_ps(f"Select-String 'output_limit' '{config_path}'")
print("\nVerification - output_limit lines:")
print(r.std_out.decode())

# Step 5: Note — do NOT restart gitlab-runner since it will be picked up automatically
# GitLab Runner reloads config every 3 seconds without restart
print("\nGitLab Runner auto-reloads config every 3 seconds — no service restart needed.")
print("output_limit = 65536 KB (64 MB) is now set.")
