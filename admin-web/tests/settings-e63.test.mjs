import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const read=f=>readFileSync(new URL('../dist/'+f,import.meta.url),'utf8');
const escape=x=>String(x??'').replace(/[&<>"']/g,k=>({
 '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[k]));
const data={
  days:30,
  summary:{sessions_active:5,professionals_active:10,mfa_enabled:9,mfa_pending:1,
    failures:2,successes:8,revoked_7d:0,expiring_24h:1},
  my_mfa:{enabled:true,remaining_recovery_codes:7},
  my_sessions:[{id:31,current:true},{id:33,current:false}],
};
const person={
  first_name:'Awa',last_name:'DIALLO',full_name:'Awa DIALLO',
  email:'awa@superadmin.example.test',phone_number:'+221700000000',
  photo_url:null,role:'superAdmin',
};
function factory(api={adminSecurityOverview:async()=>data},visible=()=>true){
 const sandbox={window:{},Date,Intl,Number,Object,String,Promise};
 runInNewContext(read('settings-e63.js'),sandbox);
 let preference='system',profile={...person};const actions=[];
 let renders=0;
 const ctrl=sandbox.window.GConnectSettingsE63({
  api,safe:escape,profile:()=>profile,validPhoto:()=>null,
  motion:()=>preference,setMotion:x=>{preference=x;actions.push(['motion',x]);},
  openProfile:x=>actions.push(['profile',x]),
  openAbout:()=>actions.push(['about']),go:x=>actions.push(['go',x]),
  render:()=>renders++,isVisible:visible,
 });
 return {ctrl,actions,motion:()=>preference,update:p=>profile={...profile,...p},renders:()=>renders};
}
test('E63 mounts only Superadmin settings; the 3-role existing profile controls stay intact',()=>{
 const html=read('admin-connected-e19.html'),api=read('etablissement-api.js');
 assert.match(html,/pages\.parametres=settingsE63\.page/);
 assert.match(html,/if\(isPlatformAdmin&&view==='parametres'\)settingsE63\?\.ensure\(\)/);
 assert.match(html,/settings-e63\.css\?v=e63-personal-1/);
 assert.match(html,/settings-e63\.js\?v=e63-personal-1/);
 assert.match(html,/openProfile:tab=>\{\s*\$\('profile-open'\)\.click\(\);\s*profileTab\(tab\)/);
 assert.match(html,/setMotion:value=>\{\s*motionPreference\.value=value;\s*motionPreference\.dispatchEvent/);
 assert.match(html,/pages\.sessions=securityE62\.page/);
 assert.match(html,/pages\.audit=auditE61\.page/);
 assert.match(html,/pages\.statistiques=statisticsE60\.page/);
 assert.match(html,/professional-profile-form/);
 assert.match(html,/professional-password-form/);
 assert.match(html,/professional-profile-upload/);
 assert.match(api,/const professionalProfileUpdate = async payload/);
 assert.match(api,/const professionalChangePassword =/);
});
test('E63 shows only actual user data and observed MFA counters',async()=>{
 const {ctrl}=factory();
 let html=ctrl.page();
 assert.match(html,/Profil <em>& paramètres<\/em>/);
 assert.match(html,/Awa DIALLO/);
 assert.match(html,/awa@superadmin\.example\.test/);
 assert.match(html,/e63-safety-stats/);
 assert.match(html,/<strong>—<\/strong>/);
 await ctrl.load();
 html=ctrl.page();
 assert.match(html,/Codes de secours disponibles/);
 assert.match(html,/<strong>7<\/strong>/);
 assert.match(html,/<strong>2<\/strong>/);
 assert.match(html,/Authentification renforcée active/);
 assert.match(html,/Changer mon mot de passe/);
 assert.doesNotMatch(html,/Mode démonstration|Aucune donnée réelle|Prévisualisation/);
});
test('E63 inherits and updates existing browser-local motion preference',()=>{
 const {ctrl,actions,motion}=factory();
 assert.match(ctrl.page(),/data-e63-motion="system" aria-pressed="true"/);
 ctrl.action({dataset:{e63Motion:'off'}});
 assert.equal(motion(),'off');
 assert.deepEqual(actions,[['motion','off']]);
 assert.match(ctrl.page(),/data-e63-motion="off" aria-pressed="true"/);
 ctrl.action({dataset:{e63Motion:'invalid'}});
 assert.equal(motion(),'off');
});
test('E63 calls the existing profile, photo, password, about and navigation UX',()=>{
 const {ctrl,actions}=factory();
 for(const command of ['profile','photo','password','sessions','audit','about'])
  ctrl.action({dataset:{e63Action:command}});
 assert.deepEqual(actions,[
  ['profile','profile'],['profile','profile'],['profile','security'],
  ['go','sessions'],['go','audit'],['about'],
 ]);
});
test('E63 has no invented MFA status on failure and does not expose secrets',async()=>{
 const {ctrl}=factory({adminSecurityOverview:async()=>{throw Error('Connexion interrompue.')}});
 await ctrl.load();
 const html=ctrl.page();
 assert.match(html,/Connexion interrompue/);
 assert.match(html,/État indisponible/);
 assert.doesNotMatch(html,/MFA activée.*certifiée/);
 assert.doesNotMatch(html,/token_hash|encrypted_secret|password\s*:/);
});
test('E63 uses escaped text for profile fields and accepts photos only from sanitizing owner callback',()=>{
 const {ctrl,update}=factory();
 update({full_name:'<img src=x onerror=alert(1)>',email:'<script>evil()</script>'});
 const html=ctrl.page();
 assert.match(html,/&lt;img src=x onerror=alert\(1\)&gt;/);
 assert.match(html,/&lt;script&gt;evil\(\)&lt;\/script&gt;/);
 assert.doesNotMatch(html,/<img src=x onerror=/);
});
test('E63 page has a transparent hero, standalone CSS, responsive and reduced-motion controls',()=>{
 const css=read('settings-e63.css');
 assert.match(css,/\.e63-hero\{/);
 assert.match(css,/background:transparent;border:0;box-shadow:none;border-radius:0/);
 assert.match(css,/@keyframes e63-float/);
 assert.match(css,/@keyframes e63-enter/);
 assert.match(css,/prefers-reduced-motion:reduce/);
 assert.match(css,/html\[data-motion="off"\]/);
 assert.match(css,/@media\(max-width:430px\)/);
 assert.doesNotMatch(css,/\.sidebar\{/);
});
