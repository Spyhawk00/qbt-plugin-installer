"""
Graphical front end for install_qbt_plugins.py -- what the .exe opens.

Three screens: Welcome (what was found on this PC and exactly what will
happen, including closing qBittorrent), Installing (a live step list), and
Done. All the real work is install_qbt_plugins.run_install(), run on a worker
thread; its printed log is captured into the "Show details" panel.

The window keeps ONE fixed size for the whole run (it never jumps between
screens). It is sized for the fullest Welcome screen; the other screens fill
the same frame with something useful (the engines being added, how to
search), and "Show details" swaps the log into that same panel.

Run with command-line arguments and it behaves exactly like the script
(install_qbt_plugins.main), printing to the console it was started from.
"""

import platform
import queue
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

import install_qbt_plugins as core

IS_WINDOWS = platform.system() == "Windows"


# ---------------------------------------------------------------------------
# Command-line passthrough
# ---------------------------------------------------------------------------

def run_cli() -> None:
    """The windowed .exe has no console; borrow the one it was started from."""
    if IS_WINDOWS and getattr(sys, "frozen", False):
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):  # ATTACH_PARENT_PROCESS
            sys.stdout = open("CONOUT$", "w", encoding="utf-8")
            sys.stderr = sys.stdout
            sys.stdin = open("CONIN$", "r", encoding="utf-8")
    core.main()


# ---------------------------------------------------------------------------
# Look and feel
# ---------------------------------------------------------------------------

def windows_prefers_dark() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


LIGHT = {
    "bg": "#f4f6fb", "card": "#ffffff", "border": "#e3e7ef", "text": "#1b2333",
    "muted": "#5d6b82", "faint": "#8a95a8", "accent": "#2563eb", "accent_hover": "#1d4ed8",
    "accent_text": "#ffffff", "ok": "#16a34a", "warn": "#d97706", "bad": "#dc2626",
    "button": "#e8ecf4", "button_hover": "#dde3ee", "log_bg": "#f7f8fb",
}
DARK = {
    "bg": "#16181d", "card": "#1f2229", "border": "#2c313b", "text": "#e8ebf1",
    "muted": "#9aa4b5", "faint": "#6e7889", "accent": "#3b82f6", "accent_hover": "#2563eb",
    "accent_text": "#ffffff", "ok": "#22c55e", "warn": "#f59e0b", "bad": "#f87171",
    "button": "#2a2f39", "button_hover": "#333945", "log_bg": "#181a20",
}

FONT = "Segoe UI" if IS_WINDOWS else "Helvetica"
MONO = "Consolas" if IS_WINDOWS else "Courier"

WIDTH, HEIGHT = 540, 440  # width, and the least height (see _measure_height())
PAD = 22                  # outer margin

# Plugin file -> name shown in the GUI.
ENGINE_NAMES = {
    "piratebay": "The Pirate Bay", "leetx": "1337x", "therarbg": "TheRARBG",
    "limetorrents": "LimeTorrents", "torrentscsv": "Torrents-CSV", "snowfl": "snowfl",
    "knaben": "Knaben", "yts": "YTS (movies)", "nyaasi": "Nyaa (anime)",
    "subsplease": "SubsPlease (anime)", "fitgirl_repacks": "FitGirl (games)",
    "audiobookbay": "AudioBook Bay", "academictorrents": "Academic Torrents",
    "jackett": "Jackett",
}


def engine_names():
    files = list(core.REMOTE_PLUGINS) + [p.name for p in core.LOCAL_PLUGINS]
    stems = [Path(f).stem for f in files]
    return sorted((ENGINE_NAMES.get(st, st) for st in stems), key=str.lower)

# Status icon -> colour key.
ICONS = {"✓": "ok", "!": "warn", "✕": "bad", "•": "faint"}

# Step key (from run_install) -> label in the progress list.
STEP_LABELS = {
    "python": "Install Python",
    "close": "Close qBittorrent",
    "plugins": "Install the search engines",
    "search": "Turn on the Search tab",
    "reopen": "Reopen qBittorrent",
}
SPINNER = "◐◓◑◒"


def short_path(path: Path, limit: int = 40) -> str:
    """'C:\\Users\\me\\AppData\\Local\\qBittorrent\\nova3\\engines' ->
    '…\\AppData\\Local\\qBittorrent\\nova3\\engines' when too long."""
    text = str(path)
    if len(text) <= limit:
        return text
    parts = path.parts
    for keep in range(len(parts) - 1, 0, -1):
        tail = "\\".join(parts[-keep:]) if IS_WINDOWS else "/".join(parts[-keep:])
        candidate = "…" + ("\\" if IS_WINDOWS else "/") + tail
        if len(candidate) <= limit:
            return candidate
    return "…" + text[-(limit - 1):]


