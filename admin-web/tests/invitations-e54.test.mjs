import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const read = path => readFileSync(new URL('../dist/'+path, import.meta.url), 'utf8');
const secureText = value => String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
function instance(role, api) {
  const dom={addEventListener:()=>{},body:{appendChild:()=>{}}};
  const box={window:{},document:dom,Date,Number,String,FormData,Promise};
  runInNewContext(read('invitations-e54.js'),box);
  let renders=0;
  const module=box.window.GConnectInvitationsE54({
    api,role,safe:secureText,
    intro:(title,desc)=>'<h1>'+title+'</h1><p>'+String(desc||'')+'</p>',
    panel:(_title,_desc,body)=>body,
    render:()=>{renders++;},isVisible:()=>true,
  });
  return {module, rendered:()=>renders};
}
test('E54 preserves E38 client and adds scoped API calls',()=>{
  const source=read('etablissement-api.js');
  for(const name of ['invoiceHistory','invoiceIssue','myInvoices','subscriptionCheckoutVerify',
    'restoreSession','enterpriseOwnerInvitations','enterpriseInviteOwner',
    'enterpriseRecruiterInvitations','enterpriseInviteRecruiter','enterpriseRevokeRecruiter',
    'enterprisePreviewInvitation','enterpriseAcceptInvitation']){
    assert.match(source,new RegExp('\\b'+name+'\\b'));
  }
  assert.match(source,/enterpriseRevokeInvitation/);
  assert.match(source,/Number\.isSafeInteger/);
});
test('Superadmin displays only real enterprise/institution invitations and secure actions',async()=>{
  const future=new Date(Date.now()+86400000).toISOString();
  let calls=0;
  const {module}=instance('superAdmin',{
    listInvitations:async()=>{calls++;return [{id:8,email:'school@test.example',institution_name:'Campus',expires_at:future}]},
    enterpriseOwnerInvitations:async()=>{calls++;return [{id:10,email:'owner@test.example',company_name:'Entreprise',expires_at:future,kind:'owner'}]}
  });
  await module.load();const html=module.page();
  assert.equal(calls,2);
  assert.match(html,/school@test\.example/);
  assert.match(html,/owner@test\.example/);
  assert.match(html,/data-e54-form="owner"/);
  assert.match(html,/data-e54-form="school"/);
  assert.match(html,/data-e54-detail="owner:0"/);
  assert.doesNotMatch(html,/Ajouter à la maquette|Données fictives/);
});
test('Only verified owner receives recruiter invitation controls',async()=>{
  const future=new Date(Date.now()+86400000).toISOString();
  const {module}=instance('enterprise',{
    enterpriseMembership:async()=>({membership:'owner',company:{name:'Horizon'}}),
    enterpriseRecruiterInvitations:async()=>[{id:4,email:'staff@test.example',kind:'recruiter',expires_at:future}],
    enterpriseRecruiters:async()=>[{id:5,email:'active@test.example',name:'Recruteur',active:true}],
  });
  await module.load();const html=module.page();
  assert.match(html,/data-e54-form="recruiter"/);
  assert.match(html,/staff@test\.example/);
  assert.match(html,/active@test\.example/);
  assert.match(html,/data-e54-member="5"/);
});
test('Recruiters receive a read-only team view',async()=>{
  const {module}=instance('enterprise',{
    enterpriseMembership:async()=>({membership:'recruiter',company:{name:'Horizon'}}),
    enterpriseRecruiterInvitations:async()=>{throw Error('Must not call owner endpoint')},
  });
  await module.load();const html=module.page();
  assert.match(html,/réservées à son responsable/);
  assert.doesNotMatch(html,/data-e54-form="recruiter"/);
});
test('Activation route is private and removes the fragment before contact with the API',()=>{
  const activation=read('entreprise-activation.js');
  const html=read('entreprise-activation.html');
  assert.match(activation,/history\.replaceState/);
  assert.match(activation,/enterprisePreviewInvitation\(invitation\)/);
  assert.match(activation,/enterpriseAcceptInvitation/);
  assert.doesNotMatch(activation,/(localStorage|sessionStorage|console\.log)/);
  assert.match(html,/name="referrer" content="no-referrer"/);
  assert.match(html,/autocomplete="new-password"/);
});
test('The same professional E19 shell hosts both E54 invitation screens',()=>{
  const html=read('admin-connected-e19.html');
  assert.match(html,/invitationsE54=window\.GConnectInvitationsE54/);
  assert.match(html,/if\(isPlatformAdmin\)pages\.invitations=invitationsE54\.page/);
  assert.match(html,/if\(isEnterpriseAdmin\)pages\.team=invitationsE54\.page/);
  assert.match(html,/invitationsE54\.ensure\(view\)/);
});

