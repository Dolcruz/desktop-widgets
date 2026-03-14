# Desktop Widgets

Minimalist desktop widgets for Windows that embed directly into your wallpaper. Built with Python and Tkinter using the Windows WorkerW API.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey)

## Features

- **To Do** – Simple todo list with add, check, delete. Completed items get sorted to the bottom.
- **Gesundheit (Health Tracker)** – Monthly calendar with daily habit tracking. Days are colored from red (0% done) → orange → green (100% done). Tracks streaks.
- **Notizen (Notes)** – Free-form scratchpad with auto-save.
- **Wetter (Weather)** – Current weather + 3-day forecast with ASCII art. Data from [wttr.in](https://wttr.in).
- **Settings** – Dark/light theme toggle and transparency slider. Changes apply to all widgets in real-time.

All widgets are borderless, transparent, and sit on the desktop behind all windows – always visible on your wallpaper.

## Setup

### Requirements

- Windows 10/11
- Python 3.8+ ([python.org](https://www.python.org/downloads/))
- No external packages needed – uses only Python standard library

### Run

```bash
pythonw desktop_widgets.pyw
```

Or double-click `desktop_widgets.pyw` in Explorer.

### Autostart (run on boot)

Create a file in your Windows Startup folder:

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a new file called `DesktopWidgets.vbs` with this content:

```vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\path\to\pythonw.exe"" ""C:\path\to\desktop_widgets.pyw""", 0, False
```

Replace the paths with your actual Python and script locations.

## Configuration

### Weather Location

Open `desktop_widgets.pyw` and change the `CITY` variable near the top:

```python
# Weather location – set your city here (empty string = auto-detect by IP)
CITY = "Schriesheim"
```

You can use any city name, e.g. `"Berlin"`, `"München"`, `"New York"`. Leave empty (`""`) to auto-detect your location by IP address.

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

All data is stored as simple files next to the script:

| File | Content |
|------|---------|
| `todos.json` | Your todo items |
| `health_data.json` | Habits and daily tracking data |
| `notes.txt` | Your notes |
| `widget_settings.json` | Theme and opacity settings |

## How It Works

The widgets use the Windows `WorkerW` API layer to embed themselves behind desktop icons but above the wallpaper. This means they're always visible but never get in the way of your work.

## License

MIT
