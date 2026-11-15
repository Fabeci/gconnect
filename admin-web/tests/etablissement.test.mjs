import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../dist/etablissement.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('../dist/etablissement.css', import.meta.url), 'utf8');
const cssGlass = readFileSync(new URL('../dist/etablissement-glass.css', import.meta.url), 'utf8');
const cssTokens = readFileSync(new URL('../dist/glass-tokens.css', import.meta.url), 'utf8');
const js = readFileSync(new URL('../dist/etablissement.js', import.meta.url), 'utf8');

test('la prévisualisation établissement utilise les assets officiels et Manrope', () => {
  assert.match(html, /\/assets\/logo_icon.png/);
  assert.match(html, /\/tokens\.css/);
  assert.match(html, /\/etablissement\.css/);
  assert.match(html, /\/etablissement\.js/);
  assert.match(cssTokens, /Manrope/);
  assert.match(cssTokens, /#3761FF/i);
});
test('les sept modules administratifs sont présents', () => {
  for (const page of ['overview','promotions','members','events','team','subscription','settings']) {
    assert.match(js, new RegExp('id:\\x27'+page+'\\x27'));
  }
});
test('la sidebar dispose d’un mode réduit avec loupe et d’un tiroir mobile', () => {
  assert.match(js, /ea-search-compact/);
  assert.match(js, /ea-open-menu/);
  assert.match(js, /ea-backdrop/);
  assert.match(cssGlass, /\.ea-shell\.is-collapsed/);
  assert.match(cssGlass, /\.ea-shell\.is-mobile-open/);
  assert.match(css + cssGlass, /prefers-reduced-motion/);
});
test('les vues ne simulent ni données métier réelles ni authentification', () => {
  assert.match(js, /Aucune donnée réelle n’est disponible/);
  assert.match(js, /Aucune activité à afficher/);
  assert.match(js, /Mode prévisualisation/);
  assert.doesNotMatch(js, /localStorage|sessionStorage|fetch\(|paymentIntent|authToken/);
});


test('chaque module propose une interface dédiée et des interactions de prévisualisation', () => {
  for (const view of ['promotions','members','events','team','subscription','settings']) {
    assert.match(js, new RegExp("function "+view+"\\(\\)"));
  }
  assert.match(js, /data-draft-form="promotions"/);
  assert.match(js, /data-draft-form="events"/);
  assert.match(js, /data-draft-form="team"/);
  assert.match(js, /id="ea-profile-form"/);
  assert.match(js, /data-plan="/);
  assert.match(js, /function bindPreviewActions/);
  assert.match(js, /function draftList/);
  assert.match(css, /\.ea-workspace/);
  assert.match(css, /\.ea-plan-grid/);
  assert.match(css, /\.ea-empty-state/);
});

test('les données saisies restent éphémères et sont échappées avant affichage', () => {
  assert.match(js, /const preview=/);
  assert.match(js, /function draftList/);
  assert.match(js, /safe\(item\.title\)/);
  assert.match(js, /safe\(item\.caption\)/);
  assert.match(js, /safe\(preview\.profile\.name\)/);
  assert.match(js, /e\.preventDefault\(\)/);
  assert.match(js, /reportValidity\(\)/);
  assert.doesNotMatch(js, /localStorage|sessionStorage|fetch\(|XMLHttpRequest/);
});

test('les factures et données personnelles ne sont jamais fictivement chargées', () => {
  assert.match(js, /Les listes nominatives ne sont jamais simulées/);
  assert.match(js, /Aucune facture/);
  assert.match(js, /Aucun abonnement actif/);
  assert.match(js, /les données autorisées|des données autorisées/i);
});

test('les composants administration conservent un layout explicite et compact', () => {
  for (const [selector, declaration] of [
    ['ea-sidebar', 'display:flex'],
    ['ea-search', 'display:flex'],
    ['ea-nav', 'display:grid'],
    ['ea-nav-item', 'display:flex'],
    ['ea-top', 'display:flex'],
    ['ea-top-actions', 'display:flex'],
    ['ea-hero', 'display:grid'],
    ['ea-actions', 'display:flex'],
    ['ea-grid', 'display:grid'],
    ['ea-twocol', 'display:grid']
  ]) {
    assert.match(cssGlass, new RegExp('\\.' + selector + '\\s*\\{[^}]*' + declaration, 's'));
  }
  assert.match(cssGlass, /\.ea-mobile-open\s*\{[^}]*display:none/s);
  assert.match(cssGlass, /\.ea-shell\.is-collapsed\s+\.ea-nav-text/);
  assert.doesNotMatch(js, /setInterval\(syncTheme,\s*1\)/);
});

test('le tableau de bord E1 montre uniquement les indicateurs autorisés par l’API', () => {
  assert.match(html, /\/etablissement-api\.js/);
  assert.match(js, /GConnectEstablishmentApi\.connect/);
  assert.match(js, /GConnectEstablishmentApi\.disconnect/);
  assert.match(js, /id="ea-login-form"/);
  assert.match(js, /stats\?\.promotions_count/);
  assert.match(js, /stats\?\.users\?\.students/);
  assert.match(js, /stats\?\.posts\?\.events/);
  assert.match(js, /role="alert"/);
  assert.doesNotMatch(js, /localStorage|sessionStorage|fetch\(/);
});
