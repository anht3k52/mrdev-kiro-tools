@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Build .exe (Nuitka, lam roi ma) - Tool 3 9router Injector ===
echo (Can: Python 3.12 + pip install nuitka. Lan dau tu tai MinGW ~vai phut.)
rem --- Ep dung Python 3.12 (MinGW64 KHONG chay duoc voi Python 3.13) ---
set PY=
py -3.12 --version >nul 2>nul && set PY=py -3.12
if not defined PY ( where python3.12 >nul 2>nul && set PY=python3.12 )
if not defined PY (
  echo LOI: Khong tim thay Python 3.12. MinGW64 khong build duoc voi Python 3.13.
  echo Cai Python 3.12 tu python.org roi chay lai file nay.
  pause
  exit /b 1
)
%PY% -m nuitka --onefile --assume-yes-for-downloads --mingw64 --lto=no ^
  --windows-console-mode=disable --enable-plugin=tk-inter ^
  --include-package-data=customtkinter --include-package-data=tkinterdnd2 ^
  --output-dir=_build --output-filename=Tool3_9router_Injector.exe ^
  inject_9router_gui.py
echo.
echo === Xong. File exe o: _build\Tool3_9router_Injector.exe ===
pause
