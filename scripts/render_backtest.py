"""Build a transparent HTML/CSV historical report from completed analysis."""
import csv
import html
import json
from collections import Counter
from pathlib import Path
from datetime import datetime
try:
    from .backtest_october import OUT,TZ
except ImportError:
    from backtest_october import OUT,TZ

def esc(value):return html.escape(str(value if value is not None else 'N/D'),quote=True)
def when(value):return datetime.fromisoformat(value).astimezone(TZ).strftime('%d/%m/%Y %H:%M')
def score(f):return f"{f['teams']['home']['name']} {f['goals']['home']}–{f['goals']['away']} {f['teams']['away']['name']}"
def pct(n,d):return f'{100*n/d:.1f}%' if d else 'N/D'
REASONS={'complex_phase':'Fase compleja / posible arrastre de puntos','cup_table_not_domestic':'Copa: falta tabla doméstica del rival',
    'conference_table':'MLS: tabla por conferencia no reconstruida',
    'tie_crosses_fifth':'Empate en puntos que cruza el quinto puesto','overlapping_previous_fixture':'Otro encuentro previo podría seguir en juego',
    'insufficient_table_history':'Historial insuficiente para reconstruir tabla','missing_historical_score':'Marcador histórico ausente',
    'incomplete_team_history':'Historial del equipo incompleto','previous_match_missing':'Último partido no disponible'}

