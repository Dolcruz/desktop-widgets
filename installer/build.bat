@echo off
echo ============================================
echo  Building Desktop Widgets installer
echo ============================================
echo.

cd /d "%~dp0.."

:: Step 1: Build .exe with PyInstaller
echo [1/2] Building .exe with PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
  --name "DesktopWidgets" ^
  --icon "installer\desktop_widgets.ico" ^
  --add-data "installer\desktop_widgets.ico;." ^
  desktop_widgets.pyw

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    echo Make sure PyInstaller is installed: pip install pyinstaller
    pause
    exit /b 1
)

echo.
echo [2/2] Build complete!
echo.
echo Output: dist\DesktopWidgets.exe
echo.

:: Step 2: Check if Inno Setup is available
where iscc >nul 2>&1
if errorlevel 1 (
    echo To create the installer .exe, install Inno Setup 6:
    echo   https://jrsoftware.org/isdl.php
    echo Then run:  iscc installer\setup.iss
) else (
    echo Building installer with Inno Setup...
    iscc installer\setup.iss
    echo.
    echo Installer created in: dist\DesktopWidgets-Setup.exe
)

echo.
pause
