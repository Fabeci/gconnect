# G-Connect — Sprint 0 : audit et architecture SaaS

**Date : 21 octobre 2026 · Statut : proposition à valider avant implémentation**

Périmètre : Administration Établissement, Administration Entreprise et Superadministration G-Connect. L’application mobile Étudiants & Alumni est déclarée existante par le commanditaire ; son backend n’a pas pu être identifié dans les sources accessibles. Ce rapport ne décrit donc pas ce backend comme s’il avait été audité.

## 1. Décision proposée

Construire deux portails d’organisation partageant les composants Modern Blue Glass et une console de superadministration distincte. Organiser les services par domaines : identités, organisations et accès, communauté, recrutement, abonnements et facturation, audit. Favoriser une extension modulaire du backend mobile après son analyse. Ne pas démarrer par des microservices ni par un remplacement de l’identité existante.

Une organisation constitue un tenant ; son type est `institution` ou `company`. Un utilisateur peut appartenir à plusieurs organisations et conserve une identité globale. Le rôle, le type d’organisation, le périmètre de la ressource et les droits du contrat sont vérifiés côté serveur à chaque opération. Une affiliation étudiante ne confère aucun droit administratif.

**Point bloquant pour l’intégration :** obtenir le dépôt mobile/backend, sa branche de référence, sa documentation d’API et son mécanisme d’authentification. Le socle visuel peut être préparé après validation, mais aucun choix irréversible de stockage ou d’identité ne doit précéder cet audit.

## 2. Audit Git vérifié

Les références distantes ont été consultées en lecture seule avec `git ls-remote --heads origin`, et la PR avec le connecteur GitHub.

| Élément | Constat |
|---|---|
| Dépôt | `taogoulahtihamy-gif/g-connect`, privé selon les métadonnées GitHub |
| Branche active | `feat/gconnect-premium-v1` |
| HEAD local et distant | `5f637bb02fabe8700c8428af9563895d737d2876` |
| Arbre de travail au début de l’audit | Propre : aucun fichier modifié, aucun fichier non suivi |
| Relation à `main` | 9 commits d’avance, 0 de retard par rapport aux références vérifiées |
| `main` local et distant | `949d87743c498270af8e82c9eda31fba7fba5dfa` |
| `feat/gconnect-premium-v03` local et distant | `d1203acbfba13b4c17744b34bc26305b15452f46` |
| Branche locale `refonte-design-complet` | HEAD `1252805`, sans branche distante correspondante |
| Travail non publié sur cette ancienne branche | `016bcbc` et `1252805`, absents de l’ensemble des références distantes locales vérifiées |
| PR #2 | Ouverte, brouillon, non fusionnée ; tête `5f637bb`, base `main` |

La branche récente est entièrement publiée. Les deux anciens commits locaux sont conservés ; ils ne doivent pas être supprimés ou réappliqués automatiquement. Aucune branche, PR ou base de données n’a été modifiée pendant cet audit. Le seul ajout prévu par ce livrable est le présent document, non commité et non poussé.

