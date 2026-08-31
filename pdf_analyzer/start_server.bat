@echo off
title PDF Analyzer Server
echo ====================================================
echo   PDF Analyzer Server is starting...
echo ====================================================
cd /d "%~dp0"
echo Opening browser at http://127.0.0.1:8080 ...
start http://127.0.0.1:8080
python run.py
pause
