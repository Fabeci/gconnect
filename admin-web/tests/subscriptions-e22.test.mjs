import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
const html=source('dist/admin-connected-e19.html');
const api=source('dist/etablissement-api.js');
const moduleCode=source('dist/subscriptions-e22.js');
const styles=source('dist/subscriptions-e22.css');
const js=html.match(/<script>([\s\S]*?)<\/script>/)?.[1]||'';

function factory(apiMock,admin){
 const redirects=[];
 const sandbox={window:{location:{assign:url=>redirects.push(url)}},URL,Intl,FormData:class{
   constructor(values){this.values=values}
   get(key){return this.values[key]}
 }};
 vm.runInNewContext(moduleCode,sandbox);
 const notifications=[];
 const context={
   api:apiMock,admin,
   safe:value=>String(value).replaceAll('<','&lt;').replaceAll('>','&gt;'),
   intro:(title,sub)=>'<header>'+title+' '+sub+'</header>',
   panel:(title,sub,body)=>'<section>'+title+' '+sub+body+'</section>',
   notify:message=>notifications.push(message),
   render:()=>{},route:()=>admin?'abonnements':'subscription'
 };
 return {ui:sandbox.window.GConnectSubscriptionsE22(context),notifications,redirects};
}

test('all five administration submit buttons align at the bottom of their cards',()=>{
 assert.match(moduleCode,/class="e22-card"/);
 assert.match(moduleCode,/class="e22-layout-form"/);
 assert.match(styles,/\.e22-card\{[^}]*display:flex;flex-direction:column/);
 assert.match(styles,/\.e22-layout-form\{[^}]*flex:1/);
 assert.match(styles,/\.e22-layout-form>\.e22-actions\{[^}]*margin-top:auto/);
});

test('one shared shell has enterprise, institution and Superadmin subscription navigation',()=>{
 assert.match(js,/\['subscription','Abonnement','billing'\]/);
 assert.match(js,/pages\.abonnements=\(\)=>billingE22\.adminPage\(\)/);
 assert.match(js,/pages\.facturation=\(\)=>financeE36\.page\(\)/);
 assert.doesNotMatch(js,/pages\.facturation=\(\)=>billingE22\.adminPage\(\)/);
 assert.match(js,/pages\.subscription=\(\)=>billingE22\.clientPage\(\)/);
 assert.match(html,/subscriptions-e22\.js\?v=e22-pricing-20261026a/);
 assert.match(html,/subscriptions-e22\.css\?v=e22-pricing-20261026a/);
 new vm.Script(js);
 new vm.Script(moduleCode);
});

test('MFA closure is the only way subscription data leaves the backend',()=>{
 assert.match(api,/function commercialRequest/);
 assert.match(api,/tokenKind !== 'WebToken'/);
 assert.match(api,/pricingAdminOffers/);
 assert.match(api,/subscriptionMine/);
 assert.doesNotMatch(api,/localStorage\.setItem|sessionStorage\.setItem/);
});

test('customer sees exact configured matrix: 1, 6, 12 months and quote',async()=>{
 const catalog=[{id:2,name:'Offre par compte',kind:'per_account',is_active:true,description:'',
   prices:[{id:1,term_months:1,seats:200,amount:'1000.00',currency:'XOF',is_active:true},
           {id:2,term_months:6,seats:200,amount:'5000.00',currency:'XOF',is_active:true},
           {id:3,term_months:12,seats:200,amount:'9000.00',currency:'XOF',is_active:true},
           {id:4,term_months:0,seats:200,amount:null,currency:'XOF',is_active:true}]}];
 const {ui}=factory({
   subscriptionCatalog:async()=>catalog,
   subscriptionMine:async()=>({current:null,history:[]}),
 },false);
 await ui.load();
 const text=ui.clientPage();
 for(const name of ['1 mois','6 mois','12 mois','Sur devis','200 comptes'])assert.ok(text.includes(name));
 assert.match(text,/Aucun abonnement actif/);
 assert.doesNotMatch(text,/facture payée|paiement effectué/i);
});

