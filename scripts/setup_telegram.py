"""Interactive local setup: token is never displayed or committed."""
import getpass
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
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
    print('Telegram configurado en .env local, excluido de Git. No se ha enviado ningún mensaje.')

if __name__=='__main__':
    main()
