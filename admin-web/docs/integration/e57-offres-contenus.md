# E57 | Offres & contenus · Superadmin Premium V2

## Périmètre effectivement livré

La page `Offres & contenus` remplace le placeholder local de la console Superadmin par un observatoire éditorial **en lecture seule**, alimenté par les modèles Django `Post`, `Opportunity` et `Report`.

**Règle de conception :** chaque page garde son identité propre. E57 utilise une composition éditoriale sans bannière opaque, une constellation de cartes, des accents lavande/corail et des animations non bloquantes. Les pages Factures (E38), Invitations (E54/E56), Entreprises et Établissements conservent leur structure.

### Capacités

- Résumé réel : publications, opportunités, événements, signalements en attente.
- Répartition calculée depuis le backend : opportunités, événements, projets et discussions/partages.
- Catalogue paginé des contenus de toutes les organisations, trié par date décroissante.
- Recherche par titre, description, auteur, établissement et entreprise.
- Filtres de type `all / opportunity / event / project / discussion / share`.
- Filtres d'état exclusifs `all / published / draft / hidden / archived`.
- Fiche détaillée en modal, avec auteur, organisation, audience, engagement, signalements et statut réel.
- Chargement, erreur visible, relance, résultat vide et navigation entre pages. Pas de nombres inventés.
- Animation du héros, des métriques, des cartes et des barres, avec support mobile, `prefers-reduced-motion` et du thème sombre.

La modération active (masquer, suspendre, supprimer ou restaurer) **n'est pas incluse** dans ce module, volontairement. Aucune opération n'écrit dans `Post`, `Report` ou les quotas de publication.

## Contrat backend

Dépôt : `gconnect_api`, branche `feat/e54-integrate-e38-e53`.

```http
GET /api/v1/backoffice/content-directory/?type=all&state=all&search=&page=1&page_size=12
Authorization: WebToken <token-de-session-MFA>
```

Réponse `data` :

```json
{
  "summary": {
    "total": 0,
    "opportunities": 0,
    "events": 0,
    "projects": 0,
    "discussions": 0,
    "published": 0,
    "drafts": 0,
    "archived": 0,
    "hidden": 0,
    "reports_pending": 0
  },
  "count": 0,
  "page": 1,
  "pages": 1,
  "page_size": 12,
  "results": []
}
```

Les valeurs 0 sont un *exemple de schéma JSON*, pas des mesures réelles. Le navigateur affiche `—` tant que la réponse valide n'est pas chargée.

Accès : **Superadmin avec MFA et WebToken valides uniquement**, contrôle côté Django. Un invité reçoit `401`; les autres rôles reçoivent `403`. Pas d'information sur les identifiants privés, mots de passe, pièces jointes de candidature ni secrets MFA.

La pagination (1 à 50 éléments) et les filtres sont validés par le serveur. Aucun modèle ni migration nouveaux dans E57.

## Mise à jour locale sans perte des comptes

Les deux dépôts doivent être mis à jour avec les *branches distinctes* correspondantes. Avant un `git pull`, contrôler `git status --short` et préserver toute modification locale.

```sh
cd /mnt/chak/gconnect-api-e22
git status --short
git pull --ff-only origin feat/e54-integrate-e38-e53
```

Pour le backend, **conserver la base historique** `db.local.sqlite3`, déjà identifiée comme contenant le compte `superadmin@gconnect.com` :

```sh
cd /mnt/chak/gconnect-api-e22
source .venv/bin/activate
GCONNECT_DEV_DB_PATH="$PWD/db.local.sqlite3" python manage.py runserver 127.0.0.1:8002 --settings=gconnect_api.settings.dev
```

Lancer le frontend dans un autre terminal :

```sh
cd /mnt/chak/g-connect
git status --short
git pull --ff-only origin feat/e54-invitations-premium
GCONNECT_BACKEND_PORT=8002 PORT=5173 node scripts/serve-professional-portals.cjs
```

Ouvrir `http://127.0.0.1:5173/superadmin` et choisir **Offres & contenus**. Recharger la page avec `Ctrl+Maj+R` si le navigateur a conservé l'ancien JS/CSS.

**Important :** ne pas appliquer automatiquement les migrations anciennes encore en attente, ni remplacer les deux bases SQLite. Vérifier séparément leur état et sauvegarder avant toute évolution du schéma. E57 n'en ajoute aucune.

## Validation

- Backend : `python manage.py test apps.api.v1.backoffice.tests_content_directory_e57 --settings=gconnect_api.settings.dev --noinput`.
- Frontend : `node --test tests/contents-e57.test.mjs`.
- Chromium : `node scripts/verify-e57-contents-visual.cjs`.
- CI backend : suite E38/E53/E54 + tests E57, sans base de données utilisateur.
- CI frontend : tests des autres modules E54/E38, puis fixture visuelle E57 + audit WCAG AA.

La CI valide les contrats et une fixture navigateur, **pas** un accès direct à la base SQLite locale de l'utilisateur.