def app_icon(tk, colors):
    """A small magnifier-on-blue icon drawn in code (no image file needed)."""
    size = 32
    img = tk.PhotoImage(width=size, height=size)
    accent, white = colors["accent"], "#ffffff"
    for y in range(size):
        for x in range(size):
            dx = max(0, abs(x - 15.5) - 9.5)
            dy = max(0, abs(y - 15.5) - 9.5)
            if dx * dx + dy * dy > 36:
                continue
            r = ((x - 13) ** 2 + (y - 13) ** 2) ** 0.5
            ring = 5.5 <= r <= 8.2
            handle = 18 <= x <= 24 and 18 <= y <= 24 and abs(x - y) <= 1.6
            img.put(white if ring or handle else accent, (x, y))
    return img


class Tooltip:
    """Shows `text` in a small box while the mouse is over `widget`."""

    def __init__(self, app, widget, text):
        self.app, self.widget, self.text, self.tip = app, widget, text, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _event=None):
        if self.tip:
            return
        tk, c = self.app.tk, self.app.c
        self.tip = tk.Toplevel(self.widget)
        self.tip.overrideredirect(True)
        self.tip.attributes("-topmost", True)
        tk.Label(self.tip, text=self.text, font=(FONT, 9), bg=c["card"], fg=c["text"],
                 padx=8, pady=4, relief="solid", bd=1).pack()
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip.geometry(f"+{x}+{y}")

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ---------------------------------------------------------------------------
# The app
# ---------------------------------------------------------------------------

