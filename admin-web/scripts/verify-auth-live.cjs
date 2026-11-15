/*
 * Optional real E4 contract test.
 * Run with GCONNECT_BACKEND_PATH=/path/to/gconnect_api npm run test:auth:live
 * It uses an isolated SQLite database and never edits the backend checkout.
 */
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { chromium } = require('playwright');

const frontendRoot = path.resolve(__dirname, '../dist');
const backendRoot = path.resolve(process.env.GCONNECT_BACKEND_PATH || '/mnt/chak/gconnect-api-fabeci');
const python = process.env.GCONNECT_BACKEND_PYTHON || path.join(backendRoot, '.venv/bin/python');
const frontendOrigin = 'http://127.0.0.1:8086';
const apiRoot = 'http://127.0.0.1:8001/api/v1';
const temporaryRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'gconnect-e4-live-'));
const databasePath = path.join(temporaryRoot, 'contract.sqlite3');
const backendLog = path.join(temporaryRoot, 'django.log');
const artifacts = path.resolve(__dirname, '../artifacts/auth-live');
const environment = {
  ...process.env,
  DJANGO_SETTINGS_MODULE: 'gconnect_api.settings.dev',
  GCONNECT_DEV_DB_PATH: databasePath,
  GCONNECT_WEB_APP_URL: frontendOrigin,
  PYTHONDONTWRITEBYTECODE: '1',
  PYTHONUNBUFFERED: '1',
};

let backendProcess;
let browser;
let frontendServer;

function command(args) {
  const result = spawnSync(python, ['-B', 'manage.py', ...args], {
    cwd: backendRoot,
    env: environment,
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(`Backend command failed (${args.join(' ')}):\n${result.stdout}\n${result.stderr}`);
  }
  return result.stdout;
}

function base32Decode(value) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const character of value.replace(/=+$/g, '').toUpperCase()) {
    const index = alphabet.indexOf(character);
    if (index < 0) throw new Error('Invalid base32 TOTP secret.');
    bits += index.toString(2).padStart(5, '0');
  }
  const bytes = [];
  for (let offset = 0; offset + 8 <= bits.length; offset += 8) {
    bytes.push(Number.parseInt(bits.slice(offset, offset + 8), 2));
  }
  return Buffer.from(bytes);
}

function totp(secret) {
  const counter = Math.floor(Date.now() / 30000);
  const value = Buffer.alloc(8);
  value.writeBigUInt64BE(BigInt(counter));
  const digest = crypto.createHmac('sha1', base32Decode(secret)).update(value).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const number = (digest.readUInt32BE(offset) & 0x7fffffff) % 1000000;
  return String(number).padStart(6, '0');
}

function serveFrontend() {
  frontendServer = http.createServer((request, response) => {
    const pathname = new URL(request.url, frontendOrigin).pathname;
    const file = path.join(frontendRoot, pathname === '/' ? 'auth.html' : pathname);
    if (!file.startsWith(frontendRoot + path.sep)) {
      response.writeHead(403).end();
      return;
    }
    fs.readFile(file, (error, body) => {
      if (error) {
        response.writeHead(404).end();
        return;
      }
      const type = ({
        '.css': 'text/css', '.html': 'text/html', '.js': 'text/javascript',
        '.jpg': 'image/jpeg', '.png': 'image/png', '.ttf': 'font/ttf',
      })[path.extname(file)] || 'application/octet-stream';
      response.writeHead(200, { 'Content-Type': type });
      response.end(body);
    });
  });
  return new Promise((resolve, reject) => {
    frontendServer.once('error', reject);
    frontendServer.listen(8086, '127.0.0.1', resolve);
  });
}

async function waitForBackend() {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(apiRoot + '/users/invitations/preview/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invitation: 'invalid-contract-probe-token-000000' }),
      });
      if (response.status >= 400 && response.status < 500) return;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error('Django E4 did not become ready within 30 seconds.');
}

async function waitForInvitationLink() {
  const pattern = new RegExp(frontendOrigin.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '/etablissement-activation\\.html#invitation=([A-Za-z0-9_-]{30,128})');
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    const match = fs.readFileSync(backendLog, 'utf8').match(pattern);
    if (match) return match[0];
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error('The console email did not contain an activation link.');
}

async function clickExact(page, name) {
  await page.getByRole('button', { name, exact: true }).click();
}

async function passwordStep(page, email, password) {
  await page.getByLabel('Adresse e-mail', { exact: true }).fill(email);
  await page.getByLabel('Mot de passe', { exact: true }).fill(password);
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/users/web-login/'));
  await clickExact(page, 'Se connecter');
  const payload = await (await responsePromise).json();
  assert.equal(payload.success, true);
  assert.equal(payload.data.mfa_required, true);
  assert.equal(payload.data.token, undefined, 'web-login must not issue a token before MFA');
  return payload.data;
}

async function enrollMfa(page) {
  await page.getByRole('heading', { name: 'Sécurisez votre compte', exact: true }).waitFor();
  assert.equal(await page.locator('.ea-sidebar').count(), 0, 'dashboard exposed before MFA');
  const secret = (await page.locator('.auth-mfa-secret code').textContent()).trim();
  await page.locator('#auth-otp').fill(totp(secret));
  await clickExact(page, 'Activer la double authentification');
  await page.getByRole('heading', { name: 'Conservez vos codes', exact: true }).waitFor();
  const recoveryCodes = await page.locator('.auth-recovery code').allTextContents();
  assert.equal(recoveryCodes.length, 8);
  await clickExact(page, 'J’ai sauvegardé mes codes, continuer');
  return recoveryCodes;
}

