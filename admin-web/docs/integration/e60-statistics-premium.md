# E60 · Statistiques globales Premium V2

## Objet et périmètre
Remplacer **uniquement** le placeholder `Statistiques` du Superadmin par un
observatoire fiable, sans altérer le shell E19, les pages Invitations E54,
Factures E38, Offres E57, Imports E58, Modération E59 ni les autres espaces.

Les anciens blocs chiffrés et courbes fictives de la page Statistiques
sont remplacés par des agrégats issus de Django. Les illustrations animées du
haut de page sont décoratives : elles ne portent aucune valeur statistique.

Identité Premium autonome : porcelaine, iris bleu et vert lagon,
en-tête **transparent** inspiré de la page Factures, cartes animées,
graphiques SVG bâtis à partir de l'API, modales de définition des indicateurs,
responsive et thème sombre, `prefers-reduced-motion`.

## Indicateurs réels
- Nouveaux comptes : utilisateurs dont `date_joined` appartient à la
  période choisie. Comparaison avec la période immédiatement précédente.
  Le pourcentage de croissance est **indéfini (`null`)** si la période
  précédente ne contient aucun compte, et non artificiellement 0 %.
- Comptes enregistrés : total `User`, tous rôles.
- Entreprises vérifiées : `Enterprise.is_active=True` et
  `verified_at IS NOT NULL`; ne signifie pas « revenu vérifié ».
- Établissements actifs : `Institution.is_active=True`.
- Profil des utilisateurs : comptage sur cinq rôles.
- Répartition du contenu : comptage de cinq catégories de `Post`.
- Publications publiées : non masquées, non archivées, non brouillon.
- Candidatures : total du registre `Application`.
- Abonnements en cours : `BusinessSubscription.status=active` et dates
  de validité couvrant le jour courant. **Pas une preuve de paiement**.
- Signalements en attente : `Report.status=pending`.
- Tendances : comptes enregistrés (`User.date_joined`), nouvelles publications
  (`Post.created_at`), établissements créés (`Institution.created_at`) et
  **comptes propriétaires d'entreprises** (`Enterprise.user.date_joined`).
  Cette dernière courbe n'est **pas** une série de dates de vérification.

## Périodes
- 30 jours : regroupement par jour.
- 90 jours : regroupement par semaine (lundi).
- 180 jours : regroupement par mois.
- 365 jours : regroupement par mois.

Les séries renvoient les intervalles de calendrier réels, y compris les
jours/semaines/mois sans événement (zéros factuels). Chaque valeur du
navigateur provient de l'API. En cas de panne ou de refus d'accès, les
indicateurs affichent `—`, jamais des données inventées.

## Endpoints et protection

Branche backend `gconnect_api/feat/e54-integrate-e38-e53` :

```http
GET /api/v1/backoffice/statistics-v2/?days=180
Authorization: WebToken <Superadmin MFA>
```

- `IsAuthenticated` + `IsSuperAdmin`, WebToken délivré après MFA.
- Réponse agrégée, sans e-mails, mots de passe, fichiers, secrets ou données
  nominatives.
- `Cache-Control: no-store`.
- Paramètre `days` limité strictement à `30`, `90`, `180`, `365`.
- Aucune écriture ou migration.
- L'ancien endpoint `/api/v1/backoffice/stats/` reste intact pour les clients
  existants.

## CI et recette

Django :
`python manage.py test apps.api.v1.backoffice.tests_statistics_portal_e60 --settings=gconnect_api.settings.dev`

Node :
`node --test tests/statistics-e60.test.mjs`

Chromium :
`node scripts/verify-e60-statistics-visual.cjs`

Le navigateur en CI utilise une **fixture isolée** et vérifie le style
transparent, les animations, l'accessibilité WCAG AA, les courbes, le
changement de période, la modale de provenance et le rendu mobile.
**La validation des données réelles sur ton environnement Ubuntu reste une
étape de recette distincte.**

Pour mettre à jour le backend et le frontend, vérifier les modifications
locales avec `git status --short` dans chaque dépôt ; utiliser les mêmes
branches E54. Ne pas lancer `git reset --hard`, `git clean` ou
`migrate` de manière automatique sur la base historique.
