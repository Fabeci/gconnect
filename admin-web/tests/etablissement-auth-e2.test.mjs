import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const js=readFileSync(new URL('../dist/etablissement.js',import.meta.url),'utf8');
const dashboard=readFileSync(new URL('../dist/etablissement.html',import.meta.url),'utf8');
const loginPage=readFileSync(new URL('../dist/etablissement-connexion.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../dist/etablissement-auth.css',import.meta.url),'utf8');

function loadLoggedOut(pathname){
 let html='';
 const root={set innerHTML(value){html=value},get innerHTML(){return html}};
 const location={pathname};
 const history={replaceState(_state,_title,url){location.pathname='/'+url}};
 const document={
  documentElement:{dataset:{}},
  title:'',
  getElementById(id){
   if(id==='gc-establishment-app')return root;
   if(id==='ea-login-form')return {addEventListener(){}};
   return null;
  },
  addEventListener(){}
 };
 const window={
  location,history,
  addEventListener(){},
  EstablishmentMotion:{preferenceChanged(){}},
  GConnectEstablishmentApi:{isConnected:()=>false,disconnect(){}}
 };
 runInNewContext(js,{window,document,matchMedia:()=>({matches:false,addEventListener(){}})});
 return {html,location,document};
}

test('an anonymous browser cannot see the establishment dashboard or menu',()=>{
 const {html,location,document}=loadLoggedOut('/etablissement.html');
 assert.equal(location.pathname,'/etablissement-connexion.html');
 assert.match(document.title,/Connexion Établissement/);
 assert.match(html,/id="ea-login-form"/);
 assert.match(html,/autocomplete="current-password"/);
 assert.doesNotMatch(html,/class="ea-sidebar"/);
 assert.doesNotMatch(html,/class="ea-metric"/);
 assert.doesNotMatch(html,/data-route="members"/);
});

test('direct opening of the login URL remains an unauthenticated login screen',()=>{
 const {html,location}=loadLoggedOut('/etablissement-connexion.html');
 assert.equal(location.pathname,'/etablissement-connexion.html');
 assert.match(html,/Accès sécurisé/);
 assert.match(html,/id="ea-password-visibility"/);
});

test('both URLs bootstrap the same gated application, with the E2 styles',()=>{
 for(const html of [dashboard,loginPage]){
  assert.match(html,/etablissement-api\.js/);
  assert.match(html,/etablissement\.js/);
  assert.match(html,/etablissement-auth\.css/);
 }
 assert.match(css,/\.ea-auth-card/);
 assert.match(js,/function clearLocalDrafts/);
 assert.match(js,/function endSession/);
 assert.match(js,/GConnectEstablishmentApi\.disconnect/);
 assert.match(js,/if\(!window\.GConnectEstablishmentApi\.isConnected\(\)\|\|!live\.profile\|\|!live\.stats\)/);
 assert.doesNotMatch(js,/localStorage|sessionStorage|document\.cookie/);
});