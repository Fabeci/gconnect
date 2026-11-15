import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const page=read('admin-connected-e19.html');
const e31=read('institutions-e31.js');
const e32=read('enterprises-e32.js');
const css=read('floating-hero-e33.css');

test('E33 layout override loads after both existing modules and remains scoped',()=>{
  const e31Styles=page.indexOf('/institutions-e31.css?v=');
  const e32Styles=page.indexOf('/enterprises-e32.css?v=');
  const e33Styles=page.indexOf('/floating-hero-e33.css?v=');
  assert.ok(e31Styles>0 && e32Styles>0 && e33Styles>e31Styles && e33Styles>e32Styles);
  assert.match(css,/\.e31-page \.e31-hero,/);
  assert.match(css,/\.e32-page \.e32-hero/);
  assert.doesNotMatch(css,/#view\s*\{|\.sidebar\s*\{|\.topbar\s*\{/);
});

test('E33 removes colored rectangular hero blocks while retaining circular artwork',()=>{
  assert.match(css,/border:\s*0;/);
  assert.match(css,/border-radius:\s*0;/);
  assert.match(css,/background:\s*transparent;/);
  assert.match(css,/box-shadow:\s*none;/);
  assert.match(css,/\.e31-page \.e31-campus-visual/);
  assert.match(css,/\.e31-page \.e31-campus-orbit\.orbit-one/);
  assert.match(css,/\.e31-page \.e31-campus-node/);
  assert.match(css,/\.e32-page \.e32-network-art/);
  assert.match(css,/\.e32-page \.e32-network-ring/);
  assert.match(css,/\.e32-page \.e32-network-item/);
  assert.match(css,/radial-gradient\(ellipse at center/);
  assert.match(css,/\.e32-page \.e32-hero h1\s*\{[^}]*color:\s*#283d75/);
  assert.match(css,/\.e32-page \.e32-hero p\s*\{[^}]*color:\s*#7b8cae/);
});

test('E33 retains action buttons, figures, search tools, modals and business quotas',()=>{
  assert.match(e31,/data-e31-action="invite"/);
  assert.match(e31,/data-e31-action="refresh"/);
  assert.match(e31,/e31-metrics/);
  assert.match(e31,/data-e31-search/);
  assert.match(e31,/id="e31-detail-dialog"/);
  assert.match(e32,/data-e32-action="invite"/);
  assert.match(e32,/data-e32-action="refresh"/);
  assert.match(e32,/e32-stats/);
  assert.match(e32,/data-e32-search/);
  assert.match(e32,/id="e32-detail-dialog"/);
  assert.match(e32,/CRÉDITS DE PUBLICATION/);
});

test('E33 mobile view is content-first; reduced-motion setting is honored',()=>{
  assert.match(css,/@media \(max-width: 900px\)/);
  assert.match(css,/\.e31-page \.e31-campus-visual,\s*\.e32-page \.e32-network-art \{ display: none; \}/);
  assert.match(css,/@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css,/\.e31-page \.e31-campus-core,\s*\.e32-page \.e32-network-central \{ animation: none; \}/);
});
