"""Generate public, credential-free API-Football data for GitHub Pages."""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo('America/Bogota')
FINISHED = {'FT', 'AET', 'PEN'}
try:
    from .standings import api_ranks, load_checks, resolve_rank
except ImportError:
    from standings import api_ranks, load_checks, resolve_rank

def load_env(path):
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

class API:
    def __init__(self):
        self.key = os.environ.get('FOOTBALL_API_KEY')
        if not self.key:
            raise RuntimeError('Falta FOOTBALL_API_KEY. Configura el secreto o usa --env con el .env de APUESTAS.')
        self.calls = 0

    def get(self, endpoint, **params):
        query = endpoint + '?' + urllib.parse.urlencode(params)
        import hashlib
        cache = ROOT / '.cache' / (hashlib.sha256(query.encode()).hexdigest() + '.json')
        if cache.exists() and time.time() - cache.stat().st_mtime < 3600:
            return json.loads(cache.read_text(encoding='utf-8'))
        time.sleep(.3)
        req = urllib.request.Request('https://v3.football.api-sports.io/' + query, headers={'x-apisports-key': self.key})
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.load(r)
        self.calls += 1
        if data.get('errors'):
            raise RuntimeError('API-Football: ' + json.dumps(data['errors'], ensure_ascii=False))
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps(data), encoding='utf-8')
        return data

def evaluate(fixture, history, ranks, previous, now, checks=None):
    """Each side is evaluated independently; absent evidence never qualifies."""
    out = []
    home, away = fixture['teams']['home'], fixture['teams']['away']
    kickoff = datetime.fromisoformat(fixture['fixture']['date'])
    year = kickoff.astimezone(TZ).year
    h2h = sorted([f for f in history if f['fixture']['status']['short'] in FINISHED
        and datetime.fromisoformat(f['fixture']['date']) < min(kickoff, now)
        and f['teams']['home']['id'] == away['id'] and f['teams']['away']['id'] == home['id']
        and datetime.fromisoformat(f['fixture']['date']).astimezone(TZ).year == year],
        key=lambda f: f['fixture']['date'], reverse=True)
    last = h2h[0] if h2h else None
    for side, team, rival in [('home', home, away), ('away', away, home)]:
        reasons, missing = [], []
        if not last:
            reasons.append('Sin enfrentamiento finalizado en el mismo año')
        goals = None
        oldside = 'away' if side == 'home' else 'home'
        threshold = 2 if oldside == 'home' else 1
        if last:
            oldside = 'home' if last['teams']['home']['id'] == team['id'] else 'away'
            goals = last['goals'][oldside]
            if goals is None:
                missing.append('Marcador H2H no disponible')
            elif goals < threshold:
                reasons.append(f'Goles H2H insuficientes ({goals}/{threshold})')
        rank, rank_check = resolve_rank(fixture, rival['id'], ranks.get(rival['id']), checks or [], now)
        if rank is None:
            missing.append(rank_check.get('note') or 'Posición del rival no disponible; requiere verificación web')
        elif rank <= 5:
            reasons.append('Rival entre los primeros 5')
        recent = previous.get(team['id'])
        won = False
        if recent:
            rs = 'home' if recent['teams']['home']['id'] == team['id'] else 'away'
            won = recent['teams'][rs].get('winner') is True
            if not won:
                reasons.append('No ganó su último partido')
        else:
            missing.append('Último partido no disponible')
        prequalified = not reasons and not missing
        eligible = fixture['fixture']['status']['short'] == 'NS' and kickoff > now
        if not eligible:
            reasons.append('Partido iniciado o no programado')
        out.append({'team': team['name'], 'teamId': team['id'], 'side': side,
            'status': 'excluded' if reasons else 'pending' if missing else 'candidate',
            'reasons': reasons + missing, 'rivalRank': rank, 'h2h': last,
            'previous': recent, 'goals': goals, 'won': won,
            'previousVenue': oldside, 'requiredH2hGoals': threshold,
            'targetGoals': 1, 'rankVerification': rank_check, 'prequalified': prequalified})
    return out

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    p = argparse.ArgumentParser()
    p.add_argument('--env', type=Path)
    p.add_argument('--date', default=datetime.now(TZ).date().isoformat())
    p.add_argument('--days', type=int, default=3)
    args = p.parse_args()
    if not 1 <= args.days <= 7:
        p.error('--days debe estar entre 1 y 7')
    if args.env:
        load_env(args.env)
    api = API()
    config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    checks = load_checks(ROOT)
    now = datetime.now(TZ)
    matches, errors, leagues_seen = [], [], set()
    selected = {x['id'] for x in config['leagues']}
    for offset in range(args.days):
        day = (datetime.fromisoformat(args.date) + timedelta(days=offset)).date().isoformat()
        fixtures = api.get('fixtures', date=day, timezone='America/Bogota')['response']
        for f in fixtures:
            league = f['league']
            if league['id'] not in selected:
                continue
            print(f"Analizando {f['fixture']['id']}: {f['teams']['home']['name']} / {f['teams']['away']['name']}", flush=True)
            leagues_seen.add(league['id'])
            ranks, previous, history = {}, {}, []
            try:
                tables = api.get('standings', league=league['id'], season=league['season'])['response']
                ranks = api_ranks(tables, f)
            except Exception as e:
                errors.append(f"Clasificación {league['name']}: {e}")
            try:
                history = api.get('fixtures/headtohead', h2h=f"{f['teams']['home']['id']}-{f['teams']['away']['id']}", **{'from': f'{now.year}-01-01', 'to': args.date})['response']
                for team in f['teams'].values():
                    recent = api.get('fixtures', team=team['id'], last=10)['response']
                    recent = [x for x in recent if x['fixture']['status']['short'] in FINISHED and datetime.fromisoformat(x['fixture']['date']) < min(now, datetime.fromisoformat(f['fixture']['date']))]
                    previous[team['id']] = max(recent, key=lambda x: x['fixture']['date']) if recent else None
            except Exception as e:
                errors.append(f"Antecedentes {f['fixture']['id']}: {e}")
            matches.append({'fixture': f, 'selections': evaluate(f, history, ranks, previous, now, checks)})
    result = {'updatedAt': now.isoformat(), 'from': args.date, 'days': args.days,
        'source': 'API-Football', 'matches': matches, 'errors': errors,
        'leaguesSeen': len(leagues_seen), 'apiCalls': api.calls, 'demo': False}
    target = ROOT / 'data' / 'matches.json'
    target.parent.mkdir(exist_ok=True)
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    temp.replace(target)
    try:
        from .tracking_history import sync
    except ImportError:
        from tracking_history import sync
    sync(ROOT)
    print(f"Listo: {len(matches)} partidos, {api.calls} consultas, {len(errors)} incidencias.")

if __name__ == '__main__':
    main()
