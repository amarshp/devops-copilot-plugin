#!/usr/bin/env python3
"""
log_excerpt.py
--------------
Extracts all meaningful signal lines from a large CI/build log (any size, no truncation).
Scans every line, deduplicates repeated identical lines (keeping a count), and writes a
compact excerpt file suitable for LLM comparison via qc_compare_logs.py.

Use this BEFORE qc_compare_logs.py whenever the raw log exceeds ~50KB.
The output excerpt is typically 5-30KB regardless of source log size.

Usage:
    python log_excerpt.py --log path/to/raw.log --output path/to/excerpt.log
    python log_excerpt.py --log path/to/raw.log  # prints to stdout

Signal categories captured (ALL matching lines, no cap):
  - C# compile errors:      error CS####:
  - MSBuild task errors:    error MSB####:
  - NuGet errors:           error NU####:
  - Generic build errors:   ": error "  (avoids false positives from "no error" / "error-prone")
  - C# compile warnings:    warning CS####:
  - MSBuild warnings:       warning MSB####:
  - NuGet warnings:         warning NU####:
  - MSBuild summaries:      "X Error(s)", "X Warning(s)"
  - Build outcome:          "Build succeeded.", "Build FAILED."
  - Job outcome:            "Job succeeded", "Job failed"
  - Exit code lines:        "exit code N", "exiting with code N", "Exit status N"
  - Robocopy result:        robocopy summary lines (files copied/failed counts)
  - Self-heal / retry:      "self-heal", "retry succeeded", "CS0535 self-heal"
  - Exceptions / tracebacks:"EXCEPTION", "Traceback (most recent"
  - FATAL lines:            lines containing FATAL
  - NuGet restore failures: "packages failed to restore", "restore failed"
  - Network / share errors: "The network path was not found", "Access is denied", "NET USE"
  - GitLab runner markers:  "$ " command echo lines (first 40 only, to show what ran)
  - Section headers:        "=== ", "--- ", lines of repeated = or - (phase boundaries)
"""

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path


# ---------------------------------------------------------------------------
# Pattern groups — ordered from most specific to most generic so the category
# label assigned to each line is meaningful.
# ---------------------------------------------------------------------------

PATTERNS = [
    # --- Compile / build errors (specific error codes first) ---
    ("CS_ERROR",      re.compile(r"\berror\s+CS\d+\s*:", re.I)),
    ("MSB_ERROR",     re.compile(r"\berror\s+MSB\d+\s*:", re.I)),
    ("NU_ERROR",      re.compile(r"\berror\s+NU\d+\s*:", re.I)),
    # Generic ": error " catches linker errors, custom task errors, etc.
    # Use ": error " (colon+space prefix) to avoid matching "no error", "error-prone"
    ("BUILD_ERROR",   re.compile(r":\s+error\s+", re.I)),

    # --- Compile / build warnings (specific codes first) ---
    ("CS_WARN",       re.compile(r"\bwarning\s+CS\d+\s*:", re.I)),
    ("MSB_WARN",      re.compile(r"\bwarning\s+MSB\d+\s*:", re.I)),
    ("NU_WARN",       re.compile(r"\bwarning\s+NU\d+\s*:", re.I)),

    # --- MSBuild summary lines ---
    ("MSBUILD_SUMMARY", re.compile(r"\d+\s+Error\(s\)|\d+\s+Warning\(s\)", re.I)),

    # --- Build outcome ---
    ("BUILD_RESULT",  re.compile(r"Build\s+(succeeded|FAILED)\b", re.I)),

    # --- Job / pipeline outcome ---
    ("JOB_RESULT",    re.compile(r"\bJob\s+(succeeded|failed)\b", re.I)),

    # --- Exit codes ---
    ("EXIT_CODE",     re.compile(r"exit(?:ing with)?\s+(?:code\s+)?(\d+)|exit\s+status\s+\d+", re.I)),

    # --- Robocopy result summary ---
    # Robocopy prints a summary table with "Files :", "Dirs :", "Bytes :"
    # followed by counts. The critical line is the one with "Failed" column > 0.
    ("ROBOCOPY",      re.compile(
        r"(?:Files\s*:|Dirs\s*:|Bytes\s*:.*Failed|ERROR\s+\d+\s+\(0x)"
        r"|The process cannot access|Robocopy.*exited",
        re.I
    )),

    # --- Self-heal / retry ---
    ("SELF_HEAL",     re.compile(r"self.?heal|retry\s+succeeded|CS0535\s+self", re.I)),

    # --- Exceptions / tracebacks ---
    ("EXCEPTION",     re.compile(r"\bEXCEPTION\b|Traceback \(most recent", re.I)),

    # --- FATAL ---
    ("FATAL",         re.compile(r"\bFATAL\b", re.I)),

    # --- NuGet restore failures ---
    ("NUGET_FAIL",    re.compile(r"packages?\s+failed\s+to\s+restore|restore\s+failed", re.I)),

    # --- Network / share errors ---
    ("NETWORK_ERR",   re.compile(
        r"The network path was not found"
        r"|Access is denied"
        r"|NET USE.*error"
        r"|System error \d+ has occurred"
        r"|could not be mapped",
        re.I
    )),

    # --- BOM check ---
    ("BOM_CHECK",     re.compile(r"bom.?check|BOMCheck", re.I)),

    # --- Section headers / phase boundaries ---
    # Lines like "=== Stage: Compile ===" or "--- NuGet Restore ---"
    # Also MSBuild project headers: "Build started", "Project \"...\" on node"
    ("SECTION",       re.compile(
        r"^={3,}|^-{3,}"
        r"|Build started\b"
        r'|Project\s+"[^"]+"\s+\(default targets\)'
        r"|Target\s+\w+.*in project",
        re.I
    )),
]

