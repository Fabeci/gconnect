import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Script} from 'node:vm';

const read=name=>readFileSync(new URL('../dist/'+name,import.meta.url),'utf8');
const html=read('admin-connected-e19.html');
const api=read('etablissement-api.js');
const mod=read('institutions-e31.js');
const styles=read('institutions-e31.css');
const identity=read('module-identities-e31.css');
const inline=html.match(/<script>([\s\S]*?)<\/script>/)?.[1]||'';

test('E31 academic module wired to Superadmin only and integrates with existing shell',()=>{
  assert.match(html,/src="\/institutions-e31\.js\?v=e31-campus-1"/);
  assert.match(html,/href="\/institutions-e31\.css\?v=e31-campus-1"/);
  assert.match(inline,/if\(isPlatformAdmin\)\{\s*academicE31=window.GConnectInstitutionDirectoryE31/);
  assert.match(inline,/pages\.etablissements=\(\)=>academicE31\.page\(\)/);
  assert.match(inline,/if\(isPlatformAdmin&&view==='etablissements'\)academicE31\?\.ensure\(\)/);
  assert.match(inline,/document\.documentElement\.dataset\.module=view/);
  assert.doesNotThrow(()=>new Script(inline));
});

test('E31 data comes from secured backend, without hard-coded fake school figures',()=>{
  assert.match(api,/const institutionsDirectory = params => \{/);
  assert.match(api,/commercialRequest\('\/backoffice\/institutions\/\?'\+query\.toString\(\),'GET',null,true\)/);
  assert.match(mod,/api\.institutionsDirectory\(\{/);
  assert.match(mod,/result\?\.results/);
  assert.match(mod,/result\?\.summary/);
  assert.doesNotMatch(mod,/schoolSeed|companySeed|Math\.random\(/);
  assert.match(mod,/Aucun établissement n’est enregistré dans le backend/);
});

test('E31 directory supports search, status, subscription, pagination, and detail',()=>{
  assert.match(mod,/data-e31-search/);
  assert.match(mod,/data-e31-filter="status"/);
  assert.match(mod,/data-e31-filter="billing"/);
  assert.match(mod,/data-e31-action="prev"/);
  assert.match(mod,/data-e31-action="next"/);
  assert.match(mod,/data-e31-action="detail"/);
  assert.match(mod,/id="e31-detail-dialog"/);
  assert.match(mod,/dlg\.showModal\(\)/);
  assert.match(mod,/go\('invitations'\)/);
  assert.match(mod,/go\('abonnements'\)/);
  assert.match(mod,/page_size:12/);
  assert.match(mod,/state\.loading/);
  assert.match(mod,/state\.error/);
  assert.doesNotThrow(()=>new Script(mod));
});

test('E31 special educational identity remains responsive and honors reduced motion',()=>{
  assert.match(styles,/\.e31-hero/);
  assert.match(styles,/\.e31-campus-visual/);
  assert.match(styles,/\.e31-companion/);
  assert.match(styles,/\.e31-school-row/);
  assert.match(styles,/\.e31-detail::backdrop/);
  assert.match(styles,/@media\(max-width:690px\)/);
  assert.match(styles,/@media\(prefers-reduced-motion:reduce\)/);
  assert.match(identity,/data-module="entreprises"/);
  assert.match(identity,/data-module="recruteurs"/);
  assert.match(identity,/data-module="utilisateurs"/);
  assert.match(identity,/data-module="abonnements"/);
  assert.match(identity,/data-module="facturation"/);
  assert.match(identity,/data-module="invitations"/);
  assert.match(identity,/data-module="contenus"/);
  assert.match(identity,/data-module="moderation"/);
  assert.match(identity,/data-module="imports"/);
  assert.match(identity,/data-module="statistiques"/);
  assert.match(identity,/data-module="audit"/);
  assert.match(identity,/data-module="sessions"/);
  assert.match(identity,/data-module="parametres"/);
});
