"""
Desktop Widgets – Todo, Health Tracker, Notes, Weather & Settings.
All-in-one desktop widget suite for Windows.
Embeds borderless transparent widgets directly into the desktop wallpaper layer.

Usage:
    pythonw desktop_widgets.pyw
"""

import tkinter as tk
import ctypes
import ctypes.wintypes
import json
import os
import sys
import calendar
import threading
import urllib.request
from datetime import datetime, date, timedelta


# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directory – uses %APPDATA%/DesktopWidgets when running as .exe,
# otherwise stores data next to the script (for development).
if getattr(sys, 'frozen', False):
    DATA_DIR = os.path.join(os.environ.get("APPDATA", SCRIPT_DIR), "DesktopWidgets")
else:
    DATA_DIR = SCRIPT_DIR
os.makedirs(DATA_DIR, exist_ok=True)

# Data files
SETTINGS_FILE = os.path.join(DATA_DIR, "widget_settings.json")
TODOS_FILE = os.path.join(DATA_DIR, "todos.json")
TODO_HISTORY_FILE = os.path.join(DATA_DIR, "todo_history.txt")
HEALTH_FILE = os.path.join(DATA_DIR, "health_data.json")
NOTES_FILE = os.path.join(DATA_DIR, "notes.txt")

# Weather location – set your city here (empty string = auto-detect by IP)
CITY = "Schriesheim"

# Font
FONT_FAMILY = "Segoe UI"
MONO_FONT = "Consolas"

# Layout
MARGIN_RIGHT = 40
MARGIN_TOP = 60
GAP = 20
TODO_W, TODO_H = 420, 600
HEALTH_W, HEALTH_H = 355, 660
NOTES_W, NOTES_H = 420, 280
WEATHER_W, WEATHER_H = 355, 340
SETTINGS_W, SETTINGS_H = 420, 185

# Default health habits (only used on first run)
DEFAULT_HABITS = [
    "7500 Schritte",
    "Genug Wasser trinken",
    "Krafttraining",
    "Joggen",
]


# ═══════════════════════════════════════════════════════════════════════
# Themes
# ═══════════════════════════════════════════════════════════════════════

THEMES = {
    "dark": {
        "BG_COLOR": "#0a0a0a",
        "FG_COLOR": "#d4d4d4",
        "ACCENT": "#ffffff",
        "DONE_COLOR": "#3a3a3a",
        "ENTRY_BG": "#151515",
        "CHECK_COLOR": "#9ece6a",
        "SEPARATOR": "#1a1a1a",
        "DANGER": "#f7768e",
    },
    "light": {
        "BG_COLOR": "#f2f2f2",
        "FG_COLOR": "#1a1a1a",
        "ACCENT": "#000000",
        "DONE_COLOR": "#aaaaaa",
        "ENTRY_BG": "#e6e6e6",
        "CHECK_COLOR": "#9ece6a",
        "SEPARATOR": "#dadada",
        "DANGER": "#f7768e",
    },
}

# Health calendar gradient: red -> orange -> green
C_LOW = (0xF7, 0x76, 0x8E)
C_MID = (0xE0, 0xAF, 0x68)
C_HIGH = (0x9E, 0xCE, 0x6A)

MONTHS_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]
DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WEEKDAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


# ═══════════════════════════════════════════════════════════════════════
# Windows API – embed widgets into the desktop
# ═══════════════════════════════════════════════════════════════════════

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
FindWindowExW = user32.FindWindowExW
SendMessageTimeoutW = user32.SendMessageTimeoutW
SetParent = user32.SetParent
SMTO_NORMAL = 0x0000
ENUMWINDOWSPROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
)


def find_worker_w():
    """Find the WorkerW window behind desktop icons."""
    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return None
    result = ctypes.wintypes.DWORD()
    SendMessageTimeoutW(
        progman, 0x052C, 0, 0, SMTO_NORMAL, 1000, ctypes.byref(result)
    )
    worker_w = [None]

    def _cb(hwnd, _):
        if FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None):
            worker_w[0] = FindWindowExW(0, hwnd, "WorkerW", None)
        return True

    EnumWindows(ENUMWINDOWSPROC(_cb), 0)
    return worker_w[0]


def embed_in_desktop(hwnd):
    """Embed a window into the desktop WorkerW layer."""
    worker = find_worker_w()
    if worker:
        SetParent(hwnd, worker)
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════
# Settings manager
# ═══════════════════════════════════════════════════════════════════════

class SettingsManager:
    def __init__(self):
        self._last_mtime = 0
        self._cached = None
        self.load()
        try:
            self._last_mtime = os.path.getmtime(SETTINGS_FILE)
        except OSError:
            pass

    def load(self):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                self._cached = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            self._cached = {"theme": "dark", "opacity": 0.7}
        return self._cached

    def save(self, s):
        tmp = SETTINGS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
        os.replace(tmp, SETTINGS_FILE)
        self._cached = s
        try:
            self._last_mtime = os.path.getmtime(SETTINGS_FILE)
        except OSError:
            pass

    def get_theme_name(self):
        return self._cached.get("theme", "dark")

    def get_theme(self):
        name = self.get_theme_name()
        return dict(THEMES.get(name, THEMES["dark"]))

    def get_opacity(self):
        return self._cached.get("opacity", 0.7)

    def start_watching(self, root, callback):
        """Poll settings file for changes every 300ms."""
        def _check():
            try:
                mt = os.path.getmtime(SETTINGS_FILE)
                if mt != self._last_mtime:
                    self._last_mtime = mt
                    self.load()
                    callback()
            except OSError:
                pass
            root.after(300, _check)
        root.after(300, _check)


# ═══════════════════════════════════════════════════════════════════════
# Theme helpers
# ═══════════════════════════════════════════════════════════════════════

