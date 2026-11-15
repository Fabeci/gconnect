'use strict';
/* E31 · Academic partner network, connected to secured Superadmin directory.
 * Distinct campus art direction. No fabricated counts, status or payments.
 */
(function(){
  const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('fr');
  window.GConnectInstitutionDirectoryE31=function({api,safe,icon,notify,go,render,isVisible}){
    const state={search:'',status:'all',billing:'all',page:1,page_size:12,loading:false,loaded:false,error:'',payload:null};
    let seq=0,timer=null;
    const esc=value=>safe(value??'');
    const number=value=>Number(value||0).toLocaleString('fr-FR');
    const nameLetters=(item)=>{
      const parts=String(item.acronym||item.name||'E').trim().split(/\s+/);
      return (parts.length>1?parts.slice(0,2).map(p=>p[0]).join(''):parts[0].slice(0,2)).toUpperCase();
    };
    const safeHttpUrl=value=>{
      try{
        const url=new URL(value,location.href);
        if(url.protocol==='https:'||(url.protocol==='http:'&&['localhost','127.0.0.1'].includes(url.hostname)))return url.href;
      }catch(error){}
      return '';
    };
    const data=()=>state.payload||{summary:{total:null,active:null,inactive:null,subscribed:null,expiring_30_days:null},results:[],count:0,pages:1,page:1};
    const metric=(label,value,sub,type,symbol)=>`
      <article class="e31-metric e31-metric--${type}">
        <div class="e31-metric-top"><span class="e31-metric-icon">${icon(symbol)}</span><span class="e31-metric-spark" aria-hidden="true">↗</span></div>
        <strong>${value===null||value===undefined?'—':number(value)}</strong><span class="e31-metric-label">${esc(label)}</span>
        <small>${esc(sub)}</small>
      </article>`;
    const badge=(text,kind)=>`<span class="e31-badge e31-badge--${kind}">${esc(text)}</span>`;
    const row=item=>{
      const logo=safeHttpUrl(item.logo_url);
      const total=Number(item.active_accounts||0);
      const sub=item.subscription;
      const quota=Number(sub?.capacity||0);
      const progress=quota>0?Math.min(100,Math.round(total/quota*100)):0;
      return `<article class="e31-school-row">
        <div class="e31-school-identity">
          <span class="e31-school-logo">${logo?`<img src="${esc(logo)}" alt="" loading="lazy" onerror="this.hidden=true">`:''}<span>${esc(nameLetters(item))}</span></span>
          <div><h3>${esc(item.name)}</h3>
            <p>${esc([item.city,item.country].filter(Boolean).join(', ')||'Localisation non renseignée')}
            ${item.acronym?'<span class="e31-acronym">· '+esc(item.acronym)+'</span>':''}</p></div>
        </div>
        <div class="e31-school-community"><strong>${number(item.members_count)}</strong><small>Membres rattachés</small></div>
        <div class="e31-school-status">${badge(item.is_active?'Actif':'Inactif',item.is_active?'active':'inactive')}
          <small>${sub?'Forfait : '+esc(sub.name):'Aucun forfait actif'}</small></div>
        <div class="e31-school-capacity"><strong>${sub?number(total)+' / '+number(quota):'—'}</strong>
          <span class="e31-capacity-track" aria-hidden="true"><i style="width:${progress}%"></i></span>
          <small>${sub?number(sub.remaining)+' places disponibles':'Sans capacité contractuelle'}</small></div>
        <button type="button" class="e31-view" data-e31-action="detail" data-e31-id="${Number(item.id)}" aria-label="Voir la fiche de ${esc(item.name)}">Voir la fiche <span aria-hidden="true">↗</span></button>
      </article>`;
    };
    const empty=()=>{
      const filtered=!!state.search||state.status!=='all'||state.billing!=='all';
      return `<div class="e31-empty" role="status"><span class="e31-empty-icon">${icon('school')}</span>
        <h3>${filtered?'Aucun établissement pour ces filtres':'Votre annuaire est prêt à accueillir ses partenaires'}</h3>
        <p>${filtered?'Modifiez le nom recherché ou réinitialisez les filtres pour élargir les résultats.':'Aucun établissement n’est enregistré dans le backend. Les futurs partenaires apparaîtront ici dès leur création.'}</p>
        ${filtered?'<button class="e31-ghost" type="button" data-e31-action="reset">Réinitialiser les filtres</button>':
          '<button class="e31-primary" type="button" data-e31-action="invite">Gérer les invitations →</button>'}</div>`;
    };
    function page(){
      const payload=data(),stats=payload.summary||{};
      const value=v=>state.loaded&&v!==undefined?v:null;
      const list=!state.loaded
        ?'<div class="e31-loading" role="status">Chargement des établissements depuis G-Connect…</div>'
        :state.error
        ?`<div class="e31-error" role="alert"><strong>Impossible de charger l’annuaire</strong><p>${esc(state.error)}</p><button type="button" data-e31-action="retry">Réessayer</button></div>`
        :payload.results?.length?payload.results.map(row).join(''):empty();
      const rangeStart=payload.count?(payload.page-1)*state.page_size+1:0;
      const rangeEnd=Math.min(payload.count,payload.page*state.page_size);
      const loadingBadge=state.loading?'<span class="e31-loading-label">Actualisation…</span>':'<span class="e31-realtime">Source : backend sécurisé</span>';
      return `<div class="e31-page" data-e31-page>
        <section class="e31-hero" aria-labelledby="e31-hero-title">
          <div class="e31-hero-copy"><span class="e31-eyebrow"><span class="e31-eyebrow-dot"></span> RÉSEAU ACADÉMIQUE · G-CONNECT</span>
            <h1 id="e31-hero-title">Vos établissements.<br><em>Un écosystème qui grandit.</em></h1>
            <p>Pilotez les partenaires académiques, suivez leurs communautés et leurs capacités d’accès depuis un seul espace.</p>
            <div class="e31-hero-actions">
              <button type="button" class="e31-primary" data-e31-action="invite">Inviter un responsable <span aria-hidden="true">↗</span></button>
              <button type="button" class="e31-hero-outline" data-e31-action="refresh">Actualiser les données ↻</button>
            </div>
          </div>
          <div class="e31-campus-visual" aria-hidden="true">
            <span class="e31-campus-orbit orbit-one"></span><span class="e31-campus-orbit orbit-two"></span>
            <span class="e31-campus-core">${icon('school')}</span>
            <span class="e31-campus-node campus-a">${icon('users')}</span>
            <span class="e31-campus-node campus-b">${icon('school')}</span>
            <span class="e31-campus-node campus-c">${icon('billing')}</span>
            <span class="e31-campus-caption">CAMPUS CONNECTÉS · RÉSEAU VIVANT</span>
          </div>
        </section>
        <section class="e31-insight">
          <div class="e31-section-title"><div><span class="e31-section-eyebrow">VUE D'ENSEMBLE</span><h2>La vie de votre réseau</h2></div>${loadingBadge}</div>
          <div class="e31-metrics">
            ${metric('Établissements',value(stats.total),'Partenaires référencés','total','school')}
            ${metric('En activité',value(stats.active),'Organisations activées','active','shield')}
            ${metric('Avec abonnement',value(stats.subscribed),'Forfaits actifs et valides','subscribed','billing')}
            ${metric('Échéances proches',value(stats.expiring_30_days),'Dans les 30 prochains jours','expiring','history')}
          </div>
        </section>
        <section class="e31-workspace" aria-labelledby="e31-directory-title">
          <div class="e31-section-title e31-list-title"><div>
            <span class="e31-section-eyebrow">ANNUAIRE DES PARTENAIRES</span><h2 id="e31-directory-title">Explorer les établissements</h2>
            <p>Recherche, statut, abonnement et accès à chaque fiche partenaire.</p>
          </div><span class="e31-directory-count">${state.loaded?number(payload.count):'—'} résultat(s)</span></div>
          <div class="e31-toolbar">
            <label class="e31-filter-search">${icon('school')}<input id="e31-search" data-e31-search type="search" placeholder="Nom, sigle, ville ou pays…" value="${esc(state.search)}" aria-label="Rechercher un établissement"></label>
            <label class="e31-filter-select">Statut<select data-e31-filter="status" aria-label="Filtrer par statut">
              <option value="all"${state.status==='all'?' selected':''}>Tous les statuts</option>
              <option value="active"${state.status==='active'?' selected':''}>Actifs</option>
              <option value="inactive"${state.status==='inactive'?' selected':''}>Inactifs</option></select></label>
            <label class="e31-filter-select">Abonnement<select data-e31-filter="billing" aria-label="Filtrer par abonnement">
              <option value="all"${state.billing==='all'?' selected':''}>Tous les forfaits</option>
              <option value="active"${state.billing==='active'?' selected':''}>Avec abonnement</option>
              <option value="none"${state.billing==='none'?' selected':''}>Sans abonnement</option></select></label>
            <button type="button" class="e31-reset" data-e31-action="reset" aria-label="Effacer les filtres" title="Effacer les filtres">↺</button>
          </div>
          <div class="e31-workspace-grid">
            <div class="e31-directory" aria-busy="${state.loading}">
              <div class="e31-directory-heading"><span>PARTENAIRES ACADÉMIQUES</span><small>Comptes et forfaits calculés depuis les données réelles</small></div>
              <div class="e31-school-rows">${list}</div>
              <div class="e31-paginator">
                <span>${state.loaded?`Affichage ${number(rangeStart)}–${number(rangeEnd)} sur ${number(payload.count)}`:'Données en cours de chargement'}</span>
                <div><button type="button" data-e31-action="prev" ${state.page<=1?'disabled':''} aria-label="Page précédente">‹ Précédent</button>
                  <span>Page ${number(payload.page||state.page)} / ${number(payload.pages||1)}</span>
                  <button type="button" data-e31-action="next" ${state.page>=(payload.pages||1)?'disabled':''} aria-label="Page suivante">Suivant ›</button></div>
              </div>
            </div>
            <aside class="e31-companion" aria-labelledby="e31-followup-title">
              <div class="e31-companion-icon">${icon('school')}</div>
              <span class="e31-section-eyebrow">SUIVI DU RÉSEAU</span>
              <h3 id="e31-followup-title">Les partenaires,<br>au bon rythme.</h3>
              <p>Anticipez les échéances et accompagnez la capacité de chaque établissement.</p>
              <div class="e31-companion-stats">
                <div><strong>${state.loaded?number(stats.expiring_30_days):'—'}</strong><span>Forfaits arrivant à échéance</span></div>
                <div><strong>${state.loaded?number(stats.inactive):'—'}</strong><span>Établissements inactifs</span></div>
              </div>
              <button type="button" class="e31-companion-link" data-e31-action="subscriptions">Gérer les abonnements <span>↗</span></button>
              <div class="e31-companion-foot">La présence dans l’annuaire ne constitue pas une vérification administrative. Les abonnements affichés correspondent à des contrats en cours.</div>
            </aside>
          </div>
        </section>
        <dialog class="e31-detail" id="e31-detail-dialog" aria-labelledby="e31-detail-heading">
          <div class="e31-detail-shell" id="e31-detail-content"></div>
        </dialog>
      </div>`;
    }
    async function load(){
      const current=++seq;
      state.loading=true;state.error='';
      try{
        const result=await api.institutionsDirectory({
          search:state.search,status:state.status,billing:state.billing,
          page:state.page,page_size:state.page_size,
        });
        if(current!==seq)return;
        if(!Array.isArray(result?.results)||!result?.summary)throw new Error('Réponse du répertoire invalide.');
        state.payload=result;state.loaded=true;
      }catch(error){
        if(current!==seq)return;
        state.error=error.message||'Service indisponible';state.loaded=true;
      }finally{
        if(current===seq){state.loading=false;if(isVisible())render();}
      }
    }
    function ensure(){if(!state.loaded&&!state.loading)void load();}
    function openDetail(id){
      const item=data().results.find(r=>Number(r.id)===id);
      if(!item)return;
      const dlg=document.getElementById('e31-detail-dialog');
      if(!dlg)return;
      const logo=safeHttpUrl(item.logo_url),site=safeHttpUrl(item.website),sub=item.subscription;
      const initials=nameLetters(item);
      const locationText=[item.city,item.country].filter(Boolean).join(', ')||'Non renseignée';
      const percent=sub&&Number(sub.capacity)>0?Math.min(100,Math.round(Number(item.active_accounts)/Number(sub.capacity)*100)):0;
      dlg.querySelector('#e31-detail-content').innerHTML=`<div class="e31-detail-head"><div class="e31-detail-brand">
        <span class="e31-detail-logo">${logo?`<img src="${esc(logo)}" alt="" onerror="this.hidden=true">`:''}${esc(initials)}</span>
        <div><span class="e31-section-eyebrow">FICHE PARTENAIRE · G-CONNECT</span><h2 id="e31-detail-heading">${esc(item.name)}</h2><small>${esc(locationText)}</small></div>
        </div><button type="button" class="e31-detail-close" data-e31-action="close" aria-label="Fermer la fiche">×</button></div>
        <div class="e31-detail-body">
          <div class="e31-detail-badges">${badge(item.is_active?'Établissement actif':'Établissement inactif',item.is_active?'active':'inactive')}${badge(sub?'Abonnement actif':'Sans abonnement actif',sub?'active':'neutral')}</div>
          <p class="e31-detail-description">${esc(item.description||'Aucune description renseignée pour cet établissement.')}</p>
          <section class="e31-detail-metrics">
            <div><strong>${number(item.members_count)}</strong><span>membres rattachés</span></div>
            <div><strong>${number(item.active_accounts)}</strong><span>comptes autorisés</span></div>
            <div><strong>${sub?number(sub.remaining):'—'}</strong><span>places disponibles</span></div>
          </section>
          <div class="e31-detail-columns">
            <section><h3>Coordonnées</h3>
              <dl><dt>Localisation</dt><dd>${esc(locationText)}</dd>
              <dt>Adresse</dt><dd>${esc(item.address||'Non renseignée')}</dd>
              <dt>E-mail de contact</dt><dd>${esc(item.email||'Non renseigné')}</dd>
              <dt>Téléphone</dt><dd>${esc(item.phone||'Non renseigné')}</dd>
              <dt>Accréditation</dt><dd>${esc(item.accreditation||'Non renseignée')}</dd></dl>
              ${site?`<a href="${esc(site)}" target="_blank" rel="noopener noreferrer" class="e31-detail-link">Site de l’établissement ↗</a>`:''}
            </section>
            <section><h3>Abonnement & capacité</h3>
              ${sub?`<strong class="e31-detail-subname">${esc(sub.name)}</strong>
                  <p class="e31-detail-helper">Valable jusqu’au ${esc(new Date(sub.expires_at+'T12:00:00').toLocaleDateString('fr-FR'))}</p>
                  <div class="e31-detail-progress"><i style="width:${percent}%"></i></div>
                  <p class="e31-detail-helper">${number(item.active_accounts)} comptes autorisés sur ${number(sub.capacity)} places.</p>`:
                 '<p class="e31-detail-helper">Aucun contrat actif enregistré pour cet établissement.</p>'}
              <button type="button" class="e31-companion-link" data-e31-action="subscriptions">Voir les abonnements ↗</button>
            </section>
          </div>
        </div>`;
      dlg.showModal();
    }
    function action(button){
      const type=button.dataset.e31Action;
      if(type==='detail')return openDetail(Number(button.dataset.e31Id));
      if(type==='close'){document.getElementById('e31-detail-dialog')?.close();return;}
      if(type==='invite'){go('invitations');return;}
      if(type==='subscriptions'){document.getElementById('e31-detail-dialog')?.close();go('abonnements');return;}
      if(type==='reset'){state.search='';state.status='all';state.billing='all';state.page=1;void load();return;}
      if(type==='retry'||type==='refresh'){void load();return;}
      if(type==='prev'&&state.page>1){state.page-=1;void load();}
      if(type==='next'&&state.page<(state.payload?.pages||1)){state.page+=1;void load();}
    }
    function onFilter(select){
      const key=select.dataset.e31Filter;
      if(!['status','billing'].includes(key))return;
      state[key]=select.value;
      state.page=1;void load();
    }
    function onSearch(input){
      clearTimeout(timer);
      state.search=input.value;state.page=1;
      timer=setTimeout(()=>{void load();},350);
    }
    return Object.freeze({page,ensure,action,onFilter,onSearch});
  };
})();
