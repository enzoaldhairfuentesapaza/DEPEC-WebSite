@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto error
)
if not exist ".venv\depec-ready" (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto error
  echo listo>".venv\depec-ready"
)
if not exist "instance\depec.sqlite" (
  ".venv\Scripts\python.exe" -m flask --app run init-db
  if errorlevel 1 goto error
  ".venv\Scripts\python.exe" -m flask --app run seed-demo
  if errorlevel 1 goto error
)
echo.
echo Abre http://127.0.0.1:5000 en tu navegador.
echo Pulsa Ctrl+C para detener el servidor.
".venv\Scripts\python.exe" run.py
exit /b
:error
echo No se pudo iniciar. Revisa que Python 3.11+ y el lanzador py esten instalados.
pause
exit /b 1
