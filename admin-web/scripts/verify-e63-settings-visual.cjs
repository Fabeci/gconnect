'use strict';
/* E63 browser regression. Uses mocked profile and security reads ONLY in CI,
   never writes to user's database or tests real password operations. */
const {chromium}=require('playwright');
const {AxeBuilder}=require('@axe-core/playwright');
const {readFileSync,mkdirSync}=require('node:fs');
const {join}=require('node:path');
const assert=require('node:assert/strict');
const js=readFileSync(join(__dirname,'../dist/settings-e63.js'),'utf8');
const css=readFileSync(join(__dirname,'../dist/settings-e63.css'),'utf8');
const dir=join(__dirname,'../artifacts/auth');mkdirSync(dir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:940},deviceScaleFactor:1});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.setContent('<!doctype html><html lang="fr" data-space="superadmin" data-module="parametres">'+
   '<head><meta charset="utf-8"><title>G-Connect E63 · Profil & paramètres</title></head>'+
   '<body style="margin:0;background:#eef3ff;font-family:Manrope,system-ui,sans-serif">'+
   '<main id="view" style="width:min(1280px,calc(100% - 32px));margin:20px auto"></main></body></html>');
  await page.addStyleTag({content:css});await page.addScriptTag({content:js});
  await page.evaluate(async()=>{
   const safe=v=>String(v??'').replace(/[&<>"']/g,k=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
   }[k]));
   const profile={
    full_name:'Awa Diallo',first_name:'Awa',last_name:'Diallo',
    email:'awa@example.test',phone_number:'+221 700 000 000',role:'superAdmin',photo_url:null,
   };
   let pref='system',ctrl;
   window.__e63Actions=[];
   const api={adminSecurityOverview:async()=>({
    my_mfa:{enabled:true,remaining_recovery_codes:6},
    my_sessions:[{id:22,current:true},{id:23,current:false}],
    summary:{sessions_active:6,mfa_enabled:10,mfa_pending:2,failures:2,successes:7,expiring_24h:1},
   })};
   const host=document.getElementById('view');
   const render=()=>host.innerHTML=ctrl.page();
   ctrl=window.GConnectSettingsE63({
    api,safe,profile:()=>profile,validPhoto:()=>null,
    motion:()=>pref,setMotion:value=>{pref=value;window.__e63Actions.push('motion:'+value)},
    openProfile:tab=>window.__e63Actions.push('profile:'+tab),
    openAbout:()=>window.__e63Actions.push('about'),
    go:route=>window.__e63Actions.push('go:'+route),
    render,isVisible:()=>true,
   });
   document.addEventListener('click',event=>{
    const button=event.target.closest('[data-e63-action],[data-e63-motion]');
    if(button)ctrl.action(button);
   });
   render();await ctrl.load();
  });
  const hero=page.locator('.e63-hero');await hero.waitFor();
  assert.deepEqual(await hero.evaluate(el=>{
   const s=getComputedStyle(el);return[s.backgroundColor,s.boxShadow,s.borderTopWidth];
  }),['rgba(0, 0, 0, 0)','none','0px']);
  assert.equal(await page.locator('.e63-panel').count(),4);
  assert.match(await page.locator('.e63-profile-panel').textContent(),/Awa Diallo/);
  assert.match(await page.locator('.e63-safety').textContent(),/Codes de secours disponibles/);
  assert.match(await page.locator('.e63-panel').first().evaluate(el=>getComputedStyle(el).animationName),/e63-enter/);
  await page.waitForTimeout(820);
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.deepEqual(axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),[],'E63 WCAG AA');
  await page.screenshot({path:join(dir,'e63-settings-desktop.png'),fullPage:true,animations:'disabled'});
  await page.locator('[data-e63-motion="off"]').click();
  assert.equal(await page.locator('[data-e63-motion="off"]').getAttribute('aria-pressed'),'true');
  await page.locator('[data-e63-action="profile"]').click();
  await page.locator('[data-e63-action="password"]').click();
  await page.locator('.e63-safety-actions [data-e63-action="sessions"]').click();
  const actions=await page.evaluate(()=>window.__e63Actions);
  assert.deepEqual(actions,['motion:off','profile:profile','profile:security','go:sessions']);
  await page.setViewportSize({width:390,height:844});
  await page.waitForTimeout(120);
  const overflow=await page.evaluate(()=>[document.documentElement.scrollWidth,innerWidth]);
  assert.ok(overflow[0]<=overflow[1]+2,'E63 mobile horizontal overflow '+overflow);
  await page.screenshot({path:join(dir,'e63-settings-mobile.png'),fullPage:true,animations:'disabled'});
  assert.deepEqual(errors,[]);
  console.log('E63 visual smoke OK: transparent profile hero, real session status, existing profile & password controls, reduced-motion, WCAG AA, mobile');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
