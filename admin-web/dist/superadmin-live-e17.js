'use strict';
/* E17 — Connected Superadmin workspace. Session credentials remain inside
   GConnectEstablishmentApi; no tokens, demo records or browser persistence. */
(function () {
  const api = window.GConnectEstablishmentApi;
  const NAV = [
    ['overview', 'Vue d’ensemble', 'layout', 'Pilotage'],
    ['establishments', 'Établissements', 'school', 'Pilotage'],
    ['companies', 'Entreprises', 'building', 'Pilotage'],
    ['users', 'Utilisateurs', 'users', 'Pilotage'],
    ['invitations', 'Invitations', 'mail', 'Accès'],
    ['subscriptions', 'Abonnements', 'credit', 'Finances'],
    ['billing', 'Facturation', 'receipt', 'Finances'],
    ['audit', 'Journal d’audit', 'activity', 'Sécurité'],
    ['security', 'Sessions et sécurité', 'shield', 'Sécurité'],
    ['settings', 'Paramètres', 'settings', 'Sécurité']
  ];
  const ICONS = {
    layout:'M3 3h8v8H3z M13 3h8v5h-8z M13 10h8v11h-8z M3 13h8v8H3z',
    school:'M3 10l9-6 9 6 M5 10v10h14V10 M9 20v-6h6v6',
    building:'M5 21V4h14v17 M9 8h2 M15 8h1 M9 12h2 M15 12h1 M9 16h2 M15 16h1',
    users:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75',
    mail:'M3 5h18v14H3z M3 6l9 7 9-7',
    credit:'M2 6h20v12H2z M2 10h20 M6 15h4',
    receipt:'M5 3h14v18l-3-2-4 2-4-2-3 2z M9 9h6 M9 13h6',
    activity:'M3 12h4l3-7 4 14 3-7h4',
    shield:'M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6z M9 12l2 2 4-4',
    settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M4.9 4.9L7 7 M17 17l2.1 2.1 M19.1 4.9L17 7 M7 17l-2.1 2.1',
    bell:'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4',
    sun:'M12 3v2 M12 19v2 M3 12h2 M19 12h2 M5.6 5.6l1.4 1.4 M17 17l1.4 1.4 M18.4 5.6L17 7 M7 17l-1.4 1.4 M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8',
    moon:'M20 14.2A8 8 0 0 1 9.8 4a8 8 0 1 0 10.2 10.2z',
    menu:'M4 7h16 M4 12h16 M4 17h16',
    chevron:'M9 18l6-6-6-6',
    arrow:'M5 12h14 M13 6l6 6-6 6',
    refresh:'M20 6v5h-5 M4 18v-5h5 M5 10a7 7 0 0 1 12-4l3 5 M4 13l3 5a7 7 0 0 0 12-4',
    check:'M5 12l5 5L20 7',
    logout:'M9 21H4V3h5 M16 17l5-5-5-5 M21 12H9',
    search:'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14 M16 16l5 5',
    close:'M5 5l14 14 M19 5L5 19'
  };
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon = (name, size = 18) => '<svg width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' + (ICONS[name] || ICONS.layout) + '"/></svg>';
  let host = null, callbacks = null, route = 'overview', invitations = [], loaded = false;
  let loading = false, saving = false, error = '', notice = '', search = '', navOpen = false, compact = false, profileOpen = false, serial = 0;
  const sections = {
    overview:['Vue d’ensemble','Suivez les accès professionnels et les opérations de G-Connect.'],
    establishments:['Établissements','Supervision des organisations universitaires.'],
    companies:['Entreprises','Suivi des partenaires et de leurs accès.'],
    users:['Utilisateurs','Gestion transverse des identités et autorisations.'],
    invitations:['Invitations','Invitez et suivez les responsables d’établissement.'],
    subscriptions:['Abonnements','Préparez les accès commerciaux de la plateforme.'],
    billing:['Facturation','Suivi des paiements et justificatifs.'],
    audit:['Journal d’audit','Traçabilité des opérations sensibles.'],
    security:['Sessions et sécurité','Protection de l’espace de supervision.'],
    settings:['Paramètres','Préférences de votre console Superadmin.']
  };

  function validSession() {
    return Boolean(api && api.isConnected() && api.getCurrent()?.profile?.role === 'superAdmin');
  }
  function profile() { return api.getCurrent()?.profile || {}; }
  function theme() { return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'; }
  function pendingInvitation(inv) {
    const date = Date.parse(inv.expires_at || '');
    return !inv.accepted && !inv.revoked && Number.isFinite(date) && date > Date.now();
  }
  function countPending() { return invitations.filter(pendingInvitation).length; }
  function status(inv) {
    if (inv.accepted) return ['Activée','success'];
    if (inv.revoked) return ['Révoquée','neutral'];
    const date = Date.parse(inv.expires_at || '');
    return Number.isFinite(date) && date <= Date.now() ? ['Expirée','warning'] : ['En attente','pending'];
  }
  function navMarkup() {
    let lastGroup = '';
    return NAV.map(row => {
      let group = '';
      if (lastGroup !== row[3]) { lastGroup = row[3]; group = '<span class="sa-nav-group">' + esc(lastGroup) + '</span>'; }
      return group + '<button type="button" class="sa-nav-item' + (route === row[0] ? ' active' : '') + '" data-route="' + row[0] + '"' + (route === row[0] ? ' aria-current="page"' : '') + ' title="' + esc(row[1]) + '">' + icon(row[2]) + '<span>' + esc(row[1]) + '</span>' + (route === row[0] ? '<i></i>' : '') + '</button>';
    }).join('');
  }
  const head = (name, description, extra = '') => '<header class="sa-page-heading"><div><span class="sa-eyebrow">ADMINISTRATION G-CONNECT</span><h1 id="sa-page-title" tabindex="-1">' + esc(name) + '</h1><p>' + esc(description) + '</p></div>' + extra + '</header>';
  const badge = (label, color) => '<span class="sa-badge sa-badge-' + color + '">' + esc(label) + '</span>';
  const card = (body, cls = '') => '<section class="sa-card ' + cls + '">' + body + '</section>';
  const metric = (name, value, description, glyph) => '<article class="sa-metric"><span class="sa-metric-icon">' + icon(glyph) + '</span><p>' + esc(name) + '</p><strong>' + esc(value) + '</strong><small>' + esc(description) + '</small></article>';
  function inviteItems() {
    if (!loaded) return '<div class="sa-empty">Chargement des invitations…</div>';
    const filtered = invitations.filter(inv => (String(inv.institution_name || '') + ' ' + String(inv.email || '')).toLowerCase().includes(search.toLowerCase()));
    if (!filtered.length) return '<div class="sa-empty">Aucune invitation à afficher pour cette recherche.</div>';
    return '<ul class="sa-invite-list">' + filtered.map(inv => {
      const [label, color] = status(inv);
      const id = Number(inv.id);
      return '<li><span class="sa-list-avatar">' + icon('school', 19) + '</span><div class="sa-list-text"><strong>' + esc(inv.institution_name || ('Établissement #' + (inv.institution_id || '—'))) + '</strong><span>' + esc(inv.email || 'Adresse indisponible') + '</span></div>' + badge(label, color) + (pendingInvitation(inv) && Number.isSafeInteger(id) && id > 0 ? '<button class="sa-text-action" type="button" data-revoke="' + id + '"' + (saving ? ' disabled' : '') + '>Révoquer</button>' : '') + '</li>';
    }).join('') + '</ul>';
  }
  function overview() {
    return head('Vue globale de G-Connect','Un pilotage clair de vos accès et invitations, basé sur les données disponibles.') +
      '<div class="sa-welcome">' +
      '<div><span class="sa-welcome-tag">ESPACE DE SUPERVISION</span><h2>Bienvenue dans votre console Superadmin.</h2><p>Les accès sont protégés par une authentification renforcée. Retrouvez ici les opérations réellement disponibles.</p><button class="sa-white-button" type="button" data-route="invitations">Gérer les invitations ' + icon('arrow', 17) + '</button></div>' +
      '<div class="sa-welcome-symbol" aria-hidden="true">G<span>•</span></div></div>' +
      '<div class="sa-metrics">' +
      metric('Invitations en attente',loaded && !error ? String(countPending()) : '—',error ? 'Données indisponibles' : loaded ? 'Données du backend' : 'Chargement…','mail') +
      metric('Compte sécurisé','MFA','Session vérifiée par Django','shield') +
      metric('Établissements actifs','—','API de répertoire à connecter','school') +
      metric('Abonnements actifs','—','Module de facturation absent','credit') + '</div>' +
      '<div class="sa-two-col">' +
      card('<div class="sa-card-heading"><div><span class="sa-eyebrow">ACTIVITÉ</span><h2>Invitations récentes</h2></div><button type="button" class="sa-text-action" data-route="invitations">Tout voir ' + icon('chevron', 15) + '</button></div>' + (loaded ? inviteItems() : '<div class="sa-empty">Chargement…</div>'),'sa-list-card') +
      card('<span class="sa-eyebrow">ÉTAT DU SERVICE</span><h2>Déploiement progressif</h2><div class="sa-check-row">' + icon('check') + '<span>Connexion et MFA reliées au backend</span></div><div class="sa-check-row">' + icon('check') + '<span>Invitations administrateur disponibles</span></div><div class="sa-wait-row">○ <span>Répertoire d’organisations à raccorder</span></div><div class="sa-wait-row">○ <span>Abonnements et paiements à développer côté serveur</span></div><p class="sa-footnote">Aucun chiffre commercial fictif n’est affiché.</p>','sa-state-card') + '</div>';
  }
  function invitationsPage() {
    return head('Invitations professionnelles','Créez et suivez de véritables invitations via le backend Django.',
      '<button type="button" class="sa-secondary-button" data-refresh ' + (loading ? 'disabled' : '') + '>' + icon('refresh', 16) + ' Actualiser</button>') +
      '<div class="sa-two-col sa-invitations-grid">' +
      card('<span class="sa-eyebrow">NOUVEL ACCÈS</span><h2>Inviter un responsable</h2><p class="sa-muted">Renseignez l’identifiant numérique d’un établissement existant et son adresse professionnelle.</p>' +
      '<form id="sa-invite-form" class="sa-form"><label for="sa-institution">Identifiant de l’établissement</label><input id="sa-institution" name="institution_id" type="number" inputmode="numeric" min="1" step="1" placeholder="Ex. : 12" required>' +
      '<label for="sa-invite-email">E-mail du responsable</label><input id="sa-invite-email" name="email" type="email" autocomplete="email" maxlength="254" placeholder="responsable@universite.sn" required>' +
      '<p class="sa-warn">Le backend d’abonnement n’est pas encore raccordé : aucun paiement n’est vérifié par cette interface. Réservez les invitations aux opérations autorisées.</p>' +
      '<button type="submit" class="sa-primary-button" ' + (saving ? 'disabled' : '') + '>' + (saving ? 'Envoi en cours…' : 'Envoyer l’invitation') + ' ' + icon('arrow', 16) + '</button></form>','sa-invite-create') +
      card('<div class="sa-card-heading"><div><span class="sa-eyebrow">SUIVI</span><h2>Invitations enregistrées</h2></div>' + (loaded ? badge(invitations.length+' au total','neutral') : '') + '</div>' +
      '<label class="sa-search-label" for="sa-invite-search">' + icon('search', 17) + '<input id="sa-invite-search" placeholder="Rechercher un établissement ou e-mail" autocomplete="off" value="' + esc(search) + '"></label>' +
      (error ? '<p class="sa-inline-error" role="alert">'+esc(error)+'</p>' : inviteItems()), 'sa-list-card') + '</div>';
  }
  function notReady(title, description, note) {
    return head(title,description) + card('<div class="sa-empty-feature"><div class="sa-feature-icon">' + icon('shield',28) + '</div><h2>Module en préparation</h2><p>' + esc(note) + '</p><span class="sa-badge sa-badge-neutral">Aucune donnée simulée</span></div>','sa-feature');
  }
  function subscriptionsPage() {
    return head('Abonnements','Les formules commerciales seront reliées aux droits d’accès des organisations.') +
      '<div class="sa-plan-grid">' + [
        ['1 mois','Activation mensuelle'],['6 mois','Engagement semestriel'],['12 mois','Engagement annuel'],['Sur mesure','Contrat personnalisé']
      ].map(plan => card('<span class="sa-eyebrow">FORMULE ENVISAGÉE</span><h2>' + plan[0] + '</h2><p>' + plan[1] + '</p><span class="sa-badge sa-badge-neutral">Non commercialisée</span>','sa-plan')).join('') + '</div>' +
      card('<h2>Condition d’activation à implémenter</h2><p>La validation d’un paiement doit précéder l’envoi d’une invitation et l’activation des droits. Le backend actuel ne fournit pas encore les API de contrat, paiement et suspension : aucune facturation n’est exécutée ici.</p>','sa-callout');
  }
  function settingsPage() {
    return head('Paramètres','Personnalisez l’affichage de votre espace de travail.') +
      card('<span class="sa-eyebrow">MON COMPTE</span><h2>Administrateur général</h2><div class="sa-property"><span>Compte connecté</span><strong>' + esc(profile().email) + '</strong></div><div class="sa-property"><span>Autorisation</span><strong>Superadmin</strong></div><div class="sa-property"><span>Sécurité</span><strong>MFA vérifiée</strong></div>','sa-settings-card') +
      card('<span class="sa-eyebrow">APPARENCE</span><h2>Thème de la console</h2><p>Ces préférences restent locales au navigateur et ne modifient pas votre profil serveur.</p><button type="button" class="sa-secondary-button" data-action="theme">' + icon(theme()==='dark'?'sun':'moon') + ' Passer en mode ' + (theme()==='dark'?'clair':'sombre') + '</button>','sa-settings-card');
  }
  function content() {
    if(route==='overview')return overview();
    if(route==='invitations')return invitationsPage();
    if(route==='subscriptions')return subscriptionsPage();
    if(route==='settings')return settingsPage();
    const data=sections[route] || sections.overview;
    const notes={
      establishments:'Un point de lecture des établissements autorisés sera disponible dès qu’une API de répertoire protégée sera validée.',
      companies:'Les entreprises et leurs contrats ne disposent pas encore d’API de gestion dans ce périmètre.',
      users:'Les droits et identités devront être exposés par des endpoints Superadmin avec contrôles de périmètre.',
      billing:'Aucune transaction ni facture réelle ne peut encore être consultée dans cette interface.',
      audit:'Les événements d’audit doivent provenir exclusivement d’un journal backend autorisé.',
      security:'L’inventaire des sessions et les opérations de sécurité nécessitent des endpoints dédiés.'
    };
    return notReady(data[0],data[1],notes[route] || 'Ce module sera disponible après intégration du backend.');
  }
  function render() {
    if (!host || !callbacks) return;
    if (!validSession()) { callbacks.expired?.(); return; }
    const title=sections[route]?.[0] || 'Superadmin';
    const headerDate = new Intl.DateTimeFormat('fr-FR',{day:'numeric',month:'long',year:'numeric'}).format(new Date());
    host.innerHTML =
      '<div class="sa-live' + (compact?' sa-compact':'') + (navOpen?' sa-menu-open':'') + '">' +
        '<div class="sa-mobile-shade" data-action="close-menu"></div>' +
        '<aside class="sa-sidebar" id="sa-sidebar" aria-label="Navigation Superadmin">' +
          '<div class="sa-brand"><span class="sa-brand-mark"><img src="/assets/logo_icon.png" alt="" width="28" height="28"></span><span class="sa-brand-copy"><strong>G-Connect</strong><small>SUPERADMIN</small></span></div>' +
          '<nav class="sa-navigation" aria-label="Rubriques">' + navMarkup() + '</nav>' +
          '<div class="sa-sidebar-bottom"><div class="sa-sidebar-person"><span class="sa-avatar">SA</span><span><strong>Administration</strong><small>Accès sécurisé</small></span></div><button type="button" class="sa-sidebar-collapse" data-action="compact">Adapter le menu ' + icon('chevron',15) + '</button></div>' +
        '</aside>' +
        '<div class="sa-main-wrap"><header class="sa-topbar"><div class="sa-topbar-start"><button class="sa-icon-button sa-mobile-menu" type="button" data-action="menu" aria-label="Ouvrir la navigation" aria-expanded="'+navOpen+'">' + icon('menu') + '</button><div class="sa-breadcrumb">G-Connect <span>/</span> <strong>' + esc(title) + '</strong></div></div>' +
          '<div class="sa-top-actions"><span class="sa-date">' + esc(headerDate) + '</span><button type="button" class="sa-icon-button" data-action="theme" aria-label="Changer le thème">' + icon(theme()==='dark'?'sun':'moon') + '</button><button type="button" class="sa-icon-button" data-action="notifications" aria-label="Notifications">' + icon('bell') + '</button><button type="button" class="sa-profile-button" data-action="profile" aria-expanded="' + profileOpen + '"><span class="sa-avatar">SA</span><span>Superadmin</span>' + icon('chevron',14) + '</button></div>' +
          (profileOpen ? '<div class="sa-profile-popover"><strong>' + esc(profile().email) + '</strong><span>Superadmin · MFA vérifiée</span><button type="button" data-route="settings">' + icon('settings',16) + ' Paramètres</button><button type="button" data-action="logout">' + icon('logout',16) + ' Se déconnecter</button></div>' : '') +
        '</header><main id="gc-main" class="sa-content">' +
          (notice?'<div class="sa-notice" role="status">' + esc(notice) + '<button type="button" data-action="dismiss" aria-label="Fermer le message">' + icon('close',16) + '</button></div>':'') +
          content() +
        '</main><footer class="sa-footer">G-Connect · Espace Superadmin sécurisé <span>Accès après vérification MFA</span></footer></div>' +
      '</div>';
    bind();
  }
  function navigate(next) {
    if(!sections[next])return;
    route=next;navOpen=false;profileOpen=false;notice='';render();
    host?.querySelector('#sa-page-title')?.focus({preventScroll:true});
  }
  function bind() {
    host.querySelectorAll('[data-route]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.route)));
    host.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>{
      switch(b.dataset.action){
        case 'menu':navOpen=!navOpen;render();break;
        case 'close-menu':navOpen=false;render();break;
        case 'compact':compact=!compact;render();break;
        case 'profile':profileOpen=!profileOpen;render();break;
        case 'theme':{
          const next=theme()==='dark'?'light':'dark';
          document.documentElement.dataset.theme=next;
          try{localStorage.setItem('gconnect_auth_theme',next);}catch{}
          render();break;
        }
        case 'notifications':notice='Le centre de notifications nécessite une API backend dédiée.';render();break;
        case 'logout':callbacks.logout?.();break;
        case 'dismiss':notice='';render();break;
      }
    }));
    host.querySelector('[data-refresh]')?.addEventListener('click',()=>loadInvitations());
    host.querySelector('#sa-invite-search')?.addEventListener('input',e=>{
      const input=e.target; const pos=input.selectionStart;
      search=input.value;render();
      const next=host.querySelector('#sa-invite-search');
      next?.focus();if(pos!==null)next?.setSelectionRange(pos,pos);
    });
    host.querySelector('#sa-invite-form')?.addEventListener('submit',event=>{
      event.preventDefault();
      const f=event.currentTarget;
      if(saving||!f.reportValidity())return;
      const values=new FormData(f);
      const id=Number(values.get('institution_id'));
      const email=String(values.get('email')||'').trim();
      if(!Number.isSafeInteger(id)||id<=0){notice='Choisissez un identifiant numérique valide.';render();return;}
      sendInvitation(id,email);
    });
    host.querySelectorAll('[data-revoke]').forEach(b=>b.addEventListener('click',()=>{
      const id=Number(b.dataset.revoke);
      if(!Number.isSafeInteger(id)||id<=0||saving)return;
      if(!confirm('Révoquer cette invitation ? Cette action est définitive.'))return;
      revokeInvitation(id);
    }));
  }
  async function loadInvitations() {
    if(!host||!callbacks)return;
    const id=++serial;loading=true;error='';render();
    try {
      const response=await api.listInvitations();
      if(id!==serial||!host)return;
      invitations=Array.isArray(response)?response:Array.isArray(response?.results)?response.results:[];
      loaded=true;
    }catch(e){
      if(id!==serial||!host)return;
      if(/session.*expir/i.test(e.message||'')){callbacks.expired?.();return;}
      error='Les invitations ne sont pas disponibles : '+(e.message||'réessayez plus tard.');
      loaded=true;invitations=[];
    }finally{if(id===serial&&host){loading=false;render();}}
  }
  async function sendInvitation(institutionId,email) {
    if(saving)return;
    saving=true;notice='';render();
    try{
      await api.sendInvitation(email,institutionId);
      if(!host)return;
      notice='Invitation envoyée. Le responsable recevra son lien personnel.';
      await loadInvitations();
      route='invitations';
    }catch(e){
      if(!host)return;
      if(/session.*expir/i.test(e.message||'')){callbacks.expired?.();return;}
      notice='Invitation non envoyée : '+(e.message||'erreur serveur.');
    }finally{saving=false;if(host)render();}
  }
  async function revokeInvitation(id) {
    if(saving)return;
    saving=true;render();
    try{
      await api.revokeInvitation(id);
      if(!host)return;
      notice='Invitation révoquée.';
      await loadInvitations();
    }catch(e){
      if(!host)return;
      if(/session.*expir/i.test(e.message||'')){callbacks.expired?.();return;}
      notice='Révocation impossible : '+(e.message||'erreur serveur.');
    }finally{saving=false;if(host)render();}
  }
  function unmount(){serial++;callbacks=null;host=null;invitations=[];loaded=false;loading=false;saving=false;notice='';error='';search='';}
  function mount(target, options) {
    if(!target || !validSession()) throw new Error('Session Superadmin vérifiée requise.');
    unmount();
    host=target;
    callbacks={logout:options?.onLogout,expired:options?.onExpired};
    route='overview';navOpen=false;profileOpen=false;compact=false;
    render();loadInvitations();
  }
  window.GConnectSuperadminConsole=Object.freeze({mount,unmount});
})();