def apply_theme(root, old_theme, new_theme, opacity):
    """Recursively remap all theme colors on the entire widget tree."""
    root.attributes("-alpha", opacity)
    color_map = {}
    for key in old_theme:
        old_v = old_theme[key].lower()
        new_v = new_theme[key]
        if old_v != new_v.lower():
            color_map[old_v] = new_v
    if color_map:
        _retheme(root, color_map)


def _retheme(widget, color_map):
    for child in widget.winfo_children():
        _retheme(child, color_map)
    for prop in (
        "bg", "fg", "insertbackground", "selectbackground",
        "selectforeground", "activebackground", "highlightbackground",
    ):
        try:
            val = str(widget.cget(prop)).lower()
            if val in color_map:
                widget.configure(**{prop: color_map[val]})
        except (tk.TclError, AttributeError):
            pass


def lerp_color(pct):
    """Red (0%) -> orange (50%) -> green (100%)."""
    pct = max(0.0, min(1.0, pct))
    if pct <= 0.5:
        t = pct * 2
        r1, g1, b1 = C_LOW
        r2, g2, b2 = C_MID
    else:
        t = (pct - 0.5) * 2
        r1, g1, b1 = C_MID
        r2, g2, b2 = C_HIGH
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def fg_for_bg(bg_hex):
    """Pick a readable foreground for a given background."""
    r = int(bg_hex[1:3], 16)
    g = int(bg_hex[3:5], 16)
    b = int(bg_hex[5:7], 16)
    return "#0a0a0a" if (0.299 * r + 0.587 * g + 0.114 * b) > 130 else "#e8e8e8"


# ═══════════════════════════════════════════════════════════════════════
# Base widget class
# ═══════════════════════════════════════════════════════════════════════

class BaseWidget:
    """Common setup for all desktop widgets."""

    def __init__(self, parent, settings, title, width, height, x, y):
        self.settings = settings
        self._current_theme = settings.get_theme()
        self._t = dict(self._current_theme)

        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.overrideredirect(True)
        self.win.configure(bg=self._t["BG_COLOR"])
        self.win.resizable(False, False)
        self.win.attributes("-alpha", settings.get_opacity())
        self.win.geometry(f"{width}x{height}+{x}+{y}")

    def embed(self):
        self.win.update_idletasks()
        self.win.update()
        hwnd = self.win.winfo_id()
        if not embed_in_desktop(hwnd):
            self.win.attributes("-topmost", False)
            self.win.lower()

    @property
    def t(self):
        return self._t

    def _base_apply_theme(self):
        old = self._current_theme
        new = self.settings.get_theme()
        opacity = self.settings.get_opacity()
        self._t = dict(new)
        apply_theme(self.win, old, new, opacity)
        self._current_theme = new


# ═══════════════════════════════════════════════════════════════════════
# Todo Widget
# ═══════════════════════════════════════════════════════════════════════

