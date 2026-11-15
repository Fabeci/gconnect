'use strict';
/* E61 | Real MFA-bound audit timeline, Premium G-Connect design.
   No invented activity, no raw event metadata or network identifiers. */
(function(){
 const path={
  history:'<path d="M3 12a9 9 0 1 0 3-6"/><path d="M3 3v6h6m3-3v6l4 2"/>',
  shield:'<path d="m12 2 9 4v6c0 6-4 9-9 10-5-1-9-4-9-10V6l9-4Z"/><path d="m8 12 3 3 5-6"/>',
  flag:'<path d="M5 21V4m0 0c5-3 9 3 15 0v12c-6 3-10-3-15 0"/>',
  mail:'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/>',
  key:'<circle cx="8" cy="15" r="5"/><path d="m12 11 9-9m-4 1 4 4m-6-2 3 3"/>',
  rows:'<rect x="4" y="3" width="16" height="18" rx="3"/><path d="M8 8h8m-8 4h8m-8 4h6"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
  refresh:'<path d="M20 5v6h-6M4 19v-6h6"/><path d="M5 10a8 8 0 0 1 14-3l1 4M4 14a8 8 0 0 0 14 3"/>',
  right:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  close:'<path d="M5 5 19 19M19 5 5 19"/>',
  check:'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  alert:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4M17 3v4M3 10h18"/>',
  user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-6 6-6 12 0 18m0-18c6 6 6 12 0 18"/>',
 };
 const icon=k=>'<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round">'+(path[k]||path.history)+'</svg>';
 const categories={
  all:'Tous les événements',access:'Accès et connexions',
  invitations:'Invitations',moderation:'Modération',operations:'Opérations',other:'Autres',
 };
 const categoryLabels={access:'Accès',invitations:'Invitation',moderation:'Modération',operations:'Opération',other:'Autre'};
 const categoryIcon={access:'key',invitations:'mail',moderation:'flag',operations:'rows',other:'history'};
 const periods={7:'7 jours',30:'30 jours',90:'90 jours',180:'6 mois'};
 const defs=[
  ['events','Événements','history','indigo','Événements sur la période'],
  ['invitations','Invitations','mail','copper','Traçabilité des invitations'],
  ['moderation','Modérations','flag','rose','Décisions de conformité'],
  ['access','Accès & connexions','shield','teal','Actions d’authentification'],
 ];
 const fields={
  report_id:'Signalement',post_id:'Publication',job_id:'Lot d’import',institution_id:'Établissement',
  enterprise_id:'Entreprise',user_id:'Utilisateur',total:'Lignes traitées',
  success:'Réussites',errors:'Anomalies',count:'Quantité',
  outcome:'Issue',import_type:'Type d’import',organisation_type:'Organisation',
 };
 const pretty=n=>new Intl.NumberFormat('fr-FR').format(n);
 const num=n=>Number.isSafeInteger(n)&&n>=0?pretty(n):'—';
 const dateTime=t=>{
  const d=new Date(t||'');return Number.isNaN(d.getTime())?'Date indisponible':
   new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium',timeStyle:'short'}).format(d);
 };
 const day=t=>{
  if(typeof t!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(t))return '';
  const d=new Date(t+'T12:00:00Z');
  return new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'short',timeZone:'UTC'}).format(d);
 };
 const options=(entries,selected)=>entries.map(([k,v])=>
  '<option value="'+k+'"'+(selected===String(k)?' selected':'')+'>'+v+'</option>').join('');
 window.GConnectAuditE61=function({api,safe,render,isVisible}){
  const state={
   days:30,category:'all',action:'all',search:'',page:1,page_size:12,
   ready:false,loading:false,error:'',payload:null,
  };
  let serial=0,searchTimer=null,dialog=null;
  const visible=()=>isVisible();
  const s=()=>state.payload?.summary||{};
  const count=k=>state.error?'—':num(s()[k]);
  function hero(){
   return '<header class="e61-hero"><div class="e61-hero-copy">'+
     '<span class="e61-overline e61-eyebrow"><i></i>TRAÇABILITÉ · CONSOLE SUPERADMIN</span>'+
     '<h1>Journal <em>d’audit</em></h1>'+
     '<p>Une mémoire vérifiable des événements sensibles du réseau. Identifiez les activités, examinez les interventions et suivez les accès sans exposer les données confidentielles.</p>'+
     '<div class="e61-seal">'+icon('shield')+' Registre réel · Consultation sécurisée en lecture seule</div></div>'+
     '<div class="e61-art" aria-hidden="true"><i class="e61-halo e61-halo-outer"></i><i class="e61-halo e61-halo-inner"></i>'+
     '<div class="e61-art-document"><span class="e61-art-header">'+icon('shield')+' AUDIT <b>●</b></span>'+
     '<span class="e61-art-rule e61-art-rule-a"></span><span class="e61-art-rule e61-art-rule-b"></span>'+
     '<span class="e61-art-rule e61-art-rule-c"></span><span class="e61-art-rule e61-art-rule-d"></span>'+
     '<span class="e61-art-check">'+icon('check')+'</span></div>'+
     '<span class="e61-art-icon e61-art-icon-one">'+icon('history')+'</span>'+
     '<span class="e61-art-icon e61-art-icon-two">'+icon('key')+'</span>'+
     '<span class="e61-art-icon e61-art-icon-three">'+icon('mail')+'</span>'+
     '<i class="e61-art-dot e61-art-dot-one"></i><i class="e61-art-dot e61-art-dot-two"></i></div></header>';
  }
  function periodBar(){
   return '<section class="e61-period-bar"><div><span class="e61-overline">01 / OBSERVATION</span>'+
    '<p>'+(state.payload?'Du '+safe(day(state.payload.since))+' au '+safe(day(state.payload.until)):
    'Fenêtre de consultation du journal')+'</p></div>'+
    '<div class="e61-period-controls" role="group" aria-label="Période de consultation">'+
    Object.entries(periodsMap()).map(([d,label])=>
     '<button type="button" data-e61-days="'+d+'" aria-pressed="'+(state.days===+d)+'"'+
     (state.days===+d?' class="active"':'')+'>'+label+'</button>').join('')+
    '<button type="button" data-e61-action="refresh" class="e61-refresh" aria-label="Actualiser le journal">'+icon('refresh')+'</button></div></section>';
  }
  const periodsMap=()=>periods;
  function metrics(){
   return '<section class="e61-metrics" aria-label="Indicateurs du registre">'+defs.map(([key,name,ic,tone,sub],i)=>
    '<button type="button" class="e61-metric e61-metric-'+tone+'" data-e61-category="'+
    (key==='events'?'all':key==='access'?'access':key)+'" aria-label="Filtrer : '+name+'">'+
    '<span class="e61-metric-top"><span class="e61-metric-symbol">'+icon(ic)+'</span>'+
    '<span class="e61-metric-more">'+icon('right')+'</span></span>'+
    '<strong class="e61-metric-number">'+count(key)+'</strong>'+
    '<span class="e61-metric-name">'+name+'</span><small>'+sub+'</small></button>'
   ).join('')+'</section>';
  }
  function filterBox(){
   const actions=state.payload?.action_choices||[];
   return '<div class="e61-ledger-head"><div><span class="e61-overline">02 / CHRONOLOGIE</span>'+
    '<h2>Historique des événements</h2><p>Chaque ligne correspond à un événement enregistré côté serveur.</p></div>'+
    '<span class="e61-readonly">'+icon('shield')+' Lecture seule</span></div>'+
    '<div class="e61-toolbar"><label class="e61-search">'+icon('search')+
    '<input type="search" data-e61-search aria-label="Rechercher un événement" '+
    'placeholder="Acteur, événement…" maxlength="100" autocomplete="off" value="'+safe(state.search)+'"></label>'+
    '<label class="e61-filter">Catégorie<select data-e61-filter="category">'+
    options(Object.entries(categories),state.category)+'</select></label>'+
    '<label class="e61-filter">Action<select data-e61-filter="action">'+
    options([['all','Toutes les actions'],...actions.map(x=>[String(x.value),safe(x.label)])],state.action)+
    '</select></label></div>';
  }
  function item(entry){
   const kind=Object.hasOwn(categoryLabels,entry.category)?entry.category:'other';
   return '<button type="button" class="e61-event" data-e61-item="'+Number(entry.id)+'">'+
     '<span class="e61-event-symbol e61-event-symbol-'+kind+'">'+icon(categoryIcon[kind])+'</span>'+
     '<span class="e61-event-description"><span class="e61-event-kicker">'+
      safe(dateTime(entry.created_at))+' · #'+Number(entry.id)+'</span>'+
     '<strong>'+safe(entry.label||'Événement enregistré')+'</strong>'+
     '<small>'+safe(entry.actor||'Compte indisponible')+'</small></span>'+
     '<span class="e61-event-right"><span class="e61-type e61-type-'+kind+'">'+
     safe(categoryLabels[kind])+'</span><span class="e61-chevron">'+icon('right')+'</span></span></button>';
  }
  function ledger(){
   let records='';
   if(state.loading&&!state.ready)records='<div class="e61-blank" role="status">'+icon('history')+
    '<strong>Lecture des événements…</strong><p>Chargement du registre sécurisé.</p></div>';
   else if(state.error)records='<div class="e61-blank e61-error" role="alert">'+icon('alert')+
    '<strong>Impossible de consulter le journal</strong><p>'+safe(state.error)+'</p>'+
    '<button type="button" data-e61-action="refresh">Réessayer</button></div>';
   else if(!state.payload?.results?.length)records='<div class="e61-blank">'+icon('shield')+
    '<strong>Aucun événement pour ces filtres</strong><p>Le registre n’a renvoyé aucune entrée correspondant à votre sélection.</p></div>';
   else records='<div class="e61-events">'+state.payload.results.map(item).join('')+'</div>';
   const p=state.payload;
   let footer='';
   if(!state.error&&p)footer='<footer class="e61-page-controls"><span>'+num(p.count)+
    ' événement(s) · page '+p.page+'/'+p.pages+'</span><div>'+
    '<button type="button" data-e61-action="prev" '+(p.page<=1?'disabled':'')+'>Précédent</button>'+
    '<button type="button" data-e61-action="next" '+(p.page>=p.pages?'disabled':'')+
    '>Suivant '+icon('right')+'</button></div></footer>';
   return '<section class="e61-ledger">'+filterBox()+records+footer+'</section>';
  }
  function chart(){
   const trend=state.payload?.trend;
   if(!trend||!trend.labels?.length)return '<p class="e61-loading-note">Série disponible après chargement.</p>';
   const values=trend.events,max=Math.max(1,...values);
   const maxBars=trend.labels.length;
   const bars=values.map((v,i)=>{
    const h=(v/max*100).toFixed(1);
    const label=safe(day(trend.labels[i]));
    return '<div class="e61-bar-cell" title="'+label+' : '+v+' événement(s)">'+
     '<span class="e61-bar-amount">'+v+'</span><span class="e61-bar" style="--e61-height:'+h+'%"></span>'+
     '<span class="e61-bar-date">'+(maxBars<=14||i%Math.ceil(maxBars/7)===0?label:'')+'</span></div>';
   }).join('');
   return '<div class="e61-chart" role="img" aria-label="Historique réel des événements sur la période">'+bars+'</div>'+
    '<p class="e61-chart-note">'+(values.some(Boolean)?'Événements regroupés par '+({
     day:'jour',week:'semaine',month:'mois',
    }[trend.granularity]||'période')+'.':'Aucune activité enregistrée sur cette période.')+'</p>';
  }
  function statusBox(){
   const v=s();
   return '<section class="e61-integrity"><span class="e61-overline">04 / VIGILANCE</span>'+
    '<h2>Points de contrôle</h2>'+
    '<div class="e61-risk"><span>'+icon('alert')+'</span><div>'+
    '<strong>'+count('failed_access')+'</strong><small>Connexion(s) échouée(s)</small></div></div>'+
    '<div class="e61-risk e61-risk-ops"><span>'+icon('rows')+'</span><div>'+
    '<strong>'+count('operations')+'</strong><small>Opérations sensibles</small></div></div>'+
    '<div class="e61-integrity-note">'+icon('shield')+
    '<p>Le journal est consulté en lecture seule. Les adresses IP, secrets MFA et métadonnées libres ne sont jamais présentés.</p></div></section>';
  }
  function breakdown(){
   const sum=s(),groups=[['access','Accès et connexions','teal'],['invitations','Invitations','copper'],
    ['moderation','Modération','rose'],['operations','Opérations','indigo'],['other','Autres','slate']];
   const max=Math.max(1,...groups.map(([key])=>Number(sum[key])||0));
   const list=state.payload?groups.map(([key,label,tone])=>{
    const n=Number(sum[key])||0;
    return '<div class="e61-breakdown-row"><div><span>'+label+'</span><strong>'+num(n)+'</strong></div>'+
     '<span class="e61-track"><i class="e61-track-fill e61-track-'+tone+'" style="--e61-progress:'+
     Math.round(n/max*100)+'%"></i></span></div>';
   }).join(''):'<p class="e61-loading-note">Répartition disponible après chargement.</p>';
   return '<section class="e61-breakdown"><span class="e61-overline">05 / RÉPARTITION</span>'+
    '<h2>Activités par catégorie</h2>'+list+'</section>';
  }
  function sidebar(){
   return '<aside class="e61-side"><section class="e61-graph-panel">'+
    '<span class="e61-overline">03 / TENDANCES</span><h2>Rythme des activités</h2>'+
    '<p class="e61-graph-sub">Événements issus du journal pour la période sélectionnée.</p>'+
    chart()+'</section>'+statusBox()+breakdown()+'</aside>';
  }
  const page=()=>'<div class="e61-page">'+hero()+periodBar()+metrics()+
   '<div class="e61-body-grid">'+ledger()+sidebar()+'</div></div>';
  function valid(payload){
   if(!payload||payload.days!==state.days||!payload.summary||
       !Array.isArray(payload.results)||!Array.isArray(payload.action_choices)||
       !payload.trend||!Array.isArray(payload.trend.labels)||
       !Array.isArray(payload.trend.events)||payload.trend.labels.length!==payload.trend.events.length||
       !Number.isSafeInteger(payload.page)||!Number.isSafeInteger(payload.pages)||
       !Number.isSafeInteger(payload.count)||payload.page!==state.page)return false;
   for(const key of ['events','invitations','moderation','access','operations','other','failed_access']){
     if(!Number.isSafeInteger(payload.summary[key])||payload.summary[key]<0)return false;
   }
   if(payload.trend.events.some(x=>!Number.isSafeInteger(x)||x<0))return false;
   return true;
  }
  async function load(){
   if(state.loading||!visible())return;
   state.loading=true;state.error='';const id=++serial;
   try{
    const payload=await api.adminAuditDirectory({
     days:state.days,category:state.category,action:state.action,
     search:state.search,page:state.page,page_size:state.page_size,
    });
    if(id!==serial)return;
    if(!valid(payload))throw Error('Le registre a renvoyé un format incomplet.');
    state.payload=payload;state.ready=true;
   }catch(error){
    if(id!==serial)return;
    state.payload=null;state.ready=true;
    state.error=error?.message||'Lecture du journal impossible.';
   }finally{
    if(id===serial){state.loading=false;if(visible())render()}
   }
  }
  function reload(){
   if(state.loading){++serial;state.loading=false}
   state.ready=false;state.payload=null;void load();
  }
  function ensure(){if(!state.ready&&!state.loading&&visible())void load()}
  function period(number){
   if(Object.hasOwn(periods,String(number))&&state.days!==number){
    state.days=number;state.page=1;reload();
   }
  }
  function filter(el){
   const field=el.dataset.e61Filter;
   if(field==='category'&&Object.hasOwn(categories,el.value))state.category=el.value;
   else if(field==='action'&&(el.value==='all'||state.payload?.action_choices.some(x=>x.value===el.value)))state.action=el.value;
   else return;
   state.page=1;reload();
  }
  function search(el){
   clearTimeout(searchTimer);
   const text=String(el.value||'').slice(0,100);
   searchTimer=setTimeout(()=>{
    if(state.search===text)return;
    state.search=text;state.page=1;reload();
   },320);
  }
  function detail(id){
   if(!visible())return;
   const entry=state.payload?.results?.find(x=>x.id===id);
   if(!entry)return;
   if(!dialog){
    dialog=document.createElement('dialog');dialog.className='e61-dialog';
    dialog.setAttribute('aria-label','Fiche d’événement du journal');
    document.body.appendChild(dialog);
    dialog.addEventListener('click',e=>{
     if(e.target===dialog||e.target.closest('[data-e61-close]'))dialog.close();
    });
   }
   const safeDetails=(entry.details&&typeof entry.details==='object'?entry.details:{});
   const details=Object.entries(safeDetails).filter(([key,value])=>
      Object.hasOwn(fields,key)&&(typeof value==='string'||Number.isSafeInteger(value)));
   dialog.innerHTML='<div class="e61-dialog-head"><span class="e61-overline">FICHE DE TRAÇABILITÉ #'+id+
     '</span><button type="button" aria-label="Fermer" data-e61-close>'+icon('close')+'</button></div>'+
     '<span class="e61-dialog-badge">'+icon('shield')+' ÉVÉNEMENT ENREGISTRÉ</span>'+
     '<h2>'+safe(entry.label||'Événement')+'</h2>'+
     '<div class="e61-dialog-facts">'+[
      ['Catégorie',categoryLabels[entry.category]||'Autre'],
      ['Date et heure',dateTime(entry.created_at)],
      ['Acteur',entry.actor||'Compte indisponible'],
      ['Rôle',entry.actor_role||'Système'],
      ['Code action',entry.action||'Indisponible'],
      ['Identifiant',String(id)],
     ].map(([key,value])=>'<div><span>'+safe(key)+'</span><strong>'+safe(value)+'</strong></div>').join('')+
     '</div><div class="e61-dialog-meta"><h3>Références autorisées</h3>'+
     (details.length?details.map(([key,value])=>
      '<div><span>'+safe(fields[key])+'</span><strong>'+safe(value)+'</strong></div>').join(''):
      '<p>Aucune référence supplémentaire autorisée pour cet événement.</p>')+'</div>'+
     '<p class="e61-dialog-foot">'+icon('shield')+
     ' Aucune adresse IP, mot de passe, jeton ou métadonnée brute n’est affiché.</p>';
   if(!dialog.open)dialog.showModal();
  }
  function action(el){
   if(el.dataset.e61Days){period(Number(el.dataset.e61Days));return}
   if(el.dataset.e61Category){state.category=el.dataset.e61Category;state.page=1;reload();return}
   const id=el.dataset.e61Item;
   if(id){detail(Number(id));return}
   const cmd=el.dataset.e61Action;
   if(cmd==='refresh'){reload();return}
   if(cmd==='next'&&state.payload&&state.page<state.payload.pages){state.page++;reload();return}
   if(cmd==='prev'&&state.page>1){state.page--;reload();}
  }
  return {page,ensure,load,filter,search,action,peek:()=>({
   ready:state.ready,error:state.error,days:state.days,category:state.category,
   count:state.payload?.count??null,
  })};
 };
})();
