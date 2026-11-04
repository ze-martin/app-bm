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

def live_candidate_in_window(selection, fixture, first, last, now=None):
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
        and fixture['goals'].get(side)==0)

def should_alert(selection,fixture,now=None):
    return live_candidate_in_window(selection,fixture,65,69,now)

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

def message(s, f, statistics=None):
    minute=f['fixture']['status']['elapsed']
    return (f"BM · AVISO PREVIO · minuto {minute}\n"
        f"Revisar para el 70′: faltan aproximadamente {max(0,70-minute)} minutos de juego.\n"
        f"{f['teams']['home']['name']} {f['goals']['home']}–{f['goals']['away']} {f['teams']['away']['name']}\n"
        f"Equipo preseleccionado: {s['team']} (aún sin gol).\n"
        f"Estadísticas al momento del aviso ({minute}′):\n"
        +(statistics_text(statistics,f)+'\n' if statistics is not None else '')+
        "Comprobar dominio y estadísticas SOLO del segundo tiempo. Si el elegido marca antes del 70, descartar. No es una orden de apostar.\n"
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
    token, chat=os.environ.get('TELEGRAM_BOT_TOKEN'),os.environ.get('TELEGRAM_CHAT_ID')
    if not dry_run and not capture_only and (not token or not chat):
        raise RuntimeError('Configurar Telegram con scripts/setup_telegram.py antes de activar envíos.')
    ledger=ROOT/'.cache/telegram-sent.json'
    sent=json.loads(ledger.read_text(encoding='utf-8')) if ledger.exists() else {}
    live=fetch_live(key)
    for f in live:
        match=watch.get(f['fixture']['id'])
        if not match:
            continue
        captures=[s for s in match['selections'] if should_capture(s,f)]
        alerts=[s for s in match['selections'] if should_alert(s,f)
            and f"{f['fixture']['id']}:{s['teamId']}:65" not in sent]
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
                telegram(token,chat,message(s,f,statistics))
                sent[identity]=now.isoformat()
                ledger.parent.mkdir(exist_ok=True)
                temp=ledger.with_suffix('.tmp')
                temp.write_text(json.dumps(sent),encoding='utf-8')
                temp.replace(ledger)
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
    try:
        while True:
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
