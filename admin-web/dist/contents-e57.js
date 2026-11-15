'use strict';
/* E57 | Superadmin editorial observatory. Real Django data only, read-only.
   No public/mobile feed, no mock totals, and no admin moderation writes. */
(function(){
  const types={
    all:'Tous les contenus', opportunity:'Opportunités', event:'Événements',
    project:'Projets', discussion:'Discussions', share:'Partages',
  };
  const states={
    all:'Tous les statuts',published:'Publiés',draft:'Brouillons',
    hidden:'Masqués',archived:'Archivés',
  };
  const tones={
    opportunity:'indigo',event:'coral',project:'teal',discussion:'blue',share:'lavender',
  };
  const svg=(symbol)=>({
    file:'<rect x="5" y="3" width="14" height="18" rx="3"/><path d="M9 8h6M9 12h6M9 16h4"/>',
    bag:'<rect x="3" y="7" width="18" height="14" rx="3"/><path d="M8 7V5a3 3 0 0 1 3-3h2a3 3 0 0 1 3 3v2M3 13h18"/>',
    calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4M17 3v4M3 10h18M8 15h2M13 15h3"/>',
    spark:'<path d="m12 2 2.2 6.8L21 11l-6.8 2.2L12 20l-2.2-6.8L3 11l6.8-2.2L12 2Z"/><path d="m19 18 .8 1.8L22 20l-2.2.8L19 23l-.8-2.2L16 20l2.2-.8L19 18Z"/>',
    shield:'<path d="m12 2 9 4v6c0 6-4 9-9 10-5-1-9-4-9-10V6l9-4Z"/><path d="m8.5 12 2.4 2.5 4.6-5"/>',
    arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
    eye:'<path d="M2 12c3-5 6-7 10-7s7 2 10 7c-3 5-6 7-10 7S5 17 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    search:'<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
    chart:'<path d="M3 20h18M5 17v-4M10 17V7M15 17V4M20 17v-7"/>',
    info:'<circle cx="12" cy="12" r="10"/><path d="M12 11v6M12 7h.01"/>',
    close:'<path d="M5 5 19 19M19 5 5 19"/>',
  })[symbol]||'';
  const icon=(name)=>'<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+svg(name)+'</svg>';

  window.GConnectContentsE57=function({api,safe,render,isVisible,go}){
    const state={loaded:false,loading:false,error:'',summary:null,
      rows:[],count:0,pages:1,page:1,kind:'all',status:'all',search:''};
    let timer=null,sequence=0,dialog=null;

    const count=(key)=>state.summary&&!state.error&&Number.isSafeInteger(state.summary[key])
      ?String(state.summary[key]):'—';
    const date=value=>{
      if(!value)return 'Date non disponible';
      const parsed=new Date(value);
      return Number.isNaN(parsed.getTime())?'Date non disponible':
        new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'short',year:'numeric'}).format(parsed);
    };
    const typeName=x=>types[x]||'Publication';
    const statusName=x=>states[x]||'Statut non défini';
    const typeTone=x=>tones[x]||'blue';
    const stateTone=x=>states[x]?'state-'+x:'state-all';
    const total=(name)=>Number.isSafeInteger(state.summary?.[name])?state.summary[name]:0;
    const isCurrent=()=>isVisible();

    function metric(name,key,symbol,accent,filter,description){
      const interactive=filter!==null;
      const tag=interactive?'button':'article';
      const attrs=interactive?' type="button" data-e57-type="'+filter+'" aria-pressed="'+String(state.kind===filter)+'"':'';
      return '<'+tag+' class="e57-metric e57-metric-'+accent+'"'+attrs+'>'+
        '<span class="e57-metric-top"><span class="e57-metric-icon">'+icon(symbol)+'</span>'+
        (interactive?'<span class="e57-metric-chevron">'+icon('arrow')+'</span>':'<span class="e57-metric-mini">LIVE</span>')+'</span>'+
        '<span class="e57-metric-value">'+count(key)+'</span>'+
        '<span class="e57-metric-label">'+name+'</span>'+
        '<span class="e57-metric-desc">'+description+'</span></'+tag+'>';
    }
    function art(){
      return '<div class="e57-hero-art" aria-hidden="true">'+
        '<div class="e57-orbit e57-orbit-out"></div><div class="e57-orbit e57-orbit-in"></div>'+
        '<div class="e57-art-core"><span class="e57-art-icon">'+icon('file')+'</span>'+
        '<span class="e57-art-lines"><i></i><i></i><i></i></span></div>'+
        '<span class="e57-art-badge e57-art-bag">'+icon('bag')+'</span>'+
        '<span class="e57-art-badge e57-art-calendar">'+icon('calendar')+'</span>'+
        '<span class="e57-art-badge e57-art-spark">'+icon('spark')+'</span>'+
        '<span class="e57-art-point e57-art-dot-one"></span>'+
        '<span class="e57-art-point e57-art-dot-two"></span>'+
        '</div>';
    }
    function heading(){
      return '<header class="e57-hero"><div class="e57-hero-copy">'+
        '<span class="e57-eyebrow"><span class="e57-pulse"></span>OBSERVATOIRE DES CONTENUS · G-CONNECT</span>'+
        '<h1>Offres <em>&</em> contenus</h1>'+
        '<p>Les publications qui font vivre votre réseau, suivies dans un espace de supervision clair, sécurisé et indépendant.</p>'+
        '<span class="e57-hero-note">'+icon('shield')+
        '<span>Consultation vérifiée · Aucune donnée de démonstration</span></span></div>'+art()+'</header>';
    }
    function editorial(){
      if(!state.summary || state.error)return '';
      const metrics=[
        ['Opportunités','opportunities','indigo'],
        ['Événements','events','coral'],
        ['Projets','projects','teal'],
        ['Discussions & partages','discussions','blue'],
      ];
      const max=Math.max(1,...metrics.map(m=>total(m[1])));
      return '<section class="e57-breakdown" aria-label="Répartition réelle des contenus">'+
        '<div class="e57-breakdown-top"><div><span class="e57-overline">VUE ÉDITORIALE</span>'+
        '<h2>Votre communauté en mouvement</h2><p>Répartition des publications par catégorie, calculée à partir du serveur.</p></div>'+
        '<span class="e57-breakdown-total">'+count('total')+' contenus</span></div>'+
        '<div class="e57-bars">'+metrics.map(([name,key,tone])=>
          '<div class="e57-bar-row"><span>'+name+'</span><div class="e57-bar-track">'+
          '<i class="e57-bar-fill e57-bar-'+tone+'" style="--e57-w:'+Math.round(total(key)/max*100)+'%"></i></div>'+
          '<strong>'+count(key)+'</strong></div>').join('')+'</div>'+
        '<div class="e57-breakdown-foot"><span>'+icon('eye')+
        ' '+count('published')+' publications publiées</span><span>'+
        count('hidden')+' masquées par modération</span></div></section>';
    }
    function filters(){
      return '<div class="e57-search-panel"><div class="e57-search-header">'+
        '<div><span class="e57-overline">RÉPERTOIRE ÉDITORIAL</span>'+
        '<h2>Explorer les publications</h2><p>Recherchez un contenu ou affinez la sélection.</p></div>'+
        '<button type="button" class="e57-ghost-button" data-e57-action="refresh">'+icon('chart')+' Actualiser</button></div>'+
        '<div class="e57-filter-bar">'+
        '<label class="e57-search">'+icon('search')+
        '<input type="search" autocomplete="off" maxlength="120" data-e57-search placeholder="Rechercher un titre, une organisation..." value="'+safe(state.search)+'" aria-label="Rechercher des contenus" />'+
        '<span class="e57-search-line"></span></label>'+
        '<label class="e57-select-label">Type'+
        '<select data-e57-filter="kind" aria-label="Filtrer par type">'+
        Object.entries(types).map(([key,val])=>'<option value="'+key+'"'+(key===state.kind?' selected':'')+'>'+val+'</option>').join('')+
        '</select></label>'+
        '<label class="e57-select-label">Statut'+
        '<select data-e57-filter="status" aria-label="Filtrer par statut">'+
        Object.entries(states).map(([key,val])=>'<option value="'+key+'"'+(key===state.status?' selected':'')+'>'+val+'</option>').join('')+
        '</select></label></div></div>';
    }
    function story(item){
      const tone=typeTone(item.type);
      const label=typeName(item.type);
      const avatar=item.type==='opportunity'?'bag':item.type==='event'?'calendar':item.type==='project'?'spark':'file';
      const organisation=item.organisation || item.author_name || 'Auteur non renseigné';
      const snippet=item.excerpt||'Aucun descriptif fourni.';
      return '<button type="button" class="e57-story" data-e57-detail="'+Number(item.id)+'"'+
        ' aria-label="Consulter '+safe(item.title||'Publication')+'">'+
        '<span class="e57-story-art e57-story-art-'+tone+'">'+icon(avatar)+'</span>'+
        '<span class="e57-story-main"><span class="e57-story-taxonomy">'+safe(label)+' · '+safe(date(item.created_at))+'</span>'+
        '<strong>'+safe(item.title||'Publication sans titre')+'</strong>'+
        '<span class="e57-story-excerpt">'+safe(snippet)+'</span>'+
        '<span class="e57-story-source">'+safe(organisation)+'</span></span>'+
        '<span class="e57-story-side"><span class="e57-status '+stateTone(item.state)+'">'+safe(statusName(item.state))+'</span>'+
        (Number(item.pending_reports)>0?'<span class="e57-alert">'+Number(item.pending_reports)+' signalement(s)</span>':'')+
        '<span class="e57-story-arrow">'+icon('arrow')+'</span></span></button>';
    }
    function list(){
      if(state.loading&&!state.loaded)return '<div class="e57-loading" role="status">Chargement du catalogue sécurisé…</div>';
      if(state.error)return '<div class="e57-error" role="alert"><strong>Données indisponibles</strong><p>'+safe(state.error)+'</p>'+
        '<button type="button" class="e57-ghost-button" data-e57-action="refresh">Réessayer</button></div>';
      if(!state.loaded)return '<div class="e57-loading" role="status">Connexion au répertoire…</div>';
      if(!state.rows.length)return '<div class="e57-empty">'+icon('spark')+
        '<strong>Aucun contenu pour ces filtres.</strong>'+
        '<p>Les résultats apparaîtront ici dès qu’une publication correspondra aux critères.</p>'+
        (state.kind!=='all'||state.status!=='all'||state.search?
        '<button type="button" class="e57-ghost-button" data-e57-action="clear">Effacer les filtres</button>':'')+'</div>';
      return '<div class="e57-story-list">'+state.rows.map(story).join('')+'</div>';
    }
    function paging(){
      if(!state.loaded||state.error)return '';
      return '<div class="e57-pager"><span>'+state.count+' résultat(s) · page '+state.page+' / '+state.pages+'</span>'+
        '<div><button type="button" data-e57-action="prev" '+(state.page<=1?'disabled':'')+'>← Précédent</button>'+
        '<button type="button" data-e57-action="next" '+(state.page>=state.pages?'disabled':'')+'>Suivant →</button></div></div>';
    }
    function page(){
      return '<div class="e57-page">'+heading()+
        '<section class="e57-metrics" aria-label="Indicateurs de contenu">'+
        metric('Publications','total','file','indigo','all','Toutes catégories confondues')+
        metric('Opportunités','opportunities','bag','violet','opportunity','Emplois, stages et formations')+
        metric('Événements','events','calendar','coral','event','Vie du réseau')+
        metric('Signalements à examiner','reports_pending','shield','teal',null,'File de modération')+
        '</section>'+editorial()+filters()+
        '<section class="e57-list-panel" aria-label="Catalogue réel des contenus">'+
        '<div class="e57-list-heading"><div><span class="e57-overline">PUBLICATIONS RÉELLES</span>'+
        '<h2>Derniers contenus du réseau</h2></div>'+
        '<span class="e57-results-counter">'+(state.loaded&&!state.error?state.count+' résultat(s)':'Synchronisation…')+'</span></div>'+
        list()+paging()+'</section></div>';
    }
    async function load(){
      if(state.loading||!isCurrent())return;
      const id=++sequence;
      state.loading=true;state.error='';
      try{
        const response=await api.adminContentDirectory({
          type:state.kind,state:state.status,search:state.search,
          page:state.page,page_size:12,
        });
        if(id!==sequence)return;
        if(!response||!Array.isArray(response.results)||
            !response.summary||!Number.isSafeInteger(response.count)||
            !Number.isSafeInteger(response.pages)||
            !Number.isSafeInteger(response.page))
          throw new Error('Réponse du répertoire non conforme.');
        state.rows=response.results;
        state.summary=response.summary;
        state.count=response.count;
        state.pages=response.pages;
        state.page=response.page;
        state.loaded=true;
      }catch(error){
        if(id!==sequence)return;
        state.error=error?.message||'Impossible de charger les contenus.';
        state.loaded=true;
        state.summary=null;state.rows=[];state.count=0;
      }finally{
        if(id===sequence){
          state.loading=false;
          if(isCurrent())render();
        }
      }
    }
    function ensure(){if(!state.loaded&&!state.loading&&isCurrent())void load();}
    function refetch(){
      // A new filter supersedes an in-flight response; never show stale results.
      if(state.loading){sequence++;state.loading=false;}
      state.loaded=false;
      void load();
    }
    function action(element){
      const kind=element.dataset.e57Action;
      if(kind==='refresh'){refetch();return}
      if(kind==='clear'){state.kind='all';state.status='all';state.search='';state.page=1;refetch();return}
      if(kind==='next'&&state.page<state.pages){state.page++;refetch();return}
      if(kind==='prev'&&state.page>1){state.page--;refetch();return}
      if(element.dataset.e57Type&&Object.hasOwn(types,element.dataset.e57Type)){
        state.kind=element.dataset.e57Type;state.page=1;refetch();return;
      }
      if(element.dataset.e57Detail)openDetail(Number(element.dataset.e57Detail));
    }
    function onFilter(element){
      const name=element.dataset.e57Filter,value=element.value;
      if(name==='kind'&&Object.hasOwn(types,value))state.kind=value;
      else if(name==='status'&&Object.hasOwn(states,value))state.status=value;
      else return;
      state.page=1;refetch();
    }
    function onSearch(element){
      const value=element.value.slice(0,120);
      clearTimeout(timer);
      timer=setTimeout(()=>{
        if(value===state.search)return;
        state.search=value;state.page=1;refetch();
      },330);
    }
    function openDetail(id){
      const item=state.rows.find(row=>Number(row.id)===id);
      if(!item||!isCurrent())return;
      if(!dialog){
        dialog=document.createElement('dialog');dialog.className='e57-dialog';
        dialog.setAttribute('aria-label','Détails d’un contenu');
        document.body.appendChild(dialog);
        dialog.addEventListener('click',event=>{
          if(event.target===dialog||event.target.closest('[data-e57-close]'))dialog.close();
        });
      }
      const status=states[item.state]||'Statut inconnu';
      dialog.innerHTML='<div class="e57-dialog-top"><span class="e57-overline">FICHE DE SUPERVISION</span>'+
        '<button type="button" data-e57-close aria-label="Fermer">'+icon('close')+'</button></div>'+
        '<span class="e57-dialog-kicker">'+safe(typeName(item.type))+' · '+safe(date(item.created_at))+'</span>'+
        '<h2>'+safe(item.title||'Publication sans titre')+'</h2>'+
        '<p class="e57-dialog-description">'+safe(item.description||'Aucun descriptif fourni.')+'</p>'+
        '<div class="e57-dialog-data">'+[
          ['Statut',status],['Auteur',item.author_name||'Non renseigné'],
          ['Organisation',item.organisation||'Non renseignée'],
          ['Audience',item.audience||'Non précisée'],
          ['Vues',String(Number(item.views)||0)],
          ['Commentaires',String(Number(item.comments)||0)],
          ['Réactions',String(Number(item.reactions)||0)],
          ['Signalements en attente',String(Number(item.pending_reports)||0)],
        ].map(([k,v])=>'<div><span>'+safe(k)+'</span><strong>'+safe(v)+'</strong></div>').join('')+
        '</div><div class="e57-dialog-bottom"><span>'+icon('shield')+
        ' Consultation seule, aucune modification des contenus</span>'+
        '<button type="button" data-e57-close class="e57-ghost-button">Fermer</button></div>';
      if(!dialog.open)dialog.showModal();
    }
    return {page,ensure,load,action,onFilter,onSearch,peek:()=>({
      page:state.page,count:state.count,loaded:state.loaded,error:state.error,
      kind:state.kind,status:state.status,
    })};
  };
})();