Sources : [PR #2](https://github.com/taogoulahtihamy-gif/g-connect/pull/2), [commit audité](https://github.com/taogoulahtihamy-gif/g-connect/tree/5f637bb02fabe8700c8428af9563895d737d2876).

## 3. Audit du frontend

| Fichier ou ensemble | Rôle réel et observations |
|---|---|
| `dist/index.html` | Entrée statique ; charge quatre feuilles CSS, Manrope locale et `app.js` |
| `dist/app.js` | JavaScript natif, vues sous forme de chaînes HTML, état global en mémoire et événements affectés après rendu |
| `dist/tokens.css` | Palette, typographie Manrope, rayons, ombres et réduction des animations |
| `dist/campus.css` | Thème Modern Blue Glass partagé et adaptations responsive |
| `dist/style.css`, `dist/premium.css` | Couches historiques toujours chargées ; nombreuses surcharges et valeurs en dur |
| `dist/assets/` | Logos, photographie locale, polices et licence Manrope |
| `tests/frontend.test.mjs` | Cinq cas déclarés, essentiellement assertions textuelles sur les fichiers ; aucune preuve de sécurité backend |
| `scripts/verify-visual.cjs` | Contrôles Playwright de 7 vues et 5 largeurs ; plusieurs navigations invoquent directement `navigate()` |
| `.github/workflows/` | CI syntaxe JS et tests textuels ; ne lance pas le script Playwright |
| `docs/modern-blue-glass/` | Captures et rapport de validation visuelle antérieur |

**Fonctions réelles :** navigation interne, recherche et filtres sur tableaux locaux, favoris dans un `Set` en mémoire, ouverture/réduction de sidebar, messages d’information et saisie de formulaire. Les favoris disparaissent au rechargement. Réduire la sidebar conserve le formulaire ; changer de vue reconstruit le DOM et ne constitue pas une sauvegarde.

**Fonctions non démontrées et non connectées :** connexion, sessions, invitations réelles, réseau persistant, candidature, messagerie, sauvegarde de profil, gestion d’organisation, abonnements, paiements et factures. Les rôles du sélecteur Profil sont une donnée d’interface, pas un système d’autorisation. Les nombres, offres, personnes et événements sont des exemples.

Aucun backend, schéma SQL, migration, contrat OpenAPI, client API, gestionnaire de dépendances frontend ou application Next.js n’est présent dans cette branche. La mention Next.js/TypeScript et FastAPI/PostgreSQL dans le README est une intention ancienne, pas la preuve d’une implémentation.

Risques à traiter avant le branchement de données : concaténations `innerHTML` à remplacer par un rendu échappé systématique ; identifiants de favoris actuellement fondés sur l’index du tableau ; absence de routes URL et d’historique applicatif ; absence d’états chargement/erreur réseau ; dépendance Playwright non verrouillée ; styles hérités difficiles à maintenir. Il n’a pas été démontré de vulnérabilité exploitable sur les données statiques actuelles.

Contrôles relancés pour Sprint 0 : `node --check dist/app.js`, `node --test tests/frontend.test.mjs` : réussite. Le script visuel n’a pas été relancé pour cet audit, car il réécrit les captures ; sa validation précédente n’est pas un audit de sécurité SaaS.

## 4. Recherche du backend mobile : résultat et limites

| Recherche effectuée | Résultat |
|---|---|
| Arborescence, README, documentation, CI et références API dans le dépôt | Aucun lien identifiable vers un backend mobile G-Connect |
| README de `main` et de l’ancienne branche locale | Même projet frontend ; aucune documentation backend retrouvée |
| Inventaire GitHub accessible du compte | 41 dépôts retournés ; un seul dépôt nommé autour de « connect » : `g-connect` |
| Recherche de code GitHub sur le compte : `G-Connect`, `gconnect`, `alumni` | Aucun résultat ; recherche limitée à l’index et aux branches par défaut accessibles |
| Recherche web publique ciblée sur le compte et le nom | Aucun résultat permettant d’identifier ce backend ; homonymes écartés |
| Recherche de noms de fichiers/dossiers G-Connect et OpenAPI sous `/mnt/chak` | Aucun backend associé identifié ; des répertoires techniques non accessibles limitent cette recherche |

**Conclusion : documentation et dépôt du backend mobile introuvables dans le périmètre consulté. Cela ne prouve pas leur absence.** Ils peuvent se trouver sous un autre compte, une branche non indexée, un autre nom ou dans une documentation privée. Aucun dépôt backend d’un autre produit n’est assimilé à G-Connect.

À fournir pour l’audit d’intégration : dépôt et branche mobile/backend, README technique, contrat OpenAPI ou collection d’API, schéma/migrations, fournisseur d’identité, règles d’accès actuelles, stockage des CV/fichiers, environnements disponibles, versions mobiles encore supportées. Les liens et contrats suffisent à ce stade ; aucun secret de production n’est demandé.

La matrice de compatibilité à remplir avant implémentation couvrira : identité stable des utilisateurs, entreprises/écoles déjà existantes, offres et candidatures déjà exposées, identifiants, pagination, erreurs, uploads, notifications, authentification et compatibilité des anciennes versions mobiles.

## 5. Architecture cible proposée, sous réserve de l’existant

### 5.1 Frontières et choix techniques

| Couche | Proposition | Condition |
|---|---|---|
| Web organisations | Une application React/TypeScript avec deux ensembles de routes et un shell commun ; Next.js est le candidat par défaut cohérent avec le README | Valider l’hébergement, les besoins serveur et les contraintes de session avant de figer le framework |
| Superadministration | Entrée ou application déployable séparément, composants partagés, session et audience d’API dédiées | Pas de privilèges globaux fournis au navigateur d’un tenant |
| API métier | Monolithe modulaire ou modules du backend existant ; contrat HTTP versionné | Conserver le langage/framework existant s’il convient ; FastAPI reste une option, pas une décision acquise |
| Identité | Réutiliser ou fédérer le fournisseur mobile, avec mapping stable des sujets | Aucun second annuaire ni migration de mots de passe sans analyse |
| Données | Modèle relationnel ; PostgreSQL partagé avec isolation par ligne si compatible avec le backend | Aucun provisionnement pendant Sprint 0 ; ne pas imposer une migration du stockage mobile |
| Fichiers | Stockage objet privé ; téléchargement après autorisation, URL temporaire | Réutiliser le stockage mobile si ses garanties sont suffisantes |
| Tâches | Worker pour imports, exports, relances et traitement fiable des événements | Une file et un journal transactionnel d’événements suffisent au départ |
| Paiement | Adaptateur prestataire, webhook authentifié, rapprochement périodique | Prestataire, pays, devises et moyens de paiement à choisir |

Organisation de code indicative après accord : application des portails, application superadmin, bibliothèque `ui`, bibliothèque de contrats API ; modules backend `identity`, `organizations`, `community`, `recruitment`, `billing`, `audit`. Conserver `dist/` comme référence visuelle pendant la transition. Ne pas transformer le grand `app.js` en système SaaS par accumulation de conditions.

Chemin d’une requête : interface → session serveur/BFF si retenu → authentification API → contexte organisation validé → permission et droit d’abonnement → domaine métier → stockage isolé. Le BFF, s’il existe, gère la session du navigateur ; l’API conserve ses propres contrôles d’autorisation.

### 5.2 Intégration mobile sans remplacement

Décision après audit : **A)** étendre le backend existant si ses modules et son identité conviennent ; **B)** ajouter un module SaaS adjacent et un adaptateur versionné si l’existant ne peut accueillir la facturation ; **C)** proposer séparément une migration progressive seulement si des incompatibilités sont démontrées. Aucune de ces voies ne justifie une réécriture immédiate.

