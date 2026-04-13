#!/usr/bin/env python3
"""
Pipeline Phase Resumer — Runner Script

Usage:
    python .github/skills/pipeline-phase-resumer/run.py analyze <pipeline_dir> --phase <phase>
    python .github/skills/pipeline-phase-resumer/run.py generate --source-dir <dir> --output-dir <dir> --phase <phase> --ref-build-number N --ref-build-version X.Y.Z.W --ref-destdir "E:/..."
    python .github/skills/pipeline-phase-resumer/run.py lint --pipeline-dir <dir>

Requires: PyYAML  (uv run --with pyyaml ...)
"""
import sys
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
sys.path.insert(0, os.path.dirname(SCRIPTS_DIR))

from scripts.resumer import main
main()