async function logout(page) {
  if ((await page.viewportSize()).width <= 900) {
    await page.locator('#ea-open-menu').click();
    assert.equal(await page.locator('#ea-sidebar').getAttribute('inert'), null);
  }
  await page.locator('#ea-signout-nav').click();
  await page.getByRole('heading', { name: 'Vous êtes déconnecté', exact: true }).waitFor();
}

async function main() {
  assert(fs.existsSync(path.join(backendRoot, 'manage.py')), `Backend not found: ${backendRoot}`);
  assert(fs.existsSync(python), `Backend Python not found: ${python}`);
  fs.mkdirSync(artifacts, { recursive: true });
  await serveFrontend();

  command(['migrate', '--noinput', '--settings=gconnect_api.settings.dev']);
  const seedOutput = command([
    'shell', '--settings=gconnect_api.settings.dev', '-c',
    "from apps.api.v1.establishments.models import Institution; from apps.api.v1.users.models import User; institution=Institution.objects.create(name='Campus E4 Live', acronym='E4'); User.objects.create_user(username='super-e4-live', email='super.e4.live@example.test', password='Super-E4-Live-Password!', role='superAdmin', is_active=True, first_name='Super'); print(f'LIVE_INSTITUTION_ID={institution.pk}')",
  ]);
  const institutionMatch = seedOutput.match(/LIVE_INSTITUTION_ID=(\d+)/);
  assert(institutionMatch, `Could not read seeded institution id:\n${seedOutput}`);
  const institutionId = institutionMatch[1];

  const logDescriptor = fs.openSync(backendLog, 'a');
  backendProcess = spawn(python, ['-B', 'manage.py', 'runserver', '127.0.0.1:8001', '--noreload', '--settings=gconnect_api.settings.dev'], {
    cwd: backendRoot,
    env: environment,
    stdio: ['ignore', logDescriptor, logDescriptor],
  });
  fs.closeSync(logDescriptor);
  await waitForBackend();

  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const browserErrors = [];
  page.on('pageerror', error => browserErrors.push(error.message));
  await page.addInitScript(apiBase => { window.GCONNECT_API_BASE_URL = apiBase; }, apiRoot);

  await page.goto(frontendOrigin + '/auth.html#login/superadmin');
  const superLogin = await passwordStep(page, 'super.e4.live@example.test', 'Super-E4-Live-Password!');
  assert.equal(superLogin.mfa_action, 'enroll');
  await enrollMfa(page);
  await page.getByRole('heading', { name: /^Bienvenue/ }).waitFor();
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);

  await page.locator('#auth-invite_institution').fill(institutionId);
  await page.locator('#auth-invite_email').fill('invitee.e4.live@example.test');
  await clickExact(page, 'Envoyer une invitation');
  await page.getByText('invitee.e4.live@example.test').waitFor();
  const invitationLink = await waitForInvitationLink();
  await clickExact(page, 'Se déconnecter');
  await clickExact(page, 'Oui, me déconnecter');
  await page.getByRole('heading', { name: 'Vous êtes déconnecté', exact: true }).waitFor();

  await page.goto(invitationLink);
  await page.getByRole('heading', { name: 'Bienvenue dans votre espace', exact: true }).waitFor();
  await page.locator('#auth-first_name').fill('Awa');
  await page.locator('#auth-last_name').fill('Diop');
  await page.locator('#auth-password').fill('Invitee-E4-Live-Password!');
  await page.locator('#auth-confirm').fill('Invitee-E4-Live-Password!');
  await clickExact(page, 'Activer mon compte');
  await page.getByRole('heading', { name: 'Votre compte est activé', exact: true }).waitFor();
  assert.equal(new URL(page.url()).hash, '#activated/etablissement');

  await clickExact(page, 'Se connecter');
  const establishmentLogin = await passwordStep(page, 'invitee.e4.live@example.test', 'Invitee-E4-Live-Password!');
  assert.equal(establishmentLogin.mfa_action, 'enroll');
  const establishmentRecovery = await enrollMfa(page);
  await page.locator('.ea-sidebar').waitFor();
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
  await page.screenshot({ path: path.join(artifacts, 'establishment-dashboard-mobile.png'), fullPage: true });
  await logout(page);

  await page.goto(frontendOrigin + '/auth.html#login/etablissement');
  const recoveryLogin = await passwordStep(page, 'invitee.e4.live@example.test', 'Invitee-E4-Live-Password!');
  assert.equal(recoveryLogin.mfa_action, 'verify');
  await page.getByRole('heading', { name: 'Vérifiez votre identité', exact: true }).waitFor();
  await page.locator('#auth-mfa_code').fill(establishmentRecovery[0]);
  await clickExact(page, 'Vérifier et accéder');
  await page.locator('.ea-sidebar').waitFor();
  await logout(page);

  assert.deepEqual(browserErrors, []);
  console.log('PASS: live E4 Superadmin MFA, invitation email, activation, establishment MFA, recovery code, dashboard gate and logout.');
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close().catch(() => {});
  if (backendProcess && !backendProcess.killed) backendProcess.kill('SIGTERM');
  if (frontendServer) await new Promise(resolve => frontendServer.close(resolve));
  fs.rmSync(temporaryRoot, { recursive: true, force: true });
});
