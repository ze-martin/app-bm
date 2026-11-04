@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo BM - Avisos al 65 y estadisticas al 70
echo Actualizando la preseleccion deportiva antes de iniciar...
python scripts\refresh.py --env D:/CODEX/APUESTAS/.env --days 3
if errorlevel 1 goto failed
echo Mantener esta ventana y el PC encendidos. Ctrl+C detiene el monitor.
python scripts\telegram_monitor.py --football-env D:/CODEX/APUESTAS/.env --publish
if errorlevel 1 goto failed
exit /b 0
:failed
echo No se pudo iniciar. Revisa la configuracion o si ya hay otro monitor activo.
pause
exit /b 1
