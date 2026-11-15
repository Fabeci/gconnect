import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const read=path=>readFileSync(new URL('../dist/'+path,import.meta.url),'utf8');

test('enterprise shell exposes only real professional modules',()=>{
  const html=read('admin-connected-e19.html');
  for(const route of ['offers','applications','publications','team','subscription','statistics','notifications','settings']){
    assert.ok(html.includes("['"+route+"',"),route);
  }
  assert.match(html,/GConnectEnterpriseE24/);
  assert.match(html,/enterprise-e24\.js/);
  assert.match(html,/enterprise-e24\.css/);
});
test('E24 module parses and uses MFA-scoped backend methods',()=>{
  const source=read('enterprise-e24.js');
  assert.doesNotThrow(()=>new Function(source));
  assert.match(source,/api\.enterpriseRequest/);
  assert.match(source,/\/backoffice\/enterprise\/offers\//);
  assert.match(source,/\/backoffice\/enterprise\/applications\//);
  assert.match(source,/\/backoffice\/enterprise\/publications\//);
  assert.doesNotMatch(source,/localStorage|sessionStorage/);
});
test('enterprise management API accepts only MFA-verified role',()=>{
  const source=read('etablissement-api.js');
  assert.match(source,/current\?\.profile\?\.role !== 'enterprise'/);
  assert.match(source,/tokenKind !== 'WebToken'/);
});
