@echo off
title PDF Analyzer Backend
echo ====================================================
echo   PDF Analyzer Backend API is starting on port 8080...
echo ====================================================
cd /d "%~dp0"
python run.py
pause