class TodoWidget(BaseWidget):
    def __init__(self, parent, settings):
        screen_w = parent.winfo_screenwidth()
        x = screen_w - TODO_W - MARGIN_RIGHT
        super().__init__(parent, settings, "Desktop Todos", TODO_W, TODO_H, x, MARGIN_TOP)
        self.todos = self._load()
        self._ensure_history_file()
        self._build_ui()
        self.embed()

    def _load(self):
        if os.path.exists(TODOS_FILE):
            try:
                with open(TODOS_FILE, "r", encoding="utf-8") as f:
                    todos = json.load(f)
                    if isinstance(todos, list):
                        todos.sort(key=lambda x: x.get("done", False))
                        return todos
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _save(self):
        with open(TODOS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.todos, f, ensure_ascii=False, indent=2)

    def _ensure_history_file(self):
        if os.path.exists(TODO_HISTORY_FILE):
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(TODO_HISTORY_FILE, "w", encoding="utf-8") as f:
                f.write("Desktop Todo History\n")
                f.write("====================\n\n")
                if self.todos:
                    f.write(f"[{timestamp}] SNAPSHOT | Imported existing todos\n")
                    for todo in self.todos:
                        text = " ".join(todo.get("text", "").splitlines()).strip()
                        if not text:
                            continue
                        status = "DONE" if todo.get("done", False) else "OPEN"
                        f.write(f"[{timestamp}] SNAPSHOT | {status} | {text}\n")
        except IOError:
            pass

    def _append_history(self, action, todo):
        text = " ".join(todo.get("text", "").splitlines()).strip()
        if not text:
            return

        status = "DONE" if todo.get("done", False) else "OPEN"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(TODO_HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {action} | {status} | {text}\n")
        except IOError:
            pass

    def _build_ui(self):
        t = self.t
        pad = 16

        title_frame = tk.Frame(self.win, bg=t["BG_COLOR"])
        title_frame.pack(fill="x", padx=pad, pady=(16, 6))

        tk.Label(
            title_frame, text="To Do", fg=t["ACCENT"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 18, "bold"), anchor="w",
        ).pack(side="left")

        self.count_lbl = tk.Label(
            title_frame, text="", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 11), anchor="e",
        )
        self.count_lbl.pack(side="right", padx=(0, 2))

        tk.Frame(self.win, bg=t["SEPARATOR"], height=1).pack(fill="x", padx=pad, pady=(0, 8))

        self.list_container = tk.Frame(self.win, bg=t["BG_COLOR"])
        self.list_container.pack(fill="both", expand=True, padx=pad)

        self.canvas = tk.Canvas(
            self.list_container, bg=t["BG_COLOR"], highlightthickness=0,
            width=TODO_W - 36,
        )
        self.list_frame = tk.Frame(self.canvas, bg=t["BG_COLOR"])
        self.list_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_scroll))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        tk.Frame(self.win, bg=t["SEPARATOR"], height=1).pack(fill="x", padx=pad, pady=(8, 0))

        input_frame = tk.Frame(self.win, bg=t["BG_COLOR"])
        input_frame.pack(fill="x", padx=pad, pady=(10, 14))

        self.entry = tk.Entry(
            input_frame, bg=t["ENTRY_BG"], fg=t["FG_COLOR"], insertbackground=t["FG_COLOR"],
            font=(FONT_FAMILY, 14), relief="flat", bd=8,
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self._add)

        add_btn = tk.Label(
            input_frame, text=" + ", fg=t["BG_COLOR"], bg=t["ACCENT"],
            font=(FONT_FAMILY, 14, "bold"), cursor="hand2", padx=8,
        )
        add_btn.pack(side="right", padx=(6, 0))
        add_btn.bind("<Button-1>", self._add)

        self._render()

    def _on_scroll(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _render(self):
        t = self.t
        for w in self.list_frame.winfo_children():
            w.destroy()

        open_count = sum(1 for x in self.todos if not x.get("done", False))
        self.count_lbl.config(text=f"{open_count} offen" if open_count else "")

        for i, todo in enumerate(self.todos):
            row = tk.Frame(self.list_frame, bg=t["BG_COLOR"])
            row.pack(fill="x", pady=4)

            done = todo.get("done", False)
            chk = tk.Label(
                row, text="✓" if done else "○",
                fg=t["CHECK_COLOR"] if done else t["DONE_COLOR"],
                bg=t["BG_COLOR"], font=(FONT_FAMILY, 14), cursor="hand2", width=2,
            )
            chk.pack(side="left")
            chk.bind("<Button-1>", lambda e, idx=i: self._toggle(idx))

            txt_fg = t["DONE_COLOR"] if done else t["FG_COLOR"]
            txt_font = (FONT_FAMILY, 14, "overstrike") if done else (FONT_FAMILY, 14)
            lbl = tk.Label(
                row, text=todo["text"], fg=txt_fg, bg=t["BG_COLOR"],
                font=txt_font, anchor="w", wraplength=TODO_W - 110,
            )
            lbl.pack(side="left", fill="x", expand=True)

            x_btn = tk.Label(
                row, text="×", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
                font=(FONT_FAMILY, 14), cursor="hand2",
            )
            x_btn.pack(side="right", padx=(4, 0))
            x_btn.bind("<Button-1>", lambda e, idx=i: self._delete(idx))
            x_btn.bind("<Enter>", lambda e, b=x_btn: b.config(fg=t["DANGER"]))
            x_btn.bind("<Leave>", lambda e, b=x_btn: b.config(fg=t["DONE_COLOR"]))

        self.win.update_idletasks()
        max_h = min(len(self.todos) * 34 + 10, 450)
        self.canvas.configure(height=max(max_h, 40))

    def _add(self, _e=None):
        text = self.entry.get().strip()
        if not text:
            return
        todo = {"text": text, "done": False}
        self.todos.insert(0, todo)
        self.todos.sort(key=lambda x: x.get("done", False))
        self._append_history("ADDED", todo)
        self._save()
        self.entry.delete(0, "end")
        self._render()

    def _toggle(self, idx):
        todo = self.todos[idx]
        todo["done"] = not todo["done"]
        action = "COMPLETED" if todo["done"] else "REOPENED"
        self.todos.sort(key=lambda x: x.get("done", False))
        self._append_history(action, todo)
        self._save()
        self._render()

    def _delete(self, idx):
        todo = self.todos.pop(idx)
        self._append_history("DELETED", todo)
        self._save()
        self._render()

    def apply_theme(self):
        self._base_apply_theme()
        self._render()


# ═══════════════════════════════════════════════════════════════════════
# Health Tracker Widget
# ═══════════════════════════════════════════════════════════════════════

class HealthWidget(BaseWidget):
    def __init__(self, parent, settings):
        screen_w = parent.winfo_screenwidth()
        x = screen_w - TODO_W - MARGIN_RIGHT - GAP - HEALTH_W
        super().__init__(parent, settings, "Desktop Health", HEALTH_W, HEALTH_H, x, MARGIN_TOP)

        self.data = self._load()
        self.today = date.today()
        self.view_year = self.today.year
        self.view_month = self.today.month
        self.selected_date = self.today
        self._placeholder_on = True
        self._build_ui()
        self.embed()
        self._schedule_midnight()

    def _load(self):
        if os.path.exists(HEALTH_FILE):
            try:
                with open(HEALTH_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "habits" in data and "days" in data:
                        return data
            except (json.JSONDecodeError, IOError):
                pass
        return {"habits": list(DEFAULT_HABITS), "days": {}}

    def _save(self):
        with open(HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _schedule_midnight(self):
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ms = int((midnight - now).total_seconds() * 1000) + 500
        self.win.after(ms, self._on_midnight)

    def _on_midnight(self):
        self.today = date.today()
        self.selected_date = self.today
        self.view_year = self.today.year
        self.view_month = self.today.month
        self._render_calendar()
        self._render_habits()
        self._schedule_midnight()

    def _build_ui(self):
        t = self.t
        pad = 16

        tf = tk.Frame(self.win, bg=t["BG_COLOR"])
        tf.pack(fill="x", padx=pad, pady=(16, 6))
        tk.Label(
            tf, text="Gesundheit", fg=t["ACCENT"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 18, "bold"), anchor="w",
        ).pack(side="left")

        self.streak_lbl = tk.Label(
            tf, text="", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 11), anchor="e",
        )
        self.streak_lbl.pack(side="right", padx=(0, 2))

        tk.Frame(self.win, bg=t["SEPARATOR"], height=1).pack(fill="x", padx=pad, pady=(0, 8))

        # Month nav
        nf = tk.Frame(self.win, bg=t["BG_COLOR"])
        nf.pack(fill="x", padx=pad, pady=(2, 4))

        prev_btn = tk.Label(
            nf, text="‹", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 18), cursor="hand2",
        )
        prev_btn.pack(side="left", padx=(0, 8))
        prev_btn.bind("<Button-1>", lambda e: self._nav_month(-1))
        prev_btn.bind("<Enter>", lambda e: prev_btn.config(fg=t["ACCENT"]))
        prev_btn.bind("<Leave>", lambda e: prev_btn.config(fg=t["DONE_COLOR"]))

        self.month_lbl = tk.Label(
            nf, text="", fg=t["FG_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 13, "bold"),
        )
        self.month_lbl.pack(side="left", expand=True)

        next_btn = tk.Label(
            nf, text="›", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 18), cursor="hand2",
        )
        next_btn.pack(side="right", padx=(8, 0))
        next_btn.bind("<Button-1>", lambda e: self._nav_month(1))
        next_btn.bind("<Enter>", lambda e: next_btn.config(fg=t["ACCENT"]))
        next_btn.bind("<Leave>", lambda e: next_btn.config(fg=t["DONE_COLOR"]))

        # Day headers
        dh = tk.Frame(self.win, bg=t["BG_COLOR"])
        dh.pack(fill="x", padx=pad, pady=(6, 3))
        for name in DAYS_DE:
            tk.Label(
                dh, text=name, fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
                font=(FONT_FAMILY, 10), width=4,
            ).pack(side="left", expand=True)

        # Calendar grid
        self.cal_frame = tk.Frame(self.win, bg=t["BG_COLOR"])
        self.cal_frame.pack(fill="x", padx=10, pady=(0, 8))

        tk.Frame(self.win, bg=t["SEPARATOR"], height=1).pack(fill="x", padx=pad, pady=(0, 8))

        # Selected day header
        sh = tk.Frame(self.win, bg=t["BG_COLOR"])
        sh.pack(fill="x", padx=pad, pady=(0, 4))

        self.sel_day_lbl = tk.Label(
            sh, text="", fg=t["FG_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 13, "bold"), anchor="w",
        )
        self.sel_day_lbl.pack(side="left")

        self.progress_lbl = tk.Label(
            sh, text="", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 12),
        )
        self.progress_lbl.pack(side="right")

        # Habits
        self.habits_frame = tk.Frame(self.win, bg=t["BG_COLOR"])
        self.habits_frame.pack(fill="both", expand=True, padx=pad, pady=(0, 4))

        tk.Frame(self.win, bg=t["SEPARATOR"], height=1).pack(fill="x", padx=pad, pady=(4, 0))

        # Input
        inf = tk.Frame(self.win, bg=t["BG_COLOR"])
        inf.pack(fill="x", padx=pad, pady=(10, 14))

        self.entry = tk.Entry(
            inf, bg=t["ENTRY_BG"], fg=t["FG_COLOR"], insertbackground=t["FG_COLOR"],
            font=(FONT_FAMILY, 13), relief="flat", bd=8,
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self._add_habit)
        self._show_placeholder()
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

        add_btn = tk.Label(
            inf, text=" + ", fg=t["BG_COLOR"], bg=t["ACCENT"],
            font=(FONT_FAMILY, 13, "bold"), cursor="hand2", padx=8,
        )
        add_btn.pack(side="right", padx=(6, 0))
        add_btn.bind("<Button-1>", self._add_habit)

        self._render_calendar()
        self._render_habits()

    def _show_placeholder(self):
        self.entry.delete(0, "end")
        self.entry.insert(0, "Neues Ziel...")
        self.entry.config(fg=self.t["DONE_COLOR"])
        self._placeholder_on = True

    def _on_focus_in(self, _e=None):
        if self._placeholder_on:
            self.entry.delete(0, "end")
            self.entry.config(fg=self.t["FG_COLOR"])
            self._placeholder_on = False

    def _on_focus_out(self, _e=None):
        if not self.entry.get().strip():
            self._show_placeholder()

    def _nav_month(self, delta):
        m = self.view_month + delta
        if m > 12:
            self.view_month, self.view_year = 1, self.view_year + 1
        elif m < 1:
            self.view_month, self.view_year = 12, self.view_year - 1
        else:
            self.view_month = m
        self._render_calendar()

    def _calc_streak(self):
        habits = self.data.get("habits", [])
        if not habits:
            return 0
        streak = 0
        d = self.today
        while True:
            day_data = self.data.get("days", {}).get(d.isoformat(), {})
            done = sum(1 for h in habits if day_data.get(h, False))
            if done == len(habits):
                streak += 1
                d -= timedelta(days=1)
            elif d == self.today:
                d -= timedelta(days=1)
                continue
            else:
                break
        return streak

    def _completion(self, d):
        habits = self.data.get("habits", [])
        if not habits:
            return 0.0, 0, 0
        day_data = self.data.get("days", {}).get(d.isoformat(), {})
        done = sum(1 for h in habits if day_data.get(h, False))
        return done / len(habits), done, len(habits)

    def _render_calendar(self):
        t = self.t
        for w in self.cal_frame.winfo_children():
            w.destroy()

        self.month_lbl.config(text=f"{MONTHS_DE[self.view_month]} {self.view_year}")

        streak = self._calc_streak()
        self.streak_lbl.config(text=f"{streak} Tage Streak" if streak > 0 else "")

        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.view_year, self.view_month)

        for week in weeks:
            row = tk.Frame(self.cal_frame, bg=t["BG_COLOR"])
            row.pack(fill="x", pady=1)

            for day_num in week:
                outer = tk.Frame(row, bg=t["BG_COLOR"])
                outer.pack(side="left", expand=True, padx=1, pady=1)

                if day_num == 0:
                    tk.Label(outer, text="", bg=t["BG_COLOR"], width=4, height=1,
                             font=(FONT_FAMILY, 11)).pack()
                    continue

                d = date(self.view_year, self.view_month, day_num)
                is_today = d == self.today
                is_sel = d == self.selected_date
                is_future = d > self.today

                if is_future:
                    cell_bg, cell_fg = t["ENTRY_BG"], t["DONE_COLOR"]
                elif is_today or d.isoformat() in self.data.get("days", {}):
                    pct = self._completion(d)[0]
                    cell_bg = lerp_color(pct)
                    cell_fg = fg_for_bg(cell_bg)
                else:
                    cell_bg, cell_fg = t["ENTRY_BG"], t["DONE_COLOR"]

                border_px = 0
                if is_sel:
                    outer.config(bg=t["ACCENT"])
                    border_px = 2
                elif is_today:
                    outer.config(bg="#555555")
                    border_px = 1

                font_style = "bold" if (is_sel or is_today) else "normal"
                lbl = tk.Label(
                    outer, text=str(day_num), bg=cell_bg, fg=cell_fg,
                    font=(FONT_FAMILY, 11, font_style),
                    width=3, height=1, cursor="hand2",
                )
                lbl.pack(padx=border_px, pady=border_px)
                lbl.bind("<Button-1>", lambda _e, dd=d: self._select_day(dd))

    def _select_day(self, d):
        self.selected_date = d
        self._render_calendar()
        self._render_habits()

    def _render_habits(self):
        t = self.t
        for w in self.habits_frame.winfo_children():
            w.destroy()

        d = self.selected_date
        is_future = d > self.today
        habits = self.data.get("habits", [])
        day_data = self.data.get("days", {}).get(d.isoformat(), {})

        self.sel_day_lbl.config(text=f"{d.day}. {MONTHS_DE[d.month]}")

        pct, done, total = self._completion(d)
        if total:
            self.progress_lbl.config(text=f"{done}/{total}", fg=lerp_color(pct))
        else:
            self.progress_lbl.config(text="")

        for habit in habits:
            checked = day_data.get(habit, False)
            hf = tk.Frame(self.habits_frame, bg=t["BG_COLOR"])
            hf.pack(fill="x", pady=4)

            chk = tk.Label(
                hf, text="✓" if checked else "○",
                fg=t["CHECK_COLOR"] if checked else t["DONE_COLOR"],
                bg=t["BG_COLOR"], font=(FONT_FAMILY, 13),
                cursor="hand2" if not is_future else "", width=2,
            )
            chk.pack(side="left")
            if not is_future:
                chk.bind("<Button-1>", lambda _e, h=habit: self._toggle(h))

            txt_fg = t["DONE_COLOR"] if checked else t["FG_COLOR"]
            txt_font = (FONT_FAMILY, 13, "overstrike") if checked else (FONT_FAMILY, 13)
            lbl = tk.Label(
                hf, text=habit, fg=txt_fg, bg=t["BG_COLOR"],
                font=txt_font, anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True)
            if not is_future:
                lbl.bind("<Button-1>", lambda _e, h=habit: self._toggle(h))

            x_btn = tk.Label(
                hf, text="×", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
                font=(FONT_FAMILY, 13), cursor="hand2",
            )
            x_btn.pack(side="right", padx=(4, 0))
            x_btn.bind("<Button-1>", lambda _e, h=habit: self._delete_habit(h))
            x_btn.bind("<Enter>", lambda _e, b=x_btn: b.config(fg=t["DANGER"]))
            x_btn.bind("<Leave>", lambda _e, b=x_btn: b.config(fg=t["DONE_COLOR"]))

    def _toggle(self, habit):
        key = self.selected_date.isoformat()
        self.data.setdefault("days", {}).setdefault(key, {})
        self.data["days"][key][habit] = not self.data["days"][key].get(habit, False)
        self._save()
        self._render_calendar()
        self._render_habits()

    def _add_habit(self, _e=None):
        text = self.entry.get().strip()
        if not text or text == "Neues Ziel...":
            return
        if text not in self.data["habits"]:
            self.data["habits"].append(text)
            self._save()
        self.entry.delete(0, "end")
        self._show_placeholder()
        self._render_calendar()
        self._render_habits()

    def _delete_habit(self, habit):
        if habit in self.data["habits"]:
            self.data["habits"].remove(habit)
            for dd in self.data.get("days", {}).values():
                dd.pop(habit, None)
            self._save()
            self._render_calendar()
            self._render_habits()

    def apply_theme(self):
        self._base_apply_theme()
        self._render_calendar()
        self._render_habits()


