'use strict';
/* E59 browser regression. Uses declared API-shape fixtures, never a live report. */
const {chromium}=require('playwright');
const {AxeBuilder}=require('@axe-core/playwright');
const {readFileSync,mkdirSync}=require('node:fs');
const {join}=require('node:path');
const assert=require('node:assert/strict');
const js=readFileSync(join(__dirname,'../dist/moderation-e59.js'),'utf8');
const css=readFileSync(join(__dirname,'../dist/moderation-e59.css'),'utf8');
const dir=join(__dirname,'../artifacts/auth');mkdirSync(dir,{recursive:true});

(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:930},deviceScaleFactor:1});
  const page=await context.newPage();
  const failures=[];page.on('pageerror',error=>failures.push(error.message));
  await page.setContent('<!doctype html><html lang="fr" data-space="superadmin" data-module="moderation">'+
    '<head><meta charset="utf-8"><title>Modération G-Connect · E59</title></head>'+
    '<body style="margin:0;background:#eef3ff;font-family:Manrope,system-ui,sans-serif">'+
    '<main id="view" style="width:min(1280px,calc(100% - 32px));margin:24px auto"></main></body></html>');
  await page.addStyleTag({content:css});
  await page.addScriptTag({content:js});
  await page.evaluate(async()=>{
    const safe=value=>String(value??'').replace(/[&<>"']/g,ch=>({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
    }[ch]));
    const rows=[
      {id:11,reason:'harassment',reason_display:'Harcèlement',
       description:'Insultes répétées observées par les membres de la communauté.',
       status:'pending',status_display:'En attente',target:'post',target_id:42,
       target_title:'Publication à examiner',target_excerpt:'Annonce de recrutement.',
       organisation:'Campus Horizon',reported_by:'Awa Sow',
       created_at:'2026-11-07T08:00:00Z',reviewed_at:null,
       is_hidden:false,critical:true,can_dismiss:true,can_hide:true},
      {id:12,reason:'spam',reason_display:'Spam',description:'Messages répétés sans consentement.',
       status:'pending',target:'comment',target_id:88,target_title:'Commentaire répétitif',
       target_excerpt:'Venez voir...',organisation:'Campus Horizon',reported_by:'Moussa Diallo',
       created_at:'2026-11-06T15:00:00Z',reviewed_at:null,is_hidden:false,
       critical:false,can_dismiss:true,can_hide:false},
      {id:13,reason:'fake_info',reason_display:'Fausse information',
       description:'Informations inexactes diffusées dans une annonce.',
       status:'dismissed',target:'user',target_id:4,target_title:'Profil de l’auteur',
       target_excerpt:'',organisation:'',reported_by:'Visiteur',
       created_at:'2026-11-04T15:00:00Z',reviewed_at:'2026-11-05T16:00:00Z',
       reviewed_by:'Superadmin',is_hidden:false,critical:false,can_dismiss:false,can_hide:false},
    ];
    const data={
      summary:{total:3,pending:2,resolved:1,reviewed_30d:1,critical_pending:1,dismissed:1,actioned:0},
      by_reason:{harassment:1,hate_speech:0,spam:1,fake_info:0,inappropriate:0,other:0},
    };
    const api={
      adminModerationDirectory:async ({status='pending',target='all',reason='all',search='',page=1})=>{
        const results=rows.filter(record=>(status==='all'||record.status===status)&&
           (target==='all'||record.target===target)&&
           (reason==='all'||record.reason===reason)&&
           (!search||[record.target_title,record.description,record.reported_by]
             .join(' ').toLowerCase().includes(search.toLowerCase())));
        return {...data,results,count:results.length,pages:1,page,page_size:10};
      },
      adminModerationDecision:async(id,body)=>{
        if(id!==11||body.confirmation!=='CONFIRMER'||body.decision!=='hide_post'||body.reason.length<10)
          throw Error('Décision non confirmée');
        return {...rows[0],status:'actioned',can_hide:false,can_dismiss:false};
      },
    };
    const host=document.getElementById('view');let controller;
    const render=()=>{host.innerHTML=controller.page()};
    controller=window.GConnectModerationE59({api,safe,render,isVisible:()=>true});
    document.addEventListener('click',event=>{
      const item=event.target.closest('[data-e59-action],[data-e59-detail]');
      if(item)controller.action(item);
      const button=event.target.closest('[data-e59-modal-action],[data-e59-modal-decision]');
      if(button)controller.modalAction(button);
    });
    document.addEventListener('change',event=>{
      if(event.target.matches('[data-e59-filter]'))controller.onFilter(event.target);
      if(event.target.matches('[data-e59-approval]'))controller.checkApproval();
    });
    document.addEventListener('input',event=>{
      if(event.target.matches('[data-e59-search]'))controller.onSearch(event.target);
      if(event.target.matches('[data-e59-reason]'))controller.checkApproval();
    });
    render();await controller.load();
  });
  const hero=page.locator('.e59-hero');await hero.waitFor();
  assert.deepEqual(await hero.evaluate(el=>{
    const s=getComputedStyle(el);return [s.backgroundColor,s.boxShadow,s.borderTopWidth];
  }),['rgba(0, 0, 0, 0)','none','0px']);
  assert.equal(await page.locator('.e59-metric').count(),4);
  assert.equal(await page.locator('.e59-metric-number').first().textContent(),'2');
  assert.equal(await page.locator('.e59-case').count(),2);
  assert.match(await page.locator('.e59-metric').first().evaluate(el=>getComputedStyle(el).animationName),/e59-card/);
  await page.waitForTimeout(850);
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.deepEqual(axe.violations.map(v=>({
    id:v.id,targets:v.nodes.map(n=>({target:n.target,details:n.failureSummary})),
  })),[],'E59 accessibility');
  await page.screenshot({path:join(dir,'e59-moderation-desktop.png'),fullPage:true,animations:'disabled'});
  await page.locator('[data-e59-detail="11"]').click();
  const modal=page.locator('.e59-dialog');await modal.waitFor({state:'visible'});
  assert.match(await modal.textContent(),/Publication à examiner/);
  assert.equal(await modal.locator('[data-e59-modal-decision="hide_post"]').count(),1);
  await modal.locator('[data-e59-modal-decision="hide_post"]').click();
  const execute=modal.locator('[data-e59-modal-action="execute"]');
  assert.equal(await execute.isDisabled(),true);
  await modal.locator('[data-e59-approval]').check();
  assert.equal(await execute.isDisabled(),true);
  await modal.locator('[data-e59-reason]').fill('Publication contraire aux règles de la communauté.');
  assert.equal(await execute.isDisabled(),false);
  await execute.click();
  await modal.waitFor({state:'hidden'});
  await page.locator('.e59-toast').waitFor();
  assert.match(await page.locator('.e59-toast').textContent(),/décision journalisée/);
  await page.setViewportSize({width:390,height:844});
  const overflow=await page.evaluate(()=>[document.documentElement.scrollWidth,innerWidth]);
  assert.ok(overflow[0]<=overflow[1]+2,'E59 mobile overflow: '+overflow);
  await page.screenshot({path:join(dir,'e59-moderation-mobile.png'),fullPage:true,animations:'disabled'});
  assert.deepEqual(failures,[]);
  console.log('E59 visual smoke OK: real-shaped cases, WCAG AA, transparent hero, motion, confirmation and mobile');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
