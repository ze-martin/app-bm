"""Explicitly select an additional private chat, without exposing the bot token."""
import json
import os
import urllib.request
try:
    from .refresh import ROOT,load_env
    from .telegram_monitor import recipients,telegram
except ImportError:
    from refresh import ROOT,load_env
    from telegram_monitor import recipients,telegram

def main():
    load_env(ROOT/'.env')
    token=os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:raise SystemExit('Primero configura el bot principal.')
    print('La otra persona debe abrir TU bot en Telegram y enviar /start ahora.')
    input('Cuando lo haya hecho, pulsa Enter...')
    try:
        request=urllib.request.Request('https://api.telegram.org/bot'+token+'/getUpdates',data=json.dumps({'allowed_updates':['message'],'limit':100}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=20) as response:payload=json.load(response)
        current=recipients()
        chats={str(m['message']['chat']['id']):m['message']['chat'] for m in payload.get('result',[]) if m.get('message',{}).get('chat',{}).get('type')=='private'}
        options=[(key,chat) for key,chat in chats.items() if key not in current]
        if not options:raise SystemExit('No hay chats nuevos. Pide a la otra persona que envíe /start a tu bot y repite.')
        for n,(_,chat) in enumerate(options,1):
            print(str(n)+'. '+chat.get('first_name','')+' '+chat.get('last_name','')+' @'+chat.get('username','sin_usuario'))
        choice=int(input('Número del destinatario que quieres agregar (0 cancela): '))
        if choice==0:return
        if not 1<=choice<=len(options):raise SystemExit('Selección inválida; no se guardó nada.')
        chat=options[choice-1][0]
        telegram(token,chat,'BM · Prueba para nuevo destinatario. Se ha solicitado agregar este chat a los avisos de partidos al minuto 65. No es una recomendación de apuesta.')
        path=ROOT/'.env'
        kept=[line for line in path.read_text(encoding='utf-8').splitlines() if not line.startswith('TELEGRAM_CHAT_IDS=')]
        kept.append('TELEGRAM_CHAT_IDS='+','.join(dict.fromkeys(current+[chat])))
        path.write_text('\n'.join(kept)+'\n',encoding='utf-8')
        print('Destinatario agregado. Prueba enviada. Se conserva el destinatario original.')
        print('Si el monitor estaba abierto antes de instalar esta mejora, ciérralo con Ctrl+C y vuelve a iniciarlo.')
    except SystemExit:raise
    except Exception:raise SystemExit('No se pudo completar el alta. Revisa la conexión y repite; no compartas el token.') from None

if __name__=='__main__':main()
