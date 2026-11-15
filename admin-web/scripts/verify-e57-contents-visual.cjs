'use strict';
/* E57 visual smoke: shipped CSS/JS, real browser metrics, no live data or accounts.
 * Fixture imitates only the documented API shape, not production availability. */
const {chromium}=require('playwright');
const {AxeBuilder}=require('@axe-core/playwright');
const {readFileSync,mkdirSync}=require('node:fs');
const {join}=require('node:path');
const assert=require('node:assert/strict');
const js=readFileSync(join(__dirname,'../dist/contents-e57.js'),'utf8');
const css=readFileSync(join(__dirname,'../dist/contents-e57.css'),'utf8');
const output=join(__dirname,'../artifacts/auth');
mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1});
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setContent('<!doctype html><html lang="fr" data-space="superadmin" data-module="contenus"><head><meta charset="utf-8"><title>E57 · Offres et contenus · Contrôle visuel</title></head>'+
    '<body style="margin:0;background:#eef3fd;font-family:Manrope,system-ui,sans-serif">'+
    '<main id="view" style="width:min(1280px,calc(100% - 32px));margin:30px auto"></main></body></html>');
  await page.addStyleTag({content:css});
  await page.addScriptTag({content:js});
  await page.evaluate(async()=>{
    const safe=x=>String(x??'').replace(/[&<>"']/g,c=>({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
    }[c]));
    const records=[
      {id:1,type:'opportunity',title:'Ingénieur plateforme',description:'Nous recherchons un profil backend orienté produits.',
        excerpt:'Recrutement d’un profil backend expérimenté.',state:'published',
        organisation:'Horizon Digital',author_name:'Awa Sow',created_at:'2026-11-07T10:00:00Z',audience:'public',views:14,
        comments:5,reactions:8,pending_reports:1},
      {id:2,type:'event',title:'Forum Alumni Dakar',description:'Rencontre professionnelle ouverte à la communauté.',
        excerpt:'Un forum pour connecter diplômés et entreprises.',state:'published',
        organisation:'Campus Dakar',author_name:'Équipe campus',created_at:'2026-11-06T09:00:00Z',audience:'public',views:47,
        comments:4,reactions:17,pending_reports:0},
      {id:3,type:'project',title:'Projet climatique',description:'Une collaboration entre établissements.',
        excerpt:'Les étudiants imaginent des solutions durables.',state:'draft',
        organisation:'École de technologie',author_name:'Équipe projet',created_at:'2026-11-06T08:00:00Z',audience:'public',views:0,
        comments:0,reactions:0,pending_reports:0},
    ];
    const summary={total:3,opportunities:1,events:1,projects:1,discussions:0,
      published:2,drafts:1,hidden:0,archived:0,reports_pending:1};
    const api={adminContentDirectory:async filters=>{
      const result=records.filter(x=>(filters.type==='all'||x.type===filters.type)&&
        (filters.state==='all'||x.state===filters.state)&&
        (!filters.search||[x.title,x.organisation].join(' ').toLowerCase().includes(filters.search.toLowerCase())));
      return {summary,results:result,page:1,pages:1,count:result.length,page_size:12};
    }};
    let instance;
    const root=document.getElementById('view');
    const render=()=>{root.innerHTML=instance.page();};
    instance=window.GConnectContentsE57({api,safe,render,isVisible:()=>true,go:()=>{}});
    document.addEventListener('click',ev=>{
      const btn=ev.target.closest('[data-e57-action],[data-e57-type],[data-e57-detail]');
      if(btn)instance.action(btn);
    });
    document.addEventListener('change',ev=>{
      if(ev.target.matches('[data-e57-filter]'))instance.onFilter(ev.target);
    });
    document.addEventListener('input',ev=>{
      if(ev.target.matches('[data-e57-search]'))instance.onSearch(ev.target);
    });
    render();
    await instance.load();
  });
  const hero=page.locator('.e57-hero');
  await hero.waitFor();
  const heroStyle=await hero.evaluate(el=>({
    background:getComputedStyle(el).backgroundColor,
    shadow:getComputedStyle(el).boxShadow,
    border:getComputedStyle(el).borderTopWidth,
  }));
  assert.equal(heroStyle.background,'rgba(0, 0, 0, 0)');
  assert.equal(heroStyle.shadow,'none');
  assert.equal(heroStyle.border,'0px');
  assert.equal(await page.locator('.e57-metric').count(),4);
  assert.equal(await page.locator('.e57-story').count(),3);
  assert.equal(await page.locator('.e57-metric-value').first().textContent(),'3');
  const anim=await page.locator('.e57-metric').first().evaluate(el=>getComputedStyle(el).animationName);
  assert.match(anim,/e57-card-up/);
  await page.waitForTimeout(900);
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.deepEqual(axe.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)})),[],'E57 accessibility');
  await page.screenshot({path:join(output,'e57-offres-desktop.png'),fullPage:true,animations:'disabled'});
  await page.locator('[data-e57-detail="1"]').click();
  const modal=page.locator('.e57-dialog');
  await modal.waitFor({state:'visible'});
  assert.match(await modal.textContent(),/Ingénieur plateforme/);
  await page.locator('.e57-dialog-top [data-e57-close]').click();
  await page.locator('.e57-filter-bar [data-e57-filter="kind"]').selectOption('event');
  await page.locator('[data-e57-detail="2"]').waitFor();
  assert.equal(await page.locator('.e57-story').count(),1);
  await page.locator('[data-e57-action="clear"]').count(); // clear appears only for empty results
  await page.setViewportSize({width:390,height:844});
  await page.locator('.e57-hero h1').waitFor();
  const overflow=await page.evaluate(()=>({
    doc:document.documentElement.scrollWidth,
    viewport:innerWidth
  }));
  assert.ok(overflow.doc<=overflow.viewport+2,'No E57 horizontal scrolling on mobile: '+JSON.stringify(overflow));
  await page.screenshot({path:join(output,'e57-offres-mobile.png'),fullPage:true,animations:'disabled'});
  assert.deepEqual(errors,[]);
  console.log('E57 visual smoke passed: editorial hero, real fixture, modal, filters, WCAG AA, responsive and motion.');
 }finally{await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1;});
