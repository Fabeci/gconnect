# G-Connect E31 | Direction artistique par module

## Base commune
Manrope, bleu #3761FF, transparence douce, fenêtres arrondies, animation discrète.
Chaque module reçoit aussi une structure fonctionnelle propre, plutôt que les mêmes KPI recolorés.
Les chiffres doivent venir du backend Django; aucun statut ni paiement fictif.

## Superadmin

| Module | Mission et architecture UI | Identité visuelle |
|---|---|---|
| Vue d'ensemble | Réseau global, partenaires, alertes, raccourcis | Bleu G-Connect, orbites |
| Établissements | Annuaire filtré, communautés, capacités, fiches et échéances | Turquoise/vert d'eau, campus (refonte E31) |
| Entreprises | Portefeuille partenaires, secteurs, contrats et activité | Indigo/violet, horizon commercial |
| Recruteurs | Responsables par entreprise, rôle et accès | Ambre doux, équipes |
| Utilisateurs | Annuaire étudiants/alumni, rôles et états | Lavande, réseau humain |
| Abonnements | Forfaits, quotas, durées, demandes, historique | Bleu commerce, décision tarifaire |
| Factures & paiements | Grand livre, règlements vérifiés, rapprochements | Vert minéral, lignes comptables |
| Invitations | File d'invitations, destinataires, échéances | Cyan, messagerie |
| Offres & contenus | Bibliothèque éditoriale, prévisualisation, publication | Rose terre cuite, grille éditoriale |
| Modération | Signalements, priorisation, décisions motivées | Rouge mesuré, dossiers |
| Imports | Étapes, contrôles, erreurs de lignes, historique | Cyan technique, pipeline |
| Statistiques | Graphiques réels, périodes, comparaisons | Sarcelle, visualisation |
| Journal d'audit | Chronologie, acteur, objet, date, filtre | Acier, traçabilité |
| Sessions & sécurité | Sessions, MFA, accès, révocation | Indigo, protection |
| Paramètres | Préférences et sécurité, formulaires | Gris bleuté, organisation |

## Établissement (espace professionnel)
Tableau de bord académique, promotions/filières, étudiants/alumni, événements,
équipe d'administration et forfait en **comptes actifs simultanés**.
Identité : bleu et vert académique, organisation par cohortes et calendrier.

## Entreprise (espace professionnel)
Tableau de bord de recrutement, offres, candidatures, publications, équipe et forfait
en **publications cumulativement consommées**. Supprimer une publication ne restitue
pas son crédit. Identité : indigo et lavande, pipeline de recrutement.

## Livré / prochaines étapes
- E31 : refonte complète Superadmin > Établissements, endpoint authentifié et MFA,
  vrais membres et abonnements, filtres, pagination, fiche et échéances.
- Les autres modules ont des signatures visuelles distinctes dans le fichier
  module-identities-e31.css, sans changement de logique métier.
- Les refontes fonctionnelles complètes des autres modules suivent au rythme de
  la vérification de leurs API. Ne pas inventer de donnée absente.
- Aucune modification des contrats ou des règlements n'est introduite par E31.

## Références de recherche
Nielsen Norman Group, Data Tables: Four Major User Tasks:
https://www.nngroup.com/articles/data-tables/

Michelin Design System, Principles of a dashboard:
https://designsystem.michelin.com/data-visualization/design-guidelines/principles-of-a-dashboard

Howard University, Institutional Dashboards:
https://ira.howard.edu/institutional-research/institutional-dashboards

Baymard Institute, Digital Subscription & SaaS UX Benchmark (2025):
https://baymard.com/research-articles/digital-subscriptions-and-saas-2025-benchmark

OWASP Logging Cheat Sheet:
https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
