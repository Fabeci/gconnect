# E16 — Authentification administrative

Branche : `feat/e16-auth-minimal-premium`.
Référence : `origin/feat/e15-direct-admin-login`, commit `46f56b7`.
Worktree : `/tmp/g-connect-e16`. Le répertoire `/mnt/chak/g-connect` et ses changements E6 sont conservés.

## Interface livrée

Une composition centrale de 464 px remplace réellement le DOM avec photo, panneau éditorial et bandeau de navigation des pages administratives. Aucun chargement de photo sur ces entrées. Le logo officiel est intégré au formulaire ; il sert aussi de lien discret vers l’accueil. Le thème se règle avec un bouton iconographique de 44 px, nommé pour les lecteurs d’écran.

Manrope, titre 30 px sur ordinateur et 25 px sur mobile, description 14 px, labels 13 px, champs 14 px (16 px sur mobile pour éviter le zoom automatique iOS), boutons 14 px. Carte arrondie à 28 px, champs et boutons à 16 px. Fond bleuté léger, surface translucide et ombre douce. Le sombre reprend les tokens de `glass-refinement.css` et les surfaces ardoise du dashboard Établissement.

Les étapes partagent les mêmes composants : connexion directe, instructions d’invitation, activation et mot de passe, confirmation d’activation, récupération SMS, réinitialisation, installation et vérification MFA, codes de secours, messages d’erreur, session expirée et déconnexion. Les étapes communautaires ne sont pas proposées sur ces routes. Aucune invitation ou création de Superadmin n’est ajoutée.

Animations : entrée de la carte, apparition décalée des champs, changement d’étape, focus et bordures, boutons, messages, changement de thème et indicateur pendant une requête. Aucun mouvement permanent au repos. `prefers-reduced-motion` est respecté.

## Accès local

```bash
cd /tmp/g-connect-e16
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist
```

Le serveur a été lancé sur ce port lors de la validation.

- Établissement : <http://127.0.0.1:8080/etablissement.html>
- Administration générale : <http://127.0.0.1:8080/superadmin-login.html>
- Activation : `/etablissement-activation.html#invitation=…`, exclusivement avec le lien personnel reçu.
- Ancienne entrée : `/etablissement-connexion.html`, désormais dans la même famille visuelle.

Le client existant utilise Django sur `http://127.0.0.1:8001/api/v1`. L’origine `http://127.0.0.1:8080` est autorisée : le précontrôle CORS réel a retourné `Access-Control-Allow-Origin: http://127.0.0.1:8080`. Le port 8096 ne l’est pas ; ne pas l’utiliser pour valider une connexion réelle. Aucune configuration backend n’a été modifiée.

Une vérification Chromium depuis cette URL réelle, sans interception réseau, a également obtenu HTTP 200 sur `OPTIONS /users/web-login/` et identifié la vue Django « Establishment Web Login ».

## Fichiers

| Fichier | Modification |
| --- | --- |
| `dist/auth-admin.css` | Nouvelle composition, composants, responsive, sombre et animations administratives |
| `dist/auth.js` | Gabarits administratifs, textes, états accessibles, erreurs non techniques, retour à la connexion après expiration |
| `dist/etablissement.html` | Charge le nouveau style administratif |
| `dist/superadmin-login.html` | Charge le même style pour l’administration générale |
| `dist/etablissement-activation.html` | Harmonisation de l’activation |
| `dist/etablissement-connexion.html` | Harmonisation de l’ancienne entrée directe |
| `dist/superadmin-preview.html` | Correction du lien « Connexion réelle » vers `/superadmin-login.html` |
| `scripts/verify-auth-e16.cjs` | Captures, accessibilité, responsive, interactions et échecs sans authentification réussie |
| `scripts/verify-auth.cjs`, `scripts/verify-auth-live.cjs` | Sélecteurs textuels adaptés aux nouveaux titres |
| `tests/auth-e14-journey.test.mjs` | Réserve la vérification du style photographique E14 au portail communautaire |
| `tests/auth-e15-direct-entry.test.mjs` | Vérifie la nouvelle composition, les routes directes et les étapes protégées |
| `tests/superadmin-e11-topbar.test.mjs` | Corrige une assertion préexistante qui refusait plusieurs classes CSS sur le menu profil |
| `package.json` | Ajoute `test:auth:e16` |
| `.gitignore` | Ignore les captures générées, sauf la sélection de livraison suivie dans Git |
| `docs/e16-auth-minimal-premium.md` | Rapport et procédure de validation |

## Validation

`npm test` : 13 suites réussies, aucune suite en échec. Les tests existants de contrat API utilisent leurs doubles unitaires ; ils ne contactent pas Django.

`npm run test:auth:e16` : **82 audits réussis**, aucun débordement horizontal détecté, aucune violation signalée par axe sur les critères WCAG 2 A/AA et 2.1 AA sélectionnés, aucune erreur JavaScript. Les contrôles de syntaxe JavaScript et `git diff --check` passent également. Ces audits automatiques ne constituent pas une certification d’accessibilité.

