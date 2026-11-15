import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const read=file=>readFileSync(new URL('../dist/'+file,import.meta.url),'utf8');
const esc=text=>String(text??'').replace(/[&<>"']/g,k=>({
 '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[k]));
const events=[
 {id:7,action:'login_success',label:'Connexion réussie',category:'access',
  actor:'Administrateur',actor_role:'superAdmin',actor_id:1,
  created_at:'2026-11-07T18:25:00Z',details:{user_id:1}},
 {id:6,action:'invitation_sent',label:'Invitation envoyée',category:'invitations',
  actor:'G-Connect',actor_role:'superAdmin',actor_id:1,
  created_at:'2026-11-07T18:11:00Z',details:{enterprise_id:4}},
 {id:5,action:'report_reviewed',label:'Signalement examiné',category:'moderation',
  actor:'G-Connect',actor_role:'superAdmin',actor_id:1,
  created_at:'2026-11-07T17:30:00Z',details:{report_id:2,outcome:'dismissed'}},
 {id:4,action:'import_completed',label:'Import massif effectué',category:'operations',
  actor:'G-Connect',actor_role:'superAdmin',actor_id:1,
  created_at:'2026-11-06T20:25:00Z',details:{job_id:3,total:5,errors:1}},
];
const base={
 days:30,since:'2026-10-09',until:'2026-11-07',
 summary:{events:4,invitations:1,moderation:1,access:1,operations:1,other:0,failed_access:0},
 action_choices:[
  {value:'login_success',label:'Connexion réussie'},
  {value:'invitation_sent',label:'Invitation envoyée'},
  {value:'report_reviewed',label:'Signalement examiné'},
  {value:'import_completed',label:'Import massif effectué'},
 ],
 trend:{
  granularity:'day',labels:['2026-11-05','2026-11-06','2026-11-07'],
  events:[0,1,3],
 },
 page:1,pages:1,page_size:12,count:4,results:events,
};
function factory(api,visible=()=>true){
 const context={window:{},Intl,Date,Number,Object,String,Promise,setTimeout,clearTimeout,
   document:{createElement:()=>{throw Error('browser only')}}};
 runInNewContext(read('audit-e61.js'),context);
 let renders=0;
 const ctrl=context.window.GConnectAuditE61({
  api,safe:esc,render:()=>renders++,isVisible:visible,
 });
 return {ctrl,renders:()=>renders};
}
test('E61 integrates the new journal only and keeps earlier Premium modules intact',()=>{
 const api=read('etablissement-api.js');
 const shell=read('admin-connected-e19.html');
 assert.match(api,/const adminAuditDirectory = params/);
 assert.match(api,/privilegedRequest\('\/backoffice\/audit-v2\/\?'\+query\.toString\(\)\)/);
 assert.match(shell,/pages\.audit=auditE61\.page/);
 assert.match(shell,/view==='audit'\)auditE61\?\.ensure/);
 assert.match(shell,/audit-e61\.css\?v=e61-trust-1/);
 assert.match(shell,/audit-e61\.js\?v=e61-trust-1/);
 for(const [page,ref] of [['statistiques','statisticsE60'],['moderation','moderationE59'],
   ['imports','importsE58'],['contenus','contentsE57'],['invitations','invitationsE54']]){
   assert.ok(shell.includes('pages.'+page+'='+ref+'.page'));
 }
});
test('E61 never shows demo counts; it renders chronological actual returned events',async()=>{
 const calls=[];
 const {ctrl}=factory({adminAuditDirectory:async params=>{calls.push({...params});return base}});
 let html=ctrl.page();
 assert.match(html,/Journal <em>d’audit<\/em>/);
 assert.match(html,/e61-metric-number">—<\/strong>/);
 assert.doesNotMatch(html,/Chiffres fictifs|Connexion aux données à finaliser|Mode démonstration/);
 await ctrl.load();html=ctrl.page();
 assert.equal(calls.length,1);assert.equal(calls[0].days,30);
 assert.match(html,/e61-metric-number">4<\/strong>/);
 assert.match(html,/Connexion réussie/);
 assert.match(html,/Invitation envoyée/);
 assert.match(html,/Signalement examiné/);
 assert.match(html,/e61-chart/);
 assert.match(html,/e61-event/);
 assert.match(html,/data-e61-item="7"/);
});
test('E61 escapes server names and event labels as text, never executable HTML',async()=>{
 const malicious={...base,results:[
  {...events[0],actor:'<img onerror=alert(1)>',label:'<script>alert(1)</script>'},
 ]};
 const {ctrl}=factory({adminAuditDirectory:async()=>malicious});
 await ctrl.load();
 const html=ctrl.page();
 assert.match(html,/&lt;img onerror=alert\(1\)&gt;/);
 assert.match(html,/&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
 assert.doesNotMatch(html,/<img onerror=alert/);
 assert.doesNotMatch(html,/<script>alert/);
});
test('E61 filters and periods always query the server, no fabricated search result',async()=>{
 const calls=[];
 const {ctrl}=factory({adminAuditDirectory:async p=>{
  calls.push({...p});
  return {...base,days:p.days,page:p.page};
 }});
 await ctrl.load();
 ctrl.filter({dataset:{e61Filter:'category'},value:'moderation'});
 await new Promise(resolve=>setTimeout(resolve,5));
 assert.equal(calls[1].category,'moderation');
 ctrl.filter({dataset:{e61Filter:'action'},value:'report_reviewed'});
 await new Promise(resolve=>setTimeout(resolve,5));
 assert.equal(calls[2].action,'report_reviewed');
 ctrl.action({dataset:{e61Days:'7'}});
 await new Promise(resolve=>setTimeout(resolve,5));
 assert.equal(calls[3].days,7);
 assert.equal(ctrl.peek().days,7);
 ctrl.search({value:'G-Connect'});
 await new Promise(resolve=>setTimeout(resolve,360));
 assert.equal(calls[4].search,'G-Connect');
});
test('E61 clears old counters on API error instead of displaying fictitious zeros',async()=>{
 const {ctrl}=factory({adminAuditDirectory:async()=>{throw Error('Session WebToken expirée')}});
 await ctrl.load();
 const html=ctrl.page();
 assert.match(html,/Session WebToken expirée/);
 assert.match(html,/data-e61-action="refresh"/);
 assert.match(html,/e61-metric-number">—<\/strong>/);
 assert.doesNotMatch(html,/e61-metric-number">0<\/strong>/);
});
test('E61 uses transparent hero, entry motion and reduced-motion accessibility',()=>{
 const css=read('audit-e61.css');
 assert.match(css,/\.e61-hero\{/);
 assert.match(css,/border:0;box-shadow:none;background:transparent;border-radius:0/);
 assert.match(css,/@keyframes e61-float/);
 assert.match(css,/@keyframes e61-bars/);
 assert.match(css,/@keyframes e61-card/);
 assert.match(css,/prefers-reduced-motion:reduce/);
 assert.match(css,/data-motion="off"/);
 assert.doesNotMatch(css,/\.sidebar\{/);
});
