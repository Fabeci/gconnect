import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = path => readFileSync(new URL('../dist/' + path, import.meta.url), 'utf8');
const rounded = read('admin-rounding-e13.css');
const establishment = read('etablissement.html');
const superadmin = read('superadmin-preview.html');

test('E13 rounding layer is loaded last on both admin pages',()=>{
  assert.match(establishment, /<link rel="stylesheet" href="\/auth\.css">\s*<link rel="stylesheet" href="\/admin-rounding-e13\.css">/);
  assert.match(superadmin, /<link rel="stylesheet" href="\/superadmin-premium\.css">\s*<link rel="stylesheet" href="\/admin-rounding-e13\.css">/);
  assert.equal((establishment.match(/admin-rounding-e13\.css/g)||[]).length,1);
  assert.equal((superadmin.match(/admin-rounding-e13\.css/g)||[]).length,1);
});

test('E13 shape tokens cover both spaces with responsive variants',()=>{
  assert.match(rounded,/html\[data-space="etablissement"\],\s*html\[data-space="superadmin"\]/);
  for(const name of ['shell','hero','surface','card','inset','nav','control','pill']){
    assert.match(rounded,new RegExp('--gc-r-'+name+':'));
  }
  assert.match(rounded,/@media\(max-width:900px\)/);
  assert.match(rounded,/@media\(max-width:600px\)/);
});

test('E13 covers the establishment whole journey including authentication',()=>{
  for(const selector of [
    '.ea-sidebar','.ea-top','.ea-hero','.ea-card','.ea-settings-grid>.panel',
    '.ea-nav-item','.ea-top-popover','.ea-auth-card','.ea-auth-story',
    '.ea-auth-form .ea-field input','.ea-logout','.ea-chart-bar','.ea-chip'
  ])assert.ok(rounded.includes(selector),selector);
});

test('E13 covers superadmin dashboard, commerce, settings and nested controls',()=>{
  for(const selector of [
    '.sidebar','.topbar','.nav-btn','.topbar-popover',
    '#view .panel','#view .kpi','#view .campus-hero',
    '#view .billing-tier','#view .billing-step','#view .sa-settings-grid>.panel',
    '#view .queue-item','#view .import-tile','#view .table-scroll',
    '#view button.smallbtn','#view .chart .bar','#view .badge'
  ])assert.ok(rounded.includes(selector),selector);
});

test('E13 does not flatten avatar circles, switches or the popover positioning',()=>{
  assert.match(rounded,/\.ea-avatar,[\s\S]*?\.ea-settings-avatar\{\s*border-radius:50%/);
  assert.match(rounded,/\.sa-sidebar-avatar\{\s*border-radius:50%/);
  assert.match(rounded,/\.ea-top,[\s\S]*?\.topbar\{\s*overflow:visible/);
  assert.ok((rounded.match(/\{/g)||[]).length===(rounded.match(/\}/g)||[]).length);
});
