const {chromium}=require('playwright');const fs=require('node:fs');const assert=require('node:assert/strict');
(async()=>{
 const b=await chromium.launch({headless:true}),c=await b.newContext({viewport:{width:1024,height:768}});const results={};
 for(const [name,url,collapse,sidebar,menu] of [['students','/','#collapse','.sidebar','#mobile-menu'],['establishment','/etablissement.html','#ea-collapse','.ea-sidebar','#ea-open-menu']]){
  const p=await c.newPage();await p.goto('http://localhost:8086'+url);await p.waitForTimeout(1000);
  const sample=async(trigger,target,prop)=>p.evaluate(async({trigger,target,prop})=>{
   const out=[],start=performance.now();const read=()=>{const e=document.querySelector(target);return prop==='width'?e.getBoundingClientRect().width:getComputedStyle(e)[prop]};out.push({t:0,value:read()});document.querySelector(trigger).click();
   while(performance.now()-start<1500){await new Promise(requestAnimationFrame);out.push({t:Math.round(performance.now()-start),value:read()});}return out;
  },{trigger,target,prop});
  results[name]={sidebar:await sample(collapse,sidebar,'width')};
  fs.writeFileSync(`artifacts/animation-equivalence-20261022/${name}-transition-debug.json`,JSON.stringify(results[name],null,2));
  assert(new Set(results[name].sidebar.map(s=>s.value)).size>2,name+' sidebar intermediate widths');
  await p.setViewportSize({width:390,height:844});await p.waitForTimeout(350);results[name].mobile=await sample(menu,sidebar,'transform');
  fs.writeFileSync(`artifacts/animation-equivalence-20261022/${name}-transition-debug.json`,JSON.stringify(results[name],null,2));
  assert(new Set(results[name].mobile.map(s=>s.value)).size>2,name+' mobile intermediate transforms');
  if(name==='establishment'){
   await p.keyboard.press('Escape');await p.setViewportSize({width:1024,height:768});await p.waitForTimeout(300);
   results[name].active=await p.evaluate(async()=>{
    const target=document.querySelector('.ea-nav [data-route="promotions"]'),values=[];target.click();const start=performance.now();while(performance.now()-start<1000){await new Promise(requestAnimationFrame);values.push(getComputedStyle(target,'::before').transform)}return values;
   });assert(new Set(results[name].active).size>1,'active navigation animates');
   await p.locator('.ea-nav [data-route="overview"]').click();await p.waitForTimeout(600);
   const button=p.locator('.ea-actions .ea-button.primary');await button.hover();await p.mouse.down();await p.waitForTimeout(80);assert.match(await button.evaluate(e=>getComputedStyle(e).transform),/0.97/);await p.mouse.up();
   await p.waitForTimeout(650);assert.equal(await p.locator('.ea-ripple-host').count(),0,'detached ripple cleaned');
  }
 }
 fs.writeFileSync('artifacts/animation-equivalence-20261022/transitions.json',JSON.stringify(results,null,2));await b.close();console.log('PASS: intermediate sidebar widths, mobile transforms, active navigation, press and ripple cleanup');
})().catch(e=>{console.error(e);process.exit(1)});
