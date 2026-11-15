'use strict';
/* E60 browser visual + accessibility. Strictly synthetic isolated API-shaped
   responses to exercise the real component, never a user's production DB. */
const {chromium}=require('playwright');
const {AxeBuilder}=require('@axe-core/playwright');
const {readFileSync,mkdirSync}=require('node:fs');
const {join}=require('node:path');
const assert=require('node:assert/strict');
const js=readFileSync(join(__dirname,'../dist/statistics-e60.js'),'utf8');
const css=readFileSync(join(__dirname,'../dist/statistics-e60.css'),'utf8');
const dir=join(__dirname,'../artifacts/auth');mkdirSync(dir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:940},deviceScaleFactor:1});
  const page=await context.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.setContent('<!doctype html><html lang="fr" data-space="superadmin" data-module="statistiques">'+
   '<head><meta charset="utf-8"><title>Statistiques G-Connect E60</title></head>'+
   '<body style="margin:0;background:#eef3ff;font-family:Manrope,system-ui,sans-serif">'+
   '<main id="view" style="width:min(1280px,calc(100% - 32px));margin:20px auto"></main></body></html>');
  await page.addStyleTag({content:css});
  await page.addScriptTag({content:js});
  await page.evaluate(async()=>{
   const safe=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
   const api={
    adminGlobalStatistics:async({days})=>{
      const grain=days===30?'day':days===90?'week':'month';
      const count=days===30?30:days===90?14:days===180?7:13;
      const end=new Date('2026-11-07T12:00:00Z');
      const labels=Array.from({length:count},(_,i)=>{
        const d=new Date(end);
        d.setUTCDate(d.getUTCDate()-(count-i-1)*(grain==='day'?1:grain==='week'?7:30));
        return d.toISOString().slice(0,10);
      });
      const accounts=labels.map((_,i)=>i%4===0?5:2+i%3);
      const posts=labels.map((_,i)=>i%3===0?4:1+i%2);
      const institutions=labels.map((_,i)=>i%4===0?1:0);
      const enterprise_accounts=labels.map((_,i)=>i%5===0?2:1);
      return {
       days,since:labels[0],until:'2026-11-07',granularity:grain,
       summary:{new_accounts:48,previous_accounts:37,growth_percent:29.7,
        accounts_total:148,accounts_active:135,accounts_banned:2,
        institutions_total:17,institutions_active:15,enterprises_total:13,
        enterprises_verified:11,posts_total:94,posts_published:79,posts_hidden:4,
        comments_total:44,reactions_total:187,applications_total:32,
        reports_pending:2,subscriptions_active:9},
       roles:{student:92,alumni:27,enterprise:13,etablissement:15,superAdmin:1},
       contents:{opportunity:28,event:17,project:14,discussion:24,share:11},
       trend:{labels,accounts,posts,institutions,enterprise_accounts},
       sources:{
        accounts:'User.date_joined',posts:'Post.created_at',
        institutions:'Institution.created_at',enterprise_accounts:'Enterprise.user.date_joined',
       },
      };
    },
   };
   const host=document.getElementById('view');let controller;
   const render=()=>{host.innerHTML=controller.page()};
   controller=window.GConnectStatisticsE60({api,safe,render,isVisible:()=>true});
   document.addEventListener('click',e=>{
      const item=e.target.closest('[data-e60-period],[data-e60-action],[data-e60-detail]');
      if(item)controller.action(item);
      if(e.target.closest('[data-e60-close]'))document.querySelector('.e60-dialog')?.close();
   });
   render();await controller.load();
  });
  const hero=page.locator('.e60-hero');await hero.waitFor();
  assert.deepEqual(await hero.evaluate(el=>{
    const s=getComputedStyle(el);return [s.backgroundColor,s.boxShadow,s.borderTopWidth];
  }),['rgba(0, 0, 0, 0)','none','0px']);
  assert.equal(await page.locator('.e60-metric').count(),4);
  assert.equal(await page.locator('.e60-metric-value').first().textContent(),'48');
  assert.equal(await page.locator('.e60-svg').count(),2);
  assert.match(await page.locator('.e60-line').first().evaluate(el=>getComputedStyle(el).animationName),/e60-line/);
  await page.waitForTimeout(820);
  const a11y=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.deepEqual(a11y.violations.map(v=>({
    id:v.id,targets:v.nodes.map(n=>({target:n.target,details:n.failureSummary})),
  })),[],'E60 accessibility');
  await page.screenshot({path:join(dir,'e60-statistics-desktop.png'),fullPage:true,animations:'disabled'});
  await page.locator('[data-e60-detail="enterprises_verified"]').click();
  const dialog=page.locator('.e60-dialog');await dialog.waitFor({state:'visible'});
  assert.match(await dialog.textContent(),/Enterprise.is_active/);
  await dialog.locator('[data-e60-close]').first().click();
  await dialog.waitFor({state:'hidden'});
  await page.locator('[data-e60-period="90"]').click();
  await page.locator('[data-e60-period="90"][aria-pressed="true"]').waitFor();
  assert.equal(await page.locator('.e60-metric-value').first().textContent(),'48');
  assert.match(await page.locator('.e60-growth').textContent(),/90 jours/);
  await page.setViewportSize({width:390,height:844});
  await page.waitForTimeout(220);
  const overflow=await page.evaluate(()=>[document.documentElement.scrollWidth,innerWidth]);
  assert.ok(overflow[0]<=overflow[1]+2,'E60 mobile overflow: '+overflow);
  await page.screenshot({path:join(dir,'e60-statistics-mobile.png'),fullPage:true,animations:'disabled'});
  assert.deepEqual(errors,[]);
  console.log('E60 visual smoke OK: transparent observatory, real-shaped charts, WCAG AA, responsive, drilldowns and period filters');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
