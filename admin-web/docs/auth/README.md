# Parcours d’authentification G-Connect

Point d’entrée : `/auth.html`. Les adresses `/etablissement-connexion.html` et `/etablissement.html` conservent leur contrôle d’accès et utilisent le nouveau parcours. Un lien Connexion figure dans l’espace communautaire existant.

## Interface

Accueil par profil, connexion Superadmin / Établissement / Étudiant-Alumni, inscription en trois étapes, vérification e-mail, récupération SMS, nouveau mot de passe, confirmation et résultat de déconnexion. Palette G-Connect, Manrope et photographie locales existantes ; styles et client API partagés. Responsive dès 320 px, navigation clavier, libellés explicites, erreurs annoncées, focus après transition, collage/autocomplétion des codes et réduction des animations selon les préférences système.

## Contrats conservés

| Action | Endpoint existant | Données |
| --- | --- | --- |
| Connexion Étudiant/Alumni | `POST /users/login/` | `email`, `password` |
| Connexion Établissement/Superadmin | `POST /users/web-login/` | Défi MFA sans token |
| Configuration TOTP | `POST /users/web-mfa/setup/` | Défi MFA |
| Vérification TOTP | `POST /users/web-mfa/verify/` | Défi + code, puis WebToken |
| Invitation administrateur | `POST /users/admin/invitations/` | WebToken Superadmin |
| Activation par e-mail | `POST /users/invitations/preview/`, `/users/invitations/accept/` | Secret du lien d’invitation |
| Profil autorisé | `GET /users/me/` | `Authorization: WebToken …` pour les rôles privilégiés, `Token …` pour la communauté |
| Tableau établissement | `GET /backoffice/stats/` | scope institution obligatoire |
| Code établissement | `POST /users/register/student/check-code/` | `code` ; session Django conservée |
| Inscription étudiante | `POST /users/register/student/` | `session_token`, identité, téléphone, genre, naissance, matricule, mot de passe |
| Inscription alumni | `POST /users/register/alumni/` | multipart avec `institution_id`, identité et `proof_document` |
| Vérification e-mail | `POST /users/verify-otp/` | `user_id`, `otp` |
| Renvoi du code e-mail | `POST /users/otp/resend/` | `user_id` |
| Récupération | `POST /users/forgot-password/` | `email` ; code envoyé par SMS |
| Nouveau mot de passe | `POST /users/reset-password/` | `user_id`, `otp`, `new_password` |
| Déconnexion | `POST /users/web-logout/` ou `/users/logout/` | Selon le type de session ; effacement local même en cas d’erreur |

Les rôles serveur sont `superAdmin`, `etablissement`, `student`, `alumni`. Le choix d’espace n’attribue aucun droit. Les tokens restent exclusivement en mémoire JavaScript (jamais en localStorage, sessionStorage ou URL). Les comptes privilégiés reçoivent un **WebToken révocable seulement après MFA**. Le rechargement nécessite une nouvelle connexion. La déconnexion web révoque uniquement la session de ce navigateur ; la déconnexion étudiante/alumni conserve son contrat Token mobile.

## Limites du backend vérifié

- Le backend E4 du fork propose désormais l’invitation, l’activation et l’enrôlement MFA. La page `/etablissement-activation.html` reçoit le lien envoyé par e-mail. **SMTP réel, HTTPS et tests d’intégration** restent à valider avant production.
- Les alumni nécessitent une validation administrative du justificatif. Ils ne passent pas par la vérification OTP étudiante.
- Le tableau établissement existant est conservé. Le Superadmin possède maintenant un panneau limité à la gestion des invitations (identifiant numérique d’établissement requis), mais aucun tableau de bord global complet. L’espace communautaire authentifié reste un aperçu.
- L’ouverture de `auth.html?user_id=42#verify/community` permet de reprendre la vérification avec un identifiant fourni par un parcours fiable. Ce paramètre n’active rien sans OTP ; il est retiré de l’URL après lecture. Sans contexte, l’écran invite à reprendre l’inscription.
- L’état temporaire d’inscription et les documents restent uniquement en mémoire jusqu’à soumission. Un rechargement impose de recommencer.

## Configuration et exécution

```sh
npm ci
python3 -m http.server 8086 --directory dist
# http://localhost:8086/auth.html
npm test
npm run test:auth
# Avec le fork backend E4 disponible localement :
GCONNECT_BACKEND_PATH=/chemin/vers/gconnect_api npm run test:auth:live
```

Le client conserve `window.GCONNECT_API_BASE_URL` ou la balise `meta[name="gconnect-api-base"]`. En local, il utilise `http://localhost:8001/api/v1` (ou 127.0.0.1 selon l’hôte). En production, configurer explicitement l’URL HTTPS de l’API. L’inscription étudiante utilise `credentials: include` pour la session Django : origine autorisée avec credentials et politique de cookies compatible sont nécessaires. Privilégier un reverse proxy de même origine. Les appels authentifiés par token conservent `credentials: omit`.

## Validation

`npm test` : régressions du frontend et du client API, vérification des rôles et profils, révocation, effacement local sur erreur et cookies d’inscription.

`npm run test:auth` : serveur local éphémère, Chromium, API interceptée (aucun compte réel créé), audits axe WCAG 2 A/AA et 2.1 AA sur 9 écrans à 320, 390, 768 et 1440 px. Scénarios : erreurs de connexion, mauvais rôle, connexion de chaque rôle, inscription étudiante et alumni multipart, confirmation de mot de passe, OTP, renvoi temporisé, récupération SMS, réponse sans compte, déconnexion et panne de révocation, rechargement, clavier et réduction des animations.

`npm run test:auth:live` : base SQLite jetable, migrations et serveur Django E4 réels, puis parcours Chromium Superadmin MFA → e-mail d’invitation → activation → MFA Établissement → WebToken → tableau de bord → déconnexion → reconnexion par code de secours. Le clone backend n’est pas modifié.

Captures et rapport générés dans `artifacts/auth/` (ignoré par Git). Les tests à API interceptée vérifient les contrats et l’interface ; ils ne prouvent pas la livraison réelle d’e-mails/SMS, la configuration CORS de production ou l’activation administrative.

### Résultat Codex avant l’intégration E4 — 24 octobre 2026

- `npm test` : 4 fichiers de tests réussis.
- `npm run test:auth` : 36 audits axe réussis, scénarios réussis, aucune erreur JavaScript.
- Revue visuelle des captures desktop et mobile.
- [Accueil desktop](welcome-desktop.png) · [Connexion mobile](login-mobile.png) · [Rapport JSON](validation.json).
- Le workflow `auth-journey.yml` relance les tests sur les branches `feat/auth-*` et publie les captures en artefact CI.

### Intégration E4 (24 octobre 2026)

La branche `feat/auth-journey-premium` inclut désormais le parcours MFA Établissement et Superadmin ainsi que les invitations. Les anciens résultats de tests ci-dessus concernent **la version Codex précédente**. Voir [`docs/integration/etablissement-e4-auth-web-2026-10-24.md`](../integration/etablissement-e4-auth-web-2026-10-24.md) pour l’exécution des tests mis à jour et le branchement sur le backend E4.

Validation finale E4 : 5 suites Node réussies, 46 audits navigateur fonctionnels/accessibilité/responsive réussis, 17 tests de sécurité E3/E4 Django réussis et scénario réel `test:auth:live` réussi jusqu’à la reconnexion par code de secours. Le test réel utilise le backend console pour l’e-mail ; il ne valide donc pas la délivrabilité SMTP de production.
