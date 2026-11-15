'use strict';
/* E54.4 browser integration: real Node portal, same-origin proxy and Django HTTP contract.
 * Uses an in-memory fake upstream; never sends mail or uses production accounts. */
const {chromium}=require('playwright');
const {AxeBuilder}=require('@axe-core/playwright');
const assert=require('node:assert/strict');
const http=require('node:http');
const portal=require('./serve-professional-portals.cjs');

const token='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
const seen=[];
const backend=http.createServer(async(req,res)=>{
  let raw='';
  for await(const chunk of req)raw+=chunk;
  let data;try{data=JSON.parse(raw||'{}')}catch{data={}};
  seen.push({path:req.url,method:req.method,data,authorized:!!req.headers.authorization,cookie:!!req.headers.cookie});
  let status=200,body=null;
  if(req.url==='/api/v1/users/enterprise/invitations/preview/'&&req.method==='POST'){
    if(data.invitation===token)body={kind:'owner',company_name:'Horizon E54',email:'directeur@example.test',expires_at:'2099-01-01T00:00:00Z'};
    else if(data.invitation===token.slice(1))body={kind:'recruiter',company_name:'Horizon E54',email:'recruteur@example.test',expires_at:'2099-01-01T00:00:00Z'};
    else{status=400;body=null;}
  }else if(req.url==='/api/v1/users/enterprise/invitations/accept/'&&req.method==='POST'){
    if(data.invitation===token&&data.password==='Good-Password-E54!'&&data.first_name==='Awa'&&data.last_name==='Traore'){
      body={email:'directeur@example.test'};
    }else{status=400;body=null;}
  }else{status=404;}
  res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});
  res.end(JSON.stringify({success:status<400,data:body,message:status<400?'OK':'Invitation invalide ou expirée.'}));
});
const listen=server=>new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const close=server=>new Promise(resolve=>server.close(resolve));
(async()=>{
  await listen(backend);
  process.env.GCONNECT_BACKEND_PORT=String(backend.address().port);
  await listen(portal);
  const base='http://127.0.0.1:'+portal.address().port;
  const browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:390,height:844}});
  const page=await context.newPage();
  const errors=[];page.on('pageerror',err=>errors.push(err.message));
  try{
    const access=await page.goto(base+'/entreprise-activation.html#invitation='+token);
    assert.equal(access.status(),200);
    assert.equal(access.headers()['cache-control'],'no-store');
    assert.equal(access.headers()['referrer-policy'],'no-referrer');
    await page.getByRole('heading',{name:'Activez votre compte.'}).waitFor();
    await page.getByText('Horizon E54',{exact:true}).waitFor();
    await page.getByText('directeur@example.test',{exact:true}).waitFor();
    assert.equal(new URL(page.url()).hash,'','secret must be removed before API response');
    assert.equal((await page.locator('#ea-form').isVisible()),true);
    assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
    await page.locator('[name="first_name"]').fill('Awa');
    await page.locator('[name="last_name"]').fill('Traore');
    await page.locator('[name="password"]').fill('Good-Password-E54!');
    await page.locator('[name="confirm_password"]').fill('Different-Password-E54!');
    await page.getByRole('button',{name:/Activer mon compte/}).click();
    await page.getByText('ne correspondent pas').waitFor();
    assert.equal(seen.filter(x=>x.path.endsWith('/accept/')).length,0,'mismatching passwords never reach Django');
    await page.locator('[name="confirm_password"]').fill('Good-Password-E54!');
    await page.getByRole('button',{name:/Activer mon compte/}).click();
    await page.getByText('Compte activé.').waitFor();
    const accepted=seen.filter(x=>x.path.endsWith('/accept/'));
    assert.equal(accepted.length,1);
    assert.equal(accepted[0].data.invitation,token);
    assert.equal(accepted[0].authorized,false);
    assert.equal(accepted[0].cookie,false);
    assert.equal(await page.locator('#ea-form').isVisible(),false);
    const a=page.getByRole('link',{name:/Se connecter à mon entreprise/});
    assert.equal(await a.getAttribute('href'),'/entreprise#login/entreprise');
    await a.click();
    await page.waitForURL(u=>u.pathname==='/entreprise');
    assert.match(await page.title(),/G-Connect/);
    assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
    await page.goto(base+'/entreprise-activation.html#invitation='+token.slice(1));
    await page.getByText('recruteur@example.test',{exact:true}).waitFor();
    await page.getByText('Invitation Recruteur',{exact:true}).waitFor();
    await page.goto(base+'/entreprise-activation.html#invitation=invalid');
    await page.getByText("Le lien d'invitation est invalide.").waitFor();
    assert.equal(await page.locator('#ea-form').isVisible(),false);
    await page.goto(base+'/entreprise-activation.html#invitation='+token.slice(2));
    await page.getByText('Invitation invalide ou expirée.').waitFor();
    assert.equal(await page.locator('#ea-form').isVisible(),false);
    assert.equal(new URL(page.url()).hash,'');
    assert.equal(errors.length,0,'no browser runtime errors: '+errors.join(', '));
    await page.goto(base+'/entreprise-activation.html#invitation='+token);
    await page.getByText('Horizon E54',{exact:true}).waitFor();
    await page.locator('.ea-card').evaluate(el=>Promise.all(el.getAnimations().map(a=>a.finished)));
    const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    assert.deepEqual(axe.violations.map(x=>({id:x.id,targets:x.nodes.map(n=>({target:n.target,details:n.failureSummary}))})),[],'activation accessibility errors');
    console.log('PASS E54.4 activation: public entrypoint, proxy, owner/recruiter, single use form, redirect, a11y.');
  }finally{
    await browser.close();
    await close(portal);
    await close(backend);
    delete process.env.GCONNECT_BACKEND_PORT;
  }
})().catch(err=>{console.error(err);process.exitCode=1;});
