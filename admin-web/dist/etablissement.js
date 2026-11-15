'use strict';
// E2 : modules visibles uniquement après validation du compte par le backend.
// Les modules non raccordés à l’API restent des brouillons locaux non persistés.
const modules = [
  {id:'overview',label:'Vue d’ensemble',icon:'home',title:'Un établissement bien connecté.',description:'Retrouvez en un seul endroit les activités de votre communauté académique.',tasks:['Vue synthétique des promotions','Évolution des affiliations et des événements','Accès direct aux principaux modules']},
  {id:'promotions',label:'Promotions & filières',icon:'layers',title:'Organisez vos promotions.',description:'Préparez la gestion des filières, années et promotions de votre établissement.',tasks:['Filières et parcours','Promotions et années académiques','Rattachements et import contrôlé']},
  {id:'members',label:'Étudiants & Alumni',icon:'people',title:'Votre communauté, au même endroit.',description:'Accédez aux profils rattachés à votre établissement selon leurs autorisations.',tasks:['Affiliations validées','Étudiants et anciens étudiants','Recherches et filtres par promotion']},
  {id:'events',label:'Événements & annonces',icon:'calendar',title:'Faites vivre le campus.',description:'Planifiez les annonces et rencontres accessibles à votre communauté.',tasks:['Annonces de l’établissement','Événements et inscriptions','Historique de publication']},
  {id:'team',label:'Équipe administrative',icon:'shield',title:'Gérez votre équipe.',description:'Préparez les accès des personnes autorisées à administrer cet établissement.',tasks:['Invitations et membres','Rôles internes et permissions','Journal des changements']},
  {id:'subscription',label:'Abonnement & factures',icon:'receipt',title:'Votre abonnement G-Connect.',description:'Consultez vos droits et vos échéances après activation du service de facturation.',tasks:['Formules 1, 6 ou 12 mois','Renouvellements et échéances','Factures et historique des paiements']},
  {id:'settings',label:'Paramètres',icon:'settings',title:'Personnalisez votre espace.',description:'Retrouvez les informations et les préférences de votre établissement.',tasks:['Identité et coordonnées','Préférences et notifications','Sécurité du compte']}
];
const glyphs = {
  home:'<path d="m3 10 9-7 9 7v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 21v-8h6v8"/>',
  layers:'<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
  people:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  calendar:'<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  receipt:'<path d="M4 3h16v18l-4-2-4 2-4-2-4 2V3Z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  settings:'<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  search:'<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
  close:'<path d="M18 6 6 18M6 6l12 12"/>',
  collapse:'<path d="m15 18-6-6 6-6"/>',
  expand:'<path d="m9 18 6-6-6-6"/>',
  arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 9h18c0-1-3-2-3-9M10 21h4"/>',
  moon:'<path d="M20.4 14.6a8.6 8.6 0 0 1-11-11 8.7 8.7 0 1 0 11 11Z"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>',
  chevron:'<path d="m6 9 6 6 6-6"/>'
};
function icon(name,size=19){
 const drawing=glyphs[name]||glyphs.home;
 return '<svg class="ea-icon" width="'+size+'" height="'+size+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+drawing+'</svg>';
}
let active='overview',collapsed=false,mobile=false,search='';
let appearance='light';
let reduceEffects=false;
const motionQuery=matchMedia('(prefers-reduced-motion: reduce)');
function applyMotion(){document.documentElement.dataset.reducedMotion=String(reduceEffects||motionQuery.matches);window.EstablishmentMotion.preferenceChanged()}
motionQuery.addEventListener('change',applyMotion);
function applyAppearance(){document.documentElement.dataset.theme=appearance==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):appearance}
function syncTheme(){if(appearance==='system')applyAppearance();}
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{syncTheme();});
// The media-query listener above updates system theme without continuous polling.
const root=document.getElementById('gc-establishment-app');
function navButton(m){return '<button class="ea-nav-item '+(active===m.id?'active':'')+'" data-route="'+m.id+'" title="'+m.label+'" aria-current="'+(active===m.id?'page':'false')+'">'+icon(m.icon)+'<span class="ea-nav-text">'+m.label+'</span></button>'}
function aside(){return '<aside class="ea-sidebar" id="ea-sidebar" aria-label="Navigation de l’établissement"><div class="ea-head"><img class="ea-logo" src="/assets/logo.png" alt="G-Connect"><img class="ea-logo-small" src="/assets/logo_icon.png" alt="G-Connect"><button class="ea-icon-button ea-collapse" id="ea-collapse" aria-label="Réduire ou agrandir le menu" aria-expanded="'+(!collapsed)+'">'+icon('collapse')+'</button></div><label class="ea-search" for="ea-search-input">'+icon('search')+'<input id="ea-search-input" type="search" autocomplete="off" placeholder="Rechercher un module..." aria-label="Rechercher un module"></label><button class="ea-icon-button ea-search-compact" id="ea-search-compact" aria-label="Ouvrir la recherche" title="Rechercher">'+icon('search')+'</button><p class="ea-caption">Administration</p><nav class="ea-nav" id="ea-nav" aria-label="Modules">'+modules.filter(m=>m.id!=='settings').map(navButton).join('')+'</nav><div class="ea-side-bottom"><p class="ea-caption">Compte</p><nav class="ea-nav" aria-label="Compte">'+navButton(modules.find(m=>m.id==='settings'))+'</nav><div class="ea-identity"><div class="ea-avatar">GC</div><div class="ea-identity-copy"><strong>'+safe(live.profile?(live.stats?.institution_name||'Mon établissement'):'Mon établissement')+'</strong><small>'+(live.profile?'Compte connecté':'Prévisualisation non connectée')+'</small></div></div><button type="button" id="ea-signout-nav" class="ea-logout">'+icon('close',16)+'<span>Déconnexion</span></button></div></aside>'}
function topbar(){
 const selected=modules.find(x=>x.id===active);
 const institution=live.stats?.institution_name||'Mon établissement';
 return '<header class="ea-top">'+
  '<div class="ea-top-heading">'+
    '<button id="ea-open-menu" class="ea-icon-button ea-mobile-open" aria-label="Ouvrir la navigation" aria-expanded="'+mobile+'">'+icon('menu')+'</button>'+
    '<img class="ea-mobile-brand" src="/assets/logo.png" alt="G-Connect">'+
    '<div class="ea-trail">G-Connect / Établissement / <strong>'+safe(selected.label)+'</strong></div>'+
  '</div>'+
  '<button type="button" class="ea-search-pill" id="ea-quick-search" aria-label="Rechercher un module">'+icon('search')+'<span>Rechercher un module...</span><kbd>Ctrl K</kbd></button>'+
  '<time class="ea-top-date" id="ea-top-date" aria-label="Date du jour"></time>'+
  '<div class="ea-top-actions">'+
    '<button class="ea-icon-button ea-header-tool" id="ea-theme-toggle" aria-label="Changer de thème" aria-pressed="false" title="Clair / sombre">'+icon('moon')+'</button>'+
    '<div class="ea-top-menu-wrap">'+
      '<button class="ea-icon-button ea-header-tool" id="ea-notification-toggle" aria-label="Ouvrir les notifications" aria-expanded="false" aria-controls="ea-notification-popover" title="Notifications">'+icon('bell')+'</button>'+
      '<section class="ea-top-popover ea-notification-popover" id="ea-notification-popover" aria-label="Notifications" hidden>'+
        '<div class="ea-popover-head"><div><strong>Notifications</strong><small>Votre établissement</small></div></div>'+
        '<div class="ea-notification-empty"><strong>Aucune notification chargée</strong>Les alertes réelles ne sont pas encore raccordées à cette interface.</div>'+
      '</section>'+
    '</div>'+
    '<div class="ea-top-menu-wrap">'+
      '<button class="ea-profile-trigger" id="ea-profile-toggle" aria-label="Ouvrir le menu du compte" aria-expanded="false" aria-controls="ea-profile-popover">'+
        '<span class="ea-top-avatar" aria-hidden="true">GC</span><span class="ea-profile-label">Établissement</span>'+icon('chevron',14)+'</button>'+
      '<section class="ea-top-popover ea-profile-popover" id="ea-profile-popover" aria-label="Compte et préférences" hidden>'+
        '<div class="ea-popover-head"><span class="ea-top-avatar" aria-hidden="true">GC</span><div><strong>'+safe(institution)+'</strong><small>Compte établissement connecté</small></div></div>'+
        '<label class="ea-popover-label" for="ea-theme">Apparence</label>'+
        '<select class="ea-theme" id="ea-theme" aria-label="Apparence"><option value="light">Clair</option><option value="dark">Sombre</option><option value="system">Système</option></select>'+
        '<button class="ea-popover-link" type="button" data-route="settings">Paramètres '+icon('arrow',15)+'</button>'+
        '<button class="ea-popover-link is-danger" type="button" id="ea-signout-menu">Déconnexion '+icon('close',15)+'</button>'+
      '</section>'+
    '</div>'+
  '</div>'+
 '</header>';
}