# ═══════════════════════════════════════════════════════════════════════
# Notes Widget
# ═══════════════════════════════════════════════════════════════════════

class NotesWidget(BaseWidget):
    def __init__(self, parent, settings):
        screen_w = parent.winfo_screenwidth()
        x = screen_w - NOTES_W - MARGIN_RIGHT
        y = MARGIN_TOP + TODO_H + GAP
        super().__init__(parent, settings, "Desktop Notes", NOTES_W, NOTES_H, x, y)
        self._save_job = None
        self._build_ui()
        self.embed()

    def _build_ui(self):
        t = self.t
        pad = 16

        tf = tk.Frame(self.win, bg=t["BG_COLOR"])
        tf.pack(fill="x", padx=pad, pady=(14, 4))

        tk.Label(
            tf, text="Notizen", fg=t["ACCENT"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 18, "bold"), anchor="w",
        ).pack(side="left")

        self.char_lbl = tk.Label(
            tf, text="", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 10), anchor="e",
        )
        self.char_lbl.pack(side="right")

        tk.Frame(self.win, bg=t["SEPARATOR"], height=1).pack(fill="x", padx=pad, pady=(0, 6))

        text_frame = tk.Frame(self.win, bg=t["BG_COLOR"])
        text_frame.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        self.text = tk.Text(
            text_frame,
            bg=t["ENTRY_BG"], fg=t["FG_COLOR"], insertbackground=t["FG_COLOR"],
            font=(FONT_FAMILY, 13), relief="flat", bd=10, wrap="word",
            highlightthickness=0,
            selectbackground=t["DONE_COLOR"], selectforeground=t["FG_COLOR"],
        )
        self.text.pack(fill="both", expand=True)

        # Load existing notes
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                if content:
                    self.text.insert("1.0", content)
            except IOError:
                pass

        self._update_count()
        self.text.bind("<KeyRelease>", self._on_change)
        self.text.bind("<Enter>", lambda e: self.text.bind_all("<MouseWheel>", self._on_scroll))
        self.text.bind("<Leave>", lambda e: self.text.unbind_all("<MouseWheel>"))

    def _on_scroll(self, event):
        self.text.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_change(self, _e=None):
        self._update_count()
        if self._save_job:
            self.win.after_cancel(self._save_job)
        self._save_job = self.win.after(800, self._do_save)

    def _do_save(self):
        content = self.text.get("1.0", "end-1c")
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        self._save_job = None

    def _update_count(self):
        content = self.text.get("1.0", "end-1c")
        lines = content.count("\n") + 1 if content else 0
        self.char_lbl.config(text=f"{lines} Zeilen" if lines else "")

    def apply_theme(self):
        self._base_apply_theme()


