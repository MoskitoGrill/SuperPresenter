@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1
if exist ".venv\Scripts\python.exe" goto install
py -3 -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv .venv
    goto created
)
python -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1
if not errorlevel 1 (
    python -m venv .venv
    goto created
)
echo Nainstalujte Python 3.10 nebo novejsi s Tcl/Tk z python.org.
echo V instalatoru zapnete pridani Pythonu do PATH. Pak spustte tento soubor znovu.
goto failed
:created
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import sys, tkinter, PIL, screeninfo; assert sys.version_info >= (3, 10)"
if errorlevel 1 goto failed
echo Hotovo. Aplikaci spustite pres spustit_super_presenter.exe.
popd
pause
exit /b 0
:failed
echo Priprava selhala. Viz zprava vyse a README.md.
popd
pause
exit /b 1
