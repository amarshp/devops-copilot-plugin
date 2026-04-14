# DevOps Copilot Plugin Workspace Instructions

This workspace hosts a reusable DevOps plugin under `.github/` with agents, prompts, skills, tools, and hooks. It is a general-purpose **DevOps assistant** built around four pillars — not just a migration tool.

## Intake Before Action

Before routing into any pillar, prompt, skill, or agent workflow:

- Read `DEVOPS_PROJECT_CONTEXT.md` from the repository root if it exists.
- If the file is missing or does not establish the user's use case or CI platforms, ask focused clarifying questions first. Only ask about specific paths if the repo structure is already visible and has multiple distinct pipeline areas to choose between — never ask about paths generically. Do not ask about read-only constraints; `.github/` is always read-only unless the user explicitly asks to modify the plugin.
- Create or update `DEVOPS_PROJECT_CONTEXT.md` with the user's answers and reuse it as the main project-specific context file on later turns.
- Do not store secrets in `DEVOPS_PROJECT_CONTEXT.md`; keep secrets in `.env` only.
- Do not jump straight into setup, migration, optimization, or script execution when the use case is still ambiguous.

## Plugin Runtime Boundary

- Treat `.github/` as plugin source code during normal plugin usage.
- Do not edit, generate, delete, or refactor files under `.github/` unless the user explicitly asks to modify the plugin itself.
- If the user is using the plugin to work on their project, write project-specific notes, outputs, and helper scripts outside `.github/`.

## Skill Script Execution Model

- Files and commands under `.github/skills/**/scripts/` are reference implementations and templates, not guaranteed runnable automation for every repository.
- Never assume a documented skill script can be run unchanged in the current repo.
- First inspect the current repository and `DEVOPS_PROJECT_CONTEXT.md`, then either use an existing repo-specific script or build/adapt project-local automation outside `.github/`.
- When a skill doc shows an example command, treat it as a pattern to adapt, not a mandatory literal command.

## Four Pillars

### 1. Setup & Debug
Connect the plugin to **GitLab**, **Jenkins**, or both — whichever your project uses. Once connected you can browse build logs, inspect runners, and use the agent to help diagnose and fix pipeline failures.

Skills: `devops-setup`, `runner-inspector`, `pipeline-monitor`

### 2. Understand the Pipeline
Explore any Jenkins or GitLab pipeline: generate dependency graphs, Mermaid diagrams, phase/bottleneck summaries, and LLM-powered explanations. No migration required — useful for anyone who needs to understand what a pipeline does.

Skills: `pipeline-explorer`

### 3. Migrate (Jenkins → GitLab)
Full-featured Jenkins-to-GitLab migration built as a **self-healing loop**: plan → convert → validate → push → run → QC → diagnose → fix → repeat. Each stage feeds evidence to the next. The LLM retries on lint failures with error context. QC failures produce specific fix instructions the agent acts on. `/resume-loop` picks up from wherever the loop was interrupted. The dashboard tracks state so the agent always knows where it is. HITL stops only fire on genuine blockers (auth, infra) — fixable issues are handled automatically.

Skills: `j2gl-migrate`, `j2gl-qc`

### 4. Optimize Existing Pipelines
Analyze and decouple GitLab CI/CD pipelines for skip-ahead execution, parallelization, cache strategy improvements, and bottleneck removal — independent of any migration.

Skills: `pipeline-decoupler`

## Core Rules

- Start with use-case intake via `DEVOPS_PROJECT_CONTEXT.md` before choosing a workflow.
- Use the setup workflow in `.github/skills/devops-setup/` before any skill that calls Jenkins or GitLab APIs.
- Validate YAML before any push or pipeline trigger.
- Keep job boundaries isolated across files; do not duplicate downstream job implementations.
- Preserve exact externally referenced job names for `needs` stability.
- Use UTF-8 without BOM for YAML files.
- Treat runner inspection as read-only.
- A successful pipeline is not a QC pass by itself.
- QC pass requires explicit report outcome: `QC_STATUS: SUCCESS`.
- Keep `.github/` read-only during normal plugin usage.
- Treat skill scripts and commands as templates unless the current repo explicitly proves they are runnable as-is.

## Safety And Blockers

- Stop and report external blockers: auth failures, missing secrets, runner infra gaps, inaccessible shares.
- Do not mask infrastructure blockers with `allow_failure` unless explicitly approved.
- Do not run destructive git commands unless explicitly requested.

## Human-In-The-Loop (HITL) — Mandatory Stop Conditions

Any agent or prompt MUST stop immediately and ask the human for input when it encounters any of the following. Do not guess, assume, or work around these situations.

**Always stop and ask when:**
- `DEVOPS_PROJECT_CONTEXT.md` is missing or incomplete and the user's requested action is not yet scoped. When this fires, ask only: (1) what they are trying to accomplish, and (2) which platform they use (Jenkins, GitLab, or both). Do not ask about paths, scope, or read-only constraints — `.github/` is always read-only and that is not the user's concern.
- HTTP 401 / 403 returned from Jenkins or GitLab — do not retry or assume credentials are cached.
- A required `.env` key is missing or empty — list exactly which keys are needed and how to obtain them.
- A Jenkins job referenced in a migration plan is not found on the server — confirm whether it was renamed, decommissioned, or is in a different folder path.
- A GitLab runner tag required by a job is not present in `runners.json` — report the missing tag and ask whether to proceed with a substitute tag or stop.
- Generated YAML fails lint validation after 3 retries — stop, show the lint errors, and ask the human to clarify the job's intended behavior before retrying.
- A `needs:` reference points to a job that does not exist in the current pipeline scope — list the missing jobs and ask whether to stub, remove, or add the dependency.
- The next step would require editing `.github/` but the user has not explicitly asked to modify the plugin.
- A skill doc only provides a template script or command and no repo-specific runnable path has been identified yet.
- Any destructive action is about to run (file deletion, git reset, branch force-push, drop table) — state what will be destroyed and wait for explicit approval.
- The migration planner detects a circular dependency in the job graph — show the cycle and ask which edge to break.
- A QC report cannot be generated because the Jenkins reference log is unavailable — record status as `BLOCKED`, explain what log is needed and where to find it, and stop.
- The agent reaches the boundary of its defined scope (e.g. `migration-planner` is asked to write YAML, `qc-reviewer` is asked to edit files) — state the scope boundary, name the correct agent or prompt to use instead, and stop.

**HITL response format — always use this structure:**
```
⛔ STOP — Human input required

Reason: <one sentence explaining what was encountered>
What I need: <exact list of inputs, files, or decisions needed>
How to get it: <concrete steps the human can take>
Next step after you provide it: <what the agent will do next>
```

## Primitive Usage

- Prompts: one-shot workflows via slash commands
- Agents: multi-turn planning, implementation, review, optimization
- Skills: procedures and scripts invoked by agents/prompts
- Hooks: deterministic enforcement (pre-push validation)

Avoid overlapping entry points for the same task unless explicitly needed.