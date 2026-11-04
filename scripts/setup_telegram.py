"""Interactive local setup: token is never displayed or committed."""
import getpass
import argparse
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--test',action='store_true',help='Enviar confirmación al chat privado al terminar')
    args=parser.parse_args()
    print('Crea un bot con @BotFather y envíale /start desde tu Telegram.')
    token=getpass.getpass('Token del bot (oculto): ').strip()
    if not token or '\n' in token or '\r' in token:
        raise SystemExit('Token inválido.')
    try:
        req=urllib.request.Request('https://api.telegram.org/bot'+token+'/getUpdates',
            data=json.dumps({'allowed_updates':['message'],'limit':100}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=20) as r:
            data=json.load(r)
        chats={m['message']['chat']['id']:m['message']['chat'] for m in data.get('result',[]) if m.get('message',{}).get('chat',{}).get('type')=='private'}
        if len(chats)!=1:
            raise SystemExit('No se identificó un único chat privado. Envía /start al bot y repite con un bot dedicado.')
        chat=next(iter(chats))
    except SystemExit:
        raise
    except Exception:
        raise SystemExit('No se pudo validar el bot. Revisa el token y /start; no se guardó nada.') from None
    path=ROOT/'.env'
    old=path.read_text(encoding='utf-8') if path.exists() else ''
    kept=[line for line in old.splitlines() if not line.startswith(('TELEGRAM_BOT_TOKEN=','TELEGRAM_CHAT_ID='))]
    kept.extend(['TELEGRAM_BOT_TOKEN='+token,'TELEGRAM_CHAT_ID='+str(chat)])
    path.write_text('\n'.join(kept)+'\n',encoding='utf-8')
    print('Telegram configurado en .env local, excluido de Git.')
    if args.test:
        from telegram_monitor import telegram
        try:
            telegram(token,str(chat),'BM conectado. Los avisos están preparados para el minuto real 65 y la revisión al 70. Inicia el monitor para recibirlos; este mensaje solo confirma la conexión.')
        except RuntimeError:
            raise SystemExit('Credenciales guardadas, pero no se pudo enviar la confirmación. Revisa /start y la conexión.') from None
        print('Confirmación enviada a tu chat privado. El monitor se inicia por separado.')
    else:
        print('No se ha enviado ningún mensaje.')

if __name__=='__main__':
    main()