Pour chaque entité partagée, désigner une source de vérité. Le mobile doit rester maître de ses identités/profils tant qu’aucune autre décision n’est approuvée. Ne pas écrire simultanément depuis deux systèmes dans les mêmes tables. Si une synchronisation est nécessaire : mapping d’identifiants, événements versionnés, déduplication, reprise après échec et rapprochement. Les contrats existants restent disponibles ; les changements de schéma doivent être additifs avant tout retrait ultérieur.

Prévoir un environnement de test isolé approuvé, des données synthétiques, des drapeaux d’activation, des tests de contrat mobile et un retour arrière documenté. Aucun accès direct du navigateur à une base avec un compte privilégié.

### 5.3 Authentification

Conserver l’identité mobile lorsque sa sécurité et ses protocoles sont vérifiés. Si OIDC/OAuth est disponible, proposer Authorization Code avec PKCE, redirections strictes, validation émetteur/audience/expiration et révocation des sessions. La référence de sécurité est la [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) ; elle ne prouve pas que le mobile l’implémente.

Pour le web : session serveur et cookie `HttpOnly`, `Secure`, `SameSite` approprié, protection CSRF et rotation à la connexion/élévation de privilège. Ne pas stocker un jeton administratif durable dans `localStorage`. Pour le mobile : conserver son mécanisme actuel jusqu’à l’audit. Proposer MFA obligatoire pour les comptes de plateforme et les propriétaires d’organisation, récupération encadrée et journalisée.

Invitations : jeton à usage unique stocké sous forme de hash, durée limitée, organisation et rôle fixés côté serveur, acceptation par une identité vérifiée. Refuser la réutilisation, l’auto-attribution de rôle et le retrait du dernier propriétaire sans transfert. Un changement d’organisation invalide les caches de données de l’interface et revérifie les permissions.

### 5.4 Rôles et permissions

Utiliser des permissions atomiques, regroupées en rôles prédéfinis au départ. Les rôles personnalisés peuvent attendre. Un même utilisateur peut être recruteur dans A, lecteur dans B et alumni d’une école C, sans additionner ces pouvoirs dans toutes ses organisations.

| Rôle | Périmètre proposé |
|---|---|
| Propriétaire d’organisation | Paramètres, transfert de propriété, équipe et facturation de son organisation ; permissions métier de son type |
| Administrateur d’organisation | Équipe et opérations de son organisation ; ni transfert de propriété ni délégation supérieure à ses droits |
| Gestionnaire établissement | Affiliations académiques, promotions et accompagnement autorisé ; aucun accès aux notes internes des recruteurs |
| Recruteur entreprise | Offres et candidatures de son entreprise ; affectation par offre possible ensuite |
| Responsable facturation | Abonnement, factures et paiements de son organisation ; aucun CV ou dossier candidat |
| Lecteur | Lecture explicitement autorisée des données métier de son organisation ; pas d’export sensible implicite |
| Opérateur plateforme | Validation/suspension d’organisations selon permissions ; accès aux données métier par défaut refusé |
| Finance plateforme | Catalogue, contrats et rapprochement financier ; aucun accès automatique aux candidatures |
| Support plateforme | Diagnostic minimal ; accès exceptionnel limité, motivé, temporaire et audité |
| Superadministrateur sécurité | Gestion des accès plateforme et opérations exceptionnelles ; MFA et traçabilité renforcées |

Exemples de permissions : `organization.read`, `organization.update`, `members.invite`, `roles.assign`, `affiliations.manage`, `offers.publish`, `applications.read`, `applications.update`, `billing.read`, `billing.manage`, `audit.read`, `platform.organizations.suspend`, `platform.plans.manage`.

Règle proposée : autorisé seulement si identité valide **ET** adhésion active **ET** permission dans l’organisation active **ET** ressource dans le périmètre **ET** action compatible avec l’état d’accès/abonnement. Pour les services de récupération d’accès et de facturation, prévoir des exceptions explicites. Un abonnement ne confère jamais un rôle. Masquer un menu est ergonomique ; le serveur reste l’autorité.

## 6. Isolation et partage contrôlé

### 6.1 Propriété des données

| Catégorie | Propriétaire / visibilité |
|---|---|
| Identité et profil personnel | Utilisateur global ; seules les projections expressément autorisées sont exposées aux organisations |
| Équipe administrative | Organisation ; aucune liste inter-organisations pour un administrateur tenant |
| Affiliations et dossiers académiques | Établissement concerné ; le même étudiant peut avoir plusieurs affiliations indépendantes |
| Offre brouillon et notes | Entreprise propriétaire exclusivement |
| Offre publiée | Projection publique ou audience d’établissements explicitement ciblés ; pas d’accès à la table privée entière |
| Candidature et CV soumis | Candidat auteur et entreprise destinataire selon leurs permissions ; le CV soumis est un instantané/version, pas un accès au dossier personnel entier |
| Notes de recrutement | Entreprise exclusivement ; jamais partagées avec l’établissement par défaut |
| Suivi établissement d’une candidature | Projection minimale avec autorisation de partage explicite et révocable ; l’affiliation seule ne suffit pas |
| Abonnements, paiements, factures | Organisation facturée et permissions financières de plateforme |
| Catalogue de plans | Plateforme ; seuls les plans publiés et éligibles sont visibles aux organisations |

