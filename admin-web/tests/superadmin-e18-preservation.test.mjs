import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Script} from 'node:vm';
const read=(file)=>readFileSync(new URL('../'+file, import.meta.url),'utf8');
const login=read('dist/superadmin-login.html');
const connected=read('dist/superadmin-connected-e18.html');
const bridge=read('dist/superadmin-approved-e18.js');
const original=read('dist/superadmin-preview.html');
const script=connected.match(/<script>([\s\S]*?)<\/script>/)?.[1]||'';
test('E16 login remains canonical; E18 approved view loads after MFA only',()=>{
 assert.match(login,/auth-admin\.css/);
 assert.match(login,/superadmin-approved-e18\.js/);
 assert.doesNotMatch(login,/<script[^>]+superadmin-live-e17\.js/);
 assert.match(read('dist/auth.js'),/profile\?\.role==='superAdmin' && api\.isConnected\(\)/);
});
test('E18 reuses exact approved sidebar, topbar and style cascade',()=>{
 for(const marker of ['Pilotage du réseau','Accès et revenus','Contrôle et opérations','superadmin-premium.css','admin-rounding-e13.css','superadmin-establishment-theme.css']){
  assert.ok(original.includes(marker));
  assert.ok(connected.includes(marker));
 }
 assert.match(connected,/hero-network/);
});
test('connected view rejects direct unauthenticated entry',()=>{
 assert.match(script,/window\.parent===window/);
 assert.match(script,/GConnectEstablishmentApi\?\.isConnected/);
 assert.match(bridge,/api\?\.isConnected\(\)/);
 assert.match(bridge,/event\.source !== frame\.contentWindow/);
 assert.match(bridge,/event\.origin !== location\.origin/);
 assert.doesNotMatch(bridge,/localStorage|sessionStorage/);
});
test('real invitation API, guarded and no impersonated stats',()=>{
 for(const marker of ['liveApi.listInvitations()','liveApi.sendInvitation(email,institution)','liveApi.revokeInvitation(id)']){
  assert.ok(connected.includes(marker));
 }
 assert.match(connected,/Établissements actifs','—'/);
});
test('JavaScript parses',()=>{
 new Script(bridge);
 new Script(script);
});
