import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const src=read('finance-e36.js');
const api=read('etablissement-api.js');
const html=read('admin-connected-e19.html');
const login=read('admin-login-e19.html');
const css=read('finance-e36.css');
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}[c]));
const payload={
  summary:{paid:1,pending:1,failed:0,canceled:0,total:2,
    verified_total_xof:'25000.00',unverified_paid:0,invoicing_available:false},
  results:[
    {id:1,transaction_id:'bbbbbbbb-1111-2222-3333-444444444444',
      organisation_type:'enterprise',organisation_name:'Société <X>',
      offer_name:'Offre de test',capacity:20,quota_unit:'publications',term_months:1,
      amount:'25000.00',currency:'XOF',status:'paid',is_verified:true,provider:'cinetpay',
      created_at:'2026-11-06T10:00:00Z',verified_at:'2026-11-06T11:00:00Z',subscription_id:99},
    {id:2,transaction_id:'cccccccc-1111-2222-3333-444444444444',
      organisation_type:'institution',organisation_name:'Campus E36',
      offer_name:'Offre Campus',capacity:100,quota_unit:'accounts',term_months:6,
      amount:'60000.00',currency:'XOF',status:'pending',is_verified:false,provider:'cinetpay',
      created_at:'2026-11-06T12:00:00Z',verified_at:null,subscription_id:null},
  ],
  count:2,page:1,pages:1
};
function mount(response=payload,error=null){
  const calls=[],dialog={opened:false,closed:false,showModal(){this.opened=true},close(){this.closed=true}};
  const body={innerHTML:''}, searchInput={value:'',focus(){},setSelectionRange(){}};
  const nodes={'e36-dialog':dialog,'e36-dialog-body':body,'e36-search':searchInput};
  const ctx={window:{},document:{getElementById:k=>nodes[k]||null},setTimeout,clearTimeout,
    Intl,Date,Number,Object,console};
  vm.runInNewContext(src,ctx);
  let renders=0;
  const module=ctx.window.GConnectFinanceE36({
    api:{financeRegister:async args=>{calls.push({...args});if(error)throw Error(error);return response;}},
    safe:escape,icon:()=>'<svg></svg>',render:()=>{renders++},isVisible:()=>true,
  });
  return {module,calls,dialog,body,renders:()=>renders};
}
const tick=()=>new Promise(setImmediate);
test('E36 script and secure API are wired, independently from subscriptions',()=>{
  assert.doesNotThrow(()=>new vm.Script(src));
  assert.match(api,/const financeRegister = params =>/);
  assert.match(api,/\/backoffice\/finance\/register\//);
  assert.match(api,/true\);\n  \};\n  const adminUserSecurityAction|adminUserSecurityAction/);
  assert.ok(html.includes('finance-e36.js?v=e38-invoices-1'));
  assert.ok(html.includes('finance-e36.css?v=e37-motion-20261106'));
  assert.ok(login.includes('etablissement-api.js?v=e38-invoices-1'));
  assert.match(html,/pages\.facturation=\(\)=>financeE36\.page\(\)/);
  assert.match(html,/if\(isPlatformAdmin&&view==='facturation'\)financeE36\?\.ensure\(\)/);
  assert.match(css,/@media\(max-width:600px\)/);
});

test('E36 uses only server-provided values, does not fabricate invoices',async()=>{
  const m=mount();
  m.module.ensure();await tick();
  const out=m.module.page();
  assert.match(out,/Société &lt;X&gt;/);
  assert.doesNotMatch(out,/Société <X>/);
  assert.match(out,/25[\s\u00a0\u202f]000 XOF/);
  assert.match(out,/Facturation officielle sur paiement confirmé/);
  assert.match(out,/Commandes, pas des créances/);
  assert.match(out,/Paiements vérifiés/);
  assert.match(out,/Campus E36/);
  assert.equal(m.calls.length,1);
});

test('E36 details accurately distinguish a verified receipt from an unconfirmed order',async()=>{
  const m=mount();m.module.ensure();await tick();
  m.module.action({dataset:{e36Action:'details',e36Id:'2'}});
  assert.equal(m.dialog.opened,true);
  assert.match(m.body.innerHTML,/Non confirmée/);
  assert.match(m.body.innerHTML,/Aucun contrat confirmé/);
  assert.match(m.body.innerHTML,/n[’']est pas une facture|et non une facture/);
  m.module.action({dataset:{e36Action:'close'}});
  assert.equal(m.dialog.closed,true);
  m.module.action({dataset:{e36Action:'details',e36Id:'1'}});
  assert.match(m.body.innerHTML,/#99/);
  assert.match(m.body.innerHTML,/Vérifié/);
});

test('E36 filter and pagination query server rather than mutating payment state',async()=>{
  const m=mount();m.module.ensure();await tick();
  m.module.onFilter({value:'paid'});await tick();
  assert.equal(m.calls.length,2);
  assert.equal(m.calls[1].status,'paid');
  m.module.onFilter({value:'malformed'});await tick();
  assert.equal(m.calls.length,2);
  m.module.action({dataset:{e36Action:'refresh'}});await tick();
  assert.equal(m.calls.length,3);
});

test('E36 empty state does not show fabricated financial figures',async()=>{
  const m=mount({...payload,results:[],count:0,summary:{
    ...payload.summary,paid:0,pending:0,verified_total_xof:'0.00',
  }});
  m.module.ensure();await tick();
  assert.match(m.module.page(),/Aucune opération ne correspond/);
});
test('E36 network failure is explicit and never creates a payment',async()=>{
  const m=mount(null,'Backend momentanément indisponible');
  m.module.ensure();await tick();
  const out=m.module.page();
  assert.match(out,/Backend momentanément indisponible/);
  assert.match(out,/Réessayer/);
});


test('E37 finance hero inherits shared brand with unique floating illustration',()=>{
  const m=mount();
  const out=m.module.page();
  assert.match(out,/class="e36-hero-copy"/);
  assert.match(out,/class="e36-hero-art" aria-hidden="true"/);
  assert.match(out,/e36-art-ring--inner/);
  assert.match(out,/e36-art-node--paid/);
  assert.match(out,/e36-hero-assurance/);
  assert.doesNotMatch(out,/e36-hero-seal/);
  assert.match(css,/@keyframes e37-node-float/);
  assert.match(css,/@keyframes e37-core-float/);
  assert.match(css,/@keyframes e37-modal-enter/);
  assert.match(css,/prefers-reduced-motion:reduce/);
  assert.match(css,/data-motion="off"/);
});
