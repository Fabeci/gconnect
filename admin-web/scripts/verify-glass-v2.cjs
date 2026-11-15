const {chromium}=require('playwright');
const fs=require('node:fs');
const dir=process.env.GLASS_ARTIFACT_DIR||'artifacts/glass-v2';fs.mkdirSync(dir,{recursive:true});
(async()=>{
const browser=await chromium.launch({headless:true});
const page=await browser.newPage(); const errors=[]; const results=[];
page.on('pageerror',e=>errors.push(e.message));
const nav=async(view,width)=>{if(width<=900){await page.locator('#mobile-menu').click();await page.waitForTimeout(250);}await page.locator(`.sidebar [data-page="${view}"]`).click();await page.waitForTimeout(400)};
for(const width of [320,390,768,1024,1440,1920]){
 await page.setViewportSize({width,height:1000}); await page.goto('http://localhost:8086'); await page.waitForTimeout(400);
 for(const theme of ['light','dark']){
  await nav('settings',width);await page.locator(`button[data-theme="${theme}"]`).click();await page.waitForTimeout(400);
  for(const view of ['home','jobs','network','school','messages','profile','settings']){
   await nav(view,width);
   const metrics=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,logo:document.querySelector('.mobile-brand').getBoundingClientRect().width,hero:document.querySelector('.hero')?.getBoundingClientRect().height,header:document.querySelector('.topbar').getBoundingClientRect().height}));
   results.push({width,theme,view,...metrics});
   if(metrics.overflow) throw Error(`overflow ${width} ${theme} ${view}`);
   await page.evaluate(async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,70));}window.scrollTo(0,0)});
   await page.waitForTimeout(400);
   await page.screenshot({path:`${dir}/${width}-${theme}-${view}.png`,fullPage:true,animations:"disabled"});
  }
 }
 if(width>900){await page.locator('#collapse').click();await page.waitForFunction(()=>Math.abs(document.querySelector('.sidebar').getBoundingClientRect().width-76)<1);const w=await page.locator('.sidebar').evaluate(e=>e.getBoundingClientRect().width);if(Math.abs(w-76)>1)throw Error(`collapse ${w}`);await page.locator('#collapse').click();}
 else {await page.locator('#mobile-menu').click();await page.waitForTimeout(300);await page.locator('#collapse').click();if(await page.locator('.shell').evaluate(e=>e.classList.contains('mobile-open')))throw Error('mobile close');await page.locator('#mobile-menu').click();await page.keyboard.press('Escape');}
}
await page.setViewportSize({width:1440,height:1000});await nav('jobs',1440);
await page.locator('[data-filter="Stage"]').click();await page.waitForTimeout(400);if(await page.locator('.op-card').count()!==3)throw Error('filter');
await page.locator('[data-save]').first().click();await page.waitForTimeout(400);if(!await page.locator('.apply-btn.saved').count())throw Error('save');
await nav('settings',1440);await page.emulateMedia({colorScheme:'dark'});await page.locator('button[data-theme="light"]').click();if(await page.locator('html').getAttribute('data-theme')!=='light')throw Error('light override');await page.locator('button[data-theme="system"]').click();if(await page.locator('html').getAttribute('data-theme')!=='dark')throw Error('system');
await page.emulateMedia({reducedMotion:'reduce'});await nav('home',1440);if(await page.locator('.hero h1').evaluate(e=>getComputedStyle(e).animationName)!=='none')throw Error('reduced motion');
fs.writeFileSync(`${dir}/results.json`,JSON.stringify({results,errors,interactions:'passed'},null,2));
await browser.close();if(errors.length)throw Error(errors.join('\n'));console.log(`${results.length} page/theme/viewport checks passed; sidebar, filters, save, themes, reduced motion passed.`);
})().catch(e=>{console.error(e);process.exit(1)});
