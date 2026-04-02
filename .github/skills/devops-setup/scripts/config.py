"""
config.py — Canonical configuration loader for the DevOps Copilot Plugin.

Reads from a .env file, searching up the directory tree from this file's
location until it finds one. Environment variables already set take precedence.

All skill scripts that import ``config`` receive the same values from the
same .env; there is no per-skill configuration divergence.

Required .env keys:
    # GitLab
    GITLAB_URL              Base URL (e.g. https://gitlab.example.com)
    GITLAB_TOKEN            Personal access token (api scope)
    GITLAB_PROJECT_ID       Numeric project ID or "namespace/project"
    GITLAB_BRANCH           Branch to push to and trigger pipelines on

    # Jenkins
    JENKINS_URL             Base URL — auto-derived from JENKINS_ROOT_URL if not set explicitly
    JENKINS_ROOT_URL        Full URL of the root pipeline job
    JENKINS_USER            Jenkins username
    JENKINS_TOKEN           Jenkins API token

    # Runner (remote build agent)
    RUNNER_HOST             Hostname or IP of the build runner
    RUNNER_USER             Username
    RUNNER_PASS             Password
    RUNNER_PORT             Port (5985 for WinRM, 22 for SSH)
    RUNNER_PROTOCOL         "winrm" or "ssh"

    # LLM
    COPILOT_TOKEN           GitHub Copilot API token (for LLM calls)
    COPILOT_MODEL           Model name (default: claude-sonnet-4.6)
    COPILOT_CHAT_URL        Chat completions endpoint URL

Optional .env keys:
    POLL_INTERVAL           Seconds between pipeline status polls (default: 15)
    PIPELINE_TIMEOUT        Max seconds to wait for pipeline (default: 600)
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# .env discovery — walk up from this file's location
# ---------------------------------------------------------------------------
def _find_env() -> Path | None:
    candidate = Path(__file__).resolve()
    for parent in [candidate.parent] + list(candidate.parents):
        env_file = parent / ".env"
        if env_file.exists():
            return env_file
    return None


try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = _find_env()
    if _env_path:
        _load_dotenv(_env_path, override=False)  # env vars already set take precedence
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables


# ---------------------------------------------------------------------------
# GitLab
# ---------------------------------------------------------------------------
GITLAB_URL: str = os.environ.get("GITLAB_URL", "https://gitlab.com")
GITLAB_TOKEN: str = os.environ.get("GITLAB_TOKEN", "")
PROJECT_ID: str = os.environ.get("GITLAB_PROJECT_ID", "")
BRANCH: str = os.environ.get("GITLAB_BRANCH", "main")

POLL_INTERVAL: int = int(os.environ.get("POLL_INTERVAL", "15"))
PIPELINE_TIMEOUT: int = int(os.environ.get("PIPELINE_TIMEOUT", "600"))

# ---------------------------------------------------------------------------
# Jenkins
# ---------------------------------------------------------------------------
JENKINS_URL: str = os.environ.get("JENKINS_URL", "")
JENKINS_ROOT_URL: str = os.environ.get("JENKINS_ROOT_URL", "")
JENKINS_USER: str = os.environ.get("JENKINS_USER", "")
JENKINS_TOKEN: str = os.environ.get("JENKINS_TOKEN", "")

# ---------------------------------------------------------------------------
# Runner (remote build agent)
# ---------------------------------------------------------------------------
# EC2_* kept as aliases for backward compatibility
RUNNER_HOST: str = os.environ.get("RUNNER_HOST") or os.environ.get("EC2_HOST", "")
RUNNER_USER: str = os.environ.get("RUNNER_USER") or os.environ.get("EC2_USER", "")
RUNNER_PASS: str = os.environ.get("RUNNER_PASS") or os.environ.get("EC2_PASS", "")
RUNNER_PORT: int = int(
    os.environ.get("RUNNER_PORT") or os.environ.get("EC2_PORT", "5985")
)
RUNNER_PROTOCOL: str = os.environ.get("RUNNER_PROTOCOL", "winrm").lower()

# ---------------------------------------------------------------------------
# LLM (GitHub Copilot API)
# ---------------------------------------------------------------------------
COPILOT_TOKEN: str = os.environ.get("COPILOT_TOKEN", "")
COPILOT_MODEL: str = os.environ.get("COPILOT_MODEL", "claude-sonnet-4.6")
COPILOT_CHAT_URL: str = os.environ.get(
    "COPILOT_CHAT_URL",
    "https://api.business.githubcopilot.com/chat/completions",
)


# ---------------------------------------------------------------------------
# Validation helper (called by setup_wizard and skills at startup)
# ---------------------------------------------------------------------------
def require(*keys: str) -> None:
    """Raise RuntimeError if any of the named config keys are empty."""
    missing = [k for k in keys if not globals().get(k)]
    if missing:
        raise RuntimeError(
            f"Missing required configuration: {', '.join(missing)}. "
            "Add them to your .env file and re-run."
        )