const preview={promotions:[],events:[],team:[],selectedPlan:'6',profile:null,memberFilter:'all'};
const live={loading:false,error:'',email:'',profile:null,stats:null};
const safe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function labelField(label,name,placeholder,required=true,type='text'){return '<label class="ea-field"><span>'+label+'</span><input name="'+name+'" type="'+type+'" placeholder="'+placeholder+'" maxlength="100" '+(required?'required':'')+'></label>'}
function stateNotice(message='Aucune donnée réelle n’est disponible tant que le backend n’est pas connecté.'){return '<div class="ea-inline-notice" role="note">'+icon('shield',17)+'<span>'+message+'</span></div>'}
function headline(title,subtitle,actions=''){return '<section class="ea-page-intro"><div><p class="ea-eyebrow">Administration · G-Connect</p><h1>'+title+'</h1><p>'+subtitle+'</p></div>'+actions+'</section>'}
function emptyState(title,description){return '<div class="ea-empty-state"><div class="ea-empty-icon">'+icon('layers',23)+'</div><strong>'+title+'</strong><p>'+description+'</p></div>'}
function draftList(type){const items=preview[type];if(!items.length)return emptyState('Aucun brouillon pour le moment','Créez un premier aperçu. Il sera conservé uniquement pendant cette session, sans être envoyé sur un serveur.');return '<div class="ea-draft-list">'+items.map((item,i)=>'<article class="ea-draft"><div class="ea-draft-symbol">'+icon(type==='events'?'calendar':type==='team'?'shield':'layers')+'</div><div><strong>'+safe(item.title)+'</strong><span>'+safe(item.caption)+'</span></div><span class="ea-chip">Brouillon local</span><button type="button" class="ea-icon-button ea-remove" data-remove="'+type+'" data-index="'+i+'" aria-label="Supprimer le brouillon '+safe(item.title)+'">'+icon('close',14)+'</button></article>').join('')+'</div>'}
function intro(){return '<section class="ea-hero ea-hero-refined"><div class="hero-copy"><p class="ea-eyebrow">Portail des établissements</p><h1>Votre campus.<br>Une communauté qui grandit.</h1><p>Promotions, diplômés, événements et équipe administrative : préparez tout au même endroit, avec clarté.</p><div class="ea-actions"><button data-route="promotions" class="ea-button primary">Organiser les promotions '+icon('arrow',15)+'</button><button data-route="events" class="ea-button">Créer une annonce</button></div></div><img class="hero-photo" src="/assets/hero-gconnect.jpg" alt="Un jeune professionnel avec son ordinateur en extérieur" width="800" height="900"></section>'}
function authLocation(connected){
 const expected=connected?'etablissement.html':'etablissement-connexion.html';
 const current=window.location.pathname.split('/').pop();
 if(['etablissement.html','etablissement-connexion.html'].includes(current)&&current!==expected){
  window.history.replaceState(null,'',expected);
 }
}
function clearLocalDrafts(){
 preview.promotions.length=0;preview.events.length=0;preview.team.length=0;
 preview.profile=null;preview.memberFilter='all';preview.selectedPlan='6';
}
function endSession(){
 if(window.GConnectAuth){
  live.profile=null;live.stats=null;live.error='';live.email='';live.loading=false;
  clearLocalDrafts();active='overview';mobile=false;search='';
  window.GConnectAuth.signout(root);
  return;
 }
 window.GConnectEstablishmentApi.disconnect();
 live.profile=null;live.stats=null;live.error='';live.email='';live.loading=false;
 clearLocalDrafts();
 active='overview';mobile=false;search='';
 render();
 document.getElementById('ea-login-email')?.focus({preventScroll:true});
}
function renderLogin(){
 if(window.GConnectAuth){
  window.GConnectAuth.mount(root, async (result)=>{
   // E4: this callback runs only after the server has verified the MFA challenge.
   live.profile=result.profile;live.stats=result.stats;live.error='';live.email='';
   render();
  });
  return;
 }
 authLocation(false);
 document.title='Connexion Établissement · G-Connect';
 root.innerHTML=[
  '<div class="ea-auth-shell">',
   '<main class="ea-auth-main" id="gc-main">',
    '<header class="ea-auth-header"><img src="/assets/logo.png" alt="G-Connect" class="ea-auth-logo">',
     '<span>Portail des établissements</span></header>',
    '<div class="ea-auth-layout">',
     '<section class="ea-auth-story" aria-label="Bienvenue sur G-Connect">',
      '<span class="ea-auth-eyebrow">Votre communauté, votre espace</span>',
      '<h1>Votre établissement, connecté à ses talents.</h1>',
      '<p>Promotions, étudiants, alumni et événements réunis dans un espace pensé pour votre équipe.</p>',
      '<div class="ea-auth-story-image"><img src="/assets/hero-gconnect.jpg" alt="Un professionnel utilisant son ordinateur"></div>',
     '</section>',
     '<section class="ea-auth-card" aria-label="Connexion au compte établissement">',
      '<div class="ea-auth-lock" aria-hidden="true">',icon('shield',22),'</div>',
      '<p class="ea-auth-eyebrow">Accès sécurisé</p>',
      '<h2>Bienvenue sur G-Connect</h2>',
      '<p class="ea-auth-explainer">Connectez-vous avec votre compte administrateur d’établissement.</p>',
      '<form id="ea-login-form" class="ea-auth-form">',
       '<label class="ea-field" for="ea-login-email"><span>Adresse e-mail</span>',
        '<input id="ea-login-email" name="email" type="email" inputmode="email" autocomplete="username" maxlength="254" placeholder="Votre adresse professionnelle" value="',safe(live.email),'" required></label>',
       '<label class="ea-field" for="ea-login-password"><span>Mot de passe</span>',
        '<span class="ea-auth-password"><input id="ea-login-password" name="password" type="password" autocomplete="current-password" required>',
         '<button type="button" id="ea-password-visibility" aria-pressed="false" aria-label="Afficher le mot de passe">Afficher</button></span></label>',
       '<button type="submit" class="ea-button primary ea-auth-submit" ',(live.loading?'disabled':''),'>',
        (live.loading?'Connexion en cours…':'Se connecter'),icon('arrow',18),'</button>',
       (live.error?'<p class="ea-auth-error" role="alert">'+safe(live.error)+'</p>':''),
      '</form>',
      '<p class="ea-auth-help">Besoin d’un accès ? Contactez l’administrateur G-Connect de votre établissement.</p>',
     '</section>',
    '</div>',
    '<footer class="ea-auth-footer">© G-Connect · Espace réservé aux établissements autorisés.</footer>',
   '</main>',
  '</div>'
 ].join('');
 bindConnectionActions();
}
function overviewNotice(){
 return live.profile?'<div class="ea-alert" role="status">Statistiques de '+safe(live.stats?.institution_name||'votre établissement')+' · accès en lecture seule.</div>':'<div class="ea-alert" role="status">Mode prévisualisation : aucun étudiant, alumni ou établissement réel n’est chargé. Les brouillons créés ici ne sont pas enregistrés.</div>';
}
function metricCards(){
 const stats=live.stats;
 const metrics=[
  ['Promotions','layers',stats?.promotions_count],
  ['Étudiants & Alumni','people',stats?.users?.students!=null&&stats?.users?.alumni!=null?stats.users.students+stats.users.alumni:null],
  ['Événements','calendar',stats?.posts?.events]
 ];
 return '<div class="ea-section-line"><h2 class="ea-section-heading">Votre espace en un coup d’œil</h2><span class="ea-soft-label">'+(stats?'Statistiques réelles':'Données à connecter')+'</span></div><section class="ea-grid" aria-label="Indicateurs de l’établissement">'+metrics.map(([name,ico,value])=>'<article class="ea-card ea-metric"><div class="ea-metric-icon">'+icon(ico)+'</div><small>'+name+'</small><strong>'+(Number.isFinite(value)?safe(value):'—')+'</strong><span>'+(stats?'Données autorisées de votre établissement':'En attente des données autorisées')+'</span></article>').join('')+'</section>';
}
function communityChart(){
 const users=live.stats?.users;
 const students=users?.students,alumni=users?.alumni;
 const ready=Number.isFinite(students)&&students>=0&&Number.isFinite(alumni)&&alumni>=0;
 const max=ready?Math.max(students,alumni,1):1;
 const bars=ready?[['Étudiants',students],['Alumni',alumni]].map(([name,value])=>'<div class="ea-chart-col"><span class="ea-chart-value">'+safe(value)+'</span><span class="ea-chart-bar" style="--bar-height:'+Math.max(12,Math.round(120*value/max))+'px"></span><small>'+name+'</small></div>').join(''):'';
 return '<section class="ea-card ea-community-chart" aria-label="Répartition de la communauté">'+
  '<div class="ea-panel-head"><div><p class="ea-overline">Votre communauté</p><h2>Étudiants & Alumni</h2></div><span class="ea-chip">'+(ready?'Données de votre établissement':'Données à connecter')+'</span></div>'+
  (ready?'<div class="ea-chart-plots" role="img" aria-label="Étudiants : '+safe(students)+' ; Alumni : '+safe(alumni)+'">'+bars+'</div>':
    '<div class="ea-chart-placeholder">Le graphique apparaîtra lorsque les effectifs autorisés de votre établissement seront disponibles.</div>')+
 '</section>';
}
function overview(){
 const detail=live.stats?.posts?.total>0
  ?emptyState('Publications disponibles','Le détail des publications sera ajouté lors du raccordement des événements.')
  :emptyState('Pas encore d’activité','Aucune activité à afficher pour le moment.');
 return intro()+overviewNotice()+metricCards()+communityChart()+'<section class="ea-twocol"><article class="ea-card ea-panel"><div class="ea-panel-head"><div><p class="ea-overline">Premiers pas</p><h2>Préparez votre établissement</h2></div><span class="ea-chip">3 étapes</span></div><div class="ea-checklist">'+[['01','Structurer les promotions','Définir filières et années académiques','promotions'],['02','Organiser l’équipe','Préparer les rôles administratifs','team'],['03','Créer un premier événement','Préparer une annonce pour le campus','events']].map(([n,title,desc,to])=>'<button class="ea-step" data-route="'+to+'"><span>'+n+'</span><span><strong>'+title+'</strong><small>'+desc+'</small></span>'+icon('arrow',17)+'</button>').join('')+'</div></article><article class="ea-card ea-panel ea-side-panel"><p class="ea-overline">Activité</p><h2>Fil de votre établissement</h2><p>'+(live.profile?'Le détail des activités sera connecté dans un prochain lot.':'Publications, inscriptions et notifications apparaîtront ici lorsque l’API sera disponible.')+'</p>'+detail+'<div class="ea-panel-footer"><button data-route="members" class="ea-text-button">Explorer les profils '+icon('arrow',15)+'</button></div></article></section><section class="ea-feature-row"><div><strong>G-Connect, pensé pour votre communauté.</strong><p>Les étudiants et alumni continuent d’utiliser leur application mobile. Ici, vous administrez uniquement votre établissement.</p></div><button class="ea-button" data-route="subscription">Découvrir les formules '+icon('arrow',15)+'</button></section>';
}
function promotions(){return headline('Promotions & filières','Structurez votre parcours académique avant la mise en service de votre espace.')+stateNotice()+'<div class="ea-workspace"><article class="ea-card ea-panel"><div class="ea-panel-head"><div><p class="ea-overline">Organisation académique</p><h2>Mes promotions</h2></div><span class="ea-soft-label">Aperçu local</span></div>'+draftList('promotions')+'</article><article class="ea-card ea-panel"><p class="ea-overline">Nouvelle promotion</p><h2>Préparer une promotion</h2><p>Exemple : Informatique · DITI 2026. Aucun enregistrement définitif ne sera effectué.</p><form class="ea-form" data-draft-form="promotions">'+labelField('Filière','track','Ex. Développement informatique')+labelField('Promotion','cohort','Ex. DITI4')+labelField('Année académique','year','Ex. 2026-2027')+'<button class="ea-button primary" type="submit">Ajouter à l’aperçu '+icon('arrow',15)+'</button></form></article></div>'}
function members(){return headline('Étudiants & Alumni','Une vue claire des étudiants actuels et anciens diplômés, avec les autorisations propres à votre établissement.')+stateNotice('Les listes nominatives ne sont jamais simulées. Les accès seront filtrés côté serveur selon l’établissement et les permissions.')+'<div class="ea-card ea-panel"><div class="ea-panel-head"><div><p class="ea-overline">Annuaire institutionnel</p><h2>Explorer la communauté</h2></div><span class="ea-soft-label">Synchronisation requise</span></div><div class="ea-filter-bar"><label class="ea-field ea-filter"><span>Rechercher</span><input type="search" placeholder="Nom, formation ou promotion…" id="ea-members-query" aria-label="Rechercher un étudiant ou alumni" /></label><label class="ea-field ea-filter"><span>Statut</span><select id="ea-members-filter"><option value="all">Tous les profils</option><option value="students">Étudiants</option><option value="alumni">Alumni</option></select></label></div>'+emptyState('Annuaire en attente de connexion','La recherche et les filtres seront activés une fois les profils autorisés fournis par le backend.')+'</div><section class="ea-feature-row"><div><strong>Étudiant aujourd’hui, alumni demain.</strong><p>Un ancien étudiant reste membre de la communauté de son établissement. Sa transition de statut sera pilotée par les règles métier.</p></div></section>'}
function events(){return headline('Événements & annonces','Créez des moments de rencontre, accompagnez vos promotions et animez la vie du campus.')+stateNotice()+'<div class="ea-workspace"><article class="ea-card ea-panel"><div class="ea-panel-head"><div><p class="ea-overline">Calendrier éditorial</p><h2>Annonces préparées</h2></div><span class="ea-soft-label">Non publiées</span></div>'+draftList('events')+'</article><article class="ea-card ea-panel"><p class="ea-overline">Nouvel événement</p><h2>Créer un brouillon</h2><p>Prévisualisez un événement ; aucun message ne sera transmis à l’application mobile.</p><form class="ea-form" data-draft-form="events">'+labelField('Titre','title','Ex. Forum des métiers')+labelField('Date','date','',true,'date')+labelField('Lieu','place','Ex. Amphithéâtre A')+'<button class="ea-button primary" type="submit">Préparer l’événement '+icon('arrow',15)+'</button></form></article></div>'}
function team(){return headline('Équipe administrative','Un espace pour préparer les accès de vos responsables, avec des rôles distincts.')+stateNotice('Aucune invitation n’est envoyée. La création des comptes et les permissions seront contrôlées par le serveur.')+'<div class="ea-workspace"><article class="ea-card ea-panel"><div class="ea-panel-head"><div><p class="ea-overline">Accès collaborateurs</p><h2>Équipe à constituer</h2></div><span class="ea-soft-label">Invitations non envoyées</span></div>'+draftList('team')+'</article><article class="ea-card ea-panel"><p class="ea-overline">Accès futur</p><h2>Préparer une invitation</h2><form class="ea-form" data-draft-form="team">'+labelField('Nom du responsable','name','Ex. Responsable scolarité')+labelField('Adresse professionnelle','email','Ex. equipe@etablissement.sn',true,'email')+'<label class="ea-field"><span>Rôle proposé</span><select name="role"><option value="Gestionnaire de promotions">Gestionnaire de promotions</option><option value="Chargé de communication">Chargé de communication</option><option value="Administrateur établissement">Administrateur établissement</option></select></label><button class="ea-button primary" type="submit">Ajouter à la liste locale '+icon('arrow',15)+'</button></form></article></div><div class="ea-role-grid">'+[['Administrateur établissement','Coordination des équipes et paramètres.'],['Gestionnaire de promotions','Organisation des filières et promotions.'],['Chargé de communication','Préparation d’annonces et d’événements.']].map(([role,desc])=>'<article class="ea-role"><div class="ea-role-icon">'+icon('shield')+'</div><strong>'+role+'</strong><p>'+desc+'</p></article>').join('')+'</div>'}
function subscription(){const plans=[['1','Mensuel','1 mois','Une formule souple pour démarrer.'],['6','Semestriel','6 mois','Un suivi adapté au rythme académique.'],['12','Annuel','12 mois','Une visibilité sur toute l’année.']];return headline('Abonnement & factures','Choisissez une durée en aperçu. Les prix définitifs et les droits sont gérés par G-Connect.')+stateNotice('Aucun abonnement actif n’est détecté : cette interface ne réalise aucun paiement ni activation.')+'<div class="ea-section-line"><h2 class="ea-section-heading">Durées possibles</h2><span class="ea-soft-label">Prix configurés par le superadmin</span></div><div class="ea-plan-grid">'+plans.map(([id,name,duration,desc])=>'<button type="button" class="ea-plan '+(preview.selectedPlan===id?'is-selected':'')+'" data-plan="'+id+'" aria-pressed="'+(preview.selectedPlan===id)+'"><span class="ea-plan-head">'+name+'</span><strong>'+duration+'</strong><p>'+desc+'</p><span class="ea-price-placeholder">Tarif à définir</span><span class="ea-plan-choice">'+(preview.selectedPlan===id?'Sélectionné pour aperçu':'Prévisualiser cette formule')+' '+icon('arrow',15)+'</span></button>').join('')+'</div><section class="ea-twocol"><article class="ea-card ea-panel"><p class="ea-overline">Votre sélection</p><h2>Simulation sans engagement</h2><p>Formule <strong>'+safe(plans.find(p=>p[0]===preview.selectedPlan)[1])+'</strong> choisie pour la présentation. La tarification, la date d’échéance et le paiement seront disponibles après intégration.</p></article><article class="ea-card ea-panel"><p class="ea-overline">Historique de facturation</p><h2>Factures</h2>'+emptyState('Aucune facture','Les factures réelles apparaîtront ici après activation du système d’abonnement.')+'</article></section>'}
function institutionalSettings(){return headline('Paramètres de l’établissement','Personnalisez le profil institutionnel et anticipez les futures préférences de votre espace.')+stateNotice('Les modifications de cette page ne sont pas sauvegardées. Les données officielles seront synchronisées via l’API.')+'<div class="ea-workspace"><article class="ea-card ea-panel"><p class="ea-overline">Identité institutionnelle</p><h2>Informations générales</h2><form class="ea-form" id="ea-profile-form">'+labelField('Nom de l’établissement','name','Ex. Institut de formation')+labelField('Ville','city','Ex. Dakar')+labelField('Contact institutionnel','contact','Ex. contact@ecole.sn',true,'email')+'<button type="submit" class="ea-button primary">Afficher l’aperçu '+icon('arrow',15)+'</button></form></article><article class="ea-card ea-panel"><p class="ea-overline">Aperçu du profil</p><h2>Votre établissement</h2>'+(preview.profile?'<div class="ea-profile-preview"><span class="ea-large-monogram">'+safe(preview.profile.name.charAt(0).toUpperCase())+'</span><strong>'+safe(preview.profile.name)+'</strong><span>'+safe(preview.profile.city)+'</span><small>'+safe(preview.profile.contact)+'</small><span class="ea-chip">Temporaire</span></div>':emptyState('Profil non configuré','Saisissez les informations du formulaire pour voir leur présentation.'))+'</article></div>'}
function settings(){
 const institution=safe(live.stats?.institution_name||'Mon établissement');
 return headline('Paramètres','Une expérience adaptée à votre établissement et à votre équipe.')+
 '<section class="ea-settings-grid" aria-label="Paramètres de l’établissement">'+
   '<article class="panel"><p class="ea-settings-kicker">Votre compte</p><h3>Informations de l’établissement</h3><p class="ea-settings-description">Identité de l’espace connecté.</p>'+
    '<div class="ea-settings-profile"><span class="ea-settings-avatar" aria-hidden="true">GC</span><div><strong>'+institution+'</strong><small>Compte établissement connecté</small></div></div>'+
    '<div class="ea-settings-property"><span>Espace</span><strong>Établissement</strong></div>'+
    '<div class="ea-settings-property"><span>Données consultées</span><strong>Uniquement votre établissement</strong></div>'+
    '<div class="ea-settings-property"><span>Accès</span><strong>Session sécurisée</strong></div></article>'+
   '<article class="panel"><p class="ea-settings-kicker">Personnalisation</p><h3>Apparence et confort</h3><p class="ea-settings-description">Ajustez votre thème et la fluidité de l’interface.</p>'+
    '<div class="ea-theme-options">'+[['light','Clair'],['dark','Sombre'],['system','Système']].map(([id,label])=>'<button class="ea-button '+(appearance===id?'primary':'')+'" data-appearance="'+id+'" aria-pressed="'+(appearance===id)+'">'+label+'</button>').join('')+'</div>'+
    '<div class="ea-settings-toggle-row"><div><strong>Réduire les animations</strong><small>Respecter votre préférence de confort</small></div><label class="ea-switch"><input type="checkbox" id="ea-reduce-motion" aria-label="Réduire les animations" '+(reduceEffects||motionQuery.matches?'checked':'')+' '+(motionQuery.matches?'disabled':'')+'></label></div>'+
    '<div class="ea-settings-toggle-row"><div><strong>Navigation compacte</strong><small>Réduire ou développer le menu latéral</small></div><button type="button" class="ea-button" id="ea-toggle-settings">Adapter le menu '+icon('collapse',15)+'</button></div>'+
    '<p class="ea-settings-footnote">Les préférences visuelles sont locales à la session et ne modifient aucune donnée de l’établissement.</p></article>'+
   '<article class="panel"><p class="ea-settings-kicker">Communications</p><h3>Notifications</h3><p class="ea-settings-description">La configuration des alertes sera activée lorsque le service correspondant sera raccordé.</p>'+
    '<div class="ea-settings-toggle-row"><div><strong>Notifications d’affiliation</strong><small>Demandes et vérifications des profils</small></div><label class="ea-switch"><input type="checkbox" aria-label="Notifications d’affiliation bientôt disponibles" disabled></label></div>'+
    '<div class="ea-settings-toggle-row"><div><strong>Notifications d’événements</strong><small>Annonces et activités de votre communauté</small></div><label class="ea-switch"><input type="checkbox" aria-label="Notifications d’événements bientôt disponibles" disabled></label></div>'+
    '<p class="ea-settings-footnote">Ces options sont affichées à titre de présentation et ne sont pas sauvegardées.</p></article>'+
   '<article class="panel"><p class="ea-settings-kicker">Protection</p><h3>Sécurité et accès</h3><p class="ea-settings-description">Votre authentification et vos autorisations restent administrées par le backend G-Connect.</p>'+
    '<div class="ea-settings-property"><span>Validation des accès</span><strong>Contrôles côté serveur</strong></div>'+
    '<div class="ea-settings-property"><span>Double authentification</span><strong>Selon votre politique de sécurité</strong></div>'+
    '<div class="ea-settings-property"><span>Déconnexion</span><strong>Révocation de session</strong></div>'+
    '<p class="ea-settings-footnote">Aucune opération sensible n’est simulée depuis ce panneau.</p></article>'+
 '</section>'+institutionalSettings();
}
function setAppearance(value){
 if(!['light','dark','system'].includes(value))return;
 const update=()=>{
  appearance=value;
  applyAppearance();
  const select=document.getElementById('ea-theme');
  if(select)select.value=value;
  document.querySelectorAll('[data-appearance]').forEach(b=>{
   const selected=b.dataset.appearance===value;
   b.classList.toggle('primary',selected);
   b.setAttribute('aria-pressed',String(selected));
  });
  const themeButton=document.getElementById('ea-theme-toggle');
  if(themeButton){const dark=document.documentElement.dataset.theme==='dark';themeButton.innerHTML=icon(dark?'sun':'moon');themeButton.setAttribute('aria-pressed',String(dark));themeButton.setAttribute('aria-label',dark?'Activer le thème clair':'Activer le thème sombre')}
 };
 // The visual-only theme transition follows the Superadmin variant and the
 // supplied mobile reference; unsupported browsers fall back immediately.
 if(document.startViewTransition&&document.documentElement.dataset.reducedMotion!=='true'&&appearance!==value){
  document.startViewTransition(update);
 }else{
  update();
 }
}
function detail(m){switch(m.id){case'promotions':return promotions();case'members':return members();case'events':return events();case'team':return team();case'subscription':return subscription();case'settings':return settings();default:return headline(m.title,m.description)}}
function bindConnectionActions(){
 const login=document.getElementById('ea-login-form');
 if(login)login.addEventListener('submit',async event=>{
  event.preventDefault();
  if(live.loading||!login.reportValidity())return;
  const email=login.elements.email.value.trim();
  const password=login.elements.password.value;
  live.email=email;live.loading=true;live.error='';
  render();
  try{
   const result=await window.GConnectEstablishmentApi.connect(email,password);
   live.profile=result.profile;live.stats=result.stats;
   live.email='';
  }catch(error){
   live.profile=null;live.stats=null;
   live.error=error?.message||'Connexion impossible. Veuillez réessayer.';
  }finally{
   live.loading=false;render();
  }
 });
 const toggle=document.getElementById('ea-password-visibility');
 if(toggle)toggle.onclick=()=>{
  const input=document.getElementById('ea-login-password');
  const revealed=input.type==='password';
  input.type=revealed?'text':'password';
  toggle.textContent=revealed?'Masquer':'Afficher';
  toggle.setAttribute('aria-pressed',String(revealed));
  toggle.setAttribute('aria-label',revealed?'Masquer le mot de passe':'Afficher le mot de passe');
  input.focus();
 };
 const signout=document.getElementById('ea-signout-nav');
 if(signout)signout.onclick=endSession;
 const menuSignout=document.getElementById('ea-signout-menu');
 if(menuSignout)menuSignout.onclick=endSession;
}
function bindPreviewActions(){
 document.querySelectorAll('[data-appearance]').forEach(b=>b.onclick=()=>setAppearance(b.dataset.appearance));
 const motion=document.getElementById('ea-reduce-motion');if(motion)motion.onchange=()=>{reduceEffects=motion.checked;applyMotion()};
 const toggle=document.getElementById('ea-toggle-settings');if(toggle)toggle.onclick=()=>{if(matchMedia('(max-width:900px)').matches){mobile=true;updateNavigation();document.getElementById('ea-collapse').focus()}else{collapsed=!collapsed;updateNavigation()}};

 document.querySelectorAll('[data-plan]').forEach(b=>b.addEventListener('click',()=>{preview.selectedPlan=b.dataset.plan;render()}));
 document.querySelectorAll('[data-remove]').forEach(b=>b.addEventListener('click',()=>{const type=b.dataset.remove;const index=Number(b.dataset.index);if(['promotions','events','team'].includes(type)&&Number.isInteger(index)&&index>=0&&index<preview[type].length){preview[type].splice(index,1);render()}}));
 document.querySelectorAll('[data-draft-form]').forEach(form=>form.addEventListener('submit',e=>{
  e.preventDefault();if(!form.reportValidity())return;
  const d=Object.fromEntries(new FormData(form).entries());const type=form.dataset.draftForm;
  let item;
  if(type==='promotions')item={title:d.cohort.trim(),caption:d.track.trim()+' · '+d.year.trim()};
  else if(type==='events')item={title:d.title.trim(),caption:d.date+' · '+d.place.trim()};
  else if(type==='team')item={title:d.name.trim(),caption:d.role+' · '+d.email.trim()};
  else return;
  if(!item.title||!item.caption.trim())return;
  preview[type].unshift(item);render();const panel=document.querySelector('.ea-draft-list');if(panel)panel.scrollIntoView({block:'nearest',behavior:document.documentElement.dataset.reducedMotion==='true'?'instant':'smooth'});
 }));
 const profile=document.getElementById('ea-profile-form');
 if(profile&&preview.profile)Object.entries(preview.profile).forEach(([key,value])=>{profile.elements[key].value=value});
 if(profile)profile.addEventListener('submit',e=>{e.preventDefault();if(!profile.reportValidity())return;const d=Object.fromEntries(new FormData(profile).entries());preview.profile={name:d.name.trim(),city:d.city.trim(),contact:d.contact.trim()};if(!preview.profile.name)return;render()});
 const filter=document.getElementById('ea-members-filter');
 if(filter)filter.onchange=e=>{preview.memberFilter=e.target.value;const status=document.querySelector('.ea-empty-state p');if(status)status.textContent='Filtre « '+filter.options[filter.selectedIndex].text+' » prêt pour la future API. Aucun profil réel n’est chargé.'};
}
function render(){
 if(!window.GConnectEstablishmentApi.isConnected()||!live.profile||!live.stats){
  renderLogin();return;
 }
 authLocation(true);
 const m=modules.find(x=>x.id===active);
 if(!root.querySelector('.ea-shell')){
  root.innerHTML='<div class="ambient-bg" aria-hidden="true"><div class="ambient-glow"></div><div class="ambient-glow"></div><div class="ambient-glow"></div><div class="particles"></div></div><div class="ea-shell"><div class="ea-backdrop" id="ea-backdrop"></div>'+aside()+'<main class="ea-main" id="gc-main" tabindex="-1"></main></div>';
  window.EstablishmentMotion.init(root);
 }
 root.querySelector('.ea-main').innerHTML=topbar()+(active==='overview'?overview():detail(m));
 root.querySelectorAll('.ea-nav-item').forEach(button=>{
  const selected=button.dataset.route===active;
  button.classList.toggle('active',selected);
  button.setAttribute('aria-current',selected?'page':'false');
 });
 document.title=m.label+' · Administration Établissement · G-Connect';
 bind();bindPreviewActions();bindConnectionActions();filterNav();window.EstablishmentMotion.afterRender();
}
function filterNav(){const q=search.toLocaleLowerCase('fr').trim();document.querySelectorAll('.ea-nav-item').forEach(b=>{b.hidden=!!q&&!b.textContent.toLocaleLowerCase('fr').includes(q)});const input=document.getElementById('ea-search-input');if(input)input.value=search}
function navigate(id){if(!window.GConnectEstablishmentApi.isConnected()||!modules.some(m=>m.id===id))return;active=id;mobile=false;search='';render();window.scrollTo(0,0);document.getElementById('gc-main').focus({preventScroll:true})}
function updateNavigation(){
 const shell=document.querySelector('.ea-shell');
 if(!shell)return;
 shell.classList.toggle('is-collapsed',collapsed);
 shell.classList.toggle('is-mobile-open',mobile);
 document.getElementById('ea-collapse').setAttribute('aria-expanded',String(!collapsed));
 document.getElementById('ea-open-menu').setAttribute('aria-expanded',String(mobile));
 const sidebar=document.getElementById('ea-sidebar');
 sidebar.inert=matchMedia('(max-width:900px)').matches&&!mobile;
 document.getElementById('gc-main').inert=mobile;
 document.body.classList.toggle('ea-menu-open',mobile);
 document.getElementById('ea-collapse').setAttribute('aria-label',matchMedia('(max-width:900px)').matches?'Fermer la navigation':collapsed?'Déployer la navigation':'Réduire la navigation');
}
function bind(){
 document.querySelectorAll('[data-route]').forEach(b=>b.onclick=()=>navigate(b.dataset.route));
 document.getElementById('ea-collapse').onclick=()=>{if(matchMedia('(max-width:900px)').matches){mobile=false;updateNavigation();document.getElementById('ea-open-menu').focus()}else{collapsed=!collapsed}updateNavigation()};
 document.getElementById('ea-search-compact').onclick=()=>{collapsed=false;updateNavigation();document.getElementById('ea-search-input').focus()};
 document.getElementById('ea-open-menu').onclick=()=>{mobile=true;updateNavigation();document.getElementById('ea-collapse').focus()};
 document.getElementById('ea-backdrop').onclick=()=>{mobile=false;updateNavigation();document.getElementById('ea-open-menu').focus()};
 document.getElementById('ea-search-input').oninput=e=>{search=e.target.value;filterNav()};
 const themeSelect=document.getElementById('ea-theme');themeSelect.value=appearance;
 themeSelect.onchange=e=>setAppearance(e.target.value);
 const topDate=document.getElementById('ea-top-date');
 if(topDate){const now=new Date();topDate.dateTime=now.toISOString().slice(0,10);topDate.textContent=new Intl.DateTimeFormat('fr-SN',{weekday:'short',day:'numeric',month:'short',year:'numeric'}).format(now)}
 const themeButton=document.getElementById('ea-theme-toggle');
 const syncThemeButton=()=>{const dark=document.documentElement.dataset.theme==='dark';themeButton.setAttribute('aria-pressed',String(dark));themeButton.setAttribute('aria-label',dark?'Activer le thème clair':'Activer le thème sombre');themeButton.innerHTML=icon(dark?'sun':'moon')};
 syncThemeButton();
 themeButton.onclick=()=>setAppearance(document.documentElement.dataset.theme==='dark'?'light':'dark');
 const closePopovers=()=>{for(const [trigger,panel] of [['ea-notification-toggle','ea-notification-popover'],['ea-profile-toggle','ea-profile-popover']]){document.getElementById(panel).hidden=true;document.getElementById(trigger).setAttribute('aria-expanded','false')}};
 for(const [trigger,panel] of [['ea-notification-toggle','ea-notification-popover'],['ea-profile-toggle','ea-profile-popover']]){
  document.getElementById(trigger).onclick=()=>{const box=document.getElementById(panel);const opening=box.hidden;closePopovers();if(opening){box.hidden=false;document.getElementById(trigger).setAttribute('aria-expanded','true')}};
 }
 document.getElementById('ea-quick-search').onclick=()=>{closePopovers();if(matchMedia('(max-width:900px)').matches){mobile=true;updateNavigation()}else if(collapsed){collapsed=false;updateNavigation()}document.getElementById('ea-search-input').focus()};
 updateNavigation();
}
matchMedia('(max-width:900px)').addEventListener('change',()=>{mobile=false;updateNavigation()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&mobile){mobile=false;updateNavigation();document.getElementById('ea-open-menu').focus()}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'&&live.profile){e.preventDefault();document.getElementById('ea-quick-search')?.click()}});
document.addEventListener('click',e=>{if(!e.target.closest('.ea-top-menu-wrap'))document.querySelectorAll('.ea-top-popover').forEach(pop=>{pop.hidden=true;const trigger=pop.id==='ea-profile-popover'?'ea-profile-toggle':'ea-notification-toggle';document.getElementById(trigger)?.setAttribute('aria-expanded','false')})});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){document.querySelectorAll('.ea-top-popover').forEach(pop=>{pop.hidden=true;const trigger=pop.id==='ea-profile-popover'?'ea-profile-toggle':'ea-notification-toggle';document.getElementById(trigger)?.setAttribute('aria-expanded','false')})}});
document.addEventListener('keydown',e=>{
 if(e.key!=='Tab'||!mobile)return;
 const controls=[...document.querySelectorAll('.ea-sidebar button,.ea-sidebar input')].filter(el=>!el.hidden&&el.getClientRects().length);
 const first=controls[0],last=controls[controls.length-1];
 if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
 else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
});
window.addEventListener('pagehide',()=>{
 window.GConnectEstablishmentApi.disconnect();
 live.profile=null;live.stats=null;
 root.replaceChildren();
});
window.addEventListener('pageshow',event=>{if(event.persisted)render();});
applyMotion();
applyAppearance();
render();
