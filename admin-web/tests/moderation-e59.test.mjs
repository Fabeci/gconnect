import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({
 '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[c]));
const report={
  id:12,reason:'harassment',reason_display:'Harcèlement',
  status:'pending',target:'post',target_title:'Une publication <script>alert(1)</script>',
  target_excerpt:'Mots <b>non sûrs</b>',description:'Dossier <img onerror=alert(1)>',
  reported_by:'Exemple Auteur',organisation:'Institution Test',
  created_at:'2026-11-07T17:00:00Z',
  critical:true,can_hide:true,can_dismiss:true,is_hidden:false,
};
const response={
  summary:{total:4,pending:3,resolved:1,reviewed_30d:1,critical_pending:2,dismissed:1,actioned:0},
  by_reason:{harassment:1,hate_speech:1,spam:1,fake_info:0,inappropriate:0,other:0},
  results:[report],count:1,page:1,pages:1,page_size:10,
};
const factory=(api,visible=()=>true)=>{
 const context={window:{},Date,Intl,Object,Number,String,Promise,
 setTimeout,clearTimeout,document:{createElement:()=>{throw Error('Browser only')}}};
 runInNewContext(read('moderation-e59.js'),context);
 let renders=0;
 const controller=context.window.GConnectModerationE59({
   api,safe:escape,render:()=>{renders++},isVisible:visible,
 });
 return {controller,renders:()=>renders};
};

test('E59 uses distinct Premium identity and existing Superadmin MFA client, preserving other modules',()=>{
 const api=read('etablissement-api.js');
 const shell=read('admin-connected-e19.html');
 assert.match(api,/const adminModerationDirectory = params/);
 assert.match(api,/privilegedRequest\('\/backoffice\/moderation-v2\/\?'/);
 assert.match(api,/const adminModerationDecision = \(id,payload\)/);
 assert.match(api,/privilegedRequest\('\/backoffice\/moderation-v2\/'\+value\+'\/decision\/','POST',payload\)/);
 assert.match(shell,/moderation-e59\.css\?v=e59-trust-1/);
 assert.match(shell,/moderation-e59\.js\?v=e59-trust-1/);
 assert.match(shell,/pages\.moderation=moderationE59\.page/);
 assert.match(shell,/view==='moderation'\)moderationE59\?\.ensure/);
 assert.match(shell,/pages\.imports=importsE58\.page/);
 assert.match(shell,/pages\.contenus=contentsE57\.page/);
 assert.match(shell,/pages\.invitations=invitationsE54\.page/);
 assert.match(read('imports-e58.css'),/\.e58-file-drop\{min-height:252px;height:auto;/);
});

test('E59 renders only real statistics, uses escaped server content and has no demonstration data',async()=>{
 const calls=[];
 const {controller}=factory({
  adminModerationDirectory:async p=>{calls.push(p);return response},
 });
 let markup=controller.page();
 assert.match(markup,/Modération <em>&<\/em> conformité/);
 assert.match(markup,/e59-metric-number">—<\/strong>/);
 await controller.load();
 markup=controller.page();
 assert.match(markup,/e59-metric-number">3<\/strong>/);
 assert.match(markup,/e59-metric-number">2<\/strong>/);
 assert.match(markup,/Une publication &lt;script&gt;alert\(1\)&lt;\/script&gt;/);
 assert.doesNotMatch(markup,/<script>alert/);
 assert.match(markup,/Dossier &lt;img onerror=alert\(1\)&gt;/);
 assert.match(markup,/data-e59-detail="12"/);
 assert.equal(calls[0].status,'pending');
 assert.equal(calls[0].page_size,10);
 assert.doesNotMatch(markup,/Connexion aux données à finaliser|Aucune donnée inventée|Mode démonstration/);
});
test('E59 filters are sent to the server and paging keeps the selected status',async()=>{
 const calls=[];
 const {controller}=factory({
  adminModerationDirectory:async params=>{calls.push({...params});return {...response,pages:3,page:params.page,count:21}},
 });
 await controller.load();
 controller.onFilter({dataset:{e59Filter:'status'},value:'all'});
 await new Promise(r=>setTimeout(r,10));
 assert.equal(calls[1].status,'all');
 controller.onFilter({dataset:{e59Filter:'reason'},value:'spam'});
 await new Promise(r=>setTimeout(r,10));
 assert.equal(calls[2].reason,'spam');
 controller.onFilter({dataset:{e59Filter:'target'},value:'comment'});
 await new Promise(r=>setTimeout(r,10));
 assert.equal(calls[3].target,'comment');
 controller.action({dataset:{e59Action:'next'}});
 await new Promise(r=>setTimeout(r,10));
 assert.equal(calls[4].page,2);
 assert.equal(controller.peek().status,'all');
});
test('E59 does not invent zero values on authorization or server errors',async()=>{
 const {controller}=factory({adminModerationDirectory:async()=>{throw Error('Session Superadmin expirée')}});
 await controller.load();
 const markup=controller.page();
 assert.match(markup,/Session Superadmin expirée/);
 assert.match(markup,/data-e59-action="refresh"/);
 assert.match(markup,/e59-metric-number">—<\/strong>/);
 assert.doesNotMatch(markup,/e59-metric-number">0<\/strong>/);
});
test('E59 styles have real motion, reduced-motion and a transparent hero',()=>{
 const css=read('moderation-e59.css');
 assert.match(css,/\.e59-hero\{/);
 assert.match(css,/background:transparent;border:0;box-shadow:none;border-radius:0/);
 assert.match(css,/@keyframes e59-float/);
 assert.match(css,/@keyframes e59-rise/);
 assert.match(css,/@keyframes e59-bar/);
 assert.match(css,/prefers-reduced-motion:reduce/);
 assert.match(css,/data-motion="off"/);
 assert.doesNotMatch(css,/\.sidebar\{/);
});
