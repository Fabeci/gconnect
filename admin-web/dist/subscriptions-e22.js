'use strict';
/* E22 subscription UI factory; called only from the MFA-verified shared admin shell. */
(function(){
  window.GConnectSubscriptionsE22 = function(ctx){
    const api=ctx.api;
    const state={loaded:false,busy:false,error:'',requestError:'',catalog:[],mine:null,myRequests:[],requests:[],requestFilter:'all',expandedRequests:false,reviewRequestId:null,clientDialog:null,selectedCheckoutPriceId:null,checkout:{enabled:false,provider:'cinetpay'},checkoutOrders:[],checkoutError:'',seats:null,selectedAudience:null,offers:[],organisations:{institutions:[],enterprises:[]},assignments:[]};
    let serial=0;
    const esc=value=>ctx.safe(value===null||value===undefined?'':String(value));
    const terms={0:'Sur devis',1:'1 mois',6:'6 mois',12:'12 mois'};
    const types={flexible:'Offre Flexible',per_account:'Offre par compte'};
    const unit=p=>p.quota_unit==='publications'?'publications':'comptes';
    const audienceLabel=a=>a==='enterprise'?'Entreprises':'Établissements';
    const quotaText=p=>esc(p.capacity??p.seats)+' '+unit(p);
    const cash=p=>p.amount===null?'Sur devis':new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2}).format(Number(p.amount))+' '+esc(p.currency||'XOF');
    const pill=(text,muted)=>'<span class="e22-pill'+(muted?' muted':'')+'">'+esc(text)+'</span>';
    const empty=label=>'<div class="e22-empty">'+esc(label)+'</div>';
    const message=()=>state.error?'<div class="e22-notice e22-error" role="alert">'+esc(state.error)+'</div>':'';
    const statusText=status=>({active:'Actif',expired:'Expiré',scheduled:'À venir',ended:'Terminé',suspended:'Suspendu'})[status]||status;
    const pricerow=p=>'<tr><td>'+esc(terms[p.term_months]||p.term_months)+'</td><td>'+quotaText(p)+'</td><td><strong>'+cash(p)+'</strong></td></tr>';
    const rowTable=(rows,head)=>'<div class="e22-scroll"><table class="e22-price-grid"><thead><tr>'+head.map(label=>'<th>'+esc(label)+'</th>').join('')+'</tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';

    async function load(){
      const id=++serial;state.error='';
      try{
        if(ctx.admin){
          const [offers,organisations,assignments]=await Promise.all([
            api.pricingAdminOffers(),api.pricingAdminOrganisations(),api.pricingAdminAssignments(),
          ]);
          if(id!==serial)return;
          state.offers=Array.isArray(offers)?offers:[];
          state.organisations=organisations||{institutions:[],enterprises:[]};
          state.assignments=Array.isArray(assignments)?assignments:[];
          if(api.pricingAdminRequests){
            try{
              const requests=await api.pricingAdminRequests();
              if(id!==serial)return;
              state.requests=Array.isArray(requests)?requests:[];
              state.requestError='';
            }catch(error){
              state.requests=[];
              state.requestError=error.message||'Les demandes ne sont pas accessibles.';
            }
          }
        }else{
          const [catalog,mine]=await Promise.all([api.subscriptionCatalog(),api.subscriptionMine()]);
          if(id!==serial)return;
          state.catalog=Array.isArray(catalog)?catalog:[];
          state.mine=mine;
          state.checkoutError='';
          if(api.subscriptionCheckoutConfig && api.subscriptionCheckoutOrders){
            try{
              const [config,orders]=await Promise.all([
                api.subscriptionCheckoutConfig(),api.subscriptionCheckoutOrders(),
              ]);
              if(id!==serial)return;
              state.checkout=config||{enabled:false};
              state.checkoutOrders=Array.isArray(orders)?orders:[];
            }catch(error){
              state.checkout={enabled:false,provider:'cinetpay'};
              state.checkoutOrders=[];
              state.checkoutError=error.message||'Le paiement est temporairement indisponible.';
            }
          }
          if(api.subscriptionRequestsMine){
            try{
              const requests=await api.subscriptionRequestsMine();
              if(id!==serial)return;
              state.myRequests=Array.isArray(requests)?requests:[];
              state.requestError='';
            }catch(error){
              state.myRequests=[];
              state.requestError=error.message||'Le suivi des demandes est indisponible.';
            }
          }
          state.seats=null;
          if(mine?.organisation_type==='institution'&&api.subscriptionSeats){
            try{state.seats=await api.subscriptionSeats();}catch(_){state.seats=null;}
          }
        }
      }catch(error){
        if(id!==serial)return;
        state.error=error.message||'Le service des abonnements ne répond pas.';
      }
      state.loaded=true;
      if(['abonnements','facturation','subscription'].includes(ctx.route()))ctx.render();
    }

    function offerCard(offer,admin){
      const all=Array.isArray(offer.prices)?offer.prices:[];
      const active=all.filter(p=>p.is_active);
      const retired=all.length-active.length;
      const badge=offer.quota_unit==='publications'?'Offre Publications':types[offer.kind]||offer.kind;
      let html='<article class="e22-card"><div class="e22-topline"><span class="e22-label">'+esc(badge)+'</span>'+pill(offer.is_active?'Disponible':'Masquée',!offer.is_active)+'</div>';
      html+='<h2>'+esc(offer.name)+'</h2><p>'+esc(offer.description||'Offre adaptée à votre organisation.')+'</p>';
      html+='<div class="e22-presentation"><span>'+esc(unit(offer)==='comptes'?'Capacité de comptes actifs':'Crédits consommés par publication')+'</span><strong>1 mois · 6 mois · 12 mois</strong></div>';
      if(active.length){
        const rows=active.map(p=>admin
          ?pricerow(p).replace('</tr>','<td><button type="button" class="e22-button subtle" data-sub-action="retire-price" data-id="'+esc(p.id)+'">Retirer</button></td></tr>')
          :pricerow(p));
        html+=rowTable(rows,admin?['Durée','Capacité','Montant','Action']:['Durée','Capacité','Montant']);
      }
      else html+=empty('Aucun tarif publié pour cette offre.');
      if(admin){
        html+='<div class="e22-history">'+esc(retired)+' ancien(s) tarif(s) conservé(s) dans l’historique.</div>';
        html+='<div class="e22-actions"><button class="e22-button subtle" type="button" data-sub-action="toggle" data-id="'+esc(offer.id)+'" data-active="'+(!offer.is_active)+'">'+(offer.is_active?'Masquer cette offre':'Réactiver cette offre')+'</button></div>';
      }
      return html+'</article>';
    }

    function quotaOverview(contract){
      const quota=contract?.quota||state.mine?.quota;
      if(!quota)return '';
      const percent=quota.limit?Math.min(100,Math.round(quota.used*100/quota.limit)):100;
      const label=quota.unit==='publications'?'Publications utilisées':'Comptes actifs';
      const warning=quota.remaining===0?'Limite atteinte : demandez un complément ou un renouvellement.':quota.remaining<=Math.max(1,Math.ceil(quota.limit*.2))?'Votre capacité arrive à sa limite.':'Votre capacité est disponible.';
      return '<section class="e22-quota" aria-label="Consommation de l’abonnement"><div class="e22-quota-heading"><div><span class="e22-label">'+label+'</span><h3>'+esc(quota.used)+' <small>/ '+esc(quota.limit)+'</small></h3></div>'+pill(quota.remaining+' restants',quota.remaining===0)+'</div>'
        +'<div class="e22-meter"><span style="width:'+percent+'%"></span></div><p>'+esc(warning)+'</p>'
        +'<p class="e22-history">Capacité initiale : '+esc(quota.included)+' · Suppléments : '+esc(quota.extra)+'. '+(quota.unit==='publications'?'La suppression d’une publication ne restitue pas de crédit.':'Désactiver un compte libère une place.')+'</p></section>';
    }

    function institutionSeats(){
      const members=Array.isArray(state.seats?.members)?state.seats.members:[];
      if(state.mine?.organisation_type!=='institution'||!members.length)return '';
      return ctx.panel('Comptes de votre établissement','Activer ou désactiver une place sans modifier le fil d’actualité.',
        rowTable(members.slice(0,50).map(m=>'<tr><td>'+esc(m.name)+'</td><td>'+esc(m.role==='student'?'Étudiant':'Alumni')+'</td><td>'+pill(m.seat_enabled&&m.user_active?'Actif':'Inactif',!m.seat_enabled||!m.user_active)+'</td><td>'
          +'<button class="e22-button subtle" type="button" data-sub-action="seat" data-id="'+esc(m.id)+'" data-role="'+esc(m.role)+'" data-enabled="'+(!m.seat_enabled)+'">'+(m.seat_enabled?'Désactiver':'Activer')+'</button></td></tr>'),['Utilisateur','Profil','Place','Action']));
    }


    function clientRequestsPanel(current){
      const orgUnit=state.mine?.organisation_type==='enterprise'?'publications':'comptes actifs';
      const rows=(state.myRequests||[]).slice(0,8).map(item=>
        '<tr><td>'+esc(requestType(item.request_type))+'</td>'
        +'<td>'+requestQuantity(item)+'</td>'
        +'<td>'+esc(String(item.created_at||'').slice(0,10))+'</td>'
        +'<td>'+pill(requestStatus(item.status),item.status!=='approved')+'</td>'
        +'<td>'+esc(item.admin_note||'—')+'</td></tr>'
      );
      const renewal='<form class="e26-client-request" data-sub-form="renewal-request">'
        +'<div><span class="e22-label">RENOUVELLEMENT</span><h3>Prolonger mon abonnement</h3>'
        +'<p>Choisissez une durée. La demande sera examinée par G-Connect.</p></div>'
        +'<label class="e22-field"><span>Durée souhaitée</span><select required name="requested_term_months">'
        +'<option value="1">1 mois</option><option value="6">6 mois</option><option value="12">12 mois</option></select></label>'
        +'<label class="e22-field"><span>Message (facultatif)</span><input name="note" maxlength="500" placeholder="Informations complémentaires"></label>'
        +'<button class="e22-button" type="submit">Envoyer la demande</button></form>';
      const capacity=current?'<form class="e26-client-request" data-sub-form="capacity-request">'
        +'<div><span class="e22-label">CAPACITÉ</span><h3>Ajouter de la capacité</h3>'
        +'<p>Demandez des '+orgUnit+' supplémentaires, sans changer la durée actuelle.</p></div>'
        +'<label class="e22-field"><span>Quantité supplémentaire</span>'
        +'<input name="requested_quantity" type="number" min="1" max="1000000" required step="1" placeholder="Ex. 10"></label>'
        +'<label class="e22-field"><span>Message (facultatif)</span><input name="note" maxlength="500" placeholder="Précisez votre besoin"></label>'
        +'<button class="e22-button" type="submit">Envoyer la demande</button></form>'
        :'<div class="e26-request-inactive">L’extension de capacité est accessible après activation d’un abonnement.</div>';
      return '<section class="e26-client-requests">'
        +'<div class="e22-section-heading"><h2>Renouveler ou augmenter ma capacité</h2><span class="e22-label">Demandes envoyées au Superadmin</span></div>'
        +(state.requestError?'<p class="e22-notice e22-error">'+esc(state.requestError)+'</p>':'')
        +'<div class="e26-client-requests-grid">'+renewal+capacity+'</div>'
        +'<p class="e22-history">L’envoi ne prélève aucun paiement et ne modifie pas votre contrat. Une décision favorable devra ensuite être appliquée manuellement.</p>'
        +'<h3 class="e26-client-history-title">Suivi de mes demandes</h3>'
        +(rows.length?rowTable(rows,['Type','Demande','Date','État','Réponse du Superadmin']):empty('Aucune demande envoyée pour le moment.'))
        +'</section>';
    }

    function clientActionTiles(){
      const isEnterprise=state.mine?.organisation_type==='enterprise';
      const metric=isEnterprise?'publications':'comptes actifs';
      const items=[
        {id:'checkout',title:'Choisir et payer un forfait',
         intro:'Parcourir les offres disponibles',description:'1, 6 ou 12 mois · règlement sécurisé sur la plateforme du prestataire.',icon:'▤'},
        {id:'request',title:'Demander un réabonnement',
         intro:'Demande personnalisée',description:'Renouvellement ou capacité supplémentaire, soumis au Superadmin.',icon:'▥'},
      ];
      return '<div class="e22-feature-grid e27-client-tiles">'+items.map(item=>
        '<button type="button" class="e22-feature" data-sub-action="client-open" data-client-view="'+item.id+'">'
        +'<span class="e22-feature-icon" aria-hidden="true">'+item.icon+'</span>'
        +'<span class="e22-feature-content"><span class="e22-label">'+(isEnterprise?'ENTREPRISE':'ÉTABLISSEMENT')+'</span>'
        +'<strong>'+esc(item.title)+'</strong><span class="e22-feature-meta">'+esc(item.intro)+'</span>'
        +'<span>'+esc(item.description)+'</span>'
        +'<span class="e22-feature-terms">Capacité en '+metric+'</span>'
        +'<span class="e22-feature-bottom">Accessible à votre organisation <b>Ouvrir →</b></span></span></button>'
      ).join('')+'</div>';
    }

    function clientOrders(){
      const orders=state.checkoutOrders||[];
      if(!orders.length)return '';
      const badge={pending:'Paiement en attente',paid:'Payé et confirmé',failed:'Paiement non validé',canceled:'Annulé'};
      return ctx.panel('Mes achats et accès','Les abonnements sont activés uniquement après vérification du paiement.',
        rowTable(orders.slice(0,12).map(o=>
          '<tr><td>'+esc(o.offer_name)+'</td>'
          +'<td>'+esc(terms[o.term_months]||o.term_months)+' · '+esc(o.capacity)+' '+unit(o)+'</td>'
          +'<td>'+cash(o)+'</td>'
          +'<td>'+pill(badge[o.status]||o.status,o.status!=='paid')+'</td>'
          +'<td>'+(o.status==='pending'
            ?'<button type="button" class="e22-button subtle" data-sub-action="verify-checkout" data-transaction-id="'+esc(o.transaction_id)+'">Vérifier mon paiement</button>'
              +(o.checkout_url?' <a class="e22-button subtle e27-checkout-return" href="'+esc(o.checkout_url)+'" target="_blank" rel="noopener noreferrer">Reprendre</a>':'')
            :(o.status==='paid'&&o.access_url
              ?'<a href="'+esc(o.access_url)+'" class="e22-button subtle">Accéder à mon espace →</a>':'—'))
          +'</td></tr>'
        ),['Forfait','Durée & capacité','Montant','Paiement','Accès'])
      );
    }

    function clientCheckoutDialog(){
      const prices=(state.catalog||[]).filter(o=>o.is_active).flatMap(o=>
        (o.prices||[]).filter(p=>p.is_active).map(p=>({offer:o,price:p})),
      ).filter(row=>[1,6,12].includes(row.price.term_months)&&row.price.amount!==null)
       .sort((a,b)=>a.price.term_months-b.price.term_months||a.price.seats-b.price.seats);
      const chosen=prices.find(row=>Number(row.price.id)===Number(state.selectedCheckoutPriceId))||prices[0];
      const isEnterprise=state.mine?.organisation_type==='enterprise';
      const tiles=prices.map(({offer,price})=>{
        const active=chosen&&chosen.price.id===price.id;
        return '<button type="button" class="e27-plan-option'+(active?' active':'')+'" aria-pressed="'+(!!active)+'"'
          +' data-sub-action="select-checkout-price" data-id="'+esc(price.id)+'">'
          +'<span class="e27-plan-name">'+esc(offer.name)+'</span>'
          +'<span class="e27-plan-term">'+esc(terms[price.term_months])+'</span>'
          +'<strong>'+esc(price.seats)+' '+(isEnterprise?'publications':'comptes actifs')+'</strong>'
          +'<span class="e27-plan-amount">'+cash(price)+'</span></button>';
      }).join('');
      const config=state.checkout||{};
      return '<dialog class="e27-client-dialog" aria-labelledby="e27-client-dialog-title">'
        +'<div class="e22-dialog-frame"><div class="e22-dialog-head">'
        +'<span class="e22-dialog-glyph" aria-hidden="true">▤</span>'
        +'<div class="e22-dialog-title"><span class="e22-label">'+(isEnterprise?'ENTREPRISES · PUBLICATIONS':'ÉTABLISSEMENTS · COMPTES ACTIFS')+'</span>'
        +'<h2 id="e27-client-dialog-title">Choisir un forfait</h2>'
        +'<p>Sélectionnez votre capacité et la durée souhaitée, puis validez le paiement.</p></div>'
        +'<button class="e22-dialog-close" type="button" data-sub-action="client-close" aria-label="Fermer la fenêtre">✕</button></div>'
        +'<div class="e22-dialog-content">'
        +'<div class="e27-checkout-columns"><section><div class="e22-section-heading"><h2>Offres disponibles</h2><span class="e22-label">1 · 6 · 12 mois</span></div>'
        +'<div class="e27-plan-options">'+(tiles||empty('Aucun forfait en ligne actuellement. Envoyez une demande de réabonnement.'))+'</div>'
        +'<p class="e22-history">Les offres sur devis nécessitent une demande auprès de G-Connect.</p>'
        +'</section><aside class="e27-checkout-summary">'
        +'<span class="e22-label">RÉCAPITULATIF</span><h3>'+esc(chosen?.offer.name||'Sélectionnez une offre')+'</h3>'
        +(chosen?'<div class="e27-summary-line"><span>Durée</span><strong>'+esc(terms[chosen.price.term_months])+'</strong></div>'
          +'<div class="e27-summary-line"><span>Capacité</span><strong>'+esc(chosen.price.seats)+' '+(isEnterprise?'publications':'comptes actifs')+'</strong></div>'
          +'<div class="e27-summary-total"><span>Montant du forfait</span><strong>'+cash(chosen.price)+'</strong></div>'
          +'<p>Le montant est fixé par le Superadmin. Le paiement s’effectue sur une page sécurisée du prestataire.</p>'
          :'<p>Les tarifs publiés apparaîtront dans cette fenêtre.</p>')
        +(state.checkoutError?'<p class="e22-notice e22-error">'+esc(state.checkoutError)+'</p>':'')
        +(!config.enabled?'<div class="e27-payment-unavailable">Paiement direct non encore activé. Vous pouvez envoyer une demande au Superadmin.</div>':'')
        +'<button type="button" class="e22-button e27-pay-button" data-sub-action="start-checkout"'
        +(!chosen||!config.enabled||state.busy?' disabled':'')+'>Payer en ligne avec CinetPay →</button>'
        +'<button type="button" class="e22-button subtle" data-sub-action="client-switch-request">Envoyer une demande à la place</button>'
        +'<p class="e27-pay-hint">Aucune carte ou donnée bancaire n’est saisie dans G-Connect. Un forfait n’est activé qu’après confirmation par le prestataire.</p>'
        +'</aside></div></div></div></dialog>';
    }

    function clientRequestDialog(){
      const isEnterprise=state.mine?.organisation_type==='enterprise';
      return '<dialog class="e27-client-dialog" aria-labelledby="e27-client-dialog-title">'
        +'<div class="e22-dialog-frame"><div class="e22-dialog-head">'
        +'<span class="e22-dialog-glyph" aria-hidden="true">▥</span>'
        +'<div class="e22-dialog-title"><span class="e22-label">'+(isEnterprise?'ENTREPRISES · PUBLICATIONS':'ÉTABLISSEMENTS · COMPTES ACTIFS')+'</span>'
        +'<h2 id="e27-client-dialog-title">Demandes de réabonnement</h2>'
        +'<p>Envoyez une demande ou consultez sa réponse, sans paiement automatique.</p></div>'
        +'<button type="button" class="e22-dialog-close" data-sub-action="client-close" aria-label="Fermer la fenêtre">✕</button></div>'
        +'<div class="e22-dialog-content">'+clientRequestsPanel(state.mine?.current)+'</div></div></dialog>';
    }

    function clientPage(){
      if(!state.loaded)return ctx.intro('Abonnement','Votre contrat et les offres proposées par G-Connect.')+empty('Chargement des abonnements…');
      const subscription=state.mine&&state.mine.current;
      const current=subscription
        ?'<div class="e22-card"><div class="e22-topline">'+pill('Abonnement actif')+'<span class="e22-label">'+esc(subscription.kind)+'</span></div><h2>'+esc(subscription.offer_name)+'</h2>'
          +'<p>'+quotaText(subscription)+' inclus · '+esc(terms[subscription.term_months]||'Sur devis')+'</p>'
          +quotaOverview(subscription)
          +rowTable([
            '<tr><td>Montant convenu</td><td colspan="2"><strong>'+cash(subscription)+'</strong></td></tr>',
            '<tr><td>Début</td><td colspan="2">'+esc(subscription.starts_at)+'</td></tr>',
            '<tr><td>Échéance</td><td colspan="2">'+esc(subscription.ends_at)+'</td></tr>',
          ],['Votre contrat','', ''])+'</div>'
        :'<div class="e22-notice">Aucun abonnement actif pour cette organisation. Sélectionnez un forfait ou envoyez une demande de réabonnement.</div>';
      const cards=(state.catalog||[]).map(o=>offerCard(o,false)).join('');
      const history=state.mine&&Array.isArray(state.mine.history)?state.mine.history:[];
      return ctx.intro('Abonnement','Découvrez vos capacités et les offres configurées par G-Connect.')
        +message()+current+clientActionTiles()+'<div class="e27-client-catalog"><div class="e22-section-heading"><h2>Offres proposées</h2><span class="e22-label">Tarifs décidés par le Superadmin</span></div>'
        +'<div class="e22-grid">'+(cards||empty('Aucune offre disponible actuellement.'))+'</div></div>'
        +clientOrders()+institutionSeats()
        +ctx.panel('Historique','Conditions réellement attribuées à votre organisation.',
          history.length?rowTable(history.map(s=>'<tr><td>'+esc(s.offer_name)+'</td><td>'+quotaText(s)+'</td><td>'+esc(s.ends_at)+'</td><td>'+pill(statusText(s.status),s.status!=='active')+'</td></tr>'),['Offre','Capacité','Échéance','État']):empty('Aucun abonnement précédent.'))
        +'<div class="e22-actions"><button type="button" class="e22-button subtle" data-sub-action="refresh">Actualiser ma consommation</button></div>'
        +'<p class="e22-history">Les fonctionnalités dépendent de votre contrat actif. Un lien vers votre espace nécessite toujours une connexion sécurisée.</p>'
        +(state.clientDialog==='checkout'?clientCheckoutDialog():state.clientDialog==='request'?clientRequestDialog():'');
    }


    const requestStatus=status=>({
      pending:'En attente',info_requested:'Précisions demandées',
      approved:'Accord de principe',rejected:'Refusée',
    })[status]||status;
    const requestType=type=>type==='renewal'?'Renouvellement':'Capacité supplémentaire';
    const requestQuantity=item=>item.request_type==='renewal'
      ?esc(terms[item.requested_term_months]||'Sur devis')
      :'+'+esc(item.requested_quantity)+' '+(item.organisation_type==='enterprise'?'publications':'comptes');
    function requestPanel(scope){
      const list=(state.requests||[]).filter(item=>item.organisation_type===scope);
      const pending=list.filter(item=>item.status==='pending');
      const urgent=pending.filter(item=>{
        if(!item.current_ends_at)return false;
        const days=(new Date(item.current_ends_at+'T12:00:00').getTime()-Date.now())/86400000;
        return days>=0&&days<=7;
      });
      const handled=list.filter(item=>item.status==='approved'||item.status==='rejected');
      const tabs=[
        ['all','Toutes'],['renewal','Renouvellements'],
        ['capacity','Capacité supplémentaire'],['history','Historique'],
      ];
      const visible=list.filter(item=>
        state.requestFilter==='all'
        ||(state.requestFilter==='history'?['approved','rejected'].includes(item.status)
        :item.request_type===state.requestFilter)
      );
      const shown=state.expandedRequests?visible:visible.slice(0,4);
      const rows=shown.map(item=>{
        const badge='e26-request-status '+(item.status==='pending'?'pending':item.status==='approved'?'accepted':item.status==='rejected'?'rejected':'more');
        return '<div class="e26-request-row"><div class="e26-request-row-main">'
          +'<span class="e26-request-org">'+esc(item.organisation_name)+'</span>'
          +'<span class="e26-request-meta">'+esc(requestType(item.request_type))+' · '+requestQuantity(item)+'</span>'
          +'<span class="e26-request-date">'+esc(String(item.created_at||'').slice(0,10))+'</span>'
          +'</div><span class="'+badge+'">'+esc(requestStatus(item.status))+'</span>'
          +'<button type="button" class="e26-review-button" data-sub-action="review-request" data-id="'+esc(item.id)+'">Examiner →</button></div>';
      }).join('');
      return '<section class="e26-requests" aria-label="Demandes commerciales">'
        +'<div class="e26-requests-heading"><div><span class="e22-label">CENTRE DE DEMANDES</span>'
        +'<h3>Renouvellements & extensions</h3>'
        +'<p>Décisions tracées, sans facturation automatique.</p></div>'
        +'<span class="e26-live-indicator" aria-hidden="true">●</span></div>'
        +'<div class="e26-request-stats">'
        +'<div><strong>'+esc(list.length)+'</strong><span>Reçues</span></div>'
        +'<div><strong>'+esc(pending.length)+'</strong><span>En attente</span></div>'
        +'<div><strong>'+esc(urgent.length)+'</strong><span>Proches échéance</span></div>'
        +'</div>'
        +(state.requestError?'<p class="e22-notice e22-error" role="alert">'+esc(state.requestError)+'</p>':'')
        +'<div class="e26-request-tabs" role="group" aria-label="Filtrer les demandes">'
        +tabs.map(t=>'<button type="button" class="'+(state.requestFilter===t[0]?'active':'')+'" data-sub-action="request-filter" data-filter="'+t[0]+'" aria-pressed="'+(state.requestFilter===t[0])+'">'+t[1]+'</button>').join('')
        +'</div><div class="e26-request-list">'
        +(rows||'<div class="e26-request-empty"><span aria-hidden="true">◫</span><strong>Aucune demande à afficher</strong><p>Les nouvelles demandes apparaîtront ici après leur envoi.</p></div>')
        +'</div>'
        +(visible.length>4?'<button type="button" class="e26-request-more" data-sub-action="request-more">'+(state.expandedRequests?'Afficher moins':'Voir toutes les demandes ('+visible.length+')')+' →</button>':'')
        +'<p class="e26-requests-footnote">'+esc(handled.length)+' demande(s) traitée(s) · Les approbations restent à activer manuellement.</p>'
        +'</section>';
    }
    function reviewRequestDialog(){
      const item=(state.requests||[]).find(i=>i.id===state.reviewRequestId);
      if(!item)return '';
      const canReview=item.status==='pending'||item.status==='info_requested';
      const mark='<strong>'+esc(item.organisation_name)+'</strong>';
      return '<dialog class="e26-review-dialog" aria-labelledby="e26-review-title">'
        +'<div class="e26-review-head"><div><span class="e22-label">EXAMEN DE DEMANDE</span><h3 id="e26-review-title">'+esc(requestType(item.request_type))+'</h3></div>'
        +'<button type="button" class="e22-dialog-close" data-sub-action="close-review" aria-label="Fermer les détails">✕</button></div>'
        +'<div class="e26-review-body"><p class="e26-review-org">'+mark+'</p>'
        +'<dl class="e26-review-data">'
        +'<div><dt>Type</dt><dd>'+esc(requestType(item.request_type))+'</dd></div>'
        +'<div><dt>Demande</dt><dd>'+requestQuantity(item)+'</dd></div>'
        +'<div><dt>Statut</dt><dd>'+esc(requestStatus(item.status))+'</dd></div>'
        +'<div><dt>Contrat de référence</dt><dd>'+(item.source_subscription_id?'N° '+esc(item.source_subscription_id):'Aucun abonnement actif')+'</dd></div>'
        +'<div><dt>Offre actuelle</dt><dd>'+esc(item.current_offer_name||'—')+'</dd></div>'
        +'<div><dt>Consommation actuelle</dt><dd>'+(item.current_quota?esc(item.current_quota.used)+' / '+esc(item.current_quota.limit)+' '+(item.organisation_type==='enterprise'?'publications':'comptes actifs'):'—')+'</dd></div>'
        +'<div><dt>Échéance actuelle</dt><dd>'+esc(item.current_ends_at||'—')+'</dd></div>'
        +'<div><dt>Demande envoyée</dt><dd>'+esc(String(item.created_at||'').slice(0,10))+'</dd></div>'
        +'</dl>'
        +'<div class="e26-review-note"><span>Message du client</span><p>'+esc(item.note||'Aucun commentaire.')+'</p></div>'
        +(item.admin_note?'<div class="e26-review-note"><span>Dernière réponse</span><p>'+esc(item.admin_note)+'</p></div>':'')
        +(canReview?'<label class="e22-field"><span>Réponse au client (obligatoire pour une demande de précisions ou un refus)</span>'
          +'<textarea name="admin_note" maxlength="500" rows="3" placeholder="Votre message…"></textarea></label>'
          +'<div class="e26-review-actions">'
          +'<button type="button" class="e22-button" data-sub-action="review-decision" data-status="approved">Accord de principe</button>'
          +'<button type="button" class="e22-button subtle" data-sub-action="review-decision" data-status="info_requested">Demander des précisions</button>'
          +'<button type="button" class="e22-button danger" data-sub-action="review-decision" data-status="rejected">Refuser</button>'
          +'</div>':'<p class="e22-notice">Décision enregistrée, aucune modification automatique du contrat.</p>')
        +'<p class="e26-review-disclaimer">Une décision favorable n’est pas un règlement. Pour donner suite, utilisez « Attribuer un abonnement » ou « Ajouter de la capacité » ci-dessous.</p>'
        +'</div></dialog>';
    }

    function adminPage(){
      if(!state.loaded)return ctx.intro('Offres & abonnements','Gestion commerciale G-Connect.')+empty('Chargement des tarifs…');
      const scope=state.selectedAudience;
      const tiles=[
        {audience:'enterprise',title:'Offres Entreprise',meta:'Publications consommées',description:'Crédits de publication non remboursables, valables pendant la durée du contrat.',icon:'▤'},
        {audience:'institution',title:'Offres Établissement',meta:'Comptes actifs',description:'Capacité simultanée : désactiver un compte libère une place.',icon:'▥'},
      ];
      const tileMarkup=tiles.map(item=>{
        const offers=(state.offers||[]).filter(o=>o.audience===item.audience);
        const prices=offers.flatMap(o=>o.prices||[]).filter(p=>p.is_active);
        const selected=scope===item.audience;
        return '<button type="button" class="e22-feature'+(selected?' selected':'')+'" data-sub-action="scope" data-audience="'+item.audience+'" aria-pressed="'+selected+'">'
          +'<span class="e22-feature-icon" aria-hidden="true">'+item.icon+'</span><span class="e22-feature-content"><span class="e22-label">'+audienceLabel(item.audience)+'</span>'
          +'<strong>'+item.title+'</strong><span class="e22-feature-meta">'+item.meta+'</span><span>'+item.description+'</span>'
          +'<span class="e22-feature-terms">1 mois <b>·</b> 6 mois <b>·</b> 12 mois <b>·</b> sur devis</span>'
          +'<span class="e22-feature-bottom">'+prices.length+' tarif(s) disponible(s) <b>'+(selected?'Configuration ouverte':'Configurer →')+'</b></span>'
          +'</span></button>';
      }).join('');
      const allOffers=state.offers||[];
      const activeOffers=allOffers.filter(o=>o.is_active).length;
      const activePrices=allOffers.reduce((count,o)=>count+(o.prices||[]).filter(p=>p.is_active).length,0);
      const activeContracts=(state.assignments||[]).filter(s=>s.status==='active').length;
      const pendingRequests=(state.requests||[]).filter(r=>r.status==='pending'||r.status==='info_requested').length;
      const metric=(label,value,detail,kind)=>'<div class="e55-metric e55-metric-'+kind+'"><span class="e55-metric-symbol" aria-hidden="true">'+({offers:'◇',prices:'▤',contracts:'◎',requests:'↗'}[kind])+'</span>'
        +'<span class="e55-metric-label">'+label+'</span><strong>'+esc(value)+'</strong><small>'+detail+'</small></div>';
      const header='<section class="e55-commercial-hero" aria-label="Pilotage des abonnements">'
        +'<div class="e55-hero-copy"><span class="e55-kicker">STRATÉGIE COMMERCIALE · G-CONNECT</span>'
        +'<h1>Offres <em>&</em> abonnements</h1>'
        +'<p>Configurez les formules du réseau et pilotez les capacités attribuées aux entreprises et aux établissements.</p>'
        +'<span class="e55-trust">◇ Tarification historisée · Quotas contrôlés côté serveur</span></div>'
        +'<div class="e55-hero-visual" aria-hidden="true"><div class="e55-orbit e55-orbit-outer"></div><div class="e55-orbit e55-orbit-inner"></div>'
        +'<div class="e55-core"><span>▤</span></div><span class="e55-satellite e55-sat-a">◇</span><span class="e55-satellite e55-sat-b">◈</span><span class="e55-satellite e55-sat-c">↗</span>'
        +'<span class="e55-visual-caption">OFFRES · CAPACITÉS · CONTRATS</span></div></section>'
        +message()
        +'<div class="e55-metrics" aria-label="Indicateurs commerciaux">'
        +metric('Offres actives',activeOffers,'Dans le catalogue','offers')
        +metric('Tarifs disponibles',activePrices,'Formules en vigueur','prices')
        +metric('Contrats actifs',activeContracts,'Attributions en cours','contracts')
        +metric('Demandes à traiter',pendingRequests,'En attente ou à préciser','requests')+'</div>'
        +'<div class="e55-portfolio-heading"><div><span class="e55-kicker">CATALOGUE COMMERCIAL</span><h2>Deux modèles, un même réseau</h2></div>'
        +'<p>Choisissez une catégorie pour ouvrir sa configuration détaillée.</p></div>'
        +'<div class="e22-feature-grid">'+tileMarkup+'</div>'
        +'<p class="e55-policy">Les contrats existants conservent leurs montants. Une attribution manuelle ne constitue ni un paiement ni une facture.</p>';
      if(!scope)return header+'<p class="e22-history">Sélectionnez un bloc pour configurer ses durées, ses quotas, ses prix et ses abonnements.</p>';
      const offers=(state.offers||[]).filter(o=>o.audience===scope||o.audience==='all'&&(o.quota_unit||'accounts')===(scope==='enterprise'?'publications':'accounts'));
      const unitLabel=scope==='enterprise'?'publications':'comptes actifs';
      const options=offers.filter(o=>o.is_active).flatMap(o=>(o.prices||[]).filter(p=>p.is_active).map(p=>({p,offer:o})));
      const orgs=scope==='enterprise'
        ?(state.organisations.enterprises||[]).map(o=>({key:'enterprise:'+o.id,label:'Entreprise · '+o.company_name}))
        :(state.organisations.institutions||[]).map(o=>({key:'institution:'+o.id,label:'Établissement · '+o.name}));
      const selects=options.map(({p,offer})=>'<option value="'+esc(p.id)+'">'+esc(offer.name)+' · '+quotaText(p)+' · '+esc(terms[p.term_months])+' · '+cash(p)+'</option>').join('');
      const orgOptions=orgs.map(o=>'<option value="'+esc(o.key)+'">'+esc(o.label)+'</option>').join('');
      const offerOptions=offers.map(o=>'<option value="'+esc(o.id)+'">'+esc(o.name)+'</option>').join('');
      const form=(key,title,fields,button)=>'<article class="e22-card"><h2>'+title+'</h2><form class="e22-layout-form" data-sub-form="'+key+'"><div class="e22-fields">'+fields+'</div><div class="e22-actions"><button class="e22-button" type="submit"'+(state.busy?' disabled':'')+'>'+button+'</button></div></form></article>';
      const field=(label,name,type,props='')=>'<label class="e22-field"><span>'+label+'</span><input name="'+name+'" type="'+type+'" '+props+'></label>';
      const select=(label,name,options)=>'<label class="e22-field"><span>'+label+'</span><select name="'+name+'" required>'+options+'</select></label>';
      const offerForm=form('offer','Créer une offre',
        field('Nom','name','text','required maxlength="150" placeholder="Offre Partenariat"')
        +field('Identifiant (lettres minuscules et tirets)','slug','text','required pattern="[a-z0-9][a-z0-9-]+" placeholder="offre-partenariat"')
        +(scope==='enterprise'
          ? '<input type="hidden" name="kind" value="flexible"><label class="e22-field"><span>Modèle</span><input type="text" value="Offre Publications" readonly aria-label="Modèle de publication"></label>'
          : select('Modèle','kind','<option value="flexible">Offre Flexible</option><option value="per_account">Offre par compte</option>'))
        +'<input type="hidden" name="audience" value="'+scope+'"><input type="hidden" name="quota_unit" value="'+(scope==='enterprise'?'publications':'accounts')+'">'
        +field('Description (facultative)','description','text','maxlength="500"'),
        'Créer l’offre');
      const editForm=form('edit-offer','Modifier une offre',
        select('Offre existante','offer_id',offerOptions)
        +field('Nouveau nom (facultatif)','name','text','maxlength="150"')
        +field('Nouvelle description (facultative)','description','text','maxlength="500"'),
        'Enregistrer les changements');
      const priceForm=form('price','Fixer ou modifier un prix',
        select('Offre','offer_id',offerOptions)
        +select('Durée','term_months','<option value="1">1 mois</option><option value="6">6 mois</option><option value="12">12 mois</option><option value="0">Sur devis</option>')
        +field('Nombre de '+unitLabel,'capacity','number','required min="1" step="1" value="'+(scope==='enterprise'?'20':'200')+'"')
        +field('Montant (laisser vide pour sur devis)','amount','number','min="0" step="0.01" placeholder="Ex. 150000"')
        +field('Devise ISO','currency','text','maxlength="3" pattern="[A-Za-z]{3}" value="XOF" required'),
        'Enregistrer le tarif');
      const assignmentForm=form('assignment','Attribuer un abonnement',
        select('Organisation','organisation',orgOptions)
        +select('Prix configuré','price_option_id',selects)
        +field('Début (vide = aujourd’hui)','starts_at','date','')
        +field('Montant négocié (sur devis)','quoted_amount','number','step="0.01" min="0" placeholder="Sur devis uniquement"')
        +field('Fin (sur devis)','ends_at','date',''),
        'Activer manuellement');
      const history=(state.assignments||[]).filter(s=>scope==='enterprise'?Boolean(s.enterprise_id):Boolean(s.institution_id));
      const running=history.filter(s=>s.status==='active');
      const topUpOptions=running.map(s=>'<option value="'+esc(s.id)+'">'+esc(s.organisation_name)+' · '+esc(s.offer_name)+'</option>').join('');
      const topUpForm=form('topup','Ajouter de la capacité',
        select('Abonnement actif','subscription_id',topUpOptions)
        +field('Crédits / places supplémentaires','quantity','number','required min="1" step="1" placeholder="Ex. 10"')
        +field('Montant convenu','amount','number','required min="0" step="0.01" value="0"')
        +field('Motif (facultatif)','note','text','maxlength="255" placeholder="Complément de quota"'),
        'Ajouter au contrat');
      const assignmentRows=history.map(s=>'<tr><td>'+esc(s.organisation_name)+'</td><td>'+esc(s.offer_name)+'</td><td>'+quotaText(s)+'</td><td>'+esc(s.quota?s.quota.used+' / '+s.quota.limit:'—')+'</td><td>'+cash(s)+'</td><td>'+pill(statusText(s.status),s.status!=='active')+'</td><td>'
        +(s.status==='active'?'<button type="button" class="e22-button danger" data-sub-action="suspend" data-id="'+esc(s.id)+'">Suspendre</button>':'—')+'</td></tr>');
      // Keep the overview as the primary page: scoped configuration opens in
      // one native, accessible modal without changing the existing API actions.
      return header
        +'<dialog class="e22-dialog" aria-labelledby="e22-dialog-title" aria-describedby="e22-dialog-description">'
        +'<div class="e22-dialog-frame">'
        +'<div class="e22-dialog-head"><span class="e22-dialog-glyph" aria-hidden="true">'+(scope==='enterprise'?'▤':'▥')+'</span>'
        +'<div class="e22-dialog-title"><span class="e22-label">'+audienceLabel(scope)+'</span><h2 id="e22-dialog-title">Configuration · '+audienceLabel(scope)+'</h2>'
        +'<p id="e22-dialog-description">'+(scope==='enterprise'?'Gérez les publications, les tarifs et les contrats des entreprises.':'Gérez les comptes actifs, les tarifs et les contrats des établissements.')+'</p></div>'
        +'<button class="e22-dialog-close" type="button" data-sub-action="back" aria-label="Fermer la configuration">✕</button></div>'
        +'<div class="e22-dialog-content">'
        +message()
        +'<div class="e26-config-top">'
        +'<section class="e26-offers" aria-label="Offres et tarifs"><div class="e22-section-heading"><h2>Offres & tarifs · '+unitLabel+'</h2><span class="e22-label">1 · 6 · 12 mois · Sur devis</span></div>'
        +'<div class="e26-offer-list">'+(offers.map(o=>offerCard(o,true)).join('')||empty('Créez votre première offre.'))+'</div></section>'
        +requestPanel(scope)+'</div>'
        +'<div class="e22-section-heading e26-config-heading"><h2>Gestion des offres et contrats</h2><span class="e22-label">Paramétrage · manuel</span></div>'
        +'<div class="e22-grid">'+offerForm+editForm+priceForm+assignmentForm+topUpForm+'</div>'
        +ctx.panel('Abonnements attribués','Les 100 dernières attributions, avec leur état réel.',
          history.length?rowTable(assignmentRows,['Organisation','Offre','Capacité','Utilisé','Prix convenu','Statut','Action']):empty('Aucune attribution enregistrée.'))
        +'<p class="e22-history">Une nouvelle version du tarif ne modifie jamais un contrat déjà attribué. Les packs complémentaires sont enregistrés séparément.</p>'
        +'</div>'+reviewRequestDialog()+'</div></dialog>';
    }

    async function submit(form){
      if(state.busy)return;
      state.busy=true;
      const data=new FormData(form),field=name=>String(data.get(name)||'').trim();
      try{
        switch(form.dataset.subForm){
          case 'renewal-request':
            await api.subscriptionCreateRequest({
              request_type:'renewal',requested_term_months:Number(field('requested_term_months')),
              note:field('note'),
            });break;
          case 'capacity-request':
            await api.subscriptionCreateRequest({
              request_type:'capacity',requested_quantity:Number(field('requested_quantity')),
              note:field('note'),
            });break;
          case 'offer':
            await api.pricingCreateOffer({
              name:field('name'),slug:field('slug'),
              kind:field('kind'),audience:field('audience'),
              quota_unit:field('quota_unit'),description:field('description'),
            });break;
          case 'edit-offer':{
            const changes={};
            for(const name of ['name','description']){
              if(field(name))changes[name]=field(name);
            }
            if(!Object.keys(changes).length)throw new Error('Indiquez au moins un changement.');
            await api.pricingUpdateOffer(Number(field('offer_id')),changes);
            break;
          }
          case 'price':
            await api.pricingSetPrice({
              offer_id:Number(field('offer_id')),term_months:Number(field('term_months')),
              capacity:Number(field('capacity')),amount:field('amount')||null,
              currency:field('currency')||'XOF',
            });break;
          case 'assignment':{
            const [type,id]=field('organisation').split(':');
            const payload={price_option_id:Number(field('price_option_id'))};
            if(type==='enterprise')payload.enterprise_id=Number(id);
            else if(type==='institution')payload.institution_id=Number(id);
            if(field('starts_at'))payload.starts_at=field('starts_at');
            if(field('quoted_amount'))payload.quoted_amount=field('quoted_amount');
            if(field('ends_at'))payload.ends_at=field('ends_at');
            await api.pricingAssign(payload);break;
          }
          case 'topup':
            await api.pricingAddCapacity(Number(field('subscription_id')),{
              quantity:Number(field('quantity')),amount:field('amount'),note:field('note'),
            });break;
          default:throw new Error('Formulaire inconnu.');
        }
        state.error='';ctx.notify('Modification enregistrée sur le serveur.');
        await load();
      }catch(error){state.error=error.message||'Modification impossible.';ctx.notify(state.error)}
      finally{state.busy=false;ctx.render()}
    }

    async function action(button){
      if(button.dataset.subAction==='client-open'){
        state.clientDialog=button.dataset.clientView==='checkout'?'checkout':'request';
        state.checkoutError='';
        ctx.render();return;
      }
      if(button.dataset.subAction==='client-close'){
        state.clientDialog=null;ctx.render();return;
      }
      if(button.dataset.subAction==='client-switch-request'){
        state.clientDialog='request';ctx.render();return;
      }
      if(button.dataset.subAction==='select-checkout-price'){
        state.selectedCheckoutPriceId=Number(button.dataset.id);
        ctx.render();return;
      }
      if(button.dataset.subAction==='start-checkout'){
        if(state.busy||!state.checkout?.enabled)return;
        const rows=(state.catalog||[]).filter(o=>o.is_active).flatMap(o=>
          (o.prices||[]).filter(p=>p.is_active&&[1,6,12].includes(p.term_months)&&p.amount!==null)
          .map(p=>p));
        const selected=rows.find(p=>p.id===Number(state.selectedCheckoutPriceId))||rows[0];
        if(!selected){ctx.notify('Sélectionnez un forfait disponible.');return;}
        state.busy=true;
        try{
          const data=await api.subscriptionCheckoutStart(Number(selected.id));
          const url=new URL(String(data.checkout_url||''));
          if(url.protocol!=='https:'||url.hostname!=='checkout.cinetpay.com'){
            throw new Error('Le fournisseur a retourné une adresse non autorisée.');
          }
          state.checkoutError='';
          // The professional dashboard may be hosted inside our own iframe.
          // Leave that frame: hosted bank checkouts must run in the top-level tab.
          const target=typeof window!=='undefined'?(window.top||window):null;
          if(target?.location&&typeof target.location.assign==='function'){
            target.location.assign(url.href);
          }else{
            ctx.notify('Lien de paiement créé. Ouvrez le prestataire depuis votre navigateur.');
          }
        }catch(error){
          state.checkoutError=error.message||'Paiement momentanément indisponible.';
          ctx.notify(state.checkoutError);
        }finally{state.busy=false;ctx.render()}
        return;
      }
      if(button.dataset.subAction==='verify-checkout'){
        if(state.busy)return;
        const transactionId=String(button.dataset.transactionId||'');
        if(!/^[0-9a-f-]{36}$/i.test(transactionId))return;
        state.busy=true;
        try{
          const result=await api.subscriptionCheckoutVerify(transactionId);
          ctx.notify(result.status==='paid'?'Paiement confirmé, votre abonnement est enregistré.':'Paiement en attente de confirmation.');
          await load();
        }catch(error){ctx.notify(error.message||'Vérification impossible.');}
        finally{state.busy=false;ctx.render()}
        return;
      }
      if(button.dataset.subAction==='scope'){
        state.selectedAudience=button.dataset.audience;ctx.render();return;
      }
      if(button.dataset.subAction==='back'){
        const audience=state.selectedAudience;
        state.selectedAudience=null;
        ctx.render();
        // Restore keyboard focus to the tile that opened the native dialog.
        if(typeof document!=='undefined' && (audience==='enterprise'||audience==='institution')){
          document.querySelector('[data-sub-action="scope"][data-audience="'+audience+'"]')?.focus();
        }
        return;
      }
      if(button.dataset.subAction==='request-filter'){
        state.requestFilter=button.dataset.filter;
        state.expandedRequests=false;
        ctx.render();return;
      }
      if(button.dataset.subAction==='request-more'){
        state.expandedRequests=!state.expandedRequests;
        ctx.render();return;
      }
      if(button.dataset.subAction==='review-request'){
        const id=Number(button.dataset.id);
        if(!(state.requests||[]).some(item=>item.id===id))return;
        state.reviewRequestId=id;
        ctx.render();return;
      }
      if(button.dataset.subAction==='close-review'){
        state.reviewRequestId=null;ctx.render();return;
      }
      if(button.dataset.subAction==='review-decision'){
        if(state.busy||!state.reviewRequestId)return;
        const note=typeof document!=='undefined'
          ?String(document.querySelector('.e26-review-dialog [name="admin_note"]')?.value||'').trim()
          :'';
        const status=button.dataset.status;
        if((status==='rejected'||status==='info_requested')&&!note){
          ctx.notify('Précisez le motif de cette décision.');return;
        }
        state.busy=true;
        try{
          await api.pricingReviewRequest(state.reviewRequestId,{status,admin_note:note});
          state.reviewRequestId=null;
          state.error='';
          ctx.notify('Décision enregistrée. Le contrat reste inchangé jusqu’à son activation manuelle.');
          await load();
        }catch(error){ctx.notify(error.message||'Décision impossible.')}
        finally{state.busy=false;ctx.render()}
        return;
      }
      if(button.dataset.subAction==='refresh'){
        await load();return;
      }
      if(state.busy)return;
      state.busy=true;
      try{
        const id=Number(button.dataset.id);
        if(button.dataset.subAction==='toggle'){
          await api.pricingUpdateOffer(id,{is_active:button.dataset.active==='true'});
        }else if(button.dataset.subAction==='retire-price'){
          if(!window.confirm('Retirer ce tarif du catalogue ? Les contrats existants conserveront leur prix.'))return;
          await api.pricingRetirePrice(id);
        }else if(button.dataset.subAction==='suspend'){
          if(!window.confirm('Suspendre cet abonnement ? Le client ne bénéficiera plus des droits de cet abonnement.'))return;
          await api.pricingUpdateAssignment(id,{status:'suspended'});
        }else if(button.dataset.subAction==='seat'){
          await api.subscriptionSetSeat({
            id,role:button.dataset.role,seat_enabled:button.dataset.enabled==='true',
          });
        }
        state.error='';ctx.notify('Modification enregistrée.');
        await load();
      }catch(error){state.error=error.message||'Modification impossible.';ctx.notify(state.error)}
      finally{state.busy=false;ctx.render()}
    }

    return Object.freeze({load,adminPage,clientPage,submit,action});
  };
})();

