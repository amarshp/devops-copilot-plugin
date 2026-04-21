import winrm
s = winrm.Session("http://10.168.244.176:5985/wsman", auth=("_ft_auto_admin", "W3lcome1"), transport="ntlm")

# Read full config
r = s.run_ps("Get-Content 'C:\\GitLab-Runner\\config.toml'")
print(r.std_out.decode())

# Check runner service status
r2 = s.run_ps("(Get-Service gitlab-runner).Status")
print("Runner service status:", r2.std_out.decode().strip())
