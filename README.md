# Desktop Widgets

Minimalist desktop widgets for Windows that embed directly into your wallpaper. Built with Python and Tkinter using the Windows WorkerW API.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey)

## Features

- **To Do** – Simple todo list with add, check, delete. New tasks appear at the top, completed items stay at the bottom, and every change is archived in a text history file.
- **Health Tracker** – Monthly calendar with daily habit tracking. Days are colored from red (0% done) to green (100% done). Tracks streaks.
- **Notes** – Free-form scratchpad with auto-save.
- **Weather** – Current weather + 3-day forecast with ASCII art. Data from [wttr.in](https://wttr.in).
- **Settings** – Dark/light theme toggle and transparency slider. Changes apply to all widgets in real-time.

All widgets are borderless, transparent, and sit on the desktop behind all windows – always visible on your wallpaper.

## Install

### Option A: Windows Installer (recommended)

Download the latest **DesktopWidgets-Setup.exe** from [Releases](https://github.com/Dolcruz/desktop-widgets/releases) and run it. The installer will:

- Install Desktop Widgets to your system
- Optionally create a desktop shortcut
- Optionally set it to start automatically with Windows
- Include a clean uninstaller

No Python required. Just install and go.

### Option B: Run from source

Requirements: Windows 10/11, Python 3.8+ ([python.org](https://www.python.org/downloads/)). No external packages needed.

```bash
pythonw desktop_widgets.pyw
```

Or double-click `desktop_widgets.pyw` in Explorer.

#### Autostart from source

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a file called `DesktopWidgets.vbs`:

```vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\path\to\pythonw.exe"" ""C:\path\to\desktop_widgets.pyw""", 0, False
```

Replace the paths with your actual Python and script locations.

## Build the Installer Yourself

If you want to build from source:

```bash
pip install pyinstaller
installer\build.bat
```

This creates `dist\DesktopWidgets.exe` (standalone, no Python needed).

To also build the installer wizard, install [Inno Setup 6](https://jrsoftware.org/isdl.php) and run:

```bash
iscc installer\setup.iss
```

## Configuration

### Weather Location

Open `desktop_widgets.pyw` and change the `CITY` variable near the top:

```python
CITY = "Schriesheim"
```

You can use any city name, e.g. `"Berlin"`, `"New York"`. Leave empty (`""`) to auto-detect by IP.

### Default Habits

Edit the `DEFAULT_HABITS` list (only used on first run):

```python
DEFAULT_HABITS = [
    "7500 Schritte",
    "Genug Wasser trinken",
    "Krafttraining",
    "Joggen",
]
```

You can also add/remove habits directly in the widget UI.

### Theme

Click the theme toggle in the Settings widget to switch between dark and light mode. Use the slider to adjust transparency (20%–100%).

## Data Files

When running from source, data is stored next to the script. When running as an installed `.exe`, data is stored in `%APPDATA%\DesktopWidgets\`.

| File | Content |
|------|---------|
| `todos.json` | Your todo items |
| `todo_history.txt` | Permanent todo history with timestamps for adds, completions, reopenings, and deletions |
| `health_data.json` | Habits and daily tracking data |
| `notes.txt` | Your notes |
| `widget_settings.json` | Theme and opacity settings |

## How It Works

The widgets use the Windows `WorkerW` API layer to embed themselves behind desktop icons but above the wallpaper. This means they're always visible but never get in the way of your work.

## License

MIT