L’isolation ne signifie pas interdire les offres publiques ou une candidature volontaire : ces échanges passent par des projections et permissions spécifiques. Un partenariat entreprise–établissement n’ouvre pas automatiquement leurs bases respectives.

### 6.2 Mesures proposées

Chaque ressource privée porte un `organization_id` non nul, fixé par le serveur. Le contexte actif provient d’une adhésion vérifiée ; un UUID, un sous-domaine ou l’en-tête du client n’est jamais une autorisation. Lire ou modifier une ressource exige de vérifier son propriétaire, y compris pour les routes imbriquées et les opérations par lots. Les réponses à une ressource d’un autre tenant doivent éviter d’en révéler l’existence.

Les requêtes, caches, clés de stockage, exports, index de recherche, canaux temps réel et tâches asynchrones doivent transporter un contexte validé et être cloisonnés. Les contrôles de téléchargement sont revérifiés au moment de servir le fichier. La [référence OWASP sur le multi-tenant](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html) sert de guide à cette défense sur plusieurs couches.

Si PostgreSQL est retenu : filtres applicatifs et politiques RLS en défense supplémentaire, `USING` pour la visibilité et `WITH CHECK` pour les écritures. Le compte applicatif ne doit être ni propriétaire, ni superutilisateur, ni `BYPASSRLS`. Considérer `FORCE ROW LEVEL SECURITY`, séparer migrations et exploitation, et fixer le contexte dans une transaction avec nettoyage garanti des connexions mutualisées. Les contraintes de clés étrangères composites `(organization_id, id)` empêchent de rattacher un enfant à une ressource d’un autre tenant. Les tables globales et les projections publiques ont des politiques distinctes. Les limites de RLS sont documentées par [PostgreSQL](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) ; RLS ne remplace pas l’autorisation métier.

Pour la superadministration, employer des endpoints dédiés, des permissions explicites et un audit durable. Pas de paramètre public `bypass_tenant`, pas de secret privilégié dans le navigateur. Les tâches globales fonctionnent avec un compte de service restreint, en sélectionnant explicitement chaque organisation. Un accès de support exceptionnel doit enregistrer acteur, motif, périmètre, durée et résultat ; l’usurpation de session n’est pas prévue en V1.

## 7. Modèle conceptuel proposé

Les noms suivants décrivent le domaine cible, pas des tables déjà présentes. Les identifiants mobiles éventuels seront mappés après audit.

| Entité | Attributs essentiels / relations et invariants |
|---|---|
| `User` | Identité globale, état du compte, coordonnées vérifiées ; aucune organisation unique imposée |
| `ExternalIdentity` | `user_id`, fournisseur, sujet externe ; unicité `(issuer, subject)`, rapprochement vérifié, jamais par email seul |
| `Organization` | Type établissement/entreprise, nom, identifiant stable, état de validation, paramètres ; changements de type contrôlés |
| `InstitutionProfile` / `CompanyProfile` | Extensions 1–1 selon le type ; données métier spécifiques séparées |
| `Membership` | Utilisateur + organisation + état invité/actif/suspendu/révoqué ; unicité du couple utilisateur/organisation |
| `Role`, `Permission`, `MembershipRole`, `RolePermission` | Relations N–N ; affectations liées à l’adhésion et donc au tenant ; rôles plateforme dans des affectations distinctes |
| `Invitation` | Organisation, destinataire, rôles autorisés, hash du jeton, échéance, auteur et date d’acceptation |
| `AcademicAffiliation` | Utilisateur + établissement + statut étudiant/alumni + promotion/formation + dates + vérification ; distincte de `Membership` |
| `Offer` | Organisation entreprise, auteur, titre, contenu, statut brouillon/publié/fermé/archivé, audience, dates ; seule l’entreprise propriétaire la modifie |
| `OfferAudience` | Offre + établissement autorisé, lorsque la publication n’est pas globale ; ne donne pas accès aux candidatures |
| `Application` | Offre + candidat + entreprise destinataire, statut, dates, version du CV ; l’entreprise doit correspondre à celle de l’offre ; une candidature par candidat/offre en V1 |
| `ApplicationEvent` / `RecruiterNote` | Historique d’état et notes internes séparés ; acteur, date, organisation ; notes non exposées au candidat par défaut |
| `FileAsset` / `ApplicationDocument` | Stockage privé, propriétaire utilisateur ou tenant, version, règles d’accès et rattachement au dossier soumis |
| `SharingGrant` | Auteur, bénéficiaire, ressource, champs/périmètre, durée et révocation ; permet un suivi limité par l’établissement |
| `Plan` | Famille commerciale, type d’organisation éligible, visibilité publié/retiré ; pas de tarif mutable utilisé rétroactivement |
| `PlanVersion` | Version immuable des fonctionnalités, quotas et règles commerciales ; conservation des anciennes versions |
| `PlanPrice` | Version de plan, devise, montant en unité monétaire minimale, durée ; variantes 1, 6, 12 mois et offres personnalisées |
| `Subscription` | Organisation + version du plan, état commercial, mode de renouvellement, dates d’essai, annulation à terme et historique ; une souscription principale courante par organisation en V1 |
| `SubscriptionPeriod` | Début inclus/fin exclue, prix et droits figés, origine commande/essai/renouvellement ; périodes successives sans double couverture accidentelle |
| `AccessRestriction` | Suspension métier/sécurité indépendante du paiement, portée, raison, auteur et levée ; ne doit pas être effacée par un webhook de paiement |
| `BillingOrder` | Achat/renouvellement/changement de plan, montant attendu, devise, organisation, durée et clé d’idempotence ; conditions figées avant paiement |
| `Payment` | Tentative, commande, référence externe unique par prestataire, montant, devise, état ; une commande peut connaître plusieurs tentatives |
| `Refund` / `PaymentAllocation` | Remboursement lié au paiement ; affectation des montants aux factures, sans assimiler une tentative à une recette |
| `Invoice` / `InvoiceLine` | Organisation, numéro unique à l’émission, identité de facturation figée, devise, lignes/prix/taxes/total figés et échéance ; document émis non réécrit |
| `CreditNote` | Correction/remboursement documenté, référence à la facture d’origine ; règles légales à valider selon l’entité facturante |
| `WebhookEvent` / `OutboxEvent` | Prestataire + identifiant événement unique, réception/traitement/reprise ; notification sortante publiée après transaction validée |
| `AuditEvent` | Acteur, organisation, action, cible, date, résultat et corrélation ; accès restreint, exclusion des secrets et contenus de CV |

