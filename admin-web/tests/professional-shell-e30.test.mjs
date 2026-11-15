import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Script} from 'node:vm';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const html=read('admin-connected-e19.html');
const css=read('professional-shell-e30.css');
const source=html.match(/<script>([\s\S]*?)<\/script>/)?.[1]||'';

test('E30 date and time are dynamic, larger and horizontally centered on the header',()=>{
  assert.match(html,/id="clock-date"/);
  assert.match(html,/id="clock-time"/);
  assert.match(source,/function updateProfessionalClock\(\)/);
  assert.match(source,/setInterval\(updateProfessionalClock,30_000\)/);
  assert.match(source,/window\.addEventListener\('focus',updateProfessionalClock\)/);
  assert.match(css,/#topbar-date\{/);
  assert.match(css,/position:absolute;left:47%;top:50%/);
  assert.match(css,/\.clock-time\{\s*font:850 16px/);
});

test('E30 sidebar identity is a keyboard accessible clickable profile shortcut with photo',()=>{
  assert.match(html,/<button class="sa-sidebar-identity" type="button" id="sidebar-profile-open"/);
  assert.match(html,/id="sidebar-profile-open"[^>]*aria-controls="professional-profile-dialog"/);
  assert.match(html,/class="sa-sidebar-avatar"/);
  assert.match(source,/\$\('sidebar-profile-open'\)\.addEventListener\('click',\(\)=>\$\('profile-open'\)\.click\(\)\)/);
  assert.match(source,/document\.querySelectorAll\('\.top-actions \.avatar,\.sa-sidebar-avatar'\)/);
  assert.match(source,/img\.className='professional-avatar-photo'/);
  assert.match(css,/\.sa-sidebar-identity:hover/);
  assert.match(css,/\.sa-sidebar-identity:focus-visible/);
});

test('E30 search opens central dialog from header, sidebar, and Ctrl+K',()=>{
  assert.match(html,/id="professional-search-dialog"/);
  assert.match(html,/id="professional-search-input"/);
  assert.match(html,/id="professional-search-results"/);
  assert.match(html,/id="module-search" readonly/);
  assert.match(source,/\$\('module-search'\)\.addEventListener\('click',\(\)=>openProfessionalSearch\('module-search'\)\)/);
  assert.match(source,/\$\('topbar-search-toggle'\)\.addEventListener\('click',\(\)=>openProfessionalSearch\('topbar-search-toggle'\)\)/);
  assert.match(source,/event\.ctrlKey\|\|event\.metaKey/);
  assert.match(source,/openProfessionalSearch\('topbar-search-toggle'\)/);
  assert.match(source,/professionalSearchDialog\.showModal\(\)/);
  assert.match(source,/professionalSearchDialog\.addEventListener\('close'/);
  assert.match(css,/\.professional-search-dialog::backdrop/);
});

test('E30 results show recent modules and suggestions without exposing other role routes',()=>{
  assert.match(source,/professionalSearchLinks=\[\.\.\.nav,\.\.\.commerce,\.\.\.secondary\]/);
  assert.match(source,/\.filter\(\(\[route\]\)=>allowedRoutes\.has\(route\)\)/);
  assert.match(source,/allowedRoutes\.has\(route\)/);
  assert.match(source,/professionalSearchHistoryKey='gconnect-recent-modules-'/);
  assert.match(source,/readProfessionalSearchHistory/);
  assert.match(source,/writeProfessionalSearchHistory/);
  assert.match(source,/Recherches récentes/);
  assert.match(source,/Suggestions pour votre espace/);
  assert.match(source,/localStorage\.removeItem\(professionalSearchHistoryKey\)/);
  assert.match(source,/if\(!allowedRoutes\.has\(route\)\|\|!pages\[route\]\)return/);
});

test('E30 palette supports dynamic filtering, keyboard navigation and no unsafe HTML from input',()=>{
  assert.match(source,/professionalSearchInput\.addEventListener\('input',renderProfessionalSearch\)/);
  assert.match(source,/searchNormalise/);
  assert.match(source,/event\.key==='ArrowDown'\|\|event\.key==='ArrowUp'/);
  assert.match(source,/event\.key==='Enter'/);
  assert.match(source,/button\.dataset\.searchRoute=route/);
  assert.match(source,/label\.textContent=title/);
  assert.match(source,/strong\.textContent=title/);
  assert.match(source,/heading\.appendChild\(label\)/);
  assert.match(css,/@media\(max-width:650px\)/);
  assert.doesNotThrow(()=>new Script(source));
});

test('E30 stylesheet is loaded after existing E28 and E29 visual system',()=>{
  const e28=html.indexOf('/professional-shell-e28.css');
  const e29=html.indexOf('/professional-shell-e29.css');
  const e30=html.indexOf('/professional-shell-e30.css');
  assert.ok(e28>=0&&e29>e28&&e30>e29);
});
