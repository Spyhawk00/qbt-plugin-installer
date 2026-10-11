@echo off
setlocal

rem ===========================================================================
rem  qBittorrent Search Plugin Installer - double-click launcher
rem  Just double-click this file. No typing required.
rem ===========================================================================

title Install qBittorrent Search Plugins
cd /d "%~dp0"

echo ===============================================================
echo   qBittorrent Search Plugin Installer
echo ===============================================================
echo.

rem --- Find a real Python interpreter --------------------------------------
rem  Prefer the "py" launcher (installed by python.org). Fall back to
rem  "python". The Microsoft Store stub prints "Python was not found", so we
rem  verify the interpreter actually runs before using it.

set "PYCMD="

py -3 --version >nul 2>&1
if %errorlevel%==0 (
    set "PYCMD=py -3"
    goto :run
)

rem The Store stub fails "python --version" (exit 9009), so a zero exit code
rem means a real interpreter.
python --version >nul 2>&1
if %errorlevel%==0 (
    set "PYCMD=python"
    goto :run
)

rem --- No Python found ------------------------------------------------------
echo Python is not installed (or not on PATH).
echo.
echo qBittorrent's search feature needs Python to run plugins, so you need
echo it installed anyway. Two easy options:
echo.
echo   1. Open Microsoft Store and install "Python 3.12", OR
echo   2. Download it from https://www.python.org/downloads/
echo      ^(tick "Add python.exe to PATH" during setup^)
echo.
echo After installing Python, double-click this file again.
echo.
pause
exit /b 1

:run
echo Using Python: %PYCMD%
echo.
%PYCMD% "%~dp0install_qbt_plugins.py" --pause %*
set "RC=%errorlevel%"

echo.
if "%RC%"=="0" (
    echo Done. You can close this window.
) else (
    echo The installer reported a problem ^(exit code %RC%^). See the messages above.
)
echo.
pause
exit /b %RC%
