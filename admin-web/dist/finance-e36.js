/* E36 · G-Connect financial operations. Real checkout data only.
 * This interface never issues invoices, authorises payments or activates subscriptions.
 */
(()=>{
'use strict';
const STATUS={all:'Toutes les opérations',paid:'Paiements vérifiés',pending:'En attente',
  failed:'Échecs',canceled:'Annulations'};
const nf=new Intl.NumberFormat('fr-FR',{maximumFractionDigits:0});
const money=(raw,code='XOF')=>{
  const n=Number(raw);
  return Number.isFinite(n)? nf.format(n)+' '+String(code||'').toUpperCase():'Montant indisponible';
};
const dt=raw=>{
  if(!raw)return 'Non renseigné';
  const value=new Date(raw);
  return Number.isNaN(value.getTime())?'Date indisponible':
    value.toLocaleString('fr-FR',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
};
const resultStatus=item=>{
  if(item.status==='paid')return item.is_verified?['Vérifié','paid']:['À examiner','alert'];
  if(item.status==='pending')return ['En attente','pending'];
  if(item.status==='failed')return ['Échec','failed'];
  if(item.status==='canceled')return ['Annulé','canceled'];
  return ['Non déterminé','alert'];
};
window.GConnectFinanceE36=({api,safe,icon,render,isVisible,invoicing})=>{
  const state={loaded:false,loading:false,error:'',payload:null,search:'',status:'all',page:1};
  let requestSequence=0,searchTimer=null,searchFocused=false;
  const count=n=>Number.isSafeInteger(Number(n))?nf.format(Number(n)):'—';
  const panel=(title,subtitle,body)=>`<section class="e36-panel">
    <div class="e36-panel-heading"><div><h3>${title}</h3><p>${subtitle}</p></div></div>${body}</section>`;
  const metric=(title,value,hint,glyph,tone)=>`<article class="e36-metric e36-metric--${tone}">
    <div class="e36-metric-symbol">${icon(glyph)}</div>
    <span>${title}</span><strong>${value}</strong><small>${hint}</small></article>`;
  const statusPill=item=>{
    const [label,type]=resultStatus(item);
    return `<span class="e36-badge e36-badge--${type}">${label}</span>`;
  };
  function page(){
    const data=state.payload,totals=data?.summary,items=data?.results||[];
    const sum=totals? `<div class="e36-metrics">
      ${metric('Paiements vérifiés',count(totals.paid),'Confirmés côté prestataire','check','success')}
      ${metric('En attente',count(totals.pending),'Commandes, pas des créances','clock','pending')}
      ${metric('Échecs et annulations',count(totals.failed+totals.canceled),'Sans activation de forfait','shield','neutral')}
      ${metric('Montant vérifié',money(totals.verified_total_xof),'Encaissements vérifiés · XOF','chart','amount')}
      </div>`:'';
    const rows=items.map(item=>`<tr>
      <td><span class="e36-txn">${safe(String(item.transaction_id).slice(0,13))}…</span>
        <small>${safe(dt(item.created_at))}</small></td>
      <td><strong>${safe(item.organisation_name)}</strong>
        <small>${item.organisation_type==='enterprise'?'Entreprise':'Établissement'}</small></td>
      <td><strong>${safe(item.offer_name)}</strong>
        <small>${count(item.capacity)} ${item.quota_unit==='publications'?'publications':'comptes'} · ${count(item.term_months)} mois</small></td>
      <td class="e36-money">${safe(money(item.amount,item.currency))}</td>
      <td>${statusPill(item)}</td>
      <td><div class="e36-row-actions"><button type="button" class="e36-row-action" data-e36-action="details" data-e36-id="${Number(item.id)}">Détails ↗</button>${invoicing?.actionButton(item)||""}</div></td>
    </tr>`).join('');
    const filters=`<div class="e36-filters">
      <label class="e36-search"><span class="e36-sr">Rechercher une organisation ou une offre</span>
      ${icon('users')}<input id="e36-search" data-e36-search type="search" maxlength="100"
      placeholder="Organisation, offre ou référence complète…" value="${safe(state.search)}" autocomplete="off"></label>
      <label class="e36-select"><span>Statut</span>
      <select data-e36-filter aria-label="Filtrer par statut">${Object.entries(STATUS).map(([k,v])=>
        `<option value="${k}" ${state.status===k?'selected':''}>${v}</option>`).join('')}</select></label>
      <button type="button" class="e36-refresh" data-e36-action="refresh" title="Actualiser les données">↻ Actualiser</button>
    </div>`;
    const pager=data?`<div class="e36-pager"><span>${count(data.count)} résultat(s) · page ${count(data.page)} sur ${count(data.pages)}</span>
      <div><button type="button" data-e36-action="prev" ${data.page<=1?'disabled':''}>Précédent</button>
      <button type="button" data-e36-action="next" ${data.page>=data.pages?'disabled':''}>Suivant</button></div></div>`:'';
    const content=state.loading&&!data?'<div class="e36-state">Chargement du registre financier…</div>':
      state.error?`<div class="e36-state e36-state--error" role="alert">${safe(state.error)}
        <button type="button" data-e36-action="refresh">Réessayer</button></div>`:
      items.length?`<div class="e36-table-wrap"><table class="e36-table">
        <thead><tr><th>Référence</th><th>Organisation</th><th>Forfait</th><th>Montant</th><th>État</th><th>Action</th></tr></thead>
        <tbody>${rows}</tbody></table></div>${pager}`:
      '<div class="e36-state e36-state--empty">Aucune opération ne correspond à cette recherche. Aucune donnée de démonstration n’est affichée.</div>';
    return `<div class="e36-page">
      <header class="e36-hero">
      <div class="e36-hero-copy">
        <span class="e36-kicker">GESTION FINANCIÈRE · G-CONNECT</span>
        <h1>Factures <em>&</em> paiements</h1>
        <p>Suivez les paiements réellement confirmés, leurs contrats et leurs justificatifs
          dans un environnement financier dédié, distinct des abonnements.</p>
        <span class="e36-hero-assurance">${icon('shield')} Données vérifiées côté serveur · Aucun montant fictif</span>
      </div>
      <div class="e36-hero-art" aria-hidden="true">
        <span class="e36-art-halo"></span>
        <span class="e36-art-ring e36-art-ring--outer"></span>
        <span class="e36-art-ring e36-art-ring--inner"></span>
        <span class="e36-art-core">${icon('receipt')}</span>
        <span class="e36-art-node e36-art-node--secure">${icon('shield')}</span>
        <span class="e36-art-node e36-art-node--paid">${icon('check')}</span>
        <span class="e36-art-node e36-art-node--trace">${icon('history')}</span>
        <span class="e36-art-caption">TRANSACTIONS · CONTRÔLES · TRAÇABILITÉ</span>
      </div>
    </header>
      ${sum}
      ${totals?.unverified_paid?`<div class="e36-alert" role="alert">
        ${count(totals.unverified_paid)} opération(s) marquée(s) « payée(s) » sans preuve complète de vérification.
        Ces opérations sont exclues des encaissements confirmés et nécessitent un examen.</div>`:''}
      <div class="e36-columns">
      ${panel('Registre des transactions','Historique réel des commandes du prestataire de paiement.',
        filters+content)}
      <div class="e36-aside">
      ${panel('Rapprochement sécurisé','Contrôles de cohérence des règlements.',
        `<div class="e36-checkline"><i>01</i><div><strong>Vérification prestataire</strong><small>Un retour de paiement seul ne prouve pas l'encaissement.</small></div></div>
        <div class="e36-checkline"><i>02</i><div><strong>Contrat rattaché</strong><small>Le paiement validé doit correspondre à un abonnement activé.</small></div></div>
        <div class="e36-checkline"><i>03</i><div><strong>Référence conservée</strong><small>Montant, devise, date et organisation restent traçables.</small></div></div>`)}
      ${panel('Facturation','Un circuit distinct de l’encaissement.',
        `<div class="e36-invoicing"><span class="e36-badge e36-badge--pending">Émission à intégrer</span>
          <h4>Facturation officielle sur paiement confirmé</h4><p>Les factures numérotées sont émises à la demande,
          uniquement après vérification du paiement et configuration des informations légales.</p>
          <p class="e36-caption">Les montants des abonnements ne sont pas des preuves de règlement.</p></div>`)}
      </div></div>
      ${invoicing?.section()||""}
      <dialog id="e36-dialog" class="e36-dialog" aria-label="Détails du règlement">
        <div id="e36-dialog-body"></div></dialog>
      </div>`;
  }
  function details(id){
    const item=(state.payload?.results||[]).find(x=>Number(x.id)===id);
    const modal=document.getElementById('e36-dialog');
    const box=document.getElementById('e36-dialog-body');
    if(!item||!modal||!box)return;
    const [label,type]=resultStatus(item);
    box.innerHTML=`<div class="e36-dialog-head">
      <div><span class="e36-kicker">DÉTAIL D’OPÉRATION</span><h2>${safe(item.organisation_name)}</h2>
      <small>Référence : ${safe(item.transaction_id)}</small></div>
      <button type="button" data-e36-action="close" aria-label="Fermer">×</button></div>
      <div class="e36-dialog-content"><div class="e36-dialog-total">
        <span>Montant enregistré</span><strong>${safe(money(item.amount,item.currency))}</strong>
        <span class="e36-badge e36-badge--${type}">${label}</span></div>
      <dl>${[
        ['Organisation',item.organisation_type==='enterprise'?'Entreprise':'Établissement'],
        ['Offre',item.offer_name],['Durée',String(item.term_months)+' mois'],
        ['Capacité',String(item.capacity)+' '+(item.quota_unit==='publications'?'publications':'comptes')],
        ['Prestataire',item.provider],['Commande créée',dt(item.created_at)],
        ['Confirmation vérifiée',item.is_verified?dt(item.verified_at):'Non confirmée'],
        ['Contrat lié',item.is_verified&&item.subscription_id?'#'+item.subscription_id:'Aucun contrat confirmé'],
      ].map(([key,value])=>`<div><dt>${safe(key)}</dt><dd>${safe(value)}</dd></div>`).join('')}</dl>
      <p class="e36-proof">Cette fiche est un relevé interne de transaction, et non une facture ni un reçu fiscal.</p>
      <div class="e36-dialog-actions"><button type="button" data-e36-action="close">Fermer</button></div></div>`;
    modal.showModal();
  }
  async function load(){
    const current=++requestSequence;state.loading=true;state.error='';
    try{
      const payload=await api.financeRegister({status:state.status,search:state.search,page:state.page});
      if(current!==requestSequence)return;
      if(!payload?.summary||!Array.isArray(payload.results))throw Error('Format du registre financier inattendu.');
      state.loaded=true;state.payload=payload;
    }catch(error){
      if(current!==requestSequence)return;
      state.error=error?.message||'Impossible de lire le registre financier.';
      state.loaded=true;state.payload=null;
    }finally{
      if(current===requestSequence){
        state.loading=false;
        if(isVisible()){
          render();
          if(searchFocused){
            const input=document.getElementById('e36-search');
            input?.focus();
            input?.setSelectionRange?.(input.value.length,input.value.length);
          }
        }
      }
    }
  }
  function ensure(){if(!state.loaded&&!state.loading)void load();invoicing?.ensure();}
  function action(el){
    switch(el.dataset.e36Action){
      case 'refresh': return void load();
      case 'details': return details(Number(el.dataset.e36Id));
      case 'close': return document.getElementById('e36-dialog')?.close();
      case 'prev': if(state.page>1){state.page--;searchFocused=false;void load();}return;
      case 'next': if(state.page<(state.payload?.pages||1)){state.page++;searchFocused=false;void load();}return;
    }
  }
  function onFilter(el){
    if(!Object.hasOwn(STATUS,el.value))return;
    state.status=el.value;state.page=1;searchFocused=false;void load();
  }
  function onSearch(el){
    state.search=String(el.value||'').slice(0,100);
    state.page=1;searchFocused=true;
    clearTimeout(searchTimer);
    searchTimer=setTimeout(()=>void load(),320);
  }
  return Object.freeze({page,ensure,action,onFilter,onSearch,rows:()=>state.payload?.results||[]});
};
})();
