import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const read=f=>readFileSync(new URL('../dist/'+f,import.meta.url),'utf8');
const escape=x=>String(x??'').replace(/[&<>"']/g,t=>({
 '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[t]));
const sample={
 days:30,since:'2026-10-09',until:'2026-11-07',
 summary:{sessions_active:12,professionals_active:24,mfa_enabled:22,mfa_pending:2,
  failures:3,successes:14,revoked_7d:2,expiring_24h:4},
 my_mfa:{enabled:true,remaining_recovery_codes:6},
 my_sessions:[
  {id:101,current:true,device:{browser:'Firefox',os:'Linux',kind:'ordinateur'},
   created_at:'2026-11-01T10:00:00Z',last_seen_at:'2026-11-07T20:00:00Z',expires_at:'2026-11-08T20:00:00Z'},
  {id:102,current:false,device:{browser:'Chrome',os:'Windows',kind:'ordinateur'},
   created_at:'2026-11-01T11:00:00Z',last_seen_at:'2026-11-07T20:00:00Z',expires_at:'2026-11-08T20:00:00Z'},
 ],
 trend:{granularity:'day',labels:['2026-11-05','2026-11-06','2026-11-07'],
  successes:[4,5,5],failures:[1,0,2]},
 sources:{sessions:'EstablishmentWebSession',mfa:'PrivilegedMFADevice',attempts:'LoginAttempt'},
};
function factory(api,visible=()=>true){
 const sandbox={window:{},Date,Intl,Number,Object,String,Promise,
  document:{createElement:()=>{throw Error('Dialog needs browser')}},setTimeout,clearTimeout};
 runInNewContext(read('security-e62.js'),sandbox);
 let draws=0;
 const controller=sandbox.window.GConnectSecurityE62({
  api,safe:escape,render:()=>draws++,isVisible:visible,
 });
 return {controller,draws:()=>draws};
}
test('E62 is mounted only in Superadmin sessions and E61/E60/E59 preserve their pages',()=>{
 const shell=read('admin-connected-e19.html');
 const client=read('etablissement-api.js');
 assert.match(shell,/pages\.sessions=securityE62\.page/);
 assert.match(shell,/view==='sessions'\)securityE62\?\.ensure/);
 assert.match(shell,/security-e62\.css\?v=e62-guardian-1/);
 assert.match(shell,/security-e62\.js\?v=e62-guardian-1/);
 for(const [page,ref]of [['audit','auditE61'],['statistiques','statisticsE60'],
  ['moderation','moderationE59'],['imports','importsE58'],['contenus','contentsE57']]){
  assert.ok(shell.includes('pages.'+page+'='+ref+'.page'),page);
 }
 assert.match(client,/const adminSecurityOverview = params/);
 assert.match(client,/const adminSecurityRevokeOwnSession = \(id,payload\)/);
 assert.match(client,/privilegedRequest\('\/backoffice\/security-v2\/\?days='\+days\)/);
 assert.match(client,/payload\?\.confirmation!=='REVOQUER'/);
});
test('E62 renders factual summary, limited own sessions and MFA recovery count',async()=>{
 const args=[];
 const {controller}=factory({adminSecurityOverview:async p=>{args.push(p);return sample}});
 assert.match(controller.page(),/e62-metric[^>]*>/);
 assert.match(controller.page(),/e62-metric[^>]*>[\s\S]*?<strong>—<\/strong>/);
 await controller.load();
 const html=controller.page();
 assert.equal(args[0].days,30);
 assert.match(html,/Sessions <em>& sécurité<\/em>/);
 assert.match(html,/e62-metric[^>]*>[\s\S]*?<strong>12<\/strong>/);
 assert.match(html,/22 \/ 24/);
 assert.match(html,/Codes de secours encore utilisables : 6/);
 assert.match(html,/Firefox · Linux/);
 assert.match(html,/Chrome · Windows/);
 assert.match(html,/Cette session/);
 assert.match(html,/data-e62-revoke="102"/);
 assert.doesNotMatch(html,/data-e62-revoke="101"/);
 assert.match(html,/e62-chart-column/);
 assert.match(html,/Aucune adresse IP/);
});
test('E62 period filters use live endpoint, never synthesize counts',async()=>{
 const calls=[];
 const {controller}=factory({adminSecurityOverview:async ({days})=>{
  calls.push(days);return {...sample,days};
 }});
 await controller.load();
 controller.action({dataset:{e62Days:'7'}});
 await new Promise(r=>setTimeout(r,5));
 assert.deepEqual(calls,[30,7]);
 assert.equal(controller.peek().days,7);
 assert.match(controller.page(),/Tentatives enregistrées · 7 jours/);
});
test('E62 invalid server response is refused and does not show made-up zeros',async()=>{
 const bad={...sample,summary:{sessions_active:12}};
 const {controller}=factory({adminSecurityOverview:async()=>bad});
 await controller.load();
 assert.match(controller.page(),/informations de sécurité incomplètes/);
 assert.match(controller.page(),/<strong>—<\/strong>/);
 assert.doesNotMatch(controller.page(),/e62-chart-column/);
});
test('E62 escapes untrusted device summaries and never treats HTML as markup',async()=>{
 const data={...sample,my_sessions:[{
  ...sample.my_sessions[0],device:{browser:'<img onerror=alert(1)>',os:'Linux',kind:'ordinateur'},
 }]};
 const {controller}=factory({adminSecurityOverview:async()=>data});
 await controller.load();
 assert.match(controller.page(),/&lt;img onerror=alert\(1\)&gt;/);
 assert.doesNotMatch(controller.page(),/<img onerror=alert/);
});
test('E62 art animation is optional, with reduced-motion and no shared CSS corruption',()=>{
 const css=read('security-e62.css');
 assert.match(css,/\.e62-hero\{/);
 assert.match(css,/background:transparent;border:0;box-shadow:none;border-radius:0/);
 assert.match(css,/@keyframes e62-card/);
 assert.match(css,/@keyframes e62-float/);
 assert.match(css,/@keyframes e62-bar/);
 assert.match(css,/prefers-reduced-motion:reduce/);
 assert.match(css,/data-motion="off"/);
 assert.doesNotMatch(css,/\.sidebar\{/);
});
