@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo BM - Configurar avisos privados al minuto 65
echo Primero crea tu bot en @BotFather y enviale /start.
echo El token se introduce de forma oculta y no se publica.
python scripts\setup_telegram.py --test
if errorlevel 1 goto failed
echo.
echo Bot guardado. Para actualizar los candidatos e iniciar los avisos,
echo abre "Iniciar avisos Telegram.cmd".
pause
exit /b 0
:failed
echo No se completo la configuracion. Revisa el mensaje anterior.
pause
exit /b 1
