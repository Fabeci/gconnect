# E59 | Modération & conformité · Premium V2

## Objectif

Remplacer le placeholder de la console Superadmin, sans toucher au shell
G-Connect validé, aux parcours Invitations, Factures, Offres & contenus,
Imports, Établissements ou Entreprises.

Identité graphique autonome : ardoise/bordeaux/rose, accent cuivre, héros
transparent et bouclier en orbite animé. Cartes et registres adaptatifs.
Modales détaillées sur chaque signalement, avec animations et prise en charge
de `prefers-reduced-motion`.

La correction E58 est également incluse :
`.e58-file-drop{height:auto}` et révision CSS afin de garder le texte
de confidentialité visible sous la zone de dépôt.

## Informations réelles

Les mesures sont issues de `Report` :
- À traiter : `status=pending`.
- Résolus : `status in (dismissed,actioned)`.
- Contrôles des 30 derniers jours : `reviewed_at >= J-30` et état traité.
- Alertes prioritaires : signalements en attente pour `harassment` ou `hate_speech`.
- Motifs : agrégats de tous les signalements en attente.
- Liste : recherche, filtres statut/cible/motif, pagination et détails.
- Actions : `dismiss` ou `hide_post` sur signalement non traité.

Aucun compteur de démonstration. Les valeurs apparaissent avec `—` avant la
réponse serveur ou en cas d'échec. Une erreur affiche un bouton de relance.

## API

Dépôt backend `gconnect_api`, branche `feat/e54-integrate-e38-e53` :

```http
GET /api/v1/backoffice/moderation-v2/?status=pending&target=all&reason=all&page=1&page_size=10
Authorization: WebToken <session Superadmin MFA>

POST /api/v1/backoffice/moderation-v2/123/decision/
Content-Type: application/json
Authorization: WebToken <session Superadmin MFA>

{
  "decision": "dismiss",
  "confirmation": "CONFIRMER",
  "reason": ""
}
```

Pour masquer une publication :
`decision=hide_post`, `confirmation=CONFIRMER` et justification entre
10 et 255 caractères.

Les décisions sont atomiques, vérifiées côté serveur et journalisées dans
`AuditLogEntry` (actions `report_reviewed` et, pour un masquage,
`post_hidden`). Un signalement déjà traité renvoie `409`. Une demande
de masquage d'utilisateur ou de commentaire est rejetée (cette première
version ne sait masquer que les publications).

La suppression, le bannissement de compte, la suppression de candidatures,
la révocation de sessions et l'édition des abonnements sont **hors périmètre**.
L'API de modération historique destinée aux clients existants reste inchangée.

Les données sont réservées aux comptes `superAdmin` avec MFA et WebToken
en cours de validité. Aucun mot de passe, secret MFA, document de candidature
ni jeton n'est inclus dans les réponses.

## Vérifications

- Backend :
  `python manage.py test apps.api.v1.backoffice.tests_moderation_portal_e59 --settings=gconnect_api.settings.dev`
- Frontend :
  `node --test tests/moderation-e59.test.mjs`
- Navigateur :
  `node scripts/verify-e59-moderation-visual.cjs`
- CI intégration : E38/E53 + E54/E57/E58/E59, contrôles sur base
  **jetable**, jamais sur la SQLite utilisateur.

Le navigateur de CI utilise des données fictives seulement pour le banc
de test (pas pour l'application), avec captures d'écran ordinateur/mobile,
contraste WCAG AA et scénario de confirmation.

## Démarrage Ubuntu sans perte des comptes

Avant toute mise à jour, vérifier `git status --short`. Ne pas exécuter
`git reset --hard`, `git clean` ni `migrate` sur la base historique
sans sauvegarde et validation séparée.

Terminal backend :

```bash
cd /mnt/chak/gconnect-api-e22
git status --short
git pull --ff-only origin feat/e54-integrate-e38-e53
source .venv/bin/activate
GCONNECT_DEV_DB_PATH="$PWD/db.local.sqlite3" \
  python manage.py runserver 127.0.0.1:8002 --settings=gconnect_api.settings.dev
```

Terminal frontend :

```bash
cd /mnt/chak/g-connect
git status --short
git pull --ff-only origin feat/e54-invitations-premium
GCONNECT_BACKEND_PORT=8002 PORT=5173 node scripts/serve-professional-portals.cjs
```

Ouvrir `http://127.0.0.1:5173/superadmin` puis **Modération**,
puis recharger le navigateur avec `Ctrl+Maj+R`.

**Attention :** E59 n'ajoute aucune migration. Les migrations plus anciennes
éventuellement en attente doivent être diagnostiquées indépendamment.
Ne pas masquer de véritables publications avant d'avoir examiné la fiche
et sauvegardé la base.