# ═══════════════════════════════════════════════════════════════════════
# Weather Widget
# ═══════════════════════════════════════════════════════════════════════

ASCII_ART = {
    "sunny": (
        "       \\   |   /      \n"
        "         .--.         \n"
        "      --( oo )--      \n"
        "         `--'         \n"
        "       /   |   \\      "
    ),
    "partly_cloudy": (
        "    \\  |  /           \n"
        "      .--.    .--.    \n"
        "   --( oo ).-(    ).  \n"
        "      `--(___.__)__) \n"
        "                      "
    ),
    "cloudy": (
        "                      \n"
        "        .--.          \n"
        "     .-(    ).        \n"
        "    (___.__)__)       \n"
        "                      "
    ),
    "overcast": (
        "                      \n"
        "      .--.  .--.     \n"
        "   .-(    )(    ).   \n"
        "  (___.__)(_.__)__)  \n"
        "                      "
    ),
    "rain": (
        "        .--.          \n"
        "     .-(    ).        \n"
        "    (___.__)__)       \n"
        "     ' ' ' ' '       \n"
        "    ' ' ' ' '        "
    ),
    "heavy_rain": (
        "        .--.          \n"
        "     .-(    ).        \n"
        "    (___.__)__)       \n"
        "    /|/|/|/|/|       \n"
        "   /|/|/|/|/|        "
    ),
    "thunder": (
        "        .--.          \n"
        "     .-(    ).        \n"
        "    (___.__)__)       \n"
        "      _/  _/         \n"
        "     /   /            "
    ),
    "snow": (
        "        .--.          \n"
        "     .-(    ).        \n"
        "    (___.__)__)       \n"
        "     *  .  *  .      \n"
        "    .  *  .  *       "
    ),
    "fog": (
        "                      \n"
        "    _ - _ - _ - _     \n"
        "     - _ - _ - _      \n"
        "    _ - _ - _ - _     \n"
        "     - _ - _ - _      "
    ),
    "loading": (
        "                      \n"
        "                      \n"
        "       Lade...        \n"
        "                      \n"
        "                      "
    ),
}

