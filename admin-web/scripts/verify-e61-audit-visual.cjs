'use strict';
/* E61 isolated browser regression. Fixture follows the exact read-only backend
   response schema; it is never shown inside the actual G-Connect deployment. */
const {chromium}=require('playwright');
const {AxeBuilder}=require('@axe-core/playwright');
const {readFileSync,mkdirSync}=require('node:fs');
const {join}=require('node:path');
const assert=require('node:assert/strict');
const js=readFileSync(join(__dirname,'../dist/audit-e61.js'),'utf8');
const css=readFileSync(join(__dirname,'../dist/audit-e61.css'),'utf8');
const dir=join(__dirname,'../artifacts/auth');mkdirSync(dir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:940},deviceScaleFactor:1});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.setContent('<!doctype html><html lang="fr" data-space="superadmin" data-module="audit">'+
   '<head><meta charset="utf-8"><title>Journal d’audit E61 · G-Connect</title></head>'+
   '<body style="margin:0;background:#eef3ff;font-family:Manrope,system-ui,sans-serif">'+
   '<main id="view" style="width:min(1280px,calc(100% - 32px));margin:20px auto"></main></body></html>');
  await page.addStyleTag({content:css});await page.addScriptTag({content:js});
  await page.evaluate(async()=>{
   const safe=value=>String(value??'').replace(/[&<>"']/g,k=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
   }[k]));
   const today='2026-11-07';
   const records=[
    {id:32,action:'login_success',label:'Connexion réussie',category:'access',
     actor:'Console Superadmin',actor_role:'superAdmin',actor_id:1,
     created_at:'2026-11-07T18:20:00Z',details:{user_id:1}},
    {id:31,action:'invitation_sent',label:'Invitation envoyée',category:'invitations',
     actor:'Console Superadmin',actor_role:'superAdmin',actor_id:1,
     created_at:'2026-11-07T17:20:00Z',details:{enterprise_id:7}},
    {id:30,action:'report_reviewed',label:'Signalement examiné',category:'moderation',
     actor:'Console Superadmin',actor_role:'superAdmin',actor_id:1,
     created_at:'2026-11-06T14:10:00Z',details:{report_id:3,outcome:'dismissed'}},
    {id:29,action:'import_completed',label:'Import massif effectué',category:'operations',
     actor:'Console Superadmin',actor_role:'superAdmin',actor_id:1,
     created_at:'2026-11-05T10:00:00Z',details:{job_id:4,total:17,errors:1}},
    {id:28,action:'mfa_success',label:'Double authentification réussie',category:'access',
     actor:'Console Superadmin',actor_role:'superAdmin',actor_id:1,
     created_at:'2026-11-04T10:00:00Z',details:{}},
    {id:27,action:'login_failed',label:'Connexion échouée',category:'access',
     actor:'Console Superadmin',actor_role:'superAdmin',actor_id:1,
     created_at:'2026-11-02T10:00:00Z',details:{}},
   ];
   const opts=[
    {value:'login_success',label:'Connexion réussie'},
    {value:'login_failed',label:'Connexion échouée'},
    {value:'mfa_success',label:'Double authentification réussie'},
    {value:'invitation_sent',label:'Invitation envoyée'},
    {value:'report_reviewed',label:'Signalement examiné'},
    {value:'import_completed',label:'Import massif effectué'},
   ];
   const api={adminAuditDirectory:async({days,category,action,search,page,page_size})=>{
    const labels=Array.from({length:days===90?14:days===180?7:days},(_,i)=>{
     const d=new Date(today+'T12:00:00Z');
     d.setUTCDate(d.getUTCDate()-(days===90?7:days===180?30:1)*((days===90?14:days===180?7:days)-i-1));
     return d.toISOString().slice(0,10);
    });
    const events=labels.map((_,i)=>i%5===0?2:(i%3===0?1:0));
    const selected=records.filter(x=>(category==='all'||x.category===category)&&
     (action==='all'||x.action===action)&&
     (!search||[x.actor,x.action].join(' ').toLowerCase().includes(search.toLowerCase())));
    return {
     days,since:labels[0],until:today,
     summary:{events:6,invitations:1,moderation:1,access:3,operations:1,other:0,failed_access:1},
     action_choices:opts,
     trend:{granularity:days===90?'week':days===180?'month':'day',labels,events},
     page,pages:1,page_size,count:selected.length,results:selected,
    };
   }};
   const host=document.getElementById('view');let controller;
   const render=()=>host.innerHTML=controller.page();
   controller=window.GConnectAuditE61({api,safe,render,isVisible:()=>true});
   document.addEventListener('click',e=>{
    const hit=e.target.closest('[data-e61-days],[data-e61-category],[data-e61-item],[data-e61-action]');
    if(hit)controller.action(hit);
   });
   document.addEventListener('change',e=>{
    if(e.target.matches('[data-e61-filter]'))controller.filter(e.target);
   });
   document.addEventListener('input',e=>{
    if(e.target.matches('[data-e61-search]'))controller.search(e.target);
   });
   render();await controller.load();
  });
  const header=page.locator('.e61-hero');await header.waitFor();
  assert.deepEqual(await header.evaluate(el=>{
   const s=getComputedStyle(el);return [s.backgroundColor,s.boxShadow,s.borderTopWidth];
  }),['rgba(0, 0, 0, 0)','none','0px']);
  assert.equal(await page.locator('.e61-metric').count(),4);
  assert.equal(await page.locator('.e61-metric-number').first().textContent(),'6');
  assert.equal(await page.locator('.e61-event').count(),6);
  assert.match(await page.locator('.e61-metric').first().evaluate(el=>getComputedStyle(el).animationName),/e61-card/);
  await page.waitForTimeout(900);
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.deepEqual(axe.violations.map(v=>({
    id:v.id,targets:v.nodes.map(n=>({target:n.target,details:n.failureSummary})),
  })),[],'E61 accessibility');
  await page.screenshot({path:join(dir,'e61-audit-desktop.png'),fullPage:true,animations:'disabled'});
  await page.locator('[data-e61-item="30"]').click();
  const dialog=page.locator('.e61-dialog');await dialog.waitFor({state:'visible'});
  assert.match(await dialog.textContent(),/Signalement examiné/);
  assert.match(await dialog.textContent(),/Signalement/);
  assert.match(await dialog.textContent(),/dismissed/);
  assert.doesNotMatch(await dialog.textContent(),/ip_address|password|token_hash/);
  await dialog.locator('[data-e61-close]').click();
  await dialog.waitFor({state:'hidden'});
  await page.locator('[data-e61-category="invitations"]').click();
  await page.locator('.e61-event').first().waitFor();
  assert.equal(await page.locator('.e61-event').count(),1);
  await page.locator('[data-e61-days="7"]').click();
  await page.locator('[data-e61-days="7"][aria-pressed="true"]').waitFor();
  await page.setViewportSize({width:390,height:844});
  const overflow=await page.evaluate(()=>[document.documentElement.scrollWidth,innerWidth]);
  assert.ok(overflow[0]<=overflow[1]+2,'E61 mobile overflow: '+overflow);
  await page.screenshot({path:join(dir,'e61-audit-mobile.png'),fullPage:true,animations:'disabled'});
  assert.deepEqual(errors,[]);
  console.log('E61 visual smoke OK: timeline, real-shaped audit events, WCAG AA, transparent hero, detail modal and mobile');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
