import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const src=read('invoices-e38.js');
const css=read('invoices-e38.css');
const finance=read('finance-e36.js');
const html=read('admin-connected-e19.html');
const login=read('admin-login-e19.html');
const api=read('etablissement-api.js');
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[c]));
const issuer={ready:true,legal_name:'G-Connect',registration_number:'REG-01',tax_identifier:'TAX-01',
  address:'Dakar',country_code:'SN',email:'finance@example.test',invoice_prefix:'GC',
  tax_label:'TVA',tax_rate:'18.00',tax_treatment:'included'};
const invoice={id:10,number:'GC-2026-000001',organisation_name:'Établissement <Test>',
  offer_name:'Forfait réel',amount_total:'15000.00',currency:'XOF',issued_at:'2026-11-06T10:00:00Z'};
function harness(admin=true){
  const calls=[],dialog={showModal(){this.open=true},close(){this.open=false},
    querySelector(){return {focus(){}}}},box={innerHTML:''};
  const docs={'e38-modal':dialog,'e38-modal-body':box};
  const dom={getElementById:id=>docs[id]};
  const ctx={window:{},document:dom,Intl,Date,Number,Object,FormData,console};
  vm.runInNewContext(src,ctx);
  let renders=0;
  const api={
    invoiceIssuer:async()=>{calls.push('issuer');return issuer},
    invoiceHistory:async()=>{calls.push('history');return {results:[invoice],page:1,pages:1,count:1}},
    myInvoices:async()=>{calls.push('my');return {results:[invoice],page:1,pages:1,count:1}},
    downloadInvoicePdf:async(id,number,mode)=>{calls.push(['pdf',id,number,mode]);return true},
    invoiceSaveIssuer:async fields=>{calls.push(['save',fields]);return issuer},
    invoiceIssue:async fields=>{calls.push(['issue',fields]);return {created:true,invoice}},
  };
  const row={id:7,status:'paid',is_verified:true,invoice_id:null,
    transaction_id:'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',amount:'15000.00',
    currency:'XOF',offer_name:'Forfait réel',organisation_name:'Établissement <Test>'};
  const mod=ctx.window.GConnectInvoicingE38({
    api,safe,render:()=>{renders++},isVisible:()=>true,
    admin,verifiedRows:()=>[row],refreshPayments:()=>calls.push('refresh-payments'),
  });
  return {mod,api,calls,dialog,box,row,renders:()=>renders};
}
const tick=()=>new Promise(setImmediate);
test('E38 scripts are parseable and integrated with all 3 professional portals',()=>{
  assert.doesNotThrow(()=>new vm.Script(src));
  assert.match(html,/invoices-e38\.js\?v=e38-invoices-1/);
  assert.match(html,/invoices-e38\.css\?v=e38-invoices-1/);
  assert.match(html,/pages\.subscription=\(\)=>billingE22\.clientPage\(\)\+clientInvoiceE38\.section\(\)/);
  assert.match(html,/invoicing:invoiceE38/);
  assert.match(html,/data-e38-action/);
  assert.match(login,/etablissement-api\.js\?v=e38-invoices-1/);
  assert.match(finance,/invoicing\?\.section\(\)/);
  assert.match(finance,/invoicing\?\.actionButton\(item\)/);
  assert.match(api,/const invoiceSaveIssuer =/);
  assert.match(api,/const downloadInvoicePdf = async/);
  assert.match(api,/headers:\{'Authorization':'WebToken '\+token/);
  assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);
  assert.match(css,/@keyframes e38-modal/);
});
test('E38 loads real invoices and HTML-escapes names',async()=>{
  const h=harness();
  h.mod.ensure();await tick();
  assert.deepEqual(h.calls,['issuer','history']);
  assert.match(h.mod.section(),/GC-2026-000001/);
  assert.match(h.mod.section(),/Établissement &lt;Test&gt;/);
  assert.doesNotMatch(h.mod.section(),/Établissement <Test>/);
  assert.match(h.mod.section(),/PDF/);
  assert.equal(h.renders(),1);
});
test('E38 protects issue button from unverified transactions and clients',()=>{
  const h=harness();
  assert.equal(h.mod.actionButton({...h.row,is_verified:false}),'');
  assert.match(h.mod.actionButton(h.row),/Émettre facture/);
  assert.match(h.mod.actionButton({...h.row,invoice_id:10,invoice_number:invoice.number}),/PDF facture/);
  assert.equal(harness(false).mod.actionButton(h.row),'');
});
test('E38 client view only loads tenant-scope history and downloads from role-scoped API',async()=>{
  const h=harness(false);h.mod.ensure();await tick();
  assert.deepEqual(h.calls,['my']);
  assert.match(h.mod.section(),/Mes factures/);
  assert.doesNotMatch(h.mod.section(),/Configurer l’émetteur/);
  await h.mod.action({dataset:{e38Action:'pdf',e38Id:'10',e38Number:invoice.number}});
  assert.deepEqual(h.calls.at(-1),['pdf',10,invoice.number,false]);
});
test('E38 legal issuer modal is the same premium dialog pattern',()=>{
  const h=harness();
  h.mod.action({dataset:{e38Action:'issuer-open'}});
  assert.equal(h.dialog.open,true);
  assert.match(h.box.innerHTML,/data-e38-form="issuer"/);
  assert.match(h.box.innerHTML,/Régime fiscal/);
  assert.match(h.box.innerHTML,/immatriculation/);
  assert.match(h.box.innerHTML,/Raison sociale légale/);
});
test('E38 issue modal includes payment proof and requires buyer address',async()=>{
  const h=harness();h.mod.ensure();await tick();
  h.mod.action({dataset:{e38Action:'issue-open',e38Id:'7'}});
  assert.match(h.box.innerHTML,/data-e38-form="issue"/);
  assert.match(h.box.innerHTML,/Paiement vérifié/);
  assert.match(h.box.innerHTML,/buyer_address/);
  assert.match(h.box.innerHTML,/Émettre et numéroter/);
});
