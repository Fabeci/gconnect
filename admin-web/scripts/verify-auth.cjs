/* Run: npm run test:auth. Self-contained server, mocked API contracts, no real accounts. */
const { chromium }=require('playwright');
const { AxeBuilder }=require('@axe-core/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const dist=path.resolve(__dirname,'../dist');
const artifacts=path.resolve(__dirname,'../artifacts/auth');
fs.mkdirSync(artifacts,{recursive:true});
const server=http.createServer((req,res)=>{
 const file=path.join(dist,new URL(req.url,'http://localhost').pathname);
 if(!file.startsWith(dist+path.sep)){res.writeHead(403).end();return;}
 fs.readFile(file,(err,body)=>{if(err){res.writeHead(404).end();return;}res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.ttf':'font/ttf'})[path.extname(file)]||'application/octet-stream');res.end(body);});
});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base=`http://127.0.0.1:${server.address().port}`;
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext();
 const page=await context.newPage();let errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>window.GCONNECT_API_BASE_URL=location.origin+'/api/v1');
 let accountRole='student', failLogin=false, failLogout=false, unknownEmail=false, calls=[], mfaAction='verify', invites=[];
 await page.route('**/api/v1/**',async route=>{
  const req=route.request();const url=new URL(req.url()).pathname;let body=null;try{body=req.postDataJSON();}catch{body=req.postData();}calls.push({url,body,headers:req.headers()});
  let data=null,status=200,message='OK';
  if(url.endsWith('/web-login/')){data={mfa_required:true,challenge:'challenge-for-tests',mfa_action:mfaAction,email:'awa@example.test'};if(failLogin){status=401;message='Identifiants incorrects.';}}
  else if(url.endsWith('/web-mfa/setup/'))data={secret:'TEST-SHARED-TOTP-SECRET',otpauth_uri:'otpauth://totp/Test',expires_at:'2026-10-24T12:00:00Z'};
  else if(url.endsWith('/web-mfa/verify/'))data={token:'test-web-memory-token',token_type:'WebToken',role:accountRole,recovery_codes:mfaAction==='enroll'?['ABCD-1111','ABCD-2222']:[]};
  else if(url.endsWith('/invitations/preview/'))data={email:'invitee@example.test',institution:'Campus Test',expires_at:'2026-10-26T12:00:00Z'};
  else if(url.endsWith('/invitations/accept/'))data={email:'invitee@example.test'};
  else if(url.endsWith('/admin/invitations/')&&req.method()==='POST'){const invite={id:invites.length+1,email:body.email,institution_id:body.institution_id,institution_name:'Campus Test',expires_at:'2099-10-26T12:00:00Z',accepted:false,revoked:false};invites.unshift(invite);data={id:invite.id,expires_at:invite.expires_at};}
  else if(url.endsWith('/admin/invitations/')&&req.method()==='GET')data=invites;
  else if(url.match(/\/admin\/invitations\/\d+\/revoke\/$/)){const found=invites.find(inv=>url.endsWith('/'+inv.id+'/revoke/'));if(found)found.revoked=true;data={};}
  else if(url.endsWith('/login/')){data={token:'test-memory-token',role:accountRole};if(failLogin){status=401;message='Email ou mot de passe incorrect.';}}
  else if(url.endsWith('/me/'))data={id:42,role:accountRole,email:'awa@example.test',first_name:'Awa',institution_id:12};
  else if(url.endsWith('/stats/'))data={scope:'institution',institution_name:'Campus Test',users:{students:2,alumni:1},posts:{events:0},promotions_count:1};
  else if(url.endsWith('/check-code/'))data={session_token:'registration-session',institution_id:12,institution_name:'Campus Test'};
  else if(url.endsWith('/forgot-password/'))data=unknownEmail?null:{user_id:42};
  else if(url.endsWith('/register/student/')||url.endsWith('/register/alumni/')){data={user_id:42,email:'awa@example.test'};status=201;}
  else if((url.endsWith('/logout/')||url.endsWith('/web-logout/'))&&failLogout){status=503;message='Serveur indisponible.';}
  await route.fulfill({status,contentType:'application/json',body:JSON.stringify({success:status<400,data,message})});
 });
 const open=async hash=>{await page.goto(base+'/auth.html'+hash);await page.locator('#auth-title').waitFor();await page.locator('.auth-card').evaluate(el=>Promise.all(el.getAnimations().map(a=>a.finished)));};
 const click=async name=>page.getByRole('button',{name,exact:true}).click();
 const heading=async text=>{await page.getByRole('heading',{name:text,exact:true}).waitFor();};
 let audits=0;
 const auditCurrent=async label=>{
  if(await page.locator('.auth-card').count()) await page.locator('.auth-card').evaluate(el=>Promise.all(el.getAnimations().map(animation=>animation.finished)));
  else await page.locator('#gconnect-approved-superadmin-frame').waitFor();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${label}`);
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.deepEqual(axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),[],`accessibility ${label}`);
  audits++;
 };
 const auditCritical=async name=>{
  for(const width of [320,1440]){
   await page.setViewportSize({width,height:900});
   await auditCurrent(`${name} ${width}`);
   await page.screenshot({path:path.join(artifacts,`${name}-${width}.png`),fullPage:true});
  }
 };
 for(const width of [320,390,768,1440]){
  await page.setViewportSize({width,height:900});
  for(const hash of ['#welcome/community','#login/community','#login/etablissement','#login/superadmin','#invitation/etablissement','#forgot/community','#verify/community','#register/community','#signedout/community']){
   await open(hash);
   await auditCurrent(`${width} ${hash}`);
  }
  await open('#welcome/community');await page.screenshot({path:path.join(artifacts,`welcome-${width}.png`),fullPage:true});
  await open('#login/etablissement');await page.screenshot({path:path.join(artifacts,`login-${width}.png`),fullPage:true});
 }
 await page.setViewportSize({width:1280,height:900});
 await open('#login/community');
 await page.getByLabel('Adresse e-mail',{exact:true}).fill('awa@example.test');await page.getByLabel('Mot de passe',{exact:true}).fill('Incorrect123!');
 await click('Afficher mot de passe');assert.equal(await page.locator('#auth-password').getAttribute('type'),'text');
 failLogin=true;await click('Se connecter');await page.getByRole('alert').filter({hasText:'Email ou mot de passe incorrect.'}).waitFor();assert.equal(await page.locator('#auth-email').inputValue(),'awa@example.test');assert.equal(await page.evaluate(()=>document.activeElement.id),'auth-error');
 failLogin=false;accountRole='superAdmin';await click('Se connecter');await page.getByRole('alert').filter({hasText:'autre espace'}).waitFor();
 accountRole='student';await click('Se connecter');await heading('Bienvenue, Awa.');
 assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
 await click('Se déconnecter');await click('Rester connecté');await heading('Bienvenue, Awa.');await click('Se déconnecter');await click('Oui, me déconnecter');await heading('À très bientôt.');
 assert.equal(calls.find(c=>c.url.endsWith('/logout/')).headers.authorization,'Token test-memory-token');
 await open('#forgot/community');await page.locator('#auth-email').fill('awa@example.test');await click('Recevoir le code');await heading('Un nouveau départ.');
 await page.locator('#auth-otp').fill('123456');await page.locator('#auth-password').fill('NewPassword123!');await page.locator('#auth-confirm').fill('WrongPassword!');await click('Enregistrer le mot de passe');assert.equal(calls.filter(c=>c.url.endsWith('/reset-password/')).length,0);
 await page.locator('#auth-confirm').fill('NewPassword123!');await click('Enregistrer le mot de passe');await heading('Heureux de vous retrouver.');assert.deepEqual(calls.find(c=>c.url.endsWith('/reset-password/')).body,{user_id:42,otp:'123456',new_password:'NewPassword123!'});
 unknownEmail=true;await open('#forgot/community');await page.locator('#auth-email').fill('unknown@example.test');await click('Recevoir le code');await heading('Un nouveau départ.');assert.equal(await page.locator('#auth-otp').count(),0);unknownEmail=false;
 for(const kind of ['student','alumni']){
  await open('#register/community');await page.locator('#auth-kind').selectOption(kind);await page.locator('#auth-code').fill('123456');await click('Continuer');await heading('Faisons connaissance.');
  for(const [name,value] of Object.entries({first_name:'Awa',last_name:'Diop',username:'awa-diop',email:'awa@example.test',phone_number:'+221770000000'}))await page.locator('#auth-'+name).fill(value);
  await page.locator('#auth-gender').selectOption('F');
  if(kind==='student'){await page.locator('#auth-date_of_birth').fill('2000-01-01');await page.locator('#auth-student_id').fill('ST-42');}
  else await page.locator('#auth-proof_document').setInputFiles({name:'diplome.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4 test')});
  await click('Continuer');await heading('Protégez votre compte.');await page.locator('#auth-password').fill('Registration123!');await page.locator('#auth-confirm').fill('Registration123!');await click('Créer mon compte');
  if(kind==='student'){
   await heading('Vérifiez votre e-mail.');await click('Renvoyer le code');await page.getByRole('status').filter({hasText:'nouveau code'}).waitFor();assert(await page.locator('#auth-resend').isDisabled());
   await page.locator('#auth-otp').fill('123456');await click('Vérifier mon e-mail');await heading('Tout est prêt.');
  }else {await heading('Votre demande est envoyée.');assert(calls.find(c=>c.url.endsWith('/register/alumni/')).headers['content-type'].includes('multipart/form-data'));}
 }
 assert.equal(calls.find(c=>c.url.endsWith('/register/student/')).body.session_token,'registration-session');
 accountRole='etablissement';mfaAction='enroll';await open('#login/etablissement');
 await page.locator('#auth-email').fill('awa@example.test');await page.locator('#auth-password').fill('Password123!');
 await click('Se connecter');await heading('Sécurisez votre compte');
 assert.match(await page.locator('.auth-mfa-secret').textContent(),/TEST-SHARED-TOTP-SECRET/);
 assert.equal(await page.locator('.ea-sidebar').count(),0,'MFA enrollment must not open dashboard');
 await auditCritical('mfa-setup');
 await page.locator('#auth-otp').fill('123456');await click('Activer la double authentification');
 await heading('Conservez vos codes');
 assert(await page.getByText('ABCD-1111').isVisible());
 await auditCritical('mfa-recovery');
 await click('J’ai sauvegardé mes codes, continuer');await page.locator('.ea-sidebar').waitFor();
 assert.equal(calls.find(c=>c.url.endsWith('/stats/')).headers.authorization,'WebToken test-web-memory-token');
 failLogout=true;await page.locator('#ea-signout-nav').click();await heading('Vous êtes déconnecté');
 await page.getByRole('status').filter({hasText:'session distante'}).waitFor();
 assert.equal(await page.locator('.ea-sidebar').count(),0);failLogout=false;
 accountRole='superAdmin';mfaAction='verify';await page.goto(base+'/superadmin-login.html#login/superadmin');await page.locator('#auth-title').waitFor();
 await page.locator('#auth-email').fill('awa@example.test');await page.locator('#auth-password').fill('Password123!');
 await click('Se connecter');await heading('Vérifiez votre identité');
 assert.equal(await page.locator('#auth-invite-form').count(),0,'admin actions hidden until MFA');
 await auditCritical('mfa-verify');
 await page.locator('#auth-mfa_code').fill('ABCD-1111');await click('Vérifier et accéder');await page.locator('#gconnect-approved-superadmin-frame').waitFor();
 assert.equal(calls.filter(c=>c.url.endsWith('/web-mfa/verify/')).at(-1).body.code,'ABCD-1111');
 const superadminFrame=page.frameLocator('#gconnect-approved-superadmin-frame');
 await superadminFrame.locator('#commerce-nav [data-route="invitations"]').click();
 await superadminFrame.locator('#live-invite-form').waitFor();
 await auditCritical('superadmin-invitations');
 await superadminFrame.locator('#live-institution').fill('12');await superadminFrame.locator('#live-email').fill('invitee@example.test');
 await superadminFrame.locator('#live-invite-form button[type="submit"]').click();await superadminFrame.getByText('invitee@example.test').waitFor();
 assert.equal(calls.find(c=>c.url.endsWith('/admin/invitations/')&&c.body?.email).headers.authorization,'WebToken test-web-memory-token');
 page.once('dialog',dialog=>dialog.accept());await superadminFrame.locator('[data-live-revoke="1"]').click();await superadminFrame.getByText('Révoquée',{exact:true}).waitFor();
 await page.reload();await heading('Connectez-vous');
 await open('#invitation/etablissement');const before=calls.length;assert.equal(await page.locator('form').count(),0);assert.equal(calls.length,before);
 const testToken='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi0123456789';
 await page.goto(base+'/etablissement-activation.html#invitation='+testToken);
 await heading('Bienvenue dans votre espace');
 await page.locator('#auth-first_name').waitFor();
 assert.equal(new URL(page.url()).hash,'','invitation secret must be removed from the address bar');
 await auditCritical('invitation-activation');
 await page.locator('#auth-first_name').fill('Awa');await page.locator('#auth-last_name').fill('Diop');
 await page.locator('#auth-password').fill('Password123!');await page.locator('#auth-confirm').fill('Password123!');
 await click('Activer mon compte');await heading('Votre compte est activé');
 assert.equal(calls.find(c=>c.url.endsWith('/invitations/accept/')).body.invitation,testToken);
 await open('#login/community');await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),'auth-email');await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),'auth-password');
 await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await page.locator('.auth-card').evaluate(el=>getComputedStyle(el).animationName),'none');
 await page.setViewportSize({width:640,height:900});await page.evaluate(()=>document.documentElement.style.fontSize='200%');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(artifacts,'results.json'),JSON.stringify({axeAudits:audits,viewports:[320,390,768,1440],criticalViewports:[320,1440],flows:['roles','invalid login','login','logout','logout failure','recovery SMS','student signup','alumni multipart signup','email OTP','resend cooldown','institution MFA and recovery codes','superadmin MFA with recovery code + invite/revoke','reload','invitation activation','keyboard','reduced motion'],consoleErrors:errors},null,2));
 console.log(`PASS: ${audits} responsive accessibility audits and authentication flows.`);
 await browser.close();server.close();
})().catch(error=>{console.error(error);server.close();process.exit(1)});
