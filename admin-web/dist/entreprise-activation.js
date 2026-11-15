'use strict';
/* E54.3: invitation token lives only in this closure and is removed from the URL immediately. */
(function () {
  const match = /^#invitation=([A-Za-z0-9_-]{30,128})$/.exec(window.location.hash);
  let invitation = match ? match[1] : null;
  window.history.replaceState(null, '', window.location.pathname + window.location.search);
  let busy = false;
  const $ = id => document.getElementById(id);
  function feedback(message, kind) {
    const node = $('ea-feedback');
    node.textContent = message;
    node.className = 'ea-feedback' + (kind ? ' ea-' + kind : '');
  }
  function previewCard(data) {
    const card = $('ea-summary');
    const title = document.createElement('strong');
    const email = document.createElement('span');
    const role = document.createElement('span');
    title.textContent = data.company_name || 'Votre entreprise';
    email.textContent = data.email || '';
    role.textContent = data.kind === 'recruiter' ? 'Invitation Recruteur' : 'Invitation Responsable';
    card.replaceChildren(title, email, role);
    card.hidden = false;
  }
  async function start() {
    const api = window.GConnectEstablishmentApi;
    if (!invitation) {
      feedback("Le lien d'invitation est invalide. Demandez un nouveau lien à votre responsable.", 'error');
      return;
    }
    if (!api?.enterprisePreviewInvitation || !api?.enterpriseAcceptInvitation) {
      feedback('Le service d’activation est indisponible. Rechargez cette page.', 'error');
      return;
    }
    try {
      const data = await api.enterprisePreviewInvitation(invitation);
      if (!data || !['owner', 'recruiter'].includes(data.kind)) {
        throw new Error('Type d’invitation non reconnu.');
      }
      previewCard(data);
      $('ea-form').hidden = false;
      feedback('Invitation validée. Complétez vos informations pour créer votre compte.');
    } catch(error) {
      invitation = null;
      feedback(error.message || 'Invitation expirée ou révoquée.', 'error');
    }
  }
  async function activate(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (busy || !invitation || !form.reportValidity()) return;
    const data = new FormData(form);
    const password = String(data.get('password') || '');
    if (password !== String(data.get('confirm_password') || '')) {
      feedback('Les deux mots de passe ne correspondent pas.', 'error');
      return;
    }
    if (password.length < 12) {
      feedback('Choisissez un mot de passe d’au moins 12 caractères.', 'error');
      return;
    }
    busy = true;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    feedback('Activation sécurisée du compte en cours…');
    try {
      await window.GConnectEstablishmentApi.enterpriseAcceptInvitation(
        invitation, password, String(data.get('first_name') || '').trim(),
        String(data.get('last_name') || '').trim());
      invitation = null;
      form.reset();
      form.hidden = true;
      $('ea-complete').hidden = false;
      feedback('Compte activé. Connectez-vous et configurez votre double authentification MFA.', 'success');
    } catch(error) {
      feedback(error.message || 'Activation impossible. Vérifiez le lien et réessayez.', 'error');
    } finally {
      busy = false;
      button.disabled = false;
    }
  }
  // Opening another invitation in this tab changes only the URL fragment.
  // Reload to re-validate its new one-time token before displaying any account data.
  window.addEventListener('hashchange', () => {
    if (window.location.hash.startsWith('#invitation=')) window.location.reload();
  });
  document.addEventListener('DOMContentLoaded', () => {
    $('ea-form').addEventListener('submit', activate);
    void start();
  });
})();
