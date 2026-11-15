'use strict';
/* E19: shared approved administrative visual after verified privileged MFA.
 * The credential stays in GConnectEstablishmentApi's parent-page memory.
 * No token is serialized, persisted, or placed into the frame URL. */
(() => {
  const api = window.GConnectEstablishmentApi;
  let host = null, frame = null, callbacks = null;
  function onMessage(event) {
    if (!frame || event.origin !== location.origin || event.source !== frame.contentWindow) return;
    if (event.data?.type === 'gconnect-admin-logout') callbacks?.logout?.();
    if (event.data?.type === 'gconnect-admin-expired') callbacks?.expired?.();
  }
  function unmount() {
    window.removeEventListener('message', onMessage);
    if (frame) frame.remove();
    host = null; frame = null; callbacks = null;
  }
  function mount(target, options) {
    const current = api?.getCurrent?.();
    const role = current?.profile?.role;
    if (!target || !api?.isConnected() || !['superAdmin', 'etablissement', 'enterprise'].includes(role)) {
      throw new Error('Session administrative vérifiée requise.');
    }
    unmount();
    host = target;
    callbacks = {logout: options?.onLogout, expired: options?.onExpired};
    frame = document.createElement('iframe');
    frame.id = 'gconnect-approved-admin-frame';
    frame.title = 'Administration G-Connect — ' + (role === 'superAdmin' ? 'Superadmin' : role === 'enterprise' ? 'Entreprise' : 'Établissement');
    frame.setAttribute('referrerpolicy', 'no-referrer');
    frame.src = '/_internal/admin-console?v=e22-pricing-20261026a';
    host.appendChild(frame);
    window.addEventListener('message', onMessage);
  }
  window.GConnectAdminConsole = Object.freeze({mount, unmount});
})();