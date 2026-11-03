"""Apply browser evidence to the existing snapshot, without spending API calls."""
import json
from datetime import datetime
try:
    from .refresh import ROOT, TZ, evaluate
    from .standings import api_ranks, load_checks
except ImportError:
    from refresh import ROOT, TZ, evaluate
    from standings import api_ranks, load_checks

def main():
    path = ROOT / 'data' / 'matches.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    checks, now = load_checks(ROOT), datetime.now(TZ)
    cached_tables = {}
    for cache in (ROOT / '.cache').glob('*.json'):
        payload = json.loads(cache.read_text(encoding='utf-8'))
        if payload.get('get') == 'standings' and payload.get('response'):
            params = payload['parameters']
            cached_tables[(int(params['league']), int(params['season']))] = payload['response']
    for match in data['matches']:
        fixture, old = match['fixture'], match['selections']
        ranks = {fixture['teams']['away' if s['side'] == 'home' else 'home']['id']: s['rivalRank']
            for s in old if s['rivalRank'] is not None and s.get('rankVerification', {}).get('status', 'api') == 'api'}
        tables = cached_tables.get((fixture['league']['id'], fixture['league']['season']))
        if tables:
            ranks = api_ranks(tables, fixture)
        history = {s['h2h']['fixture']['id']: s['h2h'] for s in old if s['h2h']}
        previous = {s['teamId']: s['previous'] for s in old}
        match['selections'] = evaluate(fixture, list(history.values()), ranks, previous, now, checks)
    data['evaluatedAt'] = now.isoformat()
    # Keep the sports-data timestamp unchanged; a browser check isn't an API refresh.
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    print('Snapshot reevaluado sin consultas API.')

if __name__ == '__main__':
    main()
