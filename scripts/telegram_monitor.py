"""Minute-65 Telegram notice and separate minute-70 statistics capture."""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
try:
    from .refresh import ROOT, TZ, load_env
    from .live_statistics import fetch_statistics, save_observation, publish_observations, statistics_text, normalize_stats
except ImportError:
    from refresh import ROOT, TZ, load_env
    from live_statistics import fetch_statistics, save_observation, publish_observations, statistics_text, normalize_stats

def fetch_live(key):
    # Never use the one-hour historical API cache for live scores.
    request=urllib.request.Request('https://v3.football.api-sports.io/fixtures?live=all',headers={'x-apisports-key':key})
    with urllib.request.urlopen(request,timeout=20) as response:
        data=json.load(response)
    if data.get('errors'):
        raise RuntimeError('API-Football no entregó datos en vivo.')
    return data.get('response',[])

def sync_published_shortlist():
    """Use scheduled Pages refreshes without overwriting a newer local snapshot."""
    path=ROOT/'data/matches.json'
    request=urllib.request.Request('https://ze-martin.github.io/app-bm/data/matches.json?t='+str(int(time.time())),headers={'Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=25) as response:
        remote=json.load(response)
    stamp=datetime.fromisoformat(remote['updatedAt'])
    now=datetime.now(TZ)
    if not isinstance(remote.get('matches'),list) or remote.get('demo') or not timedelta(minutes=-5)<=now-stamp<=timedelta(hours=24):
        raise RuntimeError('La lista publicada no está vigente; se conserva la copia local.')
    local=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not local.get('updatedAt') or stamp>datetime.fromisoformat(local['updatedAt']):
        temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(remote,ensure_ascii=False),encoding='utf-8');temp.replace(path)
        print('Preselección sincronizada con la actualización publicada.',flush=True)

def live_candidate_in_window(selection, fixture, first, last, now=None, require_zero=True):
    check=selection.get('rankVerification',{})
    if check.get('status')=='verified':
        try:
            age=(now or datetime.now(TZ))-datetime.fromisoformat(check['checkedAt'])
            if not timedelta(minutes=-5) <= age <= timedelta(hours=24):
                return False
        except (KeyError,ValueError,TypeError):
            return False
    state=fixture['fixture']['status']
    minute=state.get('elapsed')
    side=next((s for s in ('home','away') if fixture['teams'][s]['id']==selection['teamId']),None)
    return (selection.get('prequalified') is True and state['short']=='2H'
        and type(minute) is int and first <= minute <= last and side is not None
        and type(fixture['goals'].get(side)) is int and fixture['goals'][side]>=0
        and (not require_zero or fixture['goals'][side]==0))

def should_alert(selection,fixture,now=None):
    return live_candidate_in_window(selection,fixture,65,69,now,require_zero=False)

def should_capture(selection,fixture,now=None):
    return live_candidate_in_window(selection,fixture,70,75,now)

def telegram(token, chat_id, text):
    request=urllib.request.Request('https://api.telegram.org/bot'+token+'/sendMessage',
        data=json.dumps({'chat_id':chat_id,'text':text,'disable_web_page_preview':True}).encode(),
        headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            result=json.load(response)
        if not result.get('ok'):
            raise RuntimeError('Telegram rechazó el envío.')
    except (urllib.error.URLError, TimeoutError):
        # Token lives in the URL: never propagate the URL in exception output.
        raise RuntimeError('No se pudo enviar el aviso a Telegram.') from None

def recipients():
    # Read the local list on each poll so adding a recipient needs no restart.
    values=dict(os.environ)
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith(('TELEGRAM_CHAT_ID=','TELEGRAM_CHAT_IDS=')):
                key,value=line.split('=',1);values[key]=value.strip()
    return list(dict.fromkeys(c.strip() for c in (values.get('TELEGRAM_CHAT_ID','')+','+values.get('TELEGRAM_CHAT_IDS','')).split(',') if c.strip()))

def message(s, f, statistics=None):
    minute=f['fixture']['status']['elapsed']
    side=next(side for side in ('home','away') if f['teams'][side]['id']==s['teamId'])
    already_scored=f['goals'][side]>0
    status=('DESCARTADO PARA EL MÉTODO ORIGINAL: el elegido ya marcó.\n'
        'Alternativas para revisión manual desde DESPUÉS del 70 hasta el final: '
        'menos de 0,5 (ningún gol de ambos equipos) o menos de 1,5 (cero o un gol).\n'
        'Octubre, descartados: menos de 0,5 = 73/165 (44,2%; uno pendiente); '
        'menos de 1,5 = 141/166 (84,9%). Muestra reconstruida; no son probabilidades del partido actual.\n'
        'No hay una regla validada para elegir mercado con las estadísticas actuales. Revisar cuota y segundo tiempo al 70.\n'
        if already_scored else
        'ELEGIDO AÚN SIN GOL: revisar el método original al 70.\n'
        'Comprobar dominio y estadísticas SOLO del segundo tiempo. Si marca antes del 70, descartar el método original y revisar alternativas de menos goles manualmente.\n')
    return (f"BM · AVISO PREVIO · minuto {minute}\n"
        f"Revisar para el 70′: faltan aproximadamente {max(0,70-minute)} minutos de juego.\n"
        f"{f['teams']['home']['name']} {f['goals']['home']}–{f['goals']['away']} {f['teams']['away']['name']}\n"
        f"Equipo preseleccionado: {s['team']}.\n"+status+
        f"Estadísticas al momento del aviso ({minute}′):\n"
        +(statistics_text(statistics,f)+'\n' if statistics is not None else '')+
        "Aviso previo, no recomendación automática. No usar el total final del partido para liquidar estos mercados: solo goles posteriores al 70, incluido el descuento.\n"
        "https://ze-martin.github.io/app-bm/")

def run_once(dry_run=False,capture_only=False,publish=False):
    try:
        from .tracking_history import sync
    except ImportError:
        from tracking_history import sync
    sync(ROOT)
    now=datetime.now(TZ)
    data=json.loads((ROOT/'data/matches.json').read_text(encoding='utf-8'))
    # A shortlist must be refreshed daily. Never alert from an old multi-day report.
    if not data.get('updatedAt') or now-datetime.fromisoformat(data['updatedAt'])>timedelta(hours=24):
        raise RuntimeError('Preselección de más de 24 horas: actualizar datos antes de monitorear.')
    watch={m['fixture']['fixture']['id']:m for m in data['matches']
        if any(s.get('prequalified') for s in m['selections'])
        and m['fixture']['fixture']['status']['short'] in {'NS','1H','HT','2H'}
        and timedelta(hours=-4) <= datetime.fromisoformat(m['fixture']['fixture']['date'])-now <= timedelta(minutes=10)}
    if not watch:
        print('Sin candidatos en ventana de seguimiento.',flush=True)
        return
    key=os.environ.get('FOOTBALL_API_KEY')
    if not key:
        raise RuntimeError('Falta FOOTBALL_API_KEY.')
    token, chats=os.environ.get('TELEGRAM_BOT_TOKEN'),recipients()
    if not dry_run and not capture_only and (not token or not chats):
        raise RuntimeError('Configurar Telegram con scripts/setup_telegram.py antes de activar envíos.')
    ledger=ROOT/'.cache/telegram-sent.json'
    sent=json.loads(ledger.read_text(encoding='utf-8')) if ledger.exists() else {}
    deliveries=ROOT/'.cache/telegram-deliveries.json'
    delivered=json.loads(deliveries.read_text(encoding='utf-8')) if deliveries.exists() else {}
    # Old installations sent only to the original recipient.
    primary=os.environ.get('TELEGRAM_CHAT_ID')
    if not deliveries.exists():
        for identity,stamp in sent.items():
            if primary:delivered.setdefault(identity+':'+primary,stamp)
    live=fetch_live(key)
    for f in live:
        match=watch.get(f['fixture']['id'])
        if not match:
            continue
        captures=[s for s in match['selections'] if should_capture(s,f)]
        alerts=[s for s in match['selections'] if should_alert(s,f)
            and any(f"{f['fixture']['id']}:{s['teamId']}:65:{chat}" not in delivered for chat in chats)]
        if not captures and (capture_only or not alerts):
            continue
        try:
            statistics=fetch_statistics(key,f)
        except Exception:
            statistics=normalize_stats({'response':[]},f)
            print('Estadísticas no disponibles para fixture '+str(f['fixture']['id']),flush=True)
        observations,changed=save_observation(ROOT,f,captures,statistics,now) if captures else (None,False)
        if publish and captures:
            try:
                publish_observations(observations)
            except RuntimeError as e:
                print(str(e),flush=True)
        if capture_only:
            continue
        for s in alerts:
            identity=f"{f['fixture']['id']}:{s['teamId']}:65"
            if dry_run:
                print('SIMULACIÓN: '+message(s,f,statistics),flush=True)
            else:
                for chat in chats:
                    delivery=identity+':'+chat
                    if delivery in delivered:continue
                    try:
                        telegram(token,chat,message(s,f,statistics))
                    except RuntimeError:
                        print('No se pudo entregar a un destinatario; se reintentará en la ventana del aviso.',flush=True)
                        continue
                    delivered[delivery]=now.isoformat()
                    deliveries.parent.mkdir(exist_ok=True)
                    temp=deliveries.with_suffix('.tmp')
                    temp.write_text(json.dumps(delivered),encoding='utf-8');temp.replace(deliveries)
                    sent.setdefault(identity,now.isoformat())
                    temp=ledger.with_suffix('.tmp')
                    temp.write_text(json.dumps(sent),encoding='utf-8');temp.replace(ledger)
                print('Aviso enviado para fixture '+str(f['fixture']['id']),flush=True)
    history=sync(ROOT)
    if publish:
        try:
            publish_observations(history,path='data/history.json')
        except RuntimeError as e:
            print(str(e),flush=True)
    print('Consulta en vivo completada; '+str(len(watch))+' partidos en seguimiento.',flush=True)

def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser()
    p.add_argument('--env',type=Path,default=ROOT/'.env')
    p.add_argument('--football-env',type=Path)
    p.add_argument('--once',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--capture-only',action='store_true',help='Capturar estadísticas sin enviar Telegram')
    p.add_argument('--publish',action='store_true',help='Publicar solo el archivo deportivo para el dashboard')
    p.add_argument('--interval',type=int,default=60)
    p.add_argument('--hours',type=float,default=0,help='Detener al cumplir estas horas; 0 mantiene el proceso activo')
    args=p.parse_args()
    if args.interval<30:
        p.error('El intervalo mínimo es 30 segundos.')
    if args.hours<0:
        p.error('--hours no puede ser negativo.')
    load_env(args.env)
    if args.football_env:
        load_env(args.football_env)
    # A lock prevents duplicate monitor processes from sending duplicate alerts.
    lock=ROOT/'.cache/telegram-monitor.lock'
    lock.parent.mkdir(exist_ok=True)
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        p.error('Ya hay un monitor activo. Si se cerró abruptamente, revisar y retirar .cache/telegram-monitor.lock.')
    os.close(fd)
    deadline=time.monotonic()+args.hours*3600 if args.hours else None
    next_sync=0
    try:
        while True:
            if time.monotonic()>=next_sync:
                try:
                    sync_published_shortlist()
                except Exception:
                    print('No se pudo sincronizar Pages; se comprobará la vigencia de la lista local.',flush=True)
                next_sync=time.monotonic()+900
            try:
                run_once(args.dry_run,args.capture_only,args.publish)
            except Exception as e:
                # Avoid emitting exception URLs, which may include credentials.
                print('Monitor: '+(str(e) if isinstance(e,RuntimeError) else 'consulta fallida; se reintentará.'),flush=True)
                if args.once:
                    raise SystemExit(1)
            if args.once or (deadline is not None and time.monotonic()+args.interval>=deadline):
                break
            time.sleep(args.interval)
    finally:
        lock.unlink(missing_ok=True)

if __name__=='__main__':
    main()
