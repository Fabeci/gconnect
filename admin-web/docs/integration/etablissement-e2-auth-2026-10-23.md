# G-Connect — E2 Authentification et accès Établissement
Date : 23 octobre 2026

## Périmètre

Branche web : feat/etablissement-e2-auth-gate (fork taogoulahtihamy-gif/g-connect).
Base : feat/etablissement-api-e1-frontend.

Le backend partagé n'est pas modifié dans E2. Les clients web et mobile conservent les mêmes contrats HTTP.

## Parcours livré

- Accès direct à /etablissement-connexion.html : écran de connexion distinct.
- Accès anonyme à /etablissement.html : seul l'écran de connexion est présenté, avec remplacement de l'URL ; aucun menu ni indicateur privé n'est rendu.
- La connexion POST /api/v1/users/login/ se fait en HTTPS en production (HTTP localhost en développement).
- La session est ouverte seulement après confirmation du rôle etablissement, du rattachement institutionnel par GET /api/v1/users/me/ et de la portée institution par GET /api/v1/backoffice/stats/.
- L'espace Établissement est rendu après ces validations ; les indicateurs proviennent de l'API E1.
- La déconnexion en sidebar oublie le token en mémoire, efface les données affichées et les brouillons locaux.
- Le retour depuis l'historique (bfcache) demande une nouvelle authentification.
- Aucun token dans les URL, localStorage, sessionStorage ou cookies.

**Précision de sécurité :** la protection d'écran JavaScript n'est pas une frontière de sécurité. L'authentification, les rôles, l'appartenance institutionnelle et les filtrages des ressources doivent rester imposés par Django. E2 ne rend pas les modules Promotions, Membres, Événements, Équipe, Abonnement et Paramètres opérationnels : les interfaces restent locales tant que leurs API et permissions ne sont pas vérifiées.

## Tester sur Ubuntu

1. Terminal A : backend sur son port 8001 (base SQLite isolée).

~~~bash
cd /mnt/chak/gconnect-api-fabeci
export GCONNECT_DEV_DB_PATH=/mnt/chak/gconnect-api-fabeci/.venv/gconnect-web-e1.sqlite3
./.venv/bin/python -B manage.py runserver 127.0.0.1:8001 --settings=gconnect_api.settings.dev
~~~

Conserver les identifiants du compte administrateur d'établissement créé dans cette base. Le champ de la page de connexion contient un exemple, pas l'adresse réelle.

2. Terminal B : frontend depuis le fork personnel. Les commandes suivantes supposent que origin pointe bien vers taogoulahtihamy-gif/g-connect. Sinon, remplacer origin par le nom du remote correspondant, après git remote -v.

~~~bash
cd /mnt/chak/g-connect
git remote -v
git fetch origin
git switch -c feat/etablissement-e2-auth-gate --track origin/feat/etablissement-e2-auth-gate
python3 -m http.server 8086 --directory dist
~~~

Si la branche locale E2 existe déjà, utiliser git switch feat/etablissement-e2-auth-gate, puis git pull --ff-only.

3. Ouvrir http://127.0.0.1:8086/etablissement-connexion.html.
4. Se connecter, vérifier les indicateurs, visiter les modules puis utiliser « Déconnexion ».
5. Recharger : une nouvelle connexion doit être nécessaire (token éphémère).
6. Tester un rôle non-établissement et un compte établissement sans rattachement institutionnel : aucun tableau de bord ne doit apparaître.

## Configuration

En local (localhost/127.0.0.1), le frontend contacte par défaut http://127.0.0.1:8001/api/v1, pour ne pas entrer en conflit avec l'autre Django déjà sur le port 8000.

En production, configurer une URL HTTPS explicite par window.GCONNECT_API_BASE_URL ou la balise meta gconnect-api-base **avant** etablissement-api.js. Ne jamais inclure de mot de passe ou token dans cette configuration.

## Tests

~~~bash
node --check dist/etablissement.js
node --check dist/etablissement-api.js
node --test tests/etablissement-api.test.mjs tests/etablissement-auth-e2.test.mjs tests/etablissement.test.mjs
~~~

## Limites et suites

- Déconnexion locale : appeler /users/logout/ supprimerait le token Django potentiellement utilisé par l'application mobile. La révocation par appareil demande une évolution backend concertée.
- Pas de stockage persistant : reconnexion nécessaire après rechargement, nouvelle page ou fermeture.
- Auditer les permissions des futurs endpoints métier avant activation des listes d'utilisateurs et mutations.
- Le compte de test est créé uniquement sur la base SQLite locale, pas dans la base de production.
