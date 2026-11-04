"""October 2026 conditional historical simulation, with explicit coverage exclusions."""
import csv
import hashlib
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
try:
    from .refresh import ROOT, TZ, load_env
    from .standings import normalize, phase_of
except ImportError:
    from refresh import ROOT, TZ, load_env
    from standings import normalize, phase_of

CACHE=ROOT/'.cache/backtest-october-2026'
OUT=ROOT/'reports/october-2026'
START=datetime(2026,10,1,tzinfo=TZ)
END=datetime(2026,11,1,tzinfo=TZ)
DONE={'FT','AET','PEN'}

class HistoricalAPI:
    def __init__(self):
        self.key=os.environ['FOOTBALL_API_KEY']
        self.lock=threading.Lock()
        self.last=0
        self.calls=0
    def get(self,endpoint,**params):
        query=endpoint+'?'+urllib.parse.urlencode(sorted(params.items()))
        path=CACHE/(hashlib.sha256(query.encode()).hexdigest()+'.json')
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        for retry in range(4):
            with self.lock:
                time.sleep(max(0,.32-(time.monotonic()-self.last)))
                self.last=time.monotonic()
                self.calls+=1
            try:
                req=urllib.request.Request('https://v3.football.api-sports.io/'+query,headers={'x-apisports-key':self.key})
                with urllib.request.urlopen(req,timeout=45) as response:
                    data=json.load(response)
                if data.get('errors'):
                    raise RuntimeError('API: '+json.dumps(data['errors']))
                if data.get('paging',{}).get('total',1)>1:
                    raise RuntimeError('Respuesta paginada no admitida sin recorrer páginas')
                path.parent.mkdir(exist_ok=True,parents=True)
                path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
                return data
            except Exception:
                if retry==3:raise
                time.sleep(3*(retry+1))

def batch(tasks,worker,label):
    results,errors={},{}
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending={pool.submit(worker,t):t for t in tasks}
        for i,future in enumerate(as_completed(pending),1):
            t=pending[future]
            try:results[t]=future.result()
            except Exception as e:errors[str(t)]=str(e)
            if i%20==0 or i==len(pending):print(f'{label}: {i}/{len(pending)}',flush=True)
    return results,errors

def kick(f):return datetime.fromisoformat(f['fixture']['date'])
def side_for(f,team):return 'home' if f['teams']['home']['id']==team else 'away'

def reconstructed_rank(fixture,league_fixtures,team):
    """Use points bands: never guess top-five membership using an arbitrary tie-break."""
    phase=normalize(phase_of(fixture))
    if fixture['league']['id'] in {2,3}:
        return None,'cup_table_not_domestic',None
    if fixture['league']['id']==253:
        return None,'conference_table',None
    round_name=normalize(fixture['league'].get('round',''))
    if any(word in round_name for word in ['play','championship','relegation','final','group','intermedio','quadrangular','promotion','second stage','2nd phase']):
        return None,'complex_phase',None
    matches=[f for f in league_fixtures if f['league']['season']==fixture['league']['season']
        and normalize(phase_of(f))==phase and kick(f)<kick(fixture)
        and f['fixture']['status']['short'] in DONE|{'AWD','WO'}]
    points=defaultdict(int)
    unsettled=[f for f in matches if kick(fixture)-kick(f)<timedelta(hours=3)]
    for f in matches:
        if f in unsettled:continue
        h,a=f['teams']['home']['id'],f['teams']['away']['id']
        hg,ag=f['goals']['home'],f['goals']['away']
        if hg is None or ag is None:return None,'missing_historical_score',None
        points[h]+=3 if hg>ag else 1 if hg==ag else 0
        points[a]+=3 if ag>hg else 1 if hg==ag else 0
    # Include every club of this same phase, even if it has not played yet.
    clubs={t['id'] for f in league_fixtures if f['league']['season']==fixture['league']['season']
        and normalize(phase_of(f))==phase for t in f['teams'].values()}
    if team not in points or len(points)<6:return None,'insufficient_table_history',None
    possible_extra=Counter(t['id'] for f in unsettled for t in f['teams'].values())
    minimum={c:points[c] for c in clubs}
    maximum={c:points[c]+3*possible_extra[c] for c in clubs}
    # No result of an overlapping match is used: accept only if top-five membership
    # is unchanged for ALL possible outcomes and all tie-break resolutions.
    band=[1+sum(minimum[c]>maximum[team] for c in clubs if c!=team),
        1+sum(maximum[c]>=minimum[team] for c in clubs if c!=team)]
    if band[0]>5:return band[0],'outside_top5_reconstructed',band
    if band[1]<=5:return band[0],'inside_top5_reconstructed',band
    return None,'overlapping_previous_fixture' if unsettled else 'tie_crosses_fifth',band

