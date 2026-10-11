#!/usr/bin/env python3
"""
qBittorrent Search Plugin Installer
====================================
Downloads all verified-working search plugins and copies them into
qBittorrent's engines directory.

Before installing, a preflight checks the required dependencies (Python
version, pip, qBittorrent) and auto-installs any third-party Python package a
plugin needs. Today every plugin is standard-library only, so nothing extra is
installed, but the check future-proofs the installer.

Most people don't need to read this. Just double-click
qbt-plugin-installer-<version>.exe and click Install.

Usage (command line):
  python install_qbt_plugins.py              # install everything
  python install_qbt_plugins.py --dry-run    # preview only, no changes
  python install_qbt_plugins.py --force      # also rewrite unchanged files + nova3 framework
  python install_qbt_plugins.py --skip-deps  # skip the dependency preflight
  python install_qbt_plugins.py --pause      # wait for Enter before exiting
  python install_qbt_plugins.py --yes        # don't ask before installing Python / closing qBittorrent
  python install_qbt_plugins.py --no-restart # leave a running qBittorrent alone

The double-click .exe is the GUI in qbt_installer_gui.py, a front end over
run_install() below.

Verified status (October 2026) — every engine below was run through
nova2.py against the live site and the results counted. Use a query that
suits the engine: "ubuntu" on Nyaa, SubsPlease, YTS or FitGirl returns
little or nothing, and that is the site, not the plugin.

  ✔  Nyaa.si          — community plugin (MadeOfMagicAndWires). 1000 results
                         ("naruto")
  ✔  SubsPlease       — community plugin (kli885), anime simulcasts. 378
                         results ("naruto")
  ✔  TheRARBG         — REWRITTEN local copy of BurningMop's v1.3 (v2.0).
                         150 results in ~2 s. The site retitled its results
                         page, and upstream only parsed pages titled "Search
                         for ...", so it returned nothing. Upstream also
                         fetched a detail page per row from an unbounded
                         thread loop. Now: 3 pages in parallel, magnet
                         resolved on download. This is the RARBG successor;
                         the original shut down in 2023.
  ✔  snowfl            — community plugin (LightDestory). ADDED Sept 2026.
                         136 results, magnet links. A meta-search: it rate
                         limits under concurrent queries and returns zero for
                         a while, which looks exactly like a dead engine.
                         Run it on its own before concluding anything.
  ✔  Knaben           — CUSTOM plugin (knaben.py). ADDED Oct 2026. An
                         English index that collects The Pirate Bay, 1337x,
                         Nyaa, YTS and others, through its JSON API
                         (api.knaben.org/v1): 176-565 results in 2-3 s, magnet
                         links, all categories. RuTracker's Russian-language
                         results are filtered out (often a third of the hits).
  ✔  LimeTorrents     — official repo (v4.15). 160 results. Its limetorrents.lol
                         now 301-redirects to .fun, so the bundled copy that
                         patched the domain was dropped in 1.2.0: it also had
                         an unreadable "4.14-patched" version (qBittorrent
                         reads 16 characters of that line), so qBittorrent
                         logged a warning at every start and its "Check for
                         updates" button always replaced it.
  ✔  The Pirate Bay   — official repo, JSON API. 100 results
  ✔  FitGirl Repacks  — CUSTOM plugin, WP REST API. 94 results
  ✔  Torrents-CSV     — official repo, JSON API. 25 results
  ✔  Academic Torrents — community plugin (LightDestory). 21 results
  ✔  1337x            — CUSTOM plugin (leetx.py, class leetx). RE-ADDED Oct
                         2026. 1337x.to, 1337x.st and the x1337x.* domains
                         are all behind a Cloudflare JS challenge (403),
                         which is why it was removed in June. www.1337xx.to
                         serves the same index without one: identical
                         markup, uploads from the current week, and its
                         info hashes match the torrents itorrents.org holds
                         under the same names, so it is a real mirror and
                         not a clone with fake links. 5 pages in parallel,
                         magnet resolved on download.
  ✔  YTS              — CUSTOM plugin (movies only). 148 results ("batman")
  ✔  Jackett          — official repo. Reachable; returns its "api key error"
                         row until you install Jackett locally and set a key.
                         That row is the plugin working, not failing.
  ✔  AudioBook Bay    — REWRITTEN local copy of nKlido's v0.4 (v1.0). 27
                         results in ~5 s ("dune"). Upstream's three mirrors
                         (theaudiobookbay.se, audiobookbay.fi,
                         audiobookbay.is) no longer resolve and it had no
                         timeouts, so it hung ~60 s and returned nothing.
                         audiobookbay.lu serves the same site on the same
                         IP (176.97.124.219) and is now tried first. Pages
                         are capped and parallel, and the info hash is
                         fetched only on download. The site publishes no
                         peer counts, so seeds/leech show as unknown. That
                         host has been intermittent before: if this engine
                         alone returns nothing, wait rather than debug it.

  Note on ebooks/epub: No public torrent sites specialise in epub only.
  For ebooks, use the existing plugins with their 'books' category:
  The Pirate Bay, 1337x and Knaben all index ebook torrents.
  Academic Torrents covers research papers / textbooks.

  Note on qBittorrent's own "Check for updates" button: it installs every
  official plugin that is missing (eztv, torlock, solidtorrents,
  torrentproject -- all retired here) and replaces same-named plugins with a
  higher version. Re-running this installer removes them again.

  Note on DNS filtering: a filtering resolver (NextDNS, Pi-hole, an ISP block,
  some VPNs) answers torrent-site lookups with 0.0.0.0 or NXDOMAIN, and the
  plugin then fails with "getaddrinfo failed". That is not a broken plugin.
  If several engines fail that way at once, check the resolver first.

  ✘  EZTV             — NOT INSTALLED, for two separate reasons. The site is
                         alive (eztvx.to answered 200 with 1,084,249 torrents
                         when reached by IP), but it is on the block list of
                         common filtering resolvers. More seriously, the
                         plugin ships with a placeholder OMDB_API_KEY, so its
                         title lookup returns "Unauthorized" and it falls back
                         to _search_by_keywords -- and the EZTV API ignores the
                         Keywords parameter: it returns the same 100 rows and
                         the same site-wide torrents_count either way. The
                         fallback loop therefore runs until page*100 exceeds
                         1.08 million, i.e. ~10,800 requests, filtering client
                         side. It does not finish. Only install this one if
                         you paste a free key from
                         https://www.omdbapi.com/apikey.aspx into the plugin,
                         which makes it use the imdb_id path instead.
  ✘  Rutor            — REMOVED Oct 2026: it works (260 results), but it is
                         a Russian tracker with Russian-language releases,
                         and this installer ships English sites only.
                         Re-running the installer deletes an installed copy.
  ✘  TorrentGalaxy    — REMOVED Oct 2026 as too slow: ~87 s per search
                         (1249 rows for "batman"), the slowest engine by far,
                         and it holds the Search tab open the whole time. It
                         works, and its site search matches loosely, so many
                         of those rows were unrelated anyway. Re-running the
                         installer deletes an installed copy.
  ✘  torrentdownload  — REMOVED Oct 2026 as too slow: the host answers every
                         request after a flat ~20 s, so even with pages
                         fetched concurrently (qbt_plugins/torrentdownload.py,
                         v1.3, kept but not installed) a search takes ~24 s.
                         Re-running the installer deletes an installed copy.
  ✘  TorLock          — REMOVED Oct 2026: torlock.com, torlock2.com and both
                         www. hosts answer 403 with "cf-mitigated: challenge"
                         (a Cloudflare JS challenge urllib cannot pass).
                         torlock.cc is a parked page. qbt_plugins/torlock.py
                         is kept in case the site drops the challenge;
                         nothing installs it, and re-running the installer
                         deletes an installed copy (RETIRED_PLUGINS).
  ✘  BitSearch        — REMOVED: bitsearch.to answers every request with a
                         308 redirect to the identical URL — an infinite loop.
                         Confirmed by IP, so it is not just the DNS block.
  ✘  BTDig            — REMOVED: btdig.com and www.btdig.com now serve the
                         612-byte "Welcome to nginx" default page. The search
                         service is gone from that host.
  ✘  GloTorrents      — REMOVED: glodls.to aborts the TLS handshake
                         (UNEXPECTED_EOF_WHILE_READING) and plain HTTP returns
                         nginx 404. No mirror (gtdb.to, gtdb.cc, gtso.cc)
                         resolves.
  ✘  Torrentz2        — REMOVED from the install list: torrentz2.nz answered
                         with a 308 redirect to the identical URL (Sept
                         2026) and no longer resolves at all (Oct 2026). The plugin
                         file is kept in qbt_plugins/ in case the site
                         recovers; nothing installs it.

  Also tested in September 2026 and NOT added:
  ✘  Kinozal          — returns one row reading "[Error]: .../takelogin.php".
                         Login-only, same as RuTracker.
  ✘  BT4G, bt.etree   — Cloudflare 403; urllib cannot pass the challenge.
  ✘  FileMood, torrentdownloads.pro
                       — both run past 120 s without finishing. A hanging
                         engine is worse than a failing one: it holds the
                         Search tab open with no result and no error.
  ✘  Rockbox, CloudTorrents, Nitro, TorrentClaw, YourBittorrent, BakaBT,
     LinuxTracker      — reachable but returned nothing, or raised.
  ✘  NNM-Club         — does not even import under nova2.
  ✘  ETTV, TorrentQuest, IlCorsaroNero
                       — alive on public DNS but answered 0.0.0.0 on the
                         machine this was tested from, so they could not be
                         verified here. Try them if your resolver allows.

  Rechecked October 2026 for English sites and still NOT added:
  ✘  YourBittorrent, UIndex, BT4G — 403 / Cloudflare challenge.
  ✘  CloudTorrents    — its API answers Cloudflare 526 (origin down).
  ✘  AnimeTosho       — feed.animetosho.org did not answer within 11 s.
  ✘  torrentdownloads.pro — still a flat ~20 s per request.
  ✘  TorrentClaw      — its API answers "Forbidden" without an API key.
  ✘  LinuxTracker     — site alive but redesigned; the 2017 plugin finds
                         nothing on it.
  ✘  EZTV (eztvx, DrPurp v3.20) — the same OMDb-key problem as above; its
                         search page is now Cloudflare-challenged too, as are
                         the eztv.re / .wf / .tf / .yt mirrors.
  ✘  ext.to, rargb.to, TorrentFunk, Tokyo Toshokan (the site, not just the
     plugin), TorrentKitty, Demonoid (dnoid.to)
                       — all answer 403 with a Cloudflare challenge.
  ✘  BitSearch        — bitsearch.to now redirects to bitsearch.eu, whose
                         page Microsoft Defender flags as
                         Trojan:HTML/Redirector (malicious redirects). Never
                         re-add it. torlock.cc's parked page is flagged too.
  ✘  torrentgalaxy.one — fast, but a reskin of TheRARBG: same database, the
                         same 39/39 post ids for "ubuntu". Adds only duplicates.
  ✘  isoHunt (isohunt.nz), iDope, magnetdl.homes — no real results (empty,
                         script-rendered or a stub page).

  ✘  RuTracker        — not added: requires login credentials
  ✘  Myanonamouse (MAM) — not added (private tracker, invite-only)
  ✘  Kickass Torrents — REMOVED: katcr.to and mirrors return 403
  ✘  Zooqle           — REMOVED: site is defunct
  ✘  MagnetDL         — DEAD: origin down (HTTP 522), all mirrors unreachable
  ✘  DODI Repacks     — DEAD: fully behind Cloudflare; hydralinks.cloud 403
  ✘  SolidTorrents    — DEAD: solidtorrents.to no longer resolves
  ✘  TorrentProject   — DEAD: site returns no content
  ✘  Tokyo Toshokan   — BROKEN: incompatible with qBittorrent 4.6+
"""

