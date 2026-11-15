# E58 | Imports & opérations groupées · G-Connect Premium V2

## Le module

L'ancien écran provisoire est remplacé par un atelier Superadmin distinct, au style
bleu-menthe et cuivre, sans bannière opaque et avec les animations usuelles de G-Connect.
Les cartes, le haut de page, les panneaux et la modale sont indépendants des interfaces
Entreprises, Établissements, Factures, Invitations et Offres.

Ce module utilise **les imports réellement enregistrés dans Django** (`ImportJob`).
Il n'invente ni chiffres, ni ligne de démonstration, ni statut de traitement.

### Fonctionnalités E58

- Compteurs réels : imports enregistrés, lignes intégrées, erreurs et établissements importés.
- Historique paginé, filtre par type, date, nom du fichier, destination et résultat.
- Téléchargement de modèles CSV pour chaque catégorie.
- Dépôt de fichiers CSV UTF-8 / XLSX, 2 Mo maximum, 500 lignes maximum.
- Choix d'établissement, recherche limitée aux établissements actifs.
- Prévisualisation côté Django **sans écriture**, avec échantillon, anomalies et colonnes.
- Signature temporaire de prévisualisation (10 minutes), associée au contenu du fichier,
  au type et à la destination.
- **Exécution seulement après confirmation expresse**, avec résultat et journalisation.
- Traitement atomique (toutes les lignes de promotions ou d'établissements, sinon aucune).
- Modales riches, animation des cartes et de l'illustration, thème sombre et mode sans animations.

### Matrice des opérations

| Type | Prévisualisation | Exécution E58 | Justification |
|---|---|---|---|
| Établissements | Oui | Oui, après confirmation | Catalogue administratif |
| Promotions | Oui | Oui, pour un établissement actif | Catalogue pédagogique |
| Étudiants | Oui | **Non** | L'ancien import créait des comptes actifs et des mots de passe temporaires |
| Alumni | Oui | **Non** | Un parcours d'activation de compte sécurisé reste à concevoir |

Les colonnes acceptées sont décrites dans les modèles téléchargeables.

**E58 n'ajoute aucune migration ni ne remplace l'ancienne API mobile.** Les nouvelles
routes constituent un couloir sécurisé réservé aux Superadmins ayant une session
WebToken confirmée par MFA.

## Contrat API

Sur la branche `feat/e54-integrate-e38-e53` du dépôt `gconnect_api` :

```http
GET  /api/v1/backoffice/imports-v2/?page=1&type=all
POST /api/v1/backoffice/imports-v2/preview/
POST /api/v1/backoffice/imports-v2/execute/
Authorization: WebToken <jeton MFA>
```

Les deux POST utilisent `multipart/form-data` : `file`, `import_type`,
`institution` (sauf pour `establishments`). Execute exige en plus
`confirmation=CONFIRMER` et le `preview_token` renvoyé par Preview.

La réponse GET ne publie pas `created_rows`, car l'ancienne implémentation pouvait y
conserver les mots de passe temporaires générés pour des importations de comptes.
La nouvelle implémentation ne produit aucun mot de passe et ne retourne que les
champs nécessaires à la supervision.

Le serveur rejette les fichiers trop volumineux, les colonnes répétées, les types
inconnus, les doublons détectés, les prévisualisations modifiées ou expirées, les
appels anonymes et les rôles non Superadmin.

## Démarrer localement sans changer les bases

**Vérifiez d'abord les modifications locales** avec `git status --short`, puis
mettez à jour uniquement les branches de développement existantes, sans
`git reset --hard`, `git clean` ni changement de base.

Backend :

```bash
cd /mnt/chak/gconnect-api-e22
git status --short
git pull --ff-only origin feat/e54-integrate-e38-e53
source .venv/bin/activate
GCONNECT_DEV_DB_PATH="$PWD/db.local.sqlite3" \
  python manage.py runserver 127.0.0.1:8002 --settings=gconnect_api.settings.dev
```

Frontend :

```bash
cd /mnt/chak/g-connect
git status --short
git pull --ff-only origin feat/e54-invitations-premium
GCONNECT_BACKEND_PORT=8002 PORT=5173 node scripts/serve-professional-portals.cjs
```

Accéder à la console Superadmin > **Imports**.

**Aucune migration nouvelle pour E58.** Les autres migrations éventuellement en
attente doivent être vérifiées indépendamment, avec sauvegarde de la base historique
avant toute évolution.

## Validation

- Django : `python manage.py test apps.api.v1.backoffice.tests_import_portal_e58 --settings=gconnect_api.settings.dev`
- Node : `node --test tests/imports-e58.test.mjs`
- Chromium : `node scripts/verify-e58-imports-visual.cjs`

Le test navigateur n'utilise qu'une réponse simulée respectant le contrat API ;
il ne confirme pas la réussite d'un import sur la base locale de l'utilisateur.
La recette manuelle doit être effectuée avec **un fichier de test non sensible** et
une sauvegarde de la base locale avant le premier véritable import.

La création de comptes étudiants/alumni reste volontairement à traiter dans un
sprint ultérieur dédié à l'enrôlement sécurisé.
