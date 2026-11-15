'use strict';
/* E54: separate, read-only recruiter experience. The API enforces company scope. */
(function(){
  window.GConnectRecruiterE54=function({api,safe,intro,panel,render,go,isVisible}){
    const state={loaded:false,loading:false,loadingApplications:false,error:'',
      offers:[],selected:null,applications:null};
    const array=value=>Array.isArray(value)?value:[];
    const date=value=>{
      const d=new Date(value||'');
      return Number.isFinite(d.valueOf())?d.toLocaleDateString('fr-FR'):'—';
    };
    const name=()=>api.getCurrent()?.stats?.company_name||'Mon entreprise';
    const current=()=>api.getCurrent()?.stats||{};
    const message=()=>state.error?'<div class="e54-message e54-error" role="alert">'+safe(state.error)+'</div>':'';
    const waiting=()=>state.loading?'<div class="e54-placeholder">Chargement des offres autorisées…</div>':'';
    const none=text=>'<div class="e54-empty">'+safe(text)+'</div>';
    const count=(label,n)=>'<article class="e54-metric"><strong>'+safe(String(n??0))+'</strong><span>'+safe(label)+'</span></article>';
    function dashboard(){
      const stats=current();
      return intro('Vue d’ensemble · Recruteur','Espace de recrutement de '+safe(name())+'. Les opérations administratives sont réservées au responsable.')
        +message()+waiting()+'<div class="e54-metrics e54-recruiter-metrics">'+
        count('Offres visibles',stats.opportunities?.total)+count('Candidatures reçues',stats.applications?.total)+
        '</div>'+panel('Accès professionnel','Vos permissions sur G-Connect',
          '<div class="e54-form"><p>Vous pouvez consulter les opportunités de votre entreprise et les candidatures associées.</p>'+
          '<p>Vous ne pouvez pas gérer les abonnements, la facturation, les invitations ni les permissions des autres comptes.</p>'+
          '<button type="button" class="e54-primary" data-route="offers">Parcourir les offres →</button></div>');
    }
    function offers(){
      const cards=state.offers.map(x=>'<article class="e54-offer"><div><strong>'+safe(x.title||'Offre')+
        '</strong><span>'+safe(x.status||'Statut non renseigné')+' · '+date(x.created_at)+'</span></div>'+
        '<button type="button" class="e54-small" data-e54-offer="'+Number(x.id)+'">Candidatures →</button></article>').join('');
      return intro('Offres de l’entreprise','Consultation des opportunités appartenant à '+safe(name())+'.')
        +message()+waiting()+panel('Offres autorisées',String(state.offers.length)+' offre(s)',cards||none('Aucune offre consultable actuellement.'));
    }
    function applications(){
      const chosen=state.offers.find(x=>Number(x.id)===state.selected);
      const buttons=state.offers.map(x=>'<button type="button" class="e54-small" data-e54-select-offer="'+Number(x.id)+'" aria-pressed="'+String(Number(x.id)===state.selected)+'">'+safe(x.title||'Offre')+'</button>').join('');
      const records=array(state.applications).map(x=>'<article class="e54-person"><span class="e54-avatar" aria-hidden="true">◉</span><div><strong>'+safe(x.candidate_name||'Candidat')+'</strong><small>'+date(x.received_at)+'</small></div><span class="e54-status e54-pending">'+safe(x.status||'Soumise')+'</span></article>').join('');
      return intro('Candidatures','Dossiers reçus sur les offres de '+safe(name())+'. Accès en lecture seule.')
        +message()+waiting()+
        panel('Sélectionner une offre','Les candidatures sont isolées par entreprise',
          '<div class="e54-offer-actions">'+(buttons||'Aucune offre disponible.')+'</div>')+
        (chosen?panel('Candidatures · '+safe(chosen.title||'Offre'),
          state.loadingApplications?'Chargement…':String(array(state.applications).length)+' candidature(s)',
          state.loadingApplications?'<div class="e54-placeholder">Chargement des candidatures…</div>':records||none('Aucune candidature reçue pour cette offre.')):'');
    }
    async function loadOffers(){
      if(state.loading||!isVisible())return;
      state.loading=true;state.error='';
      try{
        state.offers=array(await api.enterpriseReadOffers());
        state.loaded=true;
        if(!state.offers.some(x=>Number(x.id)===state.selected))state.selected=state.offers.length?Number(state.offers[0].id):null;
      }catch(error){
        state.loaded=true;state.error=error.message||'Impossible de consulter les offres.';
      }finally{
        state.loading=false;
        if(isVisible())render();
      }
    }
    async function loadApplications(){
      if(state.loadingApplications||state.applications!==null||!Number.isSafeInteger(state.selected)||!isVisible())return;
      state.loadingApplications=true;state.error='';
      try{
        state.applications=array(await api.enterpriseReadOfferApplications(state.selected));
      }catch(error){
        state.applications=[];state.error=error.message||'Candidatures indisponibles.';
      }finally{state.loadingApplications=false;if(isVisible())render();}
    }
    function ensure(route){
      if(!['dashboard','offers','applications'].includes(route))return;
      if(!state.loaded){void loadOffers();return;}
      if(route==='applications'&&state.applications===null)void loadApplications();
    }
    function chooseOffer(id){
      const selected=state.offers.find(o=>Number(o.id)===id);
      if(!selected)return;
      state.selected=id;state.applications=null;
      if(isVisible())go('applications');
    }
    document.addEventListener('click',event=>{
      const btn=event.target.closest?.('[data-e54-offer],[data-e54-select-offer]');
      if(!btn)return;
      const id=Number(btn.dataset.e54Offer||btn.dataset.e54SelectOffer);
      if(!Number.isSafeInteger(id)||id<1)return;
      chooseOffer(id);
    });
    return {pages:{dashboard,offers,applications},ensure};
  };
})();
