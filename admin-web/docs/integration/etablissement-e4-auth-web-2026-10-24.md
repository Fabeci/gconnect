# E4 — Intégration web des invitations et de la double authentification (24/10/2026)

Branche du **fork personnel** `taogoulahtihamy-gif/g-connect` : `feat/auth-journey-premium`.
Frontend basé sur le travail de Codex `feat/auth-journey-premium`; backend attendu sur `feat/etablissement-e4-invitations-mfa` du fork `taogoulahtihamy-gif/gconnect_api`.

## Parcours disponibles

1. Le **Superadmin** se connecte par e-mail et mot de passe, configure (ou valide) son authentification TOTP, puis accède à un panneau **Inviter un responsable**. Il fournit l'identifiant de l'établissement actif et l'e-mail du responsable, visualise les 50 dernières invitations et peut révoquer celles en attente.
2. Le destinataire ouvre `/etablissement-activation.html#invitation=<secret>` depuis son e-mail. Le secret est retiré immédiatement de l'URL affichée, une prévisualisation d'établissement/e-mail est demandée au backend, puis le destinataire choisit son nom et son mot de passe. L'invitation est à usage unique et expire après 48 h.
3. Après activation, la page de connexion Établissement accepte le mot de passe puis exige une seconde étape. Pour le premier accès, la clé TOTP doit être ajoutée manuellement dans une application d'authentification. Les **huit codes de secours** fournis par le backend sont montrés une seule fois.
4. À chaque connexion suivante, un code TOTP ou un code de secours valide est requis. Aucun module Établissement n'est affiché avant confirmation MFA.
5. Le token d'accès est exclusivement en **mémoire JavaScript** ; les appels privilégiés utilisent `Authorization: WebToken …`. La déconnexion révoque le token côté serveur ; aucun secret de session n'est enregistré dans `localStorage`, `sessionStorage` ou un cookie par le frontend.
6. La connexion étudiant/alumni reste branchée sur l'API mobile existante (`Token`) et n'utilise pas la procédure E4.

## Démarrer localement

Dans le clone frontend, sur la branche `feat/auth-journey-premium` :

```bash
npm test
npm run test:auth
GCONNECT_BACKEND_PATH=/mnt/chak/gconnect-api-fabeci npm run test:auth:live
python3 -m http.server 8086 --directory dist
```

Dans le clone backend, utiliser sa base SQLite de développement **isolée** et lancer Django sur le port 8001 :

```bash
cd /mnt/chak/gconnect-api-fabeci
source .venv/bin/activate
export GCONNECT_DEV_DB_PATH=/mnt/chak/gconnect-api-fabeci/.venv/gconnect-web-e1.sqlite3
export GCONNECT_WEB_APP_URL=http://127.0.0.1:8086
python -B manage.py migrate --settings=gconnect_api.settings.dev
python -B manage.py runserver 127.0.0.1:8001 --settings=gconnect_api.settings.dev
```

Dans le navigateur :

- `http://127.0.0.1:8086/auth.html` pour le choix des trois espaces ;
- `http://127.0.0.1:8086/etablissement-connexion.html` pour Établissement ;
- le lien d'invitation est expédié par le backend (en DEV, il peut être affiché dans le terminal Django selon le backend e-mail).

## Vérifications prioritaires

- **MFA** : challenge n'accorde aucun accès avant validation ; un code faux et un code TOTP réutilisé sont refusés ; le verrouillage est serveur.
- **Invitation** : invalide/expirée/révoquée/consommée affichent une erreur ; seules les invitations envoyées par le Superadmin créent des comptes établissement.
- **Accès** : connexion Établissement à un autre rôle interdite ; statistiques obligatoirement `scope=institution` avec établissement associé.
- **Logout** : token révoqué côté serveur et supprimé en mémoire même en cas d'erreur réseau.
- **Production** : configurer SMTP transactionnel, `DEFAULT_FROM_EMAIL`, `SECRET_KEY` stable et forte, `GCONNECT_WEB_APP_URL` HTTPS, CORS et CSP. Vérifier que `/admin/` Django est isolé ou protégé par MFA équivalente (hors périmètre E4).

## Résultats vérifiés

- `npm test` : 5 suites réussies.
- `npm run test:auth` : 46 audits fonctionnels, WCAG A/AA et responsive réussis sur 320, 390, 768 et 1440 px, y compris les écrans E4 critiques.
- Tests Django `tests_privileged_auth_e4` + `tests_web_sessions_e3` : 17 réussis sur une base SQLite isolée.
- `npm run test:auth:live` : parcours réel Superadmin MFA → invitation console → activation → MFA Établissement → tableau de bord → déconnexion → code de secours réussi.

## Limites et suites

- Le panneau Superadmin E4 se limite à l'envoi, la consultation et la révocation d'invitations. Il **ne fournit pas encore** la gestion complète des établissements ni un sélecteur déroulant alimenté par l'API ; l'identifiant numérique est à renseigner.
- Le secret TOTP est fourni pour ajout manuel dans l'application ; aucun QR code distant n'est utilisé pour ne pas transmettre le secret à un service tiers.
- L’envoi d’e-mail réel n’est possible qu’après paramétrage SMTP. Le test `test:auth:live` valide le contrat sur une base et un serveur Django isolés avec le backend console ; la délivrabilité SMTP de production reste à contrôler dans l’environnement de déploiement.
- GitHub Actions peut être bloqué par le plafond de dépenses du compte : une réussite des tests locaux ne constitue pas une preuve de CI.
