#!/usr/bin/env python3
"""
Pipeline Decoupler — Runner Script
Run from any directory:
    python .github/skills/pipeline-decoupler/run.py analyze <pipeline_dir>
    python .github/skills/pipeline-decoupler/run.py decouple <pipeline_dir>
    python .github/skills/pipeline-decoupler/run.py full <pipeline_dir>

Requires: PyYAML (pip install pyyaml)
"""
import sys
import os

# Add scripts dir to path so imports work
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
sys.path.insert(0, os.path.dirname(SCRIPTS_DIR))

# Import using the package name
from scripts.cli import main
main()
