@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Cai dat thu vien cho Tool 1 - Kiro IDE Swapper ===
where py >nul 2>nul
if %errorlevel%==0 ( py -m pip install -r requirements.txt ) else ( python -m pip install -r requirements.txt )
echo.
echo === Xong. Bay gio chay RUN.bat ===
pause
