import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Script, runInNewContext } from 'node:vm';

const read = path => readFileSync(new URL('../dist/' + path, import.meta.url), 'utf8');
const establishmentHtml = read('etablissement.html');
const establishmentJs = read('etablissement.js');
const establishmentCss = read('etablissement-glass.css');
const superHtml = read('superadmin-preview.html');
const superCss = read('superadmin-premium.css');
const superSource = [...superHtml.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(Boolean);

test('E12 preserves both established navigation systems and authentic establishment protection', () => {
  for (const module of ['overview','promotions','members','events','team','subscription','settings']) {
    assert.match(establishmentJs, new RegExp("id:'" + module + "'"));
  }
  for (const id of ['primary-nav','commerce-nav','secondary-nav']) {
    assert.match(superHtml, new RegExp('id="' + id + '"'));
  }
  assert.match(establishmentJs, /!window\.GConnectEstablishmentApi\.isConnected\(\)\|\|!live\.profile\|\|!live\.stats/);
  assert.match(establishmentHtml, /\/etablissement-auth\.css/);
  assert.doesNotMatch(superSource, /fetch\s*\(/);
});

test('E12 blue active pills, pale secondary selections and dark variants are scoped per console', () => {
  assert.match(establishmentCss, /\.ea-nav-item\.active\s*\{\s*background:linear-gradient/);
  assert.match(establishmentCss, /\.ea-nav-item:not\(\.active\):hover/);
  assert.match(superCss, /\.nav-btn\.active\s*\{\s*color:#fff!important;background:linear-gradient/);
  assert.match(superCss, /\.nav-btn:not\(\.active\):hover/);
  assert.match(establishmentCss, /\[data-theme="dark"\] \.ea-nav-item\.active/);
  assert.match(superCss, /\[data-theme="dark"\] \.nav-btn\.active/);
});

test('E12 professional topbars offer search, theme, bell, profile and honest states', () => {
  for (const id of ['ea-quick-search','ea-theme-toggle','ea-notification-toggle','ea-profile-toggle','ea-theme']) {
    assert.match(establishmentJs, new RegExp('id="' + id + '"'));
  }
  for (const id of ['topbar-search-toggle','theme-toggle','notification-toggle','profile-toggle','theme-select']) {
    assert.match(superHtml, new RegExp('id="' + id + '"'));
  }
  assert.match(establishmentJs, /Aucune notification chargée/);
  assert.match(superHtml, /Aucune notification chargée/);
  assert.match(establishmentJs, /id="ea-signout-menu"/);
  assert.match(establishmentJs, /menuSignout\.onclick=endSession/);
  assert.match(establishmentJs, /e\.ctrlKey\|\|e\.metaKey/);
});

test('E12 coherent settings do not claim to change production security or notifications', () => {
  assert.match(establishmentJs, /class="ea-settings-grid"/);
  assert.match(establishmentJs, /id="ea-reduce-motion"/);
  assert.match(establishmentJs, /data-appearance=/);
  assert.match(establishmentJs, /id="ea-toggle-settings"/);
  assert.match(establishmentJs, /aria-label="Notifications d’affiliation bientôt disponibles" disabled/);
  assert.match(superSource, /function settingsPage\(/);
  assert.match(superSource, /data-preview-theme=/);
  assert.match(superSource, /data-setting=/);
  assert.match(superSource, /La MFA réelle reste obligatoire/);
});

test('E12 chart motion uses actual establishment counts and respects reduced motion', () => {
  assert.match(establishmentJs, /const students=users\?\.students,alumni=users\?\.alumni/);
  assert.match(establishmentJs, /Number\.isFinite\(students\)/);
  assert.match(establishmentJs, /function communityChart\(/);
  assert.match(establishmentCss, /@keyframes ea-chart-rise/);
  assert.match(establishmentCss, /prefers-reduced-motion/);
  assert.match(superSource, /function trendChart\(/);
  assert.match(superCss, /@keyframes sa-trend-draw/);
  assert.match(superCss, /html\[data-motion="off"\] \.sa-trend-line/);
});

test('E12 JavaScript is syntactically valid and all 15 Superadmin preview views render', () => {
  assert.doesNotThrow(() => new Script(superSource));
  assert.doesNotThrow(() => new Script(establishmentJs));
  const routes = ['dashboard','etablissements','entreprises','recruteurs','utilisateurs','abonnements','facturation','invitations','contenus','moderation','imports','statistiques','audit','sessions','parametres'];
  for (const route of routes) {
    const elements = new Map();
    const el = id => {
      if (!elements.has(id)) elements.set(id, {
        innerHTML:'',textContent:'',value:'',dataset:{},
        hidden:id.endsWith('-popover'),handlers:{},
        classList:{add(){},remove(){},contains(){return false},toggle(){}},
        addEventListener(type,handler){this.handlers[type]=handler},
        setAttribute(name,value){this[name]=value},
        querySelectorAll(){return[]},focus(){}
      });
      return elements.get(id);
    };
    const document = {
      body:{innerHTML:'',classList:{contains(){return false}}},
      documentElement:{dataset:{},classList:{add(){},remove(){}},offsetWidth:0},
      getElementById:el,querySelectorAll(){return[]},addEventListener(){}
    };
    runInNewContext(superSource, {
      location:{hostname:'127.0.0.1',hash:'#'+route},
      window:{addEventListener(){},scrollTo(){}},
      document,setTimeout(){},clearTimeout(){}
    });
    assert.ok(el('view').innerHTML.length > 350,route);
    if (route === 'parametres') assert.match(el('view').innerHTML,/settings-appearance-choices/);
    if (route === 'statistiques') assert.match(el('view').innerHTML,/sa-trend-svg/);
  }
});