CONDITION_DE = {
    113: "Sonnig", 116: "Teilw. bewölkt", 119: "Bewölkt",
    122: "Bedeckt", 143: "Neblig", 176: "Leichter Regen",
    200: "Gewitter", 227: "Leichter Schnee", 230: "Schneefall",
    248: "Nebel", 260: "Eisnebel", 263: "Nieselregen",
    266: "Nieselregen", 281: "Eisregen", 284: "Eisregen",
    293: "Leichter Regen", 296: "Regen", 299: "Starker Regen",
    302: "Starker Regen", 305: "Starkregen", 308: "Starkregen",
    323: "Leichter Schnee", 326: "Schnee", 329: "Schneefall",
    332: "Starker Schnee", 335: "Schneesturm", 338: "Schneesturm",
    353: "Schauer", 356: "Starke Schauer", 359: "Starke Schauer",
    368: "Schneeschauer", 371: "Schneeschauer",
    374: "Hagelschauer", 377: "Hagelschauer",
    386: "Gewitter", 389: "Starkes Gewitter",
    392: "Schneegewitter", 395: "Schneegewitter",
}


def _get_art(code):
    code = int(code)
    if code == 113:
        return ASCII_ART["sunny"]
    if code == 116:
        return ASCII_ART["partly_cloudy"]
    if code in (119,):
        return ASCII_ART["cloudy"]
    if code in (122,):
        return ASCII_ART["overcast"]
    if code in (200, 386, 389):
        return ASCII_ART["thunder"]
    if code in (227, 230, 323, 326, 329, 332, 335, 338, 368, 371, 374, 377, 392, 395):
        return ASCII_ART["snow"]
    if code in (143, 248, 260):
        return ASCII_ART["fog"]
    if code in (299, 302, 305, 308, 359, 362, 365):
        return ASCII_ART["heavy_rain"]
    if code in (176, 263, 266, 281, 284, 293, 296, 353, 356):
        return ASCII_ART["rain"]
    return ASCII_ART["cloudy"]