test('Recruiter console routes never expose owner billing or publishing',()=>{
  const shell=read('admin-connected-e19.html');
  const client=read('etablissement-api.js');
  const recruiter=read('recruiter-e54.js');
  assert.match(shell,/const isRecruiter=/);
  assert.match(shell,/if\(isRecruiter\)/);
  assert.match(shell,/if\(!isRecruiter\)void billingE22\.load\(\)/);
  assert.match(client,/profile\.enterprise_role === 'recruiter'/);
  assert.match(client,/\/users\/enterprise\/dashboard\//);
  assert.match(recruiter,/enterpriseReadOffers/);
  assert.match(recruiter,/enterpriseReadOfferApplications/);
  assert.doesNotMatch(recruiter, /subscriptionCheckoutStart|invoiceIssue|pricingAssign/);
});

test('Invitation service failures are visible without an automatic retry loop',async()=>{
  let attempts=0;
  const {module}=instance('superAdmin',{
    listInvitations:async()=>{attempts++;throw new Error('indisponible');},
    enterpriseOwnerInvitations:async()=>[],
  });
  await module.load();
  module.ensure();
  await Promise.resolve();
  assert.equal(attempts,1);
  assert.match(module.page(),/indisponible/);
});

test('Company name from API is escaped in the recruiter-team heading',async()=>{
  const {module}=instance('enterprise',{
    enterpriseMembership:async()=>({membership:'recruiter',company:{name:'<svg onload=alert(1)>'}}),
  });
  await module.load();
  const html=module.page();
  assert.doesNotMatch(html,/<svg onload=/);
  assert.match(html,/&lt;svg/);
});

test('Premium invitation pages preserve different identities without changing the E19 shell',async()=>{
  const {module:admin}=instance('superAdmin',{
    listInvitations:async()=>[], enterpriseOwnerInvitations:async()=>[],
  });
  const {module:enterprise}=instance('enterprise',{
    enterpriseMembership:async()=>({membership:'owner',company:{name:'Horizon'}}),
    enterpriseRecruiterInvitations:async()=>[],
    enterpriseRecruiters:async()=>[],
  });
  await Promise.all([admin.load(),enterprise.load()]);
  const school=admin.page();
  const team=enterprise.page();
  assert.match(school,/e54-stage-admin/);
  assert.match(school,/e54-workflow-school/);
  assert.match(school,/e54-workflow-building/);
  assert.match(school,/e54-journey/);
  assert.match(team,/e54-stage-team/);
  assert.match(team,/e54-workflow-recruiter/);
  assert.match(team,/e54-team-members/);
  const styles=read('invitations-e54.css');
  assert.match(styles,/\.e54-stage-team/);
  assert.match(styles,/\.e54-workflow-building/);
  assert.match(styles,/prefers-reduced-motion/);
  const shell=read('admin-connected-e19.html');
  assert.match(shell,/superadmin-premium\.css/);
  assert.match(shell,/floating-hero-e33\.css/);
  assert.match(shell,/invoices-e38\.js/);
});

test('Invitation API errors never present fake zero KPIs and provide a retry action',async()=>{
  const {module}=instance('superAdmin',{
    listInvitations:async()=>{throw new Error('API indisponible')},
    enterpriseOwnerInvitations:async()=>[],
  });
  await module.load();
  const html=module.page();
  assert.match(html,/API indisponible/);
  assert.match(html,/data-e54-refresh/);
  assert.match(html,/e54-metric[^>]*><strong>—<\/strong>/);
  assert.doesNotMatch(html,/e54-metric[^>]*><strong>0<\/strong>/);
});

test('E55 invitations header follows borderless Finance E37 pattern, not a blue banner',async()=>{
  const {module}=instance('superAdmin',{
    listInvitations:async()=>[],enterpriseOwnerInvitations:async()=>[],
  });
  await module.load();
  const html=module.page();
  assert.match(html,/^<header class="e54-stage e54-stage-admin"/);
  assert.match(html,/<h1>Invitations <em>professionnelles<\/em><\/h1>/);
  assert.doesNotMatch(html.split('</header>')[0],/Chaque nouvel accès|<h2>/);
  assert.match(html,/e54-stage-art/);
  assert.match(html,/e54-orbit-ring/);
  assert.match(html,/e54-workflow-school/);
  assert.match(html,/e54-workflow-building/);
  const css=read('invitations-e54.css');
  assert.match(css,/\.e54-stage,\s*\.e54-stage\.e54-stage-team\s*\{/);
  assert.match(css,/border:0;\s*border-radius:0;\s*background:transparent;\s*box-shadow:none;/);
  assert.match(css,/\.e54-stage::before\{content:none;box-shadow:none\}/);
  assert.match(css,/@keyframes e55-copy-appear/);
  assert.match(css,/@keyframes e55-art-appear/);
  assert.match(css,/@keyframes e55-card-enter/);
  assert.match(css,/@keyframes e55-signal-pulse/);
  assert.match(css,/\.e54-reveal\.e54-visible/);
  assert.match(css,/prefers-reduced-motion:reduce/);
  const finance=read('finance-e36.css');
  assert.match(finance,/\.e36-hero\{[\s\S]*?border:none;border-radius:0;box-shadow:none;background:transparent/);
  const shell=read('admin-connected-e19.html');
  assert.match(shell,/invitations-e54.css\?v=e56-invite-cards-1/);
  assert.match(shell,/invitations-e54.js\?v=e56-invite-cards-1/);
});

test('E55 enterprise team keeps its own teal identity and safe name rendering',async()=>{
  const {module}=instance('enterprise',{
    enterpriseMembership:async()=>({membership:'recruiter',company:{name:'<svg onload=alert(1)>'}}),
  });
  await module.load();
  const html=module.page();
  assert.match(html,/^<header class="e54-stage e54-stage-team"/);
  assert.match(html,/<h1>Équipe <em>& accès<\/em><\/h1>/);
  assert.doesNotMatch(html,/<svg onload=/);
  assert.match(html,/&lt;svg/);
  assert.doesNotMatch(html,/&amp;lt;svg/);
  assert.doesNotMatch(html,/data-e54-form="recruiter"/);
});

test('E56 invitation cards use compact actions and keep the history header free of E31 accent strokes',async()=>{
  const {module}=instance('superAdmin',{
    listInvitations:async()=>[], enterpriseOwnerInvitations:async()=>[],
  });
  await module.load();
  const html=module.page();
  assert.equal((html.match(/class="e54-form-actions"/g)||[]).length,2);
  assert.equal((html.match(/class="e54-workflow-ornament"/g)||[]).length,2);
  assert.equal((html.match(/class="e54-form-note"/g)||[]).length,2);
  assert.match(html,/data-e54-form="school"/);
  assert.match(html,/data-e54-form="owner"/);
  assert.match(html,/e54-history-panel/);
  const css=read('invitations-e54.css');
  assert.match(css,/\.e54-history-panel \.panel-title::before\s*\{\s*content:none!important;display:none!important;/);
  assert.match(css,/\.e54-invite-grid \.e54-form-actions \.e54-primary\s*\{[\s\S]*?width:auto;min-width:183px;/);
  assert.match(css,/@keyframes e56-card-appear/);
  assert.match(css,/@keyframes e56-metric-appear/);
  assert.match(css,/prefers-reduced-motion:reduce/);
});
