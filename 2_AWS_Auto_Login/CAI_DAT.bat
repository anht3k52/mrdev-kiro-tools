@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Cai dat thu vien cho Tool 2 - AWS Auto Login ===
where py >nul 2>nul
if %errorlevel%==0 (
  py -m pip install -r requirements.txt
  echo --- Cai trinh duyet Chromium cho Playwright ---
  py -m playwright install chromium
) else (
  python -m pip install -r requirements.txt
  echo --- Cai trinh duyet Chromium cho Playwright ---
  python -m playwright install chromium
)
echo.
echo === Xong. Bay gio chay RUN.bat ===
pause
