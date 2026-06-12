@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 ( py swap_ide_gui.py ) else ( python swap_ide_gui.py )
if errorlevel 1 (
  echo.
  echo Co loi. Neu thieu thu vien, chay CAI_DAT.bat truoc.
  pause
)
