const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let observations=[];
function statTable(r){
 const value=(v,key)=>v===null||v===undefined?'N/D':esc(v)+(['possession','accuracy'].includes(key)?'%':'');
 const cols=[['possession','Posesión'],['corners','Córners'],['shots','Disparos totales'],['onTarget','Disparos a puerta'],['insideBox','Disparos dentro del área'],['blocked','Disparos bloqueados'],['saves','Atajadas del portero'],['yellowCards','Amarillas'],['redCards','Rojas'],['xG','Goles esperados (xG)'],['accuracy','Precisión de tiro (%)']];
 const reds=['home','away'].some(side=>(r.statistics?.[side]?.total?.redCards??0)>0);
 return `${reds?'<p class="live70-warning">Hay expulsiones registradas: revisar su efecto en el equipo elegido antes de decidir.</p>':''}<div class="live70-table-wrap"><table class="live70-table"><caption>Captura al ${esc(r.minute)}′ · ${esc(new Date(r.capturedAt).toLocaleString('es-PE',{timeZone:'America/Bogota'}))} (UTC−5)</caption><thead><tr><th rowspan="2">Estadística</th><th colspan="2">Segundo tiempo</th><th colspan="2">Acumulado</th></tr><tr><th>${esc(r.teams.home.name)}</th><th>${esc(r.teams.away.name)}</th><th>${esc(r.teams.home.name)}</th><th>${esc(r.teams.away.name)}</th></tr></thead><tbody>${cols.map(([key,title])=>`<tr><th>${title}</th>${['secondHalf','total'].map(period=>['home','away'].map(side=>`<td>${value(r.statistics?.[side]?.[period]?.[key],key)}</td>`).join('')).join('')}</tr>`).join('')}</tbody></table></div><p class="live70-note">Marcador en la captura: ${esc(r.goals.home)}–${esc(r.goals.away)}. N/D = no disponible. Captura histórica, no marcador actualizado; revisar el partido antes de decidir.</p>`;
}
function fillSlots(){
 for(const el of document.querySelectorAll('.live70-slot')){
  const r=observations.find(r=>String(r.fixtureId)===el.dataset.fixture&&r.selections.some(s=>String(s.teamId)===el.dataset.team));
  el.innerHTML=r?statTable(r):'<p class="live70-note">Estadísticas al 70′: esperando captura del monitor. Se mostrarán posesión, córners, disparos totales y a puerta de ambos equipos, además de xG, tarjetas, disparos dentro del área, bloqueos y atajadas si hay cobertura.</p>';
 }
}
async function load(){
 const sources=['https://raw.githubusercontent.com/ze-martin/app-bm/codex/live70/data/live70.json','./data/live70.json'];
 let data=null;
 for(const source of sources){try{const response=await fetch(source+'?t='+Date.now(),{cache:'no-store'});if(!response.ok)continue;const d=await response.json();if(!Array.isArray(d.observations))continue;data=d;break;}catch{}}
 if(!data){document.querySelector('#live70-captures').textContent='No se pudieron cargar las capturas. No hay estadísticas en vivo confirmadas.';return;}
 observations=[...data.observations].sort((a,b)=>b.capturedAt.localeCompare(a.capturedAt));
 document.querySelector('#live70-captures').innerHTML=observations.length?observations.map(r=>`<article class="live70-capture"><h3>${esc(r.teams.home.name)} vs ${esc(r.teams.away.name)}</h3><p>Equipos preseleccionados: ${r.selections.map(s=>esc(s.team)).join(', ')}</p>${statTable(r)}</article>`).join(''):'<p class="live70-note">Todavía no hay capturas de candidatos al minuto 70. El monitor debe estar activo para obtener y publicar los datos; no se muestran estadísticas de ejemplo.</p>';
 fillSlots();
}
export function initLive70(){
 window.addEventListener('matches-rendered',fillSlots);
 load();
 setInterval(load,60000);
}
