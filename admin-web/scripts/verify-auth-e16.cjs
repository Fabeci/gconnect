/* E16 visual and negative-path QA. No accounts, successful login doubles, or DB writes.
   Protected screens are rendered in an isolated presentation harness only.
   Run npm run test:auth:e16 (requires Playwright Chromium). */
'use strict';
const { chromium } = require('playwright');
const { AxeBuilder } = require('@axe-core/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const vm = require('node:vm');
const dist = path.resolve(__dirname, '../dist');
const artifacts = path.resolve(__dirname, '../artifacts/auth-e16');
fs.mkdirSync(artifacts, { recursive:true });
const server = http.createServer((req,res) => {
  const file = path.resolve(dist, '.'+new URL(req.url,'http://localhost').pathname);
  if(!file.startsWith(dist+path.sep)){res.writeHead(403).end();return;}
  fs.readFile(file,(error,body) => {
    if(error){res.writeHead(404).end();return;}
    res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.ttf':'font/ttf'})[path.extname(file)]||'application/octet-stream');
    res.end(body);
  });
});

// Extract real templates in a VM with no API and no session. This hook exists
// only in this script, never in the served application or production bundle.
function presentation(state,role='etablissement') {
  const source = fs.readFileSync(path.join(dist,'auth.js'),'utf8');
  const context = {window:{addEventListener(){}}, result:''};
  const setup = `role=${JSON.stringify(role)};screen=${JSON.stringify(state)};
    mfaSecret='CLÉ-DE-CONFIGURATION-APERÇU-NON-UTILISABLE';
    recoveryCodes=Array(8).fill('APER-CUXX-CODE-NONX-VALD');
    invitePreview={institution:'Votre établissement',email:'Adresse destinataire de l’invitation'};
    userId=1;
    result=adminShell();`;
  vm.runInNewContext(source.replace(' window.GConnectAuth={',setup+'\n window.GConnectAuth={'),context);
  return context.result;
}

(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({headless:true});
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const errors=[], requests=[], audits=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('request',r=>requests.push(r.url()));
    await page.addInitScript(()=>window.GCONNECT_API_BASE_URL=location.origin+'/api/v1');
    let responseStatus=401, responseMessage='Identifiants incorrects.', blockedRequest;
    await page.route('**/api/v1/**',async route=>{
      if(blockedRequest)await blockedRequest;
      await route.fulfill({status:responseStatus,contentType:'application/json',body:JSON.stringify({success:false,message:responseMessage})});
    });
    const settle=async()=>{
      await page.evaluate(()=>document.fonts.ready);
      await page.locator('.auth-card').evaluate(el=>Promise.allSettled(el.getAnimations({subtree:true}).filter(a=>a.effect.getTiming().iterations!==Infinity).map(a=>a.finished)));
    };
    const open=async(file,hash='')=>{await page.goto(origin+'/'+file+hash);await page.locator('#auth-title').waitFor();await settle();};
    const audit=async label=>{
      await settle();
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),label+' horizontal overflow');
      const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
      assert.deepEqual(result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),[],label);
      audits.push(label);
    };
    const capture=async name=>page.screenshot({path:path.join(artifacts,name+'.png'),fullPage:true});
    const theme=async value=>{
      if(await page.locator('html').getAttribute('data-theme')!==value)await page.locator('#auth-theme-toggle').click();
      await page.waitForTimeout(260);
    };
    const sizes=[{width:1920,height:1080},{width:1366,height:768},{width:768,height:1024},{width:390,height:844},{width:360,height:800}];
    for(const file of ['etablissement.html','superadmin-login.html']){
      for(const size of sizes){
        await page.setViewportSize(size);
        await open(file);
        assert.equal(await page.locator('.auth-story,.auth-header,.auth-role-list').count(),0);
        for(const mode of ['light','dark']){
          await theme(mode);
          await audit(`${file} ${size.width} ${mode}`);
          await capture(`${file.replace('.html','')}-${size.width}-${mode}`);
        }
      }
    }
    assert(!requests.some(url=>url.includes('hero-gconnect')),'administrative login must not request a decorative photo');
    for(const file of ['etablissement.html','superadmin-login.html','etablissement-activation.html','etablissement-connexion.html']){
      await open(file);
      assert.equal(await page.locator('.auth-admin').count(),1);
    }
    for(const file of ['etablissement.html','superadmin-login.html']){
      for(const stage of ['forgot','reset','signedout',...(file==='etablissement.html'?['invitation']:[])]){
        for(const width of [390,1366]){
          await page.setViewportSize({width,height:900});
          await open(file,'#'+stage);
          for(const mode of ['light','dark']){
            await theme(mode);await audit(`${file} ${stage} ${width} ${mode}`);
            await capture(`${file.replace('.html','')}-${stage}-${width}-${mode}`);
          }
        }
      }
    }
    // Read-only visual fixtures: real templates, inert controls, no API success.
    for(const stage of ['activate','activated','mfa-setup','mfa-verify','mfa-recovery','reset','logout']){
      for(const width of [360,1366]){
        for(const mode of ['light','dark']){
          await page.setViewportSize({width,height:900});await open('etablissement.html');await theme(mode);
          await page.evaluate(markup=>{
            const themeIcon=document.querySelector('.auth-theme-icon').innerHTML;
            document.querySelector('#gc-establishment-app').innerHTML=markup;
            document.querySelector('.auth-theme-icon').innerHTML=themeIcon;
            const label=document.createElement('p');label.textContent='APERÇU VISUEL — aucune session authentifiée';
            label.style='font:12px Manrope;text-align:center;color:inherit;margin:0;padding:12px';
            document.querySelector('.auth-admin').prepend(label);
          },presentation(stage));
          await audit(`presentation-only ${stage} ${width} ${mode}`);
          await capture(`presentation-${stage}-${width}-${mode}`);
        }
      }
    }
    await page.setViewportSize({width:390,height:844});await open('etablissement.html');await theme('light');
    await page.locator('#auth-title').focus();
    const focusOrder=['auth-email','auth-password'];
    for(const id of focusOrder){await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),id);}
    await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.dataset.password),'auth-password');
    await page.keyboard.press('Enter');assert.equal(await page.locator('#auth-password').getAttribute('type'),'text');
    await page.keyboard.press('Enter');assert.equal(await page.locator('#auth-password').getAttribute('type'),'password');
    await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.dataset.go),'forgot');
    await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.type),'submit');
    const before=requests.length;
    await page.keyboard.press('Enter');assert.equal(requests.length,before,'empty form must not call API');
    assert.equal(await page.locator('#auth-email').getAttribute('aria-invalid'),'true');
    // Only a rejected request, intercepted locally. Never sent to Django.
    await page.locator('#auth-email').fill('negative-ui-check@example.invalid');
    await page.locator('#auth-password').fill('rejected-input');
    let release;blockedRequest=new Promise(resolve=>release=resolve);
    await page.locator('button[type=submit]').click();
    assert.equal(await page.locator('#auth-form').getAttribute('aria-busy'),'true');
    assert(await page.locator('button[type=submit]').isDisabled());
    await capture('loading-390-light');release();blockedRequest=null;
    await page.locator('#auth-error').filter({hasText:'Vérifiez vos identifiants'}).waitFor();
    assert.equal(await page.evaluate(()=>document.activeElement.id),'auth-error');
    await audit('invalid login 390 light');await capture('error-390-light');
    await theme('dark');await audit('invalid login 390 dark');await capture('error-390-dark');
    for(const [status,message,expected] of [[429,'Too many attempts','Patientez'],[503,'Twilio configuration backend secret','momentanément indisponible']]){
      responseStatus=status;responseMessage=status===429?'Trop de tentatives.':message;
      await page.locator('button[type=submit]').click();await page.locator('#auth-error').filter({hasText:expected}).waitFor();
      assert(!await page.locator('#auth-error').textContent().then(s=>/Twilio|secret|backend/.test(s)));
    }
    await page.locator('#auth-email').fill('corrected@example.invalid');assert.equal(await page.locator('#auth-error').textContent(),'');
    responseStatus=401;responseMessage='Votre session a expiré. Reconnectez-vous.';
    await page.locator('button[type=submit]').click();
    await page.locator('#auth-status').filter({hasText:'Votre session a expiré'}).waitFor();
    assert.equal(await page.locator('#auth-password').inputValue(),'');
    await audit('expired session');await capture('expired-session-390-dark');
    responseStatus=400;responseMessage='Invitation invalide ou expirée.';
    await open('etablissement-activation.html#invitation=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi0123456789');
    await page.locator('#auth-error').filter({hasText:'invitation est invalide ou a expiré'}).waitFor();
    assert.equal(await page.getByText('Vérification de votre invitation…',{exact:true}).count(),0);
    assert(!page.url().includes('invitation='),'invitation secret must be removed from the URL');
    assert.equal(await page.locator('#auth-password').count(),0);
    await audit('invalid or expired invitation');await capture('invalid-invitation-390-dark');
    await page.getByRole('button',{name:'Retour à la connexion',exact:true}).click();
    await page.locator('#auth-email').waitFor();
    // Check transition exists and completes; no motion is permanent while idle.
    await open('etablissement.html');
    assert.equal(await page.locator('.auth-card').evaluate(el=>getComputedStyle(el).animationName),'auth-admin-enter');
    await page.locator('[data-go=forgot]').click();
    await page.locator('[data-step=forgot]').waitFor();
    await settle();
    assert.equal(await page.evaluate(()=>document.getAnimations().filter(a=>a.playState==='running').length),0);
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await page.locator('.auth-card').evaluate(el=>getComputedStyle(el).animationName),'none');
    await page.setViewportSize({width:360,height:480});
    await audit('reduced viewport with keyboard height');
    await page.locator('#auth-email').focus();
    await page.keyboard.press('Tab');
    assert(await page.evaluate(()=>{const r=document.activeElement.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;}));
    await open('etablissement.html');await theme('dark');await page.reload();assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
    await page.setViewportSize({width:720,height:900});
    await page.evaluate(()=>document.body.style.zoom='2');await audit('200 percent zoom');
    assert.deepEqual(errors,[]);
    const report={audits:audits.length,checks:audits,viewports:sizes,consoleErrors:errors,backendSuccessTested:false,
      note:'No authenticated session, real account, SMS, invitation acceptance, database write or backend modification. Protected screenshots are inert presentation fixtures, visibly labelled.',
      interactions:['keyboard','password visibility','required fields','pending/disabled submit','401/429/503','error focus and correction','expired session','invalid invitation token removal','theme persistence','step animation','reduced motion','200% zoom','reduced keyboard viewport']};
    fs.writeFileSync(path.join(artifacts,'results.json'),JSON.stringify(report,null,2));
    console.log(`PASS: ${audits.length} accessibility/layout audits; negative paths and visual fixtures. No successful authentication simulated.`);
  } finally {await browser.close();server.close();}
})().catch(error=>{console.error(error);server.close();process.exitCode=1;});
