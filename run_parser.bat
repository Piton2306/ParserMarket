@echo off
cd /d %~dp0
call .venv\Scripts\activate
python wishmaster\parser_wishmaster.py
pause
