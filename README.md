# DevOps Copilot Plugin

A reusable **GitHub Copilot workspace plugin** for CI/CD operations — built as composable agents, prompts, skills, and hooks that drop into any project's `.github/` folder.

Not just a migration tool. Four pillars cover the full DevOps lifecycle:

| Pillar | What it does | Skills |
|--------|-------------|--------|
| **Setup & Debug** | Connect to GitLab, Jenkins, or both. Browse logs, inspect runners, diagnose failures. | `devops-setup`, `runner-inspector`, `pipeline-monitor` |
| **Understand** | Graph any pipeline, generate Mermaid diagrams, find bottlenecks. No migration needed. | `pipeline-explorer` |
| **Migrate** | Self-healing Jenkins → GitLab loop: plan → convert → validate → push → run → QC → fix → repeat. | `j2gl-migrate`, `j2gl-qc` |
| **Optimize** | Decouple pipelines, parallelize jobs, improve caching, remove bottlenecks. | `pipeline-decoupler` |

## Quick Start

### Prerequisites

- [VS Code](https://code.visualstudio.com/) with [GitHub Copilot Chat](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat)
- Python 3.10+

### 1. Install dependencies

```powershell
pip install -r .github/requirements.txt
```

### 2. Run the setup wizard

```powershell
python .github/skills/devops-setup/scripts/setup_wizard.py
```

This creates a `.env` file with your Jenkins and/or GitLab credentials. Only fill in what you use.

### 3. Open Copilot Chat

```
/start-plugin
```

The welcome prompt explains every command and routes you to the right next step.

## Slash Commands

| Command | Description |
|---------|-------------|
| `/start-plugin` | Welcome guide — first-time orientation |
| `/setup-project` | Initialize credentials and test connections |
| `/explore-pipeline` | Graph and summarize any Jenkins or GitLab pipeline |
| `/pipeline-status` | Monitor pipeline runs, download logs, diagnose failures |
| `/migrate-job` | Convert a Jenkins job to GitLab CI YAML |
| `/qc-job` | Compare Jenkins vs GitLab logs, produce QC verdict |
| `/resume-loop` | Resume an interrupted migration or QC workflow |

## Agents

Use the `@` agent picker in Copilot Chat:

| Agent | Scope | Purpose |
|-------|-------|---------|
| `migration-planner` | Read-only | Produce ordered migration plans, identify blockers |
| `migration-implementer` | Write + execute | Author YAML, run scripts, push to GitLab |
| `qc-reviewer` | Read-only | Compare logs, classify failures, produce QC reports |
| `pipeline-optimizer` | Write + execute | Decouple, parallelize, and optimize pipelines |

## Project Structure

```
.github/
├── agents/          # Multi-turn agent personas (4)
├── prompts/         # Slash-command entry points (7)
├── skills/          # Workflow bundles with Python scripts (7)
│   ├── devops-setup/
│   ├── pipeline-explorer/
│   ├── j2gl-migrate/
│   ├── j2gl-qc/
│   ├── pipeline-decoupler/
│   ├── pipeline-monitor/
│   └── runner-inspector/
├── hooks/           # Pre-push YAML validation
├── instructions/    # Coding conventions (YAML, security)
├── copilot-instructions.md
├── requirements.txt
└── README.md        # Detailed docs
```

## How It Works

**Composable primitives** — each piece has a clear role:

- **Agents** handle multi-turn conversations with scoped permissions
- **Prompts** are one-shot slash commands that invoke skills
- **Skills** bundle Python scripts and workflow instructions
- **Hooks** enforce validation gates (e.g., YAML lint before push)
- **Instructions** apply coding conventions to matching files

**Human-in-the-loop safety** — agents stop and ask for input on auth failures, missing secrets, circular dependencies, destructive actions, or out-of-scope requests. No guessing.

**Self-healing migration loop** — each stage feeds evidence to the next. LLM retries on lint failures with error context. QC failures produce specific fix instructions. `/resume-loop` picks up from wherever the loop was interrupted.

## Requirements

| Package | Purpose |
|---------|---------|
| `python-dotenv` | Load `.env` credentials |
| `requests` | Jenkins/GitLab API calls |
| `pyyaml` | YAML parsing and validation |
| `python-gitlab` | GitLab API client |
| `pywinrm` | Windows runner inspection (WinRM) |
| `paramiko` | Linux runner inspection (SSH) |

## License

See [LICENSE](LICENSE) for details.
