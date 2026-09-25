#!/bin/sh
# Runs the whole siting-compliance analysis (Linux / macOS).
cd "$(dirname "$0")" || exit 1
python3 01_download_layers.py && python3 02_siting_check.py && python3 03_figures_tables.py && python3 04_verify.py && echo "DONE - see ../figures and ../outputs/tables"
