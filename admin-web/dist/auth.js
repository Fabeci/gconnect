'use strict';
/* UI states only. Permissions and account activation remain server decisions. */
(() => {
 const api = window.GConnectEstablishmentApi;
 const roles = {
  community: {label:'Étudiant / Alumni', title:'Votre prochain chapitre commence ici.', story:'Des rencontres.<br>Des opportunités.<br><em>Votre avenir.</em>', copy:'Gardez le lien avec votre campus et les talents qui font grandir votre réseau.', accepts:['student','alumni']},
  etablissement: {label:'Établissement', title:'Votre campus vous attend.', story:'Un campus.<br>Une communauté.<br><em>Mille possibles.</em>', copy:'Réunissez vos étudiants, vos diplômés et votre équipe dans un même espace.', accepts:['etablissement']},
  superadmin: {label:'Superadmin', title:'Une vision d’ensemble, un accès dédié.', story:'Le réseau grandit.<br><em>Vous gardez le cap.</em>', copy:'Retrouvez votre accès à l’administration de la communauté G-Connect.', accepts:['superAdmin']}
 };
 const screens = new Set(['welcome','login','invitation','activate','activated','mfa-setup','mfa-verify','mfa-recovery','forgot','reset','verify','verified','register','details','credentials','pending','session','logout','signedout']);
 let root, onEstablishment, busy=false, profile=null, role='community', screen='welcome', userId=null, email='', registration={}, kind='student', notice='', currentHash='', cooldown=0, timer;
 let challenge=null, mfaSecret=null, recoveryCodes=[], pendingSession=null, inviteToken=null, invitePreview=null, invites=[];
 const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const link = (target,text) => `<button class="auth-link" type="button" data-go="${target}">${text}</button>`;
 function field(name,label,type='text',autocomplete='off',extra='') {
  const input=`<input id="auth-${name}" name="${name}" type="${type}" autocomplete="${autocomplete}" ${extra} required>`;
  return `<div class="auth-field"><label for="auth-${name}">${label}</label>${type==='password'?`<span class="auth-password">${input}<button type="button" data-password="auth-${name}" aria-label="Afficher ${label.toLowerCase()}" aria-pressed="false">Afficher</button></span>`:input}</div>`;
 }
 const emailField=()=>field('email','Adresse e-mail','email','username',`maxlength="254" value="${esc(email)}" placeholder="vous@exemple.com"`);
 const otpField=()=>field('otp','Code à 6 chiffres','text','one-time-code','inputmode="numeric" pattern="[0-9]{6}" maxlength="6" placeholder="000000"');
 const passwordField=()=>field('password','Mot de passe','password','new-password','minlength="8" aria-describedby="password-help"')+'<p class="auth-hint" id="password-help">Au moins 8 caractères. Évitez les mots de passe courants et vos informations personnelles.</p>'+field('confirm','Confirmer le mot de passe','password','new-password','minlength="8"');
 const submit=text=>`<button class="btn primary auth-full" type="submit">${text} <span aria-hidden="true">→</span></button>`;
 const form=(fields,label)=>`<form class="auth-form" id="auth-form">${fields}${submit(label)}</form>`;
 const adminScreens=new Set(['login','invitation','activate','activated','mfa-setup','mfa-verify','mfa-recovery','forgot','reset','session','logout','signedout']);
 function go(next, nextRole=role) {
  if(busy)return;
  notice='';
  if(next==='welcome'){registration={};userId=null;email='';}
  if(next==='login' || next==='welcome'){challenge=null;mfaSecret=null;recoveryCodes=[];pendingSession=null;inviteToken=null;invitePreview=null;}
  location.hash=`${next}/${nextRole}`;
 }
 function readRoute(){
  if(busy){history.replaceState(null,'',currentHash);return;}
  const [next,r]=location.hash.slice(1).split('/');
  const path=location.pathname;
  const dedicatedRole=path==='/superadmin'?'superadmin':path==='/entreprise'?'entreprise':path==='/etablissement'?'etablissement'
    :path.endsWith('/superadmin-login.html')?'superadmin'
   :(path.endsWith('/etablissement.html')||path.endsWith('/etablissement-connexion.html')||path.endsWith('/etablissement-activation.html'))?'etablissement':null;
  // Older shared URLs remain usable, but admins enter through their own portals.
  if(path.endsWith('/auth.html')&&next!=='welcome'&&(r==='etablissement'||r==='superadmin')){
   const landing=['login','invitation','forgot','signedout'].includes(next)?next:'login';
   const page=r==='etablissement'?'/etablissement.html':'/superadmin-login.html';
   location.replace(page+'#'+landing+'/'+r);
   return;
  }
  role=dedicatedRole||(next==='welcome'?'community':(roles[r]?r:'community'));
  screen=dedicatedRole&&next==='welcome'?'login'
   :(screens.has(next)?next:(dedicatedRole?'login':'welcome'));
  if(dedicatedRole&&!adminScreens.has(screen))screen='login';
  if(role==='superadmin'&&['invitation','activate','activated'].includes(screen))screen='login';
  if(['details','credentials'].includes(screen)&&!registration.institution_id)screen='register';
  if(['register','details','credentials'].includes(screen)&&role!=='community')screen='invitation';
  if(['mfa-setup','mfa-verify'].includes(screen)&&!challenge)screen='login';
  if(screen==='mfa-recovery'&&(!pendingSession||!recoveryCodes.length))screen='login';
  if(screen==='activate'&&!inviteToken)screen='invitation';
  if(['session','logout'].includes(screen)){
   if(!profile || !api.isConnected()){profile=null;screen='login';notice='Votre session n’est plus disponible. Reconnectez-vous.';}
   else role=Object.keys(roles).find(r=>roles[r].accepts.includes(profile.role))||'community';
  }
  currentHash=`#${screen}/${role}`;
  history.replaceState(null,'',currentHash);
  render();
 }
 function content(){
  if(role!=='community'&&screen!=='session')return adminContent();
  const intro=(title,description)=>`<p class="auth-kicker">${esc(roles[role].label)}</p><h1 id="auth-title" tabindex="-1">${title}</h1><p>${description}</p>`;
  const back=link('login','← Retour à la connexion');
  switch(screen){
   case 'welcome': return `<p class="auth-kicker">Bienvenue sur G-Connect</p><h1 id="auth-title" tabindex="-1">Le bon réseau.<br>Les bonnes connexions.</h1><p>Choisissez votre espace pour commencer.</p><div class="auth-role-list">${[['community','↗','Étudiant / Alumni','Votre réseau de campus et de diplômés.'],['etablissement','▦','Établissement','Administration du campus · sur invitation.'],['superadmin','◇','Superadmin','Pilotage G-Connect · accès interne réservé.']].map(([r,i,t,d])=>`<button class="auth-role" data-role="${r}"><span aria-hidden="true">${i}</span><span><strong>${t}</strong><small>${d}</small></span><span aria-hidden="true">→</span></button>`).join('')}</div><p class="auth-divider">Un seul réseau. Un espace adapté à votre rôle.</p>`;
   case 'login':return (role==='community'?link('welcome','← Changer d’espace'):'<a class="auth-link" href="/index.html">← Retour à l’accueil G-Connect</a>')+intro('Heureux de vous retrouver.',roles[role].title)+form(emailField()+field('password','Mot de passe','password','current-password')+`<div class="auth-links">${link('forgot','Mot de passe oublié ?')}</div>`,'Se connecter')+`<div class="auth-divider">${role==='community'?`Pas encore de compte ? ${link('register','Rejoindre G-Connect')}`:role==='etablissement'?`Les comptes administrateurs sont accessibles uniquement sur invitation. ${link('invitation','J’ai une invitation')}`:'Accès réservé aux administrateurs habilités. Pour obtenir un accès, contactez votre responsable G-Connect.'}</div>`+ (role==='community'?link('verify','Vérifier mon adresse e-mail'):'');
   case 'invitation':return back+intro('Un accès sur invitation.','Votre Superadmin vous invite par e-mail à administrer votre établissement.')+'<div class="auth-status">Ouvrez le lien personnel reçu dans votre boîte e-mail : il est valable 48 heures et ne peut être utilisé qu’une fois. Il confirme votre adresse et vous permet de définir votre mot de passe.</div><p>Vous disposez déjà d’un compte activé ? Connectez-vous avec votre adresse professionnelle.</p>'+link('login','Accéder à la connexion');
   case 'activate':return intro('Activez votre espace.','Cette invitation a été envoyée à votre adresse professionnelle.')+(invitePreview?'<div class="auth-session"><strong>'+esc(invitePreview.institution)+'</strong><span>'+esc(invitePreview.email)+'</span></div>'+form('<div class="auth-grid">'+field('first_name','Prénom','text','given-name')+field('last_name','Nom','text','family-name')+'</div>'+passwordField(),'Activer mon compte'):'<div class="auth-status">Vérification sécurisée de votre invitation…</div>');
   case 'activated':return '<div class="auth-check" aria-hidden="true">✓</div>'+intro('Votre adresse est confirmée.','Votre compte établissement est activé. Connectez-vous maintenant, puis configurez votre double authentification.')+link('login','Se connecter');
   case 'mfa-setup':return link('login','← Recommencer la connexion')+intro('Protégez votre compte.','Installez une application d’authentification (Google Authenticator, Microsoft Authenticator ou équivalent), puis ajoutez ce compte avec la clé ci-dessous.')+'<div class="auth-session auth-mfa-secret"><strong>Votre clé de configuration personnelle</strong><code>'+esc(mfaSecret||'')+'</code></div><p class="auth-hint">Ne partagez jamais cette clé. Elle permet de générer vos codes de connexion.</p>'+form(field('otp','Code à 6 chiffres','text','one-time-code','inputmode="numeric" pattern="[0-9]{6}" maxlength="6" placeholder="000000"'),'Activer la double authentification');
   case 'mfa-verify':return link('login','← Recommencer la connexion')+intro('Vérification de sécurité.','Ouvrez votre application d’authentification et indiquez le code affiché. Vous pouvez également utiliser un code de secours à usage unique.')+form(field('mfa_code','Code d’authentification ou de secours','text','one-time-code','maxlength="40" placeholder="Code à 6 chiffres ou code de secours"'),'Vérifier et accéder');
   case 'mfa-recovery':return '<div class="auth-check" aria-hidden="true">✓</div>'+intro('Sauvegardez vos codes de secours.','Ils ne s’afficheront plus. Chacun permet de vous reconnecter une seule fois si vous perdez votre application d’authentification.')+'<div class="auth-recovery" aria-label="Codes de secours personnels">'+recoveryCodes.map(code=>'<code>'+esc(code)+'</code>').join('')+'</div><p class="auth-hint">Conservez-les dans un gestionnaire de mots de passe ou un endroit sûr, hors de cet ordinateur partagé.</p>'+form('','J’ai sauvegardé mes codes, continuer');
   case 'forgot':return back+intro('Retrouvons votre accès.','Saisissez l’adresse e-mail de votre compte. Le code de récupération sera envoyé par SMS au numéro associé.')+form(emailField(),'Recevoir le code')+'<p class="auth-divider">Vous n’avez plus accès à ce numéro ? Contactez votre administrateur G-Connect.</p>';
   case 'reset':return back+intro('Un nouveau départ.','Si votre compte est éligible, un code vous a été envoyé par SMS. Il est valable 30 minutes.')+(userId?form(otpField()+passwordField(),'Enregistrer le mot de passe'):'<div class="auth-status">Si vous ne recevez aucun code, vérifiez votre adresse ou contactez votre administrateur.</div>')+link('forgot','Recommencer la récupération');
   case 'verify':return back+intro('Vérifiez votre e-mail.','Saisissez le code reçu par e-mail pour activer votre compte étudiant. Le code est valable 15 minutes.')+(userId?form(otpField(),'Vérifier mon e-mail')+`<button class="auth-link" id="auth-resend" type="button">Renvoyer le code</button>`:'<div class="auth-status">Ouvrez le lien fourni lors de votre inscription ou terminez votre inscription pour vérifier votre e-mail.</div>'+link('register','Reprendre mon inscription'));
   case 'verified':return '<div class="auth-check" aria-hidden="true">✓</div>'+intro('Tout est prêt.','Votre adresse e-mail a été vérifiée. Connectez-vous pour retrouver votre communauté.')+link('login','Se connecter');
   case 'register':return back+intro('Votre réseau commence ici.','Rejoignez votre établissement en quelques étapes.')+'<div class="auth-steps" role="img" aria-label="Étape 1 sur 3"><span class="active"></span><span></span><span></span></div>'+form('<label class="auth-field" for="auth-kind"><span>Votre profil</span><select id="auth-kind" name="kind"><option value="student">Étudiant</option><option value="alumni">Alumni / Diplômé</option></select></label>'+field('code','Code de votre établissement','text','off','placeholder="Code fourni par votre établissement"'),'Continuer')+'<p class="auth-divider">Vous ne connaissez pas ce code ? Demandez-le à votre établissement.</p>';
   case 'details':return link('register','← Mon établissement')+intro('Faisons connaissance.',`Votre établissement : ${esc(registration.institution_name)}`)+'<div class="auth-steps" role="img" aria-label="Étape 2 sur 3"><span class="active"></span><span class="active"></span><span></span></div>'+form('<div class="auth-grid">'+field('first_name','Prénom','text','given-name')+field('last_name','Nom','text','family-name')+'</div>'+field('username','Nom d’utilisateur','text','username')+emailField()+'<div class="auth-grid">'+field('phone_number','Téléphone','tel','tel','placeholder="+221…"')+'<label class="auth-field" for="auth-gender"><span>Genre</span><select id="auth-gender" name="gender" required><option value="">Sélectionner</option><option value="M">Masculin</option><option value="F">Féminin</option><option value="O">Autre</option></select></label></div>'+(kind==='student'?'<div class="auth-grid">'+field('date_of_birth','Date de naissance','date','bday')+field('student_id','Matricule étudiant')+'</div>':field('proof_document','Justificatif de diplôme','file','off')+'<p class="auth-hint">Votre justificatif sera examiné par l’administration avant activation du compte.</p>'),'Continuer');
   case 'credentials':return link('details','← Mes informations')+intro('Protégez votre compte.','Choisissez un mot de passe personnel pour sécuriser votre accès.')+'<div class="auth-steps" role="img" aria-label="Étape 3 sur 3"><span class="active"></span><span class="active"></span><span class="active"></span></div>'+form(passwordField(),'Créer mon compte');
   case 'pending':return '<div class="auth-check" aria-hidden="true">✓</div>'+intro('Votre demande est envoyée.','Votre compte alumni sera activé après vérification de votre justificatif par l’administration.')+link('login','Retour à la connexion');
   case 'session':return '<div class="auth-check" aria-hidden="true">✓</div>'+intro(`Bienvenue${profile.first_name?', '+esc(profile.first_name):''}.`,'Vous êtes connecté à votre compte G-Connect.')+`<div class="auth-session"><strong>${esc(roles[role].label)}</strong><span>${esc(profile.email)}</span></div>`+(role==='superadmin'?'<h2 class="auth-section-title">Inviter un responsable d’établissement</h2><p class="auth-hint">Choisissez l’identifiant de l’établissement actif et son adresse e-mail professionnelle. Le serveur enverra un lien valable 48 heures.</p><form class="auth-form" id="auth-invite-form">'+field('invite_institution','Identifiant de l’établissement','number','off','min="1" step="1"')+field('invite_email','Adresse e-mail du responsable','email','email')+submit('Envoyer une invitation')+'</form><h2 class="auth-section-title">Invitations récentes</h2><button type="button" class="auth-link" id="auth-invites-refresh">Actualiser la liste</button><ul class="auth-invites">'+(invites.length?invites.map(inv=>'<li><div><strong>'+esc(inv.institution_name)+'</strong><span>'+esc(inv.email)+'</span><small>'+esc(inv.accepted?'Activée':inv.revoked?'Révoquée':new Date(inv.expires_at).getTime()<=Date.now()?'Expirée':'En attente')+'</small></div>'+(!inv.accepted&&!inv.revoked&&new Date(inv.expires_at).getTime()>Date.now()?'<button class="auth-link" type="button" data-revoke="'+Number(inv.id)+'">Révoquer</button>':'')+'</li>').join(''):'<li>Aucune invitation à afficher.</li>')+'</ul>':'<p class="auth-hint">L’espace communautaire web reste un aperçu ; utilisez votre application habituelle pour vos activités.</p>')+link('logout','Se déconnecter');
   case 'logout':return intro('Fermer votre session ?','Vous pourrez vous reconnecter à tout moment.')+form('','Oui, me déconnecter')+link('session','Rester connecté');
   case 'signedout':return '<div class="auth-check" aria-hidden="true">✓</div>'+intro('À très bientôt.','Votre session sur ce navigateur est fermée.')+link('login','Se reconnecter')+(role==='community'?link('welcome','Changer d’espace'):'<a class="auth-link" href="/index.html">Retour à l’accueil</a>');
  }
 }
 function adminContent(){
  const intro=(title,description)=>`<p class="auth-kicker">${role==='etablissement'?'Espace Établissement':'Administration générale'}</p><h1 id="auth-title" tabindex="-1">${title}</h1><p class="auth-description">${description}</p>`;
  const back=link('login','Retour à la connexion');
  const recoveryHelp='La récupération utilise le numéro de téléphone associé à votre compte. Sans accès à ce numéro, contactez votre responsable G-Connect.';
  switch(screen){
   case 'login':return intro('Connectez-vous',role==='etablissement'?'Accédez à votre espace de gestion avec votre compte professionnel.':'Accédez à l’administration G-Connect avec votre compte habilité.')+form(emailField()+field('password','Mot de passe','password','current-password')+`<div class="auth-links">${link('forgot','Mot de passe oublié ?')}</div>`,'Se connecter')+`<div class="auth-divider">${role==='etablissement'?'<span>Première connexion ?</span>'+link('invitation','Activer mon compte'):'Accès réservé aux administrateurs habilités.'}</div>`;
   case 'invitation':return intro('Activez votre accès','Votre compte Établissement est créé sur invitation.')+'<div class="auth-status">Ouvrez le lien reçu par e-mail pour confirmer votre adresse et choisir votre mot de passe. Ce lien est personnel et valable 48 heures.</div><p class="auth-hint">Invitation absente ou expirée ? Contactez votre responsable G-Connect pour obtenir un nouveau lien.</p>'+back;
   case 'activate':return intro('Bienvenue dans votre espace','Confirmez vos informations et choisissez votre mot de passe.')+(invitePreview?'<div class="auth-session"><strong>'+esc(invitePreview.institution)+'</strong><span>'+esc(invitePreview.email)+'</span></div>'+form('<div class="auth-grid">'+field('first_name','Prénom','text','given-name')+field('last_name','Nom','text','family-name')+'</div>'+passwordField(),'Activer mon compte'):'<div class="auth-status">Vérification de votre invitation…</div>')+back;
   case 'activated':return intro('Votre compte est activé','Votre adresse e-mail est confirmée. Connectez-vous pour configurer votre double authentification.')+back;
   case 'mfa-setup':return intro('Sécurisez votre compte','Ajoutez cette clé dans votre application d’authentification, puis saisissez le code qu’elle affiche.')+'<div class="auth-session auth-mfa-secret"><strong>Clé de configuration</strong><code>'+esc(mfaSecret||'')+'</code></div><p class="auth-hint">Utilisez une application comme Google Authenticator ou Microsoft Authenticator. Gardez cette clé confidentielle.</p>'+form(otpField(),'Activer la double authentification')+back;
   case 'mfa-verify':return intro('Vérifiez votre identité','Saisissez le code de votre application d’authentification ou l’un de vos codes de secours.')+form(field('mfa_code','Code d’authentification ou de secours','text','one-time-code','maxlength="40" spellcheck="false" autocapitalize="off" placeholder="Votre code"'),'Vérifier et accéder')+'<p class="auth-hint">Chaque code de secours ne peut être utilisé qu’une fois.</p>'+back;
   case 'mfa-recovery':return intro('Conservez vos codes','Ces codes permettent de vous connecter si vous perdez l’accès à votre application d’authentification.')+'<div class="auth-recovery" aria-label="Codes de secours personnels">'+recoveryCodes.map(code=>'<code>'+esc(code)+'</code>').join('')+'</div><p class="auth-hint">Ils ne s’afficheront plus. Enregistrez-les dans un endroit sûr. Chaque code est à usage unique.</p>'+form('','J’ai sauvegardé mes codes, continuer');
   case 'forgot':return intro('Mot de passe oublié ?','Indiquez votre adresse e-mail pour recevoir un code de récupération par SMS.')+form(emailField(),'Recevoir le code')+'<p class="auth-divider">'+recoveryHelp+'</p>'+back;
   case 'reset':return intro('Nouveau mot de passe','Si votre compte est éligible, un code vous a été envoyé par SMS. Il est valable 30 minutes.')+(userId?form(otpField()+passwordField(),'Enregistrer le mot de passe'):'<div class="auth-status">Si vous ne recevez aucun code, vérifiez votre adresse ou contactez votre responsable G-Connect.</div>')+link('forgot','Recommencer la récupération')+back;
   case 'logout':return intro('Fermer votre session ?','Vous pourrez vous reconnecter avec votre mot de passe et votre code de sécurité.')+form('','Oui, me déconnecter')+link('session','Rester connecté');
   case 'signedout':return intro('Vous êtes déconnecté','Votre session sur ce navigateur est fermée.')+link('login','Se reconnecter');
  }
 }
 function adminShell(){
  return `<div class="auth-shell auth-admin"><main class="auth-layout" id="gc-main"><section class="auth-card" aria-labelledby="auth-title"><div class="auth-brand-row"><a class="auth-brand" href="/index.html" aria-label="G-Connect — accueil"><img src="/assets/logo.png" alt="G-Connect" width="145" height="40"></a><button class="auth-theme-toggle" id="auth-theme-toggle" type="button" aria-label="Activer le thème sombre" aria-pressed="false" title="Changer le thème"><svg class="auth-theme-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"></svg><span class="auth-theme-text">Mode sombre</span></button></div><div class="auth-step" data-step="${screen}">${content()}<div class="auth-alert" id="auth-error" role="alert" tabindex="-1"></div><div class="auth-status" id="auth-status" role="status">${esc(notice)}</div></div></section><footer class="auth-footer">G-Connect · ${role==='etablissement'?'Espace Établissement':'Administration générale'}</footer></main></div>`;
 }
 function render(){
  document.body.classList.remove('ea-menu-open');
  clearInterval(timer);
  document.title=({welcome:'Bienvenue',login:'Connexion',invitation:'Invitation',activate:'Activation',activated:'Compte activé','mfa-setup':'Sécuriser le compte','mfa-verify':'Code de sécurité','mfa-recovery':'Codes de secours',forgot:'Récupération',reset:'Nouveau mot de passe',verify:'Vérification e-mail',verified:'E-mail vérifié',register:'Inscription',details:'Vos informations',credentials:'Sécurité',pending:'Demande envoyée',session:'Mon compte',logout:'Déconnexion',signedout:'Session fermée'}[screen])+ ' · G-Connect';
  if (role==='superadmin' && screen==='session' && profile?.role==='superAdmin' && api.isConnected()) {
   root.innerHTML='<div class="auth-shell sa-live-shell"><div id="sa-live-root"></div></div>';
   if(!window.GConnectSuperadminConsole)throw new Error('Console Superadmin indisponible.');
   window.GConnectSuperadminConsole.mount(root.querySelector('#sa-live-root'),{
    onLogout:()=>go('logout'),
    onExpired:()=>{
     window.GConnectSuperadminConsole?.unmount();
     api.disconnect();profile=null;challenge=null;pendingSession=null;
     show('login','Votre session a expiré. Reconnectez-vous.');
    }
   });
   return;
  }
  window.GConnectSuperadminConsole?.unmount();
  root.innerHTML=role!=='community'?adminShell():`<div class="auth-shell"><header class="auth-header"><a href="/index.html" aria-label="G-Connect — accueil"><img src="/assets/logo.png" alt="G-Connect" width="145" height="40"></a><div class="auth-header-actions"><button class="auth-theme-toggle" id="auth-theme-toggle" type="button" aria-label="Activer le thème sombre" aria-pressed="false" title="Changer le thème"><svg class="auth-theme-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.4 14.6a8.6 8.6 0 0 1-11-11 8.7 8.7 0 1 0 11 11Z"/></svg><span class="auth-theme-text">Mode sombre</span></button><a class="auth-home" href="/index.html">Découvrir G-Connect <span aria-hidden="true">↗</span></a></div></header><main class="auth-layout" id="gc-main"><aside class="auth-story" aria-label="Votre communauté G-Connect"><span class="auth-kicker">Le lien qui fait la différence</span><h2>${roles[role].story}</h2><p>${roles[role].copy}</p><div class="auth-photo"><img src="/assets/hero-gconnect.jpg" alt="Un jeune professionnel avec son ordinateur" width="800" height="900"></div><div class="auth-note"><b aria-hidden="true">↗</b><span>Étudiants, alumni, établissements.<br>Avançons ensemble.</span></div></aside><section class="auth-card" aria-labelledby="auth-title">${content()}<div class="auth-alert" id="auth-error" role="alert" tabindex="-1"></div><div class="auth-status" id="auth-status" role="status">${esc(notice)}</div></section></main><footer class="auth-footer"><span>© G-Connect · Votre réseau, votre avenir.</span><span>Un espace pour chaque ambition.</span></footer></div>`;
  const authThemeToggle=root.querySelector('#auth-theme-toggle');
  const syncAuthTheme=()=>{
   if(!authThemeToggle)return;
   const dark=document.documentElement.dataset.theme==='dark';
   authThemeToggle.setAttribute('aria-pressed',String(dark));
   authThemeToggle.setAttribute('aria-label',dark?'Activer le thème clair':'Activer le thème sombre');
   authThemeToggle.querySelector('.auth-theme-text').textContent=dark?'Mode clair':'Mode sombre';
   authThemeToggle.querySelector('.auth-theme-icon').innerHTML=dark
    ?'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>'
    :'<path d="M20.4 14.6a8.6 8.6 0 0 1-11-11 8.7 8.7 0 1 0 11 11Z"/>';
  };
  if(authThemeToggle){
   try{
    const saved=localStorage.getItem('gconnect_auth_theme');
    if(saved==='dark'||saved==='light')document.documentElement.dataset.theme=saved;
    else if(role!=='community')document.documentElement.dataset.theme=window.matchMedia?.('(prefers-color-scheme: dark)').matches?'dark':'light';
   }catch{ /* Appearance is optional in private browsing. */ }
   syncAuthTheme();
   authThemeToggle.onclick=()=>{
    const next=document.documentElement.dataset.theme==='dark'?'light':'dark';
    document.documentElement.dataset.theme=next;
    try{localStorage.setItem('gconnect_auth_theme',next)}catch{}
    syncAuthTheme();
   };
  }
  root.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>go(b.dataset.go));
  root.querySelectorAll('[data-role]').forEach(b=>b.onclick=()=>{
   const selected=b.dataset.role;
   if(selected==='etablissement')location.assign('/etablissement#login/etablissement');
   else if(selected==='superadmin')location.assign('/superadmin#login/superadmin');
   else go('login','community');
  });
  root.querySelectorAll('[data-password]').forEach(b=>b.onclick=()=>{const input=document.getElementById(b.dataset.password);const show=input.type==='password';input.type=show?'text':'password';b.textContent=show?'Masquer':'Afficher';b.setAttribute('aria-pressed',String(show));b.setAttribute('aria-label',show?'Masquer le mot de passe':'Afficher le mot de passe');});
  const f=document.getElementById('auth-form');
  if(f){f.onsubmit=handleSubmit;f.oninput=e=>{e.target.removeAttribute('aria-invalid');if(e.target.name==='confirm'||e.target.name==='password')f.elements.confirm?.setCustomValidity('');if(!busy)document.getElementById('auth-error').textContent='';};
   f.addEventListener('invalid',e=>{e.target.setAttribute('aria-invalid','true');},true);
   if(screen==='details')for(const [key,value] of Object.entries(registration)){const el=f.elements.namedItem(key);if(el&&el.type!=='file')el.value=value;}
  }
  const inviteForm=document.getElementById('auth-invite-form');
  if(inviteForm)inviteForm.onsubmit=async event=>{
   event.preventDefault();
   if(busy||!inviteForm.reportValidity())return;
   const values=Object.fromEntries(new FormData(inviteForm));
   await run(async()=>{
    await api.sendInvitation(values.invite_email.trim(),Number(values.invite_institution));
    invites=await api.listInvitations();
    show('session','Invitation envoyée par e-mail au responsable.');
   });
  };
  const refreshButton=document.getElementById('auth-invites-refresh');
  if(refreshButton)refreshButton.onclick=()=>run(async()=>{invites=await api.listInvitations();show('session','Liste actualisée.');});
  root.querySelectorAll('[data-revoke]').forEach(button=>button.onclick=()=>run(async()=>{
   await api.revokeInvitation(Number(button.dataset.revoke));
   invites=await api.listInvitations();show('session','Invitation révoquée.');
  }));
  const resend=document.getElementById('auth-resend');
  if(resend){resend.onclick=()=>run(async()=>{await api.publicRequest('/users/otp/resend/',{user_id:userId});cooldown=Date.now()+60000;notice='Un nouveau code a été envoyé à votre adresse e-mail.';render();});const tick=()=>{const left=Math.max(0,Math.ceil((cooldown-Date.now())/1000));resend.disabled=!!left||busy;resend.textContent=left?`Renvoyer dans ${left} s`:'Renvoyer le code';};tick();timer=setInterval(tick,1000);}
  document.getElementById('auth-title')?.focus({preventScroll:true});
 }
 async function run(action){
  if(busy)return;busy=true;
  const error=document.getElementById('auth-error');error.textContent='';
  const form=document.getElementById('auth-form');form?.setAttribute('aria-busy','true');
  const controls=[...root.querySelectorAll('button')];controls.forEach(b=>b.disabled=true);
  const status=document.getElementById('auth-status');status.textContent='Traitement en cours…';
  try{await action();}catch(e){
   if(role!=='community'&&/session.*expir/i.test(e.message||'')){
    api.disconnect();profile=null;challenge=null;mfaSecret=null;recoveryCodes=[];pendingSession=null;
    show('login','Votre session a expiré. Reconnectez-vous.');
    return;
   }
   const feedback=role==='community'?(e.message||'Une erreur est survenue. Réessayez.'):adminError(e.message);
   if(screen==='activate'&&!invitePreview){inviteToken=null;show('invitation');}
   // A request can replace the current step before failing. Use its live region.
   const currentError=document.getElementById('auth-error');
   currentError.textContent=feedback;
   currentError.focus();
   document.getElementById('auth-status').textContent='';
  }
  finally{busy=false;form?.removeAttribute('aria-busy');controls.filter(b=>b.isConnected).forEach(b=>b.disabled=false);if(status.isConnected&&status.textContent==='Traitement en cours…')status.textContent='';}
 }
 function adminError(message=''){
  if(/trop|tentatives|patientez|verrouill/i.test(message))return 'Trop de tentatives. Patientez quelques minutes avant de réessayer.';
  if(/session.*expir/i.test(message))return 'Votre session a expiré. Reconnectez-vous.';
  if(/autre espace|non autorisé/i.test(message))return 'Ce compte ne permet pas d’accéder à cet espace. Utilisez votre compte habilité.';
  if(/serveur|backend|configur|Twilio|réseau|incompatible/i.test(message))return 'Le service est momentanément indisponible. Réessayez dans quelques instants.';
  if(screen==='activate')return invitePreview?'Cette invitation ne peut pas être utilisée ou les informations saisies ne sont pas valides. Vérifiez votre saisie ou demandez un nouveau lien.':'Cette invitation est invalide ou a expiré. Demandez un nouveau lien à votre responsable G-Connect.';
  if(screen==='forgot')return 'La récupération n’a pas pu aboutir. Vérifiez votre saisie ou contactez votre responsable G-Connect.';
  if(screen==='reset')return 'Vérifiez votre code et choisissez un mot de passe suffisamment sûr. Si le code a expiré, recommencez la récupération.';
  if(screen.startsWith('mfa-'))return 'Le code n’a pas pu être validé. Vérifiez-le ou recommencez la connexion.';
  return 'Connexion impossible. Vérifiez vos identifiants et réessayez.';
 }
 function show(next,message=''){screen=next;notice=message;currentHash=`#${next}/${role}`;history.replaceState(null,'',currentHash);render();}
 async function handleSubmit(event){
  event.preventDefault();const f=event.currentTarget;if(busy||!f.reportValidity())return;
  const data=Object.fromEntries(new FormData(f));
  if(data.confirm!==undefined&&data.confirm!==data.password){f.elements.confirm.setCustomValidity('Les mots de passe ne correspondent pas.');f.elements.confirm.reportValidity();return;}
  await run(async()=>{
   if(screen==='login'){
    email=data.email.trim();
    if(role!=='community'){
     const start=await api.startPrivilegedLogin(email,data.password);
     challenge=start.challenge;
     if(start.action==='enroll'){
      const setup=await api.beginMfaSetup(challenge);
      mfaSecret=setup.secret;
      show('mfa-setup');
     }else{mfaSecret=null;show('mfa-verify');}
     return;
    }
    const result=await api.connectAccount(email,data.password,roles[role].accepts);profile=result.profile;show('session');
   }else if(screen==='activate'){
    if(!inviteToken||!invitePreview)throw new Error('Invitation invalide. Demandez un nouveau lien.');
    const result=await api.acceptInvitation(inviteToken,data.password,data.first_name.trim(),data.last_name.trim());
    email=result.email||invitePreview.email;
    inviteToken=null;invitePreview=null;
    show('activated','Votre adresse est vérifiée.');
   }else if(screen==='mfa-setup'||screen==='mfa-verify'){
    const result=await api.finishMfa(challenge,screen==='mfa-setup'?data.otp:data.mfa_code,roles[role].accepts);
    challenge=null;mfaSecret=null;
    profile=result.profile;
    if(result.recovery_codes?.length){
     recoveryCodes=[...result.recovery_codes];
     pendingSession={profile:result.profile,stats:result.stats};
     show('mfa-recovery');
    }else{
     await enterAuthenticatedArea(result);
    }
   }else if(screen==='mfa-recovery'){
    if(!pendingSession)throw new Error('Session indisponible. Reconnectez-vous.');
    const result=pendingSession;pendingSession=null;recoveryCodes=[];
    await enterAuthenticatedArea(result);
   }else if(screen==='forgot'){
    email=data.email.trim();const result=await api.publicRequest('/users/forgot-password/',{email});userId=result?.user_id||null;show('reset');
   }else if(screen==='reset'){
    await api.publicRequest('/users/reset-password/',{user_id:userId,otp:data.otp,new_password:data.password});userId=null;show('login','Votre mot de passe a été modifié. Vous pouvez vous reconnecter.');
   }else if(screen==='verify'){
    await api.publicRequest('/users/verify-otp/',{user_id:userId,otp:data.otp});userId=null;show('verified');
   }else if(screen==='register'){
    kind=data.kind;const result=await api.publicRequest('/users/register/student/check-code/',{code:data.code.trim()});registration={...result};show('details');
   }else if(screen==='details'){
    registration={...registration,...data};email=data.email.trim();registration.email=email;show('credentials');
   }else if(screen==='credentials'){
    const {institution_name,...payload}=registration;payload.password=data.password;
    let result;
    if(kind==='alumni'){const body=new FormData();for(const [key,value] of Object.entries(payload))if(key!=='session_token')body.append(key,value);result=await api.publicRequest('/users/register/alumni/',body);}
    else result=await api.publicRequest('/users/register/student/',payload);
    userId=result?.user_id||null;registration={};show(kind==='alumni'?'pending':'verify');
   }else if(screen==='logout'){await finishLogout();}
  });
 }
 async function enterAuthenticatedArea(result){
  if(role==='etablissement'){
   if(typeof onEstablishment!=='function')throw new Error('Portail établissement indisponible.');
   await onEstablishment(result);
  }else if(role==='superadmin'){
   // Live Superadmin workspace fetches invitation data with the in-memory WebToken.
   show('session');
  }else{show('session');}
 }
 async function finishLogout(){
  let warning='';try{await api.logout();}catch(e){warning=role==='community'?'La session locale est fermée, mais la révocation côté serveur n’a pas pu être confirmée. '+e.message:'Vous êtes déconnecté de ce navigateur. La fermeture de la session distante n’a pas pu être confirmée ; réessayez lorsque le service est disponible.';}
  profile=null;registration={};userId=null;email='';challenge=null;mfaSecret=null;recoveryCodes=[];pendingSession=null;inviteToken=null;invitePreview=null;invites=[];show('signedout',warning);
 }
 window.addEventListener('pagehide',()=>{profile=null;registration={};userId=null;email='';challenge=null;mfaSecret=null;recoveryCodes=[];pendingSession=null;inviteToken=null;invitePreview=null;invites=[];clearInterval(timer);});
 window.addEventListener('hashchange',()=>{if(root?.querySelector('.auth-shell'))readRoute();});
 window.GConnectAuth={
  mount(target,callback){
   root=target;onEstablishment=callback;
   // Activation secrets only arrive in a URL fragment: remove it before any requests or logs.
   if(location.pathname.endsWith('/etablissement-activation.html')){
    role='etablissement';screen='activate';
    const match=/^#invitation=([A-Za-z0-9_-]{30,128})$/.exec(location.hash);
    history.replaceState(null,'',location.pathname);
    if(!match){screen='invitation';render();return;}
    inviteToken=match[1];invitePreview=null;render();
    run(async()=>{invitePreview=await api.previewInvitation(inviteToken);render();});
    return;
   }
   const params=new URLSearchParams(location.search);
   const id=params.get('user_id');
   if(id&&/^\d+$/.test(id))userId=Number(id);
   if(location.search)history.replaceState(null,'',location.pathname+location.hash);
   readRoute();
  },
  async signout(target){root=target;role='etablissement';screen='signedout';notice='Fermeture de la session…';render();await run(finishLogout);}
 };
})();
