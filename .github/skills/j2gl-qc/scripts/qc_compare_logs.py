#!/usr/bin/env python3

import argparse
from pathlib import Path
import re

from llm_call_template import DEFAULT_MODEL, call_llm


ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


SYSTEM_PROMPT = """You are a migration quality reviewer for Jenkins to GitLab CI conversions.

Your task is to compare a GitLab execution log to the corresponding Jenkins execution log for the same logical job or helper step.

Rules:
- Do not rely on GitLab success or failure alone.
- Classify SUCCESS only if the GitLab job reproduced the required Jenkins behavior closely enough for migration purposes.
- Classify FAIL if GitLab missed required behavior, failed earlier than Jenkins, used wrong inputs, or produced materially different side effects.
- Classify BLOCKED only if there is genuinely insufficient evidence to decide.
- Be strict about missing environment resolution, missing artifacts, missing network paths, and skipped functional steps.
- The GitLab job may be a synthetic helper that corresponds to only part of a Jenkins root job. In that case, compare only that logical portion.

Output format:
First line exactly: QC_STATUS: SUCCESS or QC_STATUS: FAIL or QC_STATUS: BLOCKED
Then provide short markdown sections named:
Assessment
Matched Behavior
Mismatches
Root Cause
Required Fix Before Next QC
"""


def read_text(path: Path, max_chars: int) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = ANSI_RE.sub("", text)
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[TRUNCATED]\n"
    return text


def build_messages(job_name: str, jenkins_job_name: str, mapping_notes: str, jenkins_log: str, gitlab_log: str) -> list[dict[str, str]]:
    user_prompt = f"""Job under QC: {job_name}
Corresponding Jenkins job: {jenkins_job_name}
Mapping notes: {mapping_notes}

Jenkins log:
```text
{jenkins_log}
```

GitLab log:
```text
{gitlab_log}
```

Compare the logs according to the rules and produce the required QC output.
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-assisted Jenkins vs GitLab log QC comparison")
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--jenkins-job-name", required=True)
    parser.add_argument("--jenkins-log", required=True)
    parser.add_argument("--gitlab-log", required=True)
    parser.add_argument("--mapping-notes", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-chars", type=int, default=16000)
    args = parser.parse_args()

    jenkins_log_path = Path(args.jenkins_log)
    gitlab_log_path = Path(args.gitlab_log)
    output_path = Path(args.output)

    jenkins_log = read_text(jenkins_log_path, args.max_chars)
    gitlab_log = read_text(gitlab_log_path, args.max_chars)
    messages = build_messages(
        args.job_name,
        args.jenkins_job_name,
        args.mapping_notes,
        jenkins_log,
        gitlab_log,
    )
    result = call_llm(messages, model=args.model).strip()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result + "\n", encoding="utf-8")
    print(result)
    print(f"\nSaved QC report to {output_path}")


if __name__ == "__main__":
    main()