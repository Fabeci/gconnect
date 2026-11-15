# G-Connect E54.4 | Raccordement et validation des invitations

## Versions de référence

- Backend Django : `gconnect_api / feat/e54-integrate-e38-e53`
- Frontend Premium V2 : `g-connect / feat/e54-invitations-premium`
- Les PR backend #5 et frontend #6 restent en brouillon. Ne pas remplacer `main`.

## Contrats HTTP validés

Les fonctions E54 utilisent les URL Django suivantes, sous `/api/v1` :

| Étape | Méthode | Chemin | Autorisation |
|---|---|---|---|
| Superadmin : liste/création entreprise | GET/POST | `/users/admin/enterprise-invitations/` | WebToken MFA Superadmin |
| Superadmin : révocation entreprise | POST | `/users/enterprise/invitations/{id}/revoke/` | WebToken MFA Superadmin |
| Entreprise : liste/création recruteurs | GET/POST | `/users/enterprise/invitations/` | WebToken MFA Responsable |
| Entreprise : liste recruteurs | GET | `/users/enterprise/recruiters/` | WebToken MFA Responsable |
| Responsable : révocation recruteur | POST | `/users/enterprise/recruiters/{id}/revoke/` | WebToken MFA Responsable |
| Invitation : prévisualisation | POST | `/users/enterprise/invitations/preview/` | Publique, jeton à usage unique |
| Invitation : acceptation | POST | `/users/enterprise/invitations/accept/` | Publique, jeton à usage unique |
| Équipe : tableau de bord | GET | `/users/enterprise/dashboard/` | WebToken MFA Entreprise |
| Recruteur : offres | GET | `/users/enterprise/offers/` | WebToken MFA Entreprise |
| Recruteur : candidatures par offre | GET | `/users/enterprise/offers/{id}/applications/` | WebToken MFA Entreprise |

Les autorisations et l'isolation multi-entreprises sont appliquées par Django et non par les seuls boutons du frontend.

## Mise en route locale, sans publier de données

Dans le dépôt backend, utiliser le virtualenv et les paramètres de développement habituels :

**Arrêter Django avec Ctrl+C avant cette opération.** Le script sélectionne la base réelle depuis les paramètres Django (y compris `GCONNECT_DEV_DB_PATH`), vérifie son intégrité, conserve une sauvegarde privée sous `~/GConnect-Sauvegardes`, puis applique les migrations. Si la sauvegarde ne peut pas être créée, il n'applique aucune migration.

```sh
cd /mnt/chak/gconnect-api-e22
git fetch origin
git switch feat/e54-integrate-e38-e53
python scripts/e54_safe_migrate.py  # Sauvegarde SQLite vérifiée hors dépôt, puis migrations users 0013/0014
python manage.py test apps.api.v1.users.tests_invitations_http_e54_4 --settings=gconnect_api.settings.dev --noinput
python manage.py runserver 127.0.0.1:8002 --settings=gconnect_api.settings.dev
```

Dans un autre terminal frontend :

```sh
cd /mnt/chak/g-connect
git fetch origin
git switch feat/e54-invitations-premium
GCONNECT_BACKEND_PORT=8002 PORT=5173 node scripts/serve-professional-portals.cjs
```

**Important :** dans l'environnement Django, définir `GCONNECT_WEB_APP_URL=http://127.0.0.1:5173` pour que les e-mails de développement pointent vers le serveur frontend utilisé. Avec `DEBUG=True`, le backend de courrier console peut afficher le lien dans la sortie Django. Pour un appareil distant, `127.0.0.1` ne convient pas : il faut un site HTTPS accessible.

Vérifier la route d'activation :

```sh
curl -I http://127.0.0.1:5173/entreprise-activation.html
```

Résultat attendu : HTTP 200, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`. La page renvoie vers `/entreprise#login/entreprise` après activation.

## CI et tests

- Frontend Node : `node --test tests/three-portals-routes.test.mjs tests/invitations-e54.test.mjs`
- Frontend navigateur : `node scripts/verify-e54-enterprise-activation.cjs`
- Django : `python manage.py test apps.api.v1.users.tests_invitations_http_e54_4 --settings=gconnect_api.settings.dev --noinput`
- CI : GitHub Actions vérifie les tests frontend, authentification et régressions Django E38/E53.

Les essais automatiques utilisent un serveur HTTP simulant le backend côté navigateur et un moteur e-mail **en mémoire** côté Django. Ils n'attestent pas une livraison SMTP publique.

## Étapes obligatoires avant production

1. Déployer le backend E54 et vérifier les migrations Django, sans migration destructive.
2. Configurer `GCONNECT_WEB_APP_URL` avec l'origine **HTTPS réelle** du frontend, non l'URL du backend ni `127.0.0.1`.
3. Configurer le SMTP réel et `DEFAULT_FROM_EMAIL` dans les variables d'environnement du serveur. Ne jamais les committer.
4. Tester sur un environnement de préproduction avec des boîtes test autorisées : invitation, réception du mail, activation, première MFA, connexion et reprise après rafraîchissement.
5. Vérifier l'expiration 48 h, la révocation de l'invitation, la révocation du recruteur et la fermeture de ses sessions.
6. Confirmer qu'un recruteur ne peut pas modifier les abonnements, paiements, factures ou accès des autres équipes.
7. Après validation seulement, envisager la fusion des PR de revue.

**Ne jamais publier :** fichiers `.env`, bases `db.sqlite3`, copies `.bak`, identifiants SMTP, jetons d'activation ou codes de secours MFA.
