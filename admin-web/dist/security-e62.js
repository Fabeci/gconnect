'use strict';
/* E62 G-Connect | Security Observatory.
   The API provides factual aggregates and only the signed-in Superadmin's
   web sessions; this view never sees device secrets or raw IP addresses. */
(function(){
 const paths={
  shield:'<path d="m12 2 9 4v6c0 5.5-4 9-9 10-5-1-9-4-9-10V6z"/><path d="m8 12 3 3 5-6"/>',
  screen:'<rect x="3" y="4" width="18" height="14" rx="3"/><path d="M8 22h8m-4-4v4"/>',
  phone:'<rect x="6" y="2" width="12" height="20" rx="3"/><path d="M11 18h2"/>',
  tablet:'<rect x="4" y="2" width="16" height="20" rx="3"/><path d="M11 19h2"/>',
  check:'<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  key:'<circle cx="8" cy="15" r="5"/><path d="m12 11 9-9m-4 1 4 4m-6-2 3 3"/>',
  alert:'<path d="m12 3 10 18H2L12 3z"/><path d="M12 9v5m0 3h.01"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  refresh:'<path d="M20 5v6h-6M4 19v-6h6"/><path d="M5 10a8 8 0 0 1 14-3l1 4M4 14a8 8 0 0 0 14 3"/>',
  close:'<path d="M5 5 19 19M19 5 5 19"/>',
  globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-6 6-6 12 0 18m0-18c6 6 6 12 0 18"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
 };
 const icon=name=>'<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+(paths[name]||paths.shield)+'</svg>';
 const periods={7:'7 jours',30:'30 jours',90:'90 jours'};
 const numbers=x=>new Intl.NumberFormat('fr-FR').format(x);
 const count=x=>Number.isSafeInteger(x)&&x>=0?numbers(x):'—';
 const formatDate=value=>{
  const d=new Date(value||'');
  return Number.isNaN(d.getTime())?'Indisponible':
   new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium',timeStyle:'short'}).format(d);
 };
 const dayDate=value=>{
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return '';
  return new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'short',timeZone:'UTC'})
   .format(new Date(value+'T12:00:00Z'));
 };
 const definitions={
  sessions_active:['Sessions web actives','Sessions professionnelles web non révoquées, non expirées et non inactives. Une même personne peut utiliser plusieurs appareils.','EstablishmentWebSession'],
  mfa_enabled:['MFA confirmée','Comptes professionnels actifs dont le dispositif de double authentification est confirmé.','PrivilegedMFADevice.confirmed_at'],
  failures:['Échecs de connexion','Tentatives de connexion échouées inscrites au journal sur la période. Il ne s’agit pas nécessairement d’incidents de sécurité avérés.','LoginAttempt.success=False'],
  expiring_24h:['Sessions arrivant à échéance','Sessions web actuellement actives dont la date d’expiration est atteinte dans les prochaines 24 heures.','EstablishmentWebSession.expires_at'],
 };
 const ownDeviceIcon=device=>device?.kind==='mobile'?'phone':device?.kind==='tablette'?'tablet':'screen';
 window.GConnectSecurityE62=function({api,safe,render,isVisible}){
  let counter=0,dialog=null;
  const state={days:30,ready:false,loading:false,error:'',payload:null,revokeBusy:false};
  const visible=()=>isVisible();
  const summary=()=>state.payload?.summary||{};
  const metric=(key,name,symbol,tone,sub)=>
   '<button type="button" class="e62-metric e62-metric-'+tone+'" data-e62-detail="'+key+
   '" aria-label="'+safe(name)+': '+count(summary()[key])+'. Ouvrir la définition">'+
   '<span class="e62-metric-top"><span class="e62-metric-icon">'+icon(symbol)+'</span>'+
   '<span class="e62-metric-link">'+icon('arrow')+'</span></span>'+
   '<strong>'+count(summary()[key])+'</strong><span>'+safe(name)+'</span>'+
   '<small>'+safe(sub)+'</small></button>';
  function art(){
   return '<div class="e62-art" aria-hidden="true"><span class="e62-orbit e62-orbit-large"></span>'+
    '<span class="e62-orbit e62-orbit-small"></span>'+
    '<div class="e62-art-lock">'+icon('lock')+'<span>'+icon('check')+'</span></div>'+
    '<i class="e62-art-token e62-art-token-first">'+icon('screen')+'</i>'+
    '<i class="e62-art-token e62-art-token-second">'+icon('key')+'</i>'+
    '<i class="e62-art-token e62-art-token-third">'+icon('shield')+'</i>'+
    '<b class="e62-glow-dot e62-glow-one"></b><b class="e62-glow-dot e62-glow-two"></b></div>';
  }
  function hero(){
   return '<header class="e62-hero"><div class="e62-hero-copy">'+
    '<span class="e62-eyebrow"><i></i>CONSOLE PROTÉGÉE · OBSERVATOIRE DES ACCÈS</span>'+
    '<h1>Sessions <em>& sécurité</em></h1>'+
    '<p>Supervisez l’état des accès professionnels, la double authentification et vos propres appareils connectés, sans exposer de secrets ou de données personnelles.</p>'+
    '<span class="e62-trust">'+icon('shield')+' Contrôle MFA actif · Gestion des appareils avec confirmation</span>'+
    '</div>'+art()+'</header>';
  }
  function controls(){
   return '<section class="e62-period"><div><span class="e62-overline">01 / PÉRIODE D’OBSERVATION</span>'+
    '<p>'+(state.payload?'Du '+safe(dayDate(state.payload.since))+' au '+safe(dayDate(state.payload.until)):'Fenêtre de lecture des tentatives de connexion')+
    '</p></div><div class="e62-period-buttons" role="group" aria-label="Période d’analyse">'+
    Object.entries(periods).map(([days,label])=>
      '<button type="button" data-e62-days="'+days+'" aria-pressed="'+(state.days===Number(days))+
      '" class="'+(state.days===Number(days)?'active':'')+'">'+label+'</button>').join('')+
    '<button type="button" data-e62-action="refresh" title="Actualiser" aria-label="Actualiser les données">'+icon('refresh')+'</button></div></section>';
  }
  function metrics(){
   return '<section class="e62-metrics" aria-label="Indicateurs de sécurité">'+
    metric('sessions_active','Sessions actives','screen','blue','Tous les appareils professionnels')+
    metric('mfa_enabled','MFA confirmée','shield','teal','Comptes professionnels protégés')+
    metric('failures','Échecs de connexion','alert','coral','Tentatives enregistrées · '+periods[state.days])+
    metric('expiring_24h','Échéances sous 24 h','clock','violet','Sessions web proches de l’expiration')+
    '</section>';
  }
  function pending(){
   return '<section class="e62-pending" role="'+(state.error?'alert':'status')+'">'+
    icon(state.error?'alert':'shield')+'<strong>'+
    (state.error?'Informations de sécurité indisponibles':'Consultation des données de sécurité…')+
    '</strong><p>'+safe(state.error||'Les valeurs proviennent exclusivement du backend G-Connect.')+'</p>'+
    (state.error?'<button type="button" data-e62-action="refresh">Réessayer</button>':'')+
    '</section>';
  }
  function deviceItem(row){
   const dev=row.device||{},who=(dev.browser||'Autre')+' · '+(dev.os||'Autre');
   return '<div class="e62-device'+(row.current?' e62-device-current':'')+'">'+
    '<span class="e62-device-icon">'+icon(ownDeviceIcon(dev))+'</span>'+
    '<div class="e62-device-main"><div class="e62-device-title"><strong>'+safe(who)+'</strong>'+
    (row.current?'<span class="e62-current-badge">'+icon('check')+' Cette session</span>':'')+'</div>'+
    '<p>Dernière activité : '+safe(formatDate(row.last_seen_at))+'</p>'+
    '<small>Ouverte le '+safe(formatDate(row.created_at))+' · Expiration : '+safe(formatDate(row.expires_at))+'</small></div>'+
    '<div class="e62-device-actions">'+(row.current?
      '<span class="e62-kept">'+icon('shield')+' Session protégée</span>':
      '<button type="button" data-e62-revoke="'+Number(row.id)+'">Déconnecter '+icon('arrow')+'</button>')+
    '</div></div>';
  }
  function deviceArea(){
   const all=state.payload?.my_sessions||[];
   return '<section class="e62-panel e62-devices"><div class="e62-panel-head"><div>'+
    '<span class="e62-overline">02 / APPAREILS PERSONNELS</span><h2>Mes sessions connectées</h2>'+
    '<p>Uniquement les appareils du Superadmin actuellement connecté.</p></div>'+
    '<span class="e62-panel-badge">'+icon('lock')+' Accès privé</span></div>'+
    '<div class="e62-devices-list">'+(all.length?all.map(deviceItem).join(''):
     '<div class="e62-empty">'+icon('screen')+'<strong>Aucun appareil actif retourné</strong>'+
     '<p>Les appareils peuvent avoir expiré ou être déjà déconnectés.</p></div>')+'</div>'+
    '<div class="e62-panel-foot">'+icon('shield')+
     ' Aucune adresse IP, empreinte d’appareil ou donnée de session secrète n’est exposée.</div></section>';
  }
  function mfaArea(){
   const mfa=state.payload?.my_mfa||{},s=summary();
   const total=Number(s.professionals_active)||0,enabled=Number(s.mfa_enabled)||0;
   const ratio=total?Math.round(100*enabled/total):null;
   return '<section class="e62-panel e62-posture"><div class="e62-panel-head"><div>'+
    '<span class="e62-overline">03 / POSTURE D’ACCÈS</span><h2>Double authentification</h2>'+
    '<p>Couverture des comptes professionnels actifs.</p></div></div>'+
    '<div class="e62-ring-wrap"><div class="e62-ring" style="--e62-percent:'+(ratio??0)+'">'+
    '<div><strong>'+(ratio===null?'—':ratio+' %')+'</strong><small>MFA confirmée</small></div></div>'+
    '<div class="e62-ring-copy"><strong>'+count(s.mfa_enabled)+' / '+count(s.professionals_active)+'</strong>'+
    '<span>Comptes professionnels confirmés</span>'+
    '<small>'+count(s.mfa_pending)+' compte(s) sans MFA confirmée</small></div></div>'+
    '<div class="e62-my-mfa"><span class="e62-my-mfa-icon">'+icon(mfa.enabled?'check':'alert')+'</span>'+
    '<div><strong>'+ (mfa.enabled?'Votre MFA est configurée':'Votre MFA n’est pas confirmée')+'</strong>'+
    '<small>Codes de secours encore utilisables : '+count(mfa.remaining_recovery_codes)+
    '</small></div></div>'+
    '<p class="e62-posture-note">Aucun secret TOTP ni code de secours n’est affiché. Les compteurs ne constituent pas une attestation d’absence d’incident.</p></section>';
  }
  function chart(){
   const t=state.payload?.trend;
   if(!t||!t.labels?.length)return '';
   const countBars=t.labels.length;
   const largest=Math.max(1,...t.successes,...t.failures);
   const column=t.labels.map((d,i)=>{
    const success=t.successes[i],failure=t.failures[i];
    return '<span class="e62-chart-column" title="'+safe(dayDate(d))+': '+count(success)+' succès, '+count(failure)+' échecs">'+
      '<span class="e62-column-values"><i class="e62-column-good" style="--e62-height:'+(success/largest*100)+'%"></i>'+
      '<i class="e62-column-fail" style="--e62-height:'+(failure/largest*100)+'%"></i></span>'+
      '<span class="e62-chart-label">'+(i===0||i===countBars-1||i%Math.max(1,Math.ceil(countBars/6))===0?safe(dayDate(d)):'')+'</span></span>';
   }).join('');
   return '<div class="e62-chart" role="img" aria-label="Évolution des tentatives de connexion enregistrées">'+column+'</div>';
  }
  function activity(){
   return '<section class="e62-panel e62-activity"><div class="e62-panel-head"><div>'+
    '<span class="e62-overline">04 / ACTIVITÉS ENREGISTRÉES</span>'+
    '<h2>Tendances des connexions</h2>'+
    '<p>Historique factuel des tentatives consignées, sans données individuelles.</p></div>'+
    '<div class="e62-chart-legend"><span><i></i>Réussites</span><span><i></i>Échecs</span></div></div>'+
    '<div class="e62-chart-inner">'+chart()+
    '<div class="e62-chart-totals"><span>'+icon('check')+count(summary().successes)+' réussites</span>'+
    '<span>'+icon('alert')+count(summary().failures)+' échecs</span></div>'+
    '<p>Source : LoginAttempt. Ce journal recense les tentatives enregistrées, pas nécessairement toutes les connexions de la plateforme.</p>'+
    '</div></section>';
  }
  function vigilance(){
   const s=summary();
   return '<section class="e62-panel e62-watch"><div class="e62-panel-head"><div>'+
    '<span class="e62-overline">05 / SURVEILLANCE</span><h2>Repères opérationnels</h2>'+
    '<p>Des états observés, sans qualifier automatiquement un incident.</p></div></div>'+
    '<div class="e62-watch-row"><span>'+icon('key')+'</span><div><strong>'+count(s.revoked_7d)+'</strong>'+
    '<small>Sessions web révoquées · 7 derniers jours</small></div></div>'+
    '<div class="e62-watch-row"><span>'+icon('clock')+'</span><div><strong>'+count(s.expiring_24h)+'</strong>'+
    '<small>Sessions actives expirant sous 24 h</small></div></div>'+
    '<div class="e62-watch-row"><span>'+icon('alert')+'</span><div><strong>'+count(s.failures)+'</strong>'+
    '<small>Tentatives échouées · '+periods[state.days]+'</small></div></div>'+
    '<div class="e62-watch-note">'+icon('shield')+
    '<p>Les sessions des autres utilisateurs ne sont pas visibles. Le contrôle individuel des comptes reste dans le module Utilisateurs.</p></div></section>';
  }
  function dashboard(){
   if(state.loading&&!state.ready||state.error||!state.payload)return pending();
   return '<div class="e62-dashboard">'+
    '<div class="e62-main-stack">'+deviceArea()+activity()+'</div>'+
    '<div class="e62-side-stack">'+mfaArea()+vigilance()+'</div>'+
    '</div><footer class="e62-footer">'+icon('shield')+
    ' Données serveur réelles · Accès MFA vérifié · Aucune session d’un tiers exposée</footer>';
  }
  function page(){return '<div class="e62-page">'+hero()+controls()+metrics()+dashboard()+'</div>';}
  function valid(d){
   if(!d||d.days!==state.days||!d.summary||!d.my_mfa||!Array.isArray(d.my_sessions)||!d.trend||
       !Array.isArray(d.trend.labels)||!Array.isArray(d.trend.successes)||
       !Array.isArray(d.trend.failures)||d.trend.labels.length!==d.trend.successes.length||
       d.trend.labels.length!==d.trend.failures.length)return false;
   const keys=['sessions_active','professionals_active','mfa_enabled','mfa_pending','failures','successes','revoked_7d','expiring_24h'];
   if(!keys.every(k=>Number.isSafeInteger(d.summary[k])&&d.summary[k]>=0))return false;
   if(!Number.isSafeInteger(d.my_mfa.remaining_recovery_codes)||typeof d.my_mfa.enabled!=='boolean')return false;
   if(!d.trend.successes.every(x=>Number.isSafeInteger(x)&&x>=0)||!d.trend.failures.every(x=>Number.isSafeInteger(x)&&x>=0))return false;
   return d.my_sessions.every(row=>Number.isSafeInteger(row.id)&&row.id>0&&
     typeof row.current==='boolean'&&row.device&&
     ['mobile','ordinateur','tablette','inconnu'].includes(row.device.kind));
  }
  async function load(){
   if(state.loading||!visible())return;
   state.loading=true;state.error='';const seq=++counter;
   try{
    const d=await api.adminSecurityOverview({days:state.days});
    if(seq!==counter)return;
    if(!valid(d))throw Error('Le serveur a retourné des informations de sécurité incomplètes.');
    state.payload=d;state.ready=true;
   }catch(e){
    if(seq!==counter)return;
    state.payload=null;state.ready=true;state.error=e?.message||'Erreur de chargement des informations.';
   }finally{
    if(seq===counter){state.loading=false;if(visible())render()}
   }
  }
  function reload(){
   if(state.loading){++counter;state.loading=false}
   state.payload=null;state.ready=false;void load();
  }
  function ensure(){if(!state.ready&&!state.loading&&visible())void load()}
  function close(){if(dialog?.open)dialog.close()}
  function ensureDialog(){
   if(!dialog){
    dialog=document.createElement('dialog');dialog.className='e62-dialog';
    dialog.setAttribute('aria-label','Confirmation de sécurité');
    document.body.appendChild(dialog);
    dialog.addEventListener('click',e=>{
     if(e.target===dialog||e.target.closest('[data-e62-dialog-close]'))close();
    });
   }
   return dialog;
  }
  function info(key){
   if(!visible()||!Object.hasOwn(definitions,key))return;
   const [title,desc,source]=definitions[key];
   const box=ensureDialog();
   box.innerHTML='<div class="e62-dialog-head"><span class="e62-overline">DÉFINITION DE L’INDICATEUR</span>'+
    '<button type="button" aria-label="Fermer" data-e62-dialog-close>'+icon('close')+'</button></div>'+
    '<span class="e62-dialog-badge">'+icon('shield')+' MESURE VÉRIFIABLE</span>'+
    '<h2>'+safe(title)+'</h2><strong class="e62-dialog-count">'+count(summary()[key])+'</strong>'+
    '<p>'+safe(desc)+'</p><div class="e62-dialog-source">'+icon('grid')+
    '<span>Provenance : <strong>'+safe(source)+'</strong></span></div>';
   box.showModal();
  }
  function confirm(id){
   if(!visible())return;
   const session=state.payload?.my_sessions?.find(row=>row.id===id);
   if(!session||session.current)return;
   const box=ensureDialog();
   const device=session.device||{};
   box.innerHTML='<div class="e62-dialog-head"><span class="e62-overline">ACTION SENSIBLE · AUTHENTIFICATION</span>'+
    '<button type="button" aria-label="Fermer" data-e62-dialog-close>'+icon('close')+'</button></div>'+
    '<span class="e62-dialog-badge e62-danger-badge">'+icon('alert')+' CONFIRMATION OBLIGATOIRE</span>'+
    '<h2>Déconnecter cet appareil ?</h2>'+
    '<p>La session <strong>'+safe(device.browser||'Autre')+' · '+safe(device.os||'Autre')+
    '</strong> sera immédiatement révoquée. Cette action ne supprime pas le compte et ne réinitialise pas la MFA.</p>'+
    '<div class="e62-confirm-detail">'+icon('screen')+' Appareil ouvert le '+safe(formatDate(session.created_at))+'</div>'+
    '<label class="e62-confirm-label" for="e62-confirm-word">Saisissez <strong>REVOQUER</strong> pour confirmer</label>'+
    '<input id="e62-confirm-word" type="text" autocomplete="off" spellcheck="false" maxlength="16" data-e62-confirm-input>'+
    '<p class="e62-dialog-error" data-e62-dialog-error role="alert" hidden></p>'+
    '<div class="e62-dialog-actions"><button type="button" data-e62-dialog-close>Annuler</button>'+
    '<button type="button" class="e62-revoke-button" data-e62-submit="'+id+'" disabled>Révoquer cet appareil</button></div>';
   box.showModal();box.querySelector('[data-e62-confirm-input]')?.focus();
  }
  function onInput(el){
   if(!el.matches('[data-e62-confirm-input]'))return;
   const button=dialog?.querySelector('[data-e62-submit]');
   if(button)button.disabled=el.value!=='REVOQUER'||state.revokeBusy;
  }
  async function revoke(id){
   const word=dialog?.querySelector('[data-e62-confirm-input]')?.value;
   if(word!=='REVOQUER'||state.revokeBusy)return;
   const row=state.payload?.my_sessions?.find(r=>r.id===id);
   if(!row||row.current)return;
   state.revokeBusy=true;
   const button=dialog.querySelector('[data-e62-submit]');
   if(button)button.disabled=true;
   try{
    await api.adminSecurityRevokeOwnSession(id,{confirmation:'REVOQUER'});
    close();reload();
   }catch(e){
    const error=dialog?.querySelector('[data-e62-dialog-error]');
    if(error){error.textContent=e?.message||'Révocation refusée.';error.hidden=false;}
    if(button)button.disabled=false;
   }finally{state.revokeBusy=false}
  }
  function action(el){
   if(el.dataset.e62Days){
    const days=Number(el.dataset.e62Days);
    if(Object.hasOwn(periods,days)&&state.days!==days){state.days=days;reload();}
    return;
   }
   if(el.dataset.e62Action==='refresh'){reload();return}
   if(el.dataset.e62Detail){info(el.dataset.e62Detail);return}
   if(el.dataset.e62Revoke){confirm(Number(el.dataset.e62Revoke));return}
   if(el.dataset.e62Submit){void revoke(Number(el.dataset.e62Submit));}
  }
  return {page,ensure,load,action,onInput,peek:()=>({
   days:state.days,ready:state.ready,error:state.error,
   sessions:state.payload?.my_sessions?.length??null,
   summary:state.payload?.summary??null,
  })};
 };
})();
