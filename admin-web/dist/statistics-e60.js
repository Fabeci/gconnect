'use strict';
/* E60 | Premium, evidence-backed G-Connect Superadmin statistical observatory.
   No demo values, no legacy charts, no browser-generated account data. */
(function(){
const icons={
 chart:'<path d="M3 20h18M5 16l4-5 4 2 5-8"/><path d="m16 5 2 0 0 2"/>',
 enterprise:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h2m3 0h2M9 11h2m3 0h2M9 15h2m3 0h2"/>',
 school:'<path d="m3 9 9-6 9 6M5 9v12h14V9M9 21v-8h6v8"/>',
 users:'<circle cx="9" cy="9" r="4"/><path d="M2 21v-2a7 7 0 0 1 14 0v2M18 7a4 4 0 0 1 0 8m1 6v-2a6 6 0 0 0-2-4"/>',
 file:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
 shield:'<path d="m12 2 9 4v6c0 6-4 9-9 10-5-1-9-4-9-10V6l9-4Z"/><path d="m8 12 3 3 5-6"/>',
 bolt:'<path d="m13 2-9 12h7l-1 8 10-12h-7V2Z"/>',
 eye:'<path d="M2 12c3-5 6-7 10-7s7 2 10 7c-3 5-6 7-10 7S5 17 2 12Z"/><circle cx="12" cy="12" r="3"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
 arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
 rotate:'<path d="M20 5v6h-6M4 19v-6h6"/><path d="M5 10a8 8 0 0 1 14-3l1 4M4 14a8 8 0 0 0 14 3"/>',
 cross:'<path d="M5 5 19 19M19 5 5 19"/>',
 check:'<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>',
 calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4M17 3v4M3 10h18"/>',
};
const icon=name=>'<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+(icons[name]||icons.chart)+'</svg>';
const periods={30:'30 jours',90:'90 jours',180:'6 mois',365:'12 mois'};
const roles=[['student','Étudiants','blue'],['alumni','Alumni','mint'],['enterprise','Entreprises','violet'],['etablissement','Responsables établissement','amber'],['superAdmin','Superadmins','slate']];
const contents=[['opportunity','Opportunités','blue'],['event','Événements','coral'],['project','Projets','mint'],['discussion','Discussions','violet'],['share','Partages','amber']];
const pretty=value=>new Intl.NumberFormat('fr-FR').format(value);
const count=value=>Number.isSafeInteger(value)&&value>=0?pretty(value):'—';
const escNumber=n=>Math.round(Math.max(0,Number(n)||0));
const descDate=value=>{
 if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return '';
 const date=new Date(value+'T12:00:00Z');
 return new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'}).format(date);
};
const graphDate=(value,grain)=>{
 if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return '';
 const date=new Date(value+'T12:00:00Z');
 return new Intl.DateTimeFormat('fr-FR',
   grain==='month'?{month:'short',year:'2-digit',timeZone:'UTC'}:{day:'2-digit',month:'short',timeZone:'UTC'}
 ).format(date);
};

window.GConnectStatisticsE60=function({api,safe,render,isVisible}){
 const state={
   days:180,ready:false,loading:false,error:'',payload:null,
 };
 let requestId=0,dialog=null;
 const current=()=>isVisible();
 const summary=()=>state.payload?.summary||{};
 const total=key=>count(summary()[key]);
 function art(){
   return '<div class="e60-art" aria-hidden="true">'+
     '<div class="e60-art-orbit e60-art-orbit-large"></div><div class="e60-art-orbit e60-art-orbit-small"></div>'+
     '<div class="e60-art-screen"><div class="e60-art-screen-top"><i></i><i></i><i></i></div>'+
     '<div class="e60-art-graph"><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div>'+
     '<span class="e60-art-wave"></span></div>'+
     '<span class="e60-art-token e60-token-building">'+icon('enterprise')+'</span>'+
     '<span class="e60-art-token e60-token-users">'+icon('users')+'</span>'+
     '<span class="e60-art-token e60-token-arrow">'+icon('chart')+'</span>'+
     '<span class="e60-art-dot e60-art-dot-one"></span><span class="e60-art-dot e60-art-dot-two"></span>'+
     '</div>';
 }
 function hero(){
   return '<header class="e60-hero"><div class="e60-hero-copy">'+
     '<span class="e60-eyebrow"><i></i>OBSERVATOIRE · DONNÉES G-CONNECT</span>'+
     '<h1>Statistiques <em>globales</em></h1>'+
     '<p>Le réseau en chiffres : communautés, partenariats et publications réels, consolidés dans une lecture claire et évolutive.</p>'+
     '<div class="e60-hero-note">'+icon('shield')+
     '<span>Indicateurs vérifiés côté serveur · Aucune donnée de démonstration</span></div></div>'+art()+'</header>';
 }
 function range(){
   return '<div class="e60-period"><div><span class="e60-overline">01 / PÉRIODE D’ANALYSE</span>'+
     '<p>'+(state.payload?'Du '+safe(descDate(state.payload.since))+' au '+safe(descDate(state.payload.until)):
     'Sélectionnez une fenêtre de lecture')+'</p></div>'+
     '<div class="e60-period-controls" role="group" aria-label="Sélection de la période">'+
     Object.entries(periods).map(([days,label])=>
       '<button type="button" data-e60-period="'+days+'" class="'+(state.days===Number(days)?'active':'')+
       '" aria-pressed="'+(state.days===Number(days))+'">'+label+'</button>').join('')+
     '<button type="button" data-e60-action="refresh" class="e60-refresh" aria-label="Actualiser les statistiques">'+icon('rotate')+'</button></div></div>';
 }
 function metric(label,key,symbol,tone,detail,caption){
   return '<button type="button" class="e60-metric e60-metric-'+tone+'" data-e60-detail="'+key+'" aria-label="'+safe(label)+' : '+total(key)+
     '. Consulter la définition"><span class="e60-metric-top"><span class="e60-metric-icon">'+icon(symbol)+'</span>'+
     '<span class="e60-metric-more">'+icon('arrow')+'</span></span>'+
     '<strong class="e60-metric-value">'+total(key)+'</strong>'+
     '<span class="e60-metric-label">'+label+'</span><small>'+caption+'</small></button>';
 }
 function metrics(){
   return '<section class="e60-metrics" aria-label="Indicateurs consolidés du réseau">'+
     metric('Nouveaux comptes','new_accounts','chart','blue','Inscriptions sur la période',periods[state.days]+' · tous profils')+
     metric('Entreprises vérifiées','enterprises_verified','enterprise','teal','Entreprises actives et validées','Partenaires professionnels vérifiés')+
     metric('Établissements actifs','institutions_active','school','amber','Établissements référencés et actifs','Réseau des établissements')+
     metric('Comptes enregistrés','accounts_total','users','purple','Tous les comptes enregistrés','Cumul historique de la plateforme')+
     '</section>';
 }
 function valid(payload){
   if(!payload||!payload.summary||!payload.roles||!payload.contents||!payload.trend||
     !Number.isSafeInteger(payload.days)||payload.days!==state.days||
     !['day','week','month'].includes(payload.granularity)||!Array.isArray(payload.trend.labels))return false;
   const keys=['accounts','posts','institutions','enterprise_accounts'],n=payload.trend.labels.length;
   if(n<1||n>53||!keys.every(k=>Array.isArray(payload.trend[k])&&payload.trend[k].length===n&&
     payload.trend[k].every(v=>Number.isSafeInteger(v)&&v>=0)))return false;
   const summaryKeys=[
     'new_accounts','previous_accounts','accounts_total','accounts_active','accounts_banned',
     'institutions_total','institutions_active','enterprises_total','enterprises_verified',
     'posts_total','posts_published','posts_hidden','comments_total','reactions_total',
     'applications_total','reports_pending','subscriptions_active',
   ];
   const integers=keys=>keys.every(key=>Number.isSafeInteger(payload.summary[key])&&payload.summary[key]>=0);
   const valuesAreReal=(items,obj)=>items.every(([key])=>
      Number.isSafeInteger(obj[key])&&obj[key]>=0);
   return integers(summaryKeys)&&
     (payload.summary.growth_percent===null||
       (typeof payload.summary.growth_percent==='number'&&Number.isFinite(payload.summary.growth_percent)))&&
     valuesAreReal(roles,payload.roles)&&valuesAreReal(contents,payload.contents);
 }
 function lineChart(keyA,keyB,labelA,labelB){
   const trend=state.payload?.trend,grain=state.payload?.granularity;
   if(!trend||!Array.isArray(trend.labels))return '<div class="e60-chart-empty">Aucune série disponible.</div>';
   const a=trend[keyA],b=trend[keyB];
   const left=45,right=22,top=26,bottom=47,w=680,h=260;
   const plotW=w-left-right,plotH=h-top-bottom;
   const max=Math.max(1,...a,...b);
   const p=(v,i)=>[left+(trend.labels.length<=1?plotW/2:i*plotW/(trend.labels.length-1)),
     top+plotH-(v/max)*plotH];
   const poly=data=>data.map((v,i)=>p(v,i).map(x=>x.toFixed(1)).join(',')).join(' ');
   const d=data=>data.map((v,i)=>p(v,i).map(x=>x.toFixed(1)).join(',')).map((pos,i)=>(i?'L':'M')+pos).join(' ');
   const area=data=>{
      const first=p(data[0]||0,0),last=p(data[data.length-1]||0,data.length-1);
      return d(data)+' L'+last[0].toFixed(1)+','+(top+plotH)+
        ' L'+first[0].toFixed(1)+','+(top+plotH)+' Z';
   };
   const ticks=[0,0.5,1].map(r=>{
      const y=(top+plotH-r*plotH).toFixed(1);
      return '<line x1="'+left+'" y1="'+y+'" x2="'+(w-right)+'" y2="'+y+'" class="e60-grid-line"/>'+
        '<text x="'+(left-12)+'" y="'+(Number(y)+4)+'" class="e60-axis-y" text-anchor="end">'+pretty(Math.round(max*r))+'</text>';
   }).join('');
   const stride=Math.max(1,Math.ceil((trend.labels.length-1)/5));
   const labels=trend.labels.map((date,i)=>i===0||i===trend.labels.length-1||i%stride===0?
      '<text x="'+p(0,i)[0].toFixed(1)+'" y="'+(h-14)+'" class="e60-axis-x" text-anchor="middle">'+safe(graphDate(date,grain))+'</text>':'').join('');
   const circles=(data,cls,label)=>data.map((v,i)=>{
      const [x,y]=p(v,i);return '<circle cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="3" class="'+cls+'">'+
        '<title>'+safe(graphDate(trend.labels[i],grain))+' · '+safe(label)+' : '+pretty(v)+'</title></circle>';
   }).join('');
   const empty=!a.some(Boolean)&&!b.some(Boolean);
   return '<div class="e60-plot-wrap"><svg class="e60-svg" viewBox="0 0 '+w+' '+h+
     '" role="img" aria-label="Évolution réelle de '+safe(labelA)+' et '+safe(labelB)+'">'+
     '<defs><linearGradient id="e60-fill-'+keyA+'" x1="0" y1="0" x2="0" y2="1">'+
     '<stop offset="0" stop-color="#5979df" stop-opacity=".19"/><stop offset="1" stop-color="#5979df" stop-opacity="0"/></linearGradient></defs>'+
     ticks+'<path d="'+area(a)+'" fill="url(#e60-fill-'+keyA+')" class="e60-area"/>'+
     '<path d="'+d(a)+'" class="e60-line e60-line-primary"/>'+
     '<path d="'+d(b)+'" class="e60-line e60-line-secondary"/>'+
     circles(a,'e60-point-primary',labelA)+circles(b,'e60-point-secondary',labelB)+labels+
     '</svg>'+(empty?'<p class="e60-chart-zero">Aucune activité enregistrée sur cette période.</p>':'')+'</div>';
 }
 function legends(first,second){
   return '<div class="e60-legend"><span><i class="e60-legend-a"></i>'+first+'</span>'+
     '<span><i class="e60-legend-b"></i>'+second+'</span></div>';
 }
 function growth(){
   const data=summary();
   const pct=data.growth_percent;
   let text='';
   if(!state.payload||state.error)text='Comparaison disponible après chargement.';
   else if(pct===null)text='Aucune inscription sur la période précédente : variation non calculable.';
   else {
     text=(pct>0?'+':'')+Number(pct).toLocaleString('fr-FR',{maximumFractionDigits:1})+
       ' % par rapport aux '+periods[state.days]+' précédents.';
   }
   return '<div class="e60-growth"><span class="e60-growth-icon">'+icon('bolt')+'</span><div>'+
     '<strong>Lecture de la dynamique</strong><p>'+safe(text)+'</p></div></div>';
 }
 function activity(){
   const sum=summary();
   return '<div class="e60-activity">'+[
     ['Publications publiées','posts_published','file'],['Candidatures cumulées','applications_total','users'],
     ['Abonnements en cours','subscriptions_active','check'],['Signalements à traiter','reports_pending','shield'],
   ].map(([label,key,ico])=>'<button type="button" class="e60-activity-item" data-e60-detail="'+key+'">'+
     '<span>'+icon(ico)+'</span><div><strong>'+total(key)+'</strong><small>'+label+'</small></div>'+
     '<i>'+icon('arrow')+'</i></button>').join('')+'</div>';
 }
 function bars(items,values){
   const max=Math.max(1,...items.map(([key])=>escNumber(values?.[key])));
   const whole=items.reduce((acc,[key])=>acc+escNumber(values?.[key]),0);
   return '<div class="e60-distribution">'+items.map(([key,label,tone])=>{
     const n=escNumber(values?.[key]);
     return '<div class="e60-distribution-item"><div class="e60-distribution-text"><span>'+safe(label)+'</span>'+
       '<strong>'+count(n)+'</strong></div><div class="e60-distribution-track"><i class="e60-distribution-fill e60-dist-'+tone+
       '" style="--e60-fill:'+Math.round(n/max*100)+'%"></i></div></div>';
   }).join('')+'<div class="e60-distribution-foot">'+pretty(whole)+' éléments répartis</div></div>';
 }
 function makePanel(tag,title,sub,inside,extra=''){
   return '<section class="e60-panel '+extra+'"><div class="e60-panel-top"><div>'+
     '<span class="e60-overline">'+tag+'</span><h2>'+title+'</h2><p>'+sub+'</p></div></div>'+
     inside+'</section>';
 }
 function body(){
   if(state.loading&&!state.ready)return '<section class="e60-pending" role="status">'+icon('chart')+
     '<strong>Lecture des données de la plateforme…</strong><p>Les indicateurs proviennent exclusivement du serveur.</p></section>';
   if(state.error)return '<section class="e60-pending e60-error" role="alert">'+icon('shield')+
     '<strong>Statistiques indisponibles</strong><p>'+safe(state.error)+'</p>'+
     '<button type="button" data-e60-action="refresh">Réessayer</button></section>';
   if(!state.payload)return '';
   const grain=state.payload.granularity;
   const first=makePanel('02 / ACTIVITÉ','Trajectoire du réseau',
     'Évolution des inscriptions et des nouvelles publications, relevées dans le temps.',
     legends('Nouveaux comptes','Publications créées')+lineChart('accounts','posts','Nouveaux comptes','Publications')+growth(),
     'e60-network-panel');
   const second=makePanel('03 / PARTENARIATS','La carte des partenariats',
     'Établissements créés et comptes propriétaires d’entreprises enregistrés sur la période.',
     legends('Établissements créés','Comptes entreprises')+
     lineChart('institutions','enterprise_accounts','Établissements créés','Comptes entreprises')+
     '<p class="e60-source-note">'+icon('info')+
     ' Pour les entreprises, la date de création du compte responsable sert de référence. Ce n’est pas une date de vérification.</p>',
     'e60-partners-panel');
   const rolesPanel=makePanel('04 / PROFILS','Composition du réseau',
     'Tous les comptes enregistrés, par profil déclaré.',
     bars(roles,state.payload.roles),'e60-roles-panel');
   const contentsPanel=makePanel('05 / PUBLICATIONS','Contenus de la communauté',
     'Répartition réelle de toutes les publications enregistrées.',
     bars(contents,state.payload.contents),'e60-contents-panel');
   const opsPanel=makePanel('06 / PILOTAGE','Repères opérationnels',
     'Volumes cumulés, hors estimations et montants financiers simulés.',
     activity(),'e60-ops-panel');
   return '<div class="e60-dashboard">'+first+second+
     '<div class="e60-secondary">'+rolesPanel+contentsPanel+'</div>'+
     opsPanel+'<footer class="e60-provenance">'+icon('shield')+
     ' Données agrégées directement depuis G-Connect. Aucune donnée fictive, aucun export nominatif.'+
     '</footer></div>';
 }
 const page=()=>'<div class="e60-page">'+hero()+range()+metrics()+body()+'</div>';
 async function load(){
   if(state.loading||!current())return;
   const id=++requestId;state.loading=true;state.error='';
   try{
     const payload=await api.adminGlobalStatistics({days:state.days});
     if(id!==requestId)return;
     if(!valid(payload))throw Error('Le serveur a retourné un jeu statistique incomplet.');
     state.payload=payload;
     state.ready=true;
   }catch(error){
     if(id!==requestId)return;
     state.payload=null;
     state.error=error?.message||'Impossible de charger les indicateurs.';
     state.ready=true;
   }finally{
     if(id===requestId){state.loading=false;if(current())render()}
   }
 }
 function ensure(){if(!state.ready&&!state.loading&&current())void load()}
 function refresh(){
   if(state.loading){requestId++;state.loading=false}
   state.ready=false;state.payload=null;void load();
 }
 function detail(key){
   const definitions={
     new_accounts:['Nouveaux comptes', 'Nombre de comptes utilisateurs créés dans la période sélectionnée. La croissance compare cette période à celle de même durée immédiatement précédente.', 'User.date_joined'],
     enterprises_verified:['Entreprises vérifiées','Nombre de profils Entreprise actifs dont la vérification a été confirmée. Les comptes non vérifiés ne sont pas comptés.', 'Enterprise.is_active · Enterprise.verified_at'],
     institutions_active:['Établissements actifs','Nombre d’établissements référencés et marqués actifs dans le catalogue.', 'Institution.is_active'],
     accounts_total:['Comptes enregistrés','Cumul de tous les comptes enregistrés : étudiants, alumni, entreprises, responsables d’établissement et superadmins.', 'User'],
     posts_published:['Publications publiées','Publications non archivées, non brouillon et non masquées par la modération.', 'Post.is_hidden_by_admin · Post.is_draft · Post.is_archived'],
     applications_total:['Candidatures cumulées','Nombre total de candidatures enregistrées sur les opportunités de la plateforme.', 'Application'],
     subscriptions_active:['Abonnements en cours','Abonnements dont le statut est actif et dont la période de validité couvre la date du jour. Cela ne signifie pas que le paiement a été vérifié.', 'BusinessSubscription.status · dates de validité'],
     reports_pending:['Signalements à traiter','Signalements enregistrés et toujours au statut « en attente ».', 'Report.status'],
   };
   if(!Object.hasOwn(definitions,key)||!current())return;
   const [heading,description,source]=definitions[key];
   if(!dialog){
     dialog=document.createElement('dialog');dialog.className='e60-dialog';
     dialog.setAttribute('aria-label','Définition d’un indicateur');
     document.body.appendChild(dialog);
     dialog.addEventListener('click',event=>{
       if(event.target===dialog||event.target.closest('[data-e60-close]'))dialog.close();
     });
   }
   dialog.innerHTML='<div class="e60-dialog-top"><span class="e60-overline">FICHE DE L’INDICATEUR</span>'+
     '<button type="button" data-e60-close aria-label="Fermer">'+icon('cross')+'</button></div>'+
     '<span class="e60-dialog-badge">'+icon('chart')+' MESURE VÉRIFIÉE</span>'+
     '<h2>'+safe(heading)+'</h2><strong class="e60-dialog-number">'+total(key)+'</strong>'+
     '<p>'+safe(description)+'</p><div class="e60-dialog-source">'+icon('info')+
     '<div><span>Référence dans le serveur</span><strong>'+safe(source)+'</strong></div></div>'+
     '<button type="button" class="e60-close" data-e60-close>Fermer</button>';
   if(!dialog.open)dialog.showModal();
 }
 function action(node){
   const period=Number(node.dataset.e60Period);
   if(node.dataset.e60Period&&Object.hasOwn(periods,period)&&period!==state.days){
     state.days=period;refresh();return;
   }
   if(node.dataset.e60Action==='refresh'){refresh();return}
   if(node.dataset.e60Detail)detail(node.dataset.e60Detail);
 }
 return {page,ensure,load,action,peek:()=>({
   ready:state.ready,days:state.days,error:state.error,summary:state.payload?.summary||null,
 })};
};
})();
