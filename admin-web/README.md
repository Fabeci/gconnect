# G-Connect

Plateforme web reliant étudiants, alumni, établissements et entreprises.

## Première livraison

Prototype frontend responsive avec la charte officielle `#3761FF`, les logos G-Connect, une sidebar flottante en glassmorphism, une recherche d'offres, les vues Accueil, Offres, Réseau, Établissements, Messages, Profil et Paramètres.

Les offres et profils affichés sont des exemples de présentation. Aucune authentification, sauvegarde de profil, messagerie ou candidature réelle n'est encore connectée à une API.

## Démarrer

```bash
cd g-connect/dist
python3 -m http.server 8080
```

Ouvrir http://localhost:8080.

## Suite du développement

- Next.js et TypeScript pour l'application maintenable.
- FastAPI avec PostgreSQL pour les comptes, organisations, profils, offres et candidatures.
- Authentification, rôles et permissions.
- Tests automatisés et déploiement.

Les logos fournis par le propriétaire du projet sont dans `dist/assets/`.

## Interface V0.3 (branche feat/gconnect-premium-v03)

L'accueil utilise `dist/premium.css`, qui ajoute un fond bleuté satiné et une sidebar translucide, des cartes d'offres plus arrondies et masque les anciennes initiales carrées des entreprises. L'image de couverture est sous licence Unsplash (Seth Ebenezer Tetteh : https://unsplash.com/photos/a-man-with-a-laptop-in-his-hand-DeqswsZEO3Y).

### Tests

```bash
node --check dist/app.js
node --test tests/frontend.test.mjs
```

Les offres, membres et chiffres de cette V0.3 sont des données de présentation, sans connexion au backend.

## Modern Blue Glass

La branche `feat/gconnect-premium-v1` utilise Manrope en local, la palette officielle
`#3761FF`, des surfaces translucides et un fond bleu glacier. Les sept vues partagent
les tokens de `dist/tokens.css` et les composants responsive de `dist/campus.css`.
La photographie locale conserve ses couleurs naturelles et se place à droite du texte
sur desktop, sous le texte sur mobile. Source : Seth Ebenezer Tetteh / Unsplash,
https://unsplash.com/photos/a-man-with-a-laptop-in-his-hand-DeqswsZEO3Y.
Manrope est fourni avec sa licence OFL dans `dist/assets/fonts/`.

La sidebar flottante se réduit sans reconstruire le formulaire actif. En mode réduit,
la loupe ouvre le champ de recherche. Sur mobile, la navigation se ferme après sélection
ou avec Échap. Les animations respectent `prefers-reduced-motion`.

Captures et rapport : [docs/modern-blue-glass/VALIDATION.md](docs/modern-blue-glass/VALIDATION.md).
Pour les contrôles navigateur, installer Playwright dans un environnement de développement,
lancer le serveur local sur le port 8080, puis exécuter `node scripts/verify-visual.cjs`.
Les fonctions de démonstration et leurs limites backend sont conservées.

## Authentification web

Le parcours commun est accessible sur `/auth.html`, avec les entrées Superadmin,
Établissement et Étudiant/Alumni. Les pages établissement existantes utilisent ce
même parcours et conservent leur tableau de bord connecté.
Voir [les contrats, limites et tests](docs/auth/README.md).

```sh
npm test
npm run test:auth
```