import argparse
import ast
import atexit
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

# The installer's version: the single source of truth. Semantic versioning,
# MAJOR.MINOR.PATCH -- see CHANGELOG.md for what bumps which part. A release
# tag (vX.Y.Z) must match this; the build workflow refuses one that doesn't.
__version__ = "1.2.0"

# Where releases are published. The installer and the "Installer updates"
# notice engine (qbt_plugins/installer_updates.py, which has its own copy)
# read the release tags (vX.Y.Z) from here to tell users about a new version.
RELEASES_URL = "https://github.com/Spyhawk00/qbt-plugin-installer/releases"

# Some Windows consoles default to cp1252 and choke on the box-drawing
# characters used in the output. Force UTF-8 where supported.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# ---------------------------------------------------------------------------
# nova3 framework files (required for any plugin to run)
# ---------------------------------------------------------------------------

# These files must live in nova3/ (the parent of nova3/engines/).
# Normally qBittorrent writes them itself on first run, but if that never
# happened the search system stays empty. They live in the main qBittorrent
# source tree, NOT in the search-plugins repo.
NOVA3_BASE = "https://raw.githubusercontent.com/qbittorrent/qBittorrent/master/src/searchengine/nova3/"
FRAMEWORK_FILES = [
    "nova2.py",
    "nova2dl.py",
    "novaprinter.py",
    "helpers.py",
    "socks.py",
]

# ---------------------------------------------------------------------------
# Plugin definitions
# ---------------------------------------------------------------------------

# Plugins fetched from remote URLs
REMOTE_PLUGINS: Dict[str, str] = {
    # Official qBittorrent repo
    "piratebay.py": (
        "https://raw.githubusercontent.com/qbittorrent/search-plugins"
        "/master/nova3/engines/piratebay.py"
    ),
    "torrentscsv.py": (
        "https://raw.githubusercontent.com/qbittorrent/search-plugins"
        "/master/nova3/engines/torrentscsv.py"
    ),
    "jackett.py": (
        "https://raw.githubusercontent.com/qbittorrent/search-plugins"
        "/master/nova3/engines/jackett.py"
    ),
    "limetorrents.py": (
        "https://raw.githubusercontent.com/qbittorrent/search-plugins"
        "/master/nova3/engines/limetorrents.py"
    ),
    # Community plugins
    "academictorrents.py": (
        "https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins"
        "/master/src/engines/academictorrents.py"
    ),
    "snowfl.py": (
        "https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins"
        "/master/src/engines/snowfl.py"
    ),
    # Anime / media
    "nyaasi.py": (
        "https://raw.githubusercontent.com/MadeOfMagicAndWires/qBit-plugins"
        "/main/engines/nyaasi.py"
    ),
    "subsplease.py": (
        "https://raw.githubusercontent.com/kli885/qBittorent-SubsPlease-Search-Plugin"
        "/main/subsplease.py"
    ),
}

# Plugins that live alongside this script (custom-written or patched)
def resource_dir() -> Path:
    """Directory holding bundled data files (qbt_plugins/).

    When packaged into a one-file .exe with PyInstaller, data files are
    unpacked to a temporary folder exposed as sys._MEIPASS. When run as a
    normal script, they sit next to this file.
    """
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled)
    return Path(__file__).parent


SCRIPT_DIR = resource_dir()
LOCAL_PLUGINS = [
    SCRIPT_DIR / "qbt_plugins" / "yts.py",
    SCRIPT_DIR / "qbt_plugins" / "fitgirl_repacks.py",  # WP REST API (hydralinks.cloud is Cloudflare-walled)
    SCRIPT_DIR / "qbt_plugins" / "therarbg.py",  # PATCHED: site layout change, bounded paging
    SCRIPT_DIR / "qbt_plugins" / "audiobookbay.py",  # PATCHED: live mirror, timeouts, bounded paging
    SCRIPT_DIR / "qbt_plugins" / "leetx.py",  # CUSTOM: 1337x via a mirror without the Cloudflare challenge
    SCRIPT_DIR / "qbt_plugins" / "knaben.py",  # CUSTOM: Knaben's JSON API (many sites at once)
]

