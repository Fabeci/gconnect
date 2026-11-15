# G-Connect — Sprint 1A : aperçu Admin Établissement

Ce lot est un **prototype de navigation**, réalisé sans backend et sans données personnelles. Il ne constitue **pas** un portail authentifié ni un produit déployable en production.

## Accès local

Depuis le dépôt GitHub cloné localement :

```bash
cd /mnt/chak/g-connect/dist
python3 -m http.server 8081
```

Ouvrir **http://localhost:8081/etablissement.html**.

L'interface étudiante actuelle reste accessible sur **http://localhost:8081/**.

## Périmètre

- Design Modern Blue Glass : bleu `#3761FF`, Manrope, logo officiel, fond glacé, panneaux arrondis.
- Sidebar flottante et réduite ; en mode réduit, la loupe rétablit la recherche.
- Navigation desktop, tablette et tiroir mobile, fermeture avec Échap.
- Sept sections : vue d'ensemble, promotions et filières, étudiants et alumni, événements et annonces, équipe administrative, abonnement et factures, paramètres.
- Recherche **locale** sur les intitulés des modules ; aucun appel API.
- États vides sans métriques fictives : tous les indicateurs restent « — ».

## Limitations volontaires

Pas de vraie session, de vérification des permissions, de données d'organisation, d'invitation, de paiement ni de facturation. Ne pas exposer ce prototype comme un portail d'administration réel. L'accès à `etablissement.html` reste public tant qu'aucune authentification serveur n'est intégrée.

## Suite après réception du backend mobile

1. Identifier les contrats d'identité existants sans les remplacer.
2. Établir les contrôles serveur de rôle et d'appartenance à l'organisation.
3. Mettre en œuvre les listes, états de chargement/erreur et actions autorisées.
4. Vérifier par tests d'intégration que l'organisation A ne peut ni lire ni modifier les données de B.
5. Préparer ensuite les portails Entreprise et Superadministration sur le même design system.

## Tests

```bash
node --check dist/etablissement.js
node --test tests/etablissement.test.mjs
```

Les contrôles de ce lot sont des tests statiques ; la validation responsive visuelle et les tests API restent à exécuter.
