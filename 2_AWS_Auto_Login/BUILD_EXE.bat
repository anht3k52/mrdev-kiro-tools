@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Build .exe (Nuitka STANDALONE) - Tool 2 AWS Auto Login ===
echo (Can: Python 3.12 + pip install nuitka + da chay playwright install chromium)
if exist _build rmdir /s /q _build
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

rem Plugin playwright tu nhung Chromium (du chrome.exe/chrome.dll) vao trong dist.
%PY% -m nuitka --standalone --assume-yes-for-downloads --mingw64 --lto=no ^
  --windows-console-mode=disable --enable-plugin=tk-inter ^
  --enable-plugin=playwright --playwright-include-browser=chromium-1134 ^
  --include-package-data=customtkinter ^
  --include-package=playwright --include-package-data=playwright ^
  --include-package=openpyxl --include-package=et_xmlfile ^
  --output-dir=_build --output-filename=Tool2_AWS_Auto_Login.exe ^
  auto_login_gui.py

echo.
echo === Doi ten folder dist ===
if exist "_build\auto_login_gui.dist" ren "_build\auto_login_gui.dist" "Tool2_AWS_Auto_Login"
echo.
echo === XONG. Gui khach CA folder: _build\Tool2_AWS_Auto_Login ===
echo (Chromium da nhung san trong folder, khong can kem ms-playwright ben ngoai.)
pause