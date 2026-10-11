# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller build for qbt-plugin-installer-<version>.exe (the GUI, windowed,
# one file). The version comes from __version__ in install_qbt_plugins.py.
# Build with:  python -m PyInstaller --noconfirm qbt-plugin-installer.spec
#
# The program itself is ~100 KB; nearly all of the .exe is the Python runtime
# and Tcl/Tk it carries. This spec leaves out what the installer never uses:
#
#  * OpenSSL (~6 MB unpacked). Downloads go through Windows' own WinINet
#    (install_qbt_plugins.http_get), so ssl/_ssl/_hashlib are not needed;
#    hashlib falls back to Python's built-in SHA-256.
#  * Tcl's time-zone database, Asian multi-byte encodings, and the Tcl/Tk
#    message catalogues and demo images (~4 MB). The GUI never formats
#    clock times, Tk renders Unicode natively, and Windows draws the
#    message boxes and file dialog itself.
#  * Standard-library modules nothing imports at run time.
#
# After changing the code, rebuild and re-test the .exe end to end: a module
# excluded here that the code starts importing fails only in the frozen
# build. UPX is deliberately off: antivirus tools often flag UPX-packed exes.

import os
import re

# Read, not imported: the version is the only thing the build needs from it.
with open(os.path.join(SPECPATH, "install_qbt_plugins.py"), encoding="utf-8") as f:
    VERSION = re.search(r'^__version__ = "([^"]+)"', f.read(), re.M).group(1)

EXCLUDES = [
    # TLS and OpenSSL-backed hashing (WinINet does HTTPS)
    "ssl", "_ssl", "_hashlib",
    # compression and maths the installer never uses
    "bz2", "_bz2", "lzma", "_lzma", "compression", "_zstd",
    "decimal", "_decimal",
    # (unicodedata stays: traceback needs it to format errors on lines with
    # non-ASCII characters, i.e. the "Something went wrong" screen)
    # development / interactive tooling
    "unittest", "doctest", "pdb", "pydoc", "pydoc_data", "idlelib",
    "turtle", "turtledemo", "tkinter.tix", "lib2to3", "ensurepip", "venv",
    # whole subsystems not used
    "asyncio", "multiprocessing", "concurrent", "sqlite3", "_sqlite3",
    "xmlrpc", "curses", "_curses", "dbm", "wsgiref", "http.server",
]

# Single-byte system code pages Tcl may be asked for on a Western, Central
# European, Cyrillic, Greek, Turkish, Hebrew, Arabic, Baltic or Vietnamese
# Windows. utf-8 is built into Tcl.
KEEP_ENCODINGS = ("ascii", "cp1250", "cp1251", "cp1252", "cp1253", "cp1254",
                  "cp1255", "cp1256", "cp1257", "cp1258", "cp437", "cp850",
                  "cp852", "cp866", "iso8859-", "koi8-")


def keep_data(dest: str) -> bool:
    d = dest.replace("\\", "/")
    if d.startswith("_tcl_data/tzdata/") or "/msgs/" in d or d.startswith("_tk_data/images/"):
        return False
    if d.startswith(("_tcl_data/msgs/", "_tk_data/msgs/")):
        return False
    if d.startswith("_tcl_data/encoding/"):
        return d.rsplit("/", 1)[-1].startswith(KEEP_ENCODINGS)
    if d.startswith("_tk_data/demos/") or "/tcltest" in d:
        return False
    return True


a = Analysis(
    ["qbt_installer_gui.py"],
    pathex=[],
    binaries=[],
    datas=[("qbt_plugins", "qbt_plugins")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=2,  # strip docstrings and asserts from the bundled bytecode
)
a.datas = [entry for entry in a.datas if keep_data(entry[0])]
a.binaries = [entry for entry in a.binaries
              if not entry[0].lower().startswith(("libcrypto", "libssl"))]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f"qbt-plugin-installer-{VERSION}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
