const {chromium}=require('playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');
const dir=process.env.EA_ARTIFACT_DIR||'artifacts/etablissement-v2';fs.mkdirSync(dir,{recursive:true});
(async()=>{
 const b=await chromium.launch({headless:true}); const p=await b.newPage();const errors=[],results=[];
 p.on('pageerror',e=>errors.push(e.message));
 const nav=async(id,width)=>{if(width<=900){await p.locator('#ea-open-menu').click();await p.waitForTimeout(240)}await p.locator(`.ea-nav [data-route="${id}"]`).click();};
 const shot=async(name)=>{await p.screenshot({path:`${dir}/${name}.png`,fullPage:true,animations:'disabled'})};
 for(const width of [320,390,768,1024,1440,1920]){
  await p.setViewportSize({width,height:1000});await p.goto('http://localhost:8086/etablissement.html');await p.evaluate(()=>document.fonts.ready);
  for(const theme of ['light','dark']){
   await p.locator('#ea-theme').selectOption(theme);
   for(const id of ['overview','promotions','members','events','team','subscription','settings']){
    await nav(id,width);
    const m=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,header:document.querySelector('.ea-top').getBoundingClientRect().height,sidebar:document.querySelector('.ea-sidebar').getBoundingClientRect().width,font:getComputedStyle(document.querySelector('h1')).fontFamily,theme:document.documentElement.dataset.theme,sidebarLayout:getComputedStyle(document.querySelector('.ea-sidebar')).display,navLayout:getComputedStyle(document.querySelector('.ea-nav')).display,topLayout:getComputedStyle(document.querySelector('.ea-top')).display,heroLayout:document.querySelector('.ea-hero')?getComputedStyle(document.querySelector('.ea-hero')).display:null}));
    assert(!m.overflow,`${width}/${theme}/${id} overflow`);assert(m.font.includes('Manrope'));assert.equal(m.theme,theme);assert.equal(m.header,width>900?68:64);assert.equal(m.sidebarLayout,'flex','sidebar layout');assert.equal(m.navLayout,'grid','navigation layout');assert.equal(m.topLayout,'flex','topbar layout');if(id==='overview')assert.equal(m.heroLayout,'grid','hero layout');if(width>900)assert.equal(m.sidebar,235);
    results.push({width,theme,id,...m});
    if([390,1440].includes(width)||id==='overview')await shot(`${width}-${theme}-${id}`);
   }
  }
  // Actual form validation and local draft creation/removal on every viewport.
  for(const [id,values] of Object.entries({promotions:{track:'Informatique',cohort:'QA <campus>',year:'2026-2027'},events:{title:'Rencontre QA',date:'2026-11-15',place:'Amphi A'},team:{name:'Responsable QA',email:'qa@example.test'}})){
   await nav(id,width);const form=p.locator(`[data-draft-form="${id}"]`);
   await form.locator('[type="submit"]').click();assert.equal(await p.locator('.ea-draft').count(),0,'required fields');
   for(const [name,value] of Object.entries(values))await form.locator(`[name="${name}"]`).fill(value);
   if(id==='team')await form.locator('select').selectOption('Chargé de communication');
   await form.locator('[type="submit"]').click();assert.equal(await p.locator('.ea-draft').count(),1);
   assert((await p.locator('.ea-draft').innerText()).includes(Object.values(values)[id==='promotions'?1:0]));
   await nav('overview',width);await nav(id,width);assert.equal(await p.locator('.ea-draft').count(),1,'draft survives navigation');
   await p.locator('[data-remove]').click();assert.equal(await p.locator('.ea-draft').count(),0);
  }
  await nav('members',width);await p.locator('#ea-members-query').fill('Test');
  for(const v of ['students','alumni','all']){await p.locator('#ea-members-filter').selectOption(v);assert.match(await p.locator('.ea-empty-state p').innerText(),/Filtre/)}
  await nav('subscription',width);for(const v of ['1','6','12']){await p.locator(`[data-plan="${v}"]`).click();assert.equal(await p.locator(`[data-plan="${v}"]`).getAttribute('aria-pressed'),'true')}
  await nav('settings',width);const form=p.locator('#ea-profile-form');
  await form.locator('[type="submit"]').click();assert.equal(await p.locator('.ea-profile-preview').count(),0);
  for(const [name,value] of Object.entries({name:'Campus QA',city:'Dakar',contact:'campus@example.test'}))await form.locator(`[name="${name}"]`).fill(value);
  await p.locator('#ea-theme').selectOption('light');assert.equal(await form.locator('[name="name"]').inputValue(),'Campus QA');
  if(width>900){await p.locator('#ea-collapse').click();await p.waitForTimeout(260);assert.equal(await p.locator('.ea-sidebar').evaluate(e=>e.getBoundingClientRect().width),76);assert.equal(await form.locator('[name="name"]').inputValue(),'Campus QA');if(width===1440)await shot('desktop-collapsed');await p.locator('#ea-search-compact').click();assert(await p.locator('#ea-search-input').evaluate(e=>e===document.activeElement));}
  else {await p.locator('#ea-open-menu').click();await p.waitForTimeout(250);if(width===390)await shot('mobile-menu');await p.locator('#ea-collapse').click();assert.equal(await p.locator('#ea-open-menu').getAttribute('aria-expanded'),'false');await p.locator('#ea-open-menu').click();await p.keyboard.press('Escape');assert.equal(await p.locator('#ea-open-menu').getAttribute('aria-expanded'),'false');await p.locator('#ea-open-menu').click();await p.locator('#ea-backdrop').click({position:{x:width-5,y:500}});assert.equal(await form.locator('[name="name"]').inputValue(),'Campus QA');}
  await form.locator('[type="submit"]').click();assert.match(await p.locator('.ea-profile-preview').innerText(),/Campus QA/);
  if(width<=900)await p.locator('#ea-open-menu').click();
  await p.locator('#ea-search-input').fill('factures');assert.equal(await p.locator('.ea-nav-item:visible').count(),1);await p.locator('#ea-search-input').fill('');
  if(width<=900)await p.keyboard.press('Escape');
  console.log(`PASS ${width}px: 14 views plus forms, drafts, plans, filters, navigation`);
 }
 // Real overview shortcut buttons preserve their destinations.
 await p.setViewportSize({width:1440,height:1000});
 for(const selector of ['.ea-actions [data-route="promotions"]','.ea-actions [data-route="events"]','.ea-step[data-route="promotions"]','.ea-step[data-route="team"]','.ea-step[data-route="events"]','.ea-text-button','.ea-feature-row .ea-button']){await nav('overview',1440);const button=p.locator(selector);const id=await button.getAttribute('data-route');await button.click();assert.equal(await p.locator('.ea-nav-item.active').getAttribute('data-route'),id)}
 await p.emulateMedia({colorScheme:'dark'});await p.locator('#ea-theme').selectOption('light');assert.equal(await p.locator('html').getAttribute('data-theme'),'light');await p.locator('#ea-theme').selectOption('system');assert.equal(await p.locator('html').getAttribute('data-theme'),'dark');await p.emulateMedia({colorScheme:'light'});await p.waitForFunction(()=>document.documentElement.dataset.theme==='light');assert.equal(await p.locator('html').getAttribute('data-theme'),'light');
 await p.emulateMedia({reducedMotion:'reduce'});assert.equal(await p.locator('.ea-sidebar').evaluate(e=>getComputedStyle(e).transitionDuration),'0s');
 // Comparisons from the unmodified student app, using its real theme controls.
 for(const width of [390,1440]){
  await p.setViewportSize({width,height:1000});await p.goto('http://localhost:8086');await p.waitForTimeout(150);
  for(const theme of ['light','dark']){
   if(width<=900)await p.locator('#mobile-menu').click();await p.locator('.sidebar [data-page="settings"]').click();await p.waitForTimeout(150);await p.locator(`button[data-theme="${theme}"]`).click();await p.waitForTimeout(150);
   if(width<=900)await p.locator('#mobile-menu').click();await p.locator('.sidebar [data-page="home"]').click();await p.waitForTimeout(150);await shot(`reference-students-${width}-${theme}`);
  }
 }
 assert.deepEqual(errors,[]);fs.writeFileSync(`${dir}/results.json`,JSON.stringify({results,errors,interactions:'passed'},null,2));await b.close();console.log('PASS: 84 views, all administrative actions, system themes, reduced motion, student comparison captures; no JS errors.');
})().catch(e=>{console.error(e);process.exit(1)});