# GitLab runner command echo lines start with "$ " — limit these to first N
# so the LLM sees what commands ran without thousands of echo lines
MAX_COMMAND_LINES = 40

ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

# For summary computation
_RE_MSBUILD_ERR_COUNT  = re.compile(r"(\d+)\s+Error\(s\)", re.I)
_RE_MSBUILD_WARN_COUNT = re.compile(r"(\d+)\s+Warning\(s\)", re.I)
_RE_CS_ERR_CODE        = re.compile(r"\berror\s+(CS\d+)\s*:", re.I)
_RE_WARN_CODE          = re.compile(r"\bwarning\s+(CS\d+|MSB\d+|NU\d+)\s*:", re.I)
_RE_BUILD_RESULT       = re.compile(r"Build\s+(succeeded|FAILED)", re.I)
_RE_JOB_RESULT         = re.compile(r"\bJob\s+(succeeded|failed)", re.I)
_RE_EXIT_CODE          = re.compile(r"exit(?:ing with)?\s+(?:code\s+)?(\d+)|exit\s+status\s+(\d+)", re.I)


def strip_ansi(line: str) -> str:
    return ANSI_RE.sub("", line)


def categorize(line: str):
    """Return the first matching category name, or None if the line is not signal."""
    for name, pattern in PATTERNS:
        if pattern.search(line):
            return name
    return None


