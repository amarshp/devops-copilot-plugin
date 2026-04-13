# DevOps Copilot Plugin

## What Is This?

This is a **Copilot plugin** — a set of files you drop into your repo that turns GitHub Copilot Chat into a fully capable DevOps engineer for your project.

Without this plugin, Copilot is a general-purpose coding assistant. It knows about code but knows nothing about *your* pipelines, *your* Jenkins jobs, or *your* GitLab setup.

With this plugin, Copilot becomes a specialist. It knows your CI/CD structure, understands the four pillars of CI/CD work, follows safe step-by-step workflows, and stops itself when it hits a genuine blocker rather than guessing. You just talk to it.

---

## Why Is This Different From Just Asking Copilot a Question?

| Without the plugin | With the plugin |
|---|---|
| Generic answers about CI/CD concepts | Answers grounded in *your* pipeline, *your* job configs, *your* logs |
| You have to guide every step manually | Copilot follows a proven workflow automatically |
| No safety guardrails — it might guess or hallucinate steps | Hard stop conditions: auth failures, missing dependencies, destructive actions all trigger a human check |
| No memory of what was done before | Tracks migration state, QC results, and run history in files it maintains |
| You need to know Jenkins, GitLab, and YAML deeply | You describe the goal; Copilot handles the technical execution |

---

## What Makes It Special

**It works from plain language.** You don't need to know command names, YAML syntax, or even what a "runner tag" is. Say what you want — the plugin figures out which workflow to run.

**It is self-healing.** The migration loop retries on lint failures with the actual error context. QC failures produce specific fix instructions. It resumes from interruptions. It doesn't just fail and stop.

**It has safety built in.** Every workflow has mandatory human checkpoints for auth failures, missing secrets, destructive operations, and anything it can't resolve automatically. It will never silently work around a blocker.

**It covers the full CI/CD lifecycle — not just migration.** Connect to an existing pipeline and it will explain it, graph it, diagnose failures, optimize it, or help you iterate faster with fast-path execution. Migration is just one of five capabilities.

**It is reusable across projects.** Drop `.github/` into any repo. The plugin adapts to what it finds — Jenkins XML, GitLab CI YAML, or both.

---

> For plugin internals, layer architecture, routing rules, and HITL details, see [PLUGIN_REFERENCE.md](PLUGIN_REFERENCE.md).

---

## What It Can Do

| Pillar | What to say | What happens |
|---|---|---|
| **Setup & Debug** | "Set up my GitLab connection" / "why did my pipeline fail?" | Connects to GitLab/Jenkins, fetches logs, diagnoses failures |
| **Understand** | "Show me the pipeline" / "explain what this pipeline does" | Generates dependency graph, diagrams, bottleneck summary |
| **Migrate** | "Migrate my Jenkins job to GitLab" | Runs plan → convert → validate → push → QC loop |
| **Optimize** | "Speed up my pipeline" / "parallelize this" | Decouples stages, improves caching, removes bottlenecks |
| **Fast Resume** | "Skip compilation, resume from Addins" | Generates a fast-path pipeline reusing a cached workspace |

---

## How to Use It

**Just describe what you want.** No commands or special syntax needed.

- *"Help me migrate my Jenkins job to GitLab"*
- *"Why is my pipeline slow?"*
- *"Set up credentials for GitLab"*
- *"Did the migration pass QC?"*
- *"Check the latest pipeline run"*

The plugin reads your intent and runs the right workflow automatically.

**You don't need to know the process upfront.** Just send a message — even just "hi" or "where do I start" — and the plugin will ask what you're trying to do, show you the full ordered journey for your goal, and walk you through each step one at a time, telling you what was just done and what comes next.

---

## Quick Start

### 1. Add `.github/` to your repo
Copy this `.github/` folder into your project root. That is all Copilot needs.

### 2. Open Copilot Chat and send your first message
Just describe what you want. Copilot automatically checks whether setup is complete before proceeding:

- If credentials are already configured → proceeds to your task immediately
- If `.env` is missing or incomplete → walks you through setup first, then resumes your task

You never need to manually run setup scripts. The first message triggers the check.

---

## Optional Shortcuts

You do not need these — the plugin works from plain language. They are available if you prefer explicit entry points.

**Slash commands** (type in Copilot Chat):

| Command | What it does |
|---|---|
| `/start-plugin` | Welcome tour, checks setup status |
| `/setup-project` | Initialize credentials and test connections |
| `/explore-pipeline` | Graph and summarize a pipeline |
| `/pipeline-status` | Check latest run, download logs, diagnose |
| `/migrate-job` | Convert a Jenkins job to GitLab CI YAML |
| `/qc-job` | Compare Jenkins vs GitLab, produce QC report |
| `/resume-loop` | Resume an interrupted migration |

**Agents** (type `@agent-name` in Copilot Chat):

Agents are **not** auto-invoked — you must explicitly pick one. Use them when you need hard permission boundaries (e.g. `@qc-reviewer` is enforced read-only and structurally cannot write files).

| Agent | Use for |
|---|---|
| `@migration-planner` | Ordered migration plan, blocker identification (read-only) |
| `@migration-implementer` | YAML authoring, script execution, push |
| `@qc-reviewer` | Jenkins vs GitLab log comparison, QC verdict (read-only) |
| `@pipeline-optimizer` | Parallelization, decoupling, cache strategy |
| `@phase-resumer` | Generate fast-path pipelines skipping earlier phases |

---

## Typical Workflows

### Any project
```
1. "Set up my GitLab / Jenkins connection"
2. "Show me the pipeline"
3. "Check the latest pipeline run"
```

### Migration
```
1. "Set up connections"
2. "Download Jenkins job configs and logs"
3. "Plan the migration"
4. "Migrate job X" → "QC job X" → repeat
```

### Optimization
```
"Speed up my pipeline" or "decouple my pipeline stages"
```

### Fast-path resume
```
"Skip compilation and resume from the Addins phase"
```