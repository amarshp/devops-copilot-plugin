#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path


def _analyze(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    msbuild_errors = 0
    msbuild_warnings = 0
    cs_errors = []
    warning_codes = set()

    for line_number, line in enumerate(lines, 1):
        error_match = re.search(r"(\d+) Error\(s\)", line)
        if error_match:
            msbuild_errors = max(msbuild_errors, int(error_match.group(1)))
        warning_match = re.search(r"(\d+) Warning\(s\)", line)
        if warning_match:
            msbuild_warnings = max(msbuild_warnings, int(warning_match.group(1)))

        if re.search(r"\berror\s+CS\d+:", line):
            cs_errors.append((line_number, line.strip()[:220]))

        warning_code_match = re.search(r":\s*warning\s+(CS\d+|MSB\d+|NU\d+):", line)
        if warning_code_match:
            warning_codes.add(warning_code_match.group(1))

    lower = text.lower()
    return {
        "name": path.stem,
        "path": str(path),
        "msbuild_errors": msbuild_errors,
        "msbuild_warnings": msbuild_warnings,
        "cs_errors": cs_errors,
        "warning_codes": sorted(warning_codes),
        "has_self_heal": "self-heal" in lower or "self heal" in lower or "retry succeeded" in lower,
    }


def _load_manifest(path: Path) -> list[Path]:
    data = json.loads(path.read_text(encoding="utf-8"))
    files = []
    for job in data.get("jobs", []):
        candidate = Path(job.get("log_path", ""))
        if candidate.exists():
            files.append(candidate)
    return files


def _resolve_files(args: argparse.Namespace) -> list[Path]:
    log_dir = Path(args.log_dir)
    if args.manifest:
        files = _load_manifest(Path(args.manifest))
    elif args.pipeline_id:
        files = [Path(item) for item in sorted(glob.glob(str(log_dir / f"p{args.pipeline_id}_*.log")))]
    elif args.all:
        files = [Path(item) for item in sorted(glob.glob(str(log_dir / "*.log")))]
    else:
        pattern = args.logs_glob or str(log_dir / "*.log")
        files = [Path(item) for item in sorted(glob.glob(pattern))]
    if not files:
        raise RuntimeError("No logs found for the requested selection")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze downloaded QC logs")
    parser.add_argument("--pipeline-id", help="Analyze logs for a specific pipeline ID")
    parser.add_argument("--log-dir", default="pipeline_logs", help="Directory that contains downloaded logs")
    parser.add_argument("--manifest", help="Manifest produced by qc_bulk_download.py")
    parser.add_argument("--logs-glob", help="Explicit glob for log files")
    parser.add_argument("--all", action="store_true", help="Analyze all logs under --log-dir")
    parser.add_argument("--output")
    args = parser.parse_args()

    files = _resolve_files(args)
    results = [_analyze(path) for path in files]

    warning_index: dict[str, int] = {}
    issues = []
    for result in results:
        for code in result["warning_codes"]:
            warning_index[code] = warning_index.get(code, 0) + 1
        if result["msbuild_errors"] or result["msbuild_warnings"] or result["cs_errors"] or result["has_self_heal"]:
            issues.append(result)

    lines = []
    lines.append("QC Analysis")
    lines.append("=" * 80)
    lines.append(f"Logs analyzed: {len(results)}")
    lines.append(f"Logs with issues: {len(issues)}")

    lines.append("\nSection 1: All Jobs")
    lines.append("-" * 80)
    for result in results:
        lines.append(
            f"- {result['name']}: "
            f"MSBuildE={result['msbuild_errors']} "
            f"MSBuildW={result['msbuild_warnings']} "
            f"CS={len(result['cs_errors'])} "
            f"SelfHeal={'yes' if result['has_self_heal'] else 'no'}"
        )

    lines.append("\nSection 2: Warning Categories")
    lines.append("-" * 80)
    if warning_index:
        for code, count in sorted(warning_index.items(), key=lambda item: item[0]):
            lines.append(f"- {code}: {count}")
    else:
        lines.append("- None")

    lines.append("\nSection 3: Self-Heal Signals")
    lines.append("-" * 80)
    self_heal_jobs = [result["name"] for result in results if result["has_self_heal"]]
    if self_heal_jobs:
        for job_name in self_heal_jobs:
            lines.append(f"- {job_name}")
    else:
        lines.append("- None")

    lines.append("\nSection 4: C# Errors")
    lines.append("-" * 80)
    found_cs_errors = False
    for result in results:
        if not result["cs_errors"]:
            continue
        found_cs_errors = True
        lines.append(f"- {result['name']}")
        for line_number, text in result["cs_errors"]:
            lines.append(f"  line {line_number}: {text}")
    if not found_cs_errors:
        lines.append("- None")

    lines.append("\nSection 5: Issues Table")
    lines.append("-" * 80)
    if issues:
        for result in issues:
            warning_codes = ", ".join(result["warning_codes"]) if result["warning_codes"] else "-"
            lines.append(
                f"- {result['name']} | "
                f"errors={result['msbuild_errors']} | "
                f"warnings={result['msbuild_warnings']} | "
                f"cs_errors={len(result['cs_errors'])} | "
                f"self_heal={'yes' if result['has_self_heal'] else 'no'} | "
                f"warning_codes={warning_codes}"
            )
    else:
        lines.append("- No issues detected")

    report = "\n".join(lines) + "\n"
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Saved report to {args.output}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
