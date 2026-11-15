import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[c]));
const data={
  days:180,since:'2026-05-12',until:'2026-11-07',granularity:'month',
  summary:{
    new_accounts:48,previous_accounts:32,growth_percent:50.0,
    accounts_total:148,accounts_active:139,accounts_banned:2,
    institutions_total:17,institutions_active:15,
    enterprises_total:13,enterprises_verified:11,
    posts_total:94,posts_published:81,posts_hidden:4,
    comments_total:32,reactions_total:180,applications_total:27,
    reports_pending:2,subscriptions_active:9,
  },
  roles:{student:92,alumni:27,enterprise:13,etablissement:15,superAdmin:1},
  contents:{opportunity:28,event:17,project:14,discussion:24,share:11},
  trend:{
    labels:['2026-05-01','2026-06-01','2026-07-01','2026-08-01','2026-09-01','2026-10-01','2026-11-01'],
    accounts:[3,4,6,8,7,15,5],posts:[1,3,7,5,8,9,10],
    institutions:[0,1,1,0,2,1,1],enterprise_accounts:[1,0,0,1,1,1,0],
  },
  sources:{
    accounts:'User.date_joined',posts:'Post.created_at',
    institutions:'Institution.created_at',
    enterprise_accounts:'Enterprise.user.date_joined',
  },
};
function factory(api,visible=()=>true){
  const context={window:{},Date,Intl,Number,Object,String,Promise,
    document:{createElement:()=>{throw Error('No DOM outside browser')}},setTimeout,clearTimeout};
  runInNewContext(read('statistics-e60.js'),context);
  let draws=0;
  const controller=context.window.GConnectStatisticsE60({
    api,safe:escape,render:()=>draws++,isVisible:visible,
  });
  return {controller,draws:()=>draws};
}
test('E60 is strictly scoped to existing Superadmin Statistics and retains every Premium module',()=>{
  const api=read('etablissement-api.js'),shell=read('admin-connected-e19.html');
  assert.match(api,/const adminGlobalStatistics = params/);
  assert.match(api,/privilegedRequest\('\/backoffice\/statistics-v2\/\?days='\+days\)/);
  assert.match(api,/adminGlobalStatistics,/);
  assert.match(shell,/statistics-e60.css\?v=e60-observatory-1/);
  assert.match(shell,/statistics-e60.js\?v=e60-observatory-1/);
  assert.match(shell,/pages\.statistiques=statisticsE60\.page/);
  assert.match(shell,/view==='statistiques'\)statisticsE60\?\.ensure/);
  for(const other of ['moderationE59','importsE58','contentsE57','invitationsE54']){
    assert.match(shell,new RegExp('pages\\.(moderation|imports|contenus|invitations)='+other+'\\.page'));
  }
});
test('E60 shows real counters and SVG time series, never demo metrics or imaginary bars',async()=>{
  const calls=[];
  const {controller}=factory({adminGlobalStatistics:async p=>{calls.push(p);return data}});
  let html=controller.page();
  assert.match(html,/Statistiques <em>globales<\/em>/);
  assert.match(html,/e60-metric-value">—<\/strong>/);
  assert.doesNotMatch(html,/2 680|1 944|Chiffres fictifs|Représentation fictive/);
  await controller.load();
  html=controller.page();
  assert.equal(calls[0].days,180);
  assert.match(html,/e60-metric-value">48<\/strong>/);
  assert.match(html,/e60-metric-value">11<\/strong>/);
  assert.match(html,/e60-metric-value">15<\/strong>/);
  assert.match(html,/e60-metric-value">148<\/strong>/);
  assert.match(html,/50 % par rapport aux 6 mois précédents/);
  assert.match(html,/e60-plot-wrap/);
  assert.match(html,/e60-line-primary/);
  assert.match(html,/e60-line-secondary/);
  assert.match(html,/Date de création du compte responsable|date de création du compte responsable/i);
  assert.match(html,/e60-activity-item/);
  assert.match(html,/Aucune donnée fictive/);
});
test('E60 period switch requests new data, no stale rows if network fails',async()=>{
  let mode='ok';const calls=[];
  const {controller}=factory({adminGlobalStatistics:async p=>{
    calls.push(p.days);
    if(mode==='err')throw Error('Session MFA requise');
    return {...data,days:p.days,granularity:p.days===30?'day':'week'};
  }});
  await controller.load();
  controller.action({dataset:{e60Period:'90'}});
  await new Promise(r=>setTimeout(r,1));
  assert.deepEqual(calls,[180,90]);
  assert.equal(controller.peek().days,90);
  mode='err';
  controller.action({dataset:{e60Period:'30'}});
  await new Promise(r=>setTimeout(r,1));
  assert.match(controller.page(),/Session MFA requise/);
  assert.match(controller.page(),/data-e60-action="refresh"/);
  assert.match(controller.page(),/e60-metric-value">—<\/strong>/);
  assert.doesNotMatch(controller.page(),/e60-metric-value">48<\/strong>/);
});
test('E60 rejects server data with mismatched series instead of drawing fictitious values',async()=>{
  const broken={...data,trend:{...data.trend,posts:[1,3]}};
  const {controller}=factory({adminGlobalStatistics:async()=>broken});
  await controller.load();
  assert.match(controller.page(),/jeu statistique incomplet/);
  assert.doesNotMatch(controller.page(),/e60-line-primary/);
});
test('E60 never substitutes missing backend role counts with fake zeros',async()=>{
  const missing={...data,roles:{student:92,alumni:27}};
  const {controller}=factory({adminGlobalStatistics:async()=>missing});
  await controller.load();
  assert.match(controller.page(),/jeu statistique incomplet/);
  assert.doesNotMatch(controller.page(),/e60-distribution-item/);
});
test('E60 has independent animated charts and reduced-motion rules',()=>{
  const css=read('statistics-e60.css');
  assert.match(css,/\.e60-hero\{/);
  assert.match(css,/background:transparent;border:0;border-radius:0;box-shadow:none/);
  assert.match(css,/@keyframes e60-line/);
  assert.match(css,/@keyframes e60-bar/);
  assert.match(css,/@keyframes e60-float/);
  assert.match(css,/prefers-reduced-motion:reduce/);
  assert.match(css,/data-motion="off"/);
  assert.doesNotMatch(css,/\.sidebar\{/);
  assert.doesNotMatch(css,/\.e59-page\{/);
});