def goal_timeline(f,events):
    """Verify regulation goal events against the final regulation score."""
    goals=[]
    for e in events:
        if e.get('type')!='Goal' or e.get('detail')=='Missed Penalty':continue
        minute=e.get('time',{}).get('elapsed')
        if type(minute) is not int:return None,'goal_without_minute'
        if minute>90:continue
        team=e.get('team',{}).get('id')
        if team not in {f['teams']['home']['id'],f['teams']['away']['id']}:return None,'unmapped_goal_team'
        goals.append({'teamId':team,'minute':minute,'extra':e.get('time',{}).get('extra'),
            'ownGoal':e.get('detail')=='Own Goal'})
    expected=f.get('score',{}).get('fulltime') or f['goals']
    if expected.get('home') is None or expected.get('away') is None:return None,'missing_regulation_score'
    def agrees(items):
        return all(sum(g['teamId']==f['teams'][side]['id'] for g in items)==expected[side] for side in ('home','away'))
    if agrees(goals):return goals,'validated'
    # Provider feeds may attribute an own-goal event to the player team or beneficiary.
    flipped=[{**g,'teamId':f['teams']['away' if g['teamId']==f['teams']['home']['id'] else 'home']['id']} if g['ownGoal'] else g for g in goals]
    if agrees(flipped):return flipped,'validated_own_goal_reassigned'
    halftime=f.get('score',{}).get('halftime') or {}
    for variant in (goals,flipped):
        # A recorded first-half goal is impossible for a side whose verified
        # halftime score is zero. Accept this repair only if regulation totals
        # AND the remaining halftime counts both reconcile.
        cleaned=[g for g in variant if not(g['minute']<=45 and halftime.get(side_for(f,g['teamId']))==0)]
        if len(cleaned)<len(variant) and agrees(cleaned) and all(
            halftime.get(side) is not None and sum(g['teamId']==f['teams'][side]['id'] and g['minute']<=45 for g in cleaned)==halftime[side]
            for side in ('home','away')):
            return cleaned,'validated_scoreless_halftime_reconciliation'
    return None,'goal_events_do_not_match_score'