# Not a search engine, so kept out of LOCAL_PLUGINS and every engine count:
# it adds an "Update available" result to searches once a newer release of
# this installer is out (see the file's header).
NOTICE_PLUGIN = SCRIPT_DIR / "qbt_plugins" / "installer_updates.py"

# Engines an earlier version of this installer put in place that have since
# died, or that are too slow to keep. Re-running the installer removes them,
# so the Search tab does not keep offering an engine that comes back empty or
# holds every search open. Each one is explained in the docstring at the top
# of this file.
RETIRED_PLUGINS = [
    "torrentgalaxy.py",
    "torrentdownload.py",
    "torlock.py",
    "torrentz2.py",
    "magnetdl.py",
    "dodi_repacks.py",
    "kickasstorrents.py",
    "zooqle.py",
    "bitsearch.py",
    "btdig.py",
    "glotorrents.py",
    "solidtorrents.py",
    "torrentproject.py",
    "eztv.py",  # official HTML scraper: eztvx.to is Cloudflare-challenged
    "tokyotoshokan.py",
    "rutor.py",  # works, but Russian-language: the installer ships English sites only
]


# ---------------------------------------------------------------------------
# Engine directory detection
# ---------------------------------------------------------------------------

def launched_by_double_click() -> bool:
    """True if we appear to own our console window (Windows double-click).

    When a console program is started from Explorer, its console closes the
    instant the process exits, so any output flashes by unread. We detect this
    by asking how many processes are attached to the console: just us means
    the window will vanish, so we should pause. Zero means there is no
    console at all (the windowed .exe run without one): nothing to keep open.
    """
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        arr = (ctypes.c_uint * 4)()
        count = ctypes.windll.kernel32.GetConsoleProcessList(arr, 4)
        return count == 1
    except Exception:
        return False


def pause_before_exit() -> None:
    """Keep the console window open until the user presses Enter."""
    try:
        input("\nPress Enter to close this window...")
    except (EOFError, KeyboardInterrupt, RuntimeError):  # RuntimeError: no stdin
        pass


class QbtLocation:
    """Where one qBittorrent install keeps the things this installer touches.

    engines_dir -- nova3/engines inside qBittorrent's DATA dir (plugins go here)
    ini         -- qBittorrent.ini in its CONFIG dir (the Search tab setting)
    exe         -- qbittorrent.exe, used to reopen it (None if not found)
    kind        -- "portable", "flatpak" or "standard": how it was found
    """

    def __init__(self, engines_dir: Path, ini: Optional[Path],
                 exe: Optional[str], kind: str) -> None:
        self.engines_dir = engines_dir
        self.ini = ini
        self.exe = exe
        self.kind = kind

    @property
    def has_run_before(self) -> bool:
        """qBittorrent creates nova3/ the first time its Search tab loads."""
        return self.engines_dir.parent.exists()


def _portable_location(exe: str) -> Optional[QbtLocation]:
    """A portable qBittorrent keeps everything in a `profile` folder beside
    its exe instead of the user profile."""
    root = Path(exe).parent / "profile"
    if not root.is_dir():
        return None
    base = root / "qBittorrent" if (root / "qBittorrent").is_dir() else root
    return QbtLocation(base / "data" / "nova3" / "engines",
                       base / "config" / "qBittorrent.ini", exe, "portable")


def locate_qbittorrent(engines_override: Optional[Path] = None) -> Optional[QbtLocation]:
    """Work out where qBittorrent keeps its plugins and settings.

    The running qBittorrent is asked first (it may be a portable copy), then
    the usual install locations. engines_override (--engines-dir) wins for
    the plugin folder; the settings file is still found normally.
    """
    system = platform.system()
    running = [p for p in qbittorrent_processes().values() if p]
    installed = find_qbittorrent()
    exes = running + ([installed] if installed and installed not in running else [])

    found: Optional[QbtLocation] = None
    for exe in exes:
        found = _portable_location(exe)
        if found:
            break

    if found is None and system == "Windows":
        # qBittorrent (4.2+) keeps its DATA dir — logs, nova3, BT_backup — in
        # %LOCALAPPDATA%\qBittorrent, while %APPDATA% (Roaming) holds only the
        # .ini config. The search engine reads nova3 from the DATA dir.
        # Plugins dropped in Roaming are silently ignored.
        local = os.environ.get("LOCALAPPDATA", "")
        appdata = os.environ.get("APPDATA", "")
        if local:
            found = QbtLocation(Path(local) / "qBittorrent" / "nova3" / "engines",
                                Path(appdata) / "qBittorrent" / "qBittorrent.ini" if appdata else None,
                                exes[0] if exes else None, "standard")
    elif found is None and system == "Darwin":
        home = Path.home()
        found = QbtLocation(
            home / "Library" / "Application Support" / "qBittorrent" / "nova3" / "engines",
            home / ".config" / "qBittorrent" / "qBittorrent.ini",
            exes[0] if exes else None, "standard")
    elif found is None:  # Linux / BSD
        home = Path.home()
        flatpak = home / ".var" / "app" / "org.qbittorrent.qBittorrent"
        if flatpak.is_dir():
            found = QbtLocation(flatpak / "data" / "qBittorrent" / "nova3" / "engines",
                                flatpak / "config" / "qBittorrent" / "qBittorrent.ini",
                                None, "flatpak")
        else:
            data = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
            config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
            found = QbtLocation(data / "qBittorrent" / "nova3" / "engines",
                                config / "qBittorrent" / "qBittorrent.ini",
                                exes[0] if exes else None, "standard")

    if found is not None and engines_override is not None:
        found.engines_dir = engines_override
    return found


def find_engines_dir() -> Optional[Path]:
    """Return the qBittorrent nova3/engines directory for this OS, or None."""
    location = locate_qbittorrent()
    return location.engines_dir if location else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_AGENT = f"Mozilla/5.0 (compatible; qbt-plugin-installer/{__version__})"

# WinINet error codes worth a readable message.
_WININET_ERRORS = {
    12002: "timed out",
    12007: "server name could not be resolved",
    12029: "could not connect to the server",
    12030: "connection was closed",
    12057: "certificate revocation check failed",
    12175: "secure connection failed",
}


