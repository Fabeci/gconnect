# E62 · Sessions & sécurité Premium V2

## Objectif
Remplacer uniquement le placeholder « Sessions & sécurité » du Superadmin,
sans intervenir sur E19 (shell), Factures E38, Invitations E54, Offres E57,
Imports E58, Modération E59, Statistiques E60 ou Journal d'audit E61.

## Identité visuelle
- Palette autonome **bleu ardoise / verre de mer / corail discret**.
- Haut de page **transparent** comme Factures, illustration de cadenas
  flottant avec orbites et état MFA, quatre cartes KPI animées et cliquables.
- Liste des appareils personnels, fiches de définition des chiffres,
  anneau de couverture MFA, histogramme des tentatives réellement consignées
  et repères opérationnels.
- Adaptatif mobile et thème sombre, avec `prefers-reduced-motion`.
- Aucune large barre de boutons uniforme ; les actions sont adaptées au
  contexte et placées dans les cartes et fiches concernées.

## Sources de données vérifiables
Backend, branche `feat/e54-integrate-e38-e53` :

```http
GET /api/v1/backoffice/security-v2/?days=30
Authorization: WebToken <session Superadmin validée par MFA>
```

Agrégats globaux **réels** sur :
- `EstablishmentWebSession` : sessions non révoquées, non expirées et
  dont l'activité est plus récente que le délai d'inactivité configuré.
- `PrivilegedMFADevice.confirmed_at` : comptes professionnels actifs
  (`superAdmin`, `etablissement`, `enterprise`) disposant d'une MFA
  confirmée. Les comptes sans MFA confirmée sont comptés séparément.
- `LoginAttempt` : tentatives réussies ou échouées **enregistrées**
  sur 7, 30 ou 90 jours ; ce journal n'assure pas l'exhaustivité de tous
  les événements d'authentification et les échecs ne prouvent pas un incident.
- `PrivilegedRecoveryCode.used_at` : nombre de codes encore utilisables
  pour le **Superadmin connecté**, sans renvoyer les codes eux-mêmes.
- `EstablishmentWebSession.revoked_at` : révocations des 7 derniers
  jours ; `expires_at` : sessions actives arrivant à expiration sous 24 h.

La liste `my_sessions` est **strictement limitée aux appareils du
Superadmin connecté**. Pour chaque appareil, l'API ne renvoie que
l'identifiant de session, sa création, sa dernière activité, son expiration,
son statut courant et des catégories générales dérivées du navigateur/OS.
Ce sont des indices et non une identification fiable de l'appareil.

Aucune donnée ne doit être extrapolée. Les métriques absentes ou la
déconnexion serveur sont représentées par `—`, jamais par des valeurs
fictives.

## Sécurité des actions
```http
POST /api/v1/backoffice/security-v2/my-sessions/<id>/revoke/
Authorization: WebToken <session Superadmin MFA>
Content-Type: application/json

{"confirmation":"REVOQUER"}
```

- L'utilisateur doit ouvrir une **modale**, puis saisir exactement
  `REVOQUER`. Le backend vérifie aussi la confirmation, indépendamment
  du navigateur.
- **Interdiction de révoquer la session utilisée** ou une session
  appartenant à un autre utilisateur.
- Une session déjà expirée ou révoquée ne peut pas être révoquée de nouveau.
- Seule la session d'un **autre appareil du compte courant** est fermée.
  Le compte et son dispositif MFA ne sont pas supprimés ou réinitialisés.
- La révocation est transactionnelle et journalisée par
  `AuditLogEntry(action='sessions_revoked')`.
- Ni l'IP, ni le user-agent brut, ni token_hash, ni secret/code MFA ne
  figurent dans les réponses.
- L'ancienne API de gestion de sessions et les autres mécanismes
  de connexion restent inchangés.
- **Aucune migration**, aucun changement de schéma.

## Recette et tests
```bash
python manage.py test apps.api.v1.backoffice.tests_security_portal_e62 --settings=gconnect_api.settings.dev
node --test tests/security-e62.test.mjs
node scripts/verify-e62-security-visual.cjs
```

Les contrôles Chromium utilisent des événements fictifs uniquement dans
le banc d'essai isolé ; aucune révocation n'est exercée contre une base
locale ou de production. Les tests vérifient les contrastes WCAG AA,
desktop et mobile, la désactivation du bouton jusqu'à confirmation, et
l'impossibilité d'agir sur sa propre session active.

Les captures CI sont sous `artifacts/auth/e62-security-*.png`.

## Mise à jour Ubuntu sans risque
Vérifier `git status --short` dans chaque dépôt avant le changement de
branche ; en cas de modifications incompatibles, s'arrêter plutôt que
faire un `git reset --hard` ou `git clean`.

- Backend : `/mnt/chak/gconnect-api-e22` ;
  `feat/e54-integrate-e38-e53` ; port 8002 ;
  `GCONNECT_DEV_DB_PATH="$PWD/db.local.sqlite3"`.
- Frontend : `/mnt/chak/g-connect` ;
  `feat/e54-invitations-premium` ; port 5173.
- Une vérification de recette réelle reste nécessaire après la CI, avec
  les données et sessions effectivement présentes sur Ubuntu.

Ne pas exécuter de migration automatique ni réinitialiser les comptes,
sessions ou codes MFA. Les PR restent en brouillon sans fusion dans `main`.
