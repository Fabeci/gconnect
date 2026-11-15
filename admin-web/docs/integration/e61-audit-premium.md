# E61 · Journal d'audit Premium V2

## Portée
Revaloriser **exclusivement** le module `Journal d’audit` Superadmin.
Conserver le shell E19, le style de navigation et toutes les pages précédentes
(E38 Factures, E54 Invitations, E57 Offres & contenus, E58 Imports, E59
Modération, E60 Statistiques), ainsi que les espaces Entreprise/Établissement.

## Identité visuelle
- Page avec palette spécifique encre, mauve et cuivre, raccordée aux couleurs
  G-Connect mais distincte de la page Statistiques.
- **Haut transparent**, illustration de document audité flottant et orbites
  animées. Aucune carte géante opaque ou bouton pleine largeur.
- Quatre cartes indicatrices cliquables (Événements, Invitations,
  Modérations, Accès & connexions).
- Liste chronologique réelle des événements, recherche utilisateur/action,
  filtres par catégorie et action, pagination.
- Panneau latéral : histogramme historique réel, connexions échouées,
  opérations sensibles, répartition par catégorie.
- Au clic d'une entrée : **fenêtre modale** affichant sa date, l'acteur,
  le rôle, la catégorie, le code d'action et les références autorisées.
- Animations d'entrée, au survol et du graphique. Responsive, thème sombre,
  `prefers-reduced-motion`.

## Source métier
Le backend lit le modèle **`AuditLogEntry`** existant et aucun autre flux
inventé. Tous les compteurs utilisent les données effectivement enregistrées.
Les périodes disponibles sont 7, 30, 90 et 180 jours. La tendance est
agrégée au jour, à la semaine ou au mois selon la fenêtre.

Seuls les événements inscrits via `log_audit_event` ou enregistrés dans la
même table sont visibles : le registre ne peut pas reconstituer les actions
historiques qui n'ont jamais été journalisées. La consultation ne génère
pas elle-même un nouvel événement, afin de ne pas fausser les compteurs.

La recherche textuelle porte sur le nom d'acteur, le nom d'utilisateur,
le code action et son libellé lisible. Les données affichées ne comportent
jamais de chiffre de démonstration. `—` signifie chargement/indisponibilité.

## Protection des données

```http
GET /api/v1/backoffice/audit-v2/?days=30&category=all&action=all&page=1&page_size=12
Authorization: WebToken <session Superadmin MFA>
```

- Accès `IsAuthenticated + IsSuperAdmin` via WebToken MFA.
- Uniquement GET, aucune écriture, révocation, suppression ni migration.
- `Cache-Control: no-store`.
- Pagination limitée aux tailles 12/24/48, périodes bornées.
- Une ancienne entrée peut contenir des secrets dans `metadata` :
  **le JSON brut n'est jamais transmis au navigateur**. Seules quelques
  références entières et valeurs d'énumération vérifiées sont exposées.
- Aucune adresse IP, cookie, session token, mot de passe ou fichier personnel
  n'est exposé par cet endpoint. Le texte libre du motif est exclu.
- Les éventuelles entrées d'action inconnue sont placées dans « Autres »
  et présentées sous un libellé neutre.

L'ancien endpoint `/backoffice/audit-log/` reste inchangé pour éviter
une régression de ses clients, mais **ne doit pas** être utilisé dans E61 :
il expose les anciennes métadonnées brutes.

## Vérifications
- Django :
  `python manage.py test apps.api.v1.backoffice.tests_audit_portal_e61 --settings=gconnect_api.settings.dev`
- Node :
  `node --test tests/audit-e61.test.mjs`
- Chromium :
  `node scripts/verify-e61-audit-visual.cjs`

Les tests navigateur utilisent des événements **fictifs seulement en CI**,
jamais dans la page de production. Le script écrit des captures desktop
et mobile dans `artifacts/auth/`. Accessibilité WCAG AA vérifiée.

## Démarrage local et protection de la SQLite historique

Vérifier `git status --short` avant de mettre à jour les branches
`feat/e54-integrate-e38-e53` (backend) et
`feat/e54-invitations-premium` (frontend).

Ne jamais employer `reset --hard`, `clean` ou `migrate` sans contrôle
préalable de la base et sauvegarde. E61 ne demande aucune migration.

Serveur backend : port 8002, configuration
`gconnect_api.settings.dev` avec `GCONNECT_DEV_DB_PATH` pointant sur
`db.local.sqlite3` historique. Frontend : port 5173, lié au port backend
par `GCONNECT_BACKEND_PORT=8002`.

La validation CI ne remplace pas la recette sur les journaux réellement
enregistrés localement.
