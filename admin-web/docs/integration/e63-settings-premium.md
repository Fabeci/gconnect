# E63 · Profil & paramètres Premium V2

## Contexte
La capture du Superadmin du 7 novembre 2026 montrait deux blocs statiques :
« Mon profil » et « Accès protégé ». E63 remplace **uniquement**
`pages.parametres` dans le shell E19 avec une identité visuelle distincte.

## Interface
- En-tête **transparent** et éditorial : identité **ivoire / mauve / bleu doux /
  cuivre**, illustration flottante d'une fiche personnelle avec orbites.
- Quatre sections principales, animations d'entrée et micro-interactions :
  **Votre signature** (avatar, nom, e-mail, téléphone, rôle),
  **Mon espace, mon rythme** (préférence de mouvement),
  **Votre coffre d'accès** (état MFA, sessions personnelles, codes restants),
  **Raccourcis** (journal, sessions, à propos).
- Disposition équilibrée avec boutons courts, sans longs boutons qui traversent
  les cartes. Adaptation mobile, thème sombre et désactivation des animations
  si `prefers-reduced-motion` ou `data-motion="off"`.

## Connexion aux vraies fonctionnalités
**Aucune nouvelle donnée de démonstration n'est injectée.**
E63 utilise exclusivement les ressources existantes :
- `GET/PATCH /api/v1/users/web-profile/` : le modal professionnel E28 reste
  le point d'édition du compte (prénom, nom, téléphone, photo). Le rôle et
  l'e-mail sont protégés côté serveur. Le formulaire contient une prévisualisation
  d'image et permet de la retirer, via le mécanisme existant.
- `POST /api/v1/users/web-change-password/` : le formulaire E29 existant
  valide l'ancien mot de passe, la politique Django et révoque les sessions
  après changement, avec reconnexion MFA nécessaire.
- `GET /api/v1/backoffice/security-v2/?days=30` : fournit l'état réel
  de la MFA, la longueur de **mes** sessions actives et le nombre de **mes**
  codes de secours encore disponibles. Ces données sensibles restent limitées
  au Superadmin authentifié. Aucun code, secret ou IP n'est fourni.
- Les raccourcis **Journal d'audit** et **Sessions & sécurité** utilisent
  les modules E61 et E62. « À propos » utilise le dialogue existant.
- Le sélecteur de mouvement est relié à
  `professional-motion-preference` déjà présent, qui applique
  `document.documentElement.dataset.motion`, appelle
  `SuperadminMotion.preferenceChanged()` et stocke la préférence dans le
  navigateur sous `gconnect-motion-<id du compte>`.
- Le thème commun existant reste en place ; aucun bouton de changement de
  thème n'est réintroduit dans la barre supérieure.

## Contraintes de sécurité
- **Aucune migration** ni création de nouvelle table ou enregistrement métier.
- La page n'expose jamais de jeton, mot de passe, code MFA ou IP.
- Le rendu de la photo passe par le validateur `safeProfileImage` du shell,
  le nom et l'e-mail par `safe` ; la construction HTML échappe les entrées
  renvoyées par le backend.
- L'état MFA n'est pas simulé : si l'API est indisponible, la page affiche
  des tirets et une erreur explicite, sans afficher des compteurs à zéro
  fictifs.
- Les préférences d'animation sont **locales à ce navigateur** ; elles ne
  sont pas présentées comme des réglages universels synchronisés.
- Le module E63 n'est activé que lorsque `isPlatformAdmin` est vrai.
  Les réglages E28 des autres rôles et tous les modules E38–E62 sont inchangés.

## Validation
```bash
node --test tests/settings-e63.test.mjs
node scripts/verify-e63-settings-visual.cjs
```
Le test navigateur vérifie l'identité visuelle, les contrastes WCAG AA,
l'ouverture des parcours réutilisés, le mouvement, le mobile et l'absence de
débordement horizontal. Captures :
`artifacts/auth/e63-settings-desktop.png` et
`artifacts/auth/e63-settings-mobile.png`.

Les tests Chromium simulent les réponses API **en CI uniquement**, sans
se connecter à la base réelle et sans changer de mot de passe.

## Déploiement local sans perte
Mettre à jour seulement `feat/e54-invitations-premium` depuis
`/mnt/chak/g-connect`. Si `git status --short` affiche des modifications
locales, vérifier avant tout changement : ne pas utiliser de `reset --hard`,
`clean` ou suppression de SQLite. Le backend actuel E62 suffit à E63,
donc **aucune commande migrate supplémentaire**.

Les PR restent en brouillon. Valider le rendu réel en ouvrant
Superadmin → Paramètres après un rechargement sans cache.
