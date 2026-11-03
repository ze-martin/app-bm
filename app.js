import {initLive70} from './live70.js?v=stats70';
import {renderDashboard} from './dashboard.js?v=dashboard70';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stamp=v=>new Date(v).toLocaleString('es-PE',{timeZone:'America/Bogota',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
const localDay=v=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Bogota',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(v));
let snapshot=null;
let rows=[],status='candidate',visible=[];
function score(f){return `${f.teams.home.name} ${f.goals.home}–${f.goals.away} ${f.teams.away.name}`;}
function goalRule(s){
 const prior=s.previousVenue??(s.side==='home'?'away':'home');
 const minimum=s.requiredH2hGoals??(prior==='home'?2:1);
 return `<div class="goal-rule"><b>Criterio 2 · ${prior==='home'?'Local → visitante':'Visitante → local'}</b><span>Antecedente: ${esc(s.goals)} gol(es) como ${prior==='home'?'local':'visitante'} · mínimo exigido: ${minimum}.</span><span>Objetivo actual: ${esc(s.team)} marca al menos 1 gol como ${s.side==='home'?'local':'visitante'}.</span></div>`;
}
function rankEvidence(f,s){
 const v=s.rankVerification??{};
 const label={api:'API-Football · fase identificada',verified:'Verificada en dos páginas',needed:'Verificación web pendiente',expired:'Revisión web vencida',invalid:'Evidencia no válida',conflict:'Conflicto entre fuentes'}[v.status]??'Verificación pendiente';
 const sources=(v.sources??[]).filter(x=>{try{return new URL(x.url).protocol==='https:';}catch{return false;}}).map(x=>`<a href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.name)} · puesto ${esc(x.rank)}</a>`).join(' · ');
 const search=encodeURIComponent(`${f.league.country} ${f.league.name} ${f.league.season} ${v.phase??''} tabla posiciones`);
 return `<div class="rank-check"><b>Clasificación: ${esc(label)}</b><span>Fase: ${esc(v.phase)}${v.checkedAt?' · Revisada: '+esc(stamp(v.checkedAt)):''}</span>${sources?`<span>${sources}</span>`:''}${v.note?`<span>${esc(v.note)}</span>`:''}<details><summary>Protocolo de verificación con scroll</summary><ol><li>Confirmar país, liga, año y fase del partido. Usar tabla general, sin filtrar local/visita.</li><li>Abrir FotMob u otra fuente y desplazarse hasta la fila del rival.</li><li>Leer puesto, equipo, partidos y puntos. Comparar con otra página de dominio distinto y la misma fase.</li><li>Registrar ambas fuentes y hora. Si discrepan, queda pendiente. La revisión vence en 24 horas.</li></ol><a href="https://www.google.com/search?q=${search}" target="_blank" rel="noopener noreferrer">Localizar tabla de esta competición</a> · <a href="./PROTOCOL_STANDINGS.md" target="_blank">Ver protocolo completo</a><p>Revisión asistida. Las actualizaciones programadas consumen evidencia vigente; no navegan ni hacen scroll automáticamente.</p></details></div>`;
}
function render(){
 visible=rows.filter(r=>(status==='all'||r.s.status===status)&&(!$('#league').value||String(r.f.league.id)===$('#league').value)&&(!$('#date').value||localDay(r.f.fixture.date)===$('#date').value)&&(`${r.f.teams.home.name} ${r.f.teams.away.name} ${r.f.league.name}`.toLowerCase().includes($('#search').value.toLowerCase())));
 $('#results').innerHTML=visible.length?visible.map(({f,s})=>`<article class="match"><div class="match-top"><div><div class="league-name">${esc(f.league.country)} / ${esc(f.league.name)} · ${esc(stamp(f.fixture.date))}</div><div class="teams">${esc(f.teams.home.name)} <span style="color:#a0aaa0">vs</span> ${esc(f.teams.away.name)}</div></div><span class="tag ${s.status}">${s.status==='candidate'?'Cumple los filtros':s.status==='pending'?'Por verificar':'Descartado'}</span></div><div class="pick">Equipo evaluado: <b>${esc(s.team)}</b> · ${s.side==='home'?'Local':'Visitante'}</div>${goalRule(s)}<div class="evidence"><span>Rival: ${s.rivalRank?`puesto ${esc(s.rivalRank)}`:'sin clasificación'}</span><span>Goles H2H: ${esc(s.goals)}</span><span>Último partido: ${s.previous?(s.won?'victoria':'sin victoria'):'sin datos'}</span></div>${rankEvidence(f,s)}${s.prequalified?`<div class="live70-slot" data-fixture="${f.fixture.id}" data-team="${s.teamId}"></div>`:''}<details><summary>Ver evidencia y motivos</summary><p>${s.h2h?`H2H · ${esc(stamp(s.h2h.fixture.date))} · ${esc(score(s.h2h))}`:'Sin H2H válido del mismo año con localías invertidas.'}</p><p>${s.previous?`Último partido · ${esc(stamp(s.previous.fixture.date))} · ${esc(score(s.previous))}`:'No hay último partido disponible.'}</p><p>${s.reasons.length?esc(s.reasons.join(' · ')):'Cumple la preselección. Revisar manualmente al minuto 70; descartar si el equipo ya anotó.'}</p></details></article>`).join(''):`<div class="empty"><b>${status==='candidate'?'Sin candidatos para estos filtros':'No hay resultados'}</b>No se fuerza una selección cuando falta evidencia o no se cumplen las reglas.</div>`;
 window.dispatchEvent(new Event('matches-rendered'));
}
for(const id of ['search','league','date'])$('#'+id).addEventListener('input',render);
document.querySelectorAll('[data-status]').forEach(b=>b.onclick=()=>{status=b.dataset.status;document.querySelectorAll('[data-status]').forEach(x=>x.classList.toggle('selected',x===b));render();});
$('#clear').onclick=()=>{['search','league','date'].forEach(x=>$('#'+x).value='');render();};
$('#export').onclick=()=>{const cell=v=>'"'+String(v??'').replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';const csv=[['Fecha','Liga','Local','Visita','Equipo','Estado','Posición rival','Localía anterior','Goles H2H','Mínimo H2H','Objetivo de goles','Estado de verificación','Fase','Fecha verificación','Fuentes de clasificación','Motivos'],...visible.map(({f,s})=>[stamp(f.fixture.date),f.league.name,f.teams.home.name,f.teams.away.name,s.team,s.status,s.rivalRank,s.previousVenue,s.goals,s.requiredH2hGoals,s.targetGoals,s.rankVerification?.status,s.rankVerification?.phase,s.rankVerification?.checkedAt,(s.rankVerification?.sources??[]).map(x=>x.url).join(' / '),s.reasons.join(' / ')])].map(r=>r.map(cell).join(',')).join('\r\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));a.download='radar-partidos.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
try{const res=await fetch('./data/matches.json',{cache:'no-store'});if(!res.ok)throw Error('No se pudo cargar el archivo de partidos');const d=await res.json();snapshot=d;rows=d.matches.flatMap(m=>m.selections.map(s=>({f:m.fixture,s:{...s}}))).sort((a,b)=>a.f.fixture.date.localeCompare(b.f.fixture.date));
 // A historical snapshot must never suggest a match that has already started.
 for(const r of rows)if(new Date(r.f.fixture.date)<=new Date()&&r.s.status==='candidate'){r.s.status='excluded';r.s.reasons=[...r.s.reasons,'La hora de inicio ya pasó; requiere revisión en vivo'];}
 $('#updated').textContent=d.updatedAt?'Actualizado · '+stamp(d.updatedAt):'Sin actualización';$('#total').textContent=d.matches.length;$('#candidates').textContent=rows.filter(r=>r.s.status==='candidate').length;$('#count').textContent=$('#candidates').textContent;$('#pending').textContent=rows.filter(r=>r.s.status==='pending').length;$('#leagues').textContent=d.leaguesSeen;
 const leagues=new Map(rows.map(r=>[r.f.league.id,r.f.league.country + " / " + r.f.league.name]));for(const [id,name]of [...leagues].sort((a,b)=>a[1].localeCompare(b[1]))){const o=new Option(name,id);$('#league').add(o);}
 const warnings=[];if(!d.updatedAt)warnings.push('Todavía no se han descargado datos de API-Football.');else if(Date.now()-new Date(d.updatedAt)>6*3600000)warnings.push('Datos de más de 6 horas: actualiza antes de decidir.');if(d.errors?.length)warnings.push(`${d.errors.length} incidencias de cobertura. Los datos ausentes no califican como candidatos.`);$('#notice').textContent=warnings.join(' ');render();
}catch(e){$('#notice').textContent=e.message;$('#results').innerHTML='<div class="empty"><b>Datos no disponibles</b>Ejecuta la actualización y vuelve a cargar.</div>';}

async function loadLeagueCatalog(){
 try{
  const response=await fetch('./config.json',{cache:'no-store'});
  if(!response.ok)throw Error('No se pudo cargar el catálogo de ligas.');
  const config=await response.json();
  $('#league-total').textContent=`· ${config.leagues.length}`;
  $('#configured-count').textContent=`Dentro de tus ${config.leagues.length} competiciones`;
  const fixtureCounts=new Map();
  for(const r of rows){if(!fixtureCounts.has(r.f.league.id))fixtureCounts.set(r.f.league.id,new Set());fixtureCounts.get(r.f.league.id).add(r.f.fixture.id);}
  $('#league-catalog').innerHTML=config.leagues.map(l=>`<article class="league-item"><b>${esc(l.name)}</b><span>${fixtureCounts.get(l.id)?.size??0} partidos en el período</span>${l.id===40?'<small>CHAMPIONSHIP · INGLATERRA</small>':''}</article>`).join('');
 }catch(e){$('#league-catalog').textContent=e.message;}
}
await loadLeagueCatalog();

renderDashboard(snapshot);

initLive70();
