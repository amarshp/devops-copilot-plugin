---
name: explore-pipeline
description: Analyze Jenkins or GitLab pipeline structure and produce graph, diagram, and summary.
argument-hint: source=jenkins|gitlab and path
agent: "agent"
---

Before exploring the pipeline:

1. Read `DEVOPS_PROJECT_CONTEXT.md` from the repository root.
2. If the file is missing or does not clearly define the current use case, source platform, target paths, and read-only boundaries, ask focused clarifying questions first.
3. Create or update `DEVOPS_PROJECT_CONTEXT.md` with the clarified exploration scope before proceeding.
4. Keep `.github/` read-only unless the user explicitly asked to modify the plugin itself.
5. Treat scripts and commands documented under `.github/skills/` as reference templates; only run them if the current repo proves they are the correct runnable assets here.

Explore this pipeline source: ${input:source:gitlab}
Path/input: ${input:path:.gitlab-ci.yml}

Use:
- [../skills/pipeline-explorer/SKILL.md](../skills/pipeline-explorer/SKILL.md)

Output:
1. project context summary and confirmed exploration scope
2. dependency graph summary
3. phase/bottleneck highlights
4. generated artifacts and paths
5. optimization opportunities

If the requested source/path is ambiguous or does not exist, stop and ask before running any workflow step.

After presenting the analysis, always end with:

**Your next step:**
- If the pipeline has bottlenecks or parallelization gaps → suggest using the `pipeline-optimizer` agent to apply skip-ahead, caching, and parallelization improvements.
- If the source is Jenkins and the user wants to move to GitLab → suggest running `/migrate-job` or the `migration-planner` agent.
- Otherwise → ask the user which area they want to act on first.
