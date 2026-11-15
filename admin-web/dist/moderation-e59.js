'use strict';
/* E59 · Superadmin moderation observatory, isolated Premium V2 identity.
   Real Django Reports only, with verified WebToken/MFA protected decisions. */
(function(){
  const signs={
    shield:'<path d="m12 2 9 4v6c0 6-4 9-9 10-5-1-9-4-9-10V6l9-4Z"/><path d="m8.5 12 2.5 2.5 5-5"/>',
    flag:'<path d="M5 21V4m0 0c5-3 9 3 15 0v12c-6 3-10-3-15 0"/>',
    check:'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',
    warning:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/>',
    eye:'<path d="M2 12c3-5 6-7 10-7s7 2 10 7c-3 5-6 7-10 7S5 17 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
    search:'<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
    cross:'<path d="M5 5l14 14M19 5 5 19"/>',
    list:'<path d="M8 5h13M8 12h13M8 19h13M3 5h.01M3 12h.01M3 19h.01"/>',
    layers:'<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    user:'<circle cx="12" cy="8" r="4"/><path d="M4 22v-2a8 8 0 0 1 16 0v2"/>',
    rotate:'<path d="M20 5v6h-6M4 19v-6h6"/><path d="M5 10a8 8 0 0 1 14-3l1 4M4 14a8 8 0 0 0 14 3"/>',
    no:'<circle cx="12" cy="12" r="9"/><path d="m6 6 12 12"/>',
  };
  const icon=name=>'<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round">'+(signs[name]||signs.shield)+'</svg>';
  const labels={all:'Tous',pending:'À traiter',dismissed:'Classés sans suite',actioned:'Mesures appliquées'};
  const targets={all:'Toutes les cibles',post:'Publications',comment:'Commentaires',user:'Comptes utilisateurs'};
  const reasons={
    all:'Tous les motifs',spam:'Spam',harassment:'Harcèlement',
    hate_speech:'Discours haineux',inappropriate:'Contenu inapproprié',
    fake_info:'Désinformation',other:'Autre',
  };
  const formatDate=value=>{
    if(!value)return 'Date indisponible';
    const date=new Date(value);
    return Number.isNaN(date.getTime())?'Date indisponible':
      new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(date);
  };

  window.GConnectModerationE59=function({api,safe,render,isVisible}){
    const state={
      ready:false,loading:false,error:'',notice:'',summary:null,reasons:null,
      rows:[],page:1,pages:1,count:0,status:'pending',target:'all',
      reason:'all',search:'',sending:false,
    };
    let requestId=0,timer=null,dialog=null,selectedId=null,decision=null;
    const current=()=>isVisible();
    const num=key=>Number.isSafeInteger(state.summary?.[key])&&!state.error?state.summary[key]:'—';
    const number=x=>Number.isFinite(Number(x))?Number(x):0;
    const pill=(status)=>'<span class="e59-state e59-state-'+safe(status)+'">'+
      safe(labels[status]||status)+'</span>';
    function art(){
      return '<div class="e59-art" aria-hidden="true"><div class="e59-art-ring e59-art-ring-1"></div>'+
        '<div class="e59-art-ring e59-art-ring-2"></div>'+
        '<div class="e59-shield">'+icon('shield')+'<span class="e59-shield-pulse"></span></div>'+
        '<span class="e59-art-chip e59-art-chip-flag">'+icon('flag')+'</span>'+
        '<span class="e59-art-chip e59-art-chip-check">'+icon('check')+'</span>'+
        '<span class="e59-art-chip e59-art-chip-eye">'+icon('eye')+'</span>'+
        '<i class="e59-art-dot e59-dot-one"></i><i class="e59-art-dot e59-dot-two"></i></div>';
    }
    function header(){
      return '<header class="e59-hero"><div class="e59-hero-copy">'+
        '<span class="e59-eyebrow"><i></i>CENTRE DE CONFIANCE · SUPERADMIN</span>'+
        '<h1>Modération <em>&</em> conformité</h1>'+
        '<p>Une supervision exigeante des signalements, des contenus et des décisions qui protègent la communauté G-Connect.</p>'+
        '<span class="e59-heronote">'+icon('shield')+
        ' Décisions tracées · Accès sécurisé par double authentification</span></div>'+art()+'</header>';
    }
    function metric(label,key,iconName,tone,desc){
      return '<article class="e59-metric e59-metric-'+tone+'">'+
        '<span class="e59-metric-icon">'+icon(iconName)+'</span>'+
        '<strong class="e59-metric-number">'+num(key)+'</strong>'+
        '<span class="e59-metric-label">'+label+'</span>'+
        '<small>'+desc+'</small></article>';
    }
    function metrics(){
      return '<section class="e59-metrics" aria-label="Indicateurs réels de modération">'+
        metric('À traiter','pending','flag','rose','Signalements ouverts')+
        metric('Résolus','resolved','check','teal','Décisions déjà prises')+
        metric('Contrôles · 30 jours','reviewed_30d','shield','blue','Revues sur la période')+
        metric('Alertes prioritaires','critical_pending','warning','amber','Harcèlement et propos haineux')+
        '</section>';
    }
    function options(obj,active){
      return Object.entries(obj).map(([key,val])=>
        '<option value="'+key+'"'+(key===active?' selected':'')+'>'+safe(val)+'</option>').join('');
    }
    function filterPanel(){
      return '<div class="e59-panel-head"><div><span class="e59-overline">01 / CENTRE DE TRAITEMENT</span>'+
        '<h2>File des signalements</h2><p>Examinez chaque cas et formalisez sa décision.</p></div>'+
        '<button type="button" class="e59-reload" data-e59-action="refresh">'+icon('rotate')+' Actualiser</button></div>'+
        '<div class="e59-filterbox"><label class="e59-search">'+icon('search')+
          '<input type="search" aria-label="Rechercher un signalement" data-e59-search autocomplete="off" maxlength="120" '+
          'placeholder="Titre, auteur ou motif…" value="'+safe(state.search)+'"></label>'+
          '<label class="e59-filter">Statut<select data-e59-filter="status">'+options(labels,state.status)+'</select></label>'+
          '<label class="e59-filter">Cible<select data-e59-filter="target">'+options(targets,state.target)+'</select></label>'+
          '<label class="e59-filter">Motif<select data-e59-filter="reason">'+options(reasons,state.reason)+'</select></label>'+
        '</div>';
    }
    function item(report){
      const title=report.target_title||'Cible indisponible';
      const risky=report.critical&&report.status==='pending';
      const color=risky?'e59-case-critical':'e59-case-standard';
      return '<button type="button" class="e59-case '+color+'" data-e59-detail="'+Number(report.id)+'">'+
        '<span class="e59-case-badge">'+icon(report.target==='user'?'user':report.target==='comment'?'list':'layers')+'</span>'+
        '<span class="e59-case-primary">'+
          '<span class="e59-case-kicker">SIGNALEMENT #'+Number(report.id)+' · '+safe(formatDate(report.created_at))+'</span>'+
          '<strong>'+safe(title)+'</strong>'+
          '<span class="e59-case-description">'+safe(report.description||'Aucune description fournie.')+'</span>'+
          '<span class="e59-case-footer">'+safe(targets[report.target]||report.target)+
          ' · '+safe(report.reported_by||'Auteur non renseigné')+'</span>'+
        '</span><span class="e59-case-end">'+
          (risky?'<span class="e59-priority">'+icon('warning')+' Prioritaire</span>':'')+
          pill(report.status)+'<span class="e59-case-more">'+icon('arrow')+'</span></span></button>';
    }
    function cases(){
      if(state.loading&&!state.ready)return '<div class="e59-placeholder" role="status">Chargement du registre…</div>';
      if(state.error)return '<div class="e59-placeholder e59-placeholder-error" role="alert">'+icon('warning')+
        '<strong>Registre indisponible</strong><p>'+safe(state.error)+'</p>'+
        '<button type="button" data-e59-action="refresh">Réessayer</button></div>';
      if(state.ready&&!state.rows.length)return '<div class="e59-placeholder">'+icon('shield')+
        '<strong>Aucun signalement dans cette sélection</strong>'+
        '<p>Les dossiers réels apparaîtront lorsqu’ils correspondront à vos filtres.</p></div>';
      return '<div class="e59-case-list">'+state.rows.map(item).join('')+'</div>';
    }
    function pagination(){
      if(!state.ready||state.error)return '';
      return '<footer class="e59-pages"><span>'+state.count+' dossier(s) · page '+state.page+'/'+state.pages+
        '</span><div><button type="button" data-e59-action="prev" '+(state.page<=1?'disabled':'')+
        '>Précédent</button><button type="button" data-e59-action="next" '+(state.page>=state.pages?'disabled':'')+
        '>Suivant '+icon('arrow')+'</button></div></footer>';
    }
    function riskLegend(){
      const list=[
        ['harassment','Harcèlement','rose'],['hate_speech','Propos haineux','rose'],
        ['spam','Spam','blue'],['fake_info','Désinformation','violet'],
        ['inappropriate','Inapproprié','amber'],['other','Autres','teal'],
      ];
      if(!state.reasons||state.error)return '<p class="e59-panel-wait">La répartition sera disponible après chargement.</p>';
      const total=list.reduce((sum,[key])=>sum+number(state.reasons[key]),0);
      const max=Math.max(1,...list.map(([key])=>number(state.reasons[key])));
      return '<div class="e59-risk-list">'+list.map(([key,label,tone])=>
        '<div class="e59-risk-row"><div><span>'+label+'</span><strong>'+number(state.reasons[key])+'</strong></div>'+
        '<span class="e59-risk-track"><i class="e59-risk-fill e59-risk-'+tone+'" '+
        'style="--e59-size:'+Math.round(number(state.reasons[key])/max*100)+'%"></i></span></div>'
      ).join('')+'</div><p class="e59-risk-foot">'+total+' signalement(s) en attente, répartis par motif.</p>';
    }
    function side(){
      return '<aside class="e59-side"><section class="e59-risk-panel">'+
        '<div class="e59-side-header"><span class="e59-overline">02 / VIGILANCE</span>'+
        '<h2>Signaux à surveiller</h2><p>Répartition des alertes encore ouvertes.</p></div>'+
        riskLegend()+'</section>'+
        '<section class="e59-protocol"><span class="e59-overline">03 / TRAÇABILITÉ</span>'+
        '<h2>Chaque décision laisse une trace.</h2>'+
        '<ol><li><span>01</span><div><strong>Qualifier</strong><p>Étudier la cible et le motif.</p></div></li>'+
        '<li><span>02</span><div><strong>Décider</strong><p>Classer ou masquer une publication.</p></div></li>'+
        '<li><span>03</span><div><strong>Tracer</strong><p>Conserver l’auteur et la date de revue.</p></div></li></ol>'+
        '<div class="e59-protocol-foot">'+icon('shield')+
        ' Aucune suppression de compte ni bannissement automatique.</div></section></aside>';
    }
    const page=()=>'<div class="e59-page">'+header()+metrics()+
      (state.notice?'<div class="e59-toast" role="status">'+icon('check')+safe(state.notice)+'</div>':'')+
      '<div class="e59-grid"><section class="e59-main">'+filterPanel()+cases()+pagination()+'</section>'+
      side()+'</div></div>';
    async function load(){
      if(state.loading||!current())return;
      const id=++requestId;state.loading=true;state.error='';
      try{
        const result=await api.adminModerationDirectory({
          status:state.status,target:state.target,reason:state.reason,
          search:state.search,page:state.page,page_size:10,
        });
        if(id!==requestId)return;
        if(!result?.summary||!result.by_reason||!Array.isArray(result.results)||
          !Number.isSafeInteger(result.count)||!Number.isSafeInteger(result.page)||
          !Number.isSafeInteger(result.pages))
          throw Error('Réponse du registre non conforme.');
        state.rows=result.results;
        state.summary=result.summary;
        state.reasons=result.by_reason;
        state.count=result.count;state.pages=result.pages;state.page=result.page;
        state.ready=true;
      }catch(err){
        if(id!==requestId)return;
        state.error=err?.message||'Impossible de lire les signalements.';
        state.summary=null;state.reasons=null;state.rows=[];
        state.ready=true;
      }finally{
        if(id===requestId){state.loading=false;if(current())render()}
      }
    }
    function ensure(){if(!state.ready&&!state.loading&&current())void load();}
    function reload(){
      if(state.loading){requestId++;state.loading=false}
      state.ready=false;void load();
    }
    function onFilter(element){
      const field=element.dataset.e59Filter;
      const val=element.value;
      if(field==='status'&&Object.hasOwn(labels,val))state.status=val;
      else if(field==='target'&&Object.hasOwn(targets,val))state.target=val;
      else if(field==='reason'&&Object.hasOwn(reasons,val))state.reason=val;
      else return;
      state.page=1;reload();
    }
    function onSearch(element){
      const input=element.value.slice(0,120);
      clearTimeout(timer);
      timer=setTimeout(()=>{
        if(state.search===input)return;
        state.search=input;state.page=1;reload();
      },320);
    }
    function decisionFooter(report){
      if(report.status!=='pending')return '<div class="e59-modal-result">'+icon('check')+
        ' Déjà traité'+(report.reviewed_by?' par '+safe(report.reviewed_by):'')+
        (report.reviewed_at?' le '+safe(formatDate(report.reviewed_at)):'')+'</div>';
      return '<div class="e59-modal-actions"><button class="e59-dismiss-button" type="button" data-e59-modal-decision="dismiss">'+
        icon('no')+' Classer sans suite</button>'+
        (report.can_hide?'<button class="e59-hide-button" type="button" data-e59-modal-decision="hide_post">'+
          icon('eye')+' Masquer la publication</button>':'')+'</div>';
    }
    function openDialog(id){
      const report=state.rows.find(x=>Number(x.id)===id);
      if(!report||!current())return;
      selectedId=id;decision=null;
      if(!dialog){
        dialog=document.createElement('dialog');dialog.className='e59-dialog';
        dialog.setAttribute('aria-label','Examen d’un signalement');
        document.body.appendChild(dialog);
        dialog.addEventListener('click',e=>{
          if(e.target===dialog||e.target.closest('[data-e59-close]'))dialog.close();
        });
        dialog.addEventListener('close',()=>{selectedId=null;decision=null});
      }
      dialog.innerHTML='<div class="e59-modal-top"><span class="e59-overline">DOSSIER DE MODÉRATION #'+id+'</span>'+
        '<button type="button" data-e59-close aria-label="Fermer la fiche">'+icon('cross')+'</button></div>'+
        '<div class="e59-modal-kicker">'+pill(report.status)+
        (report.critical&&report.status==='pending'?'<span class="e59-priority">'+icon('warning')+' Prioritaire</span>':'')+'</div>'+
        '<h2>'+safe(report.target_title||'Cible indisponible')+'</h2>'+
        '<p class="e59-modal-description">'+safe(report.description||'Aucun détail transmis.')+'</p>'+
        (report.target_excerpt?'<blockquote class="e59-target-excerpt">'+safe(report.target_excerpt)+'</blockquote>':'')+
        '<div class="e59-details">'+[
          ['Motif',report.reason_display||reasons[report.reason]||report.reason],
          ['Cible',targets[report.target]||report.target],
          ['Signalé par',report.reported_by||'Inconnu'],
          ['Organisation',report.organisation||'Non renseignée'],
          ['Créé le',formatDate(report.created_at)],
          ['Statut',labels[report.status]||report.status],
        ].map(([k,v])=>'<div><span>'+safe(k)+'</span><strong>'+safe(v)+'</strong></div>').join('')+
        '</div><div class="e59-dialog-bottom">'+decisionFooter(report)+'</div>';
      if(!dialog.open)dialog.showModal();
    }
    function selectDecision(name){
      if(state.sending||selectedId===null)return;
      const report=state.rows.find(x=>Number(x.id)===selectedId);
      if(!report||!report.can_dismiss||!['dismiss','hide_post'].includes(name)||
         (name==='hide_post'&&!report.can_hide))return;
      decision=name;
      const heading=name==='hide_post'?'Masquer cette publication ?':'Classer ce signalement ?';
      const note=name==='hide_post'
        ?'Le contenu sera retiré de la visibilité publique. Cette décision sera journalisée.'
        :'Le signalement sera clos sans masquer le contenu. Cette décision sera journalisée.';
      const content='<div class="e59-confirm-panel"><div class="e59-confirm-head">'+icon('warning')+
        '<div><h3>'+heading+'</h3><p>'+note+'</p></div></div>'+
        (name==='hide_post'?'<label class="e59-reason">Motif de masquage (10 caractères minimum)'+
          '<textarea data-e59-reason rows="3" maxlength="255" placeholder="Justification factuelle de la mesure…"></textarea></label>':'')+
        '<label class="e59-confirm-check"><input type="checkbox" data-e59-approval>'+
          '<span>Je confirme avoir examiné le dossier et autorise cette décision.</span></label>'+
        '<div class="e59-confirm-actions"><button type="button" class="e59-cancel" data-e59-modal-action="back">Retour</button>'+
        '<button type="button" class="e59-confirm-button" data-e59-modal-action="execute" disabled>'+
          icon('check')+' Enregistrer la décision</button></div></div>';
      const container=dialog?.querySelector('.e59-dialog-bottom');
      if(container)container.innerHTML=content;
    }
    function checkApproval(){
      const yes=!!dialog?.querySelector('[data-e59-approval]')?.checked;
      const reason=dialog?.querySelector('[data-e59-reason]')?.value.trim()||'';
      const valid=yes&&(decision==='dismiss'||(decision==='hide_post'&&reason.length>=10&&reason.length<=255));
      const button=dialog?.querySelector('[data-e59-modal-action="execute"]');
      if(button)button.disabled=!valid||state.sending;
    }
    async function execute(){
      const reportId=selectedId,kind=decision;
      const confirmed=!!dialog?.querySelector('[data-e59-approval]')?.checked;
      const reason=dialog?.querySelector('[data-e59-reason]')?.value.trim()||'';
      if(!confirmed||!reportId||state.sending||
         !['dismiss','hide_post'].includes(kind)||
         (kind==='hide_post'&&reason.length<10))return;
      state.sending=true;checkApproval();
      try{
        const answer=await api.adminModerationDecision(reportId,{
          decision:kind,confirmation:'CONFIRMER',reason:kind==='hide_post'?reason:'',
        });
        if(!answer||Number(answer.id)!==reportId||!['dismissed','actioned'].includes(answer.status))
          throw Error('Confirmation serveur invalide.');
        if(dialog?.open)dialog.close();
        state.notice=kind==='hide_post'?'Publication masquée et décision journalisée.':'Signalement classé et décision journalisée.';
        reload();
      }catch(err){
        state.notice='Décision non enregistrée : '+(err?.message||'Erreur inconnue.');
        const container=dialog?.querySelector('.e59-confirm-panel');
        if(container){
          const message=document.createElement('p');message.className='e59-confirm-error';
          message.textContent=err?.message||'Décision impossible.';container.prepend(message);
        }
      }finally{
        state.sending=false;checkApproval();
        if(current())render();
      }
    }
    function action(element){
      const detail=element.dataset.e59Detail;
      if(detail){openDialog(Number(detail));return}
      const kind=element.dataset.e59Action;
      if(kind==='refresh'){reload();return}
      if(kind==='next'&&state.page<state.pages){state.page++;reload();return}
      if(kind==='prev'&&state.page>1){state.page--;reload();return}
      if(kind==='clear'){
        state.status='pending';state.target='all';state.reason='all';state.search='';
        state.page=1;reload();return;
      }
    }
    function modalAction(element){
      const action=element.dataset.e59ModalDecision||element.dataset.e59ModalAction;
      if(action==='dismiss'||action==='hide_post'){selectDecision(action);return}
      if(action==='back'){if(selectedId!==null)openDialog(selectedId);return}
      if(action==='execute'){void execute()}
    }
    return {page,ensure,load,action,onFilter,onSearch,modalAction,checkApproval,
      peek:()=>({ready:state.ready,status:state.status,count:state.count,error:state.error})};
  };
})();
