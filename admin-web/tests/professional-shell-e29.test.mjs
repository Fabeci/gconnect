import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Script} from 'node:vm';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const html=read('admin-connected-e19.html');
const api=read('etablissement-api.js');
const e29=read('professional-shell-e29.css');
const source=html.match(/<script>([\s\S]*?)<\/script>/)?.[1]||'';

test('E29 left sidebar uses only the G symbol, topbar keeps the full official logo',()=>{
  const brand=html.match(/<div class="brand">([\s\S]*?)<\/div>/)?.[1]||'';
  assert.match(brand,/class="sidebar-monogram" src="\/assets\/logo_icon\.png"/);
  assert.doesNotMatch(brand,/logo\.png|brand-copy|G-connect/);
  assert.match(html,/class="top-brand"><img src="\/assets\/logo\.png"/);
  assert.doesNotMatch(source,/document\.querySelector\('\.brand-copy small'\)/);
  assert.match(e29,/\.sidebar-monogram/);
});

test('E29 search fields are transparent with a visible bottom underline and date is moved left',()=>{
  const header=html.match(/<header class="topbar">([\s\S]*?)<\/header>/)?.[1]||'';
  assert.ok(header.indexOf('id="topbar-date"')<header.indexOf('id="topbar-search-toggle"'));
  assert.match(header,/id="topbar-date"/);
  assert.match(html,/id="module-search"/);
  assert.match(e29,/\.sidebar \.sidebar-search\{/);
  assert.match(e29,/\.topbar-search-pill\{/);
  assert.match(e29,/border-bottom:2px solid/);
  assert.match(e29,/background:rgba\(248,251,255,\.08\)/);
  assert.match(e29,/#topbar-date/);
});

test('E29 account menu has distinct Profile and About, with separate About dialog',()=>{
  const menu=html.match(/<section id="profile-popover"[^>]*>([\s\S]*?)<\/section>/)?.[1]||'';
  assert.match(menu,/id="profile-open">Mon profil/);
  assert.match(menu,/id="about-open">À propos/);
  assert.match(menu,/id="live-logout-profile">Se déconnecter/);
  assert.equal((menu.match(/<button /g)||[]).length,3);
  assert.match(html,/id="professional-about-dialog"/);
  assert.match(html,/id="professional-about-close"/);
  assert.match(source,/aboutDialog\.showModal\(\)/);
  assert.match(source,/\$\('profile-open'\)\.addEventListener/);
  assert.match(source,/\$\('about-open'\)\.addEventListener/);
});

test('E29 shared modal provides real password change with confirmation, MFA re-login',()=>{
  assert.match(html,/id="professional-password-form"/);
  for(const id of ['professional-password-current','professional-password-new','professional-password-confirm']){
    assert.match(html,new RegExp('id="'+id+'"[^>]*type="password"'));
  }
  assert.match(html,/autocomplete="current-password"/);
  assert.match(html,/autocomplete="new-password"/);
  assert.match(html,/id="professional-password-feedback"/);
  assert.match(source,/accountApi\.professionalChangePassword\(current,next\)/);
  assert.match(source,/if\(next!==confirm\)/);
  assert.match(source,/if\(next===current\)/);
  assert.match(source,/if\(!result\?\.requires_relogin\)/);
  assert.match(source,/type:'gconnect-admin-logout'/);
  assert.match(api,/const professionalChangePassword = \(current_password,new_password\)/);
  assert.match(api,/commercialRequest\('\/users\/web-change-password\/', 'POST', \{current_password,new_password\}\)/);
  assert.match(api,/return request\(path, method, payload, token, 'WebToken'\)/);
  assert.doesNotMatch(api,/localStorage\.setItem|sessionStorage\.setItem/);
  assert.doesNotThrow(()=>new Script(source));
});

test('E29 dedicated styles include mobile dialog and field focus states',()=>{
  assert.match(e29,/\.professional-password-control:focus-within/);
  assert.match(e29,/\.professional-about-dialog/);
  assert.match(e29,/@media\(max-width:600px\)/);
  assert.match(html,/professional-shell-e29\.css\?v=e29-shell-1/);
});
