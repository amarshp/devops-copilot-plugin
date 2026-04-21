"""
Add output_limit = 65536 to the 'ec2' runner section in config.toml.
The first [[runners]] (git2jen-runner) already has it; the second one (ec2) does not.
"""
import sys

try:
    import winrm
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywinrm"])
    import winrm

session = winrm.Session(
    "http://10.168.244.176:5985/wsman",
    auth=("_ft_auto_admin", "W3lcome1"),
    transport="ntlm"
)

CONFIG_PATH = r"C:\GitLab-Runner\config.toml"

# Read full config
r = session.run_ps(f"Get-Content '{CONFIG_PATH}'")
lines = r.std_out.decode().splitlines()
print(f"Total lines: {len(lines)}")

# Show all output_limit occurrences
print("\n=== existing output_limit lines ===")
for i, l in enumerate(lines):
    if "output_limit" in l or "[[runners]]" in l or ('name = "ec2"' in l):
        print(f"  line {i+1}: {l}")

# Fix: insert output_limit after the [[runners]] that is followed by name = "ec2"
# Strategy: walk lines, when we see [[runners]], peek ahead for name = "ec2"
# and if that runner doesn't have output_limit before the next [[runners]], inject it.

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    if line.strip() == "[[runners]]":
        # Look ahead to see if this runner already has output_limit and get its name
        j = i + 1
        runner_lines = [line]
        has_output_limit = False
        runner_name = None
        while j < len(lines) and lines[j].strip() != "[[runners]]":
            runner_lines.append(lines[j])
            if "output_limit" in lines[j]:
                has_output_limit = True
            if lines[j].strip().startswith('name ='):
                runner_name = lines[j]
            j += 1
        print(f"\n  Runner block starting at line {i+1}: name={runner_name}, has_output_limit={has_output_limit}")
        if not has_output_limit:
            # Insert output_limit = 65536 right after the [[runners]] line
            new_lines.append("  output_limit = 65536")
            print(f"  -> INJECTED output_limit = 65536")
    i += 1

# Write back
new_content = "\n".join(new_lines)
# Use PowerShell Set-Content with the new content
# Write to a temp file then move
import tempfile, os
# We'll pass via PowerShell here-string
# Build escaped content for here-string
escaped = new_content.replace("'", "''")

write_cmd = f"""
$content = @'
{new_content}
'@
Set-Content -Path '{CONFIG_PATH}' -Value $content
Write-Output "Written OK. Lines: $($($content -split '`n').Count)"
"""

r2 = session.run_ps(write_cmd)
print("\n=== Write result ===")
print(r2.std_out.decode())
if r2.std_err:
    err = r2.std_err.decode()
    if "CLIXML" not in err and "progress" not in err.lower():
        print("STDERR:", err[:500])

# Verify
r3 = session.run_ps(f"Select-String 'output_limit|\\[\\[runners' '{CONFIG_PATH}'")
print("\n=== Final verification ===")
print(r3.std_out.decode())
