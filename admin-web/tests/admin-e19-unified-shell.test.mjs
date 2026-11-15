import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Script} from 'node:vm';

const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
const login=read('dist/admin-login-e19.html');
const auth=read('dist/auth-shared-e19.js');
const bridge=read('dist/admin-shared-e19.js');
const shared=read('dist/admin-connected-e19.html');
const script=shared.match(/<script>([\s\S]*?)<\/script>/)?.[1]||'';

test('one approved visual shell for Superadmin and Établissement',()=>{
 assert.match(login,/admin-shared-e19\.js/);
 assert.match(login,/auth-shared-e19\.js/);
 assert.match(bridge,/\/_internal\/admin-console/);
 assert.match(bridge,/\['superAdmin', 'etablissement', 'enterprise'\]/);
 assert.match(auth,/role==='superadmin'.*profile\?\.role==='superAdmin'/);
 assert.match(auth,/role==='etablissement'.*profile\?\.role==='etablissement'/);
 assert.match(shared,/superadmin-premium\.css/);
 assert.match(shared,/admin-rounding-e13\.css/);
 assert.match(shared,/hero-network/);
});
test('MFA and device-scoped WebToken remain in the API closure',()=>{
 const api=read('dist/etablissement-api.js');
 assert.match(auth,/finishMfa/);
 assert.match(api,/tokenKind = 'WebToken'/);
 assert.match(api,/getCurrent: \(\) => current/);
 assert.doesNotMatch(bridge,/localStorage|sessionStorage/);
 assert.match(api,/restoreSession/);
 assert.match(auth,/api\.restoreSession/);
 assert.doesNotMatch(api,/localStorage\.setItem|sessionStorage\.setItem/);
 assert.match(bridge,/event\.source !== frame\.contentWindow/);
 assert.match(bridge,/event\.origin !== location\.origin/);
});
test('institution only sees institution menu and scoped real stats',()=>{
 assert.match(script,/account\?\.stats\?\.scope==='institution'/);
 assert.match(script,/const nav=isPlatformAdmin/);
 assert.match(script,/allowedRoutes\.has\(route\)/);
 assert.match(script,/allowedRoutes\.has\(v\)/);
 assert.match(script,/allowedRoutes\.has\(initial\)/);
 assert.match(script,/if\(isInstitutionAdmin\)/);
 assert.match(script,/\['promotions','Promotions & filières'/);
 assert.match(script,/\['members','Étudiants & Alumni'/);
 assert.match(script,/institutionalStat\(students\)/);
 assert.match(script,/institutionalStat\(alumni\)/); 
 assert.match(script,/if\(isPlatformAdmin\)void refreshLive\(\)/);
});
test('Enterprise enters the same approved shell with a distinct MFA-verified role',()=>{
 assert.match(bridge,/\['superAdmin', 'etablissement', 'enterprise'\]/);
 assert.match(auth,/entreprise: \{label:'Entreprise'/);
 assert.match(auth,/accepts:\['enterprise'\]/);
 assert.match(auth,/profile\?\.enterprise_id/);
 assert.match(script,/const isEnterpriseAdmin=/);
 assert.match(script,/if\(!accountApi\?\.isConnected\(\)/);
 assert.match(script,/if\(isEnterpriseAdmin\)/);
 const api=read('dist/etablissement-api.js');
 assert.match(api,/\/backoffice\/enterprise-dashboard\//);
 assert.match(api,/stats\.enterprise_id !== profile\.enterprise_id/);
 assert.match(api,/data\.role === 'enterprise'/);
});
test('E19 does not change E18 reference files or preview',()=>{
 assert.match(read('dist/superadmin-approved-e18.js'),/superadmin-connected-e18\.html/);
 assert.match(read('dist/superadmin-login.html'),/superadmin-approved-e18\.js/);
 assert.match(read('dist/superadmin-preview.html'),/Pilotage du réseau/);
});
test('the shared E19 console activates the approved premium shell selectors',()=>{
 const premium=read('dist/superadmin-premium.css');
 assert.match(shared, /^<!doctype html>\s*<html lang="fr" data-space="superadmin" data-console="administration">/);
 assert.match(premium, /html\[data-space="superadmin"\] \.topbar-search-pill svg\{width:17px;height:17px/);
 assert.match(premium, /html\[data-space="superadmin"\] \.profile-trigger svg\{width:14px;height:14px/);
 assert.match(premium, /html\[data-space="superadmin"\] \.sa-sidebar-identity\{/);
 assert.match(shared, /const nav=isPlatformAdmin/);
 assert.match(read('dist/superadmin-connected-e18.html'), /data-space="superadmin"/);
});
test('premium styles and shared admin frame use the same cache-busting revision',()=>{
 const revision='e22-pricing-20261026a';
 assert.ok(login.includes('admin-shared-e19.js?v='+revision));
 assert.ok(login.includes('auth-shared-e19.js?v='+revision));
 assert.ok(bridge.includes('/_internal/admin-console?v='+revision));
 for(const stylesheet of ['superadmin-establishment-theme.css','superadmin-premium.css','admin-rounding-e13.css']){
   assert.ok(shared.includes(stylesheet+'?v='+revision),stylesheet+' must be refreshed');
 }
});
test('institution statistics are a separate, scoped page with honest empty values',()=>{
 assert.ok(script.includes('pages.statistics=institutionStatistics'));
 assert.ok(!script.includes('pages.statistics=institutionDashboard'));
 const start=script.indexOf('function institutionStatCard(');
 const end=script.indexOf('function institutionModule(',start);
 assert.ok(start>0 && end>start);
 const statsFunction=script.slice(start,end);
 const display=stats=>new Script(statsFunction+';institutionStatistics();').runInNewContext({
   account:{stats},
   safe:value=>String(value),
   icon:()=>'<svg/>',
   institutionalStat:value=>Number.isFinite(value)&&value>=0?String(value):'—',
   intro:(title,description)=>'<h1>'+title+'</h1><p>'+description+'</p>',
   panel:(title,description,body)=>'<section>'+title+body+'</section>'
 });
 const zero=display({scope:'institution',institution_name:'Établissement test',users:{students:0,alumni:0},promotions_count:1,posts:{events:0}});
 assert.ok(zero.includes('Statistiques de l’établissement'));
 assert.ok(zero.includes('Aucun membre rattaché actuellement.'));
 assert.ok(zero.includes('Promotions'));
 assert.ok(zero.includes('e20-graph-line'));
 assert.ok(zero.includes('e20-donut'));
 assert.ok(zero.includes('<strong>1</strong>'));
 assert.ok(!zero.includes('Votre communauté.<br>'));
 const createdToday=new Date().toISOString().slice(0,10);
 const activity=display({scope:'institution',institution_name:'Établissement test',
   users:{students:2,alumni:1},promotions_count:1,posts:{events:1},
   signups_last_30_days:[{date:createdToday,count:3}]});
 assert.ok(activity.includes('3 nouveau(x)'));
 assert.ok(activity.includes('e20-graph-dot'));
 const unavailable=display({scope:'institution',institution_name:'Établissement test'});
 assert.ok(unavailable.includes('Répartition indisponible'));
 assert.ok(unavailable.includes('—'));
});
test('Enterprise statistics and offers use scoped real data, including honest empty charts',()=>{
 const a=script.indexOf('const enterpriseStats=()=>');
 const b=script.indexOf('function institutionModule(',a);
 assert.ok(a>0 && b>a);
 const companyFunction=script.slice(a,b);
 const display=(stats,fn)=>new Script(companyFunction+';'+fn+'();').runInNewContext({
   account:{profile:{email:'rh@exemple.test'},stats},
   safe:value=>String(value),
   icon:()=>'<svg/>',
   institutionalStat:value=>Number.isFinite(value)&&value>=0?String(value):'—',
   intro:(title,description)=>'<h1>'+title+'</h1><p>'+description+'</p>',
   panel:(title,description,body)=>'<section>'+title+body+'</section>'
 });
 const zero={scope:'enterprise',enterprise_id:1,company_name:'Atelier Bleu',
  posts:{total:0,drafts:0},opportunities:{total:0,open:0,closed:0,recent:[]},
  applications:{total:0,by_status:{}},engagement:{views:0,reactions:0,comments:0}};
 const home=display(zero,'enterpriseDashboard');
 assert.match(home,/ESPACE ENTREPRISE/);
 assert.match(home,/Aucune offre publiée/);
 assert.doesNotMatch(home,/Baobab Digital|Institut Horizon/);
 const graph=display(zero,'enterpriseStatistics');
 assert.match(graph,/Évolution des offres et candidatures/);
 assert.match(graph,/e20-donut/);
 assert.match(graph,/Aucune nouvelle activité/);
 const today=new Date().toISOString().slice(0,10);
 const real={...zero,opportunities:{total:1,open:1,closed:0,recent:[
   {id:6,title:'Offre rattachée',status:'open',category:'job',applications:3}
 ]},applications:{total:3,by_status:{submitted:2,interview:1}},
  offers_last_30_days:[{date:today,count:1}],
  applications_last_30_days:[{date:today,count:3}]};
 assert.match(display(real,'enterpriseOffers'),/Offre rattachée/);
 assert.match(display(real,'enterpriseApplications'),/Candidatures/);
 assert.match(display(real,'enterpriseStatistics'),/Candidatures · 3/);
});
test('inline script and role-aware scripts parse',()=>{
 new Script(auth);
 new Script(bridge);
 new Script(script);
});
