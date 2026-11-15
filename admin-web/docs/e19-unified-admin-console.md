# E19 — Console administrative commune (prévisualisation)
Date : 26 octobre 2026

## Décision validée
L'interface **Superadmin E18 approuvée** devient la seule référence graphique des consoles web professionnelles.
Les rôles **Superadmin** et **Établissement** partagent le même fichier `dist/admin-connected-e19.html`.
La variation se fait par la session authentifiée et par les permissions Django : identité, menus, fonctions et chiffres.
**Entreprise** est prévue, mais son authentification privilégiée n'est pas encore raccordée : aucun accès fictif n'est autorisé.

## Préservation
- Les écrans E16 et E18, le preview Superadmin et l'ancienne interface Établissement restent **inchangés** sur cette branche.
- Aucun fichier Django, SQLite, compte, MFA ou code de récupération n'est modifié.
- La base héritée contenant 129 comptes et les sauvegardes existantes doivent rester intactes. Leur fusion nécessite une migration testée séparément.
- Les services sur le port 8000 ne sont pas concernés.

## Contenu de l'incrément
- `dist/admin-login-e19.html` : la connexion E16 éprouvée, avec les deux rôles par URL.
- `dist/auth-shared-e19.js` : le parcours MFA existant en mémoire, puis la console partagée.
- `dist/admin-shared-e19.js` : frame de même origine, sans jeton dans le DOM, l'URL ou le stockage.
- `dist/admin-connected-e19.html` : design, topbar, sidebar, thèmes et animations E18 ; menus contrôlés par rôle.
- Superadmin : mêmes écrans et invitations autorisées qu'E18.
- Établissement : statistiques vérifiées provenant de `GET /api/v1/backoffice/stats/` dans le périmètre institution ; autres modules réservés en attente d'API. Aucun effectif inventé.
- Les liens directs et changements de hash ne peuvent naviguer vers un module non autorisé dans l'interface. Les contrôles de données restent côté Django.

## Essai local isolé
Arrêter **uniquement** l'ancien serveur statique sur 8094 (Ctrl+C dans son terminal), sans arrêter Django 8001.

```bash
cd /mnt/chak/g-connect
git fetch origin feat/e19-unified-admin-console
E19_PREVIEW=$(mktemp -d /mnt/chak/gconnect-e19.XXXXXX)
git archive FETCH_HEAD dist | tar -x -C "$E19_PREVIEW"
python3 -m http.server 8094 --bind 127.0.0.1 --directory "$E19_PREVIEW/dist"
```

Ouvrir après démarrage :
- Superadmin : http://127.0.0.1:8094/admin-login-e19.html#login/superadmin
- Établissement : http://127.0.0.1:8094/admin-login-e19.html#login/etablissement

Après vérification de la même présentation visuelle, de chaque rôle et des contrôles d'accès, intégrer l'interface commune dans le point d'entrée officiel. Cette branche est une étape réversible, sans fusion ni déploiement.

## Vérifications prévues
```bash
node --test tests/admin-e19-unified-shell.test.mjs
npm test
```

La validation visuelle réelle et les parcours MFA doivent être effectués sur le poste qui possède les sessions et la base Django. Les fonctions Entreprise seront implémentées après audit du backend, sans créer de faux comptes.
