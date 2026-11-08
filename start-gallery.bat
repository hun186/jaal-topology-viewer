@echo off
setlocal
cd /d "%~dp0"
set "JAAL_ENABLE_LARGE_LOCAL=1"
echo [JAAL] Original 5-mode Gallery with fictional 500 / 3000 / 5000 / 20000-person cases
echo [JAAL] Three disconnected companies are also available in the SAME case selector.
echo [JAAL] http://127.0.0.1:8059/
echo [JAAL] Large cases load only when you select them. Ctrl+C stops the server.
echo.
python -m flask --app app:app run --host 127.0.0.1 --port 8059 --no-reload
if errorlevel 1 (
  echo [JAAL] If Flask is missing, run:
  echo    python -m pip install -r requirements.txt
  echo    python -m pip install -e .
  pause
)
endlocal
