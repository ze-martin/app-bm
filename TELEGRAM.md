# Avisos por Telegram al minuto 70

Estado inicial: integración implementada, bot todavía sin configurar. No se envían avisos hasta configurar el bot y mantener el monitor en ejecución.

## Configurar una vez

1. En Telegram abre el bot oficial @BotFather, usa `/newbot` y crea un bot dedicado a BM.
2. Abre tu nuevo bot y envíale `/start` desde tu cuenta personal.
3. En una terminal local dentro del proyecto ejecuta `python scripts/setup_telegram.py`. Pega el token en la entrada oculta de la terminal, nunca en el chat ni en archivos públicos. El asistente detecta un único chat privado y guarda token y chat ID en `.env`, excluido de Git.
4. Actualiza la preselección diaria: `python scripts/refresh.py --env D:/CODEX/APUESTAS/.env --days 3`.
5. Inicia `python scripts/telegram_monitor.py --football-env D:/CODEX/APUESTAS/.env`. Mantén este proceso activo en un PC o servidor con conexión, sin suspensión. El dashboard puede estar cerrado. Ctrl+C detiene el monitor.

Para comprobar sin enviar: `python scripts/telegram_monitor.py --football-env D:/CODEX/APUESTAS/.env --dry-run --once`.

## Cuándo avisa

- Solo equipos que cumplen todos los filtros históricos (`prequalified`), conservados aunque el partido ya haya comenzado.
- Consulta API-Football en vivo cada 60 segundos, sin reutilizar el caché histórico de una hora. Fuera de las ventanas de los candidatos no hace consultas en vivo.
- Estado segundo tiempo (`2H`) y minuto real entre 70 y 75. Si la consulta llega al 71, el mensaje indica 71; no afirma haber llegado exactamente al 70. No se avisa fuera de la ventana por una reconexión tardía.
- El equipo elegido debe seguir con cero goles. Si marcó, el marcador es desconocido o el partido fue suspendido/finalizó, no envía aviso.
- Registro local por partido/equipo para evitar envíos repetidos tras reiniciar. Se guarda después del envío exitoso. Un corte de conexión durante el envío puede dejar incierto si Telegram lo recibió; no existe garantía de entrega exactamente una vez.
- Exige preselección deportiva de menos de 24 horas. Datos y fallos de red pueden impedir un aviso. Hay que actualizar el snapshot diariamente y comprobar que el monitor sigue activo.

El aviso informa marcador y equipo para REVISAR. No decide que se deba apostar y no interpreta dominio o estadísticas del segundo tiempo. Esas comprobaciones siguen siendo manuales. No se usa inicio + 85 minutos para enviar mensajes: esa estimación solo ayuda a planificar la agenda visual.

GitHub Pages sirve la interfaz estática y no ejecuta este monitor. El cron de Actions no garantiza dispararse en el minuto exacto y no se usa como reloj para estas alertas. Para funcionamiento sin PC se necesita alojar el mismo proceso en un servidor siempre activo; no hay un servidor nuevo contratado ni configurado en esta versión.

Documentación: [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage), [API-Football](https://www.api-football.com/documentation-v3).
