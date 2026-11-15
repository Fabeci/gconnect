'use strict';
/* E58 browser integration fixture. Only documented API replies are mocked.
 * No production data is transmitted and no real database is changed. */
const {chromium}=require('playwright');
const {AxeBuilder}=require('@axe-core/playwright');
const {readFileSync,mkdirSync}=require('node:fs');
const {join}=require('node:path');
const assert=require('node:assert/strict');
const js=readFileSync(join(__dirname,'../dist/imports-e58.js'),'utf8');
const css=readFileSync(join(__dirname,'../dist/imports-e58.css'),'utf8');
const dir=join(__dirname,'../artifacts/auth');mkdirSync(dir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:930},deviceScaleFactor:1});
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setContent('<!doctype html><html lang="fr" data-module="imports" data-space="superadmin">'+
    '<head><meta charset="utf-8"><title>G-Connect · Imports E58</title></head>'+
    '<body style="margin:0;background:#eff4ff;font-family:Manrope,system-ui,sans-serif">'+
    '<main id="view" style="width:min(1280px,calc(100% - 32px));margin:20px auto"></main></body></html>');
  await page.addStyleTag({content:css});
  await page.addScriptTag({content:js});
  await page.evaluate(async()=>{
    const safe=x=>String(x??'').replace(/[&<>"']/g,c=>({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
    }[c]));
    const api={
      adminImportHistory:async()=>({
        summary:{imports:7,integrated:172,anomalies:3,establishments:2},
        page:1,pages:1,count:2,
        institutions:[{id:3,name:'Université Horizon'}],
        results:[
          {id:1,file_name:'promotions-2026.csv',type:'promotions',institution:'Université Horizon',
            total:100,integrated:98,anomalies:2,created_at:'2026-11-07T09:00:00Z'},
          {id:2,file_name:'campus.csv',type:'establishments',institution:null,
            total:3,integrated:3,anomalies:0,created_at:'2026-11-06T09:00:00Z'},
        ],
      }),
      adminImportPreview:async data=>({
        name:data.get('file').name,type:data.get('import_type'),institution:null,
        columns:['name','acronym'],rows:2,errors:[],executable:true,
        notice:'Import possible après confirmation explicite.',
        preview_token:'fixture-only-pretend-signature',
        sample:[{row:2,values:{name:'Campus Horizon',acronym:'CH'}},{row:3,values:{name:'Institut Dakar',acronym:'ID'}}],
      }),
      adminImportExecute:async data=>{
        if(data.get('confirmation')!=='CONFIRMER'||data.get('preview_token')!=='fixture-only-pretend-signature')
          throw Error('Unconfirmed action');
        return {job_id:33,integrated:2,anomalies:0};
      },
    };
    const root=document.getElementById('view');let instance;
    const render=()=>{root.innerHTML=instance.page()};
    instance=window.GConnectImportsE58({api,safe,render,isVisible:()=>true});
    document.addEventListener('click',e=>{
      const node=e.target.closest('[data-e58-action],[data-e58-type]');
      if(node)instance.action(node);
    });
    document.addEventListener('change',e=>{
      if(e.target.matches('[data-e58-file],[data-e58-school],[data-e58-filter],[data-e58-confirm]'))
        instance.onChange(e.target);
    });
    render();await instance.load();
  });
  const hero=page.locator('.e58-hero');await hero.waitFor();
  assert.deepEqual(await hero.evaluate(el=>{
    const style=getComputedStyle(el);
    return [style.backgroundColor,style.boxShadow,style.borderTopWidth];
  }),['rgba(0, 0, 0, 0)','none','0px']);
  assert.equal(await page.locator('.e58-metric').count(),4);
  assert.equal(await page.locator('.e58-metric strong').first().textContent(),'7');
  assert.equal(await page.locator('.e58-table-row').count(),2);
  assert.match(await page.locator('.e58-metric').first().evaluate(el=>getComputedStyle(el).animationName),/e58-card-in/);
  await page.waitForTimeout(720);
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.deepEqual(axe.violations.map(v=>({
    id:v.id,details:v.nodes.map(n=>({target:n.target,summary:n.failureSummary})),
  })),[],'E58 accessibility');
  await page.screenshot({path:join(dir,'e58-imports-desktop.png'),fullPage:true,animations:'disabled'});
  await page.locator('[data-e58-file]').setInputFiles({
    name:'establishments.csv',mimeType:'text/csv',buffer:Buffer.from('name,acronym\nCampus Horizon,CH\nInstitut Dakar,ID\n'),
  });
  await page.locator('[data-e58-action="preview"]').click();
  const dialog=page.locator('.e58-dialog');await dialog.waitFor({state:'visible'});
  assert.match(await dialog.textContent(),/Vérification du fichier/);
  assert.equal(await dialog.locator('[data-e58-action="execute"]').isDisabled(),true);
  await dialog.locator('[data-e58-confirm]').check();
  assert.equal(await dialog.locator('[data-e58-action="execute"]').isDisabled(),false);
  await dialog.locator('[data-e58-action="execute"]').click();
  await dialog.waitFor({state:'hidden'});
  await page.locator('.e58-notice').waitFor();
  assert.match(await page.locator('.e58-notice').textContent(),/2 ligne\(s\) intégrée\(s\)/);
  await page.setViewportSize({width:390,height:845});
  await page.waitForTimeout(250);
  const overflow=await page.evaluate(()=>[document.documentElement.scrollWidth,innerWidth]);
  assert.ok(overflow[0]<=overflow[1]+2,'No horizontal mobile overflow: '+overflow);
  assert.equal(await page.locator('.e58-type').count(),4);
  await page.screenshot({path:join(dir,'e58-imports-mobile.png'),fullPage:true,animations:'disabled'});
  assert.deepEqual(errors,[]);
  console.log('E58 visual smoke OK: editorial hero, live-shaped job history, WCAG AA, responsive, signed confirmation fixture.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
