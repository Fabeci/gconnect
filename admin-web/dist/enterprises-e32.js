'use strict';
/* E32 · Superadmin corporate partner portfolio. Actual enterprise publications, not school seats. */
(function(){
  window.GConnectEnterprisesE32=function({api,safe,icon,go,render,isVisible}){
    const state={search:'',status:'all',billing:'all',page:1,page_size:12,
      loading:false,loaded:false,error:'',payload:null};
    let sequence=0,timer=null,searchFocused=false;
    const esc=value=>safe(value??'');
    const num=value=>Number(value||0).toLocaleString('fr-FR');
    const data=()=>state.payload||{summary:{},results:[],count:0,page:1,pages:1};
    function initials(company){
      const letters=String(company.company_name||'E').trim().split(/\s+/).filter(Boolean);
      return (letters.length>=2?letters.slice(0,2).map(x=>x[0]).join(''):letters[0]?.slice(0,2)||'E').toUpperCase();
    }
    function trustedUrl(value){
      try{
        const u=new URL(value,location.href);
        if(u.protocol==='https:'||(u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)))
          return u.href;
      }catch{}
      return '';
    }
    const chip=(label,kind)=>`<span class="e32-chip e32-chip--${kind}">${esc(label)}</span>`;
    const companyBadge=company=>company.is_banned?'Accès bloqué':company.is_active?'Compte actif':'Compte inactif';
    const companyKind=company=>company.is_banned?'danger':company.is_active?'success':'neutral';
    const capacityText=(contract)=>contract?`${num(contract.used)} / ${num(contract.capacity)}`:'—';
    function logo(company){
      const uri=trustedUrl(company.logo_url);
      return `<span class="e32-logo">${uri?`<img loading="lazy" src="${esc(uri)}" alt="" onerror="this.hidden=true">`:''}<span>${esc(initials(company))}</span></span>`;
    }
    function card(company){
      const contract=company.subscription;
      const used=contract?Number(contract.used)||0:0;
      const total=contract?Number(contract.capacity)||0:0;
      const rate=total?Math.min(100,Math.round(used/total*100)):0;
      return `<article class="e32-company">
        <div class="e32-company-top">${logo(company)}${chip(companyBadge(company),companyKind(company))}</div>
        <div class="e32-company-heading"><h3>${esc(company.company_name)}</h3><p>${esc(company.sector||'Secteur non renseigné')}</p></div>
        <div class="e32-company-activity">
          <div><strong>${num(company.open_offers)}</strong><span>Offres ouvertes</span></div>
          <div><strong>${num(company.applications_count)}</strong><span>Candidatures</span></div>
          <div><strong>${num(company.offers_count)}</strong><span>Offres enregistrées</span></div>
        </div>
        <div class="e32-company-contract">
          <div class="e32-company-contract-heading"><span>CRÉDITS DE PUBLICATION</span>
            ${chip(contract?'Abonnement valide':'Sans abonnement',contract?'contract':'neutral')}</div>
          <div class="e32-company-credits"><strong>${capacityText(contract)}</strong>
            <small>${contract?num(contract.remaining)+' restant(s)':'Aucun quota actif'}</small></div>
          <div class="e32-track" aria-hidden="true"><i style="width:${rate}%"></i></div>
          <p>${contract?'Forfait : '+esc(contract.name):'Attribuer un forfait pour autoriser les publications.'}</p>
        </div>
        <div class="e32-company-foot"><span>${esc(company.contact?.location||'Localisation non renseignée')}</span>
          <button type="button" data-e32-action="detail" data-e32-id="${Number(company.id)}">Consulter la fiche <span aria-hidden="true">↗</span></button></div>
      </article>`;
    }
    function stat(label,value,note,illustration,variant){
      return `<article class="e32-stat e32-stat--${variant}">
        <div class="e32-stat-symbol">${icon(illustration)}</div><strong>${state.loaded?num(value):'—'}</strong>
        <span>${esc(label)}</span><small>${esc(note)}</small></article>`;
    }
    function empty(){
      const filtered=!!state.search||state.status!=='all'||state.billing!=='all';
      return `<div class="e32-empty"><span class="e32-empty-ico">${icon('building')}</span>
        <h3>${filtered?'Aucune entreprise pour cette recherche':'Votre portefeuille est prêt'}</h3>
        <p>${filtered?'Modifiez les filtres pour retrouver vos partenaires.':
          'Aucune entreprise n’est enregistrée. Les partenaires apparaîtront ici dès leur création dans G-Connect.'}</p>
        <button type="button" class="e32-ghost" data-e32-action="${filtered?'reset':'invite'}">${filtered?'Réinitialiser les filtres':'Inviter une entreprise'}</button></div>`;
    }
    function page(){
      const payload=data(),stats=payload.summary||{};
      const visible=state.loaded?(payload.results||[]):[];
      const content=!state.loaded
        ?'<div class="e32-loading" role="status">Chargement du portefeuille depuis le backend…</div>'
        :state.error?`<div class="e32-error" role="alert"><strong>Le portefeuille n’a pas pu être chargé.</strong><p>${esc(state.error)}</p><button data-e32-action="retry" type="button">Réessayer</button></div>`
        :visible.length?visible.map(card).join(''):empty();
      const first=payload.count?(payload.page-1)*state.page_size+1:0;
      const last=Math.min(payload.count,payload.page*state.page_size);
      return `<div class="e32-page" data-e32-page>
        <section class="e32-hero">
          <div class="e32-hero-content"><span class="e32-kicker">PARTENARIATS · G-CONNECT BUSINESS</span>
            <h1>Les entreprises qui<br><em>ouvrent des perspectives.</em></h1>
            <p>Un espace de supervision dédié aux recruteurs : partenaires, opportunités, candidatures et crédits de publication.</p>
            <div class="e32-hero-buttons">
              <button type="button" data-e32-action="invite" class="e32-primary">Inviter une entreprise <span>↗</span></button>
              <button type="button" data-e32-action="refresh" class="e32-hero-secondary">Actualiser ↻</button>
            </div>
          </div>
          <div class="e32-network-art" aria-hidden="true">
            <div class="e32-network-ring e32-ring-one"></div><div class="e32-network-ring e32-ring-two"></div>
            <div class="e32-network-central">${icon('briefcase')}<span>G-CONNECT</span></div>
            <div class="e32-network-item e32-node-a">${icon('users')} <span>Talents</span></div>
            <div class="e32-network-item e32-node-b">${icon('building')} <span>Entreprises</span></div>
            <div class="e32-network-item e32-node-c">${icon('file')} <span>Offres</span></div>
            <div class="e32-network-bottom">UN RÉSEAU D'OPPORTUNITÉS</div>
          </div>
        </section>
        <section class="e32-insights">
          <div class="e32-section-heading"><div><span class="e32-section-eyebrow">PILOTAGE DES PARTENAIRES</span>
            <h2>Votre réseau professionnel</h2></div>
            <span class="e32-live">${state.loading?'Actualisation en cours…':'Données réelles du backend'}</span></div>
          <div class="e32-stats">
            ${stat('Entreprises partenaires',stats.total,'Organisations référencées','building','all')}
            ${stat('Comptes actifs',stats.active,'Accès professionnels autorisés','shield','active')}
            ${stat('Avec forfait Publications',stats.subscribed,'Abonnements actuellement valides','billing','subscribed')}
            ${stat('Échéances dans 30 jours',stats.expiring_30_days,'Contrats à renouveler prochainement','history','expiring')}
          </div>
        </section>
        <section class="e32-portfolio">
          <div class="e32-section-heading"><div><span class="e32-section-eyebrow">PORTEFEUILLE ENTREPRISES</span>
            <h2>Annuaire des partenaires</h2><p>Retrouvez chaque recruteur, son activité et ses crédits de publication.</p></div>
            <span class="e32-total">${state.loaded?num(payload.count):'—'} entreprise(s)</span></div>
          <div class="e32-toolbar">
            <label class="e32-search">${icon('briefcase')}
              <input type="search" id="e32-search" data-e32-search placeholder="Entreprise, secteur, localisation ou e-mail…" value="${esc(state.search)}" aria-label="Rechercher une entreprise"></label>
            <label class="e32-select">Accès<select data-e32-filter="status" aria-label="Filtrer par état du compte">
              <option value="all"${state.status==='all'?' selected':''}>Tous les comptes</option>
              <option value="active"${state.status==='active'?' selected':''}>Actifs</option>
              <option value="inactive"${state.status==='inactive'?' selected':''}>Inactifs ou bloqués</option>
            </select></label>
            <label class="e32-select">Forfait<select data-e32-filter="billing" aria-label="Filtrer par abonnement">
              <option value="all"${state.billing==='all'?' selected':''}>Tous les forfaits</option>
              <option value="active"${state.billing==='active'?' selected':''}>Avec abonnement</option>
              <option value="none"${state.billing==='none'?' selected':''}>Sans abonnement</option>
            </select></label>
            <button class="e32-filter-reset" type="button" title="Effacer les filtres" aria-label="Effacer les filtres" data-e32-action="reset">↺</button>
          </div>
          <div class="e32-portfolio-layout"><div class="e32-directory" aria-busy="${state.loading}">
            <div class="e32-directory-head"><span>PARTENAIRES ENREGISTRÉS</span><span>Offres et crédits vérifiés côté serveur</span></div>
            <div class="e32-card-grid">${content}</div>
            <div class="e32-pages"><span>${state.loaded?'Affichage '+num(first)+' à '+num(last)+' sur '+num(payload.count):'Chargement…'}</span>
              <div><button type="button" data-e32-action="prev" ${state.page<=1?'disabled':''}>‹ Précédent</button>
              <span>Page ${num(payload.page||state.page)} / ${num(payload.pages||1)}</span>
              <button type="button" data-e32-action="next" ${state.page>=(payload.pages||1)?'disabled':''}>Suivant ›</button></div>
            </div>
          </div>
          <aside class="e32-aside">
            <div class="e32-aside-icon">${icon('briefcase')}</div>
            <span class="e32-section-eyebrow">GESTION DES FORFAITS</span>
            <h3>Chaque publication<br>compte.</h3>
            <p>Les entreprises achètent des crédits pour publier pendant 1, 6 ou 12 mois.
               Une publication consommée ne redevient pas disponible après suppression.</p>
            <div class="e32-aside-note"><strong>${state.loaded?num(stats.subscribed):'—'}</strong><span>Entreprises disposant actuellement d’un forfait Publications</span></div>
            <button class="e32-aside-link" type="button" data-e32-action="subscriptions">Gérer les abonnements ↗</button>
            <small>Les statuts et les contrats sont issus du backend. Aucun paiement n'est présumé effectué.</small>
          </aside></div>
        </section>
        <dialog id="e32-detail-dialog" class="e32-dialog" aria-labelledby="e32-detail-title">
          <div class="e32-dialog-content" id="e32-dialog-content"></div>
        </dialog>
      </div>`;
    }
    async function load(){
      const requestId=++sequence;
      state.loading=true;state.error='';
      try{
        const response=await api.enterprisePartnerDirectory({
          search:state.search,status:state.status,billing:state.billing,
          page:state.page,page_size:state.page_size,
        });
        if(requestId!==sequence)return;
        if(!Array.isArray(response?.results)||!response?.summary)
          throw Error('La réponse du répertoire est invalide.');
        state.payload=response;state.loaded=true;
      }catch(error){
        if(requestId!==sequence)return;
        state.error=error.message||'Service indisponible';state.loaded=true;
      }finally{
        if(requestId===sequence){
          state.loading=false;
          if(isVisible()){
            render();
            if(searchFocused){const input=document.getElementById('e32-search');input?.focus();input?.setSelectionRange?.(input.value.length,input.value.length);}
          }
        }
      }
    }
    function ensure(){if(!state.loaded&&!state.loading)void load();}
    function openDetails(id){
      const company=data().results.find(x=>Number(x.id)===id);
      if(!company)return;
      const dialog=document.getElementById('e32-detail-dialog');
      if(!dialog)return;
      const sub=company.subscription, website=trustedUrl(company.website);
      const location=company.contact?.location||'Non renseignée';
      const expiration=sub?new Date(sub.expires_at+'T12:00:00').toLocaleDateString('fr-FR'):'';
      const percent=sub&&Number(sub.capacity)>0?Math.min(100,Math.round(Number(sub.used)/Number(sub.capacity)*100)):0;
      dialog.querySelector('#e32-dialog-content').innerHTML=`<div class="e32-dialog-head">
          <div class="e32-dialog-company">${logo(company)}<div><span class="e32-section-eyebrow">FICHE PARTENAIRE · ENTREPRISE</span>
            <h2 id="e32-detail-title">${esc(company.company_name)}</h2><p>${esc(company.sector||'Secteur non renseigné')}</p></div></div>
          <button class="e32-close" type="button" data-e32-action="close" aria-label="Fermer la fiche">×</button></div>
        <div class="e32-dialog-body">
          <div class="e32-dialog-badges">${chip(companyBadge(company),companyKind(company))}
          ${chip(sub?'Forfait actif':'Aucun forfait actif',sub?'contract':'neutral')}</div>
          <div class="e32-dialog-metrics"><div><strong>${num(company.open_offers)}</strong><span>offres ouvertes</span></div>
            <div><strong>${num(company.applications_count)}</strong><span>candidatures</span></div>
            <div><strong>${num(company.offers_count)}</strong><span>offres enregistrées</span></div></div>
          <div class="e32-dialog-columns">
            <section><h3>Informations du partenaire</h3><dl>
              <dt>Adresse e-mail</dt><dd>${esc(company.contact?.email||'Non renseignée')}</dd>
              <dt>Téléphone</dt><dd>${esc(company.contact?.phone||'Non renseigné')}</dd>
              <dt>Localisation</dt><dd>${esc(location)}</dd></dl>
              ${website?`<a class="e32-site" href="${esc(website)}" target="_blank" rel="noopener noreferrer">Site de l’entreprise ↗</a>`:''}
            </section><section><h3>Abonnement Publications</h3>
              ${sub?`<strong class="e32-subscription-name">${esc(sub.name)}</strong>
                <p class="e32-subscription-expires">Échéance : ${esc(expiration)}</p>
                <div class="e32-dialog-usage"><strong>${num(sub.used)} / ${num(sub.capacity)}</strong>
                  <small>${num(sub.remaining)} crédit(s) restant(s)</small></div>
                <div class="e32-progress"><i style="width:${percent}%"></i></div>
                <p class="e32-dialog-hint">Inclus : ${num(sub.included)}, extensions : ${num(sub.extra)}.</p>`:
                '<p class="e32-dialog-hint">Cette entreprise ne dispose pas d’un abonnement Publications valide.</p>'}
              <button class="e32-aside-link" type="button" data-e32-action="subscriptions">Gérer les abonnements ↗</button>
            </section></div></div>`;
      dialog.showModal();
    }
    function action(element){
      const action=element.dataset.e32Action;
      if(action==='detail')return openDetails(Number(element.dataset.e32Id));
      if(action==='close')return document.getElementById('e32-detail-dialog')?.close();
      if(action==='invite')return go('invitations');
      if(action==='subscriptions'){
        document.getElementById('e32-detail-dialog')?.close();
        return go('abonnements');
      }
      if(action==='reset'){
        state.search='';state.status='all';state.billing='all';state.page=1;
        searchFocused=false;void load();return;
      }
      if(action==='refresh'||action==='retry'){void load();return;}
      if(action==='prev'&&state.page>1){state.page--;searchFocused=false;void load();}
      if(action==='next'&&state.page<(state.payload?.pages||1)){state.page++;searchFocused=false;void load();}
    }
    function onFilter(element){
      const key=element.dataset.e32Filter;
      if(!['status','billing'].includes(key))return;
      state[key]=element.value;state.page=1;searchFocused=false;void load();
    }
    function onSearch(element){
      clearTimeout(timer);
      state.search=element.value;state.page=1;searchFocused=true;
      timer=setTimeout(()=>void load(),350);
    }
    return Object.freeze({page,ensure,action,onFilter,onSearch});
  };
})();
