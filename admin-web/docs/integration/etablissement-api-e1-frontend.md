# G-Connect — Établissement web : intégration E1 (22 octobre 2026)

## Périmètre

Branche frontend `feat/etablissement-api-e1-frontend`, depuis `feat/gconnect-frontend-snapshot-20261022`. Aucun changement à l'espace Étudiants ou au backend de Fabeci.

- Les sept modules Établissement, la navigation et les animations restent présents.
- Le tableau de bord peut afficher **les statistiques réelles de l'établissement connecté uniquement**, via le backend G-Connect.
- Les autres modules continuent de préparer des brouillons locaux : leurs écritures serveur ne sont **pas** activées.

## Contrat utilisé

1. `POST /api/v1/users/login/` avec `email` et `password`. Le client exige le rôle `etablissement`.
2. `GET /api/v1/users/me/` avec `Authorization: Token <jeton>`. Le client exige `institution_id` et le même rôle.
3. `GET /api/v1/backoffice/stats/` avec le même jeton. Le client exige `scope: institution`.

Le client ne conserve jamais le jeton dans localStorage, sessionStorage ou l'URL. La session de cet onglet disparaît après rechargement ou sélection de « Fermer la session locale ». **Cette fermeture ne révoque pas le jeton côté serveur.** Une vraie gestion multi-appareils et révocation devra être convenue avec Fabeci avant un déploiement de production.

## Configuration

Sur localhost ou 127.0.0.1, l'API de développement est détectée sur le port 8000 (`/api/v1`). Le backend du fork autorise explicitement les origines web de développement sur 8080 et 8086.

Sur un domaine externe, définir explicitement une base API HTTPS par `window.GCONNECT_API_BASE_URL` avant `etablissement-api.js`, ou par une balise `meta[name="gconnect-api-base"]`. Sans configuration, aucun appel distant n'est lancé.

## Tests à lancer

```bash
node --test tests/frontend.test.mjs tests/etablissement.test.mjs tests/etablissement-api.test.mjs
```

Pour la validation visuelle si Chromium/Playwright est disponible, démarrer le site statique sur 8086 et réexécuter `scripts/verify-etablissement-glass.cjs`. Vérifier aussi manuellement :

- Sans connexion : aucun chiffre inventé, cartes avec tirets.
- Avec un compte d'administration **autorisé** : nom et statistiques de son établissement seulement.
- Avec un compte étudiant ou non rattaché : refus.
- Mauvais mot de passe / serveur arrêté : erreur lisible, aucune session.
- Sur mobile : connexion, navigation, thèmes, animations et focus clavier.
- Après rechargement : retour à la prévisualisation sans jeton en stockage persistant.

## Ce qui reste

- Confirmer les essais réels avec le backend de développement et des comptes explicitement autorisés.
- Auditer les listes Promotions/Membres/Événements, les règles de visibilité et les actions d'écriture avant raccordement.
- Définir avec Fabeci la stratégie de jetons par appareil et leur révocation.
- Ne pas toucher aux données ou à la base du backend partagé pendant ces tests.
