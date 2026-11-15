import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../dist/institutions-e31.js',import.meta.url),'utf8');
const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function mount(){
  const context={window:{},URL,location:{href:'http://127.0.0.1:5173/'},setTimeout,clearTimeout};
  vm.runInNewContext(source,context);
  const calls=[];
  const actions=[];
  let refreshed=0;
  const fixture={
    summary:{total:3,active:2,inactive:1,subscribed:1,expiring_30_days:1},
    count:1,page:1,pages:1,
    results:[{
      id:12,name:'École <Horizon>',acronym:'EH',city:'Dakar',country:'Sénégal',
      description:'École partenaire',is_active:true,members_count:20,active_accounts:17,
      logo_url:null,created_at:'2026-11-01T10:00:00+00:00',
      subscription:{id:9,name:'Offre Campus',capacity:100,remaining:83,expires_at:'2026-12-01',status:'active'}
    }]
  };
  const client={
    institutionsDirectory:async params=>{
      calls.push({...params});
      return fixture;
    }
  };
  const module=context.window.GConnectInstitutionDirectoryE31({
    api:client,safe:escape,icon:()=>'<svg></svg>',notify:()=>{},
    go:route=>actions.push(route),render:()=>{refreshed+=1},isVisible:()=>true,
  });
  return {module,calls,actions,fixture,updates:()=>refreshed};
}

test('E31 render displays backend data and escapes HTML labels',async()=>{
  const {module,calls,updates}=mount();
  const initial=module.page();
  assert.match(initial,/Chargement des établissements/);
  assert.doesNotMatch(initial,/NaN/);
  module.ensure();
  await new Promise(setImmediate);
  assert.equal(calls.length,1);
  assert.equal(updates(),1);
  const page=module.page();
  assert.match(page,/3/);
  assert.match(page,/École &lt;Horizon&gt;/);
  assert.doesNotMatch(page,/École <Horizon>/);
  assert.match(page,/Offre Campus/);
  assert.match(page,/17 \/ 100/);
  assert.match(page,/83 places disponibles/);
  assert.match(page,/e31-school-row/);
});

test('E31 filters use API not local fabricated counts',async()=>{
  const {module,calls}=mount();
  module.onFilter({dataset:{e31Filter:'status'},value:'inactive'});
  await new Promise(setImmediate);
  assert.equal(calls[0].status,'inactive');
  assert.equal(calls[0].billing,'all');
  module.onFilter({dataset:{e31Filter:'billing'},value:'active'});
  await new Promise(setImmediate);
  assert.equal(calls[1].billing,'active');
  assert.equal(calls[1].page,1);
  module.action({dataset:{e31Action:'reset'}});
  await new Promise(setImmediate);
  assert.equal(calls[2].status,'all');
  assert.equal(calls[2].billing,'all');
});

test('E31 actions preserve invitation and subscription route semantics',()=>{
  const {module,actions}=mount();
  module.action({dataset:{e31Action:'invite'}});
  assert.deepEqual(actions,['invitations']);
});
