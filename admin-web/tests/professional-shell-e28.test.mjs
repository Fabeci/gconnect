import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Script} from 'node:vm';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const html=read('admin-connected-e19.html');
const css=read('professional-shell-e28.css');
const api=read('etablissement-api.js');
const source=html.match(/<script>([\s\S]*?)<\/script>/)?.[1]||'';

test('E28 one header and official logo for all three professional roles',()=>{
  assert.match(html,/src="\/assets\/logo\.png" alt="G-Connect"/);
  assert.match(html,/class="sidebar-monogram" src="\/assets\/logo_icon\.png"/);
  assert.doesNotMatch(html,/class="brand-mark" aria-hidden/);
  const header=html.match(/<header class="topbar">([\s\S]*?)<\/header>/)?.[1]||'';
  assert.match(header,/id="topbar-search-toggle"/);
  assert.match(header,/id="topbar-date"/);
  assert.match(header,/id="notification-toggle"/);
  assert.doesNotMatch(header,/id="theme-toggle"|theme-icon--moon|id="theme-select"|id="motion-select"/);
  assert.match(source,/if\(isInstitutionAdmin\)/);
  assert.match(source,/if\(isEnterpriseAdmin\)/);
  assert.match(source,/const isPlatformAdmin=/);
  assert.match(read('professional-shell-e29.css'),/\.sidebar-monogram/);
});

test('E29 account popup cleanly separates Profile, About, and Log out',()=>{
  const menu=html.match(/<section id="profile-popover"[^>]*>([\s\S]*?)<\/section>/)?.[1]||'';
  assert.ok(menu);
  assert.match(menu,/id="profile-open"/);
  assert.match(menu,/id="about-open"/);
  assert.match(menu,/id="live-logout-profile"/);
  assert.equal((menu.match(/<button /g)||[]).length,3);
  assert.doesNotMatch(menu,/Apparence|Animations|Sécurité du compte|theme-select|motion-select/);
  assert.doesNotMatch(source,/document\.querySelector\('\.profile-popover-head strong'\)/);
});

test('E28 profile dialog has real user image editing and clear security fields',()=>{
  assert.match(html,/id="professional-profile-dialog"/);
  assert.match(html,/id="professional-profile-photo"/);
  assert.match(html,/id="professional-profile-upload".*accept="image\/jpeg,image\/png,image\/webp"/);
  assert.match(html,/id="professional-profile-remove"/);
  assert.match(html,/id="professional-profile-form"/);
  assert.match(html,/name="first_name"/);
  assert.match(html,/name="last_name"/);
  assert.match(html,/name="phone_number"/);
  assert.match(html,/id="professional-profile-email"[^>]*readonly/);
  assert.match(html,/data-profile-tab="profile"/);
  assert.match(html,/data-profile-tab="settings"/);
  assert.match(html,/data-profile-tab="security"/);
  assert.match(source,/accountApi\.professionalProfileUpdate\(data\)/);
  assert.match(source,/data\.append\('photo',professionalPhotoInput\.files\[0\]\)/);
  assert.match(source,/data\.append\('remove_photo','true'\)/);
  assert.match(source,/renderProfessionalIdentity\(professionalState\)/);
  assert.match(source,/professionalDialog\.showModal\(\)/);
  assert.match(css,/\.professional-profile-dialog::backdrop/);
  assert.match(css,/@media\(max-width:650px\)/);
  assert.doesNotThrow(()=>new Script(source));
});

test('E28 backend profile client requires an existing MFA-bound session',()=>{
  assert.match(api,/const professionalProfile = \(\) => commercialRequest\('\/users\/web-profile\/'\)/);
  assert.match(api,/const professionalProfileUpdate = async payload => \{/);
  assert.match(api,/commercialRequest\('\/users\/web-profile\/', 'PATCH', payload\)/);
  assert.match(api,/return request\(path, method, payload, token, 'WebToken'\)/);
  assert.doesNotMatch(api,/localStorage\.setItem|sessionStorage\.setItem/);
});

test('E28 profile menu is used in company, institution, and platform settings',()=>{
  assert.match(source,/pages\.settings=professionalSettingsOverview/);
  assert.match(source,/pages\.parametres=professionalSettingsOverview/);
  assert.match(source,/data-open-professional-profile/);
  assert.match(source,/Ouvrir le profil et modifier ma photo/);
  assert.doesNotMatch(source,/\$\('theme-toggle'\)/);
  assert.doesNotMatch(html,/id="theme-toggle"/);
  assert.match(html,/professional-shell-e28\.css/);
});
