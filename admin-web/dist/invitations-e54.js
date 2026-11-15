'use strict';
/* E54.2: Real professional invitations, scoped by Django and the existing MFA WebToken. */
(function () {
  window.GConnectInvitationsE54 = function ({api, safe, intro, panel, render, role, isVisible}) {
    const admin = role === 'superAdmin';
    const enterprise = role === 'enterprise';
    const state = {loaded:false, loading:false, busy:false, error:'', notice:'',
      schools:[], owners:[], invitations:[], members:[], membership:null};
    let dialog = null;
    const array = value => Array.isArray(value) ? value : [];
    const pending = item => !item.accepted && !item.revoked && Date.parse(item.expires_at || '') > Date.now();
    const status = item => item.accepted ? 'Acceptée' : item.revoked ? 'Révoquée' :
      (Date.parse(item.expires_at || '') <= Date.now() ? 'Expirée' : 'En attente');
    const format = value => {
      const date = new Date(value || '');
      return Number.isFinite(date.valueOf()) ? date.toLocaleDateString('fr-FR', {day:'2-digit',month:'short',year:'numeric'}) : '—';
    };
    const goodId = id => Number.isSafeInteger(Number(id)) && Number(id) > 0;
    const alert = () => (state.notice ? '<div class="e54-message" role="status">'+safe(state.notice)+'</div>' : '') +
      (state.error ? '<div class="e54-message e54-error" role="alert"><span>'+safe(state.error)+'</span><button type="button" class="e54-small" data-e54-refresh>Réessayer</button></div>' : '');
    const loading = () => !state.loaded && state.loading ? '<div class="e54-placeholder" role="status">Synchronisation des invitations…</div>' : '';
    const empty = text => '<div class="e54-empty">'+safe(text)+'</div>';
    const badge = inv => '<span class="e54-status '+(pending(inv)?'e54-pending':inv.accepted?'e54-accepted':'e54-ended')+'">'+safe(status(inv))+'</span>';
    const row = (inv, group, index) => '<tr><td><strong>'+safe(inv.company_name || inv.institution_name || 'Organisation')+'</strong><small>'+safe(inv.kind === 'recruiter'?'Recruteur':inv.kind==='owner'?'Responsable':'Établissement')+'</small></td><td>'+safe(inv.email || '—')+'</td><td>'+format(inv.expires_at)+'</td><td>'+badge(inv)+'</td><td><button class="e54-small" type="button" data-e54-detail="'+group+':'+index+'">Détails</button></td></tr>';
    const table = (list, group) => list.length
      ? '<div class="table-scroll"><table class="table e54-table"><thead><tr><th>Organisation</th><th>Adresse e-mail</th><th>Expiration</th><th>Statut</th><th>Voir</th></tr></thead><tbody>'+
        list.map((inv,i)=>row(inv,group,i)).join('')+'</tbody></table></div>'
      : empty('Aucune invitation enregistrée.');
    const metric = (label, count) => '<div class="e54-metric"><strong>'+safe(String(count))+'</strong><span>'+safe(label)+'</span></div>';
    const metrics = list => {
      const count = value => state.loaded && !state.error ? value : '—';
      return '<div class="e54-metrics">'+metric('Invitations',count(list.length))+
        metric('En attente',count(list.filter(pending).length))+metric('Acceptées',count(list.filter(i=>i.accepted).length))+
        metric('Clôturées',count(list.filter(i=>!pending(i)&&!i.accepted).length))+'</div>';
    };
    const field = (name, label, type, placeholder, max, extra='') =>
      '<label class="e54-field"><span>'+safe(label)+'</span><input name="'+name+'" type="'+type+
      '" '+extra+' maxlength="'+max+'" placeholder="'+safe(placeholder)+'" required></label>';
    // Page-specific compositions inspired by the E20/E33 hero + orbit artwork.
    // The established E19 shell, navigation, modal and E38 pages remain untouched.
    const e54Svg = kind => {
      if(kind==='school') return '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="m2 10 10-6 10 6-10 6L2 10Z"/><path d="M6 12.5v5c3 3 9 3 12 0v-5M22 10v7"/></svg>';
      if(kind==='building')return '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="12" height="18" rx="2"/><path d="M8 7h4M8 11h4M8 15h4M16 9h4v12H2"/></svg>';
      if(kind==='shield')return '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2 9 4v6c0 6-4 9-9 10-5-1-9-4-9-10V6l9-4Z"/><path d="m8.5 12 2.4 2.5 4.6-5"/></svg>';
      return '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3"/><path d="M3 20v-3c0-3 3-5 6-5s6 2 6 5v3M17 9h5M19.5 6.5v5"/></svg>';
    };
    const orbit = () =>
      '<div class="e54-orbit" aria-hidden="true"><div class="e54-orbit-ring e54-orbit-ring-outer"></div>'+
      '<div class="e54-orbit-ring e54-orbit-ring-inner"></div>'+
      '<div class="e54-orbit-core">'+e54Svg('shield')+'<span>G</span></div>'+
      '<div class="e54-orbit-node e54-node-school">'+e54Svg('school')+'</div>'+
      '<div class="e54-orbit-node e54-node-business">'+e54Svg('building')+'</div>'+
      '<div class="e54-orbit-node e54-node-people">'+e54Svg('team')+'</div>'+
      '<span class="e54-orbit-glow e54-glow-one"></span><span class="e54-orbit-glow e54-glow-two"></span></div>';
    // E55 visual alignment: the header follows the borderless finance E37 layout.
    // The illustrations, palette and access workflows remain specific to Invitations.
    const stage=(theme,kicker,title,description,chips) =>
      '<header class="e54-stage e54-stage-'+theme+'" aria-label="Présentation des accès">'+
      '<div class="e54-stage-copy"><div class="e54-stage-kicker"><span class="e54-live-dot"></span>'+safe(kicker)+'</div>'+
      '<h1>'+title+'</h1><p>'+safe(description)+'</p>'+
      '<div class="e54-stage-chips" aria-label="Garanties de sécurité">'+
      chips.map(chip=>'<span>'+safe(chip)+'</span>').join('')+'</div></div>'+
      '<div class="e54-stage-art">'+orbit()+'</div></header>';
    const journey = () => '<div class="e54-journey" aria-label="Parcours de sécurisation">'+
      '<div><span>01</span><strong>Inviter</strong><small>Un e-mail personnel</small></div>'+
      '<i aria-hidden="true"></i><div><span>02</span><strong>Activer</strong><small>Compte vérifié</small></div>'+
      '<i aria-hidden="true"></i><div><span>03</span><strong>Sécuriser</strong><small>Connexion MFA</small></div></div>';
    const accountCard = (kind,num,heading,subtitle,fields,submitText) =>
      '<div class="e54-workflow-card e54-workflow-'+kind+'">'+
      '<div class="e54-workflow-heading"><span class="e54-workflow-icon">'+e54Svg(kind)+'</span>'+
      '<div class="e54-workflow-title"><span class="e54-workflow-step">PARCOURS '+num+'</span><h3>'+safe(heading)+'</h3><p>'+safe(subtitle)+'</p></div>'+
      '<span class="e54-workflow-ornament" aria-hidden="true">'+num+'</span></div>'+
      '<form class="e54-form" data-e54-form="'+(kind==='school'?'school':'owner')+'">'+fields+
      '<div class="e54-form-actions"><span class="e54-form-note">'+e54Svg('shield')+
      '<span>Envoi sécurisé<br><small>Validation par e-mail</small></span></span>'+
      '<button class="e54-primary" type="submit" '+(state.busy?'disabled':'')+'>'+safe(submitText)+' <span aria-hidden="true">↗</span></button></div></form>'+
      '<div class="e54-workflow-foot">'+e54Svg('shield')+'<span>Activation par lien unique et double authentification</span></div></div>';
    function adminPage() {
      const all=state.schools.concat(state.owners);
      return stage('admin','GESTION DES ACCÈS · G-CONNECT',
          'Invitations <em>professionnelles</em>',
          'Accompagnez les établissements et les entreprises dans un parcours d’activation sécurisé, sans perdre le contrôle des accès.',
          ['Responsables vérifiés','Liens individuels','MFA obligatoire'])
        +journey()+alert()+loading()+metrics(all)
        +'<div class="e54-section-title"><div><span>INVITER UN RESPONSABLE</span><h2>Deux univers, deux parcours.</h2>'+
        '<p>Choisissez le type d’organisation pour ouvrir l’accès correspondant.</p></div></div>'
        +'<section class="e54-grid e54-invite-grid" aria-label="Créer une invitation">'
        +accountCard('school','01','Espace Établissement','Invitez le responsable d’un établissement déjà référencé.',
          field('institution_id','Identifiant de l’établissement','number','Ex. : 12',10,'min="1" step="1"')+
          field('email','E-mail du responsable','email','responsable@campus.sn',254,'autocomplete="email"'),
          'Envoyer l’invitation')
        +accountCard('building','02','Espace Entreprise','Créez une invitation pour un nouveau partenaire.',
          field('company_name','Nom de l’entreprise','text','Ex. : Horizon Technologies',255)+
          field('sector','Secteur d’activité','text','Ex. : Technologie',100)+
          field('email','E-mail du responsable','email','direction@entreprise.sn',254,'autocomplete="email"'),
          'Inviter cette entreprise')
        +'</section>'
        +'<div class="e54-heading"><div><span class="e54-section-kicker">TRAÇABILITÉ</span><h2>Invitations et accès</h2>'+
        '<p class="e54-heading-sub">Historique distinct pour chaque type d’organisation.</p></div>'+
        '<button class="e54-small" type="button" data-e54-refresh '+(state.loading?'disabled':'')+'>Actualiser ↻</button></div>'
        +'<section class="e54-grid e54-history-grid">'
        +'<div class="e54-history-panel e54-history-school">'+panel('Responsables Établissement',String(state.schools.length)+' invitation(s)',table(state.schools,'school'))+'</div>'+
         '<div class="e54-history-panel e54-history-building">'+panel('Responsables Entreprise',String(state.owners.length)+' invitation(s)',table(state.owners,'owner'))+'</div></section>';
    }
    function teamPage() {
      const membership=state.membership;
      const owner=membership?.membership==='owner';
      const company=membership?.company?.name || 'votre entreprise';
      const members=state.members.map(m=>'<div class="e54-person"><span class="e54-avatar" aria-hidden="true">'+safe((m.name||m.email||'?').slice(0,1).toUpperCase())+'</span><div><strong>'+safe(m.name||m.email)+'</strong><small>'+safe(m.email||'')+'</small></div><span class="e54-status '+(m.active?'e54-accepted':'e54-ended')+'">'+(m.active?'Actif':'Révoqué')+'</span>'+(m.active?'<button type="button" class="e54-small" data-e54-member="'+Number(m.id)+'">Gérer</button>':'')+'</div>').join('');
      return stage('team','ÉQUIPE · G-CONNECT',
          'Équipe <em>& accès</em>',
          'Gérez les collaborateurs de '+company+' dans un espace professionnel réservé à votre entreprise.',
          ['Équipe privée','Accès par rôle','Sessions révocables'])
        +alert()+loading()
        +(!membership ? empty('Vérification des droits en cours ou indisponible.') : !owner ?
          '<div class="e54-team-readonly"><span class="e54-workflow-icon">'+e54Svg('shield')+'</span><div><h3>Votre accès Recruteur</h3><p>Vous disposez d’un accès opérationnel aux offres et candidatures de votre entreprise. Les invitations et révocations sont réservées à son responsable.</p></div></div>' :
          metrics(state.invitations)
          +'<div class="e54-section-title"><div><span>COLLABORATEURS</span><h2>Construisez votre équipe.</h2>'+
          '<p>Invitez, suivez et pilotez les accès des recruteurs.</p></div></div>'
          +'<section class="e54-grid e54-team-grid">'
          +'<div class="e54-workflow-card e54-workflow-recruiter"><div class="e54-workflow-heading"><span class="e54-workflow-icon">'+e54Svg('team')+'</span>'+
            '<div><span class="e54-workflow-step">NOUVEL ACCÈS</span><h3>Inviter un recruteur</h3><p>Un lien personnel valable 48 heures</p></div></div>'+
            '<form class="e54-form" data-e54-form="recruiter">'+
            field('email','Adresse e-mail professionnelle','email','recruteur@entreprise.sn',254,'autocomplete="email"')+
            '<button class="e54-primary" type="submit" '+(state.busy?'disabled':'')+'>Envoyer une invitation <span aria-hidden="true">↗</span></button></form>'+
            '<div class="e54-workflow-foot">'+e54Svg('shield')+'<span>Accès personnel avec MFA obligatoire</span></div></div>'
           +'<div class="e54-team-members">'+panel('Membres de l’équipe','Comptes de '+safe(company),members || empty('Aucun collaborateur enregistré.'))+'</div>'
           +'</section>'
           +'<div class="e54-heading"><div><span class="e54-section-kicker">INVITATIONS</span><h2>Suivi des recruteurs</h2></div>'+
           '<button type="button" class="e54-small" data-e54-refresh>Actualiser ↻</button></div>'
           +'<div class="e54-history-panel e54-history-recruiter">'+panel('Historique des invitations',String(state.invitations.length)+' invitation(s)',table(state.invitations,'recruiter'))+'</div>');
    }
    // Reveal lower sections as they enter the viewport. No hidden content when
    // IntersectionObserver is unavailable or the user prefers reduced motion.
    const motionObserver = typeof window.IntersectionObserver === 'function'
      ? new window.IntersectionObserver(entries => {
          for(const entry of entries){
            if(!entry.isIntersecting) continue;
            entry.target.classList.add('e54-visible');
            motionObserver.unobserve(entry.target);
          }
        }, {threshold:0.08,rootMargin:'0px 0px -18px 0px'})
      : null;
    function scheduleMotion(){
      if(!motionObserver || typeof window.requestAnimationFrame !== 'function' ||
         window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ||
         document.documentElement?.dataset.motion==='off')return;
      window.requestAnimationFrame(() => {
        const root=document.querySelector('.e54-stage');
        if(!root)return;
        const container=root.parentElement;
        for(const target of container.querySelectorAll(
          '.e54-journey,.e54-metrics,.e54-section-title,.e54-workflow-card,.e54-heading,.e54-history-panel,.e54-team-members,.e54-team-readonly')){
          const rect=target.getBoundingClientRect();
          if(rect.top < window.innerHeight-24)continue;
          target.classList.add('e54-reveal');
          motionObserver.observe(target);
        }
      });
    }
    const page = () => {
      const html=admin ? adminPage() : teamPage();
      scheduleMotion();
      return html;
    };
    async function load() {
      if(state.loading || state.busy || !isVisible()) return;
      state.loading=true;state.error='';
      try {
        if(admin) {
          const [schools, owners]=await Promise.all([api.listInvitations(),api.enterpriseOwnerInvitations()]);
          state.schools=array(schools?.results || schools);
          state.owners=array(owners?.results || owners);
        } else if(enterprise) {
          state.membership=await api.enterpriseMembership();
          if(state.membership?.membership==='owner') {
            const [invitations,members]=await Promise.all([api.enterpriseRecruiterInvitations(),api.enterpriseRecruiters()]);
            state.invitations=array(invitations?.results || invitations);
            state.members=array(members?.results || members);
          }else{state.invitations=[];state.members=[];}
        }
        state.loaded=true;
      } catch(error) {
        // A failed load is terminal until the user explicitly refreshes; avoid request loops.
        state.loaded=true;
        state.error=error.message||'Le serveur des invitations est indisponible.';
      } finally {state.loading=false;if(isVisible())render();}
    }
    function ensure() {if(!state.loaded&&!state.loading)void load();}
    function getItem(group,index) {
      const map={school:state.schools,owner:state.owners,recruiter:state.invitations};
      return map[group]?.[Number(index)] || null;
    }
    function closeDialog(){if(dialog?.open)dialog.close();}
    function makeDialog() {
      if(dialog)return dialog;
      dialog=document.createElement('dialog');dialog.className='e54-dialog';
      dialog.setAttribute('aria-label','Détails de l’invitation ou du collaborateur');
      document.body.appendChild(dialog);
      dialog.addEventListener('click',event=>{if(event.target===dialog)closeDialog();});
      dialog.addEventListener('click',async event=>{
        if(event.target.closest('[data-e54-close]'))closeDialog();
        const btn=event.target.closest('[data-e54-confirm]');
        if(!btn || state.busy)return;
        const kind=btn.dataset.e54Confirm,id=Number(btn.dataset.e54Id);
        if(!goodId(id))return;
        closeDialog();state.busy=true;state.error='';state.notice='';
        try {
          if(kind==='school')await api.revokeInvitation(id);
          else if(kind==='member')await api.enterpriseRevokeRecruiter(id);
          else await api.enterpriseRevokeInvitation(id);
          state.notice=kind==='member'?'Accès du recruteur révoqué. Toutes ses sessions web ont été fermées.':'Invitation révoquée.';
          state.loaded=false;
        }catch(err){state.error=err.message||'Impossible de révoquer cet accès.';}
        finally{state.busy=false;if(isVisible())render();if(!state.loaded)void load();}
      });
      return dialog;
    }
    function showDetail(kind, item) {
      const id=Number(item?.id);if(!goodId(id))return;
      const member=kind==='member',canRevoke=member?Boolean(item.active):pending(item);
      const name=member?(item.name||item.email):item.company_name || item.institution_name || 'Organisation';
      const title=member?'Collaborateur':kind==='school'?'Invitation Établissement':'Invitation Entreprise';
      const node=makeDialog();
      node.innerHTML='<div class="e54-dialog-shell"><div class="e54-dialog-top"><span>G-CONNECT · ACCÈS PROFESSIONNEL</span><button type="button" data-e54-close aria-label="Fermer">×</button></div>'+
        '<h2>'+safe(title)+'</h2><p class="e54-dialog-sub">'+safe(name)+'</p>'+
        '<div class="e54-dialog-line"><span>E-mail</span><strong>'+safe(item.email||'—')+'</strong></div>'+
        '<div class="e54-dialog-line"><span>État</span><strong>'+safe(member?(item.active?'Actif':'Révoqué'):status(item))+'</strong></div>'+
        (member?'':'<div class="e54-dialog-line"><span>Expiration</span><strong>'+format(item.expires_at)+'</strong></div>')+
        '<p class="e54-warning">La révocation est définitive. '+(member?'Les sessions du collaborateur seront terminées.':'Le lien ne pourra plus être utilisé.')+'</p>'+
        '<div class="e54-dialog-actions"><button type="button" data-e54-close class="e54-small">Fermer</button>'+
        (canRevoke?'<button type="button" class="e54-danger" data-e54-confirm="'+kind+'" data-e54-id="'+id+'">Révoquer '+(member?'l’accès':'l’invitation')+'</button>':'')+
        '</div></div>';
      node.showModal();
    }
    async function submit(form) {
      if(state.busy)return;
      const kind=form.dataset.e54Form;
      const data=new FormData(form),email=String(data.get('email')||'').trim();
      if(!form.reportValidity() || !email)return;
      state.busy=true;state.error='';state.notice='';render();
      try{
        if(kind==='school') {
          const institution_id=Number(data.get('institution_id'));
          if(!goodId(institution_id))throw new Error('Identifiant d’établissement invalide.');
          await api.sendInvitation(email,institution_id);
        }else if(kind==='owner'){
          await api.enterpriseInviteOwner({email,company_name:String(data.get('company_name')||'').trim(),sector:String(data.get('sector')||'').trim()});
        }else if(kind==='recruiter'){
          await api.enterpriseInviteRecruiter(email);
        }else throw new Error('Formulaire non autorisé.');
        state.notice='Invitation envoyée. Le destinataire recevra un lien personnel par e-mail.';
        state.loaded=false;
      }catch(error){state.error=error.message||'L’envoi a échoué.';}
      finally{state.busy=false;if(isVisible())render();if(!state.loaded)void load();}
    }
    document.addEventListener('submit',event=>{
      const form=event.target.closest?.('[data-e54-form]');
      if(!form)return;
      event.preventDefault();void submit(form);
    });
    document.addEventListener('click',event=>{
      const refreshBtn=event.target.closest?.('[data-e54-refresh]');
      if(refreshBtn){state.loaded=false;void load();return;}
      const button=event.target.closest?.('[data-e54-detail],[data-e54-member]');
      if(!button)return;
      if(button.dataset.e54Member){const item=state.members.find(m=>m.id===Number(button.dataset.e54Member));if(item)showDetail('member',item);return;}
      const [group,index]=String(button.dataset.e54Detail||'').split(':');
      const item=getItem(group,index);
      if(item)showDetail(group,item);
    });
    return {page,ensure,load};
  };
})();