'use strict';
/* E34 · The people behind G-Connect. Authenticated Superadmin read-only directory. */
(function () {
  window.GConnectUsersE34 = function ({ api, safe, icon, go, render, isVisible, notify }) {
    const state = {
      search: '', role: 'all', status: 'all', page: 1, page_size: 12,
      loading: false, loaded: false, error: '', payload: null,
    };
    let seq = 0, searchTimer = null, searchFocused = false;
    let securitySeq=0,securityContext=null;
    const esc = value => safe(value ?? '');
    const num = value => Number(value || 0).toLocaleString('fr-FR');
    const data = () => state.payload || { summary: {}, results: [], count: 0, page: 1, pages: 1 };
    const roleNames = Object.freeze({
      student: 'Étudiant', alumni: 'Alumni', enterprise: 'Entreprise',
      etablissement: 'Administration établissement', superAdmin: 'Superadmin',
    });
    const roles = [
      ['all', 'Tous les rôles'], ['student', roleNames.student], ['alumni', roleNames.alumni],
      ['enterprise', roleNames.enterprise], ['etablissement', roleNames.etablissement],
      ['superAdmin', roleNames.superAdmin],
    ];
    const statuses = [['all', 'Tous les statuts'], ['active', 'Actifs'],
      ['pending', 'En attente'], ['banned', 'Bloqués']];
    const colors = {
      student: 'student', alumni: 'alumni', enterprise: 'enterprise',
      etablissement: 'school', superAdmin: 'admin',
    };
    function roleLabel(value) { return roleNames[value] || 'Rôle non identifié'; }
    function badgeRole(value) {
      return '<span class="e34-role e34-role--' + (colors[value] || 'other') + '">' + esc(roleLabel(value)) + '</span>';
    }
    function statusOf(user) {
      return user.is_banned ? ['Bloqué', 'banned'] :
        user.is_active ? ['Actif', 'active'] : ['En attente', 'pending'];
    }
    function badgeStatus(user) {
      const [label, css] = statusOf(user);
      return '<span class="e34-state e34-state--' + css + '">' + esc(label) + '</span>';
    }
    function initials(user) {
      const raw = String(user.display_name || user.username || 'U').trim();
      const parts = raw.split(/\s+/).filter(Boolean);
      return (parts.length > 1 ? parts.slice(0, 2).map(p => p[0]).join('') :
        (parts[0] || 'U').slice(0, 2)).toUpperCase();
    }
    function dateFr(iso) {
      if (!iso) return 'Non renseignée';
      const date = new Date(iso);
      return Number.isNaN(date.getTime()) ? 'Non renseignée' :
        date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
    }
    function avatar(user) {
      return '<span class="e34-avatar e34-avatar--' + (colors[user.role] || 'other') +
        '" aria-hidden="true">' + esc(initials(user)) + '</span>';
    }
    function metric(iconName, value, caption, note, variant) {
      return `<article class="e34-stat e34-stat--${variant}">
        <span class="e34-stat-icon">${icon(iconName)}</span>
        <strong>${state.loaded ? num(value) : '—'}</strong>
        <span>${esc(caption)}</span><small>${esc(note)}</small>
      </article>`;
    }
    function row(user) {
      const id = Number(user.id);
      return `<article class="e34-person">
        <div class="e34-person-identity">${avatar(user)}
          <div class="e34-person-name"><strong>${esc(user.display_name || user.username)}</strong>
          <small>${esc(user.email || '')}</small></div>
        </div>
        <div class="e34-person-role">${badgeRole(user.role)}<span class="e34-mobile-status">${badgeStatus(user)}</span>
          <small>${esc(user.association || user.location || 'Aucun rattachement renseigné')}</small>
        </div>
        <div class="e34-person-state">${badgeStatus(user)}</div>
        <span class="e34-person-date">${esc(dateFr(user.joined_at))}</span>
        <button class="e34-person-detail" data-e34-action="detail" data-e34-id="${id}" type="button"
          aria-label="Voir la fiche de ${esc(user.display_name || user.username)}">
          Fiche <span aria-hidden="true">↗</span></button>
      </article>`;
    }
    function empty() {
      const filtered = state.search || state.role !== 'all' || state.status !== 'all';
      return `<div class="e34-empty"><span class="e34-empty-icon">${icon('users')}</span>
        <h3>${filtered ? 'Aucun profil trouvé' : 'Aucun utilisateur enregistré'}</h3>
        <p>${filtered ? 'Ajustez votre recherche ou modifiez les filtres pour afficher d’autres comptes.' :
          'Les comptes créés sur G-Connect apparaîtront automatiquement dans ce répertoire.'}</p>
        ${filtered ? '<button type="button" data-e34-action="reset">Effacer les filtres</button>' : ''}
      </div>`;
    }
    function options(items, selected) {
      return items.map(([value, label]) =>
        `<option value="${esc(value)}"${value === selected ? ' selected' : ''}>${esc(label)}</option>`
      ).join('');
    }
    function page() {
      const payload = data();
      const summary = payload.summary || {};
      const professionals = (summary.enterprises || 0) +
        (summary.institution_admins || 0) + (summary.superadmins || 0);
      const members = (summary.students || 0) + (summary.alumni || 0);
      const count = Number(payload.count || 0);
      const first = count ? (payload.page - 1) * state.page_size + 1 : 0;
      const last = Math.min(count, (payload.page || 1) * state.page_size);
      const content = !state.loaded
        ? '<div class="e34-loading" role="status">Chargement des comptes depuis le backend…</div>'
        : state.error
          ? `<div class="e34-error" role="alert"><h3>Impossible de charger les profils.</h3>
              <p>${esc(state.error)}</p>
              <button data-e34-action="retry" type="button">Réessayer</button></div>`
          : (payload.results || []).length ? payload.results.map(row).join('') : empty();

      return `<div class="e34-page">
        <section class="e34-hero">
          <div class="e34-hero-copy">
            <span class="e34-eyebrow">COMMUNAUTÉ · IDENTITÉS G-CONNECT</span>
            <h1>Les personnes qui font<br><em>vivre notre réseau.</em></h1>
            <p>Étudiants, alumni et responsables professionnels. Retrouvez les comptes,
              leurs accès et leurs rattachements à partir des données de G-Connect.</p>
            <div class="e34-hero-actions">
              <button type="button" class="e34-primary" data-e34-action="refresh">Actualiser les comptes ↻</button>
              <span class="e34-hero-privacy">${icon('shield')} Visibilité réservée au Superadmin</span>
            </div>
          </div>
          <div class="e34-identity-art" aria-hidden="true">
            <span class="e34-art-halo"></span><span class="e34-art-ring e34-art-ring--a"></span>
            <span class="e34-art-ring e34-art-ring--b"></span>
            <span class="e34-art-core">${icon('users')}</span>
            <span class="e34-art-avatar e34-art-avatar--one">A</span>
            <span class="e34-art-avatar e34-art-avatar--two">G</span>
            <span class="e34-art-avatar e34-art-avatar--three">M</span>
            <span class="e34-art-avatar e34-art-avatar--four">S</span>
            <span class="e34-art-footer">UNE COMMUNAUTÉ · PLUSIEURS PARCOURS</span>
          </div>
        </section>

        <section class="e34-overview">
          <div class="e34-section-title"><div><span class="e34-kicker">VUE D’ENSEMBLE</span>
            <h2>La communauté en chiffres</h2></div>
            <span class="e34-live">${state.loading ? 'Synchronisation…' : 'Source : backend sécurisé'}</span></div>
          <div class="e34-stat-grid">
            ${metric('users', summary.total, 'Comptes enregistrés', 'Tous les profils G-Connect', 'all')}
            ${metric('check', summary.active, 'Comptes actifs', 'Non bloqués et autorisés', 'active')}
            ${metric('school', members, 'Étudiants & alumni', 'Comptes de la communauté', 'community')}
            ${metric('shield', professionals, 'Accès professionnels', 'Entreprises, établissements, Superadmin', 'pro')}
          </div>
          <div class="e34-context">
            <div class="e34-role-breakdown"><span>RÉPARTITION DES COMPTES</span>
              <div>
              ${[['student', summary.students],['alumni', summary.alumni],
                ['enterprise', summary.enterprises],['etablissement', summary.institution_admins],
                ['superAdmin', summary.superadmins]].map(([role, amount]) =>
                `<span class="e34-breakdown-tag"><i class="e34-spot e34-spot--${colors[role]}"></i>${esc(roleLabel(role))}
                   <b>${state.loaded ? num(amount) : '—'}</b></span>`).join('')}
              </div></div>
            <div class="e34-alert-summary"><span>${icon('clock')} À examiner</span>
              <strong>${state.loaded ? num(summary.pending) : '—'}</strong><small>en attente</small>
              <strong>${state.loaded ? num(summary.banned) : '—'}</strong><small>bloqués</small></div>
          </div>
        </section>

        <section class="e34-directory">
          <div class="e34-section-title"><div><span class="e34-kicker">ANNUAIRE DES COMPTES</span>
            <h2>Explorer les utilisateurs</h2>
            <p>Recherchez, filtrez et ouvrez une fiche. Les modifications sensibles restent dans les outils d’administration dédiés.</p>
          </div><span class="e34-result-count">${state.loaded ? num(count) : '—'} résultat(s)</span></div>
          <div class="e34-toolbar">
            <label class="e34-search">${icon('users')}
              <input id="e34-search" type="search" autocomplete="off" data-e34-search
                value="${esc(state.search)}" placeholder="Nom, e-mail, identifiant ou ville…"
                aria-label="Rechercher un utilisateur"></label>
            <label class="e34-select">Type de compte
              <select data-e34-filter="role" aria-label="Filtrer par rôle">${options(roles, state.role)}</select></label>
            <label class="e34-select">Statut
              <select data-e34-filter="status" aria-label="Filtrer par statut">${options(statuses, state.status)}</select></label>
            <button type="button" class="e34-reset" data-e34-action="reset" title="Effacer les filtres"
              aria-label="Effacer les filtres">↺</button>
          </div>
          <div class="e34-table" aria-busy="${state.loading}">
            <div class="e34-table-heading"><span>UTILISATEUR</span><span>RÔLE & RATTACHEMENT</span>
              <span>ACCÈS</span><span>INSCRIPTION</span><span>FICHE</span></div>
            <div class="e34-table-rows">${content}</div>
            <div class="e34-pagination"><span>Affichage ${state.loaded ? num(first) + ' à ' + num(last) + ' sur ' + num(count) : 'en cours…'}</span>
              <div><button data-e34-action="prev" type="button" ${state.page <= 1 ? 'disabled' : ''}>‹ Précédent</button>
              <span>Page ${num(payload.page || state.page)} / ${num(payload.pages || 1)}</span>
              <button data-e34-action="next" type="button"
                ${state.page >= (payload.pages || 1) ? 'disabled' : ''}>Suivant ›</button></div>
            </div>
          </div>
        </section>
        <dialog class="e34-dialog" id="e34-profile-dialog" aria-labelledby="e34-dialog-title">
          <div id="e34-dialog-content"></div>
        </dialog>
      </div>`;
    }
    function detail(id){
  const profile = (data().results || []).find(item => Number(item.id) === id);
  if (!profile) return;
  const dialog = document.getElementById('e34-profile-dialog');
  if (!dialog) return;
  const filled = text => esc(text || 'Non renseigné');
  securityContext = {profile, details:null, pendingAction:null, busy:false};
  const generation = ++securitySeq;
  dialog.querySelector('#e34-dialog-content').innerHTML =
    `<div class="e34-dialog-header">
      <div class="e34-dialog-identity">${avatar(profile)}
        <div><span class="e34-kicker">FICHE UTILISATEUR</span><h2 id="e34-dialog-title">
          ${esc(profile.display_name || profile.username)}</h2>
          <small>${esc(profile.email || '')}</small></div></div>
      <button type="button" data-e34-action="close" aria-label="Fermer la fiche" class="e34-close">×</button></div>
      <div class="e34-dialog-body">
        <div class="e34-dialog-badges">${badgeRole(profile.role)} ${badgeStatus(profile)}</div>
        <div class="e34-dialog-columns">
          <section><h3>Identité & rattachement</h3><dl>
            <dt>Identifiant</dt><dd>${filled(profile.username)}</dd>
            <dt>Adresse e-mail</dt><dd>${filled(profile.email)}</dd>
            <dt>Localisation</dt><dd>${filled(profile.location)}</dd>
            <dt>Organisation / établissement</dt><dd>${filled(profile.association)}</dd>
          </dl></section>
          <section><h3>Historique du compte</h3><dl>
            <dt>Créé le</dt><dd>${esc(dateFr(profile.joined_at))}</dd>
            <dt>Dernière connexion</dt><dd>${esc(profile.last_login_at ? dateFr(profile.last_login_at) : 'Non renseignée')}</dd>
            <dt>État d’accès</dt><dd>${esc(statusOf(profile)[0])}</dd>
          </dl><p class="e34-disclaimer">Consultation uniquement des informations de profil.
            Aucune donnée MFA, pièce privée ou mot de passe n’est disponible.</p></section>
        </div>
        <section class="e35-security-panel" id="e35-security-panel" aria-live="polite">
          <p class="e35-loading">Vérification des accès et de l’historique…</p>
        </section>
      </div>`;
  dialog.showModal();
  if(typeof api.adminUserSecurity !== 'function'){
    const panel=document.getElementById('e35-security-panel');
    if(panel)panel.innerHTML='<div class="e35-security-error" role="alert">Le module de sécurité n’a pas été chargé. Rechargez entièrement cet onglet (Ctrl + Maj + R) pour synchroniser les fichiers. Aucune intervention n’est possible dans cet état.</div>';
    return;
  }
  Promise.resolve().then(()=>api.adminUserSecurity(id)).then(info=>{
    if(generation!==securitySeq || !securityContext || securityContext.profile.id !== id)return;
    if(!info || !Array.isArray(info.eligible_actions) || !Array.isArray(info.history))
      throw Error('Réponse de sécurité invalide.');
    securityContext.details=info;
    renderSecurity();
  }).catch(error=>{
    if(generation!==securitySeq)return;
    const panel=document.getElementById('e35-security-panel');
    if(panel)panel.innerHTML=`<div class="e35-security-error" role="alert">Gestion des accès indisponible :
      ${esc(error?.message||'Erreur réseau')}. Les actions sont désactivées.</div>`;
  });
}
    function renderSecurity(){
  const panel=document.getElementById('e35-security-panel');
  const details=securityContext?.details;
  if(!panel||!details)return;
  securityContext.pendingAction=null;
  const allowed=new Set(details.eligible_actions||[]);
  const history=details.history||[];
  const auditList=history.length? history.map(item=>`
    <li><span class="e35-audit-event">${esc(item.label||item.action)}</span>
    <small>${esc(dateFr(item.created_at))} · ${esc(item.actor||'Administration')}</small>
    ${item.reason?`<p>Motif : ${esc(item.reason)}</p>`:''}</li>`).join(''):
    '<li class="e35-audit-empty">Aucune intervention de sécurité enregistrée pour ce compte.</li>';
  panel.innerHTML=`<div class="e35-security-head">
    <div><span class="e34-kicker">SÉCURITÉ DU COMPTE</span><h3>Accès et interventions</h3>
    <p>Les actions sont réservées aux Superadmins et conservées dans le journal d’audit.</p></div>
    <span class="e35-live-sessions">Sessions web actives : <strong>${num(details.live_web_sessions)}</strong></span></div>
    ${details.is_banned?`<p class="e35-ban-reason">Blocage en vigueur : ${esc(details.banned_reason||'Motif non renseigné')}
       ${details.banned_at?' · '+esc(dateFr(details.banned_at)):''}</p>`:''}
    <div class="e35-security-actions">
      ${allowed.has('ban')?'<button class="e35-btn e35-btn--danger" data-e34-action="security-prompt" data-e34-security="ban" type="button">Bloquer ce compte</button>':''}
      ${allowed.has('unban')?'<button class="e35-btn e35-btn--success" data-e34-action="security-prompt" data-e34-security="unban" type="button">Lever le blocage</button>':''}
      ${allowed.has('revoke_sessions')?'<button class="e35-btn e35-btn--neutral" data-e34-action="security-prompt" data-e34-security="revoke_sessions" type="button">Déconnecter les appareils</button>':''}
      ${!allowed.size?'<span class="e35-protected">Compte Superadmin protégé : aucune intervention possible depuis cette page.</span>':''}
    </div>
    <div class="e35-history"><h4>Historique des interventions</h4>
      <ol>${auditList}</ol></div>`;
}
    function confirmSecurity(action){
  const allowed=securityContext?.details?.eligible_actions||[];
  if(!allowed.includes(action)||securityContext.busy)return;
  securityContext.pendingAction=action;
  const panel=document.getElementById('e35-security-panel');
  if(!panel)return;
  const labels={
    ban:'Bloquer le compte et révoquer ses sessions',
    unban:'Lever le blocage du compte',
    revoke_sessions:'Déconnecter les appareils de ce compte',
  };
  panel.innerHTML=`<div class="e35-confirm">
    <span class="e34-kicker">INTERVENTION SENSIBLE</span>
    <h3>${esc(labels[action]||'Intervention')}</h3>
    <p>${action==='unban'
      ?'Le compte retrouvera son état d’activation précédent. Aucune nouvelle session ne sera créée.'
      :'Les sessions web et mobiles existantes seront invalidées. Le compte devra se reconnecter.'}</p>
    <label for="e35-reason">Motif de l’intervention <span>(10 à 255 caractères, obligatoire)</span></label>
    <textarea id="e35-reason" maxlength="255" minlength="10" rows="3"
      placeholder="Précisez le contexte et la justification de cette décision…"></textarea>
    <p class="e35-validation" id="e35-validation" role="alert"></p>
    <div class="e35-confirm-actions">
      <button class="e35-btn e35-btn--neutral" type="button" data-e34-action="security-cancel">Annuler</button>
      <button class="e35-btn ${action==='ban'?'e35-btn--danger':'e35-btn--primary'}"
       type="button" data-e34-action="security-save">${esc(labels[action]||'Confirmer')}</button>
    </div>
    <small>Une trace horodatée avec votre identité et ce motif sera conservée.</small>
  </div>`;
  panel.querySelector('textarea')?.focus();
}
    async function executeSecurity(button){
  const ctx=securityContext,action=ctx?.pendingAction;
  if(!ctx||!action||ctx.busy||!ctx.details?.eligible_actions?.includes(action))return;
  const textarea=document.getElementById('e35-reason');
  const message=document.getElementById('e35-validation');
  const reason=(textarea?.value||'').trim();
  if(reason.length<10||reason.length>255){
    if(message)message.textContent='Précisez un motif de 10 à 255 caractères.';
    textarea?.focus();
    return;
  }
  ctx.busy=true;
  if(button)button.disabled=true;
  if(message)message.textContent='Enregistrement sécurisé en cours…';
  try{
    const result=await api.adminUserSecurityAction(ctx.profile.id,action,reason);
    if(!result||result.user_id!==ctx.profile.id||result.action!==action)
      throw Error('Confirmation serveur invalide. Vérifiez le journal avant de réessayer.');
    ++securitySeq;
    securityContext=null;
    document.getElementById('e34-profile-dialog')?.close();
    notify?.(action==='ban'?'Compte bloqué et sessions révoquées.':
      action==='unban'?'Blocage levé.':'Sessions web et mobiles révoquées.');
    await load();
  }catch(error){
    if(message)message.textContent=error?.message||'Action non effectuée.';
  }finally{
    ctx.busy=false;
    if(button)button.disabled=false;
  }
}
    async function load() {
      const current = ++seq;
      state.loading = true;
      state.error = '';
      try {
        const response = await api.adminUserDirectory({
          search: state.search, role: state.role, status: state.status,
          page: state.page, page_size: state.page_size,
        });
        if (current !== seq) return;
        if (!Array.isArray(response?.results) || !response?.summary)
          throw Error('Format de données utilisateurs inattendu.');
        state.payload = response;
        state.loaded = true;
      } catch (error) {
        if (current !== seq) return;
        state.error = error.message || 'Service momentanément indisponible.';
        state.loaded = true;
      } finally {
        if (current === seq) {
          state.loading = false;
          if (isVisible()) {
            render();
            if (searchFocused) {
              const input = document.getElementById('e34-search');
              input?.focus();
              input?.setSelectionRange?.(input.value.length, input.value.length);
            }
          }
        }
      }
    }
    function ensure() { if (!state.loaded && !state.loading) void load(); }
    function action(element) {
      switch (element.dataset.e34Action) {
        case 'detail': return detail(Number(element.dataset.e34Id));
        case 'close': ++securitySeq; securityContext=null;
          return document.getElementById('e34-profile-dialog')?.close();
        case 'security-prompt': return confirmSecurity(element.dataset.e34Security);
        case 'security-cancel': return renderSecurity();
        case 'security-save': return void executeSecurity(element);
        case 'refresh': case 'retry': return void load();
        case 'reset':
          clearTimeout(searchTimer);
          state.search = ''; state.role = 'all'; state.status = 'all';
          state.page = 1; searchFocused = false; return void load();
        case 'prev':
          if (state.page > 1) { state.page--; searchFocused = false; void load(); } return;
        case 'next':
          if (state.page < (state.payload?.pages || 1)) { state.page++; searchFocused = false; void load(); } return;
      }
    }
    function onFilter(element) {
      const key = element.dataset.e34Filter;
      if (!['role', 'status'].includes(key)) return;
      if (key === 'role' && !roles.some(([value]) => value === element.value)) return;
      if (key === 'status' && !statuses.some(([value]) => value === element.value)) return;
      state[key] = element.value; state.page = 1; searchFocused = false; void load();
    }
    function onSearch(element) {
      clearTimeout(searchTimer);
      state.search = element.value; state.page = 1; searchFocused = true;
      searchTimer = setTimeout(() => void load(), 320);
    }
    return Object.freeze({ page, ensure, action, onFilter, onSearch });
  };
})();
