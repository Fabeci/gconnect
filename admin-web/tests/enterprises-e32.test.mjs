import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const html=read('admin-connected-e19.html');
const api=read('etablissement-api.js');
const src=read('enterprises-e32.js');
const css=read('enterprises-e32.css');
const inline=html.match(/<script>([\s\S]*?)<\/script>/)?.[1]||'';
const escape=value=>String(value??'').replace(/[&<>"']/g,ch=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}[ch]));

function mount(response={summary:{total:2,active:1,subscribed:1,expiring_30_days:1},
 count:1,page:1,pages:1,
 results:[{id:12,company_name:'Acme <Business>',sector:'Technologie',logo_url:null,
 contact:{email:'example@test.tld',location:'Dakar'},is_active:true,is_banned:false,
 offers_count:4,open_offers:2,applications_count:9,
 subscription:{name:'Offre Publications',capacity:20,included:18,extra:2,used:7,remaining:13,
 expires_at:'2026-12-01',unit:'publications'}}]}){
  const ctx={window:{},URL,location:{href:'http://127.0.0.1:5173/'},
    setTimeout,clearTimeout,document:{getElementById:()=>null}};
  vm.runInNewContext(src,ctx);
  const calls=[],navigations=[];let renders=0;
  const mod=ctx.window.GConnectEnterprisesE32({
    api:{enterprisePartnerDirectory:async params=>{calls.push({...params});return response}},
    safe:escape,icon:()=>'<svg/>',go:route=>navigations.push(route),
    render:()=>{renders++},isVisible:()=>true
  });
  return {mod,calls,navigations,getRenders:()=>renders};
}

test('E32 code is syntactically valid and wired only into Superadmin module',()=>{
  assert.doesNotThrow(()=>new vm.Script(src));
  assert.doesNotThrow(()=>new vm.Script(inline));
  assert.match(html,/href="\/enterprises-e32\.css\?v=e32-business-1"/);
  assert.match(html,/src="\/enterprises-e32\.js\?v=e32-business-1"/);
  assert.match(inline,/if\(isPlatformAdmin\)\{\s*academicE31=/);
  assert.match(inline,/corporateE32=window.GConnectEnterprisesE32/);
  assert.match(inline,/pages\.entreprises=\(\)=>corporateE32\.page\(\)/);
  assert.match(inline,/if\(isPlatformAdmin&&view==='entreprises'\)corporateE32\?\.ensure\(\)/);
  assert.match(api,/enterprisePartnerDirectory = params =>/);
  assert.match(api,/commercialRequest\('\/backoffice\/enterprises\/\?'\+query\.toString\(\),'GET',null,true\)/);
});

test('E32 company cards render genuine backend data, business credits and safe HTML',async()=>{
  const {mod,calls,getRenders}=mount();
  assert.match(mod.page(),/Chargement du portefeuille/);
  assert.doesNotMatch(mod.page(),/NaN/);
  mod.ensure();
  await new Promise(setImmediate);
  assert.equal(calls.length,1);
  assert.equal(getRenders(),1);
  const page=mod.page();
  assert.match(page,/Acme &lt;Business&gt;/);
  assert.doesNotMatch(page,/Acme <Business>/);
  assert.match(page,/Candidatures/);
  assert.match(page,/2/);
  assert.match(page,/9/);
  assert.match(page,/7 \/ 20/);
  assert.match(page,/13 restant\(s\)/);
  assert.match(page,/Offre Publications/);
  assert.match(page,/CRÉDITS DE PUBLICATION/);
  assert.doesNotMatch(src,/Math\.random\(|fakeEnterprise|seedCompany/);
});

test('E32 filters are sent to backend, page is reset, and actions navigate safely',async()=>{
  const {mod,calls,navigations}=mount();
  mod.onFilter({dataset:{e32Filter:'status'},value:'inactive'});
  await new Promise(setImmediate);
  assert.equal(calls[0].status,'inactive');
  mod.onFilter({dataset:{e32Filter:'billing'},value:'active'});
  await new Promise(setImmediate);
  assert.equal(calls[1].billing,'active');
  assert.equal(calls[1].page,1);
  mod.action({dataset:{e32Action:'reset'}});
  await new Promise(setImmediate);
  assert.equal(calls[2].status,'all');
  assert.equal(calls[2].billing,'all');
  mod.action({dataset:{e32Action:'invite'}});
  mod.action({dataset:{e32Action:'subscriptions'}});
  assert.deepEqual(navigations,['invitations','abonnements']);
});

test('E32 handles empty and invalid API responses without fabricating companies',async()=>{
  const {mod}=mount({summary:{total:0,active:0,subscribed:0,expiring_30_days:0},
    results:[],count:0,page:1,pages:1});
  mod.ensure();
  await new Promise(setImmediate);
  assert.match(mod.page(),/Aucune entreprise n’est enregistrée/);
  const failure=mount({data:[]});
  failure.mod.ensure();
  await new Promise(setImmediate);
  assert.match(failure.mod.page(),/Le portefeuille n’a pas pu être chargé/);
});

test('E32 custom business design responsive, accessible, differentiated from campus',()=>{
  assert.match(css,/\.e32-hero/);
  assert.match(css,/\.e32-network-art/);
  assert.match(css,/\.e32-company/);
  assert.match(css,/\.e32-dialog::backdrop/);
  assert.match(css,/@media\(max-width:720px\)/);
  assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);
  assert.match(src,/aria-label="Rechercher une entreprise"/);
  assert.match(src,/aria-busy=/);
  assert.match(src,/dialog\.showModal\(\)/);
  assert.match(src,/data-e32-action="detail"/);
});
