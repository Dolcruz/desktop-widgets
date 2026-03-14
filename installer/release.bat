@echo off
echo ============================================
echo  Creating GitHub Release
echo ============================================
echo.

cd /d "%~dp0.."

:: Check if dist\DesktopWidgets.exe exists
if not exist "dist\DesktopWidgets.exe" (
    echo ERROR: dist\DesktopWidgets.exe not found!
    echo Run installer\build.bat first.
    pause
    exit /b 1
)

:: Get version
set /p VERSION="Enter version (e.g. 1.0.0): "

echo.
echo Creating release v%VERSION%...
echo.

:: Create tag and release with gh CLI
gh release create "v%VERSION%" "dist\DesktopWidgets.exe" --title "Desktop Widgets v%VERSION%" --notes "## Desktop Widgets v%VERSION%%NL%%NL%Download **DesktopWidgets.exe** below — no Python required, just run it.%NL%%NL%### What's included%NL%- To Do widget%NL%- Health Tracker with habit streaks%NL%- Quick Notes%NL%- Weather (wttr.in)%NL%- Dark/Light theme with live toggle%NL%%NL%### Install%NL%Download and double-click `DesktopWidgets.exe`. That's it."

if errorlevel 1 (
    echo.
    echo ERROR: Release creation failed!
    echo Make sure gh is installed and authenticated.
    pause
    exit /b 1
)

echo.
echo Release v%VERSION% created!
echo.
pause
