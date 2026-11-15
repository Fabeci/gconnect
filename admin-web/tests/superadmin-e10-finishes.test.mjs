import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const styles = readFileSync(new URL('../dist/superadmin-premium.css', import.meta.url), 'utf8');
const preview = readFileSync(new URL('../dist/superadmin-preview.html', import.meta.url), 'utf8');

test('E10 hero shares a continuous painted surface without a hard division', () => {
  assert.match(styles, /E10 — Finitions de la console/);
  assert.match(styles, /\.campus-hero\s*\{\s*background:linear-gradient/);
  assert.match(styles, /\.campus-hero \.hero-network\s*\{\s*background:transparent/);
  assert.match(styles, /\.campus-hero \.hero-network::after\s*\{background:none\}/);
});

test('E10 controls provide consistent focus, checkbox, search and date polish', () => {
  for (const selector of ['input[type="checkbox"]', 'input[type="date"]', '.filters .search', '.sidebar-search:focus-within', '.switch:focus-visible']) {
    assert.ok(styles.includes(selector), selector);
  }
  assert.match(styles, /accent-color:#3761ff/);
  assert.match(styles, /input::placeholder/);
});

test('E10 night theme covers structural surfaces and dense content', () => {
  assert.match(styles, /#16243b/);
  for (const selector of ['.sidebar', '.topbar', '.panel', '.campus-hero', '.filters input', '.field label', '.table th', '.queue-item p', '.billing-tier', '.billing-step', '.nav-btn.active', '.badge.pending']) {
    assert.ok(styles.includes(selector), selector);
  }
  assert.match(styles, /\.queue-item:hover\{background:rgba\(95,128,180,\.2\)!important\}/);
});

test('E10 remains a visual preview with motion and local-only safety unchanged', () => {
  assert.match(preview, /localhost.*127\.0\.0\.1/);
  assert.match(preview, /superadmin-motion\.js/);
  assert.match(styles, /sa-reveal/);
  assert.doesNotMatch(styles, /animation:\s*none\s*!important\s*;?\s*\/\* E10/);
});
