import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (name) => readFileSync(new URL('../dist/' + name, import.meta.url), 'utf8');
const html = read('etablissement.html');
const js = read('etablissement.js');
const css = read('etablissement-motion-polish.css');

test('E5 visual motion stays isolated to the original establishment portal', () => {
  assert.match(html, /\/etablissement-motion-polish\.css/);
  assert.match(html, /\/etablissement-api\.js/);
  assert.match(html, /\/auth\.js/);
  assert.match(js, /GConnectEstablishmentApi\.isConnected\(\)/);
  assert.match(js, /GConnectAuth\.mount\(root/);
  assert.doesNotMatch(js, /localStorage|sessionStorage|fetch\(/);
  assert.match(css, /data-space="etablissement"/);
});

test('E5 icon set and interactions are lightweight and accessible', () => {
  for (const icon of ['home','layers','people','calendar','shield','receipt','settings','menu','search','close','collapse','expand','arrow']) {
    assert.match(js, new RegExp('\\b' + icon + ":'<"));
  }
  assert.match(js, /class="ea-icon"/);
  assert.match(css, /focus-visible/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /data-reduced-motion="true"/);
  assert.match(js, /document\.startViewTransition/);
  assert.match(js, /appearance!==value/);
});
