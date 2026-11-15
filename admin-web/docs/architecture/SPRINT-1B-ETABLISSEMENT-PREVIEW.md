# G-Connect — Sprint 1B : interface Établissement enrichie

## Livrable sur `feat/gconnect-establishment-portal-ui`

La navigation Modern Blue Glass (Manrope, bleu #3761FF, sidebar flottante repliable, tiroir mobile) est conservée.

Les sept écrans ont maintenant un rendu propre :
1. **Vue d’ensemble** : accueil, compteurs vides, parcours de préparation, accès rapides.
2. **Promotions & filières** : formulaire et liste de brouillons de promotions.
3. **Étudiants & Alumni** : annuaire non connecté, recherche et statut préparés.
4. **Événements & annonces** : formulaire et liste de brouillons d’événements.
5. **Équipe administrative** : brouillons d’invitations et descriptions de rôles.
6. **Abonnement & factures** : aperçu interactif de durées 1, 6 et 12 mois, sans tarif ni paiement fictif.
7. **Paramètres** : fiche institutionnelle en aperçu local.

## Frontière de sécurité

- Les brouillons vivent **uniquement en mémoire JavaScript**, durant l’onglet courant. Rafraîchir perd les modifications.
- Aucune requête réseau, aucune persistance locale, aucune invitation envoyée, aucun paiement et aucune authentification fictive.
- Les textes saisis sont échappés avant d’être insérés dans l’interface.
- Aucune donnée personnelle réelle d’étudiant/alumni ne doit être représentée avant la livraison du backend et des contrats de permission.
- Le serveur devra déterminer l’établissement courant et appliquer RBAC, isolation multi-organisations et quotas d’abonnement.

## Vérifications

- Syntaxe JavaScript vérifiée en moteur V8, navigation des sept pages et affichage sûr des brouillons vérifiés par simulation.
- `tests/etablissement.test.mjs` contient 7 tests statiques.
- GitHub Actions ajouté : `.github/workflows/establishment-ui-check.yml`, commande `node --check dist/etablissement.js` et `node --test tests/etablissement.test.mjs`.
- Le premier déclenchement GitHub Actions signale une erreur avant l’obtention de logs exploitables ; son succès **n’est pas attesté** et reste à investiguer dans l’onglet Actions.

## Reste à faire

1. Récupérer et auditer le backend de l’application mobile.
2. Définir les endpoints/contrats réels de l’espace Établissement.
3. Connecter authentification, permissions et données avec tests anti-fuite.
4. Construire ensuite les espaces Entreprise et Superadministrateur, puis le système d’abonnements réel.