Cardinalités principales : utilisateur N–N organisation via adhésion ; utilisateur N–N établissement via affiliation ; organisation 1–N offres ; offre 1–N candidatures ; utilisateur 1–N candidatures ; plan 1–N versions ; version 1–N tarifs ; organisation 1–N abonnements historiques ; abonnement 1–N périodes ; commande 1–N tentatives de paiement ; facture 1–N lignes. Les affectations relient paiements et factures sans imposer artificiellement une correspondance 1–1.

Les identités, le catalogue et les rôles plateforme sont globaux. Les tables privées financières et métier sont tenantées. Les associations qui traversent deux domaines ont une règle explicite ; elles ne sont pas des exceptions informelles au filtrage.

## 8. Plans, durées et cycle d’abonnement

### 8.1 Configuration des offres

Séparer les **fonctionnalités du plan** de la **durée vendue**. Une formule peut proposer des tarifs distincts pour 1, 6 et 12 mois ; une durée personnalisée est une proposition commerciale versionnée, avec montant explicite et dates ou unité/nombre de durée. Aucune multiplication automatique d’un prix mensuel n’est présumée.

Proposition V1 : périodes prépayées, renouvellement manuel disponible, renouvellement automatique seulement si le prestataire et le consentement client le permettent. Les changements de plan prennent effet au prochain terme ; prorata et changements immédiats restent hors V1 tant que leurs règles ne sont pas validées. Un plan retiré ne peut plus être souscrit mais continue à décrire les contrats existants.

Calcul des dates : 1/6/12 mois sont des mois calendaires, pas 30/180/360 jours. Conserver une date d’ancrage et le fuseau commercial, fixer la règle de fin de mois et convertir les bornes en instants UTC. Proposition : maintenir l’ancrage d’origine et utiliser le dernier jour lorsqu’il manque dans le mois cible. Une période est `[début, fin)`. Tester notamment le 31 janvier et les années bissextiles. Pour une durée personnalisée à dates fixes, enregistrer exactement les dates acceptées.

### 8.2 États et droits proposés

| État | Entrée / sortie | Droits proposés |
|---|---|---|
| En attente | Organisation créée, offre choisie mais sans essai ni paiement confirmé | Configuration initiale, choix de plan et facturation uniquement |
| Essai | Octroi contrôlé, durée/quota figés ; sortie vers actif au paiement ou expiré au terme | Capacités d’essai définies par le plan ; pas d’essais répétés par simple changement d’administrateur |
| Actif | Paiement confirmé et période commencée | Capacités du plan et quotas, toujours limités par les permissions |
| Délai de grâce | Fin de période payée avec renouvellement impayé ; échéance unique configurable | Proposition : consultation des dossiers existants et régularisation ; pas de nouvelles publications/imports ni nouvelles candidatures sur les offres de l’organisation |
| Expiré | Fin de période sans renouvellement ou fin du délai de grâce | Facturation, renouvellement et récupération/export encadré ; accès opérationnel bloqué, données conservées selon politique à définir |
| Suspendu | Restriction administrative ou sécurité, indépendante du statut commercial | Capacités bloquées selon la restriction ; support/régularisation seulement lorsque la raison le permet |
| Renouvellement | Événement créant une nouvelle période, pas un statut permanent | Retour/maintien en actif seulement si paiement valide et aucune suspension indépendante |

Valeurs à arbitrer : essai proposé de 14 jours et grâce de 7 jours, tous deux configurables et désactivables ; ce ne sont pas des règles déjà adoptées. Un essai expiré n’obtient pas automatiquement une grâce supplémentaire. La fin d’abonnement d’une organisation ne suspend jamais le compte personnel du candidat ni son accès mobile à ses propres données.

L’annulation volontaire désactive le renouvellement futur et conserve l’accès jusqu’à la fin payée, sauf décision contraire explicitement contractualisée. La suspension de sécurité est une restriction superposée : un paiement ne la lève pas. Sa levée recalcule les droits selon la période courante ; elle ne garantit pas le retour à actif.

