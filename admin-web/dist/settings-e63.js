'use strict';
/* E63 | G-Connect Personal Studio. A real profile and preferences surface for the
   existing Superadmin MFA session. Reuses E28/E29 dialogs, never duplicates
   credentials or pretends local display choices are backend account settings. */
(function(){
 const paths={
  user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  pen:'<path d="m3 21 4.2-1 13-13a2.2 2.2 0 0 0-3.1-3.1l-13 13z"/><path d="m14 6 4 4"/>',
  image:'<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="9" r="2"/><path d="m4 18 5-5 3 3 3-3 5 5"/>',
  shield:'<path d="m12 2 9 4v6c0 6-4 9-9 10-5-1-9-4-9-10V6z"/><path d="m8 12 3 3 5-6"/>',
  lock:'<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  sparkle:'<path d="m12 2 2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z"/>',
  motion:'<path d="M3 12h4m3 0h4m3 0h4M6 6l3 3-3 3m8 0 3 3-3 3"/>',
  monitor:'<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M9 22h6m-3-4v4"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9.5 9a3 3 0 1 1 5 2.5c-1 .7-2.5 1.2-2.5 3M12 18h.01"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  key:'<circle cx="8" cy="15" r="5"/><path d="m12 11 9-9m-4 1 4 4m-6-2 3 3"/>',
  history:'<path d="M3 12a9 9 0 1 0 3-6M3 3v6h6"/><path d="M12 7v5l4 2"/>',
  check:'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  refresh:'<path d="M20 5v6h-6M4 19v-6h6"/><path d="M5 10a8 8 0 0 1 14-3l1 4M4 14a8 8 0 0 0 14 3"/>',
  mail:'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/>',
  globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-6 6-6 12 0 18m0-18c6 6 6 12 0 18"/>',
  dots:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
 };
 const icon=n=>'<svg viewBox="0 0 24 24" fill="none" aria-hidden="true" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+(paths[n]||paths.shield)+'</svg>';
 const motionOptions={system:'Selon le système',on:'Activées',off:'Désactivées'};
 const format=x=>Number.isSafeInteger(x)&&x>=0?new Intl.NumberFormat('fr-FR').format(x):'—';
 window.GConnectSettingsE63=function({api,safe,profile,validPhoto,motion,setMotion,openProfile,openAbout,go,render,isVisible}){
  const state={ready:false,loading:false,security:null,error:''};
  let seq=0;
  const visible=()=>isVisible();
  const my=()=>profile()||{};
  const name=()=>{
   const p=my();return String(p.full_name||[p.first_name,p.last_name].filter(Boolean).join(' ')||p.email||'Superadmin G-Connect');
  };
  const avatar=(cls='')=>{
   const photo=validPhoto(my().photo_url),initials=String(
    [my().first_name,my().last_name].filter(Boolean).map(x=>x[0]).join('')
   ).slice(0,2).toUpperCase()||'SA';
   return '<span class="e63-avatar '+cls+'">'+(photo?
    '<img src="'+safe(photo)+'" alt="Photo du compte connecté" referrerpolicy="no-referrer">':
    '<span aria-hidden="true">'+safe(initials)+'</span>')+
    '<i>'+icon('check')+'</i></span>';
  };
  function art(){
   return '<div class="e63-art" aria-hidden="true"><i class="e63-orbit e63-orbit-large"></i>'+
    '<i class="e63-orbit e63-orbit-small"></i><span class="e63-art-sheet"><span>'+icon('user')+
    '</span><b></b><b></b><b></b><small>'+icon('check')+'</small></span>'+
    '<i class="e63-art-float e63-art-float-a">'+icon('pen')+'</i>'+
    '<i class="e63-art-float e63-art-float-b">'+icon('shield')+'</i>'+
    '<i class="e63-art-float e63-art-float-c">'+icon('sparkle')+'</i>'+
    '<i class="e63-star e63-star-a"></i><i class="e63-star e63-star-b"></i></div>';
  }
  function hero(){
   return '<header class="e63-hero"><div class="e63-hero-copy">'+
    '<span class="e63-overline e63-hero-kicker"><i></i>ESPACE PERSONNEL · G-CONNECT</span>'+
    '<h1>Profil <em>& paramètres</em></h1>'+
    '<p>Votre identité, vos préférences et la sécurité de votre compte, réunies dans un espace personnel. Chaque modification sensible reste soumise aux contrôles du serveur.</p>'+
    '<span class="e63-trust">'+icon('shield')+' Compte professionnel vérifié par authentification renforcée</span>'+
    '</div>'+art()+'</header>';
  }
  function profileCard(){
   const p=my();return '<section class="e63-panel e63-profile-panel"><div class="e63-panel-head"><div>'+
    '<span class="e63-overline">01 / IDENTITÉ</span><h2>Votre signature</h2>'+
    '<p>Les données de ce profil sont conservées sur votre compte G-Connect.</p></div>'+
    '<span class="e63-panel-symbol">'+icon('user')+'</span></div>'+
    '<div class="e63-identity">'+avatar('e63-identity-avatar')+
    '<div class="e63-identity-main"><span class="e63-role">SUPERADMIN · CONSOLE CENTRALE</span>'+
    '<h3>'+safe(name())+'</h3><p>'+safe(p.email||'Adresse indisponible')+'</p>'+
    '<span class="e63-membership">'+icon('check')+' Accès professionnel actif</span></div></div>'+
    '<dl class="e63-details">'+
    '<div><dt>'+icon('user')+' Prénom</dt><dd>'+safe(p.first_name||'Non renseigné')+'</dd></div>'+
    '<div><dt>'+icon('user')+' Nom</dt><dd>'+safe(p.last_name||'Non renseigné')+'</dd></div>'+
    '<div><dt>'+icon('mail')+' Adresse e-mail</dt><dd>'+safe(p.email||'Non renseignée')+'</dd></div>'+
    '<div><dt>'+icon('globe')+' Téléphone</dt><dd>'+safe(p.phone_number||'Non renseigné')+'</dd></div>'+
    '</dl>'+
    '<div class="e63-profile-actions"><button type="button" class="e63-primary e63-primary-compact" data-e63-action="profile">'+
    icon('pen')+' Modifier mon profil '+icon('arrow')+'</button>'+
    '<button type="button" class="e63-secondary" data-e63-action="photo">'+icon('image')+' Ma photo</button></div>'+
    '</section>';
  }
  function prefsCard(){
   const selected=motion();
   return '<section class="e63-panel e63-preferences"><div class="e63-panel-head e63-pref-head"><div>'+
    '<span class="e63-overline">02 / EXPÉRIENCE</span><h2>Mon espace, mon rythme</h2>'+
    '<p>Des réglages d’affichage locaux, sans incidence sur vos autorisations.</p></div>'+
    '<span class="e63-panel-symbol">'+icon('sparkle')+'</span></div>'+
    '<div class="e63-pref-body"><div class="e63-pref-lead"><span>'+icon('motion')+'</span><div>'+
    '<strong>Animations de l’interface</strong><p>Choisissez le mouvement qui vous convient. Vos préférences sont mémorisées dans ce navigateur.</p>'+
    '</div></div><div class="e63-motion-grid" role="group" aria-label="Préférences d’animations">'+
    Object.entries(motionOptions).map(([key,label])=>
      '<button type="button" data-e63-motion="'+key+'" aria-pressed="'+(selected===key)+
      '" class="'+(selected===key?'active':'')+'"><span class="e63-motion-preview e63-motion-'+key+'">'+
      icon(key==='off'?'lock':key==='system'?'monitor':'motion')+'</span><strong>'+label+'</strong>'+
      '<small>'+(key==='system'?'Respecte votre appareil':key==='on'?'Transitions dynamiques':'Effets limités')+
      '</small></button>').join('')+
    '</div><div class="e63-pref-rule"></div>'+
    '<div class="e63-pref-locked"><span>'+icon('monitor')+'</span><div>'+
    '<strong>Apparence harmonisée G-Connect</strong>'+
    '<p>Le thème partagé reste cohérent dans les interfaces professionnelles. Aucun réglage ici ne modifie le thème des autres comptes.</p>'+
    '</div><span class="e63-pref-tag">Style commun</span></div></div></section>';
  }
  const security=()=>state.security||{};
  function safetyCard(){
   const data=security(),sec=data.my_mfa||{},sum=data.summary||{};
   const ok=state.ready&&!state.error&&data.my_mfa;
   return '<section class="e63-panel e63-safety"><div class="e63-panel-head e63-safety-head"><div>'+
    '<span class="e63-overline">03 / ACCÈS PROTÉGÉ</span><h2>Votre coffre d’accès</h2>'+
    '<p>Informations vérifiées via votre session Superadmin.</p></div>'+
    '<span class="e63-panel-symbol">'+icon('shield')+'</span></div>'+
    '<div class="e63-safety-state">'+
    '<span class="e63-safety-mark">'+icon(ok&&sec.enabled?'check':'shield')+'</span>'+
    '<div><strong>'+(state.error?'État indisponible':!state.ready?'Contrôle du statut…':
      sec.enabled?'Authentification renforcée active':'Authentification à vérifier')+'</strong>'+
    '<small>'+(state.error?'Le serveur ne répond pas au contrôle MFA.':
     ok&&sec.enabled?'Session actuellement validée par MFA':
     !state.ready?'Lecture des informations serveur':'Veuillez vérifier votre configuration sécurisée')+
    '</small></div></div>'+
    '<div class="e63-safety-stats"><div><span>'+icon('monitor')+' Mes appareils actifs</span>'+
    '<strong>'+(ok?format(data.my_sessions?.length):'—')+'</strong></div>'+
    '<div><span>'+icon('key')+' Codes de secours disponibles</span>'+
    '<strong>'+(ok?format(sec.remaining_recovery_codes):'—')+'</strong></div>'+
    '</div><p class="e63-safety-notice">'+icon('lock')+
    ' Vos codes secrets ne sont jamais affichés ici. Une modification du mot de passe révoque les sessions et exige une reconnexion MFA.</p>'+
    '<div class="e63-safety-actions"><button type="button" class="e63-primary" data-e63-action="password">'+
    icon('key')+' Changer mon mot de passe '+icon('arrow')+'</button>'+
    '<button type="button" class="e63-secondary" data-e63-action="sessions">'+icon('monitor')+
    ' Gérer mes sessions</button></div>'+
    (state.error?'<p class="e63-error" role="alert">'+safe(state.error)+
      ' <button type="button" data-e63-action="refresh">Réessayer</button></p>':'')+
    '</section>';
  }
  function navigation(){
   return '<section class="e63-panel e63-shortcuts"><div class="e63-panel-head"><div>'+
    '<span class="e63-overline">04 / RACCOURCIS</span><h2>Votre console en un geste</h2>'+
    '<p>Accédez aux contrôles sans quitter votre espace sécurisé.</p></div></div>'+
    '<div class="e63-shortcut-list">'+[
      ['audit','history','Journal d’audit','Voir les actions réellement enregistrées.'],
      ['sessions','shield','Sessions & sécurité','Consulter l’état des accès et des appareils.'],
      ['about','help','À propos de G-Connect','Retrouver les informations de votre espace.'],
    ].map(([action,ic,title,sub])=>'<button type="button" data-e63-action="'+action+
      '"><span class="e63-shortcut-icon">'+icon(ic)+'</span><span><strong>'+title+
      '</strong><small>'+sub+'</small></span><i>'+icon('arrow')+'</i></button>').join('')+
    '</div></section>';
  }
  function page(){
   return '<div class="e63-page">'+hero()+
    '<div class="e63-layout"><div class="e63-main">'+profileCard()+prefsCard()+'</div>'+
    '<div class="e63-side">'+safetyCard()+navigation()+'</div></div>'+
    '<footer class="e63-footer">'+icon('shield')+
    ' Vos informations personnelles sont modifiées uniquement via les API sécurisées G-Connect. Les préférences d’animation sont locales.</footer></div>';
  }
  function valid(d){
   return !!(d&&d.my_mfa&&typeof d.my_mfa.enabled==='boolean'&&
    Number.isSafeInteger(d.my_mfa.remaining_recovery_codes)&&
    Array.isArray(d.my_sessions)&&d.my_sessions.every(x=>Number.isSafeInteger(x.id)&&
    typeof x.current==='boolean')&&d.summary&&
    Number.isSafeInteger(d.summary.sessions_active));
  }
  async function load(){
   if(state.loading||!visible())return;
   state.loading=true;state.error='';const current=++seq;
   try{
    const d=await api.adminSecurityOverview({days:30});
    if(current!==seq)return;
    if(!valid(d))throw Error('Le serveur a retourné un état de sécurité incomplet.');
    state.security=d;state.ready=true;
   }catch(error){
    if(current!==seq)return;
    state.security=null;state.ready=true;
    state.error=error?.message||'Informations de sécurité indisponibles.';
   }finally{
    if(current===seq){state.loading=false;if(visible())render();}
   }
  }
  function refresh(){
   if(state.loading){++seq;state.loading=false}
   state.security=null;state.ready=false;void load();
  }
  function ensure(){if(!state.ready&&!state.loading&&visible())void load();}
  function action(node){
   if(node.dataset.e63Motion){
    const v=node.dataset.e63Motion;
    if(Object.hasOwn(motionOptions,v)&&motion()!==v){setMotion(v);render();}
    return;
   }
   const command=node.dataset.e63Action;
   if(command==='profile'||command==='photo'){openProfile('profile');return;}
   if(command==='password'){openProfile('security');return;}
   if(command==='preferences'){openProfile('settings');return;}
   if(command==='sessions'||command==='audit'){go(command);return;}
   if(command==='about'){openAbout();return;}
   if(command==='refresh'){refresh();}
  }
  return {page,ensure,load,action,refresh,peek:()=>({
   ready:state.ready,error:state.error,deviceCount:state.security?.my_sessions?.length??null,
  })};
 };
})();
