---
name: pipeline-explorer
description: 'Analyze Jenkins XML and GitLab YAML pipelines, generate dependency graphs and diagrams, and summarize phases and bottlenecks.'
argument-hint: 'jenkins or gitlab pipeline analysis request'
---

# Pipeline Explorer

## Project Context And Execution Model
- Read `DEVOPS_PROJECT_CONTEXT.md` before running this skill.
- If the file is missing or does not define the pipeline source, target paths, and read-only boundaries, ask clarifying questions first and update it.
- Keep `.github/` read-only during normal plugin usage unless the user explicitly asked to modify the plugin itself.
- Commands and scripts under `.github/skills/` are reference implementations and templates. Only run them if this repo proves they are the correct runnable assets here.
- If the repo needs custom analysis automation, create or adapt project-local scripts outside `.github/`.

## Reference Commands
- python .github/skills/pipeline-explorer/scripts/jenkins_graph.py path/to/jenkins_graph_xml.json --config-dir path/to/config_xml --output plugin_artifacts/dependency_graph.txt
- python .github/skills/pipeline-explorer/scripts/gitlab_graph.py --ci .gitlab-ci.yml --output plugin_artifacts/gitlab_graph.json
- python .github/skills/pipeline-explorer/scripts/generate_diagrams.py --tree fetch_xml/pipeline_tree.txt --output-dir plugin_artifacts/diagrams
- python .github/skills/pipeline-explorer/scripts/pipeline_summary.py --graph plugin_artifacts/gitlab_graph.json --output plugin_artifacts/pipeline_summary.md

Do not assume these exact commands are correct for every repository. Verify the repo layout and evidence paths first.
