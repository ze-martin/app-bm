"""Fetch, normalize and optionally publish minute-70 observations."""
import json
import math
import subprocess
import urllib.request
import urllib.error
import base64
from datetime import datetime
from pathlib import Path

METRICS={'possession':'Ball Possession','corners':'Corner Kicks','shots':'Total Shots','onTarget':'Shots on Goal',
    'insideBox':'Shots insidebox','blocked':'Blocked Shots','saves':'Goalkeeper Saves',
    'yellowCards':'Yellow Cards','redCards':'Red Cards','xG':'expected_goals'}

def normalize_stats(payload, fixture):
    by_team={r['team']['id']:r for r in payload.get('response',[])}
    result={}
    for side in ('home','away'):
        raw=by_team.get(fixture['teams'][side]['id'],{})
        result[side]={}
        for period, field in [('total','statistics'),('secondHalf','statistics_2h')]:
            values={v['type']:v.get('value') for v in raw.get(field,[])}
            parsed={}
            for key,label in METRICS.items():
                value=values.get(label)
                try:
                    n=float(str(value).rstrip('%')) if value is not None else None
                    if n is not None and (not math.isfinite(n) or n<0 or (key=='possession' and n>100) or (key not in {'possession','xG'} and not n.is_integer())):
                        n=None
                    parsed[key]=int(n) if n is not None and n.is_integer() else n
                except (ValueError,TypeError):
                    parsed[key]=None
            result[side][period]=parsed
            shots, on_target=parsed['shots'],parsed['onTarget']
            parsed['accuracy']=round(100*on_target/shots,1) if shots and on_target is not None and on_target<=shots else None
    return result

def fetch_statistics(key,fixture):
    request=urllib.request.Request('https://v3.football.api-sports.io/fixtures/statistics?fixture='+str(fixture['fixture']['id'])+'&half=true',headers={'x-apisports-key':key})
    with urllib.request.urlopen(request,timeout=20) as response:
        payload=json.load(response)
    if payload.get('errors'):
        raise RuntimeError('Estadísticas de API-Football no disponibles.')
    return normalize_stats(payload,fixture)

def save_observation(root,fixture,selections,statistics,now):
    path=Path(root)/'data/live70.json'
    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'source':'API-Football','observations':[]}
    # Preserve the first captured observation for each team; never relabel a later minute as 70.
    seen={(r['fixtureId'],s['teamId']) for r in data['observations'] for s in r['selections']}
    fresh=[{'teamId':s['teamId'],'team':s['team']} for s in selections if (fixture['fixture']['id'],s['teamId']) not in seen]
    if fresh:
        data['observations'].append({'fixtureId':fixture['fixture']['id'],'capturedAt':now.isoformat(),
            'minute':fixture['fixture']['status']['elapsed'],'teams':fixture['teams'],'goals':fixture['goals'],
            'selections':fresh,'statistics':statistics})
        # Keep seven days of observations.
        data['observations']=[r for r in data['observations'] if (now-datetime.fromisoformat(r['capturedAt'])).total_seconds()<=7*86400]
        data['updatedAt']=now.isoformat()
        path.parent.mkdir(exist_ok=True)
        temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        temp.replace(path)
    return data, bool(fresh)

def publish_observations(data):
    """Public sports data only. No Actions build per live observation."""
    process=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True)
    credential=dict(line.split('=',1) for line in process.stdout.splitlines() if '=' in line)
    token=credential.get('password')
    if not token:
        raise RuntimeError('No hay autenticación GitHub para publicar las observaciones.')
    def api(path,method='GET',body=None):
        req=urllib.request.Request('https://api.github.com/repos/ze-martin/app-bm'+path,method=method,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'},
            data=json.dumps(body).encode() if body is not None else None)
        with urllib.request.urlopen(req,timeout=25) as response:
            return json.load(response)
    branch='codex/live70'
    try:
        try:
            api('/git/ref/heads/'+branch)
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
            head=api('/git/ref/heads/main')['object']['sha']
            api('/git/refs','POST',{'ref':'refs/heads/'+branch,'sha':head})
        body={'message':'Actualizar observaciones deportivas del minuto 70','branch':branch,
            'content':base64.b64encode(json.dumps(data,ensure_ascii=False).encode()).decode()}
        try:
            old=api('/contents/data/live70.json?ref='+branch)
            if base64.b64decode(old.get('content','')) == base64.b64decode(body['content']):
                return
            body['sha']=old['sha']
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
        api('/contents/data/live70.json','PUT',body)
    except Exception:
        raise RuntimeError('No se pudo publicar el archivo deportivo en GitHub; se conserva copia local.') from None

def statistics_text(stats,fixture):
    def value(v,percent=False):
        return 'N/D' if v is None else str(v)+('%' if percent else '')
    lines=[]
    for period,label in [('secondHalf','SEGUNDO TIEMPO'),('total','ACUMULADO DEL PARTIDO')]:
        lines.append(label+' · local / visita')
        for key,title in [('possession','Posesión'),('corners','Córners'),('shots','Disparos totales'),('onTarget','A puerta'),
            ('insideBox','Disparos dentro del área'),('blocked','Disparos bloqueados'),('saves','Atajadas'),
            ('yellowCards','Amarillas'),('redCards','Rojas'),('xG','xG'),('accuracy','Precisión de tiro')]:
            lines.append(title+': '+value(stats['home'][period].get(key),key in {'possession','accuracy'})+' / '+value(stats['away'][period].get(key),key in {'possession','accuracy'}))
    reds=[stats[side]['total'].get('redCards') for side in ('home','away')]
    if any(r is not None and r>0 for r in reds):
        lines.append('ATENCIÓN: hay expulsiones registradas; revisar cómo afectan al equipo elegido.')
    lines.append('N/D = dato no disponible. No se estima la posesión del 2T restando porcentajes.')
    return '\n'.join(lines)
