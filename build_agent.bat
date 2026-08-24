@echo off
REM ============================================================
REM  Build agent.exe with Nuitka + UPX (single file, no console)
REM  Run this on Windows. Requirements:
REM    1) pip install nuitka psutil
REM    2) upx.exe on PATH  ->  https://github.com/upx/upx/releases
REM  Nuitka will auto-download a C compiler (MinGW) on first run
REM  if no MSVC is found (needs internet).
REM ============================================================
setlocal

python -m nuitka ^
  --standalone ^
  --onefile ^
  --windows-disable-console ^
  --enable-plugin=tk-inter ^
  --include-module=psutil ^
  --assume-yes-for-downloads ^
  --output-dir=dist ^
  --output-filename=agent.exe ^
  --upx-binary=upx ^
  agent.py

if errorlevel 1 (
  echo.
  echo [Build failed] Make sure "nuitka", "psutil" and "upx" are available.
  echo Then run this script again.
  pause
  exit /b 1
)

echo.
echo [Build OK] dist\agent.exe
pause
endlocal
