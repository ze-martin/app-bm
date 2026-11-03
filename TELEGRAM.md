# Avisos por Telegram al minuto 70

Estado inicial: integración implementada, bot todavía sin configurar. No se envían avisos hasta configurar el bot y mantener el monitor en ejecución.

## Configurar una vez

1. En Telegram abre el bot oficial @BotFather, usa `/newbot` y crea un bot dedicado a BM.
2. Abre tu nuevo bot y envíale `/start` desde tu cuenta personal.
3. En una terminal local dentro del proyecto ejecuta `python scripts/setup_telegram.py`. Pega el token en la entrada oculta de la terminal, nunca en el chat ni en archivos públicos. El asistente detecta un único chat privado y guarda token y chat ID en `.env`, excluido de Git.
4. Actualiza la preselección diaria: `python scripts/refresh.py --env D:/CODEX/APUESTAS/.env --days 3`.
5. Inicia `python scripts/telegram_monitor.py --football-env D:/CODEX/APUESTAS/.env --publish`. Mantén este proceso activo en un PC o servidor con conexión, sin suspensión. El dashboard puede estar cerrado. Ctrl+C detiene el monitor.

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

## Estadísticas del aviso

El monitor consulta `fixtures/statistics?fixture=ID&half=true` al detectar un candidato en 70–75 minutos. Incluye posesión, córners, disparos totales y a puerta de ambos equipos: `statistics_2h` para segundo tiempo y `statistics` para acumulado. Null, campos ausentes o valores inválidos son N/D. No resta porcentajes de posesión ni infiere dominancia o umbrales que no han sido definidos. La captura conserva el minuto real y la hora; no se etiqueta un 72 como 70.

`--publish` guarda solo datos deportivos en la rama pública `codex/live70`. El dashboard lee ese archivo cada 60 segundos y muestra las capturas en el partido y en la sección de estadísticas. No se ejecuta un despliegue Pages por cada captura. Requiere la autenticación GitHub existente en el equipo que ejecuta el monitor; no publica tokens.

Para obtener/publicar estadísticas sin configurar Telegram: `python scripts/telegram_monitor.py --football-env D:/CODEX/APUESTAS/.env --capture-only --publish`. Sigue requiriendo un proceso activo en PC o servidor. Si se ejecuta sin `--publish`, los datos se guardan únicamente en `data/live70.json` local y no actualizan el dashboard público.

La captura es una observación histórica, no un marcador permanentemente actualizado. Si falla la consulta de estadísticas, el aviso muestra N/D; no se oculta el fallo ni se rellena con ceros.

## Qué es tu bot y cómo funciona

El bot es un chat de Telegram que recibe los avisos enviados por el monitor BM. No analiza partidos por su cuenta ni ejecuta apuestas. La cadena es: API-Football → monitor encendido → bot → tu celular. Puedes cerrar el dashboard; el monitor debe seguir activo en PC o servidor. El celular solo necesita Telegram, conexión y notificaciones habilitadas.

En @BotFather escribe `/newbot`, elige un nombre (por ejemplo BM Radar) y un usuario disponible que termine en `bot`. BotFather entrega un token: es la contraseña del bot. Introdúcelo únicamente en `python scripts/setup_telegram.py`, cuya entrada está oculta. Después de crear el bot, abre su enlace y pulsa Iniciar o envía `/start`; Telegram no permite que el bot inicie una conversación contigo sin ese paso. El asistente local detecta el chat privado para enviarte avisos.

Crear el bot no enciende el monitor. La captura de 12 horas que se inició en este PC funciona sin enviar mensajes (`--capture-only`). Para recibir avisos, hay que configurar el bot y sustituir ese proceso por el monitor sin `--capture-only`, evitando dos monitores simultáneos. Estado de esta entrega: bot no configurado y mensajes sin activar.

El aviso incluirá marcador, minuto real, elegido y estadísticas de ambos equipos. Ahora también agrega disparos dentro del área, bloqueos, atajadas, amarillas, rojas, xG y precisión (tiros a puerta / tiros totales). xG admite decimales y sigue la cobertura del proveedor. Las rojas generan una advertencia visual y en Telegram, sin decidir automáticamente la apuesta. No se inventa un índice de presión ni un pronóstico de gol.

Si pierdes el token, puedes revocarlo y emitir otro desde @BotFather. No necesitas dar tu contraseña de Telegram al dashboard. Para silenciar el bot, puedes silenciar el chat o detener el monitor.

Fuentes: [Creación de bots](https://core.telegram.org/bots/tutorial), [Cómo funcionan](https://core.telegram.org/bots).