def _wininet_get(url: str, timeout: float) -> bytes:
    """HTTPS GET through Windows' own WinINet.

    Used instead of urllib on Windows so the frozen .exe needn't carry
    Python's OpenSSL (about 6 MB of its size); it also honours the PC's proxy
    settings automatically.
    """
    import ctypes
    from ctypes import wintypes as wt
    wi = ctypes.WinDLL("wininet", use_last_error=True)
    HINTERNET = ctypes.c_void_p
    wi.InternetOpenW.restype = HINTERNET
    wi.InternetOpenW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD]
    wi.InternetOpenUrlW.restype = HINTERNET
    wi.InternetOpenUrlW.argtypes = [HINTERNET, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
                                    wt.DWORD, ctypes.c_size_t]
    wi.InternetSetOptionW.argtypes = [HINTERNET, wt.DWORD, ctypes.c_void_p, wt.DWORD]
    wi.HttpQueryInfoW.argtypes = [HINTERNET, wt.DWORD, ctypes.c_void_p,
                                  ctypes.POINTER(wt.DWORD), ctypes.POINTER(wt.DWORD)]
    wi.InternetReadFile.argtypes = [HINTERNET, ctypes.c_void_p, wt.DWORD,
                                    ctypes.POINTER(wt.DWORD)]
    wi.InternetCloseHandle.argtypes = [HINTERNET]

    def fail(what):
        code = ctypes.get_last_error()
        return OSError(f"{what}: {_WININET_ERRORS.get(code, f'WinINet error {code}')}")

    session = wi.InternetOpenW(USER_AGENT, 0, None, None, 0)  # PRECONFIG: system proxy
    if not session:
        raise fail("could not start a connection")
    request = None
    try:
        ms = wt.DWORD(int(timeout * 1000))
        for option in (2, 5, 6):  # CONNECT, SEND, RECEIVE timeouts
            wi.InternetSetOptionW(session, option, ctypes.byref(ms), ctypes.sizeof(ms))
        flags = (0x80000000    # RELOAD: never a cached copy
                 | 0x04000000  # NO_CACHE_WRITE: leave nothing in the IE cache
                 | 0x00080000  # NO_COOKIES
                 | 0x00000200)  # NO_UI
        request = wi.InternetOpenUrlW(session, url, None, 0, flags, 0)
        if not request:
            raise fail(url.split("/")[2] if "//" in url else url)

        status, size = wt.DWORD(0), wt.DWORD(ctypes.sizeof(wt.DWORD))
        if wi.HttpQueryInfoW(request, 19 | 0x20000000,  # STATUS_CODE | FLAG_NUMBER
                             ctypes.byref(status), ctypes.byref(size), None) \
                and status.value >= 400:
            raise OSError(f"HTTP Error {status.value}")

        chunks, buf, got = [], ctypes.create_string_buffer(65536), wt.DWORD(0)
        while True:
            if not wi.InternetReadFile(request, buf, len(buf), ctypes.byref(got)):
                raise fail("download interrupted")
            if got.value == 0:
                return b"".join(chunks)
            chunks.append(buf.raw[:got.value])
    finally:
        if request:
            wi.InternetCloseHandle(request)
        wi.InternetCloseHandle(session)


def newer_release(timeout: float = 5) -> Optional[str]:
    """The newest released version if it is newer than this one, else None.

    Reads the release tags from GitHub's releases feed (not the API, which
    limits unauthenticated calls). Any failure -- offline, no releases yet --
    is just None: this is a courtesy, never a reason to stop.
    """
    try:
        feed = http_get(RELEASES_URL + ".atom", timeout).decode("utf-8", "replace")
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    tags = re.findall(r'/releases/tag/v(\d+\.\d+\.\d+)"', feed)
    latest = max(tags, key=parse_version, default=None)
    if latest and parse_version(latest) > parse_version(__version__):
        return latest
    return None


def http_get(url: str, timeout: float = 15) -> bytes:
    """Fetch a URL: WinINet on Windows, urllib elsewhere."""
    if platform.system() == "Windows":
        return _wininet_get(url, timeout)
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download(url: str, dest: Path, force: bool, dry_run: bool,
             kind: str = "plugin") -> str:
    """Download url → dest. Returns status string.

    kind="plugin"    -> must contain a search class / prettyPrinter. An
                        installed copy is compared with upstream and replaced
                        when it differs, so re-running the installer brings
                        an older install up to date without --force.
    kind="framework" -> just needs to be plausible Python source. An
                        installed copy is left alone: qBittorrent writes
                        these itself to match its own version, and master
                        may not suit an older qBittorrent.
    """
    exists = dest.exists()
    if exists and not force and kind == "framework":
        return "SKIP  (already exists, use --force to overwrite)"

    if dry_run and not exists:
        return "DRY   would download"

    try:
        content = http_get(url, timeout=15)

        # Sanity check: must look like the right kind of Python source
        if kind == "plugin":
            if b"def search" not in content and b"prettyPrinter" not in content:
                raise ValueError("downloaded content doesn't look like a plugin")
        else:  # framework file: just verify it's non-trivial Python
            if len(content) < 50 or (b"import" not in content
                                     and b"def " not in content):
                raise ValueError("downloaded content doesn't look like Python")
    except Exception as exc:
        if exists:
            # Couldn't check for an update, but the installed copy still works.
            return f"SKIP  (kept installed copy; update check failed: {exc})"
        return f"FAIL  {exc}"

    if exists and not force:
        try:
            if dest.read_bytes() == content:
                return "SKIP  (already up to date)"
        except OSError:
            pass
    if dry_run:
        return "DRY   would update"

    try:
        dest.write_bytes(content)
    except OSError as exc:
        return f"FAIL  {exc}"
    return "OK    (updated)" if exists else "OK"


def copy_local(src: Path, dest: Path, force: bool, dry_run: bool) -> str:
    """Copy a local plugin file → dest. Returns status string."""
    if not src.exists():
        return f"FAIL  source not found: {src}"

    # Bundled plugins are the ones this project patches, so an installed copy
    # that differs is an older patch (or the broken upstream file it
    # replaced). Refresh it without needing --force, or re-running the
    # installer would never deliver a fix to someone who already has it.
    updating = False
    if dest.exists() and not force:
        try:
            if dest.read_bytes() == src.read_bytes():
                return "SKIP  (already up to date)"
        except OSError:
            pass
        updating = True

    if dry_run:
        return "DRY   would update" if updating else "DRY   would copy"

    try:
        shutil.copy2(src, dest)
    except OSError as exc:
        return f"FAIL  {exc}"
    return "OK    (updated)" if updating else "OK"


def retired_leftovers(engines_dir: Path, filename: str) -> List[Path]:
    """Every file a retired engine leaves behind, not just its .py:
    the favicon qBittorrent saves beside it (.ico/.png), files some plugins
    keep there (.json settings, .log), and Python's compiled copy in
    __pycache__. Found even when the .py itself was removed earlier."""
    stem = Path(filename).stem
    found = [engines_dir / (stem + ext) for ext in (".py", ".ico", ".png", ".json", ".log")]
    cache = engines_dir / "__pycache__"
    if cache.is_dir():
        found += sorted(cache.glob(f"{stem}.*.pyc"))
    return [f for f in found if f.is_file()]


def remove_retired(engines_dir: Path, dry_run: bool) -> List[str]:
    """Delete RETIRED_PLUGINS and their leftovers from engines_dir.
    Returns the engines that were still installed (their .py existed)."""
    removed, acted = [], False
    for filename in RETIRED_PLUGINS:
        leftovers = retired_leftovers(engines_dir, filename)
        if not leftovers:
            continue
        was_installed = (engines_dir / filename) in leftovers
        failed = None
        if not dry_run:
            for path in leftovers:
                try:
                    path.unlink()
                except OSError as exc:
                    failed = exc
        acted = True
        if failed:
            print(f"  {filename:<30} FAIL  {failed}")
            continue
        if was_installed:
            removed.append(filename)
        what = "removed" if was_installed else f"{len(leftovers)} leftover file(s) cleaned"
        print(f"  {filename:<30} {'DRY   would be ' + what if dry_run else ('REMOVED' if was_installed else 'OK    ' + what)}")
    if not acted:
        print(f"  {'none installed':<30} OK")
    return removed


# ---------------------------------------------------------------------------
# Dependency checks / auto-install
# ---------------------------------------------------------------------------

MIN_PYTHON = (3, 9)  # nova3 framework + modern plugins require >= 3.9

# Real third-party packages that qBittorrent search plugins are known to use,
# mapped import-name -> pip-package-name. We ONLY auto-install from this
# allowlist. Plugins commonly contain optional or Python-2 fallback imports
# (e.g. `HTMLParser`, `settings_gui`, `StringIO`) wrapped in try/except — those
# are NOT real dependencies and must never be sent to pip.
KNOWN_THIRD_PARTY = {
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "cloudscraper": "cloudscraper",
    "cfscrape": "cfscrape",
    "lxml": "lxml",
    "Crypto": "pycryptodome",
    "yaml": "PyYAML",
}


def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    # CREATE_NO_WINDOW: in the windowed GUI build, each console helper
    # (tasklist, py, pip) would otherwise flash up its own black window.
    flags = 0x08000000 if platform.system() == "Windows" else 0
    return subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)