class InstallerApp:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk

        if IS_WINDOWS:
            try:  # crisp text on high-DPI screens
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        self.c = DARK if windows_prefers_dark() else LIGHT
        self.root = tk.Tk()
        self.root.title("qBittorrent Search Engines")
        self.root.configure(bg=self.c["bg"])
        self.root.resizable(False, False)
        # Tk sizes are in pixels while fonts are in points, so on a 150%
        # display text grows and boxes don't. Scale every pixel size.
        self.scale = max(1.0, self.root.winfo_fpixels("1i") / 96.0)
        try:
            self._icon = app_icon(tk, self.c)
            self.root.iconphoto(True, self._icon)
        except Exception:
            pass
        self._dark_title_bar()

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Accent.Horizontal.TProgressbar", troughcolor=self.c["border"],
                        background=self.c["accent"], bordercolor=self.c["border"],
                        lightcolor=self.c["accent"], darkcolor=self.c["accent"],
                        thickness=self.px(5))
        style.configure("Vertical.TScrollbar", background=self.c["button"],
                        troughcolor=self.c["log_bg"], bordercolor=self.c["log_bg"],
                        arrowcolor=self.c["muted"])

        self.events: "queue.Queue[tuple]" = queue.Queue()
        self.env = None             # what _detect() found
        self.engines_override = None
        self.shown_steps = set()
        self.step_rows = {}
        self.spin_index = 0
        self.outcome = None
        self.log_lines = []
        self.log_text = None
        self.placed = False
        self.measuring = False

        self.body = tk.Frame(self.root, bg=self.c["bg"])
        self.body.pack(fill="both", expand=True, padx=self.px(PAD), pady=(self.px(18), self.px(PAD)))
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.withdraw()  # stay hidden while the height is measured
        self.measuring = True
        self.height = self._measure_height()
        self.measuring = False
        self.show_checking()
        self.root.deiconify()
        self.root.after(50, self._pump)
        self.root.after(120, self._spin)

    # -- layout helpers ------------------------------------------------------

    def px(self, n: float) -> int:
        return int(round(n * self.scale))

    @property
    def inner_width(self) -> int:
        """Usable width inside a card, for wrapping text."""
        return self.px(WIDTH - 2 * PAD - 2 * 16 - 4)

    def _measure_height(self) -> int:
        """The one window height for this PC: the tallest screen the run
        could show, laid out off-screen with this PC's fonts and scaling.

        A hard-coded height fits only the display it was tuned on: text
        does not scale in step with pixels, so at 100-150% the same screens
        came out up to ~30 px taller than at 175% and were cut off.
        """
        long_path = Path("C:/Users/Example User/AppData/Local/qBittorrent/nova3/engines")
        tallest = core.QbtLocation(long_path, None, "qbittorrent.exe", "standard")
        worst_env = dict(location=tallest, running={0: ""}, exe="qbittorrent.exe",
                         need_python=True, record=None, has_plugins=False)
        heights = []

        def measure():
            self.root.update_idletasks()
            heights.append(self.body.winfo_reqheight() + self.px(18) + self.px(PAD))

        self.show_welcome(worst_env)
        measure()
        self._render_installing(worst_env)
        measure()
        for reopened, python_ok in ((True, True), (False, False)):
            outcome = core.Outcome()
            outcome.reopened, outcome.python_ok = reopened, python_ok
            self.show_done(outcome, measuring=True)
            measure()

        # Put back everything those screens set up.
        self.clear()
        self.env = self.outcome = None
        self.shown_steps = set()
        self.log_lines = []
        return max(max(heights) + self.px(2), self.px(HEIGHT))

    def fit(self) -> None:
        """Set the one window size, once, centred. Every screen is laid out
        to fit inside it, so it never changes afterwards."""
        if self.placed or self.measuring:
            return
        width, height = self.px(WIDTH), self.height
        x = (self.root.winfo_screenwidth() - width) // 2
        y = max(0, (self.root.winfo_screenheight() - height) // 3)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(width, height)
        self.root.maxsize(width, height)
        self.placed = True

    def _dark_title_bar(self) -> None:
        if not IS_WINDOWS or self.c is not DARK:
            return
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value),
                                                       ctypes.sizeof(value))
        except Exception:
            pass

    def clear(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self.step_rows = {}
        self.log_text = None
        # Each screen binds Enter to its own main button (or none); never let
        # it carry over, or Enter during an install would start another.
        self.root.unbind("<Return>")

    def label(self, parent, text, size=10, weight="normal", color="text", **kw):
        kw.setdefault("justify", "left")
        kw.setdefault("anchor", "w")
        return self.tk.Label(parent, text=text, font=(FONT, size, weight),
                             fg=self.c[color], bg=kw.pop("bg", parent["bg"]), **kw)

    def card(self, parent, pady=(0, 0)):
        outer = self.tk.Frame(parent, bg=self.c["border"])
        outer.pack(fill="x", pady=pady)
        inner = self.tk.Frame(outer, bg=self.c["card"], padx=self.px(16), pady=self.px(12))
        inner.pack(fill="both", padx=1, pady=1)
        return inner

    def section_title(self, parent, text, top=0):
        self.label(parent, text.upper(), size=8, weight="bold", color="faint").pack(
            fill="x", pady=(self.px(top), self.px(6)))

    def divider(self, parent):
        self.tk.Frame(parent, bg=self.c["border"], height=1).pack(
            fill="x", pady=(self.px(10), self.px(10)))

    def button(self, parent, text, command, primary=False, state="normal"):
        enabled = state != "disabled"
        bg = self.c["accent"] if primary and enabled else self.c["button"]
        hover = self.c["accent_hover"] if primary else self.c["button_hover"]
        fg = self.c["accent_text"] if primary else self.c["text"]
        b = self.tk.Button(parent, text=text, command=command,
                           font=(FONT, 10, "bold" if primary else "normal"),
                           bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
                           relief="flat", bd=0, padx=self.px(18), pady=self.px(6),
                           cursor="hand2" if enabled else "arrow",
                           highlightthickness=0, state=state,
                           disabledforeground=self.c["faint"])
        if enabled:
            b.bind("<Enter>", lambda e: b.configure(bg=hover))
            b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def link(self, parent, text, command, size=9):
        lab = self.label(parent, text, size=size, color="accent", cursor="hand2")
        lab.bind("<Button-1>", lambda e: command())
        return lab

    def header(self, title, subtitle=None):
        top = self.tk.Frame(self.body, bg=self.c["bg"])
        top.pack(fill="x")
        self.label(top, title, size=15, weight="bold").pack(side="left")
        self.label(top, f"v{core.__version__}", size=9, color="faint").pack(side="right")
        if subtitle:
            self.label(self.body, subtitle, size=10, color="muted",
                       wraplength=self.px(WIDTH - 2 * PAD)).pack(fill="x", pady=(self.px(2), 0))
        self.tk.Frame(self.body, bg=self.c["bg"], height=self.px(12)).pack(fill="x")

    def grid_rows(self, parent, rows):
        """Aligned rows: (icon, name, value, action-or-None, tooltip-or-None)."""
        grid = self.tk.Frame(parent, bg=parent["bg"])
        grid.pack(fill="x")
        grid.columnconfigure(2, weight=1)
        for r, (icon, name, value, action, tip) in enumerate(rows):
            pad = (0, self.px(5))
            self.label(grid, icon, size=10, weight="bold", color=ICONS.get(icon, "faint"),
                       width=2).grid(row=r, column=0, sticky="nw", pady=pad)
            self.label(grid, name, size=10, weight="bold").grid(
                row=r, column=1, sticky="nw", padx=(0, self.px(14)), pady=pad)
            val = self.label(grid, value, size=10,
                             color="warn" if icon == "!" else "bad" if icon == "✕" else "muted",
                             wraplength=self.inner_width - self.px(235 if action else 185))
            val.grid(row=r, column=2, sticky="nw", pady=pad)
            if tip:
                Tooltip(self, val, tip)
            if action:
                action(grid).grid(row=r, column=3, sticky="ne", padx=(self.px(8), 0), pady=pad)
        return grid

    def bullet_list(self, parent, items):
        """(icon, text) lines; '!' items are the ones the user must notice."""
        for icon, text in items:
            row = self.tk.Frame(parent, bg=parent["bg"])
            row.pack(fill="x", pady=(0, self.px(5)))
            self.label(row, icon, size=10, weight="bold", color=ICONS.get(icon, "faint"),
                       width=2).pack(side="left", anchor="n")
            self.label(row, text, size=10, color="text" if icon == "!" else "muted",
                       wraplength=self.inner_width - self.px(30)).pack(side="left", fill="x")

    def footer(self, message=None):
        """Button bar: details link on the left, buttons on the right."""
        bar = self.tk.Frame(self.body, bg=self.c["bg"])
        bar.pack(side="bottom", fill="x", pady=(self.px(14), 0))
        if message:
            self.label(bar, message, size=9, color="warn",
                       wraplength=self.px(WIDTH - 2 * PAD)).pack(fill="x", pady=(0, self.px(10)))
        buttons = self.tk.Frame(bar, bg=self.c["bg"])
        buttons.pack(fill="x")
        return buttons

    # -- screen 0: checking --------------------------------------------------

    def show_checking(self) -> None:
        self.clear()
        self.header("Search engines for qBittorrent")
        box = self.card(self.body)
        self.label(box, "Checking your PC…", size=10, color="muted").pack(fill="x")
        bar = self.ttk.Progressbar(box, mode="indeterminate",
                                   style="Accent.Horizontal.TProgressbar")
        bar.pack(fill="x", pady=(self.px(8), 0))
        bar.start(12)
        self.fit()
        threading.Thread(target=self._detect, daemon=True).start()

    def _detect(self) -> None:
        """Find qBittorrent, its folders and Python. Changes nothing."""
        try:
            location = core.locate_qbittorrent(self.engines_override)
            running = core.qbittorrent_processes()
            exe = (location.exe if location else None) or core.find_qbittorrent()
            if getattr(sys, "frozen", False) or sys.version_info[:2] < core.MIN_PYTHON:
                need_python = core.find_system_python() is None
            else:
                need_python = False
            record = core.read_install_record(location.engines_dir) if location else None
            has_plugins = bool(location) and location.engines_dir.exists() and any(
                p.name != "__init__.py" for p in location.engines_dir.glob("*.py"))
            env = dict(location=location, running=running, exe=exe,
                       need_python=need_python, record=record, has_plugins=has_plugins)
            self.events.put(("detected", env))
        except Exception:
            self.events.put(("detect_failed", traceback.format_exc()))

    # -- screen 1: welcome ---------------------------------------------------

    def show_welcome(self, env) -> None:
        self.env = env
        self.clear()
        location, running = env["location"], env["running"]
        engines = len(core.REMOTE_PLUGINS) + len(core.LOCAL_PLUGINS)
        self.header("Search engines for qBittorrent",
                    f"Adds {engines} working search engines to qBittorrent's Search tab.")

        card = self.card(self.body)

        # --- On this PC
        self.section_title(card, "On this PC")
        qbt_known = bool(env["exe"]) or bool(location and location.has_run_before)
        rows = []
        if running:
            rows.append(("✓", "qBittorrent", "Installed · running", None, None))
        elif qbt_known:
            rows.append(("✓", "qBittorrent", "Installed", None, None))
        else:
            rows.append(("!", "qBittorrent", "Not found on this PC", None, None))

        if env["need_python"]:
            rows.append(("!", "Python", "Missing — will be installed", None, None))
        else:
            rows.append(("✓", "Python", "Installed", None, None))

        if location:
            kind = {"portable": "  (portable)", "flatpak": "  (Flatpak)"}.get(location.kind, "")
            rows.append(("✓", "Plugin folder", short_path(location.engines_dir) + kind,
                         lambda parent: self.link(parent, "Change", self.change_folder),
                         str(location.engines_dir)))
        else:
            rows.append(("✕", "Plugin folder", "Not found",
                         lambda parent: self.link(parent, "Choose", self.change_folder), None))

        # Version: one short line. What it means for this run is said in the
        # plan below ("refreshed" vs "installed"), not crammed in here.
        record, downgrade, refresh = env["record"], False, False
        new = core.parse_version(core.__version__)
        if record:
            prev = str(record.get("version", "?"))
            old = core.parse_version(prev)
            if old and old > new:
                downgrade = True
                rows.append(("✕", "Version", f"v{prev} — newer than this installer", None, None))
            elif old == new:
                refresh = True
                rows.append(("✓", "Version", f"v{prev} — already installed", None, None))
            else:
                refresh = True
                rows.append(("•", "Version", f"v{prev} → updating to v{core.__version__}",
                             None, None))
        elif env["has_plugins"]:
            refresh = True
            rows.append(("•", "Version", f"Older version → updating to v{core.__version__}",
                         None, None))
        else:
            rows.append(("•", "Version", "Not installed yet", None, None))
        self.grid_rows(card, rows)

        blocked = None
        if downgrade:
            blocked = ("This PC already has a newer version of these search engines. "
                       "Download the latest installer instead.")
        elif not qbt_known:
            blocked = ("Install qBittorrent and open it once, then run this installer again.")
        elif location is None:
            blocked = "Choose qBittorrent's plugin folder (Choose, above) to continue."

        self.divider(card)
        if blocked:
            # Nothing will happen, so the plan is replaced by the reason why.
            self.section_title(card, "Can't install yet")
            self.bullet_list(card, [("!", blocked)])
        else:
            self.section_title(card, "When you click Install")
            plan = []
            if running:
                plan.append(("!", "qBittorrent closes and reopens — torrents are saved first."))
            if env["need_python"]:
                plan.append(("!", f"Python {core.PYTHON_INSTALLER['version']} is installed "
                                  "(from python.org, no admin needed)."))
            plan.append(("✓", f"The {engines} search engines are "
                              + ("refreshed to their latest versions." if refresh
                                 else "installed.")))
            plan.append(("✓", "The Search tab is turned on."))
            self.bullet_list(card, plan)
        # The exact steps run_install() will ask to confirm; already agreed to
        # by clicking Install on this screen.
        self.shown_steps = set(core.disruptive_steps(env["need_python"], bool(running)))

        bar = self.footer()
        if blocked and not qbt_known:
            self.button(bar, "Get qBittorrent",
                        lambda: webbrowser.open("https://www.qbittorrent.org/download")
                        ).pack(side="left")
        install = self.button(bar, "Install", self.start_install, primary=True,
                              state="disabled" if blocked else "normal")
        install.pack(side="right")
        self.button(bar, "Cancel", self.root.destroy).pack(side="right", padx=(0, self.px(8)))
        if not blocked:
            self.root.bind("<Return>", lambda e: install.invoke())
            install.focus_set()
        self.fit()

    def change_folder(self) -> None:
        from tkinter import filedialog
        picked = filedialog.askdirectory(title="Choose qBittorrent's nova3\\engines folder",
                                         parent=self.root)
        if not picked:
            return
        path = Path(picked)
        # Accept the qBittorrent data folder or nova3 too; plugins go in engines.
        if path.name.lower() == "qbittorrent":
            path = path / "nova3" / "engines"
        elif path.name.lower() == "nova3":
            path = path / "engines"
        self.engines_override = path
        self.show_checking()

    # -- screen 2: installing ------------------------------------------------

    def start_install(self) -> None:
        self._render_installing(self.env)
        opts = core.Options(engines_dir=self.engines_override)
        threading.Thread(target=self._worker, args=(opts,), daemon=True).start()

    def _render_installing(self, env) -> None:
        self.clear()
        self.header("Installing…")

        card = self.card(self.body)
        keys = []
        if env["need_python"]:
            keys.append("python")
        if env["running"]:
            keys.append("close")
        keys += ["plugins", "search"]
        if env["running"]:
            keys.append("reopen")
        for key in keys:
            row = self.tk.Frame(card, bg=self.c["card"])
            row.pack(fill="x", pady=(0, self.px(3)))
            icon = self.label(row, "○", size=11, color="faint", width=2)
            icon.pack(side="left")
            text = self.label(row, STEP_LABELS[key], size=10, color="muted")
            text.pack(side="left", padx=(self.px(4), 0))
            self.step_rows[key] = (icon, text)
        self.progress = self.ttk.Progressbar(card, mode="indeterminate",
                                             style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(self.px(4), 0))
        self.progress.start(12)

        bar = self.footer()
        self._panel(bar, self._engines_panel)
        self.fit()

    def _panel(self, bar, build, open_log=False) -> None:
        """The space between the main card and the footer. It shows the
        panel `build` makes, and the footer's "Show details" link swaps the
        install log into the same space, so the window size never changes."""
        area = self.tk.Frame(self.body, bg=self.c["bg"])
        area.pack(fill="both", expand=True, pady=(self.px(12), 0), before=bar.master)

        info = build(area)

        log = self.tk.Frame(area, bg=self.c["border"])
        text = self.tk.Text(log, font=(MONO, 8), bg=self.c["log_bg"], fg=self.c["muted"],
                            relief="flat", bd=0, padx=self.px(8), pady=self.px(6),
                            wrap="none", height=1, highlightthickness=0)
        scroll = self.ttk.Scrollbar(log, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        text.insert("end", "".join(self.log_lines))
        text.see("end")
        text.configure(state="disabled")
        self.log_text = text

        def show(log_visible):
            if log_visible:
                info.pack_forget()
                log.pack(fill="both", expand=True)
                link.configure(text="Hide details")
            else:
                log.pack_forget()
                info.pack(fill="x")  # natural height; only the log fills the space
                link.configure(text="Show details")

        link = self.link(bar, "Show details", lambda: show(not log.winfo_ismapped()))
        link.pack(side="left")
        show(open_log)

    def _info_card(self, parent):
        outer = self.tk.Frame(parent, bg=self.c["border"])
        inner = self.tk.Frame(outer, bg=self.c["card"], padx=self.px(16), pady=self.px(12))
        inner.pack(fill="x", padx=1, pady=1)
        return outer, inner

    def _engines_panel(self, parent):
        outer, inner = self._info_card(parent)
        self.section_title(inner, "Adding these search engines")
        grid = self.tk.Frame(inner, bg=self.c["card"])
        grid.pack(fill="x")
        names = engine_names()
        cols = 3
        per_col = -(-len(names) // cols)
        for i, name in enumerate(names):
            cell = self.tk.Frame(grid, bg=self.c["card"])
            cell.grid(row=i % per_col, column=i // per_col, sticky="w",
                      padx=(0, self.px(10)), pady=(0, self.px(3)))
            self.label(cell, "•", size=9, color="accent").pack(side="left", padx=(0, self.px(5)))
            self.label(cell, name, size=9, color="muted").pack(side="left")
        for col in range(cols):
            grid.columnconfigure(col, weight=1, uniform="engines")
        return outer

    def _howto_panel(self, parent):
        outer, inner = self._info_card(parent)
        self.section_title(inner, "How to search")
        steps = [
            "Open qBittorrent and click the Search tab.",
            "Type what you're looking for and click Search. Results from every "
            "engine appear in one list.",
            "Double-click a result to start downloading it.",
        ]
        for n, text in enumerate(steps, 1):
            row = self.tk.Frame(inner, bg=self.c["card"])
            row.pack(fill="x", pady=(0, self.px(6)))
            size = self.px(20)
            dot = self.tk.Canvas(row, width=size, height=size, bg=self.c["card"],
                                 highlightthickness=0)
            dot.create_oval(1, 1, size - 1, size - 1, fill=self.c["button"], outline="")
            dot.create_text(size / 2, size / 2, text=str(n), fill=self.c["text"],
                            font=(FONT, 8, "bold"))
            dot.pack(side="left", anchor="n", padx=(0, self.px(10)))
            self.label(row, text, size=10, color="muted",
                       wraplength=self.inner_width - self.px(34)).pack(side="left", fill="x")
        self.label(inner, "Run this installer again any time to update the engines.",
                   size=9, color="faint").pack(fill="x", pady=(self.px(4), 0))
        return outer

    def _worker(self, opts) -> None:
        events = self.events

        class Capture:
            def write(self, s):
                if s:
                    events.put(("log", s))
                return len(s)

            def flush(self):
                pass

        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = Capture()
        try:
            outcome = core.run_install(opts, confirm=self._confirm_from_worker,
                                       step=lambda k, s: events.put(("step", k, s)))
            events.put(("finished", outcome))
        except Exception:
            events.put(("crashed", traceback.format_exc()))
        finally:
            sys.stdout, sys.stderr = old_out, old_err

    def _confirm_from_worker(self, steps) -> bool:
        """The user agreed to the plan on the Welcome screen. Ask again only
        if something new turned up since (e.g. qBittorrent was started)."""
        disruptive = set(core.disruptive_steps(True, True))
        new = [s for s in steps if s in disruptive and s not in self.shown_steps]
        if not new:
            return True
        answer = {}
        done = threading.Event()

        def ask():
            from tkinter import messagebox
            answer["ok"] = messagebox.askokcancel(
                "Before we continue",
                "Something changed since you clicked Install:\n\n"
                + "\n\n".join("• " + s for s in new) + "\n\nContinue?",
                parent=self.root)
            done.set()

        self.root.after(0, ask)
        done.wait()
        return answer.get("ok", False)

    def _set_step(self, key, state) -> None:
        if key not in self.step_rows:
            return
        icon, text = self.step_rows[key]
        glyph, color, text_color = {
            "running": (SPINNER[0], "accent", "text"),
            "done": ("✓", "ok", "text"),
            "skipped": ("–", "faint", "faint"),
            "failed": ("!", "warn", "text"),
        }[state]
        icon.configure(text=glyph, fg=self.c[color])
        text.configure(fg=self.c[text_color])
        icon.state = state

    def _spin(self) -> None:
        self.spin_index = (self.spin_index + 1) % len(SPINNER)
        for icon, _ in self.step_rows.values():
            if getattr(icon, "state", None) == "running":
                try:
                    icon.configure(text=SPINNER[self.spin_index])
                except self.tk.TclError:
                    pass
        self.root.after(120, self._spin)

    # -- screen 3: done ------------------------------------------------------

    def show_done(self, outcome, crash=None, measuring=False) -> None:
        self.outcome = outcome
        self.clear()
        c = self.c
        env = self.env or {}

        if crash or outcome.error:
            icon, color, title = "!", "bad", "Something went wrong"
            message = outcome.error if outcome.error else (
                "The installer hit an unexpected problem. Open the details below "
                "to see what happened.")
        elif outcome.cancelled:
            icon, color, title = "–", "faint", "Cancelled"
            message = "Nothing was changed."
        elif not outcome.python_ok:
            icon, color, title = "!", "warn", "Almost done"
            message = ("Engines installed, but Python couldn't be installed, so search "
                       "won't run yet. Install it from python.org, then run this again.")
        elif outcome.failed:
            icon, color, title = "!", "warn", "Almost done"
            message = (f"{outcome.failed} item(s) couldn't be downloaded. Check your "
                       "internet connection and run this again.")
        elif outcome.reopened:
            icon, color, title = "✓", "ok", "All done!"
            message = ("qBittorrent is open again, behind this window. Click Finish "
                       "to go to it, then open its Search tab.")
        elif outcome.needs_restart:
            icon, color, title = "✓", "ok", "Almost done"
            message = ("Restart qBittorrent to load the new engines: right-click its "
                       "icon near the clock, choose Exit, then open it again.")
        else:
            icon, color, title = "✓", "ok", "All done!"
            message = "Open qBittorrent and go to its Search tab to start searching."

        self.header("Search engines for qBittorrent")
        card = self.card(self.body)
        top = self.tk.Frame(card, bg=c["card"])
        top.pack(fill="x")
        size = self.px(44)
        badge = self.tk.Canvas(top, width=size, height=size, bg=c["card"], highlightthickness=0)
        badge.create_oval(1, 1, size - 1, size - 1, fill=c[color], outline="")
        badge.create_text(size / 2, size / 2, text=icon, fill="#ffffff", font=(FONT, 16, "bold"))
        badge.pack(side="left", anchor="n")
        words = self.tk.Frame(top, bg=c["card"])
        words.pack(side="left", fill="x", expand=True, padx=(self.px(14), 0))
        self.label(words, title, size=14, weight="bold").pack(fill="x")
        self.label(words, message, size=10, color="muted",
                   wraplength=self.inner_width - size - self.px(14)).pack(fill="x", pady=(self.px(2), 0))

        if not crash and not outcome.cancelled and not outcome.error:
            parts = [f"{outcome.installed} installed or updated",
                     f"{outcome.skipped} already up to date"]
            if outcome.removed:
                parts.append(f"{outcome.removed} dead engines removed")
            self.divider(card)
            self.label(card, "  ·  ".join(parts), size=9, color="faint").pack(fill="x")

        # The last click hands the user over to qBittorrent:
        #  - reopened: qBittorrent is already starting; keep this window on
        #    top so its window can't bury the button, and Finish brings
        #    qBittorrent to the front as this closes.
        #  - not running: "Open qBittorrent" is the natural next step, so it
        #    is the main button.
        bar = self.footer()
        exe = env.get("exe")
        ok = not crash and not outcome.cancelled and not outcome.error
        if ok and outcome.reopened:
            primary = self.button(bar, "Finish", self._finish_to_qbittorrent, primary=True)
            primary.pack(side="right")
            if not measuring:
                self._stay_on_top()
        elif ok and exe and (measuring or not core.qbittorrent_processes()):
            primary = self.button(bar, "Open qBittorrent",
                                  lambda: (core.launch_qbittorrent(exe), self.root.destroy()),
                                  primary=True)
            primary.pack(side="right")
            self.button(bar, "Close", self.root.destroy).pack(side="right", padx=(0, self.px(8)))
        else:
            primary = self.button(bar, "Close", self.root.destroy, primary=True)
            primary.pack(side="right")
        self.root.bind("<Return>", lambda e: primary.invoke())
        primary.focus_set()
        self._panel(bar, self._howto_panel, open_log=bool(crash))
        self.fit()

    def _stay_on_top(self) -> None:
        """Keep the Done screen above qBittorrent, which grabs the front as it
        starts. Only on this last screen, and only until the user clicks."""
        try:
            self.root.attributes("-topmost", True)
            self.root.lift()
            self.root.focus_force()
        except self.tk.TclError:
            pass

    def _finish_to_qbittorrent(self) -> None:
        """Close the installer and put qBittorrent's window in front.

        Done while this window still has the foreground (the user just
        clicked it), which is when Windows lets us hand the foreground on.
        """
        if IS_WINDOWS:
            try:
                import ctypes
                import ctypes.wintypes as wt
                user32 = ctypes.windll.user32
                pids = set(core.qbittorrent_processes())
                best = []

                @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
                def collect(hwnd, _):
                    owner = wt.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                    if owner.value in pids and user32.IsWindowVisible(hwnd) \
                            and user32.GetWindowTextLengthW(hwnd) > 0:
                        best.append(hwnd)
                    return True

                user32.EnumWindows(collect, 0)
                self.root.attributes("-topmost", False)
                for hwnd in best[:1]:
                    if user32.IsIconic(hwnd):
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
        self.root.destroy()

    # -- plumbing ------------------------------------------------------------

    def _pump(self) -> None:
        """Apply events from the worker threads on the Tk thread."""
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "log":
                    self.log_lines.append(event[1])
                    if self.log_text is not None:
                        try:
                            self.log_text.configure(state="normal")
                            self.log_text.insert("end", event[1])
                            self.log_text.see("end")
                            self.log_text.configure(state="disabled")
                        except self.tk.TclError:
                            pass
                elif kind == "step":
                    self._set_step(event[1], event[2])
                elif kind == "detected":
                    self.show_welcome(event[1])
                elif kind == "detect_failed":
                    self.log_lines.append(event[1])
                    out = core.Outcome()
                    out.error = "Couldn't check this PC for qBittorrent."
                    self.show_done(out, crash=event[1])
                elif kind == "finished":
                    self.show_done(event[1])
                elif kind == "crashed":
                    self.log_lines.append(event[1])
                    self.show_done(core.Outcome(), crash=event[1])
        except queue.Empty:
            pass
        self.root.after(50, self._pump)

    def _on_close(self) -> None:
        busy = bool(self.step_rows) and self.outcome is None
        if busy:
            from tkinter import messagebox
            if not messagebox.askyesno("Still installing",
                                       "The installer is still working. Close anyway?",
                                       parent=self.root):
                return
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if len(sys.argv) > 1:
        run_cli()
        return
    InstallerApp().run()


if __name__ == "__main__":
    main()
