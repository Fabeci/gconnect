import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = name => readFileSync(new URL('../dist/' + name, import.meta.url), 'utf8');
const css = read('auth-premium-e14.css');
const js = read('auth.js');
const entries = ['auth.html']; // E16 admin entry points have their own composition.

test('E14 stylesheet loads after the existing auth skin across all entry points', () => {
  for (const page of entries) {
    const html = read(page);
    assert.match(html, /<link rel="stylesheet" href="\/auth-premium-e14\.css">/);
    assert.equal((html.match(/auth-premium-e14\.css/g) || []).length, 1);
    assert.ok(html.indexOf('auth-premium-e14.css') > html.indexOf('auth.css'), page);
    if (page === 'etablissement.html') {
      assert.ok(html.indexOf('auth-premium-e14.css') > html.indexOf('admin-rounding-e13.css'));
    }
  }
});

test('the photographic story is immersive rather than a detached blue pane', () => {
  assert.match(css, /\.auth-shell \.auth-photo\{\s*position:absolute;/);
  assert.match(css, /inset:0;\s*width:100%;\s*height:100%;/);
  assert.match(css, /\.auth-shell \.auth-story::before\{/);
  assert.match(css, /background:linear-gradient\(180deg,/);
  assert.match(css, /\.auth-shell \.auth-photo img\{/);
  assert.match(css, /object-position:center 24%/);
  assert.match(css, /\.auth-shell \.auth-card\{[\s\S]*?border-radius:40px;/);
});

test('the rounded visual system reaches every step and field', () => {
  for (const component of ['auth-header','auth-story','auth-note','auth-card','auth-role',
    'auth-field','auth-password','auth-recovery','auth-session','auth-status',
    'auth-alert','auth-invites','auth-check','auth-steps']) {
    assert.ok(css.includes('.'+component), component);
  }
  for (const state of ['welcome','login','invitation','activate','activated',
    'mfa-setup','mfa-verify','mfa-recovery','forgot','reset','verify','verified',
    'register','details','credentials','pending','session','logout','signedout']) {
    assert.ok(js.includes("'" + state + "'"), 'Auth state '+state);
  }
});

test('dark theme, keyboard focus, mobile and reduced motion remain supported', () => {
  assert.match(css, /html\[data-theme="dark"\] \.auth-shell\{/);
  assert.match(css, /@media\(max-width:800px\)/);
  assert.match(css, /@media\(max-width:520px\)/);
  assert.match(css, /@media\(prefers-reduced-motion:reduce\)/);
  assert.match(css, /\.auth-shell \.auth-card :focus-visible/);
  assert.match(js, /id="auth-theme-toggle"/);
  assert.match(js, /aria-pressed/);
  assert.match(js, /localStorage\.setItem\('gconnect_auth_theme',next\)/);
});

test('account eligibility and second factor remain server-driven', () => {
  assert.match(js, /const api = window\.GConnectEstablishmentApi;/);
  assert.match(js, /api\.previewInvitation\(inviteToken\)/);
  assert.match(js, /api\.sendInvitation\(/);
  assert.match(js, /api\.listInvitations\(/);
  assert.match(js, /const roles = \{/);
  assert.match(js, /accepts:\['superAdmin'\]/);
  assert.match(js, /accepts:\['etablissement'\]/);
  assert.match(js, /mfa-verify/);
  assert.doesNotMatch(js, /localStorage\.setItem\([^)]*(?:token|session)/);
});

test('style sheet braces are balanced', () => {
  assert.equal((css.match(/\{/g) || []).length, (css.match(/\}/g) || []).length);
});
