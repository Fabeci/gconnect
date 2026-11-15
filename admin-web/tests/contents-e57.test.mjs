import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[c]));
const summary={
  total:3,opportunities:1,events:1,projects:0,discussions:1,
  drafts:0,archived:0,hidden:0,published:3,reports_pending:1,
};
const rows=[
  {id:1,title:'Ingénieur <script>alert(1)</script>',description:'Stage et emploi',
    excerpt:'Emploi à Dakar',type:'opportunity',state:'published',audience:'public',
    author_name:'Awa Sow',organisation:'Horizon <img onerror=alert(1)>',
    created_at:'2026-11-06T08:00:00Z',views:12,comments:2,reactions:3,pending_reports:1},
  {id:2,title:'Forum alumni',description:'Bienvenue à la communauté',
    excerpt:'Événement campus',type:'event',state:'published',
    author_name:'Campus',organisation:'École',created_at:'2026-11-05T11:00:00Z',
    views:0,comments:0,reactions:0,pending_reports:0},
  {id:3,title:'Retour de stage',description:'Discussion',excerpt:'Conseils',
    type:'discussion',state:'published',author_name:'Alumni',organisation:null,
    created_at:'2026-11-04T11:00:00Z',views:1,comments:0,reactions:0,pending_reports:0},
];

function factory(api,visible=()=>true){
  const context={window:{},document:{createElement:()=>{throw Error('Not in text-only test')}},
    Date,Intl,Object,Number,String,Promise,setTimeout,clearTimeout};
  runInNewContext(read('contents-e57.js'),context);
  let renders=0;
  const controller=context.window.GConnectContentsE57({
    api,safe:escape,render:()=>{renders++},isVisible:visible,go:()=>{},
  });
  return {controller,renders:()=>renders};
}

test('E57 includes privileged global Django URL, but changes no other privileged API method',()=>{
  const api=read('etablissement-api.js');
  const shell=read('admin-connected-e19.html');
  assert.match(api,/const adminContentDirectory = params/);
  assert.match(api,/privilegedRequest\('\/backoffice\/content-directory\/\?'\+query\.toString\(\)\)/);
  assert.match(api,/adminContentDirectory,/);
  assert.match(shell,/GConnectContentsE57/);
  assert.match(shell,/pages\.contenus=contentsE57\.page/);
  assert.match(shell,/view==='contenus'\)contentsE57\?\.ensure\(\)/);
  assert.match(shell,/contents-e57\.css/);
  assert.match(shell,/contents-e57\.js/);
  assert.match(shell,/pages\.facturation=\(\)=>financeE36\.page\(\)/);
  assert.match(shell,/pages\.invitations=invitationsE54\.page/);
});

test('E57 shows only real server counts, safe text, editorial filters and details',async()=>{
  const requested=[];
  const {controller}=factory({
    adminContentDirectory:async params=>{
      requested.push({...params});
      return {summary,count:3,pages:1,page:1,results:rows};
    },
  });
  assert.match(controller.page(),/e57-hero/);
  assert.match(controller.page(),/e57-metric-value">—<\/span>/);
  await controller.load();
  assert.equal(requested.length,1);
  assert.equal(requested[0].type,'all');
  assert.equal(requested[0].page_size,12);
  const html=controller.page();
  assert.match(html,/Offres <em>&<\/em> contenus/);
  assert.match(html,/Ingénieur &lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.doesNotMatch(html,/<script>alert\(1\)<\/script>/);
  assert.match(html,/Horizon &lt;img onerror=alert\(1\)&gt;/);
  assert.doesNotMatch(html,/<img onerror=/);
  assert.match(html,/Forum alumni/);
  assert.match(html,/3 contenus/);
  assert.match(html,/data-e57-filter="kind"/);
  assert.match(html,/data-e57-filter="status"/);
  assert.match(html,/data-e57-detail="1"/);
  assert.doesNotMatch(html,/Aucune donnée inventée|Connexion aux données à finaliser/);
});

test('E57 refuses to invent zeros when the API fails',async()=>{
  const {controller}=factory({
    adminContentDirectory:async()=>{throw Error('Authentification expirée')},
  });
  await controller.load();
  const html=controller.page();
  assert.match(html,/Authentification expirée/);
  assert.match(html,/Données indisponibles/);
  assert.match(html,/e57-metric-value">—<\/span>/);
  assert.doesNotMatch(html,/e57-metric-value">0<\/span>/);
});

test('E57 filters and paging request the server, not client-side synthetic data',async()=>{
  const calls=[];
  const {controller}=factory({
    adminContentDirectory:async params=>{
      calls.push({...params});
      return {summary,count:24,page:params.page,pages:2,results:params.type==='event'?rows.slice(1,2):rows};
    },
  });
  await controller.load();
  controller.action({dataset:{e57Type:'event'}});
  await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(calls[1].type,'event');
  assert.equal(controller.peek().kind,'event');
  controller.action({dataset:{e57Action:'next'}});
  await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(calls[2].page,2);
  controller.onFilter({dataset:{e57Filter:'status'},value:'hidden'});
  await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(calls[3].state,'hidden');
  assert.equal(calls[3].page,1);
  controller.action({dataset:{e57Action:'clear'}});
  await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(calls[4].type,'all');
  assert.equal(calls[4].state,'all');
});

test('E57 CSS stays in its own namespace, animates pages, and honors reduced motion',()=>{
  const css=read('contents-e57.css');
  assert.match(css,/\.e57-hero\{/);
  assert.match(css,/background:transparent;border:0;box-shadow:none;border-radius:0/);
  assert.match(css,/@keyframes e57-badge-float/);
  assert.match(css,/@keyframes e57-card-up/);
  assert.match(css,/@keyframes e57-bar-load/);
  assert.match(css,/prefers-reduced-motion:reduce/);
  assert.match(css,/data-motion="off"/);
  assert.doesNotMatch(css,/html\[data-module="facturation"\]/);
  assert.doesNotMatch(css,/\.sidebar\{/);
});

test('E57 latest filter wins over a slow previous HTTP response',async()=>{
  const pending=[];
  const {controller}=factory({
    adminContentDirectory:params=>new Promise(resolve=>{
      pending.push({params,resolve});
    }),
  });
  const first=controller.load();
  assert.equal(pending.length,1);
  controller.action({dataset:{e57Type:'event'}});
  assert.equal(pending.length,2);
  const makeResult=(page,count)=>({
    summary:{...summary,total:count},count,pages:1,page,results:rows.slice(0,count),
  });
  pending[1].resolve(makeResult(1,1));
  await new Promise(resolve=>setTimeout(resolve,0));
  pending[0].resolve(makeResult(1,3));
  await first;
  assert.equal(controller.peek().kind,'event');
  assert.equal(controller.peek().count,1);
  assert.equal(controller.peek().loaded,true);
});