def settle_entry(team,goals):
    if any(g['teamId']==team and g['minute']<=70 for g in goals):
        return {'entry':False,'teamGoalAfter70':None,'anyGoalAfter70':None,'reason':'chosen_team_already_scored_by70'}
    return {'entry':True,'teamGoalAfter70':any(g['teamId']==team and g['minute']>70 for g in goals),
        'anyGoalAfter70':any(g['minute']>70 for g in goals),'reason':'eligible_zero_goals_at70'}

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    load_env(Path('D:/CODEX/APUESTAS/.env'))
    CACHE.mkdir(parents=True,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    api=HistoricalAPI()
    config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    tasks=[(l['id'],year) for l in config['leagues'] for year in (2025,2026)]
    leagues,errors=batch(tasks,lambda t:api.get('fixtures',league=t[0],season=t[1])['response'],'Historial de ligas')
    all_by_id={f['fixture']['id']:f for values in leagues.values() for f in values}
    all_fixtures=list(all_by_id.values())
    october=[f for f in all_fixtures if START<=kick(f).astimezone(TZ)<END]
    print(f'Octubre: {len(october)} partidos; historial: {len(all_fixtures)}',flush=True)
    by_league=defaultdict(list)
    for f in all_fixtures:by_league[f['league']['id']].append(f)
    # Fetch every October club, including teams with no league-only H2H, so cup
    # antecedents can qualify a side rather than silently eliminating it.
    team_ids=sorted({t['id'] for f in october for t in f['teams'].values()})
    team_tasks=[(t,year) for t in team_ids for year in (2025,2026)]
    print(f'Historial de todas las competiciones: {len(team_ids)} clubes',flush=True)
    histories,team_errors=batch(team_tasks,lambda t:api.get('fixtures',team=t[0],season=t[1],**{'from':'2026-01-01','to':'2026-10-31'})['response'],'Historial completo de equipos')
    preliminary=[]
    exclusions=Counter()
    for f in october:
        if f['fixture']['status']['short'] not in DONE:
            exclusions['unfinished_or_cancelled']+=1
            continue
        h,a=f['teams']['home']['id'],f['teams']['away']['id']
        for side in ('home','away'):
            team=f['teams'][side]
            complete={r['fixture']['id']:r for y in (2025,2026) for r in histories.get((team['id'],y),[])}
            reverse=[r for r in complete.values() if r['fixture']['status']['short'] in DONE
                and r['teams']['home']['id']==a and r['teams']['away']['id']==h
                and kick(r).astimezone(TZ).year==2026 and kick(r)<kick(f)-timedelta(hours=3)]
            antecedent=max(reverse,key=kick,default=None)
            if not antecedent:
                exclusions['no_reversed_h2h_in_complete_history']+=1;continue
            oldside=side_for(antecedent,team['id'])
            goals=antecedent['goals'][oldside]
            required=2 if oldside=='home' else 1
            if goals is None or goals<required:
                exclusions['failed_h2h_goal_threshold']+=1;continue
            rival=f['teams']['away' if side=='home' else 'home']
            rank,status,band=reconstructed_rank(f,by_league[f['league']['id']],rival['id'])
            if status=='inside_top5_reconstructed':
                exclusions['rival_top5_reconstructed']+=1;continue
            preliminary.append({'fixture':f,'teamId':team['id'],'team':team['name'],'side':side,
                'rival':rival['name'],'rank':rank,'rankStatus':status,'rankBand':band,
                'antecedent':antecedent,'previousVenue':oldside,'antecedentGoals':goals,'requiredGoals':required})
    print(f'Prefiltro: {len(preliminary)} equipos-partido',flush=True)
    qualified,unknown=[],[]
    for row in preliminary:
        team=row['teamId'];f=row['fixture']
        history={r['fixture']['id']:r for y in (2025,2026) for r in histories.get((team,y),[])}
        if any(str((team,y)) in team_errors for y in (2025,2026)):
            row['pendingReason']='incomplete_team_history';unknown.append(row);continue
        # Re-evaluate the H2H with the full cross-competition history (avoids stale league-only antecedents).
        reverse=[r for r in history.values() if r['fixture']['status']['short'] in DONE and kick(r)<kick(f)-timedelta(hours=3)
            and r['teams']['home']['id']==f['teams']['away']['id'] and r['teams']['away']['id']==f['teams']['home']['id']]
        antecedent=max(reverse,key=kick,default=None)
        if not antecedent:
            exclusions['h2h_missing_in_complete_history']+=1;continue
        oldside=side_for(antecedent,team)
        if antecedent['goals'][oldside] is None or antecedent['goals'][oldside]<(2 if oldside=='home' else 1):
            exclusions['cross_competition_h2h_failed']+=1;continue
        row.update(antecedent=antecedent,antecedentGoals=antecedent['goals'][oldside],previousVenue=oldside)
        previous=max([r for r in history.values() if r['fixture']['status']['short'] in DONE and kick(r)<kick(f)-timedelta(hours=3)],key=kick,default=None)
        row['previous']=previous
        if previous is None:
            row['pendingReason']='previous_match_missing';unknown.append(row);continue
        if previous['teams'][side_for(previous,team)].get('winner') is not True:
            exclusions['previous_match_not_won']+=1;continue
        if row['rankStatus']!='outside_top5_reconstructed':
            row['pendingReason']=row['rankStatus'];unknown.append(row);continue
        qualified.append(row)
    event_ids=sorted({r['fixture']['fixture']['id'] for r in qualified+unknown})
    print(f'Clasificación reconstruida: {len(qualified)} aptos previos; {len(unknown)} pendientes; eventos de {len(event_ids)} partidos',flush=True)
    events,event_errors=batch(event_ids,lambda id:api.get('fixtures/events',fixture=id)['response'],'Minutos de gol')
    for row in qualified+unknown:
        f=row['fixture'];id=f['fixture']['id']
        timeline,state=goal_timeline(f,events[id]) if id in events else (None,'events_request_failed')
        row['eventsStatus']=state
        row['goalEvents']=timeline
        if timeline is not None:
            row.update(settle_entry(row['teamId'],timeline))
        elif ((f.get('score',{}).get('halftime') or {}).get(row['side']) or 0)>0:
            row.update(entry=False,teamGoalAfter70=None,anyGoalAfter70=None,reason='chosen_team_scored_in_verified_halftime')
        else:
            row.update(entry=None,teamGoalAfter70=None,anyGoalAfter70=None,reason=state)
    entries=[r for r in qualified if r['entry'] is True]
    unique_entries={r['fixture']['fixture']['id'] for r in entries}
    result={'period':{'from':'2026-10-01','to':'2026-10-31','timezone':'America/Bogota'},
        'generatedAt':datetime.now(TZ).isoformat(),'configuredLeagues':config['leagues'],
        'summary':{'fixturesOctober':len(october),'finishedFixtures':sum(f['fixture']['status']['short'] in DONE for f in october),
            'prequalifiedTeams':len(qualified),'prequalifiedMatches':len({r['fixture']['fixture']['id'] for r in qualified}),
            'entriesTeams':len(entries),'entriesMatches':len(unique_entries),
            'prequalifiedMatchesWithoutEntry':len({r['fixture']['fixture']['id'] for r in qualified}-unique_entries),
            'chosenTeamGoalSuccess':sum(r['teamGoalAfter70'] for r in entries),'anyGoalSuccessTeams':sum(r['anyGoalAfter70'] for r in entries),
            'anyGoalSuccessMatches':len({r['fixture']['fixture']['id'] for r in entries if r['anyGoalAfter70']}),
            'noEntryAlreadyScored':sum(r['entry'] is False for r in qualified),
            'eventsUnresolved':sum(r['entry'] is None for r in qualified),
            'pendingHistoricalCriteria':len(unknown)},
        'exclusions':dict(exclusions),'requestErrors':{'leagues':errors,'teams':team_errors,'events':event_errors},
        'qualified':qualified,'pending':unknown,
        'coverage':[{'id':l['id'],'name':l['name'],'octoberFixtures':sum(f['league']['id']==l['id'] for f in october),
            'seasonsFetched':[y for y in (2025,2026) if (l['id'],y) in leagues]} for l in config['leagues']],
        'limitations':[
            'Simulación condicional; las posiciones se reconstruyen con 3 puntos por victoria y 1 por empate, sin archivo oficial de posiciones históricas ni sanciones.',
            'Se muestra una banda conservadora de posiciones posibles. Solo se acepta fuera del top 5 si toda la banda queda fuera, incluso con cualquier desempate.',
            'No se utiliza el resultado de otro partido iniciado menos de 3 horas antes. Se ensayan límites de puntos para cualquier resultado posible; si la pertenencia al top 5 sigue siendo ambigua, queda pendiente.',
            'Se separan como pendientes las fases complejas, tablas por conferencia (MLS), arrastres de puntos y copas sin tabla doméstica.',
            'Se consultan todos los clubes de octubre en todas las competiciones de temporadas 2025 y 2026 para revisar el último partido y el último H2H del mismo año.',
            'No se simula el juicio de dominio ni umbrales de estadísticas al 70, porque no están definidos. No se usan estadísticas finales para decidir una entrada.',
            'La entrada es en 70:00 con cero goles del elegido. Un gol registrado como minuto 70 se trata como anterior o simultáneo; el éxito exige minuto mayor a 70.',
            'Se incluye descuento del segundo tiempo (90+), se excluye prórroga y tandas. Los eventos se concilian con el marcador de tiempo reglamentario.',
            'Si un evento de gol del primer tiempo contradice un descanso de cero goles, solo se retira si el resto concilia con descanso y resultado final. Un gol confirmado en el descanso basta para descartar la entrada aunque otros eventos sean inconsistentes.',
            'No hay cuotas históricas ni registro de dinero apostado; los porcentajes no son rentabilidad y no prueban apuestas reales.'
        ]}
    (OUT/'analysis.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result['summary'],ensure_ascii=False,indent=2),flush=True)
    print('Consultas nuevas: '+str(api.calls),flush=True)

if __name__=='__main__':main()
