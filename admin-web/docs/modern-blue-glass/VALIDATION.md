# Modern Blue Glass — validation du 21 octobre 2026

Direction appliquée aux sept vues : Manrope locale, bleu #3761FF, texte #17243D,
fond #F5F7FC et bleu glacier, surfaces translucides et rayons partagés.
Le travail non commité trouvé au démarrage a été conservé et complété.

## Captures

- [Accueil desktop, 1440 px](home-desktop.png)
- [Accueil mobile, 390 px](home-mobile.png)
- [Sidebar réduite](sidebar-collapsed.png)
- [Menu mobile ouvert](sidebar-mobile.png)
- Les captures `jobs`, `network`, `school`, `messages`, `profile` et `settings`
  sont disponibles en 1440 et 390 px dans ce dossier.

## Vérifications

- Syntaxe JavaScript et suite existante `node --test tests/frontend.test.mjs` : réussite.
- Chromium / Playwright : les 7 pages aux largeurs 320, 390, 768, 1024 et 1440 px
  ne débordent pas horizontalement ; les titres utilisent Manrope.
- Recherche latérale et recherche d’offres, filtres, résultat vide, sauvegarde d’offre,
  réduction/déploiement, loupe en mode réduit, navigation mobile et Échap : réussite.
- Le formulaire conserve son texte lors de la réduction de la sidebar.
- Aucune erreur JavaScript pendant les parcours.
- Captures produites avec réduction des animations activée ; CSS désactive également
  les transitions et le défilement animé avec `prefers-reduced-motion`.
- Revue visuelle : accueil desktop/mobile, cartes offres/réseau/établissements,
  formulaire profil, état vide Messages, Paramètres et les deux modes de sidebar.
- Contrastes calculés sur les couleurs de référence : texte principal/fond 14,45:1,
  texte secondaire/bleu clair 5,37:1, blanc/bouton principal 4,87:1,
  lien/bleu clair 5,68:1. Les transparences restent à apprécier dans leur contexte ;
  ceci n’est pas un audit complet d’accessibilité.

La photo est locale, sans filtre coloré, sans texte superposé ; le visage reste visible
sur mobile. Le menu mobile fermé est masqué aussi pour la navigation au clavier.

## Limites préexistantes

Le projet reste une démonstration frontend. Authentification, messagerie et sauvegarde
réelle du profil ne sont pas connectées. Les données de présentation sont conservées.
Les contrôles navigateur concernent Chromium ; Safari et Firefox n’ont pas été testés.