def main():
    data=json.loads((OUT/'analysis.json').read_text(encoding='utf-8'))
    summary=data['summary']
    records=[(r,'reconstructed') for r in data['qualified']]+[(r,'pending') for r in data['pending']]
    records.sort(key=lambda x:(x[0]['fixture']['fixture']['date'],x[0]['team']))
    columns=['Fixture ID','Fecha Bogotá/Lima','Liga','Local','Visitante','Equipo elegido','Estatus histórico',
        'Puesto mínimo reconstruido del rival','Puesto máximo reconstruido','Motivo pendiente','H2H fecha','H2H resultado',
        'Último partido fecha','Último partido resultado','Eventos validados','Entrada simulada al 70','Gol del elegido después del 70',
        'Cualquier gol después del 70','Minutos de goles reglamentarios']
    with (OUT/'detalle.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(columns)
        for r,state in records:
            f=r['fixture'];band=r['rankBand'] or [None,None]
            writer.writerow([f['fixture']['id'],when(f['fixture']['date']),f['league']['name'],f['teams']['home']['name'],
                f['teams']['away']['name'],r['team'],state,*band,REASONS.get(r.get('pendingReason'),''),
                when(r['antecedent']['fixture']['date']),score(r['antecedent']),
                when(r['previous']['fixture']['date']) if r.get('previous') else '',score(r['previous']) if r.get('previous') else '',
                r['eventsStatus'],r['entry'],r['teamGoalAfter70'],r['anyGoalAfter70'],
                ' / '.join(f"{g['minute']}"+(f"+{g['extra']}" if g.get('extra') else '')+f" (equipo {g['teamId']})" for g in r['goalEvents'] or [])])
    league_rows=[]
    for league in data['coverage']:
        pre=[r for r in data['qualified'] if r['fixture']['league']['id']==league['id']]
        entries=[r for r in pre if r['entry'] is True]
        pending=[r for r in data['pending'] if r['fixture']['league']['id']==league['id']]
        ids={r['fixture']['fixture']['id'] for r in entries}
        wins={r['fixture']['fixture']['id'] for r in entries if r['anyGoalAfter70']}
        league_rows.append(f"<tr><td>{esc(league['name'])}</td><td>{league['octoberFixtures']}</td><td>{len({r['fixture']['fixture']['id'] for r in pre})}</td><td>{len(ids)}</td><td>{len(wins)}</td><td>{pct(len(wins),len(ids))}</td><td>{len(pending)}</td></tr>")
    table_rows=[]
    for r,state in records:
        f=r['fixture'];rank='–'.join(map(str,r['rankBand'])) if r['rankBand'] else 'Pendiente'
        if state=='pending':status='Criterio histórico pendiente'
        elif r['entry'] is None:status='Eventos insuficientes'
        elif r['entry']:status='Entrada simulada al 70'
        else:status='Sin entrada: ya había marcado'
        def outcome(value):return 'Sí' if value is True else 'No' if value is False else 'N/D'
        goals=', '.join(f"{g['minute']}"+(f"+{g['extra']}" if g.get('extra') else '')+'′ '+('elegido' if g['teamId']==r['teamId'] else 'rival') for g in r['goalEvents'] or []) or 'Sin goles validados'
        details=f"H2H {when(r['antecedent']['fixture']['date'])}: {score(r['antecedent'])}. Último partido: {score(r['previous']) if r.get('previous') else 'N/D'}. Goles: {goals}."
        if state=='pending':details+=' '+REASONS.get(r.get('pendingReason'),r.get('pendingReason',''))
        league_name=f"{f['league']['country']} / {f['league']['name']}"
        table_rows.append(f'''<tr data-state="{state}" data-entry="{str(r['entry']).lower()}"><td>{esc(when(f['fixture']['date']))}</td><td>{esc(league_name)}</td><td>{esc(score(f))}<br><b>Elegido: {esc(r['team'])}</b><details><summary>Evidencia</summary>{esc(details)}</details></td><td>{esc(rank)}</td><td>{esc(status)}</td><td>{outcome(r['teamGoalAfter70'])}</td><td>{outcome(r['anyGoalAfter70'])}</td></tr>''')
    pending_counts=Counter(REASONS.get(r.get('pendingReason'),r.get('pendingReason','Otro')) for r in data['pending'])
    title='Octubre 2026 · Simulación al minuto 70'
    content=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><style>
    *{{box-sizing:border-box}}body{{font-family:system-ui,sans-serif;background:#f3f6ef;color:#20392b;margin:0}}main{{max-width:1350px;margin:auto;padding:35px 24px}}h1{{font-size:34px;letter-spacing:-1px}}h2{{margin-top:35px}}p,li{{line-height:1.7;font-size:13px}}a{{color:#39713c}}.notice{{padding:20px;background:#fff1d4;border-left:4px solid #b78f3f}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:24px 0}}.card{{padding:20px;background:white;border:1px solid #dfe7d8;border-radius:9px}}.card span{{font-size:12px;color:#718469}}.card strong{{display:block;font-size:32px;margin:10px 0}}.wrap{{overflow:auto;background:white;border:1px solid #dce6d6;border-radius:8px}}table{{width:100%;border-collapse:collapse;font-size:11px}}th,td{{padding:12px;border-bottom:1px solid #e7ecdf;text-align:left;vertical-align:top}}th{{background:#e7efdf}}details{{margin-top:8px;color:#6e8164;max-width:450px;line-height:1.7}}summary{{cursor:pointer}}select,input{{font:13px system-ui;padding:10px;border:1px solid #d2dfc9;border-radius:5px;margin:0 6px 15px 0}}footer{{font-size:11px;margin-top:30px;color:#819078}}</style></head><body><main>
    <a href="../../">← Dashboard BM</a><h1>{title}</h1><p>Del 1 al 31 de octubre, horario Bogotá/Lima. Simulación retrospectiva; no acredita apuestas reales.</p>
    <div class="notice"><b>Resultado condicionado a posiciones reconstruidas.</b><p>Se reconstruyen puntos antes de cada encuentro, sin archivo oficial de tablas históricas ni sanciones fechadas. Los casos ambiguos se separan y no entran en la tasa principal. La simulación aplica H2H del año, goles, rival fuera del top 5, victoria previa y cero goles del elegido al 70; no aplica un filtro de dominio en vivo.</p></div>
    <div class="cards"><article class="card"><span>Partidos de octubre localizados</span><strong>{summary['fixturesOctober']}</strong><small>{summary['finishedFixtures']} finalizados · 48 competiciones</small></article><article class="card"><span>Aptos previos, con tabla reconstruida</span><strong>{summary['prequalifiedMatches']}</strong><small>{summary['prequalifiedTeams']} selecciones de equipo</small></article><article class="card"><span>Partidos con entrada simulada al 70</span><strong>{summary['entriesMatches']}</strong><small>{summary['entriesTeams']} selecciones sin gol al 70</small></article><article class="card"><span>Cualquier gol después del 70</span><strong>{summary['anyGoalSuccessMatches']} / {summary['entriesMatches']}</strong><small>{pct(summary['anyGoalSuccessMatches'],summary['entriesMatches'])} · partidos únicos</small></article><article class="card"><span>Gol del equipo elegido después del 70</span><strong>{summary['chosenTeamGoalSuccess']} / {summary['entriesTeams']}</strong><small>{pct(summary['chosenTeamGoalSuccess'],summary['entriesTeams'])} · selecciones de equipo</small></article></div>
    <p>{summary['noEntryAlreadyScored']} selecciones previas ya habían marcado al 70 y no generan entrada. {summary['eventsUnresolved']} selecciones previas no se pudieron resolver por eventos incompletos. {summary['pendingHistoricalCriteria']} selecciones adicionales tienen criterios históricos pendientes.</p>
    <p><a href="detalle.csv">Descargar detalle CSV</a> · <a href="analysis.json">Datos y evidencia JSON</a></p>
    <h2>Resultados por competición</h2><p>“Cualquier gol” se cuenta por partido único. “Pendientes” se expresa por equipo, pues el criterio depende del rival.</p><div class="wrap"><table><thead><tr><th>Competición</th><th>Partidos octubre</th><th>Aptos previos reconstruidos</th><th>Partidos con entrada</th><th>Con gol posterior</th><th>Tasa</th><th>Equipos pendientes</th></tr></thead><tbody>{''.join(league_rows)}</tbody></table></div>
    <h2>Detalle de candidatos y casos pendientes</h2><input id="query" placeholder="Buscar equipo o liga" aria-label="Buscar equipo o liga"><select id="state" aria-label="Estado histórico"><option value="reconstructed">Tabla reconstruida</option><option value="pending">Criterio pendiente</option><option value="all">Todos</option></select><select id="entry" aria-label="Entrada simulada"><option value="all">Cualquier entrada</option><option value="true">Con entrada</option><option value="false">Sin entrada</option><option value="null">Eventos sin resolver</option></select>
    <p><button id="prev">← Anterior</button> <span id="page-label"></span> <button id="next">Siguiente →</button></p><div class="wrap"><table id="detail"><thead><tr><th>Fecha</th><th>Liga</th><th>Partido y evidencia</th><th>Banda de puesto del rival</th><th>Estado</th><th>Gol elegido &gt;70</th><th>Cualquier gol &gt;70</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
    <h2>Casos pendientes</h2><ul>{''.join(f'<li>{esc(k)}: {v} equipos-partido.</li>' for k,v in pending_counts.most_common())}</ul>
    <h2>Cómo leer el análisis</h2><ol>{''.join('<li>'+esc(x)+'</li>' for x in data['limitations'])}</ol><footer>Fuente: API-Football · Generado {esc(when(data['generatedAt']))} UTC−5. No se calcularon ganancias, cuotas ni ROI.</footer>
    </main><script>let page=0;function filter(reset=true){{if(reset)page=0;const q=document.querySelector('#query').value.toLowerCase(),s=document.querySelector('#state').value,e=document.querySelector('#entry').value;const all=[...document.querySelectorAll('#detail tbody tr')];const selected=all.filter(r=>(s==='all'||r.dataset.state===s)&&(e==='all'||r.dataset.entry===e)&&r.textContent.toLowerCase().includes(q));all.forEach(r=>r.hidden=true);selected.slice(page*30,page*30+30).forEach(r=>r.hidden=false);document.querySelector('#page-label').textContent=selected.length+' filas · página '+(page+1)+' de '+Math.max(1,Math.ceil(selected.length/30));document.querySelector('#prev').disabled=page===0;document.querySelector('#next').disabled=(page+1)*30>=selected.length;}}['query','state','entry'].forEach(id=>document.querySelector('#'+id).addEventListener('input',()=>filter()));document.querySelector('#prev').onclick=()=>{{page--;filter(false);}};document.querySelector('#next').onclick=()=>{{page++;filter(false);}};filter();</script></body></html>'''
    (OUT/'index.html').write_text(content,encoding='utf-8')
    print('Informe HTML y CSV generados en '+str(OUT))

if __name__=='__main__':main()
