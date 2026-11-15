'use strict';
/* E58 · Superadmin import studio: protected, truthful history and preview-first
   catalogue imports. No account auto-creation and no blind upload actions. */
(function(){
 const icons={
  tray:'<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>',
  check:'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  warning:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/>',
  school:'<path d="m2 10 10-6 10 6-10 6-10-6ZM6 13v5c3 3 9 3 12 0v-5M22 10v7"/>',
  file:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
  filter:'<path d="M3 6h18M6 12h12M9 18h6"/>',
  arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  spark:'<path d="m12 3 2.7 6.3L21 12l-6.3 2.7L12 21l-2.7-6.3L3 12l6.3-2.7L12 3Z"/>',
  shield:'<path d="m12 2 9 4v6c0 6-4 9-9 10-5-1-9-4-9-10V6l9-4Z"/><path d="m8.5 12 2.4 2.5 4.6-5"/>',
  x:'<path d="M5 5 19 19M19 5 5 19"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',
  download:'<path d="M12 3v12m-4-4 4 4 4-4M5 17v4h14v-4"/>',
  rotate:'<path d="M20 6v5h-5M4 18v-5h5"/><path d="M5 10a8 8 0 0 1 14-3l1 4M4 13a8 8 0 0 0 14 3"/>',
 };
 const icon=k=>'<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7">'+(icons[k]||icons.file)+'</svg>';
 const types={establishments:'Établissements',promotions:'Promotions',students:'Étudiants',alumni:'Alumni'};
 const columns={
  establishments:['name','acronym','text_code','address','phone','email'],
  promotions:['name','year','department','level','is_general'],
  students:['email','username','first_name','last_name','date_of_birth','student_id'],
  alumni:['email','username','first_name','last_name','graduation_date','promotion_name'],
 };
 const accepted='.csv,.xlsx';
 const safeName=x=>String(x||'').slice(0,160);
 const date=value=>{
   if(!value)return 'Date inconnue';
   const d=new Date(value);
   return Number.isNaN(d.getTime())?'Date inconnue':
     new Intl.DateTimeFormat('fr-FR',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(d);
 };
 window.GConnectImportsE58=function({api,safe,render,isVisible}){
   const state={
     ready:false,loading:false,submitting:false,error:'',notice:'',summary:null,
     rows:[],count:0,page:1,pages:1,historyType:'all',schools:[],
     kind:'establishments',school:'',file:null,preview:null,
     schoolQuery:'',schoolError:'',confirmed:false,
   };
   let modal=null,requestId=0,searchTimer=null;
   const active=()=>isVisible();
   const metric=(label,key,iconName,tone,sub)=>{
     const value=state.summary&&!state.error&&Number.isSafeInteger(state.summary[key])
       ?state.summary[key]:'—';
     return '<article class="e58-metric e58-metric-'+tone+'">'+
       '<span class="e58-metric-icon">'+icon(iconName)+'</span>'+
       '<strong>'+value+'</strong><span>'+label+'</span><small>'+sub+'</small></article>';
   };
   const orbit=()=>'<div class="e58-orbit" aria-hidden="true"><div class="e58-orbit-wide"></div>'+
     '<div class="e58-orbit-inner"></div><div class="e58-core">'+icon('file')+
     '<span class="e58-core-lines"><i></i><i></i><i></i></span></div>'+
     '<div class="e58-bubble e58-bubble-upload">'+icon('tray')+'</div>'+
     '<div class="e58-bubble e58-bubble-check">'+icon('check')+'</div>'+
     '<div class="e58-bubble e58-bubble-school">'+icon('school')+'</div>'+
     '<i class="e58-dot e58-dot-a"></i><i class="e58-dot e58-dot-b"></i></div>';
   const hero=()=>'<header class="e58-hero"><div class="e58-hero-copy">'+
     '<span class="e58-overline"><i></i>STRUCTURATION DES DONNÉES · G-CONNECT</span>'+
     '<h1>Imports <em>&</em> opérations groupées</h1>'+
     '<p>Un atelier de gestion précis pour préparer les fichiers, contrôler les lignes et suivre les intégrations de votre réseau.</p>'+
     '<span class="e58-hero-assurance">'+icon('shield')+
     'Validation avant import · Aucun compte créé automatiquement</span></div>'+
     '<div class="e58-hero-art">'+orbit()+'</div></header>';
   const metrics=()=>'<section class="e58-metrics" aria-label="Indicateurs réels des imports">'+
     metric('Imports','imports','tray','blue','Opérations enregistrées')+
     metric('Lignes intégrées','integrated','check','green','Traitements réussis')+
     metric('Anomalies','anomalies','warning','amber','Erreurs enregistrées')+
     metric('Établissements','establishments','school','purple','Établissements intégrés')+
     '</section>';
   const typeList=()=>Object.entries(types).map(([id,name])=>
     '<button type="button" class="e58-type e58-type-'+id+'" data-e58-type="'+id+
     '" aria-pressed="'+String(state.kind===id)+'">'+
     '<span class="e58-type-symbol">'+icon(id==='establishments'?'school':id==='promotions'?'file':id==='students'?'spark':'check')+'</span>'+
     '<strong>'+name+'</strong><small>'+(id==='promotions'||id==='establishments'?'Prévisualisation et import':'Prévisualisation uniquement')+
     '</small></button>').join('');
   const schoolSelector=()=>{
     if(state.kind==='establishments')return '<p class="e58-no-school">'+icon('school')+
       ' Les établissements créés seront ajoutés au catalogue de la plateforme.</p>';
     return '<div class="e58-school-group"><label class="e58-field e58-school-query">Rechercher un établissement'+
       '<input data-e58-school-query type="search" maxlength="80" placeholder="Nom de l’établissement" value="'+safe(state.schoolQuery)+'"></label>'+
       '<label class="e58-field e58-school-choice">Établissement de destination'+
       '<select data-e58-school><option value="">Sélectionner l’établissement</option>'+
       state.schools.map(v=>'<option value="'+Number(v.id)+'"'+(String(v.id)===state.school?' selected':'')+'>'+safe(v.name)+'</option>').join('')+
       '</select></label></div>'+
       (state.schoolError?'<p class="e58-helper-error">'+safe(state.schoolError)+'</p>':'');
   };
   const upload=()=>'<section class="e58-studio"><div class="e58-studio-head">'+
     '<div><span class="e58-section-tag">01 / PRÉPARATION</span><h2>Nouvel import</h2>'+
     '<p>Choisissez un jeu de données. Chaque fichier est d’abord analysé sans écriture.</p></div>'+
     '<span class="e58-secure-badge">'+icon('shield')+' Opération contrôlée</span></div>'+
     '<div class="e58-type-grid" role="group" aria-label="Type de données">'+typeList()+'</div>'+
     '<div class="e58-studio-inner"><div class="e58-upload-column">'+
       '<label class="e58-file-drop" data-e58-drop>'+
         '<input type="file" data-e58-file accept="'+accepted+'" aria-label="Choisir un fichier à analyser">'+
         '<span class="e58-file-icon">'+icon('tray')+'</span>'+
         '<strong>'+(state.file?safe(safeName(state.file.name)):'Déposez un fichier ou parcourez vos dossiers')+'</strong>'+
         '<small>'+(state.file?safe((state.file.size/1024).toFixed(1)+' Ko'):'CSV UTF-8 ou Excel XLSX · 2 Mo maximum · 500 lignes maximum')+'</small>'+
         '<span class="e58-file-pick">'+(state.file?'Changer le fichier':'Parcourir les fichiers')+' '+icon('arrow')+'</span>'+
       '</label>'+
       '<div class="e58-file-guide">'+icon('shield')+
       '<p>Vos fichiers restent privés et sont envoyés uniquement lors de la prévisualisation sécurisée.</p></div>'+
     '</div><div class="e58-rules-column"><div class="e58-rules-title"><span>'+icon('filter')+'</span>'+
       '<div><strong>Paramètres du traitement</strong><small>Contrôles avant toute intégration</small></div></div>'+
       schoolSelector()+
       '<div class="e58-rules-line"><span>Structure attendue</span><strong>'+safe(columns[state.kind].slice(0,3).join(' · '))+'…</strong></div>'+
       '<div class="e58-rules-line"><span>Volume maximal</span><strong>500 lignes</strong></div>'+
       '<div class="e58-rules-line"><span>Exécution</span><strong class="e58-execute-status">'+
         (['promotions','establishments'].includes(state.kind)?'Après confirmation':'Désactivée pour les comptes')+'</strong></div>'+
       '<div class="e58-studio-actions"><button type="button" class="e58-button-secondary" data-e58-action="template">'+
         icon('download')+' Modèle CSV</button>'+
       '<button type="button" class="e58-button-primary" data-e58-action="preview" '+
         ((!state.file||state.submitting)?'disabled':'')+'>'+icon('eye')+' Prévisualiser <span>↗</span></button></div>'+
       '</div></div></section>';
   const typeOptions=()=>'<option value="all">Tous les types</option>'+
     Object.entries(types).map(([k,n])=>'<option value="'+k+'"'+(state.historyType===k?' selected':'')+'>'+n+'</option>').join('');
   const history=()=>{
     let body='<div class="e58-loading" role="status">Chargement du registre des opérations…</div>';
     if(state.error)body='<div class="e58-error" role="alert"><strong>Historique indisponible</strong>'+
       '<p>'+safe(state.error)+'</p><button data-e58-action="refresh">Réessayer</button></div>';
     else if(state.ready&&!state.rows.length)body='<div class="e58-empty">'+icon('tray')+
       '<strong>Aucun import enregistré pour cette sélection</strong>'+
       '<p>Les opérations réellement confirmées apparaîtront ici avec leur résultat.</p></div>';
     else if(state.ready)body='<div class="e58-history-table" role="table" aria-label="Historique des imports">'+
       '<div class="e58-table-head" role="row"><span role="columnheader">Fichier et date</span><span role="columnheader">Type / destination</span>'+
       '<span role="columnheader">Intégrées</span><span role="columnheader">Anomalies</span><span role="columnheader">Résultat</span></div>'+
       state.rows.map(job=>{
         const errors=Number(job.anomalies)||0,created=Number(job.integrated)||0;
         const status=errors&&created?'Partiel':errors?'Échec':'Terminé';
         const tone=errors?'e58-job-warning':'e58-job-success';
         return '<div class="e58-table-row" role="row"><span class="e58-file-summary" role="cell"><i>'+icon('file')+'</i>'+
         '<span><strong>'+safe(job.file_name)+'</strong><small>'+safe(date(job.created_at))+'</small></span></span>'+
         '<span class="e58-job-type" role="cell"><strong>'+safe(types[job.type]||job.type)+'</strong>'+
         '<small>'+safe(job.institution||'Plateforme')+'</small></span>'+
         '<span class="e58-table-num" role="cell">'+created+'</span>'+
         '<span class="e58-table-num" role="cell">'+errors+'</span>'+
         '<span class="e58-job-status '+tone+'" role="cell">'+status+'</span></div>';
       }).join('')+'</div>';
     return '<section class="e58-history"><div class="e58-history-heading"><div>'+
       '<span class="e58-section-tag">02 / TRAÇABILITÉ</span><h2>Historique des opérations</h2>'+
       '<p>Rapports des imports réellement enregistrés par le serveur.</p></div>'+
       '<div class="e58-history-tools"><label class="e58-history-filter">Filtrer'+
       '<select data-e58-filter>'+typeOptions()+'</select></label>'+
       '<button type="button" class="e58-icon-button" data-e58-action="refresh" aria-label="Actualiser l’historique">'+
       icon('rotate')+'</button></div></div>'+
       '<div class="e58-history-content">'+body+'</div>'+
       (state.ready&&!state.error?'<footer class="e58-pager"><span>'+state.count+' opération(s) · page '+state.page+
         ' / '+state.pages+'</span><div><button data-e58-action="prev" '+(state.page<=1?'disabled':'')+
         '>Précédent</button><button data-e58-action="next" '+(state.page>=state.pages?'disabled':'')+
         '>Suivant</button></div></footer>':'')+'</section>';
   };
   const message=()=>state.notice?'<div class="e58-notice" role="status">'+icon('check')+safe(state.notice)+'</div>':'';
   const page=()=>'<div class="e58-page">'+hero()+metrics()+message()+upload()+history()+'</div>';

   function formData(){
     const data=new FormData();
     data.set('file',state.file,state.file.name);
     data.set('import_type',state.kind);
     if(state.kind!=='establishments')data.set('institution',state.school);
     return data;
   }
   async function load(){
     if(state.loading||!active())return;
     const id=++requestId;state.loading=true;state.error='';
     try{
       const result=await api.adminImportHistory({
         page:state.page,type:state.historyType,institution_search:state.schoolQuery,
       });
       if(id!==requestId)return;
       if(!result||!Array.isArray(result.results)||!result.summary||
           !Array.isArray(result.institutions)||!Number.isSafeInteger(result.count))
         throw new Error('Historique incomplet.');
       state.summary=result.summary;
       state.rows=result.results;
       state.schools=result.institutions;
       state.count=result.count;state.pages=result.pages;state.page=result.page;
       state.ready=true;
     }catch(error){
       if(id!==requestId)return;
       state.error=error?.message||'Impossible de récupérer les imports.';
       state.summary=null;state.rows=[];state.ready=true;
     }finally{
       if(id===requestId){state.loading=false;if(active())render()}
     }
   }
   function ensure(){if(!state.ready&&!state.loading&&active())void load();}
   function reload(){
     if(state.loading){requestId++;state.loading=false}
     state.ready=false;void load();
   }
   function downloadTemplate(){
     const header=columns[state.kind].join(',');
     const blob=new Blob(['\uFEFF'+header+'\n'],{type:'text/csv;charset=utf-8;'});
     const href=URL.createObjectURL(blob);
     const node=document.createElement('a');
     node.href=href;node.download='gconnect-modele-'+state.kind+'.csv';
     document.body.appendChild(node);node.click();node.remove();
     setTimeout(()=>URL.revokeObjectURL(href),2000);
   }
   async function preview(){
     if(!state.file||state.submitting)return;
     if(state.kind!=='establishments'&&!state.school){
       state.notice='Sélectionnez un établissement avant la prévisualisation.';render();return;
     }
     state.submitting=true;state.notice='';
     try{
       const result=await api.adminImportPreview(formData());
       if(!result||!Number.isSafeInteger(result.rows)||!Array.isArray(result.errors))
         throw new Error('Rapport de contrôle non conforme.');
       state.preview=result;state.confirmed=false;openModal();
     }catch(err){state.notice='Prévisualisation impossible : '+(err?.message||'Erreur inconnue.');}
     finally{state.submitting=false;if(active())render();}
   }
   function closeModal(){
     if(modal?.open)modal.close();
   }
   function openModal(){
     if(!modal){
       modal=document.createElement('dialog');modal.className='e58-dialog';
       modal.setAttribute('aria-label','Prévisualisation sécurisée du fichier');
       document.body.appendChild(modal);
       modal.addEventListener('click',event=>{
         if(event.target===modal||event.target.closest('[data-e58-close]'))closeModal();
       });
     }
     const info=state.preview;
     if(!info)return;
     const good=info.executable&&info.errors.length===0;
     const cellSample=info.sample.map(row=>'<div class="e58-sample-row"><span>Ligne '+Number(row.row)+'</span>'+
       '<strong>'+safe(Object.values(row.values).slice(0,3).join(' · '))+'</strong></div>').join('');
     modal.innerHTML='<div class="e58-modal-top"><span class="e58-section-tag">PRÉVISUALISATION · SANS ÉCRITURE</span>'+
       '<button type="button" data-e58-close aria-label="Fermer">'+icon('x')+'</button></div>'+
       '<h2>Vérification du fichier</h2><p class="e58-modal-intro">'+safe(info.name)+'</p>'+
       '<div class="e58-preview-stats"><span><strong>'+info.rows+'</strong>Lignes analysées</span>'+
       '<span><strong>'+info.errors.length+'</strong>Anomalies détectées</span>'+
       '<span><strong>'+info.columns.length+'</strong>Colonnes reconnues</span></div>'+
       '<p class="e58-preview-advice '+(good?'e58-preview-ok':'e58-preview-alert')+'">'+
       icon(good?'check':'warning')+' '+safe(info.notice||'')+'</p>'+
       '<div class="e58-preview-list"><h3>Aperçu des premières lignes</h3>'+
       (cellSample||'<p>Aucune ligne disponible.</p>')+'</div>'+
       (info.errors.length?'<div class="e58-preview-errors"><h3>Lignes à corriger</h3>'+
         info.errors.slice(0,10).map(e=>'<p>Ligne '+Number(e.row)+' : '+safe(e.message)+'</p>').join('')+'</div>':'')+
       '<div class="e58-modal-actions">'+
       (good?'<label class="e58-confirm"><input type="checkbox" data-e58-confirm>'+
         '<span>Je confirme avoir vérifié ce fichier et autorise l’intégration de ces données.</span></label>':'')+
       '<div><button class="e58-button-secondary" type="button" data-e58-close>Fermer</button>'+
       (good?'<button class="e58-button-primary" type="button" data-e58-action="execute" disabled>'+
         icon('check')+' Confirmer l’intégration</button>':'')+'</div></div>';
     if(!modal.open)modal.showModal();
   }
   async function execute(){
     if(!state.confirmed||!state.preview?.executable||!state.file||state.submitting)return;
     state.submitting=true;state.notice='';
     const button=modal?.querySelector('[data-e58-action="execute"]');
     if(button)button.disabled=true;
     try{
       const data=formData();
       data.set('confirmation','CONFIRMER');
       data.set('preview_token',state.preview.preview_token);
       const response=await api.adminImportExecute(data);
       if(!Number.isSafeInteger(response.integrated))throw Error('Réponse serveur inattendue.');
       closeModal();state.file=null;state.preview=null;state.confirmed=false;
       state.page=1;
       state.notice=response.integrated+' ligne(s) intégrée(s). Résultat conservé dans l’historique.';
       reload();
     }catch(err){
       state.notice='Import refusé : '+(err?.message||'Erreur inconnue.');
       closeModal();state.preview=null;state.confirmed=false;render();
     }finally{state.submitting=false}
   }
   function selectFile(input){
     const file=input.files?.[0];
     if(!file)return;
     if(!/\.(csv|xlsx)$/i.test(file.name)||file.size>2*1024*1024){
       state.notice='Format CSV/XLSX uniquement, 2 Mo maximum.';render();return;
     }
     state.file=file;state.preview=null;state.notice='';render();
   }
   function action(element){
     const action=element.dataset.e58Action;
     const kind=element.dataset.e58Type;
     if(kind&&Object.hasOwn(types,kind)){
       state.kind=kind;state.file=null;state.preview=null;state.notice='';
       state.school='';render();return;
     }
     if(action==='template'){downloadTemplate();return}
     if(action==='preview'){void preview();return}
     if(action==='execute'){void execute();return}
     if(action==='refresh'){reload();return}
     if(action==='prev'&&state.page>1){state.page--;reload();return}
     if(action==='next'&&state.page<state.pages){state.page++;reload();return}
   }
   function onChange(element){
     if(element.matches('[data-e58-file]')){selectFile(element);return}
     if(element.matches('[data-e58-school]')){state.school=element.value;state.preview=null;return}
     if(element.matches('[data-e58-filter]')){state.historyType=element.value;state.page=1;reload();return}
     if(element.matches('[data-e58-confirm]')){
       state.confirmed=element.checked;
       const button=modal?.querySelector('[data-e58-action="execute"]');
       if(button)button.disabled=!state.confirmed;
     }
   }
   function onInput(element){
     if(!element.matches('[data-e58-school-query]'))return;
     clearTimeout(searchTimer);const value=element.value.slice(0,80);
     searchTimer=setTimeout(()=>{state.schoolQuery=value;state.school='';reload()},350);
   }
   return {page,ensure,load,action,onChange,onInput,peek:()=>({
     ready:state.ready,count:state.count,error:state.error,kind:state.kind,
   })};
 };
})();
