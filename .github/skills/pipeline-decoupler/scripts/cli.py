"""
Pipeline Decoupler CLI
Usage:
    python -m pipeline_decoupler analyze <pipeline_dir> [--ci-file FILE]
    python -m pipeline_decoupler decouple <pipeline_dir> [--ci-file FILE] [--output-dir DIR]
    python -m pipeline_decoupler full <pipeline_dir> [--ci-file FILE] [--output-dir DIR]
"""

import argparse
import os
import sys
import json

from .analyzer import analyze_pipeline
from .decoupler import decouple_pipeline


def cmd_analyze(args):
    """Analyze a pipeline and print the report."""
    result = analyze_pipeline(args.pipeline_dir, args.ci_file)
    print(result.summary())

    if args.json:
        json_path = os.path.join(args.pipeline_dir, "pipeline_analysis.json")
        data = {
            "ci_file": result.ci_file,
            "stages": result.stages,
            "total_jobs": result.total_jobs,
            "jobs": {
                name: {
                    "stage": j.stage,
                    "needs": j.needs,
                    "has_dotenv": j.has_dotenv,
                    "dotenv_file": j.dotenv_file,
                    "source_file": j.source_file,
                }
                for name, j in result.jobs.items()
            },
            "topo_order": result.topo_order,
            "bottlenecks": [{"job": b[0], "downstream_count": b[1]} for b in result.bottlenecks],
            "phases": [
                {
                    "id": p.id,
                    "name": p.name,
                    "jobs": p.jobs,
                    "stages": p.stages_covered,
                    "exit_job": p.exit_job,
                    "cross_phase_needs": p.cross_phase_needs,
                    "dotenv_sources": p.dotenv_sources,
                }
                for p in result.phases
            ],
            "dotenv_producers": result.dotenv_producers,
            "include_files": result.include_files,
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"\nJSON analysis written to: {json_path}")


def cmd_decouple(args):
    """Analyze and generate decoupled pipeline files."""
    print(f"Analyzing pipeline: {args.pipeline_dir}/{args.ci_file}")
    result = analyze_pipeline(args.pipeline_dir, args.ci_file)

    print(f"\nFound {result.total_jobs} jobs in {len(result.stages)} stages")
    print(f"Identified {len(result.phases)} phases, {len(result.bottlenecks)} bottlenecks\n")

    output_dir = args.output_dir or os.path.join(args.pipeline_dir, "decoupled_output")
    os.makedirs(output_dir, exist_ok=True)

    files = decouple_pipeline(result, output_dir)

    for rel_path, content in files.items():
        full_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Generated: {rel_path}")

    print(f"\nAll files written to: {output_dir}")
    print("Review DECOUPLING_PLAN.md for instructions.")


def cmd_full(args):
    """Run both analyze and decouple."""
    args_copy = argparse.Namespace(**vars(args))
    args_copy.json = True
    cmd_analyze(args_copy)
    print("\n" + "=" * 70 + "\n")
    cmd_decouple(args)


def main():
    parser = argparse.ArgumentParser(
        prog="pipeline_decoupler",
        description="Analyze and decouple GitLab CI/CD pipelines for skip-ahead execution.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze a pipeline and print dependency report")
    p_analyze.add_argument("pipeline_dir", help="Directory containing .gitlab-ci.yml")
    p_analyze.add_argument("--ci-file", default=".gitlab-ci.yml", help="Main CI file name (default: .gitlab-ci.yml)")
    p_analyze.add_argument("--json", action="store_true", help="Also write JSON analysis file")
    p_analyze.set_defaults(func=cmd_analyze)

    # decouple
    p_decouple = subparsers.add_parser("decouple", help="Generate decoupled pipeline files with skip-ahead support")
    p_decouple.add_argument("pipeline_dir", help="Directory containing .gitlab-ci.yml")
    p_decouple.add_argument("--ci-file", default=".gitlab-ci.yml", help="Main CI file name (default: .gitlab-ci.yml)")
    p_decouple.add_argument("--output-dir", help="Output directory (default: <pipeline_dir>/decoupled_output)")
    p_decouple.set_defaults(func=cmd_decouple)

    # full
    p_full = subparsers.add_parser("full", help="Run analyze + decouple")
    p_full.add_argument("pipeline_dir", help="Directory containing .gitlab-ci.yml")
    p_full.add_argument("--ci-file", default=".gitlab-ci.yml", help="Main CI file name (default: .gitlab-ci.yml)")
    p_full.add_argument("--output-dir", help="Output directory (default: <pipeline_dir>/decoupled_output)")
    p_full.set_defaults(func=cmd_full)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