### 8.3 Renouvellement et fiabilité

Paiement avant terme : la nouvelle période commence à la fin de la période déjà acquise. Paiement pendant la grâce : proposition de continuité depuis l’échéance initiale, mentionnée avant achat. Après expiration : nouvelle période à partir de la date de reprise convenue, sans consommation rétroactive automatique. Une commande devenue obsolète ou payée tardivement doit être rapprochée et traitée selon sa politique, sans écraser une souscription plus récente.

Les droits effectifs sont vérifiés à la requête d’après les dates et restrictions ; un job de minuit en retard ne doit pas prolonger un accès. Le worker matérialise les transitions, envoie les rappels et assure les reprises. Quotas contrôlés atomiquement au moment des écritures, y compris en concurrence.

Le retour du navigateur après paiement ne prouve pas le règlement. Le serveur vérifie la signature du webhook, la référence de commande, le prestataire, le montant et la devise ; déduplique les événements, traite les livraisons désordonnées et rapproche les statuts avec le prestataire. La souscription n’est activée qu’une fois, dans une transaction cohérente avec la période acquise. Un échec tardif ne doit pas rétrograder un paiement déjà confirmé sans règle de remboursement/contestation.

Paiement manuel éventuel : validation par un opérateur financier autorisé, justificatif, référence et audit, sans bouton tenant permettant de se déclarer payé. Ne pas conserver de données de carte ; déléguer la collecte au prestataire choisi. Les formats de factures, taxes, numérotation, devises, remboursements et conservation doivent être validés avec les responsables financiers/juridiques avant encaissement réel.

## 9. Menus et écrans proposés

Les menus reflètent les permissions. Tous les écrans prévoient chargement, vide, erreur, accès refusé et abonnement restreint, avec une action de sortie utile.

| Espace | Menu / écrans |
|---|---|
| Commun organisations | Connexion et récupération ; acceptation d’invitation ; sélection d’organisation ; tableau de bord ; profil personnel ; sécurité/session ; aide |
| Établissement | Vue d’ensemble ; étudiants & alumni (liste, dossier autorisé, vérification d’affiliation) ; promotions/formations ; imports avec aperçu et rapport d’erreurs ; opportunités partagées ; suivi d’insertion autorisé ; partenariats ; équipe & rôles ; abonnement & factures ; paramètres ; journal d’activité |
| Entreprise | Vue d’ensemble ; offres (liste, création, brouillon, publication, fermeture) ; candidatures (liste, filtres, détail, historique, notes privées) ; profil public entreprise ; partenariats établissements ; équipe & rôles ; abonnement & factures ; paramètres ; journal d’activité |
| Superadministration | Vue plateforme ; organisations (validation, activation, suspension motivée) ; utilisateurs & accès plateforme ; catalogue plans/versions/tarifs/durées ; abonnements & échéances ; paiements/rapprochement/remboursements ; factures/avoirs ; audit ; support encadré ; suivi des tâches et incidents |

Le suivi d’insertion, les partenariats, les imports et les statistiques avancées sont des écrans cibles à prioriser, pas des fonctions prouvées du mobile. La messagerie n’est pas engagée en V1 avant connaissance du service existant. Ne pas afficher de faux indicateurs opérationnels : valeurs réelles, état vide ou démonstration explicitement signalée.

## 10. Réutilisation Modern Blue Glass

| Réutiliser / extraire | Travail nécessaire pour le SaaS |
|---|---|
| Tokens couleur, Manrope locale, rayons 14/24/32 px, ombres et mouvement réduit | Consolider les valeurs et supprimer progressivement les surcharges historiques, avec comparaison visuelle |
| Sidebar flottante ouverte/réduite et mobile | Composant contrôlé, vrai routage, organisation active, menus par permissions ; gestion du focus et clavier |
| Topbar, breadcrumb, logo, avatar et boutons icônes | Liens réels, titres de page, états accessibles, notifications uniquement branchées à des données réelles |
| Boutons, badges, cartes, panneaux, formulaires | Variantes documentées, disabled/loading/error, labels, validation, focus, contraste |
| Recherche et filtres | Pagination serveur, requêtes annulables, état vide/erreur, URL partageable et cache tenanté |
| Toasts et états vides | Messages accessibles, pas de confirmation de succès avant réponse serveur |
| Carte d’offre et profil organisation | Réutiliser la composition ; contrats de données et actions à reconstruire |
| Photographie et héros | Actifs de marque pour accueil/onboarding ; ne pas occuper les écrans administratifs denses |

Composants absents à créer après validation : tableau paginé responsive, dialogue de confirmation, panneau de détail, sélecteur d’organisation, formulaire d’invitation, matrice de permissions, badge d’état d’abonnement, résumé de facture, chronologie d’audit et résumé d’erreurs d’import. Les principes visuels sont réutilisables immédiatement ; les fonctions de `app.js` ne constituent pas une bibliothèque métier ou de sécurité.

## 11. Stratégie de tests et critères de sécurité

### 11.1 Jeu de données de référence