def _registry_qbittorrent() -> List[str]:
    """qbittorrent.exe paths the Windows installer registered."""
    try:
        import winreg
    except ImportError:
        return []
    found = []
    lookups = [
        (r"Software\Microsoft\Windows\CurrentVersion\App Paths\qbittorrent.exe", ""),
        (r"Software\Microsoft\Windows\CurrentVersion\Uninstall\qBittorrent", "DisplayIcon"),
        (r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\qBittorrent", "DisplayIcon"),
        (r"Software\qBittorrent", "InstallLocation"),
    ]
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for subkey, value in lookups:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    raw = str(winreg.QueryValueEx(key, value)[0])
            except OSError:
                continue
            path = Path(raw.split(",")[0].strip().strip('"'))  # "x.exe",0 icon form
            if path.is_dir():
                path = path / "qbittorrent.exe"
            found.append(str(path))
    return found


def find_qbittorrent() -> Optional[str]:
    """Best-effort locate the qBittorrent executable."""
    exe = shutil.which("qbittorrent") or shutil.which("qbittorrent-nox")
    if exe:
        return exe
    if platform.system() == "Windows":
        candidates = _registry_qbittorrent()
        for base in (os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                     os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                     os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
            candidates.append(str(Path(base) / "qBittorrent" / "qbittorrent.exe"))
        for cand in candidates:
            if Path(cand).is_file():
                return cand
    elif platform.system() == "Darwin":
        cand = Path("/Applications/qBittorrent.app/Contents/MacOS/qbittorrent")
        if cand.exists():
            return str(cand)
    return None


def _python_is_usable(cmd: List[str]) -> bool:
    """True if `cmd` runs a Python at least MIN_PYTHON."""
    check = f"import sys; sys.exit(0 if sys.version_info[:2] >= {MIN_PYTHON} else 1)"
    try:
        return _run(cmd + ["-c", check]).returncode == 0
    except OSError:
        return False


def _registered_pythons() -> List[str]:
    """python.exe paths registered under PEP 514 -- where qBittorrent looks.

    A Python installed a moment ago by install_python() is in the registry but
    not yet on this process's PATH, so it must be found this way.
    """
    try:
        import winreg
    except ImportError:
        return []
    found = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            core = winreg.OpenKey(hive, r"Software\Python\PythonCore")
        except OSError:
            continue
        with core:
            i = 0
            while True:
                try:
                    tag = winreg.EnumKey(core, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(core, tag + r"\InstallPath") as key:
                        try:
                            exe = winreg.QueryValueEx(key, "ExecutablePath")[0]
                        except OSError:
                            exe = str(Path(winreg.QueryValueEx(key, "")[0]) / "python.exe")
                    found.append(exe)
                except OSError:
                    continue
    # Newest first, so qBittorrent and this installer agree on the same one.
    return sorted(set(found), reverse=True)


def find_system_python() -> Optional[str]:
    """Locate a real system Python that qBittorrent could use for search.

    qBittorrent's search runs plugins under a system Python interpreter, so one
    must exist even after the plugin files are copied. This is independent of
    the interpreter running THIS installer (which, when frozen into an .exe,
    bundles its own private Python).
    """
    if platform.system() == "Windows":
        # The py launcher (python.org) is the most reliable signal.
        launcher = shutil.which("py")
        if launcher and _python_is_usable([launcher, "-3"]):
            return launcher
        for exe in _registered_pythons():
            if Path(exe).exists() and _python_is_usable([exe]):
                return exe

    exe = shutil.which("python") or shutil.which("python3")
    if exe and "WindowsApps" not in exe:  # skip the non-functional Store stub
        if _python_is_usable([exe]):
            return exe
    return None


# Installed silently when no usable Python is found. Pinned to one release and
# its SHA-256, so a corrupted or substituted download is refused before it
# runs. The file is also Authenticode-signed by the Python Software
# Foundation. Per-user install: no administrator prompt.
PYTHON_INSTALLER = {
    "version": "3.13.16",
    "url": "https://www.python.org/ftp/python/3.13.16/python-3.13.16-amd64.exe",
    "sha256": "fb4f9f5d438b2396da0086dc70b935c530cb578e37adc6d354f7ad2037fee83b",
}
PYTHON_INSTALL_ARGS = [
    "/quiet",
    "InstallAllUsers=0",          # per-user: no UAC prompt
    "InstallLauncherAllUsers=0",  # the py launcher too, or it asks for admin
    "Include_launcher=1",
    "PrependPath=1",
    "Include_test=0",
    "Include_doc=0",
    "Shortcuts=0",
]


def install_python(dry_run: bool) -> Optional[str]:
    """Download and silently install Python. Returns the new interpreter."""
    version = PYTHON_INSTALLER["version"]
    if platform.system() != "Windows" or platform.machine().lower() not in ("amd64", "x86_64"):
        offer_install_python()
        return None
    if dry_run:
        print(f"    DRY   would download and silently install Python {version}")
        return None

    print(f"    Installing Python {version} (about 30 MB, one minute) ...")
    import hashlib
    import tempfile
    try:
        data = http_get(PYTHON_INSTALLER["url"], timeout=120)
    except Exception as exc:
        print(f"    FAIL  download: {exc}")
        offer_install_python()
        return None
    if hashlib.sha256(data).hexdigest() != PYTHON_INSTALLER["sha256"]:
        print("    FAIL  the download did not match the expected checksum; not running it.")
        offer_install_python()
        return None

    # The installer and its setup logs go in one private folder that is
    # deleted afterwards. Without /log, the Python setup leaves a set of
    # "Python 3.x (64-bit)_*.log" files in %TEMP% on every run.
    work = Path(tempfile.mkdtemp(prefix="qbt-plugin-installer-"))
    setup = work / f"python-{version}-amd64.exe"
    log = work / "python-setup.log"
    try:
        setup.write_bytes(data)
        rc = subprocess.run([str(setup)] + PYTHON_INSTALL_ARGS + ["/log", str(log)],
                            timeout=900).returncode
        if rc not in (0, 3010):
            # Keep the reason in our own log before the folder goes.
            for setup_log in sorted(work.glob("*.log"))[:1]:
                tail = setup_log.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]
                for line in tail:
                    print(f"    | {line}")
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"    FAIL  installer: {exc}")
        offer_install_python()
        return None
    finally:
        shutil.rmtree(work, ignore_errors=True)
    # 3010 = success, reboot recommended (not needed for qBittorrent's use).
    if rc not in (0, 3010):
        print(f"    FAIL  Python installer exited with code {rc}")
        offer_install_python()
        return None

    exe = find_system_python()
    if exe:
        print(f"    OK    Python {version} installed")
    else:
        print("    FAIL  Python installed but could not be found afterwards")
    return exe


def offer_install_python() -> None:
    """Tell the user how to install Python by hand (when automatic install can't)."""
    print("    qBittorrent's search needs Python installed to run the plugins.")
    print("    Download it from https://www.python.org/downloads/")
    print("    (tick \"Add python.exe to PATH\" during setup), then run this again.")


def ensure_pip() -> bool:
    """Return True if pip is usable, bootstrapping it via ensurepip if needed."""
    if _run([sys.executable, "-m", "pip", "--version"]).returncode == 0:
        return True
    _run([sys.executable, "-m", "ensurepip", "--upgrade"])
    return _run([sys.executable, "-m", "pip", "--version"]).returncode == 0


def python3_is_store_stub() -> bool:
    """On Windows, detect the Microsoft Store python3 alias (a non-functional
    redirect that breaks naive `python3` calls)."""
    p = shutil.which("python3")
    return bool(p and "WindowsApps" in p)


def preflight() -> bool:
    """Check core dependencies, changing nothing.

    Returns True if a usable system Python is missing (so one needs
    installing). Nothing here is fatal: plugins are still copied, so search
    works the moment Python is there.
    """
    print("── Preflight: dependencies ──────────────────────────────")
    frozen = getattr(sys, "frozen", False)
    v = sys.version_info
    need_python = False

    if frozen:
        # Running as a packaged .exe: our interpreter is bundled, so what
        # matters is whether qBittorrent will find a SYSTEM Python for search.
        if find_system_python():
            print(f"  {'Python (system)':<30} OK")
        else:
            print(f"  {'Python (system)':<30} NOT FOUND")
            need_python = True
    elif v[:2] >= MIN_PYTHON:
        print(f"  {'Python ' + '.'.join(map(str, v[:3])):<30} OK")
    elif find_system_python():
        # This script runs on an old Python, but a newer one qBittorrent
        # can use is installed too.
        print(f"  {'Python (system)':<30} OK")
    else:
        print(f"  {'Python ' + '.'.join(map(str, v[:3])):<30} TOO OLD "
              f"(need >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")
        need_python = True

    # pip only matters for auto-installing third-party plugin packages, which
    # runs against this interpreter. When frozen into an .exe that interpreter
    # is our private bundle (not the system Python), so the check is irrelevant
    # and its failure would needlessly alarm the user — skip it.
    if not frozen:
        if ensure_pip():
            print(f"  {'pip':<30} OK")
        else:
            print(f"  {'pip':<30} MISSING (could not bootstrap via ensurepip)")
            # Not fatal: plugins are stdlib-only today, pip only needed if a
            # future plugin pulls a third-party package.

    qbt = find_qbittorrent()
    if qbt:
        print(f"  {'qBittorrent':<30} OK")
    else:
        print(f"  {'qBittorrent':<30} NOT FOUND")
        print("    Plugins will still be copied, but install qBittorrent to use them.")

    if platform.system() == "Windows" and python3_is_store_stub():
        print(f"  {'python3 alias':<30} Microsoft Store stub (informational)")
        print("    qBittorrent finds the real Python via the registry, so this is")
        print("    usually harmless. If search misbehaves, turn off the alias under")
        print("    Settings > Apps > Advanced app settings > App execution aliases.")

    print()
    return need_python


# ---------------------------------------------------------------------------
# qBittorrent: close / reopen, and the Search tab setting
# ---------------------------------------------------------------------------

def qbittorrent_processes() -> Dict[int, str]:
    """Running qBittorrent processes on Windows, as {pid: exe path}."""
    if platform.system() != "Windows":
        return {}
    try:
        out = _run(["tasklist", "/FI", "IMAGENAME eq qbittorrent.exe",
                    "/FO", "CSV", "/NH"]).stdout
    except OSError:
        return {}
    procs: Dict[int, str] = {}
    import ctypes
    import ctypes.wintypes as wt
    kernel32 = ctypes.windll.kernel32
    for line in out.splitlines():
        fields = line.strip().strip('"').split('","')
        if len(fields) < 2 or fields[0].lower() != "qbittorrent.exe":
            continue
        try:
            pid = int(fields[1])
        except ValueError:
            continue
        path = ""
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if handle:
            buf = ctypes.create_unicode_buffer(32768)
            size = wt.DWORD(len(buf))
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                path = buf.value
            kernel32.CloseHandle(handle)
        procs[pid] = path
    return procs


def close_qbittorrent(pids: List[int], timeout: float = 30) -> bool:
    """Ask qBittorrent to quit cleanly. Returns True once it has exited.

    A plain close request only hides it in the tray. Instead send the
    messages Windows sends at shutdown/restart (WM_QUERYENDSESSION and
    WM_ENDSESSION with ENDSESSION_CLOSEAPP): qBittorrent then saves resume
    data and exits exactly as if Exit were chosen from the tray. It is never
    force-killed; if it doesn't exit, the caller tells the user what to do.
    """
    import ctypes
    import ctypes.wintypes as wt
    import time
    user32 = ctypes.windll.user32
    wanted = set(pids)
    windows = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def collect(hwnd, _):
        owner = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value in wanted:
            windows.append(hwnd)
        return True

    user32.EnumWindows(collect, 0)
    result = wt.DWORD()
    ENDSESSION_CLOSEAPP, SMTO_ABORTIFHUNG = 0x1, 0x2
    for message, wparam in ((0x0011, 0), (0x0016, 1)):  # QUERYENDSESSION, ENDSESSION
        for hwnd in windows:
            user32.SendMessageTimeoutW(hwnd, message, wparam, ENDSESSION_CLOSEAPP,
                                       SMTO_ABORTIFHUNG, 5000, ctypes.byref(result))

    deadline = time.time() + timeout
    while time.time() < deadline:
        if not wanted & set(qbittorrent_processes()):
            return True
        time.sleep(0.5)
    return False


def launch_qbittorrent(exe: str) -> bool:
    """Start qBittorrent detached from this console window."""
    try:
        subprocess.Popen([exe], close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         creationflags=0x00000008 | 0x00000200)  # DETACHED | NEW_GROUP
        return True
    except OSError:
        return False


def enable_search_tab(ini: Path, dry_run: bool) -> str:
    """Turn on View > Search Engine, which qBittorrent hides by default.

    Must only run while qBittorrent is closed: it rewrites this file on exit
    and would undo the change. Edited line by line, not with configparser,
    which would rewrite qBittorrent's own escaping and key case.
    """
    key, on = "Search\\SearchEnabled", "Search\\SearchEnabled=true"
    try:
        lines = ini.read_text(encoding="utf-8").splitlines() if ini.exists() else []
    except OSError as exc:
        return f"FAIL  {exc}"

    section, insert_at = None, None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped
            if section == "[Preferences]":
                insert_at = i + 1
            continue
        if section == "[Preferences]" and stripped.split("=", 1)[0] == key:
            if stripped == on:
                return "SKIP  (already on)"
            lines[i] = on
            break
    else:
        if insert_at is None:
            lines += (["", "[Preferences]", on] if lines else ["[Preferences]", on])
        else:
            lines.insert(insert_at, on)

    if dry_run:
        return "DRY   would turn on"
    try:
        ini.parent.mkdir(parents=True, exist_ok=True)
        ini.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        return f"FAIL  {exc}"
    return "OK"


def confirm_plan(steps: List[str], assume_yes: bool) -> bool:
    """Tell the user what is about to happen, and wait for them to agree."""
    print("── Before we start ──────────────────────────────────────")
    print("  This installer will:")
    for step in steps:
        print(f"    • {step}")
    print()
    if assume_yes:
        print("  Continuing (--yes).")
        print()
        return True
    try:
        input("  Press Enter to continue, or close this window to cancel. ")
    except (EOFError, KeyboardInterrupt):
        print()
        print("  Cancelled — nothing was changed. (Use --yes to run without asking.)")
        return False
    print()
    return True


def scan_imports(py_files: List[Path]) -> Set[str]:
    """Return the set of top-level modules imported by the given .py files."""
    mods: Set[str] = set()
    for f in py_files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    mods.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
    return mods


def plugin_python() -> Optional[List[str]]:
    """Command prefix for the Python that qBittorrent runs plugins under.

    Unfrozen, that is the interpreter running this script. Frozen into the
    .exe, sys.executable is the installer itself, so `sys.executable -m pip`
    would re-launch the installer -- use the system Python instead.
    """
    if not getattr(sys, "frozen", False):
        return [sys.executable]
    exe = find_system_python()
    if exe is None:
        return None
    return [exe, "-3"] if Path(exe).stem.lower() == "py" else [exe]


def sys_python_lacks(python: List[str], mod: str) -> bool:
    """True if `mod` is not importable under the given Python."""
    check = ("import importlib.util, sys; "
             "sys.exit(importlib.util.find_spec(sys.argv[1]) is None)")
    return _run(python + ["-c", check, mod]).returncode != 0


def install_plugin_dependencies(engines_dir: Path, dry_run: bool) -> None:
    """Scan installed plugins and pip-install any required third-party package.

    Only packages on the KNOWN_THIRD_PARTY allowlist are considered, so optional
    / Python-2 fallback imports inside plugins are never mistaken for real
    dependencies. A package is installed only if it isn't already importable.
    """
    print("── Plugin Python packages ───────────────────────────────")
    py_files = sorted(p for p in engines_dir.glob("*.py") if p.name != "__init__.py")
    needed = scan_imports(py_files) & set(KNOWN_THIRD_PARTY)

    if not needed:
        print(f"  {'no third-party packages required':<30} OK")
        print()
        return

    python = plugin_python()
    if python is None:
        print(f"  {'system Python not found':<30} SKIP  install Python, then re-run")
        print()
        return

    missing: Set[str] = set()
    for mod in needed:
        if sys_python_lacks(python, mod):
            missing.add(mod)

    if not missing:
        print(f"  {'third-party packages':<30} OK")
        print()
        return

    for mod in sorted(missing):
        pkg = KNOWN_THIRD_PARTY[mod]
        if dry_run:
            print(f"  {mod:<30} DRY  would: pip install {pkg}")
            continue
        print(f"  {mod:<30} installing {pkg} ...")
        r = _run(python + ["-m", "pip", "install", "--user", pkg])
        if r.returncode == 0:
            print(f"  {mod:<30} OK")
        else:
            tail = (r.stderr.strip().splitlines() or ["pip error"])[-1]
            print(f"  {mod:<30} FAIL  {tail}")
    print()


# ---------------------------------------------------------------------------
# Install record (which installer version last ran on this engines dir)
# ---------------------------------------------------------------------------

# Written next to the plugins after a successful install. qBittorrent only
# loads *.py from engines/, and plugins already keep their own .json there
# (jackett.json, for one), so this file is invisible to the Search tab.
# Installs made before 1.2.0 have no record.
INSTALL_RECORD = "qbt-plugin-installer.json"


def parse_version(text: str) -> Optional[Tuple[int, ...]]:
    """'1.2.0' -> (1, 2, 0); None if it isn't a plain dotted version."""
    try:
        return tuple(int(part) for part in text.strip().lstrip("v").split("."))
    except (AttributeError, ValueError):
        return None


def read_install_record(engines_dir: Path) -> Optional[dict]:
    try:
        data = json.loads((engines_dir / INSTALL_RECORD).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def write_install_record(engines_dir: Path, plugins: List[str]) -> None:
    record = {
        "version": __version__,
        "installed": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plugins": sorted(plugins),
    }
    try:
        (engines_dir / INSTALL_RECORD).write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"  (could not save install record: {exc})")


def check_previous_install(engines_dir: Path, force: bool, dry_run: bool) -> bool:
    """Say what this run is upgrading from. Returns False to refuse a downgrade.

    An older installer over a newer install would put back engines the newer
    one retired and overwrite its patched plugins with older code, so it is
    refused unless --force. A dry run only previews, so it is allowed.
    """
    record = read_install_record(engines_dir)
    has_plugins = engines_dir.exists() and any(
        p.name != "__init__.py" for p in engines_dir.glob("*.py"))

    if record is None:
        if has_plugins:
            print("Previous install: an older version (before 1.2.0) — it will be upgraded.")
        return True

    previous = str(record.get("version", "?"))
    old, new = parse_version(previous), parse_version(__version__)
    if old is None or old < new:
        print(f"Previous install: v{previous} — upgrading to v{__version__}.")
        return True
    if old == new:
        print(f"Previous install: v{previous} — already installed. Refreshing the engines.")
        return True

    print(f"These plugins were installed by a NEWER installer, v{previous}.")
    print(f"This one is v{__version__}: running it would bring back engines that")
    print(f"v{previous} removed as dead or slow, and replace its fixes with older code.")
    if force or dry_run:
        print("Continuing anyway" + (" (--force)." if force else " (dry run, nothing changes)."))
        return True
    print("Get the latest installer instead, or pass --force to downgrade anyway.")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

class Options:
    """What to do. Built from the command line, or by the GUI."""

    def __init__(self, dry_run: bool = False, force: bool = False,
                 engines_dir: Optional[Path] = None, skip_deps: bool = False,
                 yes: bool = False, no_restart: bool = False) -> None:
        self.dry_run = dry_run
        self.force = force
        self.engines_dir = engines_dir
        self.skip_deps = skip_deps
        self.yes = yes
        self.no_restart = no_restart


class Outcome:
    """How a run ended, for the command line's exit code and the GUI."""

    def __init__(self) -> None:
        self.exit_code = 0
        self.cancelled = False
        self.error = ""            # set when the run stopped early
        self.installed = 0
        self.skipped = 0
        self.removed = 0
        self.failed = 0
        self.python_ok = True
        self.reopened = False
        self.needs_restart = False  # qBittorrent still running the old plugins
        self.engines_dir: Optional[Path] = None


def disruptive_steps(need_python: bool, running: bool) -> List[str]:
    """The steps the user must hear about before they happen."""
    steps = []
    if need_python:
        steps.append(f"Download and install Python {PYTHON_INSTALLER['version']} "
                     "from python.org. qBittorrent needs it to run search "
                     "plugins. (No administrator prompt.)")
    if running:
        steps.append("Close qBittorrent and reopen it when done. It saves your "
                     "torrents first, exactly like choosing Exit, so nothing "
                     "is lost; downloads pause for a few seconds.")
    return steps


def _noop_step(key: str, state: str) -> None:
    pass


def run_install(opts: Options,
                confirm: Callable[[List[str]], bool],
                step: Callable[[str, str], None] = _noop_step) -> Outcome:
    """Do the whole install. Prints a detailed log as it goes.

    confirm(steps) is called with the disruptive steps (installing Python,
    closing qBittorrent) before any of them happen; returning False cancels
    with nothing changed. step(key, state) reports progress for the GUI:
    key is one of "python", "close", "plugins", "search", "reopen" and state
    one of "running", "done", "skipped", "failed".
    """
    out = Outcome()
    print(f"qBittorrent Search Plugin Installer v{__version__}")
    print()

    # Dependency preflight — only checks; nothing is installed until the user
    # has been told what will happen.
    need_python = preflight() if not opts.skip_deps else False

    location = locate_qbittorrent(opts.engines_dir)
    if location is None:
        print("ERROR: Could not detect qBittorrent engines directory.")
        print("       Use --engines-dir /path/to/engines to specify it manually.")
        out.exit_code, out.error = 1, "Could not find qBittorrent's plugin folder."
        return out
    engines_dir = out.engines_dir = location.engines_dir
    print(f"Engines dir: {engines_dir}" + (f"  ({location.kind} install)"
                                          if location.kind != "standard" else ""))
    if location.ini:
        print(f"Settings:    {location.ini}")

    if not check_previous_install(engines_dir, opts.force, opts.dry_run):
        out.exit_code = 1
        out.error = ("These plugins were installed by a newer version of this "
                     "installer. Get the latest installer instead.")
        return out
    print()

    # qBittorrent has to be closed while the Search tab setting is written
    # (it rewrites its settings on exit) and restarted to load new plugins.
    running = {} if opts.no_restart else qbittorrent_processes()

    # Say what is about to happen before doing anything disruptive, and wait
    # for the user to agree. Copying plugin files alone needs no warning.
    disruptive = disruptive_steps(need_python, bool(running))
    if disruptive:
        if opts.dry_run:
            print("── Before we start ──────────────────────────────────────")
            print("  A real run would first ask before it:")
            for line in disruptive:
                print(f"    • {line}")
            print()
        elif not confirm(disruptive + ["Install or update the search plugins.",
                                       "Turn on qBittorrent's Search tab."]):
            out.cancelled = True
            return out

    if need_python:
        print("── Python ───────────────────────────────────────────────")
        step("python", "running")
        out.python_ok = install_python(opts.dry_run) is not None
        step("python", "done" if out.python_ok or opts.dry_run else "failed")
        print()
    else:
        step("python", "skipped")

    closed = False
    if running and not opts.dry_run:
        print("── Closing qBittorrent ──────────────────────────────────")
        step("close", "running")
        closed = close_qbittorrent(list(running))
        if closed:
            print(f"  {'qBittorrent':<30} OK    (closed cleanly; will reopen)")
        else:
            print(f"  {'qBittorrent':<30} still running — continuing; restart it at the end")
        step("close", "done" if closed else "failed")
        print()
    else:
        step("close", "skipped")

    step("plugins", "running")
    if not engines_dir.exists():
        if opts.dry_run:
            print(f"DRY   would create: {engines_dir}")
        else:
            print(f"Creating: {engines_dir}")
            engines_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Framework files (nova3/ parent directory)
    nova3_dir = engines_dir.parent
    print("── nova3 framework files ────────────────────────────────")
    framework_missing = 0
    for fname in FRAMEWORK_FILES:
        url = NOVA3_BASE + fname
        dest = nova3_dir / fname
        status = download(url, dest, opts.force, opts.dry_run, kind="framework")
        # A framework file only matters if it is absent at the end. With
        # --force while qBittorrent is running, the write is refused with
        # "Permission denied" because qBittorrent holds these files open --
        # and the copy already on disk is the one we would have written.
        # That is not a failure; a missing file is, because then no plugin
        # can run at all.
        if status.startswith("FAIL") and dest.exists():
            status = "KEEP  (in use by qBittorrent; existing copy is fine)"
        elif status.startswith("FAIL"):
            framework_missing += 1
        print(f"  {fname:<30} {status}")
    print()

    # Remote plugins
    print("── Remote plugins ──────────────────────────────────────")
    for filename, url in REMOTE_PLUGINS.items():
        dest = engines_dir / filename
        status = download(url, dest, opts.force, opts.dry_run)
        results[filename] = status
        print(f"  {filename:<30} {status}")

    print()

    # Local/custom plugins
    print("── Custom plugins (local) ───────────────────────────────")
    for src in LOCAL_PLUGINS:
        dest = engines_dir / src.name
        status = copy_local(src, dest, opts.force, opts.dry_run)
        results[src.name] = status
        print(f"  {src.name:<30} {status}")
    # The update notice: installed like a plugin but not counted as an
    # engine, and a failure here doesn't fail the install.
    notice = copy_local(NOTICE_PLUGIN, engines_dir / NOTICE_PLUGIN.name, opts.force, opts.dry_run)
    print(f"  {NOTICE_PLUGIN.name:<30} {notice}")

    print()

    # Dead engines left behind by earlier versions of this installer
    print("── Retired plugins ─────────────────────────────────────")
    retired = remove_retired(engines_dir, opts.dry_run)
    print()

    # Auto-install any third-party Python packages the plugins need.
    if not opts.skip_deps:
        install_plugin_dependencies(engines_dir, opts.dry_run)

    ok    = sum(1 for s in results.values() if s.startswith("OK"))
    skip  = sum(1 for s in results.values() if s.startswith("SKIP"))
    dry   = sum(1 for s in results.values() if s.startswith("DRY"))
    fail  = sum(1 for s in results.values() if s.startswith("FAIL")) + framework_missing
    step("plugins", "failed" if fail else "done")

    # The Search tab, then reopen qBittorrent if we closed it.
    print("── qBittorrent ──────────────────────────────────────────")
    step("search", "running")
    still_running = bool(qbittorrent_processes()) if not opts.dry_run else bool(running)
    if location.ini is None:
        search_status = "SKIP  (settings file location unknown)"
    elif still_running and not opts.dry_run:
        search_status = "SKIP  (qBittorrent is running; turn on View > Search Engine)"
    else:
        search_status = enable_search_tab(location.ini, opts.dry_run)
    print(f"  {'Search tab':<30} {search_status}")
    step("search", "failed" if search_status.startswith("FAIL")
         or "running" in search_status else "done")

    if closed:
        step("reopen", "running")
        exe = next((p for p in running.values() if p), None) or location.exe or find_qbittorrent()
        out.reopened = bool(exe) and launch_qbittorrent(exe)
        print(f"  {'qBittorrent':<30} {'OK    (reopened)' if out.reopened else 'FAIL  could not reopen it'}")
        step("reopen", "done" if out.reopened else "failed")
    else:
        if running and opts.dry_run:
            print(f"  {'qBittorrent':<30} DRY   would close and reopen")
        step("reopen", "skipped")
    print()

    # Record the version only for a complete install, so a partial one is
    # never mistaken for an up-to-date one next time.
    if not opts.dry_run and not fail:
        installed = [name for name, s in results.items() if not s.startswith("FAIL")]
        write_install_record(engines_dir, installed)

    out.installed, out.skipped, out.removed, out.failed = ok, skip, len(retired), fail
    out.needs_restart = not out.reopened and bool(running or still_running)
    out.exit_code = 1 if fail else 0

    print("── Summary ─────────────────────────────────────────────")
    if framework_missing:
        print(f"  {framework_missing} nova3 framework file(s) are missing. qBittorrent's")
        print("  search cannot run any plugin without them. Check your network,")
        print("  then run this installer again.")
    if opts.dry_run:
        print(f"  Would install: {dry + ok}   Already present: {skip}   "
              f"Would remove: {len(retired)}   Errors: {fail}")
        print()
        print("  Run without --dry-run to apply.")
    else:
        print(f"  Installed: {ok}   Skipped: {skip}   Removed: {len(retired)}   Failed: {fail}")
        if not fail:
            print(f"  Plugins are now at installer version v{__version__}.")
        print()
        if not out.python_ok:
            print("  Search will not work until Python is installed (see above).")
            print("  Install it, then run this installer again.")
        elif out.reopened:
            print("  ALL DONE — qBittorrent has been reopened. Open its Search tab")
            print("  to use the new search engines.")
        elif out.needs_restart:
            print("  ALMOST DONE — restart qBittorrent so it loads the new engines:")
            print("    1. Right-click the qBittorrent icon in the system tray")
            print("       (bottom-right, near the clock) and choose Exit.")
            print("       Closing the window is NOT enough — it hides in the tray.")
            print("    2. Reopen qBittorrent and open the Search tab.")
        else:
            print("  ALL DONE — open qBittorrent and go to the Search tab.")
    print()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"Install qBittorrent search plugins (v{__version__})."
    )
    parser.add_argument(
        "--version", action="version", version=f"qbt-plugin-installer {__version__}"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be installed without making any changes."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Rewrite every file even if unchanged, including the nova3 "
             "framework files (plugins update without this)."
    )
    parser.add_argument(
        "--engines-dir", type=Path, default=None,
        help="Override the engines directory path."
    )
    parser.add_argument(
        "--skip-deps", action="store_true",
        help="Skip the dependency preflight and auto-install steps."
    )
    parser.add_argument(
        "--pause", action="store_true",
        help="Wait for the user to press Enter before exiting (used by the "
             "double-click launchers so the window stays open)."
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Don't ask before installing Python or closing qBittorrent."
    )
    parser.add_argument(
        "--no-restart", action="store_true",
        help="Leave a running qBittorrent alone (restart it yourself afterwards)."
    )
    args = parser.parse_args()

    # Keep the window open if asked (by the launchers) or if we were started by
    # double-clicking in Explorer. atexit ensures this runs even on early exits.
    if args.pause or launched_by_double_click():
        atexit.register(pause_before_exit)

    opts = Options(dry_run=args.dry_run, force=args.force,
                   engines_dir=args.engines_dir, skip_deps=args.skip_deps,
                   yes=args.yes, no_restart=args.no_restart)
    outcome = run_install(opts, confirm=lambda steps: confirm_plan(steps, args.yes))
    # Here, not in run_install(): the GUI checks on its own thread, and an
    # offline lookup can take ~10 s that an install shouldn't wait for.
    newer = newer_release()
    if newer:
        print(f"\nA newer version of this installer, v{newer}, is out: {RELEASES_URL}/latest")
    sys.exit(outcome.exit_code)


if __name__ == "__main__":
    main()
