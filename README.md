# BM · Radar de partidos

Dashboard estático en español, compatible con GitHub Pages. Consulta API-Football desde Python y publica únicamente los resultados, sin exponer la clave en el navegador.

## Ejecutar

Requiere Python 3.10+ con la base de zonas horarias disponible (`pip install tzdata` en Windows si falta).

```powershell
python scripts/refresh.py --env 'D:/CODEX/APUESTAS/.env' --days 3
python -m http.server 8080
```

Abre http://localhost:8080. Para otra fecha: `--date 2026-11-05`. Los días admitidos van de 1 a 7. La API se consulta con la misma variable `FOOTBALL_API_KEY` que utiliza APUESTAS; no se modifica ese proyecto. Caché local de una hora. La cantidad de consultas depende de los partidos y equipos disponibles.

## Publicar en GitHub Pages

1. Sube este proyecto a tu repositorio GitHub.
2. En Settings → Secrets and variables → Actions crea `FOOTBALL_API_KEY` con tu clave existente.
3. En Settings → Pages selecciona GitHub Actions como fuente.
4. Ejecuta “Actualizar radar y publicar Pages” desde Actions.

El workflow actualiza los próximos tres días a las 05:20, 11:20 y 17:20 de Bogotá/Lima y al ejecutarlo manualmente. Los pushes publican el snapshot existente sin gastar consultas adicionales. Si falla la consulta inicial, no publica una descarga vacía. No publica `.env`, cachés ni scripts Python. Repositorio: https://github.com/ze-martin/app-bm · Dashboard: https://ze-martin.github.io/app-bm/

## Reglas y evidencia

Fuente: Excel `Parámetros_APP.xlsx` y dos audios del 03/11/2026. Cada equipo se evalúa por separado, sin transformar estos filtros en probabilidades.

- Se consulta el último enfrentamiento finalizado del mismo año calendario, anterior a la consulta, con localías invertidas según el ejemplo del audio. Puede pertenecer a otra competición.
- Se considera la condición del equipo en ese antecedente: si antes fue local y marcó 2 o más, ahora de visitante se evalúa para marcar al menos 1; si antes fue visitante y marcó 1 o más, ahora de local se evalúa para marcar al menos 1. El audio de las 13:28 del 03/11/2026 confirma ambas direcciones. Cada fila y el CSV muestran la localía anterior, los goles, el mínimo exigido y el objetivo actual. Es un filtro histórico, no una probabilidad calculada.
- Se exige posición del rival mayor que 5 en la liga del partido y victoria del elegido en su último encuentro finalizado de cualquier competición.
- Sin clasificación o antecedentes suficientes, queda “Por verificar”, salvo que otra regla ya permita descartarlo. En copas sin tabla de liga no se infiere una posición: queda pendiente. La fase se identifica con la ronda del fixture antes de leer posiciones. Si la API no resuelve la tabla, se aplica el [protocolo de navegación con scroll](PROTOCOL_STANDINGS.md), con dos fuentes, registro de evidencia y vigencia de 24 horas. La revisión web es asistida, no scraping desatendido.
- Solo se califican partidos `NS` con inicio futuro. El navegador retira candidatos cuyo horario ya pasó.
- La revisión al minuto 70 es manual: descartar si el equipo ya anotó y evaluar estadísticas del segundo tiempo. Esta versión no obtiene estadísticas en vivo ni sugiere importes o ejecuta apuestas.

“ESPAÑA” y “1ERA ESPAÑA” se unifican en La Liga; por eso son 48 competiciones únicas (incluida la Championship de Inglaterra, API-Football 40). “CHPRE” se interpreta como Chipre. Se usa primera división para los países sin división explícita. Estos supuestos se pueden cambiar en `config.json`. Los identificadores de ligas deben contrastarse con la cobertura de tu plan API-Football.

Filtros por texto, liga, fecha y estado; evidencias desplegables; exportación CSV de las filas visibles; diseño adaptable a móvil. Ante una descarga parcial, se indican las incidencias. Un resultado sin candidatos es válido y no se rellena con ejemplos.

## Verificación

```powershell
python -m unittest discover -s tests
node --check app.js
```

Documentación: https://www.api-football.com/documentation-v3 y https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages

## Dashboard y Telegram

Panel de cobertura de clasificación, filtros acumulados, motivos de descarte, distribución de candidatos por liga y agenda orientativa. [Configurar avisos por Telegram](TELEGRAM.md): requiere bot y monitor activo en PC o servidor. La integración no está activada todavía.

## Revisión de cobertura de ligas

Se contrastaron todas las identidades con el catálogo de API-Football. Paraguay necesita 250 (Apertura) y 252 (Clausura); 251 es División Intermedia y queda fuera. Uruguay usa 268 para las fases de 2026; el antiguo 270 no tiene temporada 2026 y no se añade. Cada ficha del catálogo público muestra país, nombre del proveedor, ID, temporada y fecha de auditoría.

`python scripts/audit_leagues.py --env RUTA_ENV` comprueba que el alcance requerido esté completo y que coincidan país, tipo y temporada. El workflow repite la auditoría antes de cada descarga programada. Identidad verificada no garantiza estadísticas disponibles en cada fixture.

## Análisis histórico de octubre 2026

`python scripts/backtest_october.py` descarga historiales de las 48 competiciones y de todos los clubes participantes en octubre; conserva el caché histórico en `.cache/backtest-october-2026/`. `python scripts/render_backtest.py` genera el informe HTML, CSV y JSON en `reports/october-2026/`.

El análisis es una simulación, no un registro de apuestas. Las posiciones son una reconstrucción por puntos sin archivo oficial de sanciones; se separan empates que cruzan el quinto puesto, conferencias, fases complejas y copas. La entrada exige cero goles del elegido al 70; se concilian los eventos con el marcador reglamentario antes de resolver gol del elegido y cualquier gol posterior. No se usan estadísticas finales para inferir dominio al 70 ni se calcula rentabilidad sin cuotas históricas. El informe detalla todas las limitaciones y sus denominadores.
