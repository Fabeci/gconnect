'use strict';
/* E62 browser regression with isolated API-shaped fixtures only.
   Never touches real credentials, sessions or database records. */
const {chromium}=require('playwright');
const {AxeBuilder}=require('@axe-core/playwright');
const {readFileSync,mkdirSync}=require('node:fs');
const {join}=require('node:path');
const assert=require('node:assert/strict');
const js=readFileSync(join(__dirname,'../dist/security-e62.js'),'utf8');
const css=readFileSync(join(__dirname,'../dist/security-e62.css'),'utf8');
const dir=join(__dirname,'../artifacts/auth');mkdirSync(dir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:940},deviceScaleFactor:1});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.setContent('<!doctype html><html lang="fr" data-space="superadmin" data-module="sessions"><head><meta charset="utf-8"><title>G-Connect E62 · Sessions & sécurité</title></head>'+
   '<body style="margin:0;background:#eef3ff;font-family:Manrope,system-ui,sans-serif">'+
   '<main id="view" style="width:min(1280px,calc(100% - 32px));margin:20px auto"></main></body></html>');
  await page.addStyleTag({content:css});await page.addScriptTag({content:js});
  await page.evaluate(async()=>{
   const safe=v=>String(v??'').replace(/[&<>"']/g,k=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
   }[k]));
   const own=[
    {id:100,current:true,device:{browser:'Firefox',os:'Linux',kind:'ordinateur'},
      created_at:'2026-11-06T12:00:00Z',last_seen_at:'2026-11-07T20:00:00Z',expires_at:'2026-11-08T23:00:00Z'},
    {id:101,current:false,device:{browser:'Chrome',os:'Windows',kind:'ordinateur'},
      created_at:'2026-11-05T12:00:00Z',last_seen_at:'2026-11-07T19:00:00Z',expires_at:'2026-11-08T23:00:00Z'},
   ];
   let revoked=false;
   window.__e62Actions=[];
   const api={
    adminSecurityOverview:async({days})=>{
      const count=days===7?7:days===30?30:14;
      const now=new Date('2026-11-07T12:00:00Z');
      const labels=Array.from({length:count},(_,i)=>{
       const day=new Date(now);day.setUTCDate(day.getUTCDate()-(count-1-i)*(days===90?7:1));
       return day.toISOString().slice(0,10);
      });
      return {
       days,since:labels[0],until:'2026-11-07',
       summary:{sessions_active:revoked?11:12,professionals_active:24,
        mfa_enabled:22,mfa_pending:2,failures:3,successes:14,revoked_7d:revoked?3:2,expiring_24h:4},
       my_mfa:{enabled:true,remaining_recovery_codes:6},
       my_sessions:revoked?[own[0]]:own,
       trend:{granularity:days===90?'week':'day',labels,
        successes:labels.map((_,i)=>i%4===0?4:1),failures:labels.map((_,i)=>i%5===0?2:0)},
       sources:{sessions:'EstablishmentWebSession',mfa:'PrivilegedMFADevice',attempts:'LoginAttempt'},
      };
    },
    adminSecurityRevokeOwnSession:async(id,payload)=>{
      window.__e62Actions.push({id,confirmation:payload.confirmation});
      if(id!==101||payload.confirmation!=='REVOQUER')throw Error('Confirmation rejetée.');
      revoked=true;
    },
   };
   const host=document.getElementById('view');let controller;
   const render=()=>host.innerHTML=controller.page();
   controller=window.GConnectSecurityE62({api,safe,render,isVisible:()=>true});
   document.addEventListener('click',event=>{
    const hit=event.target.closest('[data-e62-days],[data-e62-action],[data-e62-detail],[data-e62-revoke],[data-e62-submit]');
    if(hit)controller.action(hit);
   });
   document.addEventListener('input',event=>{
    if(event.target.matches('[data-e62-confirm-input]'))controller.onInput(event.target);
   });
   render();await controller.load();
  });
  const hero=page.locator('.e62-hero');await hero.waitFor();
  assert.deepEqual(await hero.evaluate(el=>{
   const styles=getComputedStyle(el);
   return [styles.backgroundColor,styles.boxShadow,styles.borderTopWidth];
  }),['rgba(0, 0, 0, 0)','none','0px']);
  assert.equal(await page.locator('.e62-metric').count(),4);
  assert.equal(await page.locator('.e62-metric strong').first().textContent(),'12');
  assert.equal(await page.locator('.e62-device').count(),2);
  assert.equal(await page.locator('[data-e62-revoke="100"]').count(),0);
  assert.equal(await page.locator('[data-e62-revoke="101"]').count(),1);
  assert.match(await page.locator('.e62-metric').first().evaluate(el=>getComputedStyle(el).animationName),/e62-card/);
  await page.waitForTimeout(920);
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.deepEqual(axe.violations.map(v=>({
   id:v.id,nodes:v.nodes.map(x=>({target:x.target,summary:x.failureSummary})),
  })),[],'E62 accessibility');
  await page.screenshot({path:join(dir,'e62-security-desktop.png'),fullPage:true,animations:'disabled'});
  await page.locator('[data-e62-detail="mfa_enabled"]').click();
  let dialog=page.locator('.e62-dialog');await dialog.waitFor({state:'visible'});
  assert.match(await dialog.textContent(),/PrivilegedMFADevice.confirmed_at/);
  await dialog.locator('[data-e62-dialog-close]').first().click();
  await dialog.waitFor({state:'hidden'});
  await page.locator('[data-e62-revoke="101"]').click();
  await dialog.waitFor({state:'visible'});
  const button=dialog.locator('[data-e62-submit="101"]');
  assert.equal(await button.isDisabled(),true);
  await dialog.locator('[data-e62-confirm-input]').fill('NON');
  assert.equal(await button.isDisabled(),true);
  await dialog.locator('[data-e62-confirm-input]').fill('REVOQUER');
  assert.equal(await button.isEnabled(),true);
  await button.click();
  await dialog.waitFor({state:'hidden'});
  await page.locator('.e62-device').first().waitFor();
  assert.equal(await page.locator('.e62-device').count(),1);
  const result=await page.evaluate(()=>window.__e62Actions);
  assert.deepEqual(result,[{id:101,confirmation:'REVOQUER'}]);
  assert.equal(await page.locator('.e62-device-current').count(),1);
  await page.locator('[data-e62-days="7"]').click();
  await page.locator('[data-e62-days="7"][aria-pressed="true"]').waitFor();
  await page.setViewportSize({width:390,height:844});
  await page.waitForTimeout(170);
  const overflow=await page.evaluate(()=>[document.documentElement.scrollWidth,innerWidth]);
  assert.ok(overflow[0]<=overflow[1]+2,'E62 mobile overflow '+overflow);
  await page.screenshot({path:join(dir,'e62-security-mobile.png'),fullPage:true,animations:'disabled'});
  assert.deepEqual(errors,[]);
  console.log('E62 visual smoke OK: real-shaped metrics, private devices, current session protected, confirmed revoke, WCAG AA, responsive');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
