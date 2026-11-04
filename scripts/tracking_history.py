"""Durable public sports journal. Never infer a sent notice or a placed bet."""
import json
import argparse
import subprocess
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
try:
    from .refresh import ROOT, TZ, API, load_env
    from .backtest_october import goal_timeline, settle_entry
except ImportError:
    from refresh import ROOT, TZ, API, load_env
    from backtest_october import goal_timeline, settle_entry

START = '2026-11-03'

def read(root=ROOT):
    path=Path(root)/'data/history.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'since':START,'records':[]}

def write(data,root=ROOT):
    path=Path(root)/'data/history.json'
    path.parent.mkdir(exist_ok=True)
    data['updatedAt']=datetime.now(TZ).isoformat()
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    temp.replace(path)

def ingest(data,snapshot,origin='saved_snapshot'):
    rows={r['id']:r for r in data['records']}
    for m in snapshot.get('matches',[]):
        f=m['fixture']; date=f['fixture']['date']
        if datetime.fromisoformat(date).astimezone(TZ).date().isoformat()<START:continue
        for s in m['selections']:
            if not s.get('prequalified'):continue
            identity=f"{f['fixture']['id']}:{s['teamId']}"
            # An after-kickoff evaluation is not evidence of a pregame detection.
            evaluated=snapshot.get('evaluatedAt') or snapshot.get('updatedAt')
            before=bool(evaluated and datetime.fromisoformat(evaluated)<datetime.fromisoformat(date))
            if identity not in rows:
                rows[identity]={'id':identity,'fixtureId':f['fixture']['id'],'teamId':s['teamId'],
                    'team':s['team'],'kickoff':date,'home':f['teams']['home']['name'],
                    'away':f['teams']['away']['name'],'league':f.get('league',{}).get('name','Sin liga'),
                    'detectedAt':evaluated,'pregameEvidence':before,'origin':origin,
                    'criteria':s,'notice':None,'capture':None,'result':None,
                    'recommendation':'manual_review_not_recorded','bet':'not_recorded'}
            elif before and not rows[identity]['pregameEvidence']:
                rows[identity].update(pregameEvidence=True,detectedAt=evaluated,criteria=s,origin=origin)
    data['records']=sorted(rows.values(),key=lambda r:(r['kickoff'],r['id']))

def sync(root=ROOT):
    data=read(root)
    ingest(data,json.loads((Path(root)/'data/matches.json').read_text(encoding='utf-8')))
    observations=Path(root)/'data/live70.json'
    obs=json.loads(observations.read_text(encoding='utf-8')).get('observations',[]) if observations.exists() else []
    ledger=Path(root)/'.cache/telegram-sent.json'
    sent=json.loads(ledger.read_text(encoding='utf-8')) if ledger.exists() else {}
    for r in data['records']:
        for minute in (65,70):
            stamp=sent.get(r['id']+':'+str(minute))
            if stamp:r['notice']={'sentAt':stamp,'targetMinute':minute}
        capture=next((o for o in obs if o['fixtureId']==r['fixtureId'] and any(s['teamId']==r['teamId'] for s in o['selections'])),None)
        if capture:r['capture']=capture
    write(data,root)
    return data

def settle(data,api):
    fixtures={}
    for r in data['records']:
        if r.get('result',{} ) and r['result'].get('status')=='settled':continue
        if datetime.fromisoformat(r['kickoff'])>datetime.now(TZ)-timedelta(hours=2):continue
        fid=r['fixtureId']
        if fid not in fixtures:
            response=api.get('fixtures',id=fid)['response']
            if not response:continue
            f=response[0]
            if f['fixture']['status']['short'] not in {'FT','AET','PEN'}:continue
            goals,evidence=goal_timeline(f,api.get('fixtures/events',fixture=fid)['response'])
            fixtures[fid]=(f,goals,evidence)
        f,goals,evidence=fixtures[fid]
        r['result']={'status':'pending' if goals is None else 'settled','evidence':evidence,
            'score':f['score']['fulltime'],'checkedAt':datetime.now(TZ).isoformat()}
        if goals is not None:r['result'].update(settle_entry(r['teamId'],goals),goalsAfter70=[g for g in goals if g['minute']>70])

def main():
    p=argparse.ArgumentParser();p.add_argument('--recover',action='store_true');p.add_argument('--settle',action='store_true');p.add_argument('--remote',action='store_true');p.add_argument('--publish',action='store_true');p.add_argument('--env',type=Path,default=Path('D:/CODEX/APUESTAS/.env'));a=p.parse_args()
    if a.remote:
        try:
            with urllib.request.urlopen('https://raw.githubusercontent.com/ze-martin/app-bm/codex/live70/data/history.json',timeout=25) as response:remote=json.load(response)
            data=read();rows={r['id']:r for r in data['records']}
            for r in remote['records']:
                old=rows.get(r['id'],{})
                # Retain evidence accumulated by either writer.
                merged={**old,**r}
                for key in ('notice','capture','result'):
                    merged[key]=r.get(key) or old.get(key)
                rows[r['id']]=merged
            data['records']=list(rows.values());write(data)
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
    if a.recover:
        data=read()
        commits=subprocess.check_output(['git','log','--reverse','--format=%H','--','data/matches.json'],text=True).splitlines()
        for commit in commits:
            raw=subprocess.check_output(['git','show',commit+':data/matches.json'])
            ingest(data,json.loads(raw),origin='git_snapshot:'+commit)
        write(data)
    data=sync()
    if a.settle:
        load_env(a.env);settle(data,API());write(data)
    if a.publish:
        try:
            from .live_statistics import publish_observations
        except ImportError:
            from live_statistics import publish_observations
        publish_observations(data,path='data/history.json')
    print(json.dumps({'records':len(data['records']),'pregame':sum(r['pregameEvidence'] for r in data['records']),
        'notices':sum(bool(r['notice']) for r in data['records']),'captures':sum(bool(r['capture']) for r in data['records'])}))

if __name__=='__main__':main()
