@echo off
setlocal
rem Start the fictional 77-person, 169-directed-link company communication demo.
rem Usage: run-company-demo.bat [port] (default 8059). No downloads or writes.
cd /d "%~dp0"
set "PORT=8059"
if not "%~1"=="" set "PORT=%~1"
echo.
echo Company Communication Demo ^(FICTIONAL^): 77 roles, 169 directed sender-to-recipient links.
echo Open http://127.0.0.1:%PORT%/ after the server starts.
echo Choose [Network / Fully Expanded] for the general email network.
echo.
python -m jaal_topology --edges "examples\company_communications.csv" --metadata "examples\company_people.csv" --port "%PORT%"
if errorlevel 1 (
    echo.
    echo Demo could not start. Verify Python 3.10+ and install once from repo root:
    echo   python -m pip install -e .
    exit /b 1
)
endlocal
