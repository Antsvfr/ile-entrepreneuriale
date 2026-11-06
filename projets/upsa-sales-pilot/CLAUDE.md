# Maison UPSA Sales Pilot

Application **web locale** (React + TypeScript strict + Node ≥ 22.13 + SQLite) de pilotage commercial pour une commerciale du laboratoire UPSA qui reprend un secteur de pharmacies : fiche client 360°, paracétamol, gammes OTC, conventions et engagements, visites et RDV, groupements et plans trade, DN des nouveautés, plan d'action, exports, import du fichier « X20 Cockpit Territoire ».

**Où vit le code : uniquement sur le Mac d'Anton** (`~/Downloads/upsa copilot/UPSA-Sales-Pilot-transfert/1-projet/upsa-sales-pilot`). Il n'y a **pas de dépôt Git** connu et le zip ne contient **que la documentation** : le travail X20 du 22 octobre n'existe nulle part ici. Cette maison ne contient donc aucun code.

## Où lire
- `dossier/00_LIRE_EN_PREMIER_DOSSIER.md` : dossier de reprise (règles absolues §3, lancement §4).
- `dossier/projet/CLAUDE.md` (copié sous le nom `CLAUDE-projet.md`), `docs/` (règles métier, décisions, modèle de données, sécurité, feuille de route), `.claude/references/`.
- `branches.md`, `etat-des-lieux.md`.

## Règles absolues du projet (elles priment sur tout)
1. Ne jamais réinitialiser la base (`npm run db:reset` sur l'espace réel) sans autorisation explicite.
2. Ne jamais supprimer de données, de sauvegardes, de skills ni de fichier important.
3. Avant toute migration : sauvegarde vérifiée, changements présentés, accord d'Anton.
4. **Pas de push GitHub, pas de déploiement, pas de service cloud**, pas de télémétrie, pas de ressource tierce dans l'interface.
5. **Aucune donnée commerciale réelle** envoyée à un service externe ; tests, démo et exemples restent 100 % fictifs.
6. **Données réelles et Claude : l'autorisation de l'entreprise n'a jamais été confirmée.** Claude ne lit que les en-têtes et des comptages du cockpit ; c'est Anton qui lance l'import réel.
7. Ne rien inventer : critères ACP1/ACP2, défendre/maintenir/construire, nomenclature produits, formats « R sur O » / « Y2OBIC », termes contractuels.
8. Une donnée absente n'est jamais remplacée par 0 ; une donnée non confirmée n'est jamais présentée comme validée ; une prévision n'est jamais du facturé.
9. Pas de double comptage du CA (paracétamol non remboursé = « dont » ; les périmètres X20 ne s'additionnent pas).
10. Ne jamais présenter comme opérationnelle une fonction non développée.
11. Ne pas recréer le projet ni modifier l'architecture inutilement ; n'annoncer que les tests réellement exécutés.

**Conséquence pour l'île :** les agents de cette maison ne peuvent aujourd'hui que lire et améliorer la documentation, la feuille de route et les spécifications. Tout changement de code se fait avec Claude Code **sur le Mac**.

## Règles communes à toutes les maisons-projets
- Jamais de travail direct sur `main`. Toute modification part d'une branche dédiée, en petits commits testés.
- Aucune fusion, aucun push vers `main`, aucun déploiement, aucune migration de production sans l'accord explicite d'Anton **dans le chat**.
- Aucun secret (mot de passe, `service_role`, clé HMAC, jeton) dans Git, un journal, une URL ou le chat. Aucun accès aux variables d'environnement de production.
- Jamais de preuve fabriquée : un test ou une porte n'est « PASS » que s'il a réellement été exécuté, et le dit (local, mock, réel).
- Chaque intervention est consignée dans `journal.md` de la maison.
