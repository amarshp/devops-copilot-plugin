---
name: pipeline-explorer
description: 'Analyze Jenkins XML and GitLab YAML pipelines, generate dependency graphs and diagrams, and summarize phases and bottlenecks.'
argument-hint: 'jenkins or gitlab pipeline analysis request'
---

# Pipeline Explorer

## Commands
- python .github/skills/pipeline-explorer/scripts/jenkins_graph.py path/to/jenkins_graph_xml.json --config-dir path/to/config_xml --output plugin_artifacts/dependency_graph.txt
- python .github/skills/pipeline-explorer/scripts/gitlab_graph.py --ci .gitlab-ci.yml --output plugin_artifacts/gitlab_graph.json
- python .github/skills/pipeline-explorer/scripts/generate_diagrams.py --tree fetch_xml/pipeline_tree.txt --output-dir plugin_artifacts/diagrams
- python .github/skills/pipeline-explorer/scripts/pipeline_summary.py --graph plugin_artifacts/gitlab_graph.json --output plugin_artifacts/pipeline_summary.md
