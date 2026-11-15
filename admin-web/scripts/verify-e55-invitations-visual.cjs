'use strict';
/* E55: visual regression guard for the seamless, animated G-Connect Invitations header.
 * Uses the actual shipped CSS/JS, with mocked data only for the visual fixture. */
const {chromium}=require('playwright');
const {readFileSync,mkdirSync}=require('node:fs');
const {join}=require('node:path');
const assert=require('node:assert/strict');
const baseCss=readFileSync(join(__dirname,'../dist/module-identities-e31.css'),'utf8');
const css=readFileSync(join(__dirname,'../dist/invitations-e54.css'),'utf8');
const js=readFileSync(join(__dirname,'../dist/invitations-e54.js'),'utf8');
const output=join(__dirname,'../artifacts/auth');
mkdirSync(output,{recursive:true});
const escape=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
(async()=>{
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:920},deviceScaleFactor:1});
    await page.setContent('<!doctype html><html lang="fr"><head><meta charset="utf-8"></head>'+
      '<body style="margin:0;background:#edf3ff;font-family:Manrope,system-ui,sans-serif">'+
      '<main id="view" style="width:min(1280px,calc(100% - 32px));margin:34px auto"></main></body></html>');
    await page.evaluate(()=>{document.documentElement.dataset.space='superadmin';document.documentElement.dataset.module='invitations';});
    await page.addStyleTag({content:baseCss});
    await page.addStyleTag({content:css});
    await page.addScriptTag({content:js});
    async function open(role) {
      await page.evaluate(async role=>{
        const root=document.getElementById('view');
        const api=role==='superAdmin'?{
          listInvitations:async()=>[],
          enterpriseOwnerInvitations:async()=>[]
        }:{
          enterpriseMembership:async()=>({membership:'owner',company:{name:'Horizon Technologie'}}),
          enterpriseRecruiterInvitations:async()=>[],
          enterpriseRecruiters:async()=>[]
        };
        let instance;
        const render=()=>{root.innerHTML=instance.page();};
        instance=window.GConnectInvitationsE54({
          role,api,
          safe:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),
          intro:()=>'', panel:(title,desc,body)=>'<section class="panel"><div class="panel-title"><div><h2>'+title+'</h2><p>'+desc+'</p></div></div>'+body+'</section>',
          render, isVisible:()=>true
        });
        await instance.load();
      },role);
    }
    await open('superAdmin');
    const hero=page.locator('.e54-stage-admin');
    await hero.waitFor();
    const computed=await hero.evaluate(el=>{
      const c=getComputedStyle(el);
      const title=el.querySelector('h1');
      const ticker=el.querySelector('.e54-stage-kicker');
      return {
        backgroundColor:c.backgroundColor,
        backgroundImage:c.backgroundImage,
        border:c.borderTopWidth,
        radius:c.borderTopLeftRadius,
        shadow:c.boxShadow,
        title:title.textContent.trim(),
        tickerAnimation:getComputedStyle(ticker).animationName,
        ringAnimation:getComputedStyle(el.querySelector('.e54-orbit-ring-inner')).animationName,
        artVisible:getComputedStyle(el.querySelector('.e54-stage-art')).display!=='none'
      };
    });
    assert.equal(computed.backgroundColor,'rgba(0, 0, 0, 0)');
    assert.equal(computed.backgroundImage,'none');
    assert.equal(computed.border,'0px');
    assert.equal(computed.radius,'0px');
    assert.equal(computed.shadow,'none');
    assert.equal(computed.title,'Invitations professionnelles');
    assert.match(computed.tickerAnimation,/e55-copy-appear/);
    assert.match(computed.ringAnimation,/e54-rotate/);
    assert.equal(computed.artVisible,true);
    const cards=page.locator('.e54-invite-grid .e54-workflow-card');
    assert.equal(await cards.count(),2);
    const firstButton=page.locator('.e54-invite-grid .e54-form-actions .e54-primary').first();
    const actionSizes=await firstButton.evaluate(el=>({
      button:el.getBoundingClientRect().width,
      card:el.closest('.e54-workflow-card').getBoundingClientRect().width,
      animation:getComputedStyle(el.closest('.e54-workflow-card')).animationName
    }));
    assert.ok(actionSizes.button < actionSizes.card*.62,'Invitations CTA must remain compact');
    assert.match(actionSizes.animation,/e56-card-appear/);
    const kpiAnimation=await page.locator('.e54-metrics>.e54-metric').first().evaluate(el=>getComputedStyle(el).animationName);
    assert.match(kpiAnimation,/e56-metric-appear/);
    const marker=await page.locator('.e54-history-panel .panel-title').first().evaluate(el=>({
      content:getComputedStyle(el,'::before').content,
      display:getComputedStyle(el,'::before').display
    }));
    assert.equal(marker.display,'none','No turquoise marker in history cards');
    assert.equal(marker.content,'none');
    await page.waitForTimeout(650);
    await page.screenshot({path:join(output,'e56-invitations-desktop.png'),fullPage:true,animations:'disabled'});
    await page.setViewportSize({width:390,height:844});
    await page.waitForTimeout(300);
    assert.equal(await hero.locator('h1').isVisible(),true);
    assert.equal(await hero.evaluate(el=>getComputedStyle(el).backgroundColor),'rgba(0, 0, 0, 0)');
    const mobileButton=await firstButton.evaluate(el=>({
      button:el.getBoundingClientRect().width,
      card:el.closest('.e54-workflow-card').getBoundingClientRect().width
    }));
    assert.ok(mobileButton.button<mobileButton.card*.94,'Avoid full-width mobile CTAs');
    await page.screenshot({path:join(output,'e56-invitations-mobile.png'),fullPage:true,animations:'disabled'});
    await page.setViewportSize({width:1440,height:920});
    await open('enterprise');
    const team=page.locator('.e54-stage-team');
    await team.waitFor();
    assert.equal(await team.evaluate(el=>getComputedStyle(el).backgroundColor),'rgba(0, 0, 0, 0)');
    assert.equal(await team.locator('h1').textContent(),'Équipe & accès');
    console.log('E56 visual smoke OK: borderless hero, distinct enterprise, premium cards, compact CTA, no history markers, animated KPIs, responsive.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
