# Operación del dashboard BM

Para posiciones ausentes o ambiguas y solicitudes de verificar tablas, seguir `PROTOCOL_STANDINGS.md`, incluyendo navegación con scroll, fase correcta y evidencia. No declarar una verificación automática si solo se abrieron enlaces. Usar la clave existente únicamente desde entorno local o secreto de Actions. Al publicar cambios de reglas, recalcular también el snapshot y comprobar Pages. La revisión externa es asistida; no prometer scroll desatendido desde Actions.

Al revisar cobertura de países, ejecutar `scripts/audit_leagues.py` y contrastar los IDs con el catálogo actual. Paraguay requiere tanto 250 (Apertura) como 252 (Clausura); 251 es segunda división. Uruguay 2026 integra Clausura en 268; no añadir el antiguo 270 por su nombre sin comprobar temporadas. Publicar la evidencia en `data/league-audit.json` y renovar los fixtures al cambiar el alcance.
