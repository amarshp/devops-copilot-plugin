"""
Pipeline Phase Resumer — Core Logic

Provides three commands:
  analyze  — identify gate jobs and dotenv producers for a target phase
  generate — produce the fast_<phase> pipeline directory
  lint     — validate YAML structure of a generated pipeline
"""

import argparse
import os
import re
import shutil
import sys
from typing import Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: uv run --with pyyaml ...")


# ---------------------------------------------------------------------------
# Phase registry — what each phase needs gated by, and what it includes
# Add entries here as migration expands to new phases.
# ---------------------------------------------------------------------------
PHASE_REGISTRY: Dict[str, dict] = {
    "addins": {
        "description": "All Addins compilation (QTCustSupport → SetupUtils)",
        # Jobs whose needs: will be replaced by bootstrap validators
        "gates_replaced": [
            "UFT.Compile.FrontEnd.Infra.BomCheck",
            "UFT.Compile.FrontEnd.ReplayRecoveryUI.BomCheck",
            "UFT.Compile.FrontEnd.ObjectRepository.BomCheck",
        ],
        # Bootstrap job names emitted (one per gate replaced)
        "bootstrap_jobs": [
            "fast-resume-frontend-infra-bootstrap",
            "fast-resume-replayrecovery-bootstrap",
            "fast-resume-objectrepo-bootstrap",
        ],
        # GitLab CI stages in which each bootstrap job runs
        "bootstrap_stages": [
            "compile-addins-qtcustsupport",
            "compile-addins-winbased",
            "compile-addins-webservices",
        ],
        # Stage files to INCLUDE in the fast pipeline (relative to ci/stages/)
        # Everything else from the source is copied verbatim but not included.
        "include_stages": [
            "INFRA.Net.Use.yml",
            "uft-build-env-setup.yml",
            "uft-build-compute-version.yml",
            "uft-compile-setup.yml",
            "INFRA.UFT.MSBuild.yml",
            "INFRA.Product.AllDependencies.LocalMirror.yml",
            "UFT.BuildNumber.Creator.yml",
            "fast-resume-bootstrap.yml",       # generated
            "UFT.Compile.Addins.QTCustSupport.yml",
            "UFT.Compile.Addins.WinBased.yml",
            "UFT.Compile.Addins.WebServices.yml",
            "UFT.Compile.Addins.AI.yml",
            "UFT.Compile.Addins.TePackage.yml",
            "UFT.Compile.Addins.WebBased.yml",
            "UFT.Compile.Addins.Stingray.yml",
            "UFT.Compile.Addins.CoreAddins.yml",
            "UFT.Compile.Addins.IBAPackage.yml",
            "UFT.Compile.Addins.Flex.yml",
            "UFT.Compile.Addins.Java.yml",
            "UFT.Compile.Addins.DotNet.yml",
            "UFT.Compile.Addins.UIAutomation.yml",
            "UFT.Compile.Addins.UIAutomation2.yml",
            "UFT.Compile.Addins.AF.yml",
            "UFT.Compile.Addins.PDF.yml",
            "UFT.Compile.Addins.ERP.yml",
            "UFT.Compile.Services.yml",
            "UFT.Compile.Addins.Metro.yml",
            "UFT.Compile.Addins.MobilePackage.yml",
            "UFT.Compile.SetupUtils.yml",
        ],
        # Stages list for the generated .gitlab-ci.yml
        "stages": [
            "build-prepare", "build-number", "compile-setup", "compile-prepare",
            "compile-local-mirror",
            "compile-addins-qtcustsupport",
            "compile-addins-winbased",
            "compile-addins-webservices",
            "compile-addins-ai",
            "compile-addins-tepackage",
            "compile-addins-webbased",
            "compile-addins-stingray",
            "compile-addins-coreaddins",
            "compile-addins-ibapackage",
            "compile-addins-flex",
            "compile-addins-java",
            "compile-addins-dotnet",
            "compile-addins-uiautomation",
            "compile-addins-uiautomation2",
            "compile-addins-af",
            "compile-addins-pdf",
            "compile-addins-erp",
            "compile-services",
            "compile-addins-metro",
            "compile-addins-mobilepackage",
            "compile-setuputils",
        ],
        # Which Addin stage files need their gate needs: patched and how
        "needs_patches": {
            "UFT.Compile.Addins.QTCustSupport.yml": {
                "UFT.Compile.FrontEnd.Infra.BomCheck": "fast-resume-frontend-infra-bootstrap",
            },
            "UFT.Compile.Addins.WinBased.yml": {
                "UFT.Compile.FrontEnd.ReplayRecoveryUI.BomCheck": "fast-resume-replayrecovery-bootstrap",
            },
            "UFT.Compile.Addins.WebServices.yml": {
                "UFT.Compile.FrontEnd.ObjectRepository.BomCheck": "fast-resume-objectrepo-bootstrap",
            },
            "UFT.Compile.Addins.AI.yml": {
                "UFT.Compile.FrontEnd.ObjectRepository.BomCheck": "fast-resume-objectrepo-bootstrap",
            },
        },
        # Paths to validate in bootstrap (relative to DestDir)
        "workspace_check_paths": [
            "bin",
            "build",
            "include",
        ],
    },
    "setup": {
        "description": "Setup Generation (ALM/BTP → WiX installer)",
        "gates_replaced": [
            "UFT.Compile.SetupUtils.BomCheck",
        ],
        "bootstrap_jobs": [
            "fast-resume-setuputils-bootstrap",
        ],
        "bootstrap_stages": [
            "setup-alm-btp",
        ],
        "include_stages": [
            "INFRA.Net.Use.yml",
            "uft-build-env-setup.yml",
            "uft-build-compute-version.yml",
            "uft-compile-setup.yml",
            "INFRA.UFT.MSBuild.yml",
            "INFRA.Product.AllDependencies.LocalMirror.yml",
            "UFT.BuildNumber.Creator.yml",
            "fast-resume-bootstrap.yml",
            # Setup stage files (to be added once migrated)
            "UFT.Setup.ALMAndBTP.yml",
            "UFT.Prepare.MLUSetup.yml",
            "UFT.Prepare.AllSetup.yml",
            "UFT.Generic.ChangeBinFiles.yml",
            "UFT.Create.MLU.yml",
            "UFT.Setup.Finalize.yml",
            "UFT.Create.Setups.Wix.yml",
            "UFT.Setup.Publish.yml",
        ],
        "stages": [
            "build-prepare", "build-number", "compile-setup", "compile-prepare",
            "compile-local-mirror",
            "setup-alm-btp",
            "setup-prepare-mlu",
            "setup-prepare-all",
            "setup-bin-changes",
            "setup-create-mlu",
            "setup-finalize",
            "setup-create-wix",
            "setup-publish",
        ],
        "needs_patches": {
            "UFT.Setup.ALMAndBTP.yml": {
                "UFT.Compile.SetupUtils.BomCheck": "fast-resume-setuputils-bootstrap",
            },
        },
        "workspace_check_paths": [
            "bin",
            "build",
            "include",
            "bin\\setup",
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_yaml_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(data: dict) -> str:
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def find_ci_file(pipeline_dir: str) -> str:
    candidate = os.path.join(pipeline_dir, ".gitlab-ci.yml")
    if os.path.isfile(candidate):
        return candidate
    raise FileNotFoundError(f"No .gitlab-ci.yml found in {pipeline_dir}")


def find_stages_dir(pipeline_dir: str) -> str:
    for path in ["ci/stages", "ci\\stages"]:
        candidate = os.path.join(pipeline_dir, path)
        if os.path.isdir(candidate):
            return candidate
    raise FileNotFoundError(f"No ci/stages/ directory found under {pipeline_dir}")


# ---------------------------------------------------------------------------
# Command: analyze
# ---------------------------------------------------------------------------

def cmd_analyze(pipeline_dir: str, phase: str) -> None:
    """Print phase boundary analysis."""
    if phase not in PHASE_REGISTRY:
        print(f"Unknown phase '{phase}'. Known phases: {', '.join(PHASE_REGISTRY)}")
        sys.exit(1)

    info = PHASE_REGISTRY[phase]
    stages_dir = find_stages_dir(pipeline_dir)

    print(f"\nPhase: {phase}")
    print(f"Description: {info['description']}")
    print(f"\nGate jobs that will be replaced by bootstrap validators:")
    for gate, bootstrap in zip(info["gates_replaced"], info["bootstrap_jobs"]):
        print(f"  {gate}  →  {bootstrap}")

    print(f"\nStage files that will be included in fast_{phase}:")
    for f in info["include_stages"]:
        path = os.path.join(stages_dir, f)
        exists = "✓" if os.path.isfile(path) else "✗ MISSING"
        print(f"  {f}  [{exists}]")

    print(f"\nNeeds patches:")
    for stage_file, patches in info.get("needs_patches", {}).items():
        for old_gate, new_bootstrap in patches.items():
            print(f"  {stage_file}: {old_gate}  →  {new_bootstrap}")

    print(f"\nWorkspace validation paths (relative to DestDir):")
    for p in info.get("workspace_check_paths", []):
        print(f"  {p}")


# ---------------------------------------------------------------------------
# Command: generate
# ---------------------------------------------------------------------------

def cmd_generate(
    source_dir: str,
    output_dir: str,
    phase: str,
    ref_build_number: str,
    ref_build_version: str,
    ref_destdir: str,
    repo_prefix: str = "uft_build",
    runner_tag: str = "ec2-runner",
) -> None:
    """Generate the fast_<phase> pipeline directory."""
    if phase not in PHASE_REGISTRY:
        print(f"Unknown phase '{phase}'. Known phases: {', '.join(PHASE_REGISTRY)}")
        sys.exit(1)

    info = PHASE_REGISTRY[phase]
    stages_dir_src = find_stages_dir(source_dir)
    stages_dir_out = os.path.join(output_dir, "ci", "stages")
    os.makedirs(stages_dir_out, exist_ok=True)

    # 1. Copy all stage files verbatim
    print(f"Copying stage files from {stages_dir_src} ...")
    for fname in os.listdir(stages_dir_src):
        if fname.endswith(".yml"):
            shutil.copy2(os.path.join(stages_dir_src, fname), os.path.join(stages_dir_out, fname))
    print(f"  Copied {len(os.listdir(stages_dir_src))} files.")

    # 2. Copy .preflight-check.yml if present
    preflight_src = os.path.join(source_dir, "ci", ".preflight-check.yml")
    if os.path.isfile(preflight_src):
        os.makedirs(os.path.join(output_dir, "ci"), exist_ok=True)
        shutil.copy2(preflight_src, os.path.join(output_dir, "ci", ".preflight-check.yml"))

    # 3. Apply needs patches
    for stage_file, patches in info.get("needs_patches", {}).items():
        path = os.path.join(stages_dir_out, stage_file)
        if not os.path.isfile(path):
            print(f"  WARNING: patch target not found: {stage_file}")
            continue
        _apply_needs_patches(path, patches)
        print(f"  Patched needs: {stage_file}")

    # 4. Patch uft-build-compute-version.yml for reuse path
    _patch_compute_version(stages_dir_out)

    # 5. Patch UFT.BuildNumber.Creator.yml to never run when reuse is set
    _patch_buildnumber_creator(stages_dir_out)

    # 6. Generate bootstrap file
    bootstrap_path = os.path.join(stages_dir_out, "fast-resume-bootstrap.yml")
    _generate_bootstrap(bootstrap_path, phase, info, ref_destdir)
    print(f"  Generated: fast-resume-bootstrap.yml")

    # 7. Generate root .gitlab-ci.yml
    _generate_root_ci(
        source_dir=source_dir,
        output_dir=output_dir,
        phase=phase,
        info=info,
        ref_build_number=ref_build_number,
        ref_build_version=ref_build_version,
        ref_destdir=ref_destdir,
        repo_prefix=repo_prefix,
        runner_tag=runner_tag,
    )
    print(f"  Generated: .gitlab-ci.yml")

    print(f"\nfast_{phase} pipeline written to: {output_dir}")
    print(f"Next: lint with  python run.py lint --pipeline-dir {output_dir}")


def _apply_needs_patches(path: str, patches: Dict[str, str]) -> None:
    """Replace old gate job names with new bootstrap job names in needs: blocks."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old_gate, new_bootstrap in patches.items():
        # Replace in needs: list items  - job: <name>
        content = re.sub(
            r'(\s*-\s*job:\s*)' + re.escape(old_gate) + r'(\b)',
            r'\g<1>' + new_bootstrap + r'\2',
            content,
        )
        # Also handle bare string needs (- "JobName")
        content = re.sub(
            r'(\s*-\s*["\']?)' + re.escape(old_gate) + r'(["\']?\s*$)',
            r'\g<1>' + new_bootstrap + r'\2',
            content,
            flags=re.MULTILINE,
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _patch_compute_version(stages_dir: str) -> None:
    """Add reuse path to uft-build-compute-version.yml if not already present."""
    path = os.path.join(stages_dir, "uft-build-compute-version.yml")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "FAST_RESUME_REFERENCE_BUILD_NUMBER" in content:
        return  # already patched
    # Prepend an early-exit script block before the real script
    reuse_block = (
        '  # fast-resume: short-circuit using reference build vars\n'
        '  - |\n'
        '    if [ -n "$FAST_RESUME_REFERENCE_BUILD_NUMBER" ]; then\n'
        '      echo "BuildNumber=$FAST_RESUME_REFERENCE_BUILD_NUMBER" >> build.env\n'
        '      echo "BuildVersion=$FAST_RESUME_REFERENCE_BUILD_VERSION" >> build.env\n'
        '      echo "DestDir=$FAST_RESUME_REFERENCE_DESTDIR" >> build.env\n'
        '      echo "Workspace_Home=$FAST_RESUME_REFERENCE_DESTDIR" >> build.env\n'
        '      echo "[fast-resume] Reusing reference build $FAST_RESUME_REFERENCE_BUILD_VERSION"\n'
        '      exit 0\n'
        '    fi\n'
    )
    # Insert after the first "script:" line
    content = re.sub(r'(\bscript:\s*\n)', r'\1' + reuse_block, content, count=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Patched reuse path: uft-build-compute-version.yml")


def _patch_buildnumber_creator(stages_dir: str) -> None:
    """Add rules: when: never when FAST_RESUME_REUSE_PREVIOUS_BUILD is true."""
    path = os.path.join(stages_dir, "UFT.BuildNumber.Creator.yml")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "FAST_RESUME_REUSE_PREVIOUS_BUILD" in content:
        return
    # Append rules block to each job definition (insert before first "stage:" line)
    rules_block = (
        '  rules:\n'
        '    - if: \'$FAST_RESUME_REUSE_PREVIOUS_BUILD == "true"\'\n'
        '      when: never\n'
        '    - when: on_success\n'
    )
    content = re.sub(r'(\n  stage:)', rules_block + r'\1', content, count=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Patched rules: UFT.BuildNumber.Creator.yml")


def _generate_bootstrap(path: str, phase: str, info: dict, ref_destdir: str) -> None:
    """Generate the fast-resume-bootstrap.yml validation jobs."""
    check_paths = info.get("workspace_check_paths", ["bin", "build"])
    check_cmds = "\n".join(
        f'    - if not exist "%FAST_RESUME_REFERENCE_DESTDIR%\\{p}" (echo MISSING: {p} & exit 1)'
        for p in check_paths
    )

    lines = [
        "# fast-resume bootstrap validators",
        "# These jobs replace real compilation gates.",
        "# They only verify the reference workspace is intact on disk.",
        "# They do NOT compile anything.",
        "",
    ]
    for job_name, stage, gate in zip(
        info["bootstrap_jobs"],
        info["bootstrap_stages"],
        info["gates_replaced"],
    ):
        lines += [
            f"{job_name}:",
            f"  stage: {stage}",
            f"  # Replaces: {gate}",
            "  script:",
            f'    - echo "fast-resume bootstrap: validating reference workspace"',
            f'    - echo "Reference: %FAST_RESUME_REFERENCE_BUILD_VERSION% at %FAST_RESUME_REFERENCE_DESTDIR%"',
            check_cmds,
            f'    - echo "Bootstrap OK: workspace is intact"',
            "  variables:",
            "    GIT_STRATEGY: none",
            "",
        ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _generate_root_ci(
    source_dir: str,
    output_dir: str,
    phase: str,
    info: dict,
    ref_build_number: str,
    ref_build_version: str,
    ref_destdir: str,
    repo_prefix: str,
    runner_tag: str = "ec2-runner",
) -> None:
    """Generate the root .gitlab-ci.yml for the fast_<phase> pipeline."""
    # Read original for variables block
    try:
        src_ci = load_yaml_file(find_ci_file(source_dir))
        orig_vars = src_ci.get("variables", {})
    except FileNotFoundError:
        orig_vars = {}

    # Build includes list
    include_block = ""
    for stage_file in info["include_stages"]:
        include_block += f"  - local: '{repo_prefix}/ci/stages/{stage_file}'\n"

    # Build stages list
    stages_block = "\n".join(f"  - {s}" for s in info["stages"])

    # Build variables block — preserve originals, add reuse vars
    var_lines = []
    for k, v in orig_vars.items():
        if isinstance(v, dict):
            # GitLab parametrized variable
            val = v.get("value", "")
            desc = v.get("description", "")
            var_lines.append(f"  {k}:")
            var_lines.append(f'    value: "{val}"')
            if desc:
                var_lines.append(f'    description: "{desc}"')
        else:
            var_lines.append(f'  {k}: "{v}"')
    variables_block = "\n".join(var_lines)

    content = f"""\
# fast_{phase} Pipeline — Resume from {phase} phase
# Skips all compilation before {phase} by reusing a reference build workspace.
# Generated by pipeline-phase-resumer skill.
#
# HOW TO UPDATE THE REFERENCE BUILD:
#   Set FAST_RESUME_REFERENCE_BUILD_NUMBER, _BUILD_VERSION, _DESTDIR below
#   to match the pipeline whose workspace you want to reuse.

default:
  tags:
    - {runner_tag}

stages:
{stages_block}

variables:
  # ── fast-resume reuse controls ──────────────────────────────────────────
  FAST_RESUME_REUSE_PREVIOUS_BUILD:
    value: "true"
    description: "Set to false to run a full build instead of reusing a cached workspace"
  FAST_RESUME_REFERENCE_BUILD_NUMBER:
    value: "{ref_build_number}"
    description: "BuildNumber from the reference pipeline (uft-build-compute-version job log)"
  FAST_RESUME_REFERENCE_BUILD_VERSION:
    value: "{ref_build_version}"
    description: "BuildVersion from the reference pipeline (Major.Minor.N.Postfix)"
  FAST_RESUME_REFERENCE_DESTDIR:
    value: "{ref_destdir}"
    description: "DestDir on EC2 runner from the reference pipeline (forward slashes)"
  # ── pipeline variables (preserved from source) ─────────────────────────
{variables_block}

include:
{include_block}
"""
    with open(os.path.join(output_dir, ".gitlab-ci.yml"), "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Command: lint
# ---------------------------------------------------------------------------

def cmd_lint(pipeline_dir: str) -> None:
    """Basic YAML structural validation of the generated pipeline."""
    errors = []
    ci_file = os.path.join(pipeline_dir, ".gitlab-ci.yml")

    if not os.path.isfile(ci_file):
        print(f"ERROR: .gitlab-ci.yml not found in {pipeline_dir}")
        sys.exit(1)

    # 1. Parse root CI
    try:
        root = load_yaml_file(ci_file)
    except yaml.YAMLError as e:
        print(f"YAML parse error in .gitlab-ci.yml: {e}")
        sys.exit(1)

    # 2. Check include paths exist
    includes = root.get("include", [])
    if isinstance(includes, dict):
        includes = [includes]
    for inc in includes:
        if isinstance(inc, dict) and "local" in inc:
            local_path = inc["local"].lstrip("/")
            full = os.path.join(pipeline_dir, "..", local_path)
            # Try relative to pipeline_dir too
            full2 = os.path.join(pipeline_dir, local_path.replace("uft_build/", "").replace("uft_build\\", ""))
            if not os.path.isfile(full) and not os.path.isfile(full2):
                errors.append(f"include: local '{inc['local']}' — file not found")

    # 3. Parse all stage files
    stages_dir = os.path.join(pipeline_dir, "ci", "stages")
    if os.path.isdir(stages_dir):
        for fname in os.listdir(stages_dir):
            if not fname.endswith(".yml"):
                continue
            fpath = os.path.join(stages_dir, fname)
            try:
                load_yaml_file(fpath)
            except yaml.YAMLError as e:
                errors.append(f"{fname}: YAML error — {e}")

    # 4. Check bootstrap file exists
    bootstrap = os.path.join(stages_dir, "fast-resume-bootstrap.yml")
    if not os.path.isfile(bootstrap):
        errors.append("fast-resume-bootstrap.yml not found in ci/stages/")

    # 5. Check mandatory gate vars present in root
    for var in ["FAST_RESUME_REFERENCE_BUILD_NUMBER", "FAST_RESUME_REFERENCE_BUILD_VERSION",
                "FAST_RESUME_REFERENCE_DESTDIR"]:
        if var not in str(root.get("variables", {})):
            errors.append(f"variables: missing {var}")

    if errors:
        print(f"\nLint FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print(f"\nLint PASSED — {pipeline_dir}")


# ---------------------------------------------------------------------------
# Command: discover
# ---------------------------------------------------------------------------

def cmd_discover(pipeline_dir: str) -> None:
    """
    Dynamically scan a pipeline directory to discover logical phases and gate jobs.
    Works on any GitLab CI structure — does NOT require phase to be in PHASE_REGISTRY.
    Prints a phase map that tells you what to pass to 'analyze' and 'generate'.
    """
    try:
        ci_file = find_ci_file(pipeline_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    root = load_yaml_file(ci_file)
    stages: List[str] = root.get("stages", [])
    includes = root.get("include", [])
    if isinstance(includes, dict):
        includes = [includes]

    # Parse all included stage files → build job map
    try:
        stages_dir = find_stages_dir(pipeline_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    job_map: Dict[str, dict] = {}   # job_name -> {stage, needs, file}
    parse_errors: List[str] = []
    files_parsed = 0
    files_missing = 0

    for inc in includes:
        if not isinstance(inc, dict) or "local" not in inc:
            continue
        local_path = inc["local"].replace("\\", "/")
        fname = os.path.basename(local_path)
        fpath = os.path.join(stages_dir, fname)
        if not os.path.isfile(fpath):
            files_missing += 1
            continue
        try:
            data = load_yaml_file(fpath)
            files_parsed += 1
        except Exception as exc:
            parse_errors.append(f"{fname}: {exc}")
            continue
        for job_name, job_def in data.items():
            if not isinstance(job_def, dict) or job_name.startswith("."):
                continue  # skip YAML anchors / templates
            stage = job_def.get("stage", "")
            needs_raw = job_def.get("needs", [])
            needs: List[str] = []
            if isinstance(needs_raw, list):
                for n in needs_raw:
                    if isinstance(n, str):
                        needs.append(n)
                    elif isinstance(n, dict):
                        needs.append(n.get("job", ""))
            job_map[job_name] = {"stage": stage, "needs": needs, "file": fname}

    # Group stages into logical phases by name prefix (first two dash-separated words)
    phase_groups: Dict[str, List[str]] = {}
    for stage in stages:
        parts = stage.split("-")
        phase_key = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else parts[0]
        phase_groups.setdefault(phase_key, []).append(stage)

    # Find BomCheck gate jobs + fan-out (how many downstream jobs need each gate)
    bom_jobs = [(name, info) for name, info in job_map.items()
                if "BomCheck" in name or "bomcheck" in name.lower()]
    gate_fanout: Dict[str, int] = {}
    bom_names = {name for name, _ in bom_jobs}
    for info in job_map.values():
        for needed in info["needs"]:
            if needed in bom_names:
                gate_fanout[needed] = gate_fanout.get(needed, 0) + 1

    # Print discovey report
    print(f"\nPipeline discovery: {pipeline_dir}")
    print(f"  Stages total     : {len(stages)}")
    print(f"  Includes parsed  : {files_parsed}  (missing: {files_missing})")
    print(f"  Jobs found       : {len(job_map)}")
    if parse_errors:
        print(f"  Parse errors     : {len(parse_errors)}")
        for e in parse_errors:
            print(f"    ! {e}")

    print(f"\nLogical phase groups (inferred from stage name prefixes):")
    print(f"  {'Phase key':<30} {'Stages':>6}  {'Registry':>14}  Stages list")
    print(f"  {'-'*30} {'-'*6}  {'-'*14}  {'-'*40}")
    for phase_key, phase_stages in phase_groups.items():
        reg = "✓ supported" if phase_key in PHASE_REGISTRY else "⬜ not registered"
        stages_preview = ", ".join(phase_stages[:3]) + (" ..." if len(phase_stages) > 3 else "")
        print(f"  {phase_key:<30} {len(phase_stages):>6}  {reg:<14}  {stages_preview}")

    print(f"\nGate job candidates (BomCheck pattern — these mark phase boundaries):")
    sorted_gates = sorted(bom_jobs, key=lambda x: gate_fanout.get(x[0], 0), reverse=True)
    for job_name, info in sorted_gates[:15]:
        fanout = gate_fanout.get(job_name, 0)
        print(f"  {job_name:<55} stage: {info['stage']:<28} downstream: {fanout}")
    if len(sorted_gates) > 15:
        print(f"  ... ({len(sorted_gates) - 15} more gate jobs not shown)")

    print(f"\nRegistered phases (ready to use with 'analyze'/'generate'):")
    for phase, phase_info in PHASE_REGISTRY.items():
        print(f"  --phase {phase:<18} {phase_info['description']}")

    print(f"\nTo analyze a specific phase boundary:")
    print(f"  python run.py analyze {pipeline_dir} --phase <phase-key>")
    print(f"\nFor a phase not in the registry, add it to PHASE_REGISTRY in scripts/resumer.py")
    print(f"  (use the gate jobs listed above; or ask the phase-resumer agent to plan it for you)")


# ---------------------------------------------------------------------------
# Command: check-prereqs
# ---------------------------------------------------------------------------

def cmd_check_prereqs(
    pipeline_dir: str,
    phase: str,
    env_file: str = ".env",
    ref_build_number: Optional[str] = None,
    ref_build_version: Optional[str] = None,
    ref_destdir: Optional[str] = None,
) -> None:
    """
    Validate prerequisites needed to generate a fast_<phase> pipeline.
    Outputs a structured PASS / WARN / FAIL report with an action plan for any blockers.
    Exit 0 if ready (all PASS or only WARNs), exit 1 if any FAIL.
    """
    results: List[Tuple[str, str, str]] = []  # (status, item, detail)
    plan_items: List[str] = []

    # 1. .env file ─────────────────────────────────────────────────────────
    env_path = env_file if os.path.isabs(env_file) else os.path.join(os.getcwd(), env_file)
    if os.path.isfile(env_path):
        results.append(("PASS", ".env file", f"found at {env_path}"))
        with open(env_path, "r", encoding="utf-8") as f:
            env_content = f.read()
        for key in ["GITLAB_TOKEN", "GITLAB_PROJECT_ID"]:
            if re.search(rf'^{key}\s*=\s*\S', env_content, re.MULTILINE):
                results.append(("PASS", f".env: {key}", "present and non-empty"))
            else:
                results.append(("FAIL", f".env: {key}", "missing or empty"))
                plan_items.append(f"  Add {key}=<value> to {env_path}")
    else:
        results.append(("FAIL", ".env file", f"not found (looked for {env_path})"))
        plan_items.append(f"  Create {env_path} with at minimum:")
        plan_items.append(f"    GITLAB_TOKEN=<personal_access_token>")
        plan_items.append(f"    GITLAB_PROJECT_ID=<numeric_project_id>")
        plan_items.append(f"  Run the 'devops-setup' skill first if credentials are not yet configured.")

    # 2. Phase ─────────────────────────────────────────────────────────────
    if phase in PHASE_REGISTRY:
        results.append(("PASS", f"Phase '{phase}'", "found in registry — full config available"))
        info = PHASE_REGISTRY[phase]

        # 3. Stage files (only when phase is registered) ───────────────────
        try:
            stages_dir = find_stages_dir(pipeline_dir)
            missing_files: List[str] = []
            found_count = 0
            for fname in info["include_stages"]:
                if fname == "fast-resume-bootstrap.yml":
                    continue  # generated, not expected in source
                fpath = os.path.join(stages_dir, fname)
                if os.path.isfile(fpath):
                    found_count += 1
                else:
                    missing_files.append(fname)
            status = "PASS" if not missing_files else "WARN"
            results.append((status, "Stage files",
                            f"{found_count} found, {len(missing_files)} missing"))
            if missing_files:
                plan_items.append(f"  Missing stage YAMLs (must be migrated before generate):")
                for mf in missing_files:
                    plan_items.append(f"    - {mf}")
                plan_items.append(f"  Use the j2gl-migrate skill to convert the Jenkins XML for each missing file.")
        except FileNotFoundError as e:
            results.append(("FAIL", "Stage files", str(e)))
            plan_items.append(f"  Ensure this directory exists: {pipeline_dir}/ci/stages/")
    else:
        results.append(("WARN", f"Phase '{phase}'",
                        "not in PHASE_REGISTRY — run 'discover' to see gate jobs, then add an entry"))
        plan_items.append(f"  Option A: Use a registered phase: {', '.join(PHASE_REGISTRY.keys()) or 'none yet'}")
        plan_items.append(f"  Option B: Run 'discover' to inspect this pipeline's phase boundary jobs,")
        plan_items.append(f"            then add a '{phase}' entry to PHASE_REGISTRY in scripts/resumer.py")
        plan_items.append(f"            or ask the phase-resumer agent to draft the registry entry for you.")

    # 4. Reference build variables ─────────────────────────────────────────
    all_ref = ref_build_number and ref_build_version and ref_destdir
    if all_ref:
        results.append(("PASS", "Reference build vars",
                        f"BUID_NUMBER={ref_build_number}  VERSION={ref_build_version}"))
        results.append(("PASS", "Reference DESTDIR", str(ref_destdir)))
    else:
        missing_vars = []
        if not ref_build_number:
            missing_vars.append("--ref-build-number")
        if not ref_build_version:
            missing_vars.append("--ref-build-version")
        if not ref_destdir:
            missing_vars.append("--ref-destdir")
        results.append(("FAIL", "Reference build vars", f"missing: {', '.join(missing_vars)}"))
        plan_items.append(f"  Get reference build info from any successful pipeline run:")
        plan_items.append(f"    1. Open the 'uft-build-compute-version' job log")
        plan_items.append(f"    2. Find lines: BuildNumber=N, BuildVersion=X.Y.Z.W, DestDir=<path>")
        plan_items.append(f"    3. Pass these to 'generate' as --ref-build-number / --ref-build-version / --ref-destdir")
        plan_items.append(f"    4. Or ask the phase-resumer agent: 'find me the latest successful pipeline vars'")

    # Print report ─────────────────────────────────────────────────────────
    icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}
    print(f"\nPREREQ CHECK  phase={phase}  source={pipeline_dir}")
    print("=" * 70)
    has_fail = False
    has_warn = False
    for status, item, detail in results:
        print(f"  [{status}] {icon.get(status,'?')} {item}")
        print(f"         {detail}")
        if status == "FAIL":
            has_fail = True
        elif status == "WARN":
            has_warn = True

    if plan_items:
        print(f"\nACTION PLAN:")
        for item in plan_items:
            print(item)

    if has_fail:
        print(f"\nSTATUS: BLOCKED — resolve FAIL items above before running 'generate'")
        sys.exit(1)
    elif has_warn:
        print(f"\nSTATUS: WARNINGS — review items above; generation can proceed with caution")
    else:
        print(f"\nSTATUS: READY — all prerequisites met, safe to run 'generate'")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline Phase Resumer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Typical workflow:\n"
            "  1. discover   — scan pipeline to see available phases and gate jobs\n"
            "  2. check-prereqs — validate you have everything needed before generate\n"
            "  3. analyze    — show exactly what will be generated for a given phase\n"
            "  4. generate   — produce the fast_<phase> pipeline directory\n"
            "  5. lint       — validate the generated YAML\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # discover  ─ dynamic phase/gate inspection (no phase required)
    p_disc = sub.add_parser(
        "discover",
        help="Scan a pipeline directory to discover phases, stages, and gate jobs (no phase required)",
    )
    p_disc.add_argument("pipeline_dir", help="Path to source pipeline directory (e.g. migrated_yamls/uft_build)")

    # check-prereqs  ─ validate all inputs before generate
    p_pre = sub.add_parser(
        "check-prereqs",
        help="Validate prerequisites for generating a fast-path pipeline; prints an action plan on failure",
    )
    p_pre.add_argument("pipeline_dir", help="Path to source pipeline directory")
    p_pre.add_argument("--phase", required=True,
                       help="Phase to check (use 'discover' to find valid phase keys)")
    p_pre.add_argument("--env-file", default=".env",
                       help="Path to .env file containing GITLAB_TOKEN/GITLAB_PROJECT_ID (default: .env)")
    p_pre.add_argument("--ref-build-number", default=None,
                       help="BuildNumber from reference pipeline (optional — detected as FAIL if omitted)")
    p_pre.add_argument("--ref-build-version", default=None,
                       help="BuildVersion from reference pipeline (optional — detected as FAIL if omitted)")
    p_pre.add_argument("--ref-destdir", default=None,
                       help="DestDir on runner from reference pipeline (optional — detected as FAIL if omitted)")

    # analyze  ─ detailed gate/include breakdown for a known phase
    p_analyze = sub.add_parser(
        "analyze",
        help="Show gate jobs, stage files, and needs patches for a target phase",
    )
    p_analyze.add_argument("pipeline_dir", help="Path to source pipeline directory")
    p_analyze.add_argument("--phase", required=True,
                           help="Phase name to analyze (must be in PHASE_REGISTRY; run 'discover' first if unsure)")

    # generate  ─ produce the fast_<phase> pipeline directory
    p_gen = sub.add_parser("generate", help="Generate the fast_<phase> pipeline directory")
    p_gen.add_argument("--source-dir", required=True,
                       help="Source pipeline directory (e.g. migrated_yamls/uft_build)")
    p_gen.add_argument("--output-dir", required=True,
                       help="Output directory (e.g. migrated_yamls/fast_addins)")
    p_gen.add_argument("--phase", required=True,
                       help="Phase to resume from (must be in PHASE_REGISTRY)")
    p_gen.add_argument("--ref-build-number", required=True,
                       help="BuildNumber from reference pipeline")
    p_gen.add_argument("--ref-build-version", required=True,
                       help="BuildVersion from reference pipeline (e.g. 2026.3.12.0)")
    p_gen.add_argument("--ref-destdir", required=True,
                       help="DestDir on runner (e.g. E:/FT/QTP/win32_release/2026.3.12.0)")
    p_gen.add_argument("--repo-prefix", default="uft_build",
                       help="GitLab repo-root folder name used in include: local: paths (default: uft_build)")
    p_gen.add_argument("--runner-tag", default="ec2-runner",
                       help="GitLab runner tag for the default: tags: block (default: ec2-runner)")

    # lint  ─ structural YAML validation
    p_lint = sub.add_parser("lint", help="Validate YAML structure of a generated pipeline")
    p_lint.add_argument("--pipeline-dir", required=True,
                        help="Path to generated pipeline directory")

    args = parser.parse_args()

    if args.command == "discover":
        cmd_discover(args.pipeline_dir)
    elif args.command == "check-prereqs":
        cmd_check_prereqs(
            pipeline_dir=args.pipeline_dir,
            phase=args.phase,
            env_file=args.env_file,
            ref_build_number=args.ref_build_number,
            ref_build_version=args.ref_build_version,
            ref_destdir=args.ref_destdir,
        )
    elif args.command == "analyze":
        cmd_analyze(args.pipeline_dir, args.phase)
    elif args.command == "generate":
        cmd_generate(
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            phase=args.phase,
            ref_build_number=args.ref_build_number,
            ref_build_version=args.ref_build_version,
            ref_destdir=args.ref_destdir,
            repo_prefix=args.repo_prefix,
            runner_tag=args.runner_tag,
        )
    elif args.command == "lint":
        cmd_lint(args.pipeline_dir)
