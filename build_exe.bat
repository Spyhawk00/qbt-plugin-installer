@echo off
setlocal
cd /d "%~dp0"

rem ===========================================================================
rem  Build the standalone qbt-plugin-installer-<version>.exe (Windows).
rem  Requires Python; installs PyInstaller into the current Python if missing.
rem  Output: dist\qbt-plugin-installer-<version>.exe (version = __version__)
rem ===========================================================================

echo Installing build dependency (PyInstaller)...
python -m pip install --upgrade pyinstaller || goto :err

echo.
echo Building one-file executable...
rem The .exe opens the GUI (qbt_installer_gui.py), windowed: no console.
rem Run it with arguments (e.g. --dry-run) from a terminal for the CLI.
rem All build settings, including what is left out to keep the .exe small,
rem live in qbt-plugin-installer.spec.
python -m PyInstaller --noconfirm qbt-plugin-installer.spec || goto :err

echo.
echo Done. Executable is in the dist folder (qbt-plugin-installer-^<version^>.exe).
exit /b 0

:err
echo.
echo Build failed. See the messages above.
exit /b 1
