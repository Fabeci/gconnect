import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[c]));
const summary={imports:4,integrated:82,anomalies:3,establishments:2};
const response={
  summary,
  institutions:[{id:11,name:'Campus <script>alert(1)</script>'}],
  count:1,pages:1,page:1,
  results:[{
    id:13,type:'promotions',file_name:'promo-2026.csv',
    total:27,integrated:25,anomalies:2,institution:'Campus Dakar',
    created_at:'2026-11-07T13:00:00Z',
  }],
};
function factory(api,visible=()=>true){
  const context={window:{},document:{createElement:()=>{throw Error('No DOM in text-only test')}},
    Date,Intl,Object,Number,String,Promise,setTimeout,clearTimeout};
  runInNewContext(read('imports-e58.js'),context);
  let renders=0;
  const controller=context.window.GConnectImportsE58({
    api,safe:escape,render:()=>{renders++},isVisible:visible,
  });
  return {controller,renders:()=>renders};
}
test('E58 is isolated to existing Superadmin Imports and never changes invoices or invitations',()=>{
  const api=read('etablissement-api.js');
  const shell=read('admin-connected-e19.html');
  assert.match(api,/const adminImportHistory = params/);
  assert.match(api,/privilegedRequest\('\/backoffice\/imports-v2\/\?'/);
  assert.match(api,/const adminImportPreview = payload/);
  assert.match(api,/const adminImportExecute = payload/);
  assert.match(shell,/let importsE58=null/);
  assert.match(shell,/pages\.imports=importsE58\.page/);
  assert.match(shell,/view==='imports'\)importsE58\?\.ensure/);
  assert.match(shell,/imports-e58.css\?v=e58-studio-2/);
  assert.match(shell,/imports-e58.js\?v=e58-studio-1/);
  assert.match(shell,/pages\.contenus=contentsE57\.page/);
  assert.match(shell,/pages\.invitations=invitationsE54\.page/);
});
test('E58 displays real jobs, no invented metrics, with escaped filenames',async()=>{
  const {controller}=factory({
    adminImportHistory:async()=>({...response,results:[
      {...response.results[0],file_name:'<img src=x onerror=alert(1)>.csv'},
    ]}),
  });
  let html=controller.page();
  assert.match(html,/e58-hero/);
  assert.match(html,/e58-metric/);
  assert.match(html,/>—<\/strong>/);
  await controller.load();
  html=controller.page();
  assert.match(html,/Imports <em>&<\/em> opérations groupées/);
  assert.match(html,/>82<\/strong>/);
  assert.match(html,/>3<\/strong>/);
  assert.match(html,/&lt;img src=x onerror=alert\(1\)&gt;\.csv/);
  assert.doesNotMatch(html,/<img src=x onerror=/);
  assert.match(html,/Campus Dakar/);
  assert.match(html,/Aucun compte créé automatiquement/);
  assert.match(html,/data-e58-file/);
  assert.match(html,/data-e58-action="template"/);
});
test('E58 separates executable catalogues from preview-only user accounts',async()=>{
  const {controller}=factory({adminImportHistory:async()=>response});
  await controller.load();
  controller.action({dataset:{e58Type:'students'}});
  let html=controller.page();
  assert.match(html,/Désactivée pour les comptes/);
  assert.match(html,/data-e58-type="students" aria-pressed="true"/);
  controller.action({dataset:{e58Type:'promotions'}});
  html=controller.page();
  assert.match(html,/Après confirmation/);
  assert.match(html,/data-e58-school/);
  assert.equal(controller.peek().kind,'promotions');
});
test('E58 reports failure without fake zeros and keeps retry control',async()=>{
  const {controller}=factory({adminImportHistory:async()=>{throw Error('Base indisponible')}});
  await controller.load();
  const html=controller.page();
  assert.match(html,/Base indisponible/);
  assert.match(html,/>—<\/strong>/);
  assert.match(html,/data-e58-action="refresh"/);
  assert.doesNotMatch(html,/e58-metric[^]*?<strong>0<\/strong>/);
});
test('E58 CSS has its own Premium identity, motion and reduced-motion accessibility',()=>{
  const css=read('imports-e58.css');
  assert.match(css,/\.e58-hero\{/);
  assert.match(css,/background:transparent;border:0;border-radius:0;box-shadow:none/);
  assert.match(css,/@keyframes e58-card-in/);
  assert.match(css,/@keyframes e58-float/);
  assert.match(css,/@keyframes e58-modal-show/);
  assert.match(css,/prefers-reduced-motion:reduce/);
  assert.match(css,/data-motion="off"/);
  assert.doesNotMatch(css,/\.sidebar\{/);
  assert.doesNotMatch(css,/html\[data-module="facturation"\]/);
});
