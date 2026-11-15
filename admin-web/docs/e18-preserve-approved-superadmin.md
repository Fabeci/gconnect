# E18 — Retour à l’interface Superadmin approuvée

Date : 25 octobre 2026  
Branche : `feat/e18-preserve-approved-superadmin`

## Intention confirmée par Tihamy

- Garder **strictement la connexion E16** (formulaire central Manrope, bleu #3761FF, thèmes).
- Après MFA validé par Django, présenter le tableau de bord approuvé dans `dist/superadmin-preview.html` : même sidebar, topbar, emplacements, thèmes, animations, pages et visuel réseau.
- Ne **pas** afficher la console de substitution inventée en E17.
- Préserver l’espace Établissement et les modifications E6 en local.

## Implémentation

- `dist/superadmin-login.html` conserve ses composants E16 et charge uniquement le bridge E18 à la place d’E17.
- `dist/superadmin-approved-e18.js` monte un frame de même origine en session autorisée seulement; la session WebToken demeure en mémoire dans l’API du parent. Aucun jeton dans l’URL, le DOM du frame, le stockage ou des messages.
- `dist/superadmin-connected-e18.html` conserve la cascade CSS, le markup/sidebar/topbar et l’animation du tableau E15. La prévisualisation initiale `superadmin-preview.html` reste intacte, à des fins de comparaison.
- Les sections réelles chargent les invitations depuis `listInvitations`; envoyer/révoquer fait appel à `sendInvitation` / `revokeInvitation` après contrôle du backend.
- Les autres modules conservent la navigation et des états d’attente lisibles, sans publier de métriques inventées. Les courbes et barres animées originales sont présentes, **explicitement qualifiées d’illustrations**, pas de statistiques réelles. Les API de répertoire, paiements, statistiques, audit restent à raccorder.
- Le message « Déconnexion » déclenche le parcours de sortie E16 du document parent.

## Vérifications et limites

- Analyse syntaxique des scripts du tableau et du bridge : OK.
- Rendu simulé en mémoire (DOM minimal) : navbar et hero réseau approuvés, invitation de test remontée depuis API factice, pas de chiffres/identités de la maquette dans le rendu.
- Test sur le vrai backend Django avec MFA et inspection visuelle navigateur : **reste à réaliser par un compte autorisé**.
- L’interface est servie en statique localement, mais seules les API du backend autorisées rendent des données réelles : un frame frontend ne constitue pas une frontière de sécurité.
- Facturation/paiement : **non raccordés**. Toute activation d’abonnement doit être validée côté serveur après paiement réel.
- Seule la branche E18 est modifiée. Aucune fusion, aucun déploiement.

## Tester sans toucher au dossier de travail

Arrêter d’abord **le serveur de prévisualisation E17 sur le port 8094** avec Ctrl+C dans son terminal, pour conserver la même origine que la session E17 déjà fonctionnelle. Ne pas interrompre le backend Django.

```bash
cd /mnt/chak/g-connect
git fetch origin feat/e18-preserve-approved-superadmin
E18_REP=$(mktemp -d /mnt/chak/gconnect-e18.XXXXXX)
git archive FETCH_HEAD dist | tar -x -C "$E18_REP"
python3 -m http.server 8094 --bind 127.0.0.1 --directory "$E18_REP/dist"
```

Ouvrir : http://127.0.0.1:8094/superadmin-login.html#login/superadmin

Comparaison visuelle sans authentification réelle : http://127.0.0.1:8094/superadmin-preview.html

Tests Node proposés : `node --test tests/superadmin-e18-preservation.test.mjs`.