def extract(log_path: Path) -> list[str]:
    """
    Stream the log file line by line. Collect signal lines with deduplication.
    Also compute a per-job SUMMARY block (error counts, warning codes, build/job result).
    Returns a list of output lines (strings, already formatted).
    """
    # dedup: stripped_line -> (category, count, first_seen_line_no, original_line)
    seen: OrderedDict[str, list] = OrderedDict()
    command_lines_seen = 0
    total_lines = 0

    # Summary accumulators
    max_msbuild_errors   = 0
    max_msbuild_warnings = 0
    cs_error_codes: set[str]   = set()
    warning_codes:  set[str]   = set()
    build_result  = "unknown"
    job_result    = "unknown"
    exit_codes: list[int] = []
    has_self_heal = False

    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line_no, raw in enumerate(fh, 1):
            total_lines += 1
            line = strip_ansi(raw.rstrip("\n"))
            if not line.strip():
                continue

            # --- Summary accumulation (runs on every line, not just signal lines) ---
            m = _RE_MSBUILD_ERR_COUNT.search(line)
            if m:
                max_msbuild_errors = max(max_msbuild_errors, int(m.group(1)))
            m = _RE_MSBUILD_WARN_COUNT.search(line)
            if m:
                max_msbuild_warnings = max(max_msbuild_warnings, int(m.group(1)))
            for m in _RE_CS_ERR_CODE.finditer(line):
                cs_error_codes.add(m.group(1))
            for m in _RE_WARN_CODE.finditer(line):
                warning_codes.add(m.group(1))
            m = _RE_BUILD_RESULT.search(line)
            if m:
                build_result = m.group(1).upper()
            m = _RE_JOB_RESULT.search(line)
            if m:
                job_result = m.group(1).lower()
            m = _RE_EXIT_CODE.search(line)
            if m:
                code_str = m.group(1) or m.group(2)
                if code_str:
                    exit_codes.append(int(code_str))
            if re.search(r"self.?heal|retry\s+succeeded", line, re.I):
                has_self_heal = True

            # --- Signal line collection ---
            # GitLab runner command echo (starts with "$ ")
            if line.lstrip().startswith("$ "):
                if command_lines_seen < MAX_COMMAND_LINES:
                    key = line.strip()
                    if key not in seen:
                        seen[key] = ["CMD", 1, line_no, line]
                    else:
                        seen[key][1] += 1
                    command_lines_seen += 1
                continue

            cat = categorize(line)
            if cat is None:
                continue

            key = line.strip()
            if key in seen:
                seen[key][1] += 1  # increment count
            else:
                seen[key] = [cat, 1, line_no, line]

    # --- Build SUMMARY block ---
    summary: list[str] = []
    summary.append("## SUMMARY")
    summary.append(f"  MSBuild errors   : {max_msbuild_errors}")
    summary.append(f"  MSBuild warnings : {max_msbuild_warnings}")
    summary.append(f"  CS error codes   : {', '.join(sorted(cs_error_codes)) or 'none'}")
    summary.append(f"  Warning codes    : {', '.join(sorted(warning_codes)) or 'none'}")
    summary.append(f"  Build result     : {build_result}")
    summary.append(f"  Job result       : {job_result}")
    if exit_codes:
        last = exit_codes[-1]
        summary.append(f"  Exit code (last) : {last}  {'<-- non-zero' if last != 0 else ''}")
    summary.append(f"  Self-heal        : {'YES' if has_self_heal else 'no'}")

    # --- Build output ---
    out: list[str] = []
    out.append(f"# LOG EXCERPT — {log_path.name}")
    out.append(f"# Source: {log_path}")
    out.append(f"# Total lines scanned: {total_lines:,}")
    out.append(f"# Signal lines (deduplicated): {len(seen):,}")
    out.append("#")
    out.append("# Format of detail sections: (xN if repeated) | line_no | content")
    out.append("#")
    out.extend(summary)
    out.append("")

    # Group by category for readability
    by_cat: dict[str, list] = {}
    for key, (cat, count, line_no, line) in seen.items():
        by_cat.setdefault(cat, []).append((count, line_no, line))

    category_order = [
        "FATAL", "EXCEPTION",
        "CS_ERROR", "MSB_ERROR", "NU_ERROR", "BUILD_ERROR",
        "NUGET_FAIL", "NETWORK_ERR",
        "MSBUILD_SUMMARY", "BUILD_RESULT", "JOB_RESULT", "EXIT_CODE",
        "ROBOCOPY",
        "SELF_HEAL", "BOM_CHECK",
        "CS_WARN", "MSB_WARN", "NU_WARN",
        "SECTION",
        "CMD",
    ]

    for cat in category_order:
        if cat not in by_cat:
            continue
        out.append(f"\n## {cat}")
        for count, line_no, line in by_cat[cat]:
            repeat = f" (x{count})" if count > 1 else ""
            out.append(f"  L{line_no:>6}{repeat}  {line}")

    # Any categories not in ordered list
    for cat, entries in by_cat.items():
        if cat in category_order:
            continue
        out.append(f"\n## {cat}")
        for count, line_no, line in entries:
            repeat = f" (x{count})" if count > 1 else ""
            out.append(f"  L{line_no:>6}{repeat}  {line}")

    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Extract all signal lines from a large CI/build log for LLM comparison. "
            "Scans every line — no truncation. Output is ~5-30KB regardless of source size. "
            "Pass the output file to qc_compare_logs.py as --jenkins-log or --gitlab-log."
        )
    )
    ap.add_argument("--log", required=True, help="Path to the raw log file (any size)")
    ap.add_argument(
        "--output",
        help="Write excerpt to this file. If omitted, prints to stdout.",
    )
    args = ap.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        sys.exit(f"ERROR: log file not found: {log_path}")

    lines = extract(log_path)
    text = "\n".join(lines) + "\n"

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"Excerpt written -> {out_path}  ({len(text):,} bytes)")
    else:
        print(text)


if __name__ == "__main__":
    main()
