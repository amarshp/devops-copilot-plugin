---
name: explore-pipeline
description: Analyze Jenkins or GitLab pipeline structure and produce graph, diagram, and summary.
argument-hint: source=jenkins|gitlab and path
agent: "agent"
---

Explore this pipeline source: ${input:source:gitlab}
Path/input: ${input:path:.gitlab-ci.yml}

Use:
- [../skills/pipeline-explorer/SKILL.md](../skills/pipeline-explorer/SKILL.md)

Output:
1. dependency graph summary
2. phase/bottleneck highlights
3. generated artifacts and paths
4. optimization opportunities

After presenting the analysis, always end with:

**Your next step:**
- If the pipeline has bottlenecks or parallelization gaps → suggest using the `pipeline-optimizer` agent to apply skip-ahead, caching, and parallelization improvements.
- If the source is Jenkins and the user wants to move to GitLab → suggest running `/migrate-job` or the `migration-planner` agent.
- Otherwise → ask the user which area they want to act on first.
