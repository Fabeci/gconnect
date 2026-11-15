import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const html=read('admin-connected-e19.html');
const api=read('etablissement-api.js');
const src=read('users-e34.js');
const css=read('users-e34.css');
const inline=html.match(/<script>([\s\S]*?)<\/script>/)?.[1]||'';
const escape=value=>String(value??'').replace(/[&<>"']/g,ch=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}[ch]));
const fixture={
  summary:{total:5,active:3,students:1,alumni:1,enterprises:1,
    institution_admins:1,superadmins:1,pending:1,banned:1,joined_30_days:2},
  count:2,page:1,pages:1,results:[
    {id:3,display_name:'Awa <Test>',username:'awa',email:'awa@example.test',
      role:'student',role_label:'Étudiant',is_active:true,is_banned:false,
      association:'Campus de Dakar',location:'Dakar',joined_at:'2026-11-03T11:12:00Z',last_login_at:null},
    {id:4,display_name:'Superviseur B',username:'superb',email:'super@example.test',
      role:'superAdmin',role_label:'Super Admin',is_active:true,is_banned:false,
      association:'',location:'',joined_at:'2026-11-01T11:12:00Z',last_login_at:'2026-11-04T11:12:00Z'},
  ]
};
function mount(result=fixture){
  const calls=[],modal={innerHTML:''},dialog={
    opened:false,closed:false,querySelector:()=>modal,
    showModal(){this.opened=true},close(){this.closed=true},
  };
  const ctx={window:{},setTimeout,clearTimeout,Date,
    document:{getElementById:id=>id==='e34-profile-dialog'?dialog:null}};
  vm.runInNewContext(src,ctx);
  let renders=0;
  const users=ctx.window.GConnectUsersE34({
    api:{adminUserDirectory:async params=>{calls.push({...params});return result}},
    safe:escape,icon:()=>'<svg></svg>',go:()=>{},render:()=>{renders++},isVisible:()=>true,
  });
  return {users,calls,dialog,modal,renderCount:()=>renders};
}

test('E34 removes Recruteurs from Superadmin navigation and uses real five backend roles',()=>{
  assert.doesNotThrow(()=>new vm.Script(inline));
  assert.match(inline,/\['etablissements','Établissements','school'\],\['entreprises','Entreprises','building'\],\['utilisateurs','Utilisateurs','users'\]/);
  assert.doesNotMatch(inline,/\['recruteurs','Recruteurs','briefcase'\]/);
  assert.doesNotMatch(inline,/pages\.recruteurs=/);
  assert.match(src,/student: 'Étudiant'/);
  assert.match(src,/alumni: 'Alumni'/);
  assert.match(src,/enterprise: 'Entreprise'/);
  assert.match(src,/etablissement: 'Administration établissement'/);
  assert.match(src,/superAdmin: 'Superadmin'/);
  assert.doesNotMatch(src,/recruteur/i);
});

test('E34 loads only for Superadmin through WebToken-protected endpoint',()=>{
  assert.match(html,/href="\/users-e34\.css\?v=e34-community-1"/);
  assert.match(html,/src="\/users-e34\.js\?v=e35-security-sync-20261106"/);
  assert.match(inline,/if\(isPlatformAdmin\)\{\s*academicE31=/);
  assert.match(inline,/peopleE34=window.GConnectUsersE34/);
  assert.match(inline,/pages\.utilisateurs=\(\)=>peopleE34\.page\(\)/);
  assert.match(inline,/if\(isPlatformAdmin&&view==='utilisateurs'\)peopleE34\?\.ensure\(\)/);
  assert.match(api,/adminUserDirectory = params =>/);
  assert.match(api,/commercialRequest\('\/backoffice\/user-directory\/\?'\+query\.toString\(\),'GET',null,true\)/);
  assert.doesNotThrow(()=>new vm.Script(src));
});

test('E34 shows real counts, escaped identity and role breakdown, without mock data',async()=>{
  const {users,calls,renderCount}=mount();
  assert.match(users.page(),/Chargement des comptes depuis le backend/);
  users.ensure();
  await new Promise(setImmediate);
  assert.equal(calls.length,1);
  assert.equal(renderCount(),1);
  const html=users.page();
  assert.match(html,/5/);
  assert.match(html,/Awa &lt;Test&gt;/);
  assert.doesNotMatch(html,/Awa <Test>/);
  assert.match(html,/Campus de Dakar/);
  assert.match(html,/Superviseur B/);
  assert.match(html,/À examiner/);
  assert.match(html,/En attente/);
  assert.match(html,/Bloqué/);
  assert.doesNotMatch(src,/Math\.random\(|userSeed|demoPeople/);
});

test('E34 role and status filters are server-backed; reset clears both',async()=>{
  const {users,calls}=mount();
  users.onFilter({dataset:{e34Filter:'role'},value:'student'});
  await new Promise(setImmediate);
  assert.equal(calls[0].role,'student');
  assert.equal(calls[0].page,1);
  users.onFilter({dataset:{e34Filter:'status'},value:'pending'});
  await new Promise(setImmediate);
  assert.equal(calls[1].status,'pending');
  users.action({dataset:{e34Action:'reset'}});
  await new Promise(setImmediate);
  assert.equal(calls[2].role,'all');
  assert.equal(calls[2].status,'all');
  assert.equal(calls[2].search,'');
  users.onFilter({dataset:{e34Filter:'role'},value:'recruteur'});
  assert.equal(calls.length,3);
});

test('E34 renders confidential profile safely in read-only modal',async()=>{
  const {users,modal,dialog}=mount();
  users.ensure();
  await new Promise(setImmediate);
  users.action({dataset:{e34Action:'detail',e34Id:'3'}});
  assert.equal(dialog.opened,true);
  assert.match(modal.innerHTML,/Awa &lt;Test&gt;/);
  assert.doesNotMatch(modal.innerHTML,/Awa <Test>/);
  assert.match(modal.innerHTML,/FICHE UTILISATEUR/);
  assert.match(modal.innerHTML,/Consultation uniquement/);
  assert.doesNotMatch(modal.innerHTML,/password|totp|secret/i);
  users.action({dataset:{e34Action:'close'}});
  assert.equal(dialog.closed,true);
});

test('E34 accessible responsive visual identity keeps art airy rather than hero banner',()=>{
  assert.match(css,/\.e34-identity-art/);
  assert.match(css,/\.e34-art-ring/);
  assert.match(css,/\.e34-hero\s*\{/);
  assert.doesNotMatch(css,/\.e34-hero\s*\{[^}]*background:linear-gradient/);
  assert.match(css,/@media\(max-width:620px\)/);
  assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);
  assert.match(src,/aria-label="Rechercher un utilisateur"/);
  assert.match(src,/aria-busy=/);
  assert.match(src,/id="e34-profile-dialog"/);
});

test('E34 handles actual zero state and bad API response without imaginary figures',async()=>{
  const empty=mount({summary:{total:0,active:0,students:0,alumni:0,enterprises:0,
    institution_admins:0,superadmins:0,pending:0,banned:0},results:[],count:0,page:1,pages:1});
  empty.users.ensure();
  await new Promise(setImmediate);
  assert.match(empty.users.page(),/Aucun utilisateur enregistré/);
  const invalid=mount({summary:{},data:[]});
  invalid.users.ensure();
  await new Promise(setImmediate);
  assert.match(invalid.users.page(),/Impossible de charger les profils/);
});