Au minimum deux entreprises A/B et deux établissements C/D, un utilisateur multi-organisations avec des rôles différents, un recruteur A, un responsable facturation A, un gestionnaire C, deux candidats, une adhésion révoquée, un compte support sans accès exceptionnel et un opérateur plateforme. Chaque tenant possède offres/dossiers/fichiers/factures distincts. Prévoir une offre publique et un partage explicite vers C pour vérifier les exceptions légitimes.

### 11.2 Tests anti-fuite obligatoires

| Test | Résultat attendu |
|---|---|
| Jeton A + identifiant de ressource B dans URL, corps, query ou en-tête | Aucune lecture, écriture ou révélation d’existence non autorisée ; aucun effet de bord |
| Liste, recherche, compteurs, pagination et export | Aucun enregistrement ni total privé d’un autre tenant |
| Offre A + candidature/document/référence B | Rejet applicatif et intégrité en stockage ; pas de rattachement croisé |
| Changement de `organization_id` ou attribution de rôle dans un payload | Champs ignorés/refusés selon contrat ; pas d’escalade |
| Deux tenants du même type et de types différents | Même niveau d’isolation ; le type n’est pas une frontière suffisante |
| Utilisateur admin A / lecteur B | Les permissions A ne deviennent pas utilisables dans B, même après changement d’onglet |
| Cache ou connexion DB réutilisés après une requête A | Aucun contexte A résiduel pendant B ; contexte absent = refus |
| Fichier, URL signée, export asynchrone, job réessayé, canal temps réel | Pas d’accès hors périmètre ; révocation effective, durée des URL maîtrisée |
| Adhésion retirée ou rôle diminué | Refus dès la requête suivante selon la politique de révocation, y compris pour une session déjà ouverte |
| RLS avec le vrai compte applicatif, si retenue | Lecture et écriture inter-tenants interdites ; compte non privilégié, policies vérifiées par table |
| Superadmin/support | Une session tenant ne devient jamais plateforme ; finance ne peut lire un CV ; accès exceptionnel limité et audité |
| Offre publique et candidature volontaire | Projection publique autorisée ; notes, factures et autres candidatures restent invisibles |
| Établissement C lié au candidat | Aucun accès au dossier de recrutement sans partage explicite ; révocation du partage supprime cet accès |

Ces tests doivent être exécutés contre l’API et le stockage réels d’un environnement de test approuvé, pas uniquement contre des mocks de l’interface. Ajouter un contrôle de couverture : chaque nouvel endpoint et table tenantés doit avoir une preuve d’isolation positive et négative.

### 11.3 Autres suites

- Authentification : jetons expirés, audience/émetteur incorrects, invitation expirée/réutilisée, révocation, MFA, fixation de session, CSRF, absence d’accès par simple modification de menu.
- Abonnements : toutes les transitions, frontières temporelles, 1/6/12 mois et durées personnalisées, fin de mois, année bissextile, fuseaux, renouvellement anticipé/tardif, annulation à terme, reprise après panne et suspension persistante après paiement.
- Paiements : signature invalide, doublon, rejeu, ordre inversé, montant/devise incorrects, tentatives concurrentes, paiement tardif, remboursement/contestation ; aucune double activation ni double facture.
- Quotas : deux écritures simultanées à la limite, modifications de plan, imports/exports ; refus cohérent et transactionnel.
- Contrats mobile : endpoints et identifiants existants compatibles, mapping d’identité, droits du candidat et anciennes versions mobiles supportées.
- Frontend : parcours via clics et URL, navigation arrière, rôles, états réseau, formulaire, focus/dialogues, lecteur d’écran, reduced motion et tailles 320–1440 px ; Chromium, Firefox et WebKit avant lancement.
- Exploitation : restauration vérifiée, reprise de worker, alertes webhook/job, journaux sans secrets, purge/rétention par catégorie après validation de la politique.

Critère transversal : aucune fuite inter-organisation connue, aucune régression de contrat mobile acceptée implicitement, aucune action privilégiée dépendant seulement de l’interface. La CI bloque les changements qui échouent aux tests d’isolation ; les tests visuels complètent ces contrôles sans les remplacer.

## 12. Découpage en sprints

Ordre recommandé ; durées et capacité de l’équipe à confirmer après accès au backend. Chaque sprint se termine par une démonstration, les tests associés et une PR non fusionnée automatiquement.

| Sprint | Périmètre | Critères d’acceptation |
|---|---|---|
| 0 — présent rapport | État Git, audit frontend, recherche backend, architecture, modèle et arbitrages | Faits/propositions séparés ; backend manquant explicitement identifié ; validation des décisions demandée |
| 1 — identité et isolation | Audit complémentaire du backend, contrats, shell trois espaces, organisation active, rôles de base et premier parcours protégé | Deux organisations testées avec identités de test ; refus inter-tenant au niveau API/stockage ; session et sélection d’organisation réelles ; aucune régression mobile ; design system extrait sans effacer le prototype |
| 2 — établissement | Affiliations et annuaire autorisé, équipe, promotions ; import minimal si validé | Un gestionnaire C ne voit jamais D ; doublons/imports traités ; affiliations sans droits administratifs implicites ; audit des changements |
| 3 — entreprise | Cycle d’offre et candidature, documents privés, historique et notes | Offre publiée consommable par le mobile selon contrat ; candidat et entreprise destinataire accèdent au bon dossier ; notes privées isolées ; tests inter-tenant verts |
| 4 — abonnements | Plans versionnés, tarifs 1/6/12 mois et personnalisés, essai/grâce/expiration/suspension, quotas | Horloge de test et transitions complètes ; configuration sans code ; droits calculés serveur ; aucune activation sur simple callback navigateur |
| 5 — paiements et factures | Prestataire en sandbox, renouvellement, rapprochement, documents financiers | Doublons et désordre sans double effet ; facture figée ; échecs/reprises démontrés ; règles fiscales et devises validées avant production |
| 6 — superadmin et préparation lancement | Gestion plateforme complète, support encadré, audit, exploitation, tests croisés et pilote | Permissions plateforme cloisonnées ; restauration testée ; revue sécurité ; validation métiers des trois espaces ; plan de déploiement et retour arrière approuvés |