class WeatherWidget(BaseWidget):
    REFRESH_MS = 30 * 60 * 1000  # 30 minutes

    def __init__(self, parent, settings):
        screen_w = parent.winfo_screenwidth()
        x = screen_w - TODO_W - MARGIN_RIGHT - GAP - HEALTH_W
        y = MARGIN_TOP + HEALTH_H + GAP
        super().__init__(parent, settings, "Desktop Weather", WEATHER_W, WEATHER_H, x, y)
        self._weather_data = None
        self._build_ui()
        self.embed()
        self._fetch_async()

    def _build_ui(self):
        t = self.t
        pad = 16

        tf = tk.Frame(self.win, bg=t["BG_COLOR"])
        tf.pack(fill="x", padx=pad, pady=(14, 0))

        tk.Label(
            tf, text="Wetter", fg=t["ACCENT"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 18, "bold"), anchor="w",
        ).pack(side="left")

        self.updated_lbl = tk.Label(
            tf, text="", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 10), anchor="e",
        )
        self.updated_lbl.pack(side="right")

        self.location_lbl = tk.Label(
            self.win, text="", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 10), anchor="w",
        )
        self.location_lbl.pack(fill="x", padx=pad, pady=(0, 4))

        tk.Frame(self.win, bg=t["SEPARATOR"], height=1).pack(fill="x", padx=pad, pady=(0, 6))

        main = tk.Frame(self.win, bg=t["BG_COLOR"])
        main.pack(fill="x", padx=pad, pady=(4, 0))

        self.ascii_lbl = tk.Label(
            main, text=ASCII_ART["loading"], fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(MONO_FONT, 11), justify="left", anchor="nw",
        )
        self.ascii_lbl.pack(side="left", anchor="nw")

        info = tk.Frame(main, bg=t["BG_COLOR"])
        info.pack(side="right", fill="y", anchor="ne", padx=(8, 0))

        self.temp_lbl = tk.Label(
            info, text="--°", fg=t["ACCENT"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 28, "bold"), anchor="e",
        )
        self.temp_lbl.pack(anchor="e")

        self.feels_lbl = tk.Label(
            info, text="", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 10), anchor="e",
        )
        self.feels_lbl.pack(anchor="e")

        self.cond_lbl = tk.Label(
            info, text="", fg=t["FG_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 11), anchor="e",
        )
        self.cond_lbl.pack(anchor="e", pady=(4, 0))

        self.detail_lbl = tk.Label(
            info, text="", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 10), anchor="e", justify="right",
        )
        self.detail_lbl.pack(anchor="e", pady=(2, 0))

        tk.Frame(self.win, bg=t["SEPARATOR"], height=1).pack(fill="x", padx=pad, pady=(10, 8))

        self.forecast_frame = tk.Frame(self.win, bg=t["BG_COLOR"])
        self.forecast_frame.pack(fill="x", padx=pad, pady=(0, 8))

        self.error_lbl = tk.Label(
            self.win, text="", fg="#555555", bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 10),
        )
        self.error_lbl.pack(fill="x", padx=pad)

    def _fetch_async(self):
        def _do():
            try:
                url = f"https://wttr.in/{CITY}?format=j1&lang=de"
                req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
                self.win.after(0, lambda: self._on_data(data))
            except Exception:
                self.win.after(0, self._on_error)

        threading.Thread(target=_do, daemon=True).start()
        self.win.after(self.REFRESH_MS, self._fetch_async)

    def _on_data(self, data):
        t = self.t
        self._weather_data = data
        self.error_lbl.config(text="")
        self.updated_lbl.config(text=f"↻ {datetime.now().strftime('%H:%M')}")

        try:
            area = data["nearest_area"][0]
            city = area["areaName"][0]["value"]
            country = area["country"][0]["value"]
            self.location_lbl.config(text=f"{city}, {country}")
        except (KeyError, IndexError):
            pass

        cur = data["current_condition"][0]
        code = int(cur.get("weatherCode", 119))

        self.ascii_lbl.config(text=_get_art(code), fg=t["FG_COLOR"])
        temp = cur.get("temp_C", "--")
        self.temp_lbl.config(text=f"{temp}°")
        feels = cur.get("FeelsLikeC", "")
        self.feels_lbl.config(text=f"Gefühlt: {feels}°" if feels and feels != temp else "")

        cond = CONDITION_DE.get(code, cur.get("weatherDesc", [{}])[0].get("value", ""))
        self.cond_lbl.config(text=cond)

        humidity = cur.get("humidity", "")
        wind = cur.get("windspeedKmph", "")
        details = []
        if humidity:
            details.append(f"Feuchte: {humidity}%")
        if wind:
            details.append(f"Wind: {wind} km/h")
        self.detail_lbl.config(text="\n".join(details))

        self._render_forecast(data.get("weather", []))

    def _on_error(self):
        self.error_lbl.config(text="Kein Internet")
        self.updated_lbl.config(text="offline")

    def _render_forecast(self, days):
        t = self.t
        for w in self.forecast_frame.winfo_children():
            w.destroy()

        for i, day in enumerate(days[:3]):
            date_str = day.get("date", "")
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                weekday = WEEKDAYS_DE[dt.weekday()]
                if dt.date() == datetime.now().date():
                    weekday = "Heute"
            except (ValueError, IndexError):
                weekday = date_str

            max_t = day.get("maxtempC", "--")
            min_t = day.get("mintempC", "--")
            hourly = day.get("hourly", [])
            noon = hourly[len(hourly) // 2] if hourly else {}
            code = int(noon.get("weatherCode", 119))
            cond = CONDITION_DE.get(code, "")

            col = tk.Frame(self.forecast_frame, bg=t["BG_COLOR"])
            col.pack(side="left", expand=True, fill="x")

            tk.Label(
                col, text=weekday, fg=t["FG_COLOR"] if i == 0 else t["DONE_COLOR"],
                bg=t["BG_COLOR"], font=(FONT_FAMILY, 10, "bold"),
            ).pack()
            tk.Label(
                col, text=f"{max_t}° / {min_t}°", fg=t["FG_COLOR"], bg=t["BG_COLOR"],
                font=(FONT_FAMILY, 11),
            ).pack()
            tk.Label(
                col, text=cond, fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
                font=(FONT_FAMILY, 9),
            ).pack()

            if i < 2:
                tk.Frame(
                    self.forecast_frame, bg=t["SEPARATOR"], width=1,
                ).pack(side="left", fill="y", padx=4, pady=4)

    def apply_theme(self):
        self._base_apply_theme()
        if self._weather_data:
            self._render_forecast(self._weather_data.get("weather", []))


# ═══════════════════════════════════════════════════════════════════════
# Settings Widget
# ═══════════════════════════════════════════════════════════════════════

class OpacitySlider(tk.Canvas):
    """Custom minimal slider on a Canvas."""

    def __init__(self, parent, value=0.7, on_change=None, accent="#ffffff",
                 separator="#1a1a1a", **kw):
        super().__init__(parent, height=28, highlightthickness=0, **kw)
        self._value = value
        self._on_change = on_change
        self._accent = accent
        self._separator = separator
        self._min = 0.2
        self._max = 1.0
        self.bind("<Configure>", self._draw)
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._click)

    def _v2x(self, v):
        pad = 12
        return pad + (v - self._min) / (self._max - self._min) * (self.winfo_width() - 2 * pad)

    def _x2v(self, x):
        pad = 12
        w = self.winfo_width() - 2 * pad
        v = self._min + (x - pad) / max(w, 1) * (self._max - self._min)
        return max(self._min, min(self._max, round(v, 2)))

    def _draw(self, _e=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        pad, cy = 12, h // 2
        tx = self._v2x(self._value)
        self.create_line(pad, cy, w - pad, cy, fill=self._separator, width=2)
        self.create_line(pad, cy, tx, cy, fill=self._accent, width=2)
        r = 7
        self.create_oval(tx - r, cy - r, tx + r, cy + r, fill=self._accent, outline="")

    def _click(self, event):
        self._value = self._x2v(event.x)
        self._draw()
        if self._on_change:
            self._on_change(self._value)

    def set_value(self, v):
        self._value = v
        self._draw()

    def set_colors(self, accent, separator):
        self._accent = accent
        self._separator = separator
        self._draw()

    @property
    def value(self):
        return self._value


class SettingsWidget(BaseWidget):
    def __init__(self, parent, settings, all_widgets=None):
        screen_w = parent.winfo_screenwidth()
        x = screen_w - SETTINGS_W - MARGIN_RIGHT
        y = MARGIN_TOP + TODO_H + GAP + NOTES_H + GAP
        super().__init__(parent, settings, "Desktop Settings", SETTINGS_W, SETTINGS_H, x, y)
        self._all_widgets = all_widgets or []
        self._build_ui()
        self.embed()

    def _build_ui(self):
        t = self.t
        pad = 16

        tf = tk.Frame(self.win, bg=t["BG_COLOR"])
        tf.pack(fill="x", padx=pad, pady=(14, 4))
        tk.Label(
            tf, text="Settings", fg=t["ACCENT"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 18, "bold"), anchor="w",
        ).pack(side="left")

        tk.Frame(self.win, bg=t["SEPARATOR"], height=1).pack(fill="x", padx=pad, pady=(0, 10))

        # Theme toggle
        trow = tk.Frame(self.win, bg=t["BG_COLOR"])
        trow.pack(fill="x", padx=pad, pady=(0, 14))

        is_dark = self.settings.get_theme_name() == "dark"
        icon = "◑" if is_dark else "○"
        label = "Dunkel" if is_dark else "Hell"

        self.toggle_lbl = tk.Label(
            trow, text=f"{icon}  {label}", fg=t["FG_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 13), cursor="hand2",
        )
        self.toggle_lbl.pack(side="left")
        self.toggle_lbl.bind("<Button-1>", self._toggle_theme)

        # Opacity slider
        hdr = tk.Frame(self.win, bg=t["BG_COLOR"])
        hdr.pack(fill="x", padx=pad)

        tk.Label(
            hdr, text="Transparenz", fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 11),
        ).pack(side="left")

        self.pct_lbl = tk.Label(
            hdr, text=f"{int(self.settings.get_opacity() * 100)}%",
            fg=t["DONE_COLOR"], bg=t["BG_COLOR"],
            font=(FONT_FAMILY, 11),
        )
        self.pct_lbl.pack(side="right")

        self.slider = OpacitySlider(
            self.win, value=self.settings.get_opacity(),
            on_change=self._on_opacity, bg=t["BG_COLOR"],
            accent=t["ACCENT"], separator=t["SEPARATOR"],
        )
        self.slider.pack(fill="x", padx=pad, pady=(4, 10))

    def _toggle_theme(self, _e=None):
        cur = self.settings.get_theme_name()
        new_name = "light" if cur == "dark" else "dark"
        s = self.settings.load()
        s["theme"] = new_name
        self.settings.save(s)
        self._do_retheme()
        # Notify all other widgets
        for w in self._all_widgets:
            if w is not self:
                w.apply_theme()

    def _on_opacity(self, val):
        s = self.settings.load()
        s["opacity"] = val
        self.settings.save(s)
        self.pct_lbl.config(text=f"{int(val * 100)}%")
        # Apply to all widgets
        self.win.attributes("-alpha", val)
        for w in self._all_widgets:
            if w is not self:
                w.win.attributes("-alpha", val)

    def _do_retheme(self):
        self._base_apply_theme()
        is_dark = self.settings.get_theme_name() == "dark"
        self.toggle_lbl.config(
            text=f"{'◑' if is_dark else '○'}  {'Dunkel' if is_dark else 'Hell'}"
        )
        self.slider.set_colors(self.t["ACCENT"], self.t["SEPARATOR"])

    def apply_theme(self):
        self._do_retheme()


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    root.withdraw()  # hidden root window

    settings = SettingsManager()

    # Create all widgets
    todo = TodoWidget(root, settings)
    health = HealthWidget(root, settings)
    notes = NotesWidget(root, settings)
    weather = WeatherWidget(root, settings)

    all_widgets = [todo, health, notes, weather]

    # Settings widget gets reference to all widgets for live theme switching
    settings_widget = SettingsWidget(root, settings, all_widgets=all_widgets)
    all_widgets.append(settings_widget)

    root.mainloop()


if __name__ == "__main__":
    main()
