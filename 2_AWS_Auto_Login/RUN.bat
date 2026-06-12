@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 ( py auto_login_gui.py ) else ( python auto_login_gui.py )
if errorlevel 1 (
  echo.
  echo Co loi. Neu lan dau, chay CAI_DAT.bat truoc (cai thu vien + Chromium).
  pause
)
