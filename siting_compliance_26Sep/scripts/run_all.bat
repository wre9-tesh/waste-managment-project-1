@echo off
REM Runs the whole siting-compliance analysis (Windows). Double-click or run from this folder.
REM Step 01 needs internet and ~15 min; skip it (REM the line) to reproduce the exact numbers from data\raw.
cd /d "%~dp0"
python 01_download_layers.py || goto :err
python 02_siting_check.py || goto :err
python 03_figures_tables.py || goto :err
python 04_verify.py || goto :err
echo DONE - see ..\figures and ..\outputs\tables
pause
exit /b 0
:err
echo A step failed - read the message above.
pause