test('Superadmin UI uses real offers, saved prices and assigned subscription records',async()=>{
 const offer={id:5,slug:'offre-flexible',name:'Offre Flexible',
   kind:'flexible',audience:'institution',quota_unit:'accounts',is_active:true,prices:[
     {id:7,term_months:6,seats:50,quota_unit:'accounts',amount:'8500.00',currency:'XOF',is_active:true},
   ]};
 const calls=[];
 const {ui}=factory({
   pricingAdminOffers:async()=>[offer],
   pricingAdminOrganisations:async()=>({institutions:[{id:3,name:'Institut E22'}],enterprises:[]}),
   pricingAdminAssignments:async()=>[{id:9,institution_id:3,organisation_name:'Institut E22',offer_name:'Offre Flexible',
     status:'active',seats:50,amount:'8500.00',currency:'XOF'}],
   pricingSetPrice:async value=>calls.push(value),
 },true);
 await ui.load();
 assert.match(ui.adminPage(),/Offres Entreprise/);
 assert.match(ui.adminPage(),/Offres Établissement/);
 assert.doesNotMatch(ui.adminPage(),/Fixer ou modifier un prix/);
 await ui.action({dataset:{subAction:'scope',audience:'institution'}});
 const rendered=ui.adminPage();
 assert.match(rendered,/Fixer ou modifier un prix/);
 assert.match(rendered,/Institut E22/);
 assert.match(rendered,/8\s?500/);
 assert.match(rendered,/Suspendre/);
 assert.match(rendered,/sur devis/i);
});

test('old versioned prices are hidden from customers but visible in Superadmin audit',async()=>{
 const rates=[
   {id:3,term_months:1,seats:100,amount:'2000.00',currency:'XOF',is_active:false},
   {id:4,term_months:1,seats:100,amount:'2500.00',currency:'XOF',is_active:true},
 ];
 const offers=[{id:1,name:'Offre Flexible',kind:'flexible',audience:'institution',quota_unit:'accounts',is_active:true,prices:rates}];
 const customer=factory({subscriptionCatalog:async()=>offers,subscriptionMine:async()=>({current:null,history:[]})},false).ui;
 await customer.load();
 assert.doesNotMatch(customer.clientPage(),/2\s?000/);
 assert.match(customer.clientPage(),/2\s?500/);
 const admin=factory({
   pricingAdminOffers:async()=>offers,
   pricingAdminOrganisations:async()=>({institutions:[],enterprises:[]}),
   pricingAdminAssignments:async()=>[],
 },true).ui;
 await admin.load();
 await admin.action({dataset:{subAction:'scope',audience:'institution'}});
 assert.match(admin.adminPage(),/1 ancien\(s\) tarif/);
});

test('enterprise quota is consumed, not released by deletion, and limits are displayed',async()=>{
 const {ui}=factory({
   subscriptionCatalog:async()=>[{id:11,name:'Offre Publications',audience:'enterprise',quota_unit:'publications',is_active:true,
     prices:[{id:12,seats:20,quota_unit:'publications',term_months:6,amount:'36000.00',currency:'XOF',is_active:true}]}],
   subscriptionMine:async()=>({organisation_type:'enterprise',quota:{unit:'publications',included:20,extra:0,limit:20,used:20,remaining:0},
     current:{id:7,offer_name:'Offre Publications',seats:20,quota_unit:'publications',term_months:6,amount:'36000',currency:'XOF',
       starts_at:'2026-11-01',ends_at:'2027-05-01',quota:{unit:'publications',included:20,extra:0,limit:20,used:20,remaining:0}},history:[]}),
 },false);
 await ui.load();
 const page=ui.clientPage();
 assert.match(page,/20 <small>\/ 20/);
 assert.match(page,/suppression d’une publication ne restitue pas/);
 assert.match(page,/Limite atteinte/);
 assert.match(page,/20 publications/);
});

