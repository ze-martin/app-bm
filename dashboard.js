const escape=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const date=v=>new Date(v).toLocaleString('es-PE',{timeZone:'America/Bogota',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'});
export function summarize(data,now=Date.now()){
 const all=data.matches.flatMap(m=>m.selections.map(s=>({f:m.fixture,s})));
 const h2h=all.filter(r=>r.s.h2h);
 const goals=h2h.filter(r=>r.s.goals!==null&&r.s.goals>=r.s.requiredH2hGoals);
 const outside=goals.filter(r=>r.s.rivalRank>5);
 const won=outside.filter(r=>r.s.won);
 const watch=all.filter(r=>(r.s.prequalified===true||r.s.status==='candidate')&&['NS','1H','HT','2H'].includes(r.f.fixture.status.short));
 const upcoming=watch.filter(r=>new Date(r.f.fixture.date).getTime()>now).sort((a,b)=>a.f.fixture.date.localeCompare(b.f.fixture.date));
 const reasons=new Map();
 for(const {s} of all)for(const reason of s.reasons){
  if(reason.includes('iniciado')||reason.includes('hora de inicio'))continue;
  const category=reason.includes('enfrentamiento')?'Sin H2H del año':reason.includes('Goles H2H')?'Goles H2H insuficientes':reason.includes('primeros 5')?'Rival en top 5':reason.includes('No ganó')?'Sin victoria reciente':reason.includes('Posición')||reason.includes('fuentes')||reason.includes('web')?'Clasificación sin resolver':'Otros datos ausentes';
  reasons.set(category,(reasons.get(category)??0)+1);
 }
 const leagueCounts=new Map();
 for(const {f}of upcoming){const name=`${f.league.country} / ${f.league.name}`;leagueCounts.set(name,(leagueCounts.get(name)??0)+1);}
 return {all,h2h,goals,outside,won,watch,upcoming,reasons:[...reasons].sort((a,b)=>b[1]-a[1]),leagues:[...leagueCounts].sort((a,b)=>b[1]-a[1]),rankCoverage:all.length?Math.round(100*all.filter(r=>Number.isInteger(r.s.rivalRank)).length/all.length):0};
}
export function renderDashboard(data){
 if(!data)return;
 const a=summarize(data);
 const bars=(items,total)=>items.map(([name,n])=>`<div class="metric-row"><div><span>${escape(name)}</span><b>${n}</b></div><div class="bar-track"><i style="width:${total?Math.round(100*n/total):0}%"></i></div></div>`).join('')||'<p>Sin datos para este período.</p>';
 const funnel=[['Equipos evaluados',a.all.length],['Con H2H válido',a.h2h.length],['Superan goles H2H',a.goals.length],['Rival fuera del top 5',a.outside.length],['Además, victoria reciente',a.won.length]];
 const agenda=a.watch.filter(r=>new Date(r.f.fixture.date).getTime()>Date.now()-4*3600000).sort((a,b)=>a.f.fixture.date.localeCompare(b.f.fixture.date));
 document.querySelector('#dashboard-content').innerHTML=`<div class="insight-grid"><article class="insight-card"><span>Cobertura de clasificación</span><strong>${a.rankCoverage}%</strong><p>Equipos con posición del rival disponible; no mide acierto.</p></article><article class="insight-card"><span>Partidos futuros con candidatos</span><strong>${new Set(a.upcoming.map(r=>r.f.fixture.id)).size}</strong><p>${a.upcoming.length} equipos cumplen las reglas históricas.</p></article><article class="insight-card"><span>Próximo inicio para seguir</span><strong class="small-value">${a.upcoming[0]?escape(date(a.upcoming[0].f.fixture.date)):'Sin próximos'}</strong><p>${a.upcoming[0]?escape(a.upcoming[0].f.teams.home.name+' vs '+a.upcoming[0].f.teams.away.name):'Se actualiza con la próxima descarga.'}</p></article></div><div class="analysis-grid"><article class="insight-card"><h3>Cómo se reduce la lista</h3><p>Filtros acumulados por equipo. Incluye encuentros ya iniciados; la agenda distingue el horario.</p>${bars(funnel,a.all.length)}</article><article class="insight-card"><h3>Qué frena las selecciones</h3><p>Un equipo puede tener varios motivos; las cifras no se suman como partidos únicos.</p>${bars(a.reasons,a.all.length)}</article><article class="insight-card"><h3>Dónde están los candidatos futuros</h3><p>Equipos candidatos por liga, sin ponderación de probabilidad.</p>${bars(a.leagues,a.upcoming.length)}</article></div><div class="agenda-header"><h3>Agenda para revisar el minuto 70</h3><p>Hora orientativa = inicio + 85 min, suponiendo 15 min de descanso. El aviso previo de Telegram apunta al 65′ real de la API; la captura de estadísticas se mantiene al 70′.</p></div><div class="agenda-list">${agenda.length?agenda.map(({f,s})=>`<article><div><b>${escape(s.team)}</b><span>${escape(f.teams.home.name)} vs ${escape(f.teams.away.name)}</span></div><div><span>Inicio: ${escape(date(f.fixture.date))}</span><span>Aviso 65′ estimado: ${escape(date(new Date(new Date(f.fixture.date).getTime()+80*60000)))}</span><span>70′ estimado: ${escape(date(new Date(new Date(f.fixture.date).getTime()+85*60000)))}</span></div></article>`).join(''):'<p>No hay candidatos en la ventana actual de seguimiento.</p>'}</div>`;
}
