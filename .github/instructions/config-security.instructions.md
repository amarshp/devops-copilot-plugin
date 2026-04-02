---
name: config-security
description: Token and secret safety rules for .env and config files in the DevOps plugin.
applyTo: "**/{.env,config.py}"
---

# Config Security

- Never commit real tokens or passwords to source control.
- Keep secrets in .env and read via environment variables.
- Avoid printing full secrets in logs or reports.
- For diagnostics, mask token values except short prefixes.
- Validate required keys before calling external APIs.
- If credentials are missing or unauthorized, return a clear blocker.