test('scope navigation exposes separate publication and account pricing forms',async()=>{
 const mock={pricingAdminOffers:async()=>[
   {id:1,name:'Entreprise',audience:'enterprise',quota_unit:'publications',is_active:true,prices:[]},
   {id:2,name:'Établissement',audience:'institution',quota_unit:'accounts',is_active:true,prices:[]},
 ],pricingAdminOrganisations:async()=>({institutions:[],enterprises:[]}),pricingAdminAssignments:async()=>[]};
 const {ui}=factory(mock,true);await ui.load();
 await ui.action({dataset:{subAction:'scope',audience:'enterprise'}});
 const enterprise=ui.adminPage();
 assert.match(enterprise,/Nombre de publications/);
 assert.match(enterprise,/Offre Publications/);
 assert.doesNotMatch(enterprise,/value="per_account"/);
 assert.doesNotMatch(enterprise,/Nombre de comptes actifs/);
 await ui.action({dataset:{subAction:'scope',audience:'institution'}});
 assert.match(ui.adminPage(),/Nombre de comptes actifs/);
 assert.match(ui.adminPage(),/value="per_account"/);
 await ui.action({dataset:{subAction:'back'}});
 assert.doesNotMatch(ui.adminPage(),/data-sub-form="price"/);
});



test('Superadmin overview opens each configuration in an accessible native dialog',async()=>{
 const {ui}=factory({
   pricingAdminOffers:async()=>[],
   pricingAdminOrganisations:async()=>({institutions:[],enterprises:[]}),
   pricingAdminAssignments:async()=>[],
 },true);
 await ui.load();
 const overview=ui.adminPage();
 assert.match(overview,/data-sub-action="scope" data-audience="enterprise"/);
 assert.match(overview,/data-sub-action="scope" data-audience="institution"/);
 assert.doesNotMatch(overview,/<dialog/);
 assert.doesNotMatch(overview,/data-sub-form="offer"/);

 await ui.action({dataset:{subAction:'scope',audience:'enterprise'}});
 const enterprise=ui.adminPage();
 assert.match(enterprise,/<dialog class="e22-dialog" aria-labelledby="e22-dialog-title"/);
 assert.match(enterprise,/aria-label="Fermer la configuration"/);
 for(const form of ['offer','edit-offer','price','assignment','topup']){
   assert.match(enterprise,new RegExp('data-sub-form="'+form+'"'));
 }
 assert.match(enterprise,/Offre Publications/);
 assert.match(enterprise,/Crédits \/ places supplémentaires/);
 assert.doesNotMatch(enterprise,/value="per_account"/);

 await ui.action({dataset:{subAction:'back'}});
 assert.doesNotMatch(ui.adminPage(),/<dialog/);
 await ui.action({dataset:{subAction:'scope',audience:'institution'}});
 const institution=ui.adminPage();
 assert.match(institution,/Configuration · Établissements/);
 assert.match(institution,/Nombre de comptes actifs/);
 assert.match(institution,/value="per_account"/);
 assert.match(styles,/\.e22-dialog::backdrop/);
 assert.match(js,/subscriptionDialog\.showModal\(\)/);
 assert.match(js,/subscriptionDialog\.addEventListener\('cancel'/);
});


test('E26 demand dashboard shows real enterprise requests, filters and accessible review',async()=>{
 const requests=[
  {id:31,organisation_type:'enterprise',organisation_name:'ACME',
    request_type:'renewal',requested_term_months:6,status:'pending',
    current_ends_at:'2026-12-01',note:'Merci de renouveler',
    created_at:'2026-11-05T17:00:00'},
  {id:32,organisation_type:'institution',organisation_name:'École Exemple',
    request_type:'capacity',requested_quantity:50,status:'pending',
    created_at:'2026-11-05T18:00:00'},
 ];
 const reviewed=[];
 const {ui}=factory({
   pricingAdminOffers:async()=>[],
   pricingAdminOrganisations:async()=>({institutions:[],enterprises:[]}),
   pricingAdminAssignments:async()=>[],
   pricingAdminRequests:async()=>requests,
   pricingReviewRequest:async(id,payload)=>reviewed.push({id,payload}),
 },true);
 await ui.load();
 assert.doesNotMatch(ui.adminPage(),/CENTRE DE DEMANDES/);
 await ui.action({dataset:{subAction:'scope',audience:'enterprise'}});
 const content=ui.adminPage();
 assert.match(content,/e26-config-top/);
 assert.match(content,/CENTRE DE DEMANDES/);
 assert.match(content,/ACME/);
 assert.doesNotMatch(content,/École Exemple/);
 assert.match(content,/data-sub-action="review-request" data-id="31"/);
 await ui.action({dataset:{subAction:'review-request',id:'31'}});
 assert.match(ui.adminPage(),/class="e26-review-dialog"/);
 assert.match(ui.adminPage(),/Merci de renouveler/);
 await ui.action({dataset:{subAction:'review-decision',status:'approved'}});
 assert.equal(reviewed.length,1);
 assert.equal(reviewed[0].id,31);
 assert.equal(reviewed[0].payload.status,'approved');
 assert.doesNotMatch(ui.adminPage(),/class="e26-review-dialog"/);
});

test('E26 client requests are submitted to the server and visible in history',async()=>{
 const created=[];
 let sent=[];
 const mine={organisation_type:'enterprise',current:{
   id:9,offer_name:'Publications',seats:20,quota_unit:'publications',
   term_months:6,amount:'24000',currency:'XOF',
   starts_at:'2026-11-01',ends_at:'2027-01-31',
 },history:[]};
 const {ui}=factory({
   subscriptionCatalog:async()=>[],
   subscriptionMine:async()=>mine,
   subscriptionRequestsMine:async()=>sent,
   subscriptionCreateRequest:async payload=>{
     created.push(payload);
     sent=[{id:11,request_type:payload.request_type,requested_term_months:payload.requested_term_months,requested_quantity:payload.requested_quantity,status:'pending',created_at:'2026-11-05'}];
   },
 },false);
 await ui.load();
 assert.match(ui.clientPage(),/data-client-view="request"/);
 assert.doesNotMatch(ui.clientPage(),/data-sub-form="renewal-request"/);
 await ui.action({dataset:{subAction:'client-open',clientView:'request'}});
 assert.match(ui.clientPage(),/data-sub-form="renewal-request"/);
 assert.match(ui.clientPage(),/data-sub-form="capacity-request"/);
 assert.match(ui.clientPage(),/Aucune demande envoyée/);
 await ui.submit({dataset:{subForm:'renewal-request'},requested_term_months:'6',note:'Poursuivre'});
 assert.equal(created.length,1);
 assert.equal(created[0].request_type,'renewal');
 assert.equal(created[0].requested_term_months,6);
 assert.match(ui.clientPage(),/En attente/);
 await ui.submit({dataset:{subForm:'capacity-request'},requested_quantity:'10',note:''});
 assert.equal(created[1].requested_quantity,10);
 assert.equal(created[1].request_type,'capacity');
 assert.match(ui.clientPage(),/L’envoi ne prélève aucun paiement/);
});

test('E26 request API is limited to MFA WebToken and no fabricated payment',()=>{
 assert.match(api,/subscriptionCreateRequest = payload => commercialRequest\('\/subscriptions\/requests\/my\/', 'POST'/);
 assert.match(api,/pricingReviewRequest = \(id, payload\) => commercialRequest\('\/subscriptions\/admin\/requests\/'/);
 assert.match(styles,/\.e26-config-top\{display:grid;grid-template-columns:/);
 assert.match(styles,/\.e26-review-dialog::backdrop/);
 assert.match(js,/reviewDialog\.showModal\(\)/);
});


test('E27 enterprise plan chooser opens the premium dialog and redirects only to the verified hosted PSP domain',async()=>{
 const purchase=[];
 const offer={id:11,name:'Offre Publications',audience:'enterprise',quota_unit:'publications',is_active:true,
  prices:[{id:14,term_months:6,seats:20,amount:'30000',currency:'XOF',is_active:true},
          {id:15,term_months:12,seats:40,amount:'54000',currency:'XOF',is_active:true}]};
 const {ui,redirects}=factory({
  subscriptionCatalog:async()=>[offer],
  subscriptionMine:async()=>({organisation_type:'enterprise',current:null,history:[]}),
  subscriptionCheckoutConfig:async()=>({enabled:true,provider:'cinetpay'}),
  subscriptionCheckoutOrders:async()=>[],
  subscriptionCheckoutStart:async(priceId)=>{
   purchase.push(priceId);
   return {checkout_url:'https://checkout.cinetpay.com/payment/test-reference'};
  },
 },false);
 await ui.load();
 assert.match(ui.clientPage(),/Choisir et payer un forfait/);
 assert.doesNotMatch(ui.clientPage(),/e27-client-dialog/);
 await ui.action({dataset:{subAction:'client-open',clientView:'checkout'}});
 const modal=ui.clientPage();
 assert.match(modal,/class="e27-client-dialog"/);
 assert.match(modal,/20 publications/);
 assert.match(modal,/40 publications/);
 assert.match(modal,/Payer en ligne avec CinetPay/);
 await ui.action({dataset:{subAction:'select-checkout-price',id:'15'}});
 assert.match(ui.clientPage(),/54[\s ]?000 XOF/);
 await ui.action({dataset:{subAction:'start-checkout'}});
 assert.equal(purchase.length,1);
 assert.equal(purchase[0],15);
 assert.deepEqual(redirects,['https://checkout.cinetpay.com/payment/test-reference']);
 assert.match(js,/clientSubscriptionDialog\.showModal\(\)/);
 assert.match(styles,/\.e27-client-dialog::backdrop/);
});

test('E27 establishment only sees account quota, the payment is disabled without merchant configuration',async()=>{
 const {ui,redirects}=factory({
  subscriptionCatalog:async()=>[{
    id:2,name:'Offre Flexible',audience:'institution',quota_unit:'accounts',is_active:true,
    prices:[{id:7,term_months:1,seats:100,amount:'30000',currency:'XOF',is_active:true}],
  }],
  subscriptionMine:async()=>({organisation_type:'institution',current:null,history:[]}),
  subscriptionCheckoutConfig:async()=>({enabled:false,provider:'cinetpay'}),
  subscriptionCheckoutOrders:async()=>[],
 },false);
 await ui.load();
 await ui.action({dataset:{subAction:'client-open',clientView:'checkout'}});
 const page=ui.clientPage();
 assert.match(page,/100 comptes actifs/);
 assert.doesNotMatch(page,/20 publications/);
 assert.match(page,/Paiement direct non encore activé/);
 assert.match(page,/Payer en ligne avec CinetPay →<\/button>/);
 await ui.action({dataset:{subAction:'start-checkout'}});
 assert.equal(redirects.length,0);
 await ui.action({dataset:{subAction:'client-switch-request'}});
 assert.match(ui.clientPage(),/data-sub-form="renewal-request"/);
});

test('E27 paid plans expose only authenticated portal access, with provider confirmation needed',async()=>{
 let status='pending',checks=0;
 const {ui}=factory({
  subscriptionCatalog:async()=>[],
  subscriptionMine:async()=>({organisation_type:'enterprise',current:null,history:[]}),
  subscriptionCheckoutConfig:async()=>({enabled:true}),
  subscriptionCheckoutOrders:async()=>[{
    transaction_id:'11111111-2222-3333-4444-555555555555',status,
    offer_name:'Publications',amount:'30000',currency:'XOF',
    term_months:6,capacity:20,quota_unit:'publications',
    checkout_url:status==='pending'?'https://checkout.cinetpay.com/payment/abc':null,
    access_url:status==='paid'?'https://gconnect.example.test/entreprise#subscription':null,
  }],
  subscriptionCheckoutVerify:async()=>{
    checks++;status='paid';return {status:'paid'};
  },
 },false);
 await ui.load();
 assert.match(ui.clientPage(),/Vérifier mon paiement/);
 assert.doesNotMatch(ui.clientPage(),/Accéder à mon espace/);
 await ui.action({dataset:{subAction:'verify-checkout',transactionId:'11111111-2222-3333-4444-555555555555'}});
 assert.equal(checks,1);
 assert.match(ui.clientPage(),/Accéder à mon espace/);
 assert.doesNotMatch(ui.clientPage(),/Vérifier mon paiement/);
});
