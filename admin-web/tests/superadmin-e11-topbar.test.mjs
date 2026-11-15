import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Script, runInNewContext } from 'node:vm';

const html = readFileSync(new URL('../dist/superadmin-preview.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('../dist/superadmin-premium.css', import.meta.url), 'utf8');
const source = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).find(Boolean);

function mount(route='dashboard'){
  const elements=new Map();
  const el=id=>{
    if(!elements.has(id))elements.set(id,{
      id,innerHTML:'',textContent:'',value:'',dataset:{},
      hidden:id.endsWith('-popover'),handlers:{},
      classList:{add(){},remove(){},contains(){return false},toggle(){return false}},
      addEventListener(type,handler){this.handlers[type]=handler},
      setAttribute(name,value){this[name]=value},
      focus(){this.focused=true},querySelectorAll(){return []},
    });
    return elements.get(id);
  };
  const document={
    body:{innerHTML:'',classList:{contains(){return false}}},
    getElementById:el,querySelectorAll(){return []},
    documentElement:{dataset:{},classList:{add(){},remove(){}},offsetWidth:0},
    addEventListener(){},
  };
  const context={
    location:{hostname:'127.0.0.1',hash:'#'+route},
    document,window:{addEventListener(){},scrollTo(){}},
    setTimeout(){},clearTimeout(){},
  };
  runInNewContext(source,context);
  return {el,document};
}

test('E11 topbar keeps notifications, profile, date and theme without demo clutter',()=>{
  assert.ok(source);
  assert.doesNotThrow(()=>new Script(source));
  for(const id of ['topbar-date','theme-toggle','notification-toggle','notification-popover','profile-toggle','profile-popover','topbar-search-toggle','motion-select','theme-select']){
    assert.match(html,new RegExp('id="'+id+'"'),id);
  }
  const header=html.match(/<header class="topbar">([\s\S]*?)<\/header>/)?.[1]??'';
  assert.doesNotMatch(header, /<span class="preview-pill">● APERÇU LOCAL<\/span>/);
  assert.match(header, /id="profile-popover"[^]*?APERÇU LOCAL/);
  assert.match(header,/class="[^"]*\bprofile-popover\b[^"]*"/);
  assert.match(header,/Connexion réelle/);
  assert.match(css,/\.topbar-popover\[hidden\]/);
});

test('E11 navigation and topbar run on all fifteen preview routes',()=>{
  const routes=['dashboard','etablissements','entreprises','recruteurs','utilisateurs','abonnements','facturation','invitations','contenus','moderation','imports','statistiques','audit','sessions','parametres'];
  for(const route of routes){
    const {el}=mount(route);
    assert.ok(el('view').innerHTML.length>300,route);
    assert.match(el('topbar-date').textContent,/\d/);
    assert.ok(el('crumb-name').textContent.length>0);
  }
});

test('E11 theme and popovers respond without backend calls or fake notifications',()=>{
  const {el,document}=mount();
  el('theme-toggle').handlers.click();
  assert.equal(document.documentElement.dataset.theme,'dark');
  assert.equal(el('theme-select').value,'dark');
  el('notification-toggle').handlers.click();
  assert.equal(el('notification-popover').hidden,false);
  el('profile-toggle').handlers.click();
  assert.equal(el('notification-popover').hidden,true);
  assert.equal(el('profile-popover').hidden,false);
  assert.match(html,/Aucune notification chargée/);
  assert.doesNotMatch(source,/fetch\s*\(/);
});

test('E11 dark mode repairs inherited bright selection and popover contrast',()=>{
  assert.match(css,/data-theme="dark"\] \.nav-btn::before/);
  assert.match(css,/data-theme="dark"\] #view \.queue-item:hover \.bubble/);
  assert.match(css,/data-theme="dark"\] \.topbar-popover/);
  assert.match(css,/sa-network-breathe-night/);
});