```bash
# Dans ce worktree, réutilise les dépendances déjà installées du dépôt :
NODE_PATH=/mnt/chak/g-connect/node_modules npm run test:auth:e16
# Dans un clone autonome, après installation des dépendances :
npm run test:auth:e16
```

Le runner E16 vérifie les deux entrées à 1920×1080, 1366×768, 768×1024, 390×844 et 360×800, en clair et sombre. Il contrôle aussi les étapes secondaires, le clavier et l’ordre du focus, l’affichage du mot de passe, les champs requis, le blocage de double soumission, les erreurs 401/429/503, l’effacement des erreurs après correction, les invitations invalides, le retrait du secret de l’URL, l’expiration de session, les animations, la préférence de mouvement réduit, un zoom 200 % et une hauteur réduite pour le clavier mobile. Les rapports sont générés dans `artifacts/auth-e16/results.json`.

Les captures des étapes protégées sont des **gabarits rendus hors authentification**, explicitement marqués « APERÇU VISUEL — aucune session authentifiée ». Les valeurs de clé et de code y sont volontairement inutilisables et vérifient la place nécessaire aux textes. Aucun compte, jeton ou succès de connexion n’est créé ou simulé. Les réponses d’erreur du test restent interceptées localement.

Inspection visuelle effectuée sur les captures desktop et mobiles, dont le sombre, l’activation, la MFA et les messages d’erreur. Les codes de secours utilisent une colonne afin de conserver lisibles les 24 caractères renvoyés par Django.

Les commandes `npm run test:auth` et `npm run test:auth:live` ne sont pas exécutées pour E16 : la première simule des connexions réussies, la seconde crée des comptes dans une base de test. Leurs sélecteurs sont maintenus, mais leur validation de bout en bout reste à effectuer dans une mission autorisant ces scénarios.

## Captures de livraison

| Espace | Desktop clair | Desktop sombre | Mobile clair | Mobile sombre |
| --- | --- | --- | --- | --- |
| Établissement | [1366 px](../artifacts/auth-e16/etablissement-1366-light.png) | [1366 px](../artifacts/auth-e16/etablissement-1366-dark.png) | [390 px](../artifacts/auth-e16/etablissement-390-light.png) | [360 px](../artifacts/auth-e16/etablissement-360-dark.png) |
| Administration générale | [1366 px](../artifacts/auth-e16/superadmin-login-1366-light.png) | [1366 px](../artifacts/auth-e16/superadmin-login-1366-dark.png) | [390 px](../artifacts/auth-e16/superadmin-login-390-light.png) | [360 px](../artifacts/auth-e16/superadmin-login-360-dark.png) |

Toutes les autres captures sont disponibles localement dans `artifacts/auth-e16/` et reproductibles par le runner. Les captures de présentation sont préfixées `presentation-` pour les distinguer des routes réellement accessibles sans compte.

## Backend et limites restantes

Les endpoints, les contrôles de rôle, les jetons en mémoire, la MFA, les codes à usage unique et les protections contre les tentatives excessives restent ceux d’E15. `dist/etablissement-api.js` est inchangé. Aucun fichier backend, utilisateur ou base de données n’a été modifié. Aucun appel POST n’a été envoyé au backend pour cette mission.

Vérifications réelles en lecture seule sur Django : `OPTIONS` répond sur `web-login`, `web-mfa/setup`, `web-mfa/verify`, `invitations/preview`, `invitations/accept`, `forgot-password` et `reset-password`. La déconnexion `web-logout` retourne 401 sans session, conformément à sa protection. Cela confirme les routes disponibles, pas une authentification complète.

Limites observées dans le backend :

- La récupération existante est un code SMS, pas un lien de réinitialisation par e-mail. Elle exige un téléphone associé et Twilio configuré ; l’envoi effectif n’a pas été testé.
- L’acceptation d’une invitation Établissement ne recueille pas de numéro de téléphone. Un compte ainsi créé doit disposer d’un téléphone ajouté par un parcours autorisé pour utiliser la récupération SMS. L’interface explique cette condition et oriente vers le responsable si nécessaire.
- L’invitation/activation existante concerne les responsables Établissement. Aucun parcours public d’activation Superadmin n’est implémenté ou inventé.
- Le parcours Superadmin authentifié d’E15 aboutit à la gestion des invitations. L’aperçu des quinze modules reste un aperçu séparé ; E16 n’ajoute pas de redirection vers une fausse console authentifiée.
- L’expiration réelle de session est signalée lors d’une réponse de l’API. Les jetons restant en mémoire, un rechargement requiert une nouvelle connexion. Aucun maintien de session artificiel n’a été ajouté.

Restent à valider avec des comptes et invitations réels autorisés : connexion complète des deux rôles, activation effective, installation MFA, consommation d’un code de secours, réception SMS et réinitialisation, puis déconnexion côté serveur. Ces opérations changent des données ; elles n’ont pas été exécutées dans cette mission de design.

Aucune fusion dans `main`, aucun déploiement en production.
