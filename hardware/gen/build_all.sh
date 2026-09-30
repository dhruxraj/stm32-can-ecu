#!/usr/bin/env bash
# Rebuild all hardware outputs from the Python design description.
set -euo pipefail
cd "$(dirname "$0")"
python3 routing.py        # placement is in board.py; writes routes.json (~1 min)
python3 checks.py
python3 write_kicad.py
python3 validate_files.py
python3 fab.py
python3 gen_docs.py
