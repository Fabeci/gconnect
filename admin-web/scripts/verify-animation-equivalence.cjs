const {chromium}=require('playwright');
const fs=require('node:fs');const assert=require('node:assert/strict');
const dir='artifacts/animation-equivalence-20261022';fs.mkdirSync(dir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'no-preference',recordVideo:{dir:`${dir}/videos`,size:{width:1440,height:900}}});
 const student=await context.newPage(),admin=await context.newPage(),errors=[];let results={};
 for(const p of [student,admin])p.on('pageerror',e=>errors.push(e.message));
 await Promise.all([student.goto('http://localhost:8086/'),admin.goto('http://localhost:8086/etablissement.html')]);
 for(const [name,p,nav,home,hero,card,collapse,menu] of [
  ['students',student,'.sidebar [data-page="home"]','home','.hero h1','.op-card','#collapse','#mobile-menu'],
  ['establishment',admin,'.ea-nav [data-route="overview"]','overview','.ea-hero h1','.ea-card','#ea-collapse','#ea-open-menu']]){
  await p.waitForTimeout(650);
  console.log('Recording '+name);
  // Capture real animation frames following an actual navigation click.
  const samples=await p.evaluate(async({nav,hero})=>{
   document.querySelector(nav).click();const out=[];const start=performance.now();
   while(performance.now()-start<2200){await new Promise(requestAnimationFrame);const e=document.querySelector(hero),s=getComputedStyle(e);out.push({t:Math.round(performance.now()-start),opacity:+s.opacity,transform:s.transform});}return out;
  },{nav,hero});
  fs.writeFileSync(`${dir}/${name}-hero-samples.json`,JSON.stringify(samples));
  assert(samples.some(s=>s.opacity<.95)&&samples.some(s=>s.opacity>.99),`${name} hero progresses`);
  results[name]={hero:samples,css:await p.locator(hero).evaluate(e=>{const s=getComputedStyle(e);return {duration:s.animationDuration,delay:s.animationDelay,easing:s.animationTimingFunction}})};
  for(const time of [0,100,300]){
   if(time===0)await p.locator(nav).click();else await p.waitForTimeout(time===100?100:200);
   await p.screenshot({path:`${dir}/${name}-entrance-${time}.png`});
  }
  const button=p.locator(name==='students'?'.hero .btn.primary':'.ea-actions .ea-button.primary');
  await button.hover();await p.waitForTimeout(200);await p.screenshot({path:`${dir}/${name}-hover.png`});
  await p.mouse.down();await p.waitForTimeout(65);results[name].pressed=await button.evaluate(e=>getComputedStyle(e).transform);await p.screenshot({path:`${dir}/${name}-press.png`});await p.mouse.up();await p.waitForTimeout(450);
  // Network connect and subscription controls keep their ripple in the live DOM.
  if(name==='students'){await p.locator('.sidebar [data-page="network"]').click();await p.waitForTimeout(600);await p.evaluate(()=>document.addEventListener('click',()=>{window.lastRippleCount=document.querySelectorAll('.ripple').length},{once:true}));await p.locator('.invite').first().click();}
  else {await p.locator('.ea-nav [data-route="settings"]').click();await p.waitForTimeout(600);await p.evaluate(()=>document.addEventListener('click',()=>{window.lastRippleCount=document.querySelectorAll('.ripple').length},{once:true}));await p.locator('[data-appearance="dark"]').click();}
  await p.screenshot({path:`${dir}/${name}-ripple.png`});
  results[name].ripple=await p.evaluate(()=>window.lastRippleCount);assert(results[name].ripple>0,`${name} ripple`);
  if(name==='students'){await p.locator('.sidebar [data-page="settings"]').click();await p.waitForTimeout(350);await p.locator('button[data-theme="dark"]').click();}
  await p.waitForTimeout(600);await p.locator(nav).click();await p.waitForTimeout(700);
  await p.screenshot({path:`${dir}/${name}-dark.png`});
  await p.mouse.wheel(0,650);await p.waitForTimeout(140);await p.screenshot({path:`${dir}/${name}-scroll-140.png`});await p.waitForTimeout(500);await p.screenshot({path:`${dir}/${name}-scroll-640.png`});
  results[name].ambient=await p.locator('.ambient-glow').first().evaluate(async e=>{const a=getComputedStyle(e).transform;await new Promise(r=>setTimeout(r,180));return {before:a,after:getComputedStyle(e).transform}});
  assert.notEqual(results[name].ambient.before,results[name].ambient.after);assert.equal(await p.locator('.particle').count(),15);
  await p.evaluate(()=>scrollTo(0,0));
  // Locate actual student collapse control from markup.
  const collapseSelector=name==='students'?'#collapse':collapse;
  await p.locator(collapseSelector).click();await p.waitForTimeout(90);await p.screenshot({path:`${dir}/${name}-sidebar-90.png`});await p.waitForTimeout(400);await p.screenshot({path:`${dir}/${name}-sidebar-490.png`});
  await p.setViewportSize({width:390,height:844});await p.locator(menu).click();await p.waitForTimeout(75);await p.screenshot({path:`${dir}/${name}-mobile-75.png`});await p.waitForTimeout(400);await p.screenshot({path:`${dir}/${name}-mobile-475.png`});await p.keyboard.press('Escape');
 }
 await admin.setViewportSize({width:1440,height:900});
 for(const id of ['overview','promotions','members','events','team','subscription','settings']){
  await admin.locator(`.ea-nav [data-route="${id}"]`).click();await admin.waitForTimeout(500);
  assert.equal(await admin.locator('.ea-nav-item.active').getAttribute('data-route'),id);
  assert(await admin.locator('.ea-reveal').count()>0,`${id} reveal targets`);
 }
 // Reveal only when entering viewport, not on an offscreen render.
 await admin.locator('.ea-nav [data-route="overview"]').click();await admin.waitForTimeout(550);
 const footer=admin.locator('.ea-feature-row');assert(!(await footer.getAttribute('class')).includes('is-visible'));
 await footer.scrollIntoViewIfNeeded();await admin.waitForTimeout(450);assert((await footer.getAttribute('class')).includes('is-visible'));
 // Persistent shell and ambient nodes, no duplicated delegated ripple or particles.
 await admin.evaluate(()=>{window.savedSidebar=document.querySelector('.ea-sidebar');window.savedParticle=document.querySelector('.particle')});
 for(let i=0;i<12;i++){await admin.locator(`.ea-nav [data-route="${i%2?'settings':'overview'}"]`).click();}
 assert(await admin.evaluate(()=>savedSidebar===document.querySelector('.ea-sidebar')&&savedParticle===document.querySelector('.particle')));
 await admin.waitForTimeout(600);await admin.locator('[data-appearance="light"]').click();assert.equal(await admin.locator('[data-appearance="light"] .ripple').count(),1);
 await admin.locator('#ea-reduce-motion').check();assert.equal(await admin.locator('.particle').count(),0);assert.equal(await admin.locator('.ripple').count(),0);
 await admin.locator('.ea-nav [data-route="overview"]').click();
 assert.equal(await admin.locator('.ea-hero h1').evaluate(e=>getComputedStyle(e).animationName),'none');
 await admin.locator('.ea-nav [data-route="settings"]').click();await admin.locator('#ea-reduce-motion').uncheck();assert.equal(await admin.locator('.particle').count(),15);
 await admin.emulateMedia({reducedMotion:'reduce'});await admin.waitForFunction(()=>document.documentElement.dataset.reducedMotion==='true');assert.equal(await admin.locator('.particle').count(),0);assert.equal(await admin.locator('.ea-sidebar').evaluate(e=>getComputedStyle(e).transitionDuration),'0s');
 assert.deepEqual(errors,[]);results.checks={sevenModules:true,scrollReveal:true,persistentShell:true,singleRippleAfter12Navigations:true,reducedMotion:true,errors};
 const videos=[student.video(),admin.video()];await context.close();
 for(let i=0;i<videos.length;i++)await videos[i].saveAs(`${dir}/${i?'establishment':'students'}.webm`);
 fs.writeFileSync(`${dir}/measurements.json`,JSON.stringify(results,null,2));await browser.close();console.log('PASS animation frames, interaction recordings, 7 modules, lifecycle, reduced motion');
})().catch(e=>{console.error(e);process.exit(1)});
