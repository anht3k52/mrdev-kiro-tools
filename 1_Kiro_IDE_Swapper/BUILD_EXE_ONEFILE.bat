@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Build 1 file .exe (onefile) — cham hon lan dau, can cho ~1 phut khi mo ===
echo Khuyen dung BUILD_EXE.bat (standalone, mo nhanh hon).
echo.

set PY=
set NUITKA_CC=
py -3.12 --version >nul 2>nul && set PY=py -3.12 && set NUITKA_CC=--mingw64
if not defined PY (
  py -3.13 --version >nul 2>nul && set PY=py -3.13 && set NUITKA_CC=--zig
)
if not defined PY (
  where python >nul 2>nul && set PY=python && set NUITKA_CC=--zig
)
if not defined PY (
  echo LOI: Khong tim thay Python.
  pause
  exit /b 1
)

%PY% -m pip install -q nuitka zstandard customtkinter psutil tkinterdnd2 2>nul

%PY% -m nuitka --onefile --onefile-cache-mode=cached --assume-yes-for-downloads %NUITKA_CC% --lto=no ^
  --windows-console-mode=disable --enable-plugin=tk-inter ^
  --include-package-data=customtkinter ^
  --output-dir=_build --output-filename=Tool1_Kiro_IDE_Swapper.exe ^
  swap_ide_gui.py

echo.
echo === Xong: _build\Tool1_Kiro_IDE_Swapper.exe ===
echo Lan dau mo co the cho 30-60 giay (giai nen). Lan sau nhanh hon.
pause
