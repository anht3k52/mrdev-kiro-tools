@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Build .exe (Nuitka ONEFILE - 1 file duy nhat) - Tool 2 AWS Auto Login ===
echo (Gom luon Chromium vao trong 1 file .exe. File se RAT TO ~300-400MB va
echo  khoi dong cham hon ban standalone. Can: Python 3.12 + pip install nuitka
echo  + da chay playwright install chromium)
echo.

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

rem --playwright-include-browser=chromium: plugin Nuitka tu nhung Chromium (du
rem ca chrome.exe/chrome.dll) vao .local-browsers. Luc chay app set
rem PLAYWRIGHT_BROWSERS_PATH=0 de dung cho do (da xu ly trong auto_login_gui.py).
%PY% -m nuitka --onefile --assume-yes-for-downloads --mingw64 --lto=no ^
  --windows-console-mode=disable --enable-plugin=tk-inter ^
  --enable-plugin=playwright --playwright-include-browser=chromium-1134 ^
  --include-package-data=customtkinter ^
  --include-package=playwright --include-package-data=playwright ^
  --include-package=openpyxl --include-package=et_xmlfile ^
  --output-dir=_build_onefile --output-filename=Tool2_AWS_Auto_Login.exe ^
  auto_login_gui.py

echo.
echo === XONG. File 1-file o: _build_onefile\Tool2_AWS_Auto_Login.exe ===
echo (Chi can gui DUY NHAT file .exe nay cho khach. Khong can kem folder nao.)
echo LUU Y: lan dau mo se cham (bung Chromium ra thu muc tam) - day la binh thuong.
pause