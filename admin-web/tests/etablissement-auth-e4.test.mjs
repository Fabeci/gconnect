import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = name => readFileSync(new URL('../dist/' + name, import.meta.url), 'utf8');
const auth = read('auth.js');
const api = read('etablissement-api.js');
const activation = read('etablissement-activation.html');
const controller = read('etablissement.js');
const css = read('auth.css');

test('invitation activation is reachable from the backend emailed link', () => {
  assert.match(activation, /id="gc-establishment-app"/);
  assert.match(activation, /etablissement-api\.js/);
  assert.match(activation, /auth\.js/);
  assert.match(activation, /etablissement\.js/);
  assert.match(auth, /#invitation=/);
  assert.match(auth, /history\.replaceState\(null,'',location\.pathname\)/);
  assert.match(auth, /api\.previewInvitation\(inviteToken\)/);
  assert.match(auth, /api\.acceptInvitation\(inviteToken/);
  assert.doesNotMatch(auth, /activation des invitations n’est pas encore disponible/i);
});

test('protected web login implements password, MFA and recovery steps', () => {
  assert.match(auth, /api\.startPrivilegedLogin\(email,data\.password\)/);
  assert.match(auth, /api\.beginMfaSetup\(challenge\)/);
  assert.match(auth, /api\.finishMfa\(challenge/);
  assert.match(auth, /case 'mfa-recovery'/);
  assert.match(auth, /recoveryCodes=\[\]/);
  assert.match(css, /\.auth-recovery/);
  assert.match(api, /Authorization = scheme \+ ' ' \+ authToken/);
  assert.match(api, /tokenKind = 'WebToken'/);
  assert.match(api, /\/users\/web-logout\//);
  assert.doesNotMatch(api, /(?:localStorage|sessionStorage)\s*\.\s*(?:setItem|getItem)|document\.cookie\s*=/);
});

test('Superadmin can create/list/revoke an invitation only after MFA', () => {
  assert.match(auth, /id="auth-invite-form"/);
  assert.match(auth, /api\.sendInvitation\(/);
  assert.match(auth, /api\.listInvitations\(/);
  assert.match(auth, /api\.revokeInvitation\(/);
  assert.match(api, /current\?\.profile\?\.role !== 'superAdmin'/);
  assert.match(api, /\['etablissement', 'superAdmin', 'enterprise'\]/);
});

test('establishment dashboard mounts only after successful MFA callback', () => {
  assert.match(controller, /GConnectAuth\.mount\(root, async \(result\)/);
  assert.match(controller, /live\.profile=result\.profile;live\.stats=result\.stats/);
  assert.match(api, /async function connect\(email, password\) \{\s*return startPrivilegedLogin\(email, password\)/);
});
