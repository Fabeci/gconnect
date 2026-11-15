const {chromium}=require('playwright');
(async()=>{
const b=await chromium.launch({headless:true});const p=await b.newPage();
for(const width of [320,390,768,1024,1440,1920]){
 await p.setViewportSize({width,height:1000}); await p.goto('http://localhost:8086');await p.waitForTimeout(400);
 for(const theme of ['light','dark']){
  if(width<=900){await p.locator('#mobile-menu').click();await p.waitForTimeout(250)}
  await p.locator('.sidebar [data-page="settings"]').click();await p.waitForTimeout(400);
  await p.locator(`button[data-theme="${theme}"]`).click();await p.waitForTimeout(400);
  if(width<=900){await p.locator('#mobile-menu').click();await p.waitForTimeout(250)}
  await p.locator('.sidebar [data-page="home"]').click();await p.waitForTimeout(400);
  await p.evaluate(async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,70))}scrollTo(0,0)});await p.waitForTimeout(400);
  await p.screenshot({path:`artifacts/glass-v2/${width}-${theme}-home.png`,fullPage:true,animations:'disabled'});
 }
 if(width===1440){await p.locator('#collapse').click();await p.waitForTimeout(300);await p.screenshot({path:'artifacts/glass-v2/sidebar-collapsed.png',animations:'disabled'})}
 if(width===390){await p.locator('#mobile-menu').click();await p.waitForTimeout(300);await p.screenshot({path:'artifacts/glass-v2/mobile-menu.png',animations:'disabled'})}
}
await b.close();console.log('Final home and navigation captures complete');
})().catch(e=>{console.error(e);process.exit(1)});