Un minimum de console superadmin existe dès Sprint 1 pour l’accès protégé ; les fonctions de catalogue apparaissent avec Sprint 4 et la finance avec Sprint 5. Les sprints ne retardent pas les contrôles de sécurité jusqu’au lancement.

## 13. Sprint 1 proposé pour validation

**Objectif :** prouver qu’un administrateur se connecte avec une identité compatible mobile, choisit une organisation autorisée et ne peut jamais consulter celle d’un autre client, dans un shell Modern Blue Glass.

### Conditions d’entrée

1. Identifier le backend mobile et obtenir un accès de lecture à ses contrats et schémas, ou approuver explicitement une phase de découverte prolongée.
2. Valider l’organisation comme tenant, les utilisateurs multi-organisations, la distinction adhésion/affiliation et les rôles de base.
3. Choisir le fournisseur d’identité et la stratégie d’intégration après cet audit, pas avant.
4. Approuver séparément l’environnement de test et l’éventuelle création d’une base isolée. Ce rapport ne constitue pas cette autorisation.
5. Choisir une branche d’implémentation dédiée issue du commit de refonte validé. Aucune fusion de la PR #2 n’est nécessaire pour étudier ou préparer cette branche ; toute fusion reste soumise à validation.

### Backlog proposé

| Lot | Livrable | Acceptation mesurable |
|---|---|---|
| S1.1 — compatibilité mobile | Inventaire endpoints/identités/schéma et décision d’intégration écrite | Source de vérité nommée pour chaque entité partagée ; lacunes documentées ; absence de migration implicite |
| S1.2 — contrats et accès | Contrats connexion/session, `me`, organisations autorisées, profil organisation ; matrice permission/endpoint | Cas 401/403/404 documentés, types d’organisation validés et zéro endpoint tenant sans règle d’isolation |
| S1.3 — shell web | Routes des trois espaces, sélection d’organisation, composants fondamentaux, états chargement/refus/erreur | Navigation URL et clavier ; mobile 320 px/desktop 1440 px ; menus par permission ; données clairement issues du contrat ou de fixtures de test |
| S1.4 — première tranche API | Session réelle compatible mobile, liste des organisations de l’utilisateur, lecture du profil de l’organisation active, révocation d’adhésion | A ne peut lire B par aucun paramètre ; rôle facturation sans accès aux dossiers ; révocation vérifiée avec session ouverte |
| S1.5 — preuve et livraison | Fixtures synthétiques, tests API/stockage/contrats, CI, captures et documentation de démarrage | Deux entreprises et deux établissements ; utilisateur multi-rôles ; tests positifs/négatifs verts ; prototype préservé ; PR à valider |

Hors Sprint 1 : paiement réel, facturation légale, migration de production, remplacement du backend mobile, dossiers étudiants complets, candidatures complètes, messagerie et statistiques avancées. Les invitations peuvent être préparées dans le contrat mais ne doivent pas élargir la première tranche au détriment de l’isolation.

Si le backend reste inaccessible, S1.1 reste incomplet : seuls contrats provisoires et shell à fixtures explicitement identifiées peuvent être préparés après accord. Cette variante ne sera pas présentée comme un Sprint 1 d’authentification/intégration terminé.

## 14. Arbitrages à soumettre

| Décision | Proposition / information nécessaire |
|---|---|
| Backend mobile | Fournir dépôt/branche/documentation ; point bloquant d’intégration |
| Architecture | Étendre l’existant avec domaines modulaires ; web organisations partagé et console plateforme séparée |
| Isolation | Une organisation = un tenant ; membres multi-organisations ; RLS si stockage PostgreSQL compatible |
| Identité et rôles | Réutiliser/fédérer l’identité mobile ; MFA privilégiée ; rôles prédéfinis et permissions côté serveur |
| Partage établissement/entreprise | Pas de dossier candidat partagé automatiquement ; projection explicite et révocable |
| Abonnements | Prépayé 1/6/12 mois + durée personnalisée ; essai 14 j et grâce 7 j proposés ; restrictions et dates ci-dessus à approuver |
| Paiement | Prestataire, devises, moyens de paiement, renouvellement automatique et règles de remboursement à préciser avant Sprint 5 |
| Conservation et export | Durées par catégorie, droits après expiration et procédure de suppression à valider avant production |
| Démarrage Sprint 1 | Valider le périmètre et les prérequis ; autorisation explicite avant code, migrations ou provisionnement |

**État de livraison :** rapport uniquement. Aucun fichier métier modifié, aucune base créée, aucune PR fusionnée, aucun remplacement du backend mobile, aucun push de cet audit.
