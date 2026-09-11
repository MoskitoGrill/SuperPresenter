@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "super_presenter.py" %*
) else (
    python "super_presenter.py" %*
)
set "result=%errorlevel%"
if not "%result%"=="0" (
    echo Spusteni selhalo. Zkontrolujte instalaci podle README.md.
    pause
)
popd
exit /b %result%
