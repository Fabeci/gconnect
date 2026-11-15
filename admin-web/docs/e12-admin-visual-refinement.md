# G-Connect — E12 · Harmonisation visuelle des consoles

Branche : `feat/e12-admin-visual-system-refinement` (base : E11).

## Références étudiées
- Trois captures fournies le 24 octobre 2026 : tableau de bord, paramètres et commutateurs.
- Enregistrement d'environ 44 secondes : menu latéral compact, survol bleu pâle, sélection bleu saturé, graphiques, panneau Superadmin et animations discrètes.

## Modifications livrées

### Établissement
- Conservation stricte des sept modules, de la sidebar flottante/compactable et de l'authentification serveur.
- Sélection de navigation bleu profond et survol secondaire bleu pâle ; état sombre dédié.
- Barre supérieure avec recherche Ctrl+K, bascule clair/sombre, cloche non connectée, profil, accès Paramètres et vraie déconnexion serveur via le flux existant.
- Avatar institutionnel monogramme bleu ; pas de fausse photo ni d'identité fabriquée.
- Paramètres en grille : identité du compte, apparence, animation, navigation, notifications non raccordées et sécurité en lecture seule.
- Graphique Étudiants/Alumni animé seulement à partir des comptes API autorisés ; état vide explicite en l'absence de données.

### Superadmin
- Conservation des quinze vues et du mode d'aperçu local restreint à localhost.
- Recherche davantage visible dans la barre du haut ; cloche/profil, date et thème maintenus.
- Navigation sélectionnée en bleu profond, deuxième niveau en bleu pâle, variante sombre à contrastes lisibles.
- Carte d'identité discrète en bas de sidebar, compatible mode compact.
- Paramètres unifiés : compte, apparence, notifications et politiques visualisées sans écriture serveur ni contournement MFA.
- Graphiques de barres animés et graphique de tendance SVG sur la page Statistiques (valeurs fictives toujours identifiées).

## Accessibilité, tests et limites
- Réduction des animations selon les préférences système ; indications de focus et états aria des menus et commutateurs.
- Contrôles manuels de syntaxe JS/CSS et d'exécution des 15 routes Superadmin, des interactions topbar et du parcours logique Établissement avec contexte authentifié simulé : OK.
- Test de régression ajouté : `tests/admin-e12-visual-system.test.mjs`. Commande sur copie locale E12 : `node --test tests/admin-e12-visual-system.test.mjs`.
- Tests navigateur avec captures et exécution complète de la suite CI : restent à faire sur un environnement équipé d'un navigateur. GitHub Actions était précédemment bloqué par le plafond du compte GitHub.
- Aucune configuration de facturation, de notification, d'abonnement ou de permission backend n'a été modifiée. Les contrôles métier demeurent à intégrer via API.

## Comparaison locale peu coûteuse

```bash
cd /mnt/chak/g-connect
git fetch origin feat/e12-admin-visual-system-refinement
GCONNECT_E12_DIR=$(mktemp -d /mnt/chak/gconnect-e12.XXXXXX)
git archive FETCH_HEAD dist | tar -x -C "$GCONNECT_E12_DIR"
python3 -m http.server 8091 --bind 127.0.0.1 --directory "$GCONNECT_E12_DIR/dist"
```

Superadmin : `http://127.0.0.1:8091/superadmin-preview.html#dashboard`.
Établissement : `http://127.0.0.1:8091/etablissement.html` (nécessite le backend local et un compte autorisé).
