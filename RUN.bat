@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 ( py inject_9router_gui.py ) else ( python inject_9router_gui.py )
if errorlevel 1 (
  echo.
  echo Co loi. Neu thieu thu vien, chay CAI_DAT.bat truoc.
  pause
)
