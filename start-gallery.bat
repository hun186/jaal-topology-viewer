@echo off
setlocal EnableExtensions
cd /d "%~dp0" || exit /b 1

rem Only opt in to large synthetic Jaal cases on the local loopback server.
set "JAAL_ENABLE_LARGE_LOCAL=1"
set "JAAL_PYTHON="
set "JAAL_USE_CONDA_RUN="

rem 1. Prefer a project-local virtual environment when available.
if exist ".venv\Scripts\python.exe" (
  set "JAAL_PYTHON=%CD%\.venv\Scripts\python.exe"
  goto :run
)

rem 2. An already active dedicated Conda environment is also fine.
if /I "%CONDA_DEFAULT_ENV%"=="jaal-viewer" (
  set "JAAL_PYTHON=python"
  goto :run
)

rem 3. Double-clicking from outside Anaconda Prompt can still use the
rem dedicated Conda environment if the conda command is available.
where conda >nul 2>&1
if errorlevel 1 goto :missing_environment
call conda run -n jaal-viewer --no-capture-output python -c "import sys" >nul 2>&1
if errorlevel 1 goto :missing_environment
set "JAAL_USE_CONDA_RUN=1"

:run
echo [JAAL] Real five-mode Jaal Gallery - fictional 500 / 3000 / 5000 / 20000 / 3000-DAG cases.
echo [JAAL] Three truly disconnected companies are in the SAME case picker.
echo [JAAL] http://127.0.0.1:8059/
echo [JAAL] Large cases load only when selected. Ctrl+C stops the server.
if defined JAAL_USE_CONDA_RUN (
  echo [JAAL] Python: Conda environment "jaal-viewer".
  call conda run -n jaal-viewer --no-capture-output python -m flask --app app:app run --host 127.0.0.1 --port 8059 --no-reload
) else (
  echo [JAAL] Python: "%JAAL_PYTHON%"
  "%JAAL_PYTHON%" -m flask --app app:app run --host 127.0.0.1 --port 8059 --no-reload
)
set "JAAL_EXIT=%ERRORLEVEL%"
if not "%JAAL_EXIT%"=="0" (
  echo.
  echo [JAAL] The selected Python environment failed to start Jaal.
  echo [JAAL] This is not necessarily a missing Flask package.
  echo [JAAL] In Anaconda Prompt run these once:
  echo   conda activate jaal-viewer
  echo   python -m pip install -r requirements.txt
  echo   python -m pip install -e .
  echo [JAAL] Then run start-gallery.bat again.
  if not defined CI pause
)
exit /b %JAAL_EXIT%

:missing_environment
echo.
echo [JAAL] No isolated Jaal Python environment found.
echo [JAAL] Refusing to use Anaconda (base): it can mix user-site Dash with
echo [JAAL] the Anaconda comm/Jupyter package and fail at Dash startup.
echo [JAAL] In Anaconda Prompt, run these commands ONCE:
echo   conda create -n jaal-viewer python=3.11 -y
echo   conda activate jaal-viewer
echo   python -m pip install -r requirements.txt
echo   python -m pip install -e .
echo [JAAL] Then run start-gallery.bat again.
if not defined CI pause
exit /b 2
