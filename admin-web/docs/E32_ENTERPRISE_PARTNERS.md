# E32 · Superadmin > Entreprises

## Identité métier
- E31 Établissements : monde académique, campus, comptes actifs **simultanés**.
- E32 Entreprises : monde B2B, opportunités et recrutement, publications **cumulativement consommées**.
- Marque unifiée : Manrope, logo et navigation inchangés, modales G-Connect.
- Module Entreprises : en-tête indigo/violet avec réseau talents/offres/partenaires,
  indicateurs de la base réelle, grille de fiches commerciales plutôt qu'un second annuaire scolaire.

## Ce qui est livré
- Endpoint read-only MFA + Superadmin `/api/v1/backoffice/enterprises/`.
- Recherche par raison sociale, secteur, e-mail ou localisation de l'utilisateur.
- Filtres d'accès (actifs, inactifs/bloqués) et d'abonnement (valide/absent).
- Pagination 12 par défaut, maximum 50 côté API.
- Indicateurs réels : nombre d'entreprises, actifs, ayant un forfait Publications,
  échéances dans les 30 jours.
- Chaque carte : nom, secteur, état d'accès, offres enregistrées/ouvertes,
  candidatures, consommation de crédits sur le contrat courant, extensions,
  fiche de contact et lien vers la gestion des abonnements.
- Les publications supprimées restent dans `PublicationConsumption`, ce qui
  assure que le crédit n'est pas restitué.
- Aucune facture ni validation de paiement fictive.

## Suite logique
- Recruteurs : gestion des rôles/autorisations/invitations et visibilité par entreprise.
- Intégration de la donnée réelle des candidatures dans les analytics du Superadmin,
  avec contrôle d'accès selon les besoins.
- Améliorer les actions de gestion administrative seulement si des endpoints authentifiés
  et audités existent, jamais des boutons sans backend.

## Références UX
- Nielsen Norman Group, « Data Tables: Four Major User Tasks » :
  https://www.nngroup.com/articles/data-tables/
  Filtrer/rechercher, comparer, voir une fiche, déclencher une action.
- Atlassian Design, « Empty state » :
  https://atlassian.design/components/empty-state/
  Les zéro enregistrements et les erreurs de chargement ont des messages distincts.
- Atlassian Support, « Add and manage dashboard filters » :
  https://support.atlassian.com/platform-experiences/docs/add-and-manage-dashboard-filters/
  Filtres explicites et remise à zéro rapide.
