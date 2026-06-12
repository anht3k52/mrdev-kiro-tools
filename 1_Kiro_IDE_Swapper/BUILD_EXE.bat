@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Build .exe (Nuitka) - Tool 1 Kiro IDE Swapper ===
echo (Can: pip install nuitka zstandard customtkinter psutil tkinterdnd2)
echo.

rem --- Chon Python: 3.12=MinGW, 3.13+=Zig (khong can Visual Studio) ---
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
  echo LOI: Khong tim thay Python. Cai Python 3.12 hoac 3.13 tu python.org.
  pause
  exit /b 1
)

echo Dung: %PY%  (%NUITKA_CC%)
%PY% -m pip install -q nuitka zstandard customtkinter psutil tkinterdnd2 2>nul

rem Standalone = mo nhanh, on dinh (khuyen dung). Zip ca thu muc .dist gui nguoi dung.
%PY% -m nuitka --standalone --assume-yes-for-downloads %NUITKA_CC% --lto=no ^
  --windows-console-mode=disable --enable-plugin=tk-inter ^
  --include-package-data=customtkinter ^
  --output-dir=_build --output-filename=Tool1_Kiro_IDE_Swapper.exe ^
  swap_ide_gui.py
if errorlevel 1 (
  echo.
  echo BUILD THAT BAI. Thu cai Python 3.12 hoac chay lai (Zig tu tai lan dau ~vai phut).
  pause
  exit /b 1
)
echo.
echo === Xong. Chay file: ===
echo   _build\swap_ide_gui.dist\Tool1_Kiro_IDE_Swapper.exe
echo (Copy NGUYEN thu muc swap_ide_gui.dist — khong chi rieng file .exe)
pause
