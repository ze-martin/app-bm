"""Phase-aware API standings and audited, browser-assisted fallback."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
import re
import unicodedata

def normalize(value):
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))).strip()

def phase_of(fixture):
    return fixture['league'].get('round', '').split(' - ')[0].strip()

def api_ranks(tables, fixture):
    groups = [g for t in tables for g in t['league']['standings'] if g]
    phase = normalize(phase_of(fixture))
    matches = [g for g in groups if phase and any(phase in normalize(r.get('group', '')) for r in g)]
    named_phases = ('apertura', 'clausura', 'annual', 'anual')
    single_conflicts = len(groups) == 1 and any(
        marker in normalize(row.get('group', '')) and marker not in phase
        for row in groups[0] for marker in named_phases)
    selected = matches or (groups if len(groups) == 1 and not single_conflicts else [])
    positions = {}
    for group in selected:
        for row in group:
            positions.setdefault(row['team']['id'], set()).add(row['rank'])
    return {k: next(iter(v)) for k, v in positions.items() if len(v) == 1}

def load_checks(root):
    path = Path(root) / 'data' / 'standings-checks.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []

def resolve_rank(fixture, team_id, rank, checks, now):
    meta = {'status': 'api' if rank is not None else 'needed', 'source': 'API-Football' if rank is not None else None,
            'phase': phase_of(fixture), 'sources': []}
    records = [c for c in checks if c.get('fixtureId') == fixture['fixture']['id'] and c.get('teamId') == team_id]
    if not records:
        return rank, meta
    try:
        record = max(records, key=lambda c: c['checkedAt'])
        checked = datetime.fromisoformat(record['checkedAt'])
        if checked.tzinfo is None or not timedelta(minutes=-5) <= now - checked <= timedelta(hours=24):
            return rank, {**meta, 'status': 'expired', 'note': 'Revisión web vencida; requiere nuevo desplazamiento y lectura.'}
        if record['leagueId'] != fixture['league']['id'] or record['season'] != fixture['league']['season'] or normalize(record['phase']) != normalize(phase_of(fixture)):
            return rank, {**meta, 'status': 'invalid', 'note': 'La evidencia corresponde a otra fase o temporada.'}
        sources = record['sources']
        hosts = {urlparse(s['url']).hostname.removeprefix('www.') for s in sources if urlparse(s['url']).scheme == 'https'}
        ranks = {s['rank'] for s in sources}
        if len(hosts) < 2 or any(not s.get('row') or s.get('method') != 'visual-scroll' for s in sources):
            return rank, {**meta, 'status': 'invalid', 'note': 'Faltan dos fuentes con lectura visual de la fila.'}
        if len(ranks) != 1 or any(type(r) is not int or r < 1 or r > 100 for r in ranks):
            return None, {**meta, 'status': 'conflict', 'sources': sources, 'note': 'Las fuentes discrepan sobre la posición; pendiente.'}
        verified = next(iter(ranks))
        meta.update(status='verified', source='Verificación web', checkedAt=record['checkedAt'], sources=sources)
        if rank is not None and rank != verified:
            return None, {**meta, 'status': 'conflict', 'note': f'API ({rank}) y web ({verified}) discrepan; pendiente.'}
        return verified, meta
    except (KeyError, TypeError, ValueError, AttributeError):
        return rank, {**meta, 'status': 'invalid', 'note': 'Registro de evidencia incompleto o inválido.'}
