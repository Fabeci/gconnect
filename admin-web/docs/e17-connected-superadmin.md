# E17 — Console Superadmin authentifiée (G-Connect)

## Résultat

Les pages de connexion Superadmin et Établissement E16 restent séparées. Après validation du mot de passe et de la MFA par Django, /superadmin-login.html affiche la console Superadmin dans le même document ; l'aperçu local indépendant ne reçoit jamais de jeton d'accès.

## Interface livrée

- Identité G-Connect, police Manrope, bleu #3761FF, grands arrondis.
- Sidebar bleue, groupes de navigation, variante compacte et tiroir mobile.
- Barre supérieure avec date, thème clair/sombre, cloche informative, avatar, profil, déconnexion.
- Tableau de bord : nombre d'invitations en attente reçu de Django et statut MFA ; pas de statistiques fictives.
- Invitations réelles : liste, recherche, création pour un identifiant d'établissement existant et révocation avec confirmation.
- Sections Abonnements, Facturation, Entreprises, Établissements, Utilisateurs, Audit et Sécurité indiquées comme non raccordées au backend.
- Responsive, animations, adaptation au réglage reduced-motion.

## Contrat de sécurité

- Le WebToken reste exclusivement en mémoire dans GConnectEstablishmentApi. Aucun jeton dans le HTML, l'URL, le stockage local ou de session.
- Avant chaque rendu : session active et rôle exact superAdmin.
- Le backend Django décide des permissions effectives.
- Expiration de session : fermeture de l'accès et retour à la connexion.
- Recharger la page impose volontairement une nouvelle authentification.
- Déconnexion via l'API existante.

## Limites produit

1. Il n'existe pas encore dans ce périmètre de répertoire backend global des établissements/entreprises, ni d'API des abonnements, factures et paiements.
2. Le parcours métier « paiement confirmé → abonnement actif → invitation » reste à implémenter **côté backend**, puis à relier au frontend. Le formulaire d'invitation actuel appelle l'endpoint existant sans vérification de paiement ; il est réservé aux opérations internes autorisées.
3. La cloche affiche un message d'indisponibilité, pas de fausses notifications.
4. Les tests automatisés ne remplacent pas l'essai du vrai compte Superadmin avec MFA et backend local.

## Tester dans un dossier distinct de la branche E6

Sur Ubuntu, depuis le clone G-Connect :

    cd /mnt/chak/g-connect
    git fetch origin feat/e17-superadmin-authenticated-console
    mkdir -p /mnt/chak/gconnect-e17-preview
    git archive FETCH_HEAD dist | tar -x -C /mnt/chak/gconnect-e17-preview
    python3 -m http.server 8086 --bind 127.0.0.1 --directory /mnt/chak/gconnect-e17-preview/dist

Ouvrir http://127.0.0.1:8086/superadmin-login.html. Le backend Django local est attendu sur 127.0.0.1:8001 ; autoriser l'origine 8086 dans CORS si nécessaire.

Pour exécuter les tests après avoir récupéré la branche dans un worktree indépendant :

    node --test tests/superadmin-e17-connected.test.mjs

Vérifier : MFA, console, données réelles d'invitations, thème sombre, mobile, erreurs d'API, déconnexion, rechargement et refus des rôles non Superadmin.

Aucune fusion et aucun déploiement.
