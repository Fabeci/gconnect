/* E38 · Issued invoices, genuine PDFs, independent of checkout quotes.
 * Superadmin: legal issuer configuration and verified-checkout invoice issuance.
 * Client: read-only, organisation-scoped issued invoices with secure PDF download.
 */
(()=>{
'use strict';
const nf=new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2});
const amount=(value,currency)=>Number.isFinite(Number(value))
  ?nf.format(Number(value))+' '+String(currency||'XOF'):'Montant indisponible';
const date=value=>{
  if(!value)return '—';
  const parsed=new Date(value);
  return Number.isNaN(parsed.getTime())?'—':parsed.toLocaleDateString('fr-FR',{
    day:'2-digit',month:'short',year:'numeric',
  });
};
const fields=[
 ['legal_name','Raison sociale légale'],
 ['registration_number',"N° d’immatriculation"],
 ['tax_identifier','Identifiant fiscal'],
 ['address','Adresse juridique complète'],
 ['country_code','Pays (ISO : SN, BF…)'],
 ['email','E-mail de facturation'],
 ['invoice_prefix','Préfixe de numérotation'],
 ['tax_label','Nom de la taxe (ex. TVA)'],
 ['tax_rate','Taux (%) si taxe incluse'],
 ['exemption_reason',"Référence légale si exonération"],
];
window.GConnectInvoicingE38=({api,safe,render,isVisible,admin=true,verifiedRows,refreshPayments})=>{
  const state={ready:false,busy:false,issuer:null,history:null,error:'',notice:'',page:1,search:''};
  let currentAction='',selectedCheckout=null,loading=null;
  const e=safe;
  const fetchState=async()=>{
    state.error='';
    try{
      if(admin){
        const [issuer,history]=await Promise.all([api.invoiceIssuer(),api.invoiceHistory({page:state.page,search:state.search})]);
        state.issuer=issuer;state.history=history;
      }else state.history=await api.myInvoices({page:state.page});
      state.ready=true;
    }catch(err){
      state.ready=true;
      state.error=err?.message||'Les factures sont momentanément indisponibles.';
    }
    if(isVisible())render();
  };
  const ensure=()=>{
    if(!state.ready&&!loading)loading=fetchState().finally(()=>{loading=null});
  };
  function actionButton(item){
    if(!admin||!item?.is_verified)return '';
    if(item.invoice_id)return `<button class="e38-inline e38-inline--file" type="button"
      data-e38-action="pdf" data-e38-id="${Number(item.invoice_id)}"
      data-e38-number="${e(item.invoice_number)}">PDF facture</button>`;
    return `<button class="e38-inline" type="button" data-e38-action="issue-open"
      data-e38-id="${Number(item.id)}">Émettre facture</button>`;
  }
  function invoiceRows(){
    const entries=state.history?.results||[];
    if(!entries.length)return `<div class="e38-empty">
      <div class="e38-empty-mark">▤</div><strong>Aucune facture émise</strong>
      <p>Une facture apparaît après émission réelle sur un paiement confirmé.
      Les abonnements attribués manuellement ne sont pas des paiements.</p></div>`;
    return `<div class="e38-table-scroll"><table class="e38-table"><thead><tr>
      <th>Facture</th><th>Client</th><th>Forfait</th><th>Montant acquitté</th><th>Justificatif</th>
      </tr></thead><tbody>${entries.map(inv=>`<tr>
      <td><strong>${e(inv.number)}</strong><small>${e(date(inv.issued_at))}</small></td>
      <td>${e(inv.organisation_name||'—')}</td>
      <td>${e(inv.offer_name||'—')}</td>
      <td class="e38-money">${e(amount(inv.amount_total,inv.currency))}</td>
      <td><button type="button" class="e38-pdf" data-e38-action="pdf"
      data-e38-id="${Number(inv.id)}" data-e38-number="${e(inv.number)}">↓ PDF</button></td>
      </tr>`).join('')}</tbody></table></div>
      <footer class="e38-list-footer">
        <span>${Number(state.history?.count)||0} facture(s) · page ${Number(state.history?.page)||1} / ${Number(state.history?.pages)||1}</span>
        <div class="e38-page-controls"><button type="button" data-e38-action="prev-list"
          ${Number(state.history?.page)<=1?'disabled':''}>← Précédent</button>
          <button type="button" data-e38-action="next-list"
          ${Number(state.history?.page)>=Number(state.history?.pages)?'disabled':''}>Suivant →</button></div>
      </footer>`;
  }
  function section(){
    const ready=state.issuer?.ready;
    return `<section class="e38-page" aria-label="Facturation G-Connect">
      ${admin?`<div class="e38-issuer-banner">
        <span class="e38-icon">▣</span>
        <div><span class="e38-caption">ÉMISSION DE FACTURES</span>
          <h3>${ready?'Identité de facturation configurée':'Configurer les informations légales'}</h3>
          <p>${ready?
            'Factures numérotées, documentées et rattachées aux paiements vérifiés.' :
            'L’émission reste bloquée tant que l’émetteur, la fiscalité et les mentions légales ne sont pas validés.'}</p></div>
        <button class="e38-configure" type="button" data-e38-action="issuer-open">${ready?'Modifier l’émetteur':'Configurer l’émetteur'} ↗</button>
      </div>`:''}
      <div class="e38-list-panel">
        <header class="e38-head">
          <div><span class="e38-caption">${admin?'HISTORIQUE FINANCIER':'VOS JUSTIFICATIFS'}</span>
            <h2>${admin?'Factures émises':'Mes factures'}</h2>
            <p>Documents officiels émis et conservés, disponibles au format PDF.</p></div>
          <button type="button" class="e38-refresh" data-e38-action="refresh">↻ Actualiser</button>
        </header>
        ${admin?`<form data-e38-form="search" class="e38-history-search">
          <label><span>Rechercher une facture, un établissement ou une entreprise</span>
            <input name="search" type="search" maxlength="100" value="${e(state.search)}"
              placeholder="N° de facture ou organisation…"></label>
            <button type="submit">Rechercher</button></form>`:''}
        ${state.notice?`<div role="status" class="e38-notice">${e(state.notice)}</div>`:''}
        ${state.error?`<div class="e38-error" role="alert">${e(state.error)}</div>`:''}
        ${!state.ready&&!state.error?'<div class="e38-pending">Chargement des factures…</div>':
          state.error?'':invoiceRows()}
      </div>
      <dialog id="e38-modal" class="e38-modal" aria-label="Opération de facturation">
        <div id="e38-modal-body"></div>
      </dialog>
    </section>`;
  }
  function show(html){
    const modal=document.getElementById('e38-modal');
    const body=document.getElementById('e38-modal-body');
    if(!modal||!body)return;
    body.innerHTML=html;
    modal.showModal();
    const first=modal.querySelector('input,select,textarea');
    first?.focus();
  }
  function header(title,description){
    return `<div class="e38-modal-head"><div><span class="e38-caption">G-CONNECT · FACTURATION</span>
      <h2>${e(title)}</h2><p>${e(description)}</p></div>
      <button type="button" data-e38-action="close" aria-label="Fermer">×</button></div>`;
  }
  const input=(name,label,value='',type='text')=>`<label><span>${e(label)}</span><input name="${e(name)}"
    type="${e(type)}" value="${e(value??'')}" maxlength="254" autocomplete="off"></label>`;
  function issuerModal(){
    if(!admin)return;
    const data=state.issuer||{};
    const group=fields.map(([name,label])=>{
      const value=data[name]??'';
      if(name==='address')return `<label class="e38-wide"><span>${e(label)}</span>
        <textarea name="address" rows="3" maxlength="2000">${e(value)}</textarea></label>`;
      return input(name,label,value,name==='email'?'email':'text');
    }).join('');
    show(`${header('Identité juridique de G-Connect','À compléter avec les informations réelles de l’entité qui facture.')}
    <form data-e38-form="issuer" class="e38-modal-content">
      <div class="e38-grid">${group}
        <label><span>Régime fiscal</span><select name="tax_treatment">
        <option value="" ${!data.tax_treatment?'selected':''}>Choisir le régime réel</option>
        <option value="included" ${data.tax_treatment==='included'?'selected':''}>Taxe incluse dans le prix</option>
        <option value="exempt" ${data.tax_treatment==='exempt'?'selected':''}>Exonération / non applicable</option>
        </select></label></div>
      <p class="e38-important">Les montants proviennent des paiements vérifiés. Le régime fiscal et
       ses références légales doivent être validés avant toute émission de facture.</p>
      <div class="e38-form-error" aria-live="polite"></div>
      <div class="e38-modal-actions"><button type="button" data-e38-action="close">Annuler</button>
        <button class="e38-primary" type="submit">Enregistrer la configuration</button></div>
    </form>`);
  }
  function issueModal(id){
    if(!admin)return;
    const item=(verifiedRows?.()||[]).find(x=>Number(x.id)===Number(id));
    if(!item||!item.is_verified||item.invoice_id)return;
    selectedCheckout=item;
    if(!state.issuer?.ready){issuerModal();return;}
    show(`${header('Émettre une facture',item.organisation_name)}
      <div class="e38-issue-summary"><strong>${e(item.offer_name)}</strong>
        <span>${e(amount(item.amount,item.currency))} · Paiement vérifié</span>
        <small>Référence : ${e(item.transaction_id)}</small></div>
      <form data-e38-form="issue" class="e38-modal-content">
        <input type="hidden" name="checkout_id" value="${Number(item.id)}">
        <div class="e38-grid">
          <label class="e38-wide"><span>Adresse légale du client *</span>
            <textarea name="buyer_address" rows="3" required maxlength="2000"
            placeholder="Adresse complète de facturation"></textarea></label>
          ${input('buyer_country_code','Pays client (ISO) *','')}
          ${input('buyer_email','E-mail du client *',item.organisation_email||'','email')}
          ${input('buyer_tax_identifier','Identifiant fiscal du client (si applicable)','')}
        </div>
        <p class="e38-important">Confirmez l'identité légale et le régime fiscal applicables.
          Une facture émise devient immuable. Pour corriger un document, il faudra un avoir.</p>
        <div class="e38-form-error" aria-live="polite"></div>
        <div class="e38-modal-actions"><button type="button" data-e38-action="close">Annuler</button>
          <button class="e38-primary" type="submit">Émettre et numéroter</button></div>
      </form>`);
  }
  async function submit(form){
    if(state.busy)return;
    const type=form.dataset.e38Form;
    if(!admin||!['issuer','issue','search'].includes(type))return;
    const data=Object.fromEntries(new FormData(form).entries());
    const message=form.querySelector('.e38-form-error');
    const button=form.querySelector('[type=submit]');
    if(message)message.textContent='';
    if(type==='search'){
      state.search=String(data.search||'').trim().slice(0,100);
      state.page=1;await fetchState();return;
    }
    state.busy=true;if(button)button.disabled=true;
    try{
      if(type==='issuer'){
        const saved=await api.invoiceSaveIssuer(data);
        state.issuer=saved;
        state.notice='Identité juridique de facturation enregistrée.';
      }else{
        if(!selectedCheckout||Number(data.checkout_id)!==Number(selectedCheckout.id)
          ||!selectedCheckout.is_verified)throw Error('Transaction non vérifiée.');
        const answer=await api.invoiceIssue(data);
        state.notice=answer.created?'Facture '+answer.invoice.number+' émise avec succès.'
          :'Facture existante : '+answer.invoice.number;
      }
      document.getElementById('e38-modal')?.close();
      state.page=1;
      await fetchState();
      if(type==='issue')refreshPayments?.();
    }catch(err){
      if(message)message.textContent=err?.message||'Émission impossible.';
    }finally{state.busy=false;if(button)button.disabled=false;}
  }
  async function action(button){
    const name=button.dataset.e38Action;
    if(name==='close'){document.getElementById('e38-modal')?.close();return;}
    if(name==='issuer-open'){issuerModal();return;}
    if(name==='issue-open'){issueModal(button.dataset.e38Id);return;}
    if(name==='pdf'){
      try{
        await api.downloadInvoicePdf(Number(button.dataset.e38Id),
          String(button.dataset.e38Number||''),admin);
      }catch(err){state.error=err?.message||'Téléchargement impossible.';if(isVisible())render();}
      return;
    }
    if(name==='refresh'){await fetchState();return;}
    if(name==='next-list'||name==='prev-list'){
      if(state.busy)return;
      const page=Number(state.history?.page)||1;
      const next=page+(name==='next-list'?1:-1);
      if(next<1||next>(Number(state.history?.pages)||1))return;
      state.page=next;
      try{
        state.history=admin?await api.invoiceHistory({page:state.page,search:state.search}):
          await api.myInvoices({page:state.page});
        if(isVisible())render();
      }catch(err){state.error=err?.message||'Page indisponible.';if(isVisible())render();}
    }
  }
  return Object.freeze({section,ensure,action,submit,actionButton});
};
})();
