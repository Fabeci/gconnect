import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const read = name => readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const src=read('users-e34.js');
const api=read('etablissement-api.js');
const html=read('admin-connected-e19.html');
const login=read('admin-login-e19.html');
const css=read('users-e34.css');
const escape = value => String(value??'').replace(/[&<>"']/g,c=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}[c]));
const usersResponse={
  summary:{total:1,active:1,students:1,alumni:0,enterprises:0,institution_admins:0,superadmins:0,pending:0,banned:0},
  results:[{id:8,username:'e35',display_name:'Awa <Profile>',email:'user@example.test',
    role:'student',is_active:true,is_banned:false,association:'Dakar',
    joined_at:'2026-10-10T11:00:00Z',last_login_at:null}],count:1,page:1,pages:1
};
const securityResponse={
  id:8,role:'student',is_active:true,is_banned:false,live_web_sessions:2,
  banned_reason:'',banned_at:null,eligible_actions:['ban','revoke_sessions'],
  history:[{action:'sessions_revoked',label:'Sessions révoquées',
    created_at:'2026-11-05T20:01:00Z',actor:'Admin <A>',
    reason:'Ancienne session <unsafe>'}]
};
function mount(security=securityResponse, actionError=null, missingClient=false){
  const profile={innerHTML:''},panel={innerHTML:'',querySelector:()=>({focus(){}})};
  const reason={value:'',focus(){}},validation={textContent:''};
  const dialog={opened:false,closed:false,querySelector:()=>profile,
    showModal(){this.opened=true;},close(){this.closed=true;}};
  const nodes={'e34-profile-dialog':dialog,'e35-security-panel':panel,
    'e35-reason':reason,'e35-validation':validation};
  const document={getElementById:key=>nodes[key]||null};
  const calls={details:[],actions:[],list:0,notices:[]};
  const ctx={window:{},document,Date,setTimeout,clearTimeout,console};
  vm.runInNewContext(src,ctx);
  const users=ctx.window.GConnectUsersE34({
    api:{
      adminUserDirectory:async()=>{calls.list++;return usersResponse;},
      adminUserSecurity:missingClient?undefined:async id=>{calls.details.push(id);return security;},
      adminUserSecurityAction:async(id,action,text)=>{
        calls.actions.push({id,action,reason:text});
        if(actionError)throw new Error(actionError);
        return {user_id:id,action,security};
      },
    },safe:escape,icon:()=>'<svg></svg>',
    render:()=>{},isVisible:()=>true,notify:msg=>calls.notices.push(msg),
  });
  return {users,profile,panel,dialog,reason,validation,calls};
}
const tick=()=>new Promise(setImmediate);

test('E35 API uses same protected WebToken mechanism for reads and writes',()=>{
  assert.match(api,/const adminUserSecurity = id =>/);
  assert.match(api,/const adminUserSecurityAction = \(id, action, reason\) =>/);
  assert.match(api,/\/backoffice\/user-directory\/.*security\//);
  assert.match(api,/\{action, reason\}, true/);
  assert.match(html,/peopleE34=window.GConnectUsersE34/);
  assert.match(html,/api:accountApi,safe,icon,notify,go:goto/);
  assert.doesNotThrow(()=>new vm.Script(src));
});

test('E35 cache versions synchronize parent API and iframe user module',()=>{
  assert.ok(login.includes('etablissement-api.js?v=e38-invoices-1'));
  assert.ok(html.includes('users-e34.js?v=e35-security-sync-20261106'));
  assert.match(api,/adminUserSecurity,/);
  assert.match(api,/adminUserSecurityAction,/);
});

test('E35 never leaves an endless loader when the parent still has an old API',async()=>{
  const m=mount(securityResponse,null,true);
  m.users.ensure();await tick();
  m.users.action({dataset:{e34Action:'detail',e34Id:'8'}});
  assert.equal(m.dialog.opened,true);
  assert.match(m.panel.innerHTML,/Le module de sécurité n’a pas été chargé/);
  assert.ok(m.panel.innerHTML.includes('Ctrl + Maj + R'));
  assert.doesNotMatch(m.panel.innerHTML,/Vérification des accès et de l’historique/);
  assert.equal(m.calls.actions.length,0);
});

test('E35 detail shows actual active session count and safely escaped audit reasons',async()=>{
  const m=mount();
  m.users.ensure();await tick();
  m.users.action({dataset:{e34Action:'detail',e34Id:'8'}});
  assert.equal(m.dialog.opened,true);
  await tick();
  assert.equal(m.calls.details[0],8);
  assert.match(m.profile.innerHTML,/Awa &lt;Profile&gt;/);
  assert.match(m.panel.innerHTML,/Sessions web actives/);
  assert.match(m.panel.innerHTML,/>2<\/strong>/);
  assert.match(m.panel.innerHTML,/Admin &lt;A&gt;/);
  assert.match(m.panel.innerHTML,/Ancienne session &lt;unsafe&gt;/);
  assert.doesNotMatch(m.panel.innerHTML,/Ancienne session <unsafe>/);
  assert.match(m.panel.innerHTML,/Bloquer ce compte/);
  assert.match(m.panel.innerHTML,/Déconnecter les appareils/);
});

test('E35 requires a documented reason before requesting ban',async()=>{
  const m=mount();
  m.users.ensure();await tick();
  m.users.action({dataset:{e34Action:'detail',e34Id:'8'}});await tick();
  m.users.action({dataset:{e34Action:'security-prompt',e34Security:'ban'}});
  assert.match(m.panel.innerHTML,/Motif de l’intervention/);
  assert.match(m.panel.innerHTML,/intervention sensible/i);
  const btn={disabled:false};
  m.users.action({dataset:{e34Action:'security-save'},disabled:false});
  await tick();
  assert.equal(m.calls.actions.length,0);
  assert.match(m.validation.textContent,/10 à 255 caractères/);
  m.reason.value='Fraude détectée et revue documentée';
  m.users.action({dataset:{e34Action:'security-save'},disabled:false});
  await tick();await tick();
  assert.deepEqual(m.calls.actions[0],{id:8,action:'ban',reason:'Fraude détectée et revue documentée'});
  assert.equal(m.dialog.closed,true);
  assert.equal(m.calls.list,2);
  assert.match(m.calls.notices[0],/Compte bloqué/);
});

test('E35 cancellation does not mutate and protected Superadmin has no action',async()=>{
  const m=mount();
  m.users.ensure();await tick();
  m.users.action({dataset:{e34Action:'detail',e34Id:'8'}});await tick();
  m.users.action({dataset:{e34Action:'security-prompt',e34Security:'revoke_sessions'}});
  assert.match(m.panel.innerHTML,/Déconnecter les appareils/);
  m.users.action({dataset:{e34Action:'security-cancel'}});
  assert.match(m.panel.innerHTML,/Sessions web actives/);
  assert.equal(m.calls.actions.length,0);
  const protectedMount=mount({...securityResponse,eligible_actions:[]});
  protectedMount.users.ensure();await tick();
  protectedMount.users.action({dataset:{e34Action:'detail',e34Id:'8'}});await tick();
  assert.match(protectedMount.panel.innerHTML,/Compte Superadmin protégé/);
  protectedMount.users.action({dataset:{e34Action:'security-prompt',e34Security:'ban'}});
  assert.equal(protectedMount.calls.actions.length,0);
  assert.doesNotMatch(protectedMount.panel.innerHTML,/Motif de l’intervention/);
});

test('E35 failed request keeps the modal open and reports error',async()=>{
  const m=mount(securityResponse, 'Accès temporairement refusé par le serveur');
  m.users.ensure();await tick();
  m.users.action({dataset:{e34Action:'detail',e34Id:'8'}});await tick();
  m.users.action({dataset:{e34Action:'security-prompt',e34Security:'ban'}});
  m.reason.value='Justification valable pour le test';
  m.users.action({dataset:{e34Action:'security-save'},disabled:false});
  await tick();await tick();
  assert.equal(m.dialog.closed,false);
  assert.equal(m.calls.actions.length,1);
  assert.match(m.validation.textContent,/Accès temporairement refusé par le serveur/);
  assert.equal(m.calls.list,1);
});

test('E35 modals preserve existing visual identity and responsive use',()=>{
  assert.match(css,/\.e35-security-panel/);
  assert.match(css,/\.e35-confirm/);
  assert.match(css,/\.e35-history/);
  assert.match(css,/\.e35-btn--danger/);
  assert.match(css,/@media\(max-width:650px\)/);
  assert.match(src,/maxlength="255" minlength="10"/);
  assert.match(src,/data-e34-action="security-save"/);
});
