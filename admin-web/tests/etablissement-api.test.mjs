import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../dist/etablissement-api.js', import.meta.url), 'utf8');

function createHarness(responder, location = { protocol: 'http:', hostname: '127.0.0.1', href: 'http://127.0.0.1:8086/' }) {
  const calls = [];
  const browser = {
    location,
    localStorage: new Proxy({}, {
      get() { throw new Error('Persistent token storage is forbidden'); },
      set() { throw new Error('Persistent token storage is forbidden'); },
    }),
    sessionStorage: new Proxy({}, {
      get() { throw new Error('Persistent token storage is forbidden'); },
      set() { throw new Error('Persistent token storage is forbidden'); },
    }),
  };
  const scope = {
    window: browser, document: { querySelector: () => null }, AbortController, URL, setTimeout, clearTimeout,
    fetch: async (url, options) => {
      calls.push({ url, options });
      const result = await responder(url, options);
      return { ok: result.status < 400, status: result.status, json: async () => result.body };
    },
  };
  runInNewContext(source, scope, { filename: 'etablissement-api.js' });
  return { api: browser.GConnectEstablishmentApi, calls };
}
const ok = data => ({ status: 200, body: { success: true, data } });

test('establishment credentials start an MFA challenge without issuing a session', async () => {
  const { api, calls } = createHarness(url => {
    assert.match(url, /\/users\/web-login\/$/);
    return ok({ challenge: 'private-pre-auth-challenge', mfa_required: true, mfa_action: 'enroll', email: 'admin@example.test' });
  });
  const step = await api.connect('admin@example.test', 'safe-password');
  assert.equal(step.action, 'enroll');
  assert.equal(step.challenge, 'private-pre-auth-challenge');
  assert.equal(api.isConnected(), false);
  assert.equal(api.getCurrent(), null);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].options.headers.Authorization, undefined);
  assert.equal(calls[0].options.credentials, 'omit');
});

test('TOTP enrollment and verification unlock only the institution-scoped dashboard', async () => {
  const { api, calls } = createHarness((url, options) => {
    if (url.endsWith('/web-login/')) return ok({ mfa_required: true, challenge: 'challenge', mfa_action: 'enroll' });
    if (url.endsWith('/web-mfa/setup/')) return ok({ secret: 'SHARED-SECRET', otpauth_uri: 'otpauth://totp/name', expires_at: '2026-10-24T14:00:00Z' });
    if (url.endsWith('/web-mfa/verify/')) return ok({ token: 'web-secret', token_type: 'WebToken', role: 'etablissement', recovery_codes: ['ONE', 'TWO'] });
    if (url.endsWith('/users/me/')) return ok({ role: 'etablissement', institution_id: 18 });
    if (url.endsWith('/backoffice/stats/')) return ok({ scope: 'institution', users: { students: 2 }, posts: { events: 0 } });
    if (url.endsWith('/web-logout/')) return ok({});
    throw new Error('Unexpected ' + url);
  });
  const start = await api.startPrivilegedLogin('admin@example.test', 'password');
  const setup = await api.beginMfaSetup(start.challenge);
  assert.equal(setup.secret, 'SHARED-SECRET');
  assert.equal(api.isConnected(), false);
  const session = await api.finishMfa(start.challenge, '123456', ['etablissement']);
  assert.equal(session.stats.scope, 'institution');
  assert.deepEqual(Array.from(session.recovery_codes), ['ONE', 'TWO']);
  assert.equal(api.isConnected(), true);
  assert.equal(Object.hasOwn(api.getCurrent(), 'token'), false);
  assert.equal(calls[2].options.headers.Authorization, undefined, 'verification is still pre-auth');
  assert.equal(calls[3].options.headers.Authorization, 'WebToken web-secret');
  assert.equal(calls[4].options.headers.Authorization, 'WebToken web-secret');
  await api.logout();
  assert.equal(calls[5].url.endsWith('/users/web-logout/'), true);
  assert.equal(calls[5].options.headers.Authorization, 'WebToken web-secret');
  assert.equal(api.isConnected(), false);
});

test('invalid MFA never saves a token or fetches private resources', async () => {
  const { api, calls } = createHarness(url => url.endsWith('/web-login/')
    ? ok({ mfa_required: true, challenge: 'challenge', mfa_action: 'verify' })
    : { status: 401, body: { success: false, message: 'Code incorrect ou déjà utilisé.' } });
  const login = await api.startPrivilegedLogin('admin@example.test', 'password');
  await assert.rejects(() => api.finishMfa(login.challenge, '000000', ['etablissement']), /Code incorrect/);
  assert.equal(api.isConnected(), false);
  assert.equal(calls.length, 2);
});

test('wrong account role is rejected even with MFA proof', async () => {
  const { api } = createHarness(url => {
    if (url.endsWith('/web-mfa/verify/')) return ok({ token: 'wrong-token', token_type: 'WebToken', role: 'superAdmin' });
    return ok({});
  });
  await assert.rejects(() => api.finishMfa('challenge', '123456', ['etablissement']), /autre espace/);
  assert.equal(api.isConnected(), false);
});

