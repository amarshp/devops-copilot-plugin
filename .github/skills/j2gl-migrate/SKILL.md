---
name: j2gl-migrate
description: 'Migrate Jenkins jobs to GitLab YAML using stage dictionaries, LLM conversion, validation, and push/trigger workflows.'
argument-hint: 'target Jenkins job name or migration scope'
---

# J2GL Migrate (Jenkins → GitLab)

End-to-end workflow for converting Jenkins pipeline jobs to GitLab CI YAML. Uses LLM (GitHub Copilot API) for intelligent conversion with structure validation and retry.

## Project Context And Execution Model
- Read `DEVOPS_PROJECT_CONTEXT.md` before running this skill.
- If the file is missing or does not define the migration goal, source/target systems, writable paths, and read-only boundaries, ask clarifying questions first and update it.
- Keep `.github/` read-only during normal plugin usage unless the user explicitly asked to modify the plugin itself.
- Commands and scripts under `.github/skills/` are reference implementations and templates. Only run them if this repo proves they are the correct runnable assets here.
- If the repo needs custom migration automation, create or adapt project-local scripts outside `.github/`.

## When to Use
- "Migrate `<JobName>` to GitLab"
- "Generate GitLab YAML for the Jenkins pipeline"
- Converting a Jenkins XML config to a `.gitlab-ci.yml` stage file
- Orchestrating a bottom-up migration of a full pipeline subtree
- Validating generated YAML syntax and structure
- Pushing migrated YAML and triggering a GitLab pipeline

## Prerequisites
- [devops-setup](../devops-setup/SKILL.md) complete — `.env` present, `jenkins_graph_xml.json` available
- Reference environment setup pattern: `pip install -r .github/requirements.txt`
- `COPILOT_TOKEN` set in `.env`

## Procedure

### Step 1: Build Stage Dictionary
Parse Jenkins XML configs into a metadata index that maps jobs to stages:

Treat this as a reference command. Verify that the repo uses these paths and assets before executing it unchanged.

```powershell
python .github/skills/j2gl-migrate/scripts/build_stage_dict.py \
    --graph fetch_xml/jenkins_graph_xml.json \
    --root "<ROOT_JOB_NAME>" \
    --output plugin_artifacts/stage_dict.json
```

### Step 2: Convert a Single Job
Convert one Jenkins job to GitLab YAML using LLM:

Treat this as a reference command. If the repo has adapted conversion tooling, prefer that verified local path.

```powershell
python .github/skills/j2gl-migrate/scripts/convert_job.py "<JOB_NAME>" \
    --stage-dict plugin_artifacts/stage_dict.json \
    --output-file migrated_yamls/ci/stages/<JOB>.yml
```

The converter:
1. Builds a prompt with Jenkins XML + tail of build log + downstream job stubs
2. Calls the LLM (Claude / Copilot)
3. Validates that the output doesn't redefine downstream jobs
4. Retries up to 3 times if validation fails, passing lint errors back

### Step 3: Validate YAML
Local syntax + GitLab CI lint API:
```powershell
# Single file:
python .github/skills/j2gl-migrate/scripts/validate_yaml.py migrated_yamls/ci/stages/<JOB>.yml

# Root pipeline with includes expanded:
python .github/skills/j2gl-migrate/scripts/validate_yaml.py migrated_yamls/.gitlab-ci.yml --expand-local-includes
```

### Step 4: Orchestrate Full Migration (optional)
Migrate all jobs in dependency order (leaves first):

```powershell
python .github/skills/j2gl-migrate/scripts/orchestrate_migration.py \
    --stage-dict plugin_artifacts/stage_dict.json \
    --output-dir migrated_yamls/ci/stages
```

Add `--start-after "<JobName>"` to resume from a specific job.

### Step 5: Push and Trigger
Commit YAML files to GitLab and trigger a pipeline:

```powershell
python .github/skills/j2gl-migrate/scripts/push_and_trigger.py \
    --source-dir migrated_yamls \
    -m "migrate: <JOB_NAME> — <short description>"
```

The `-m` message is required.

Do not assume these exact commands are correct for every repository. Verify the repo layout and migration entry points first.

## Stop Conditions
- **401/403 from GitLab** → check `GITLAB_TOKEN` and project permissions
- **YAML lint fails after 3 retries** → inspect the generated YAML; may need manual fix or runner-inspector for path issues
- **Job redefines downstream jobs** → review prompt constraints in `prompts.py`
- **Runner path/tool missing** → use [runner-inspector](../runner-inspector/SKILL.md) before changing YAML

## Job Isolation Rules
- Keep each job in its own YAML file under `migrated_yamls/ci/stages/`
- Never inline downstream jobs into parent YAML files
- Preserve exact Jenkins job names when referenced in `needs:` or from other files
- Use PowerShell-first scripts for Windows runners unless otherwise established
