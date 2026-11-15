const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const dir=process.env.COMPARE_DIR||'artifacts/comparison-20261022';fs.mkdirSync(dir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 const student=await browser.newPage(),admin=await browser.newPage();const errors=[];
 for(const p of [student,admin])p.on('pageerror',e=>errors.push(e.message));
 const go=async(p,space,id,width)=>{if(width<=900)await p.locator(space==='student'?'#mobile-menu':'#ea-open-menu').click();await p.locator(space==='student'?`.sidebar [data-page="${id}"]`:`.ea-nav [data-route="${id}"]`).click();await p.waitForTimeout(350)};
 const cases=[['desktop-light',1440,'light','home','overview'],['desktop-dark',1440,'dark','home','overview'],['mobile-home',390,'light','home','overview'],['collapsed',1440,'light','home','overview'],['mobile-menu',390,'light','home','overview'],['settings',1440,'light','settings','settings'],['settings-dark',1440,'dark','settings','settings'],['mobile-settings',390,'dark','settings','settings'],['forms',1440,'light','profile','promotions']];
 for(const [name,width,theme,sv,av] of cases){
  for(const p of [student,admin])await p.setViewportSize({width,height:1000});
  await student.goto('http://localhost:8086');await admin.goto('http://localhost:8086/etablissement.html');
  await go(student,'student','settings',width);await student.locator(`button[data-theme="${theme}"]`).click();await student.waitForTimeout(350);
  await go(student,'student',sv,width);await admin.locator('#ea-theme').selectOption(theme);await go(admin,'admin',av,width);
  if(name==='collapsed'){await student.locator('#collapse').click();await admin.locator('#ea-collapse').click()}
  if(name==='mobile-menu'){await student.locator('#mobile-menu').click();await admin.locator('#ea-open-menu').click()}
  for(const [label,p] of [['students',student],['establishment',admin]]){
   await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(400);
   // Reveal the reference's below-the-fold cards before a full-page capture.
   if(name!=='mobile-menu')await p.evaluate(async()=>{for(let y=0;y<document.body.scrollHeight;y+=700){scrollTo(0,y);await new Promise(r=>setTimeout(r,40))}scrollTo(0,0)});
   await p.waitForTimeout(350);await p.screenshot({path:`${dir}/${name}-${label}.png`,fullPage:true,animations:'disabled'});
  }
 }
 await admin.setViewportSize({width:1440,height:1000});await go(admin,'admin','settings',1440);
 await admin.locator('#ea-profile-form [name="name"]').fill('Brouillon conservé');
 for(const theme of ['dark','light','system']){await admin.locator(`[data-appearance="${theme}"]`).click();assert.equal(await admin.locator('#ea-theme').inputValue(),theme);assert.equal(await admin.locator('#ea-profile-form [name="name"]').inputValue(),'Brouillon conservé')}
 await admin.locator('#ea-reduce-motion').check();await go(admin,'admin','overview',1440);assert.equal(await admin.locator('.ea-hero').evaluate(e=>getComputedStyle(e).animationName),'none');await go(admin,'admin','settings',1440);assert(await admin.locator('#ea-reduce-motion').isChecked());
 await admin.locator('#ea-toggle-settings').click();await admin.waitForTimeout(300);assert.equal(await admin.locator('.ea-sidebar').evaluate(e=>e.offsetWidth),76);
 await admin.setViewportSize({width:390,height:1000});await admin.locator('#ea-open-menu').click();await admin.keyboard.press('Shift+Tab');assert(await admin.locator('.ea-nav-item').last().evaluate(e=>e===document.activeElement));await admin.keyboard.press('Tab');assert(await admin.locator('#ea-collapse').evaluate(e=>e===document.activeElement));await admin.keyboard.press('Escape');assert(await admin.locator('#ea-open-menu').evaluate(e=>e===document.activeElement));
 await admin.emulateMedia({reducedMotion:'reduce'});assert.equal(await admin.locator('.ea-sidebar').evaluate(e=>getComputedStyle(e).transitionDuration),'0s');
 assert.deepEqual(errors,[]);fs.writeFileSync(`${dir}/checks.json`,JSON.stringify({comparisons:cases.length,settings:true,keyboardFocusTrap:true,reducedMotion:true,errors},null,2));await browser.close();console.log('PASS: 9 comparison pairs; settings, draft preservation, keyboard focus, reduced motion; no JS errors.');
})().catch(e=>{console.error(e);process.exit(1)});
