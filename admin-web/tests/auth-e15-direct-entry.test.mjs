import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createContext, runInContext } from 'node:vm';

const read = name => readFileSync(new URL('../dist/' + name, import.meta.url), 'utf8');
const source = read('auth.js');

function open(pathname, hash = '', roleButton = null) {
  const redirects = [];
  const canonicalHashes = [];
  const root = {
    innerHTML: '',
    querySelector: () => null,
    querySelectorAll: selector => selector === '[data-role]' && roleButton ? [roleButton] : [],
  };
  const location = {
    pathname, hash, search: '',
    replace: url => redirects.push(url),
    assign: url => redirects.push(url),
  };
  const document = {
    title: '',
    documentElement: { dataset: { theme: 'light' } },
    body: { classList: { remove() {} } },
    getElementById: () => null,
  };
  const window = {
    GConnectEstablishmentApi: { isConnected: () => false },
    addEventListener() {},
  };
  const history = { replaceState: (_state, _title, target) => canonicalHashes.push(target) };
  const context = createContext({
    window, document, location, history, URLSearchParams,
    localStorage: { getItem: () => null, setItem() {} },
    setInterval: () => 0, clearInterval() {},
  });
  runInContext(source, context);
  window.GConnectAuth.mount(root, () => {});
  return { root, location, redirects, canonicalHashes, roleButton };
}

test('dedicated entry points use the E16 composition and never load a selector upfront', () => {
  for (const file of ['etablissement.html','superadmin-login.html']) {
    const html = read(file);
    assert.match(html, /\/auth-admin\.css/);
    assert.match(html, /\/auth\.js/);
  }
  const establishment = open('/etablissement.html', '#welcome/etablissement');
  assert.equal(establishment.canonicalHashes.at(-1), '#login/etablissement');
  assert.match(establishment.root.innerHTML, /Connectez-vous/);
  assert.match(establishment.root.innerHTML, /Espace Établissement/);
  assert.doesNotMatch(establishment.root.innerHTML, /auth-story|auth-header|hero-gconnect|Découvrir G-Connect/);
  assert.doesNotMatch(establishment.root.innerHTML, /auth-role-list/);

  const superadmin = open('/superadmin-login.html');
  assert.equal(superadmin.canonicalHashes.at(-1), '#login/superadmin');
  assert.match(superadmin.root.innerHTML, /Connectez-vous/);
  assert.match(superadmin.root.innerHTML, /Administration générale/);
  assert.doesNotMatch(superadmin.root.innerHTML, /auth-role-list/);
});

test('administrative portals reject community-only states and Superadmin activation', () => {
  for (const file of ['etablissement.html','etablissement-connexion.html','superadmin-login.html']) {
    for (const state of ['register','details','credentials','verify','verified','pending']) {
      const result = open('/'+file, '#'+state+'/community');
      assert.match(result.canonicalHashes.at(-1), /^#login\/(etablissement|superadmin)$/);
      assert.doesNotMatch(result.root.innerHTML, /auth-role-list|auth-kind|auth-code/);
    }
  }
  assert.equal(open('/superadmin-login.html','#invitation/superadmin').canonicalHashes.at(-1),'#login/superadmin');
});

test('protected stages cannot be opened from a fabricated hash', () => {
  for (const state of ['mfa-setup','mfa-verify','mfa-recovery','session','logout']) {
    const result = open('/etablissement.html','#'+state+'/etablissement');
    assert.equal(result.canonicalHashes.at(-1),'#login/etablissement');
    assert.doesNotMatch(result.root.innerHTML,/auth-mfa-secret|auth-recovery|auth-invite-form/);
  }
});

test('role tampering in dedicated portal hashes cannot swap portals', () => {
  const establishment = open('/etablissement.html', '#login/superadmin');
  assert.equal(establishment.canonicalHashes.at(-1), '#login/etablissement');
  const superadmin = open('/superadmin-login.html', '#welcome/community');
  assert.equal(superadmin.canonicalHashes.at(-1), '#login/superadmin');
});

test('historical admin login links from the general portal redirect', () => {
  assert.deepEqual(open('/auth.html','#login/superadmin').redirects, ['/superadmin-login.html#login/superadmin']);
  assert.deepEqual(open('/auth.html','#login/etablissement').redirects, ['/etablissement.html#login/etablissement']);
});

test('general selector still works and its admin buttons go to dedicated portals', () => {
  const chooser = open('/auth.html','#welcome/community');
  assert.match(chooser.root.innerHTML, /auth-role-list/);
  for (const [role, expected] of [
    ['etablissement','/etablissement#login/etablissement'],
    ['superadmin','/superadmin#login/superadmin'],
  ]) {
    const button = { dataset: { role }, onclick: null };
    const result = open('/auth.html','#welcome/community',button);
    assert.equal(typeof button.onclick,'function');
    button.onclick();
    assert.deepEqual(result.redirects, [expected]);
  }
});

test('community registration remains distinct and no server-side gate changes', () => {
  const community = open('/auth.html','#register/community');
  assert.equal(community.canonicalHashes.at(-1), '#register/community');
  assert.match(community.root.innerHTML, /Votre réseau commence ici/);
  assert.match(source,/const api = window\.GConnectEstablishmentApi/);
  assert.match(source,/mfa-verify/);
  assert.match(source,/api\.previewInvitation/);
});