test('institution link and stats scope are both enforced after MFA', async () => {
  for (const profile of [
    { role: 'etablissement', institution_id: null },
    { role: 'etablissement', institution_id: 9 },
  ]) {
    const { api } = createHarness(url => {
      if (url.endsWith('/web-mfa/verify/')) return ok({ token: 'test', token_type: 'WebToken', role: 'etablissement' });
      if (url.endsWith('/users/me/')) return ok(profile);
      return ok({ scope: 'global', users: {}, posts: {} });
    });
    await assert.rejects(() => api.finishMfa('challenge', '123456', ['etablissement']), /établissement|statistiques incompatibles|espace professionnel administrable/);
    assert.equal(api.isConnected(), false);
  }
});

test('superadmin invites use only WebToken; no invitation secret reaches the admin client', async () => {
  const { api, calls } = createHarness((url, options) => {
    if (url.endsWith('/web-mfa/verify/')) return ok({ token: 'platform-token', token_type: 'WebToken', role: 'superAdmin' });
    if (url.endsWith('/users/me/')) return ok({ role: 'superAdmin', email: 'root@example.test' });
    if (url.endsWith('/admin/invitations/') && options.method === 'POST') return ok({ id: 22, expires_at: '2026-10-26T12:00:00Z' });
    if (url.endsWith('/admin/invitations/') && options.method === 'GET') return ok([{ id: 22, email: 'school@example.test', institution_id: 7 }]);
    if (url.endsWith('/admin/invitations/22/revoke/')) return ok({});
    if (url.endsWith('/web-logout/')) return ok({});
    throw new Error('Unexpected ' + url);
  });
  await api.finishMfa('challenge', '123456', ['superAdmin']);
  const invite = await api.sendInvitation('school@example.test', 7);
  assert.equal(invite.id, 22);
  assert.equal(invite.token, undefined);
  assert.equal((await api.listInvitations()).length, 1);
  await api.revokeInvitation(22);
  assert.equal(calls.slice(2).every(call => call.options.headers.Authorization === 'WebToken platform-token'), true);
});

test('invitation preview and acceptance are public but their secret never becomes a browser session', async () => {
  const { api, calls } = createHarness((url) => url.endsWith('/preview/')
    ? ok({ email: 'new@example.test', institution: 'Campus', expires_at: '2026-10-26T12:00:00Z' })
    : ok({ email: 'new@example.test' }));
  const result = await api.previewInvitation('from-mail-link');
  assert.equal(result.institution, 'Campus');
  await api.acceptInvitation('from-mail-link', 'strong-personal-password', 'Awa', 'Diop');
  assert.equal(api.isConnected(), false);
  assert.equal(calls.length, 2);
  assert.equal(calls.every(call => !call.options.headers.Authorization), true);
  assert.equal(calls[1].options.body.includes('strong-personal-password'), true);
});

test('community mobile-token login stays supported, but privileged legacy login is rejected', async () => {
  for (const role of ['student', 'alumni']) {
    const { api, calls } = createHarness(url => url.endsWith('/login/')
      ? ok({ token: 'mobile-token', role }) : ok({ role, email: 'test@example.test' }));
    const result = await api.connectAccount('test@example.test', 'pass', [role]);
    assert.equal(result.profile.role, role);
    assert.equal(calls[1].options.headers.Authorization, 'Token mobile-token');
    await api.logout();
    assert.equal(calls[2].url.endsWith('/users/logout/'), true);
    assert.equal(api.isConnected(), false);
  }
  const { api, calls } = createHarness(() => ok({ token: 'legacy', role: 'superAdmin' }));
  await assert.rejects(() => api.connectAccount('root@example.test', 'pass', ['superAdmin']), /Double authentification/);
  assert.equal(calls.length, 0);
});

test('aborted MFA or late server response cannot revive an invalidated session', async () => {
  let finish;
  const { api } = createHarness(() => new Promise(resolve => { finish = resolve; }));
  const pending = api.startPrivilegedLogin('admin@example.test', 'password');
  api.disconnect();
  finish(ok({ mfa_required: true, challenge: 'x', mfa_action: 'enroll' }));
  await assert.rejects(pending, /session a été fermée/);
  assert.equal(api.isConnected(), false);
});

test('production API base must be configured as HTTPS and public API actions are allowlisted', async () => {
  const { api, calls } = createHarness(() => ok({}), {
    protocol: 'https:', hostname: 'example.test', href: 'https://example.test/auth.html',
  });
  await assert.rejects(() => api.startPrivilegedLogin('admin@example.test', 'password'), /non configurée/);
  assert.equal(calls.length, 0);
  assert.throws(() => api.publicRequest('/users/web-mfa/verify/', {}), /non disponible/);
});

test('registration keeps the Django session cookie, other anonymous auth calls do not', async () => {
  const { api, calls } = createHarness(() => ok({ session_token: 'registration-session' }));
  await api.publicRequest('/users/register/student/check-code/', { code: '123456' });
  await api.publicRequest('/users/register/student/', { session_token: 'registration-session' });
  await api.publicRequest('/users/verify-otp/', { user_id: 12, otp: '123456' });
  assert.equal(calls[0].options.credentials, 'include');
  assert.equal(calls[1].options.credentials, 'include');
  assert.equal(calls[2].options.credentials, 'omit');
});
