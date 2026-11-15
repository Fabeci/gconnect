import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createContext, runInContext } from 'node:vm';

const read = name => readFileSync(new URL('../dist/' + name, import.meta.url), 'utf8');
const auth = read('auth.js');
const live = read('superadmin-live-e17.js');
const html = read('superadmin-login.html');
const css = read('superadmin-live-e17.css');

function makeConsole({ role = 'superAdmin', authenticated = true, invitations = [] } = {}) {
  let reads = 0;
  let expired = 0;
  const api = {
    isConnected: () => authenticated,
    getCurrent: () => ({ profile: { role, email: 'admin@example.test' } }),
    listInvitations: async () => { reads += 1; return invitations; },
  };
  const host = {
    innerHTML: '',
    querySelectorAll: () => [],
    querySelector: () => null,
  };
  const win = { GConnectEstablishmentApi: api };
  const document = { documentElement: { dataset: { theme: 'light' } } };
  runInContext(live, createContext({ window: win, document }));
  const actions = { onLogout() {}, onExpired() { expired += 1; } };
  return { api, win, host, actions, getReads: () => reads, getExpired: () => expired };
}

test('Superadmin MFA continues into the live console without document navigation', () => {
  // E18 preserved the connected console and updated only its approved assets.
  assert.match(html, /\/superadmin-approved-e18\.css/);
  assert.match(html, /\/superadmin-approved-e18\.js/);
  assert.ok(html.indexOf('superadmin-approved-e18.js') < html.indexOf('src="/auth.js?'));
  assert.match(html, /\/auth-admin\.css\?v=e18-approved-/);
  assert.match(html, /\/auth\.js\?v=e18-approved-/);
  assert.match(html, /name="gconnect-auth-build"/);
  assert.match(auth, /screen==='session' && profile\?\.role==='superAdmin' && api\.isConnected\(\)/);
  assert.match(auth, /GConnectSuperadminConsole\.mount/);
  assert.match(auth, /GConnectSuperadminConsole\?\.unmount\(\)/);
  assert.doesNotMatch(auth, /location\.(href|assign|replace)\s*=\s*['"].*superadmin-preview/);
});

test('Superadmin console never trusts role or a fabricated frontend route', () => {
  const wrong = makeConsole({ role: 'etablissement' });
  assert.throws(() => wrong.win.GConnectSuperadminConsole.mount(wrong.host, wrong.actions), /Session Superadmin/);
  const disconnected = makeConsole({ authenticated: false });
  assert.throws(() => disconnected.win.GConnectSuperadminConsole.mount(disconnected.host, disconnected.actions), /Session Superadmin/);
  assert.equal(wrong.getReads(), 0);
  assert.equal(disconnected.getReads(), 0);
});

test('connected console displays backend invitations and does not invent billing', async () => {
  const s = makeConsole({ invitations: [
    { id: 101, email: 'lead@campus.test', institution_name: 'Institut réel', expires_at: '2099-12-31T00:00:00Z', accepted: false, revoked: false },
    { id: 102, email: 'expired@campus.test', institution_name: 'Autre établissement', expires_at: '2020-01-01T00:00:00Z', accepted: false, revoked: false },
  ] });
  s.win.GConnectSuperadminConsole.mount(s.host, s.actions);
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(s.getReads(), 1);
  assert.match(s.host.innerHTML, /Institut réel/);
  assert.match(s.host.innerHTML, /lead@campus\.test/);
  assert.match(s.host.innerHTML, /Abonnements actifs/);
  assert.match(s.host.innerHTML, /Module de facturation absent/);
  assert.match(s.host.innerHTML, /Aucun chiffre commercial fictif/);
  assert.doesNotMatch(s.host.innerHTML, /5[\s.,]?000[\s.,]?000\s*FCFA/);
  assert.match(s.host.innerHTML, /Profil|profile|Superadmin/);
  s.win.GConnectSuperadminConsole.unmount();
  assert.equal(s.getExpired(), 0);
});

test('real requests use the existing privileged client; no WebToken goes to browser storage', () => {
  assert.match(live, /api\.listInvitations\(\)/);
  assert.match(live, /api\.sendInvitation\(email,institutionId\)/);
  assert.match(live, /api\.revokeInvitation\(id\)/);
  assert.match(live, /api\.getCurrent\(\)\?\.profile\?\.role === 'superAdmin'/);
  assert.doesNotMatch(live, /(?:localStorage|sessionStorage)\.setItem\([^)]*(?:token|credential|session)/i);
  assert.doesNotMatch(live, /window\.location\.(?:href|assign)\(?.*token/i);
});

test('E17 retains accessibility, slate dark colours, responsiveness and reduced-motion', () => {
  assert.match(live, /aria-label="Notifications"/);
  assert.match(live, /aria-label="Navigation Superadmin"/);
  assert.match(live, /aria-current="page"/);
  assert.match(css, /html\[data-theme="dark"\] \.sa-live/);
  assert.match(css, /max-width:1049px/);
  assert.match(css, /max-width:720px/);
  assert.match(css, /prefers-reduced-motion:reduce/);
  assert.match(css, /border-radius:32px/);
});
