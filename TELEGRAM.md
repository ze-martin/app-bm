# Avisos por Telegram al minuto 65 para revisar al 70

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
- Aviso previo: estado segundo tiempo (`2H`) y minuto real entre 65 y 69. Se intenta desde el 65; si el proveedor salta a 66, se indica 66 y que quedan aproximadamente 4 minutos de juego. No se envía este aviso al 70 o después: ya no habría cinco minutos de anticipación. La entrega exacta al 65 depende de la actualización de la API, la conexión y el monitor.
- El equipo elegido debe seguir con cero goles. Si marcó, el marcador es desconocido o el partido fue suspendido/finalizó, no envía aviso.
- Registro local por partido/equipo para evitar envíos repetidos tras reiniciar. Se guarda después del envío exitoso. Un corte de conexión durante el envío puede dejar incierto si Telegram lo recibió; no existe garantía de entrega exactamente una vez.
- Exige preselección deportiva de menos de 24 horas. Datos y fallos de red pueden impedir un aviso. Hay que actualizar el snapshot diariamente y comprobar que el monitor sigue activo.

El aviso previo informa marcador y equipo para REVISAR antes del 70. Si el elegido marca entre el aviso y el 70, se descarta; el aviso no implica que siga cumpliendo después. No decide que se deba apostar y no interpreta dominio o estadísticas del segundo tiempo. Esas comprobaciones siguen siendo manuales. No se usa inicio + 85 minutos para enviar mensajes: esa estimación solo ayuda a planificar la agenda visual.

GitHub Pages sirve la interfaz estática y no ejecuta este monitor. El cron de Actions no garantiza dispararse en el minuto exacto y no se usa como reloj para estas alertas. Para funcionamiento sin PC se necesita alojar el mismo proceso en un servidor siempre activo; no hay un servidor nuevo contratado ni configurado en esta versión.

Documentación: [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage), [API-Football](https://www.api-football.com/documentation-v3).

## Estadísticas del aviso

El monitor consulta `fixtures/statistics?fixture=ID&half=true` para el aviso entre 65–69 y, por separado, para la captura entre 70–75. Las estadísticas del aviso se identifican con el minuto real (por ejemplo, 65), sin guardarlas como si fueran del 70. Incluye posesión, córners, disparos totales y a puerta de ambos equipos: `statistics_2h` para segundo tiempo y `statistics` para acumulado. Null, campos ausentes o valores inválidos son N/D. No resta porcentajes de posesión ni infiere dominancia o umbrales que no han sido definidos. La captura conserva el minuto real y la hora; no se etiqueta un 72 como 70.

`--publish` guarda solo datos deportivos en la rama pública `codex/live70`. El dashboard lee ese archivo cada 60 segundos y muestra las capturas en el partido y en la sección de estadísticas. No se ejecuta un despliegue Pages por cada captura. Requiere la autenticación GitHub existente en el equipo que ejecuta el monitor; no publica tokens.

Para obtener/publicar estadísticas sin configurar Telegram: `python scripts/telegram_monitor.py --football-env D:/CODEX/APUESTAS/.env --capture-only --publish`. Sigue requiriendo un proceso activo en PC o servidor. Si se ejecuta sin `--publish`, los datos se guardan únicamente en `data/live70.json` local y no actualizan el dashboard público.

La captura es una observación histórica, no un marcador permanentemente actualizado. Si falla la consulta de estadísticas, el aviso muestra N/D; no se oculta el fallo ni se rellena con ceros.

## Qué es tu bot y cómo funciona

El bot es un chat de Telegram que recibe los avisos enviados por el monitor BM. No analiza partidos por su cuenta ni ejecuta apuestas. La cadena es: API-Football → monitor encendido → bot → tu celular. Puedes cerrar el dashboard; el monitor debe seguir activo en PC o servidor. El celular solo necesita Telegram, conexión y notificaciones habilitadas.

En @BotFather escribe `/newbot`, elige un nombre (por ejemplo BM Radar) y un usuario disponible que termine en `bot`. BotFather entrega un token: es la contraseña del bot. Introdúcelo únicamente en `python scripts/setup_telegram.py`, cuya entrada está oculta. Después de crear el bot, abre su enlace y pulsa Iniciar o envía `/start`; Telegram no permite que el bot inicie una conversación contigo sin ese paso. El asistente local detecta el chat privado para enviarte avisos.

Crear el bot no enciende el monitor. La modalidad de captura sin mensajes (`--capture-only`) sigue funcionando al 70, sin generar notificaciones anticipadas. Para recibir avisos, hay que configurar el bot y sustituir ese proceso por el monitor sin `--capture-only`, evitando dos monitores simultáneos. Estado de esta entrega: bot no configurado y mensajes sin activar.

El aviso incluirá marcador, minuto real, elegido y estadísticas de ambos equipos. Ahora también agrega disparos dentro del área, bloqueos, atajadas, amarillas, rojas, xG y precisión (tiros a puerta / tiros totales). xG admite decimales y sigue la cobertura del proveedor. Las rojas generan una advertencia visual y en Telegram, sin decidir automáticamente la apuesta. No se inventa un índice de presión ni un pronóstico de gol.

Si pierdes el token, puedes revocarlo y emitir otro desde @BotFather. No necesitas dar tu contraseña de Telegram al dashboard. Para silenciar el bot, puedes silenciar el chat o detener el monitor.

Fuentes: [Creación de bots](https://core.telegram.org/bots/tutorial), [Cómo funcionan](https://core.telegram.org/bots).

## Accesos directos para Windows

1. Crea el bot en [@BotFather](https://t.me/BotFather) con `/newbot`; por ejemplo nombre BM Radar y un usuario disponible terminado en `bot`.
2. Abre tu nuevo bot y envía `/start`.
3. En la carpeta del proyecto, abre `Configurar Telegram.cmd`. Introduce el token en la entrada oculta. Al validarlo, enviará un único mensaje de conexión al chat privado identificado. El token permanece en `.env` local, ignorado por Git.
4. Abre `Iniciar avisos Telegram.cmd`. Primero renueva los partidos y luego mantiene el monitor activo, con avisos al 65 y capturas al 70. Hay que conservar la ventana abierta, el PC encendido y sin suspensión.

El aviso al 65 es único por partido/equipo y usa una clave distinta de los antiguos avisos al 70 para evitar mezclar registros. La captura al 70 no dispara un segundo aviso.


## Registro permanente

`history.html` muestra el registro desde el 3 de noviembre de 2026. `data/history.json` conserva las selecciones aunque dejen de estar en el snapshot actual. El monitor registra avisos realmente enviados y capturas; Actions revisa resultados en sus actualizaciones programadas. La liquidación usa eventos reconciliados contra el marcador final reglamentario: minuto mayor que 70, incluyendo 90+; eventos incompletos quedan pendientes. No se infieren revisión de dominio, recomendación manual ni apuesta realizada. La recuperación inicial es parcial y separa evidencia previa de evaluaciones posteriores. El JSON publicado contiene solo datos deportivos y horas de envío, sin token ni chat privado.
