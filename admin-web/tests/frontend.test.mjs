import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8');
const js = readFileSync(new URL('../dist/glass-app.js', import.meta.url), 'utf8');
const css = readFileSync(new URL('../dist/glass.css', import.meta.url), 'utf8');
const tokens = readFileSync(new URL('../dist/glass-tokens.css', import.meta.url), 'utf8');

test('la page charge le thème glassmorphism premium', () => {
  assert.match(html, /href="\/glass-tokens\.css"/);
  assert.match(html, /href="\/glass\.css"/);
  assert.match(html, /src="\/glass-app\.js"/);
});

test('les tokens de design glassmorphism sont présents', () => {
  assert.match(tokens, /--brand:\s*#3761FF/);
  assert.match(tokens, /--glass-1/);
  assert.match(tokens, /--blur-xl/);
  assert.match(tokens, /--ease-spring/);
  assert.match(tokens, /--duration-entrance/);
  assert.match(tokens, /--stagger/);
});

test('les animations d\'entrée et stagger sont définies', () => {
  assert.match(css, /@keyframes entrance-fade-up/);
  assert.match(css, /\.stagger-children/);
  assert.match(css, /\.reveal/);
  assert.match(css, /animation-delay:/);
});

test('le glassmorphism avancé est implémenté', () => {
  assert.match(tokens, /--blur-lg:\s*blur\(24px\)/);
  assert.match(tokens, /--blur-xl:\s*blur\(32px\)/);
  assert.match(css, /var\(--blur-lg\)/);
  assert.match(css, /var\(--blur-xl\)/);
  assert.match(css, /linear-gradient\(145deg/);
  assert.match(css, /inset 0 1px/);
});

test('la sidebar conserve le verre dépoli et le mode mobile', () => {
  assert.match(css, /\.sidebar\s*\{/);
  assert.match(css, /backdrop-filter:/);
  assert.match(css, /@media\s*\(max-width:\s*720px\)/);
  assert.match(css, /\.shell\.mobile-open/);
  assert.match(js, /mobile-menu/);
  assert.match(js, /search-trigger/);
  assert.match(js, /collapse/);
});

test('le hero utilise une photo locale et des angles arrondis', () => {
  assert.match(js, /hero-gconnect\.jpg/);
  assert.match(css, /\.hero\s*\{[\s\S]*?border-radius:/);
  assert.match(css, /\.hero-photo/);
});

test('les cartes opportunités ont des badges entreprises colorés', () => {
  assert.match(css, /\.company-badge/);
  assert.match(css, /linear-gradient\(135deg/);
  assert.match(js, /company-badge/);
});

test('les parcours principaux restent présents', () => {
  for (const page of ['home','jobs','network','school','messages','profile','settings']) {
    assert.match(js, new RegExp(page));
  }
});

test('les interactions avancées sont implémentées', () => {
  assert.match(js, /AnimationEngine/);
  assert.match(js, /createRipple/);
  assert.match(js, /initMagnetic/);
  assert.match(js, /initScrollReveal/);
  assert.match(js, /initParallax/);
  assert.match(js, /IntersectionObserver/);
});

test('le thème supporte le mode sombre et reduced-motion', () => {
  assert.match(tokens, /@media \(prefers-color-scheme: dark\)/);
  assert.match(tokens, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
});