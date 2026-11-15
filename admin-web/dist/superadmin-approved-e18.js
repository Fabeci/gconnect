'use strict';
/* E18: approved E15 Superadmin visual, mounted only after E16 MFA.
 * The credential stays in GConnectEstablishmentApi's parent-page memory.
 * No token is serialized, persisted, or placed into the frame URL. */
(() => {
  const api = window.GConnectEstablishmentApi;
  let host = null, frame = null, callbacks = null;
  function onMessage(event) {
    if (!frame || event.origin !== location.origin || event.source !== frame.contentWindow) return;
    if (event.data?.type === 'gconnect-superadmin-logout') callbacks?.logout?.();
    if (event.data?.type === 'gconnect-superadmin-expired') callbacks?.expired?.();
  }
  function unmount() {
    window.removeEventListener('message', onMessage);
    if (frame) frame.remove();
    host = null; frame = null; callbacks = null;
  }
  function mount(target, options) {
    if (!target || !api?.isConnected()) throw new Error('Session Superadmin vérifiée requise.');
    unmount();
    host = target;
    callbacks = {logout: options?.onLogout, expired: options?.onExpired};
    frame = document.createElement('iframe');
    frame.id = 'gconnect-approved-superadmin-frame';
    frame.title = 'Console Superadmin G-Connect';
    frame.setAttribute('referrerpolicy', 'no-referrer');
    frame.src = '/superadmin-connected-e18.html?v=e18-approved-20261025a';
    host.appendChild(frame);
    window.addEventListener('message', onMessage);
  }
  window.GConnectSuperadminConsole = Object.freeze({mount, unmount});
})();