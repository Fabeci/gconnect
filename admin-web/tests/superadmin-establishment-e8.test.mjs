import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Script } from 'node:vm';
import { runInNewContext } from 'node:vm';

const html = readFileSync(new URL('../dist/superadmin-preview.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('../dist/superadmin-establishment-theme.css', import.meta.url), 'utf8');
const premium = readFileSync(new URL('../dist/superadmin-premium.css', import.meta.url), 'utf8');
const motion = readFileSync(new URL('../dist/superadmin-motion.js', import.meta.url), 'utf8');

test('le Superadmin reprend les marqueurs visuels de la maquette Établissement', () => {
  assert.match(html, /superadmin-establishment-theme\.css/);
  assert.match(html, /assets\/logo\.png/);
  assert.match(html, /assets\/logo_icon\.png/);
  assert.match(html, /assets\/hero-gconnect\.jpg/);
  assert.match(css, /\.campus-hero\s*\{/);
  assert.match(css, /\.sidebar\s*\{/);
  assert.match(css, /backdrop-filter:blur/);
  assert.match(css, /prefers-reduced-motion:reduce/);
});

test('les quinze sections couvrent les fonctions métier et les futures vues commerciales', () => {
  const routes = [
    'dashboard', 'etablissements', 'entreprises', 'recruteurs',
    'utilisateurs', 'abonnements', 'facturation', 'invitations', 'contenus', 'moderation',
    'imports', 'statistiques', 'audit', 'sessions', 'parametres',
  ];
  const pages = html.match(/const pages=([^;]+);\s*function closeMenu/)?.[1] ?? '';
  for (const route of routes) {
    assert.match(pages, new RegExp(`(?:^|\\{|,)${route}:`), `page manquante : ${route}`);
  }
  const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(match => match[1]).find(Boolean);
  assert.ok(script);
  assert.doesNotThrow(() => new Script(script));
});

test('le bandeau Superadmin a sa propre identité visuelle réseau', () => {
  assert.match(html, /function dashboardV3\(/);
  assert.match(html, /hero-network/);
  assert.match(html, /network-node node-school/);
  assert.match(html, /network-node node-business/);
  assert.match(html, /network-node node-recruiter/);
  assert.match(css, /\.network-center\{/);
  assert.match(css, /\.network-orbit\{/);
});

test('les animations Établissement sont reprises avec les mêmes durées', () => {
  assert.match(html, /superadmin-motion\.js/);
  assert.match(html, /SuperadminMotion\?\.afterRender\(\)/);
  assert.match(motion, /IntersectionObserver/);
  assert.match(motion, /threshold:0\.1, rootMargin:'0px 0px -50px 0px'/);
  assert.match(motion, /\(i % 6\) \* 30/);
  assert.match(motion, /element\.style\.animationDelay/);
  assert.match(motion, /createRipple/);
  assert.match(motion, /initMagnetic/);
  assert.match(motion, /initParallax/);
  assert.match(motion, /initAmbient/);
  assert.match(css, /--sa-duration-entrance:600ms/);
  assert.match(css, /--sa-duration-slower:480ms/);
  assert.match(css, /ripple-anim 500ms/);
  assert.match(css, /ambient-drift 20s/);
  assert.doesNotThrow(() => new Script(motion));
});

test('la comparaison reste locale et ne contourne pas MFA', () => {
  assert.match(html, /localhost.*127\.0\.0\.1/);
  assert.match(html, /etablissement\.html#login\/superadmin/);
  assert.match(html, /Aucune connexion, aucune API et aucune donnée réelle/);
  assert.match(html, /key==='mfa'/);
  assert.doesNotMatch(html, /fetch\s*\(/);
  assert.doesNotMatch(html, /localStorage\./);
});

test('navigation responsive, recherche de modules, thème et sidebar réduite', () => {
  assert.match(html, /id="module-search"/);
  assert.match(html, /id="theme-select"/);
  assert.match(html, /id="collapse-toggle"/);
  assert.match(css, /\.sidebar-collapsed/);
  assert.match(css, /max-width:850px/);
  assert.match(css, /max-width:600px/);
  assert.match(css, /data-theme="dark"/);
  assert.match(html, /id="commerce-nav"/);
  assert.match(html, /superadmin-premium\.css/);
  assert.match(premium, /\.command-strip/);
  assert.match(premium, /\.command-link:hover/);
  assert.match(premium, /max-width:680px/);
});

test('les animations touchent cartes, indicateurs, lignes, formulaires et facturation', () => {
  for (const selector of ['.kpi', '.queue-item', '.quick', '.table tbody tr', '.field', '.switch', '.billing-tier', '.billing-step']) {
    assert.ok(motion.includes(selector), `élément non pris en charge : ${selector}`);
  }
  assert.match(css, /sa-icon-breathe 4\.8s/);
  assert.match(css, /\.billing-tier:hover/);
  assert.match(css, /#view \.panel:hover/);
  assert.match(html, /id="motion-select"/);
  assert.match(html, /Animations actives/);
  assert.match(motion, /dataset\.motion !== 'on'/);
});

test('une page Abonnements montre le cycle paiement vérifié puis invitation sans transaction fictive', () => {
  assert.match(html, /\['abonnements','Abonnements','billing'\]/);
  assert.match(html, /abonnements:subscriptionsPage/);
  const source = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(m => m[1]).find(Boolean);
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      innerHTML:'', textContent:'', value:'', dataset:{},
      classList:{add(){},remove(){},toggle(){},contains(){return false}},
      setAttribute(){}, addEventListener(){}, querySelectorAll(){return []},
    });
    return elements.get(id);
  };
  const context = {
    location:{hostname:'127.0.0.1',hash:'#abonnements'},
    document:{body:{innerHTML:''},getElementById:element,querySelectorAll(){return []},
      documentElement:{dataset:{}}},
    window:{addEventListener(){}},setTimeout(){},clearTimeout(){},
  };
  runInNewContext(source,context);
  const page = element('view').innerHTML;
  assert.match(page, /Abonnements & facturation/);
  assert.match(page, /Confirmer côté serveur/);
  assert.match(page, /Inviter & activer/);
  assert.match(page, /aucune somme n’est encaissée/);
  assert.match(page, /aucun paiement n’est initié/);
  assert.match(element('commerce-nav').innerHTML, /Abonnements/);
  assert.match(element('commerce-nav').innerHTML, /Factures & paiements/);
  assert.match(page, /6 mois/);
  assert.match(page, /12 mois/);
  assert.doesNotMatch(source, /fetch\s*\(/);
});

test('la page Facturation ne déclenche aucun paiement et affiche ses contrôles serveur', () => {
  assert.match(html, /function facturationPage\(/);
  assert.match(html, /Paiements confirmés/);
  assert.match(html, /Validation contrôlée/);
  assert.match(html, /aucune transaction/i);
  assert.match(motion, /function animateKpis\(/);
  assert.match(motion, /850/);
  assert.match(motion, /\.command-link/);
  assert.match(premium, /animation-play-state:paused/);
});

test('les quinze routes affichent un contenu sans erreur JavaScript', () => {
  const source = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(match => match[1]).find(Boolean);
  const routes = [
    'dashboard','etablissements','entreprises','recruteurs','utilisateurs',
    'abonnements','facturation','invitations','contenus','moderation','imports',
    'statistiques','audit','sessions','parametres',
  ];
  for (const route of routes) {
    const elements = new Map();
    const element = id => {
      if (!elements.has(id)) elements.set(id,{
        innerHTML:'',textContent:'',value:'',dataset:{},
        classList:{add(){},remove(){},toggle(){},contains(){return false}},
        setAttribute(){},addEventListener(){},querySelectorAll(){return []},
      });
      return elements.get(id);
    };
    const context = {
      location:{hostname:'127.0.0.1',hash:`#${route}`},
      document:{body:{innerHTML:''},getElementById:element,querySelectorAll(){return []},
        documentElement:{dataset:{}}},
      window:{addEventListener(){}},setTimeout(){},clearTimeout(){},
    };
    assert.doesNotThrow(()=>runInNewContext(source,context),`Route cassée : ${route}`);
    const rendered = element('view').innerHTML;
    assert.ok(rendered.length>350,`Écran vide : ${route}`);
    assert.match(element('crumb-name').textContent,/\S/);
    assert.ok(
      element('primary-nav').innerHTML.includes(`data-route="${route}"`)
      || element('commerce-nav').innerHTML.includes(`data-route="${route}"`)
      || element('secondary-nav').innerHTML.includes(`data-route="${route}"`),
      `Navigation manquante : ${route}`,
    );
  }
});
