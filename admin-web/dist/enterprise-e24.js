'use strict';
/* Enterprise E24: actual scoped API data, never seeded or simulated. */
window.GConnectEnterpriseE24 = function ({api, safe, intro, notify, refresh}) {
  const cache = {offers:null, applications:null, publications:null, contract:null};
  const busy = new Set();
  let quotaLoading=false;
  let notice = '', createOffer = false, createPost = false;
  const statuses = {
    submitted:'Soumise', viewed:'Vue', shortlisted:'Présélectionnée',
    interview:'Entretien', rejected:'Refusée', accepted:'Acceptée',
  };
  const categories = {job:'Emploi',internship:'Stage',training:'Formation',
    apprenticeship:'Alternance',volunteer:'Bénévolat',project:'Projet'};
  const opt=(items,value)=>Object.entries(items).map(([key,label])=>
    '<option value="'+safe(key)+'" '+(value===key?'selected':'')+'>'+safe(label)+'</option>').join('');
  const empty=(title,detail)=>'<div class="e24-empty"><strong>'+safe(title)+'</strong><p>'+safe(detail)+'</p></div>';
  const pill=(label,theme='neutral')=>'<span class="e24-pill e24-'+theme+'">'+safe(label)+'</span>';
  const date=value=>value?new Date(value).toLocaleDateString('fr-FR'):'Non précisée';
  const feedback=()=>notice?'<div class="e24-notice" role="status">'+safe(notice)+'</div>':'';
  const notLoaded=(name)=>empty('Chargement en cours','Récupération de vos '+name+' depuis G-Connect…');
  const formField=(name,label,extra='',type='text')=>'<label class="e24-field"><span>'+label+'</span><input name="'+name+'" type="'+type+'" '+extra+' required></label>';
  const summary=(title,value,subtitle)=>'<article class="e24-metric"><small>'+safe(title)+'</small><strong>'+value+'</strong><span>'+safe(subtitle)+'</span></article>';
  function quotaBanner(){
    const contract=cache.contract?.current;
    const quota=contract?.quota;
    if(cache.contract===null)return '<div class="e24-quota">Chargement de votre abonnement…</div>';
    if(!contract||!quota||quota.unit!=='publications')return '<div class="e24-quota"><strong>Abonnement Publications requis</strong><p>Choisissez une offre avant de publier.</p><button type="button" data-route="subscription">Découvrir les abonnements →</button></div>';
    return '<div class="e24-quota'+(quota.remaining===0?' exhausted':'')+'"><div><strong>'+safe(quota.used)+' / '+safe(quota.limit)+' publications utilisées</strong>'
      +'<p>'+safe(quota.remaining)+' publication(s) restante(s) · échéance '+safe(contract.ends_at)+'</p></div>'
      +'<button type="button" data-route="subscription">'+(quota.remaining===0?'Acheter des crédits ou renouveler →':'Voir mon abonnement →')+'</button></div>';
  }
  async function reloadQuota(){
    if(quotaLoading)return;
    quotaLoading=true;
    try{cache.contract=await api.subscriptionMine();}catch(_){cache.contract=false;}
    finally{quotaLoading=false;refresh();}
  }

  function offers() {
    const rows=cache.offers;
    const heading=intro('Mes offres','Publiez et gérez les opportunités de votre entreprise.');
    const toggle='<button type="button" class="e24-primary" data-e24="toggle-offer">'+(createOffer?'Fermer le formulaire':'+ Nouvelle offre')+'</button>';
    const form=createOffer?'<form class="e24-form" data-e24-form="offer">'
      +'<h3>Publier une opportunité</h3>'
      +formField('title','Intitulé du poste','maxlength="255" minlength="3" placeholder="Ex. Développeur full-stack"')
      +'<label class="e24-field"><span>Description</span><textarea name="description" rows="5" maxlength="5000" placeholder="Décrivez la mission et les compétences recherchées"></textarea></label>'
      +'<div class="e24-form-grid"><label class="e24-field"><span>Catégorie</span><select name="category">'+opt(categories,'job')+'</select></label>'
      +'<label class="e24-field"><span>Type de contrat</span><select name="contract_type">'+opt({permanent:'CDI',fixed_term:'CDD',internship:'Stage',apprenticeship:'Alternance',freelance:'Freelance',volunteer:'Bénévolat'},'permanent')+'</select></label>'
      +'<label class="e24-field"><span>Mode de travail</span><select name="work_mode">'+opt({onsite:'Sur site',hybrid:'Hybride',remote:'À distance'},'onsite')+'</select></label>'
      +formField('location_city','Ville','placeholder="Ex. Dakar"')
      +'<label class="e24-field"><span>Durée (mois, pour stage ou alternance)</span><input name="duration_months" type="number" min="1" max="120" placeholder="Ex. 6"></label>'
      +'<label class="e24-field"><span>Date limite</span><input name="deadline" type="date"></label></div>'
      +'<button type="submit" class="e24-primary">Publier l’offre</button></form>':'';
    if(!rows)return heading+feedback()+quotaBanner()+'<div class="e24-toolbar">'+toggle+'</div>'+form+notLoaded('offres');
    const open=rows.filter(r=>r.status==='open'&&!r.is_archived).length;
    const items=rows.length?rows.map(row=>'<article class="e24-record">'
      +'<div><div class="e24-record-meta">'+pill(categories[row.category]||row.category)+' '+pill(row.is_archived?'Archivée':row.status==='open'?'Ouverte':'Fermée',row.is_archived?'neutral':row.status==='open'?'success':'neutral')+'</div>'
      +'<h3>'+safe(row.title)+'</h3><p>'+safe(row.description||'Aucune description')+'</p>'
      +'<small>'+safe(row.location_city||'Localisation non renseignée')+' · '+date(row.deadline)+' · '+Number(row.applications_count||0)+' candidature(s)</small></div>'
      +'<div class="e24-record-actions"><button type="button" data-e24="status-offer" data-id="'+Number(row.id)+'" data-status="'+(row.status==='open'?'closed':'open')+'">'+(row.status==='open'?'Fermer l’offre':'Rouvrir')+'</button>'
      +(!row.is_archived?'<button type="button" data-e24="archive-offer" data-id="'+Number(row.id)+'">Archiver</button>':'')+'</div></article>').join(''):empty('Aucune offre publiée','Créez votre première opportunité pour commencer à recevoir des candidatures.');
    return heading+feedback()+quotaBanner()+'<div class="e24-metrics">'+summary('Offres',rows.length,'Total de votre entreprise')+summary('Ouvertes',open,'En cours de recrutement')+summary('Candidatures',rows.reduce((n,r)=>n+Number(r.applications_count||0),0),'Sur toutes vos offres')+'</div>'
      +'<div class="e24-toolbar">'+toggle+'</div>'+form+'<div class="e24-stack">'+items+'</div>';
  }

  function applications() {
    const rows=cache.applications,heading=intro('Candidatures','Consultez les dossiers reçus et suivez les étapes de recrutement.');
    if(!rows)return heading+feedback()+notLoaded('candidatures');
    const items=rows.length?rows.map(row=>'<article class="e24-record">'
      +'<div><div class="e24-record-meta">'+pill(statuses[row.status]||row.status,row.status==='accepted'?'success':'neutral')+'</div>'
      +'<h3>'+safe(row.candidate_name)+'</h3><p>'+safe(row.offer_title)+'</p>'
      +'<small>'+safe(row.candidate_email)+' · Reçue le '+date(row.created_at)+'</small>'
      +(row.cover_letter?'<details class="e24-details"><summary>Lire la lettre de motivation</summary><p>'+safe(row.cover_letter)+'</p></details>':'')
      +(row.portfolio_url&&/^https?:\/\//.test(row.portfolio_url)?'<p><a href="'+safe(row.portfolio_url)+'" target="_blank" rel="noopener noreferrer">Voir le portfolio ↗</a></p>':'')
      +'</div><div class="e24-record-actions"><label class="e24-field"><span>Étape</span><select data-e24-status="'+Number(row.id)+'">'+opt(statuses,row.status)+'</select></label></div></article>').join(''):empty('Aucune candidature reçue','Les candidatures associées à vos offres apparaîtront ici.');
    return heading+feedback()+'<div class="e24-metrics">'+summary('Reçues',rows.length,'Dossiers enregistrés')+summary('Entretiens',rows.filter(a=>a.status==='interview').length,'En cours')+summary('Acceptées',rows.filter(a=>a.status==='accepted').length,'Dossiers retenus')+'</div><div class="e24-stack">'+items+'</div>';
  }

  function publications() {
    const rows=cache.publications,heading=intro('Publications','Partagez les actualités de votre entreprise avec la communauté.');
    const button='<button type="button" class="e24-primary" data-e24="toggle-post">'+(createPost?'Fermer':'Créer une publication')+'</button>';
    const form=createPost?'<form class="e24-form" data-e24-form="post"><h3>Nouvelle publication</h3>'
      +formField('title','Titre','maxlength="255" minlength="3"')
      +'<label class="e24-field"><span>Contenu</span><textarea name="content" rows="5" maxlength="5000" required></textarea></label>'
      +'<button type="submit" class="e24-primary">Publier</button></form>':'';
    const items=rows?rows.length?rows.map(row=>'<article class="e24-record"><div>'
      +'<div class="e24-record-meta">'+pill(row.post_type)+' '+pill(row.is_archived?'Archivée':'Publiée',row.is_archived?'neutral':'success')+'</div>'
      +'<h3>'+safe(row.title)+'</h3><p>'+safe(row.content||'')+'</p>'
      +'<small>'+date(row.created_at)+' · '+Number(row.views_count||0)+' vues · '+Number(row.reactions_count||0)+' réactions</small>'
      +'</div></article>').join(''):empty('Aucune publication','Partagez une actualité ou une annonce.'):notLoaded('publications');
    return heading+feedback()+quotaBanner()+'<div class="e24-toolbar">'+button+'</div>'+form+'<div class="e24-stack">'+items+'</div>';
  }

  function team() {
    const current=api.getCurrent()?.profile||{};
    return intro('Équipe & accès','Gestion des responsables et des accès à votre espace Entreprise.')
      +'<div class="e24-stack"><article class="e24-record"><div>'+pill('Administrateur principal','success')
      +'<h3>'+safe(current.email||'Compte Entreprise')+'</h3><p>Compte actuellement connecté, protégé par la double authentification.</p></div></article>'
      +empty('Invitations collaborateurs non disponibles','Le backend ne propose pas encore de gestion des membres et de leurs permissions pour les entreprises. Aucun accès supplémentaire n’a été créé.')+'</div>';
  }

  function notifications() {
    return intro('Notifications','Retrouvez les événements importants de votre espace.')
      +empty('Aucune notification professionnelle chargée','Le backend ne fournit pas encore de flux de notifications propre aux entreprises.');
  }

  const endpoints={
    offers:'/backoffice/enterprise/offers/',
    applications:'/backoffice/enterprise/applications/',
    publications:'/backoffice/enterprise/publications/',
  };
  async function reload(key) {
    if(!endpoints[key]||busy.has(key))return;
    busy.add(key);
    try{
      const result=await api.enterpriseRequest(endpoints[key]);
      cache[key]=Array.isArray(result)?result:Array.isArray(result?.results)?result.results:[];
      notice='';
    }catch(error){
      cache[key]=[];
      notice='Impossible de charger '+key+' : '+(error.message||'erreur serveur');
    }finally{
      busy.delete(key);
      refresh();
    }
  }
  function ensure(route) {
    if(endpoints[route]&&cache[route]===null&&!busy.has(route))void reload(route);
    if((route==='offers'||route==='publications')&&cache.contract===null&&!quotaLoading)void reloadQuota();
  }
  async function act(button) {
    const action=button.dataset.e24;
    if(action==='toggle-offer'){createOffer=!createOffer;notice='';refresh();return;}
    if(action==='toggle-post'){createPost=!createPost;notice='';refresh();return;}
    if(!['status-offer','archive-offer'].includes(action))return;
    const id=Number(button.dataset.id);
    if(!Number.isSafeInteger(id)||id<=0)return;
    const payload=action==='archive-offer'?{is_archived:true}:{status:button.dataset.status};
    try{
      await api.enterpriseRequest('/backoffice/enterprise/offers/'+id+'/','PATCH',payload);
      cache.offers=null;
      notice='Offre mise à jour.';
      refresh();void reload('offers');
    }catch(error){notice=error.message;refresh();}
  }
  async function changeStatus(select) {
    const id=Number(select.dataset.e24Status);
    if(!Number.isSafeInteger(id)||id<=0)return;
    try{
      await api.enterpriseRequest('/backoffice/enterprise/applications/'+id+'/','PATCH',{status:select.value});
      cache.applications=null;
      notice='Candidature mise à jour.';
      refresh();void reload('applications');
    }catch(error){notice=error.message;refresh();}
  }
  async function submit(form) {
    const kind=form.dataset.e24Form;
    if(!['offer','post'].includes(kind))return;
    const data=Object.fromEntries(new FormData(form).entries());
    if(kind==='offer'){
      if(data.duration_months)data.duration_months=Number(data.duration_months);
      if(!data.deadline)delete data.deadline;
      if(!data.duration_months)delete data.duration_months;
    }
    try{
      await api.enterpriseRequest(endpoints[kind==='offer'?'offers':'publications'],'POST',data);
      if(kind==='offer'){cache.offers=null;createOffer=false;}else{cache.publications=null;createPost=false;}
      cache.contract=null;void reloadQuota();
      notice=kind==='offer'?'Offre publiée.':'Publication créée.';
      refresh();void reload(kind==='offer'?'offers':'publications');
    }catch(error){notice=error.message;cache.contract=null;void reloadQuota();refresh();}
  }
  return {pages:{offers,applications,publications,team,notifications},ensure,act,submit,changeStatus};
};

