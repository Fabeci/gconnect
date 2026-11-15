# G-Connect — Superadmin E8 (variante visuelle)

Branche : `feat/e8-superadmin-etablissement-premium`

Base conservée : `feat/e5-etablissement-icons-motion`. L'interface
Établissement, les écrans Étudiant/Alumni et le backend Django ne sont pas
modifiés.

## Objectif

Une console de supervision avec la même grammaire visuelle que l'espace
Établissement : bleu G-Connect, Manrope, verre dépoli, logo, icônes fines,
cartes arrondies, contraste lisible et animations accessibles.

## Démarrage local

Depuis la copie Git `g-connect` :

```bash
git fetch origin feat/e8-superadmin-etablissement-premium
git switch --track origin/feat/e8-superadmin-etablissement-premium
python3 -m http.server 8086 --bind 127.0.0.1 --directory dist
```

Ouvrir : http://127.0.0.1:8086/superadmin-preview.html#dashboard

Si le port 8086 est occupé par ce même serveur, ne pas en ouvrir un second.
Actualiser le navigateur avec Ctrl+Maj+R.

## Modules visuels

- Pilotage : vue d'ensemble, établissements, entreprises, recruteurs,
  utilisateurs.
- Accès et revenus : abonnements, factures et paiements, invitations,
  offres et contenus.
- Contrôle : modération, imports, statistiques, journal d'audit,
  sessions et sécurité, paramètres.

Total : 15 vues.

## Animations

- Transitions d'apparition par bloc avec décalage progressif.
- Icônes, survols, effets de clic, carte active et navigation.
- Compteurs animés pour les exemples chiffrés, graphiques progressifs.
- Réseau illustré et animé sur le tableau de bord.
- Transition de thème, interactions clavier (Ctrl/Cmd+K pour la recherche).
- Un sélecteur permet de forcer les animations lors des essais ou de les couper.
- Respect du réglage système « réduire les animations » par défaut.

## Contrat de facturation cible

L'espace Établissement montre trois durées : **1, 6 ou 12 mois**.
La page Superadmin E8 utilise les mêmes trois durées. Aucun montant
fictif n'est indiqué et aucun paiement n'est réalisé.

Flux métier à implémenter ultérieurement côté Django :

1. Organisation éligible + période d'abonnement.
2. Facture/référence de paiement unique.
3. Confirmation de règlement **côté serveur** (signature, montant,
   devise, idempotence) ou rapprochement contrôlé.
4. Abonnement et droits actifs rattachés à l'organisation.
5. Invitation E4 (e-mail) puis activation et MFA.
6. Renouvellement, suspension, expiration et audit, sans contourner RBAC.

Les endpoints E4 d'invitation et d'authentification restent inchangés.
Les modules Abonnements et Facturation sont actuellement **des maquettes** :
aucun appel de paiement ni contrôle d'abonnement backend n'est livré.

## Validation

`npm test` : **52 tests réussis**, dont un test d'ouverture des 15 routes.
La vérification visuelle dans Firefox (bureau et mobile) reste à faire
sur le poste utilisateur : aucun navigateur de test n'a été installé
dans l'environnement de préparation.

## Fichiers ajoutés / modifiés

- `dist/superadmin-preview.html`
- `dist/superadmin-establishment-theme.css`
- `dist/superadmin-premium.css`
- `dist/superadmin-motion.js`
- `tests/superadmin-establishment-e8.test.mjs`

Cette prévisualisation est volontairement restreinte à localhost.
Ne pas l'utiliser en guise de console Superadmin sécurisée en production.
