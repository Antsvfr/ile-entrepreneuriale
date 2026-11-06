# Dossier projet — LexNote + REV-EM

*État au 6 novembre 2026. À coller tel quel au début d'une nouvelle conversation avec Claude.*

> **Consigne pour Claude** : ce dossier résume le projet et son état. Le code des dépôts reste la source de vérité. Vérifie toujours les SHA, l'état des PR et la CI sur GitHub avant d'agir, car ce document peut être dépassé.

---

## 1. Le produit

Ce sont deux applications distinctes et complémentaires, développées par la même personne (étudiant·e, tests sur Mac).

**REV-EM** est le centre de pilotage étudiant : planning, matières, cours, examens, révisions, progression, ressources générées, et l'accès aux séances LexNote.

**LexNote** est le moteur de capture et de compréhension du cours. Il couvre :
- matières, modules et séances (CM, TD, TP, séminaires, ateliers, projets) ;
- prise de notes riche ;
- transcription du professeur ;
- documents du professeur ;
- consolidation du cours et supports d'étude.

LexNote doit rester excellent **même sans IA**.

**Parcours cible :** planning REV-EM → ouverture du cours → LexNote (notes, transcription, documents) → cours consolidé → supports de révision → REV-EM (planification, quiz, flashcards) → maîtrise → examen. L'utilisateur ne doit pas avoir l'impression d'utiliser deux produits mal reliés. Il ne faut **jamais créer de fonctions en double** entre les deux applications.

**Priorités, dans l'ordre :**
1. fiabilité ;
2. sécurité ;
3. conservation des données (**une perte silencieuse de notes est un bug critique**) ;
4. fluidité REV-EM ⇄ LexNote ;
5. performance ;
6. expérience utilisateur ;
7. nouvelles fonctions.

Le rendu doit rester premium, sobre, en dark mode, responsive et accessible.

**Provenance des contenus :** `USER_NOTE`, `PROFESSOR_TRANSCRIPT`, `PROFESSOR_DOCUMENT`, `AI_INFERENCE`, `VERIFIED_EXTERNAL_SOURCE`.

---

## 2. Dépôts, branches et PR

### LexNote — `Antsvfr/LexNote`
- **Stack :** React + TypeScript + Vite, PWA (workbox), IndexedDB local-first avec synchronisation, Supabase (Auth, Postgres avec RLS, Edge Functions en Deno), hébergement Vercel.
- **Tests :** Vitest et Playwright.
- **Chaîne de PR empilées, en brouillon, à fusionner dans cet ordre :** `#12 → #10 → #11 → #13 → #14`.
  - #12 `claude/reconcile-main-production-schema` : réconciliation du schéma de production.
  - #10 `claude/revem-course-launch` : lancement d'un cours depuis REV-EM.
  - #11 `claude/generalize-lexnote-smart-transcript` : généralisation du produit (toutes filières) et actions sur la transcription.
  - #13 `claude/persistent-revem-auth` : session persistante, « Rester connecté », connexion automatique REV-EM → LexNote.
  - **#14 `claude/production-readiness-observability`** : branche de travail actuelle (préparation à la mise en production).
- **Dernier SHA connu de #14 : `caf8b40`** (correctif micro). La CI était sans échec et la prévisualisation Vercel prête.
- **Prévisualisation :** https://lex-note-git-claude-production-readiness-observability-svfr.vercel.app
- **La production = `main`**, qui est plus ancienne. Les correctifs de #14 n'y sont pas tant que la chaîne n'est pas fusionnée et déployée.

### REV-EM — `Antsvfr/REV-EM`
- **Stack :** JavaScript sans bundler ni `package.json`, servi par GitHub Pages ; Supabase (migrations `000` à `009`, Edge Functions `integration-gateway`, `integration-link`, `brightspace-*`).
- **Pas de CI.** Les tests sont des scripts `node tests/*.test.{js,mjs}`.
- **Chaîne :** `#24 → #25`. La branche de travail `claude/lexnote-sso-launch` (#25, SHA `b7773d5`) contient #24.

**Règles Git :**
- ne jamais travailler sur `main` ;
- ne jamais fusionner sans accord explicite ;
- jamais de rebase de la chaîne empilée (commits de fusion uniquement) ;
- des commits petits, testés et sans aucun secret.

---

## 3. Intégration REV-EM ⇄ LexNote

- **Protocole :** `lexnote-revem/v1`, signé par HMAC entre les deux serveurs.
  - En-têtes : `kid`, sender, recipient, horodatage avec tolérance d'horloge, nonce anti-rejeu.
  - Rotation de clé possible via `INTEGRATION_KEY_PREVIOUS[_ID]`.
  - Aucun JWT ne circule entre les serveurs.
- **Liaison des comptes :** les étapes sont start, inspect, confirm, puis CONNECTED. Le statut peut ensuite être consulté ; la liaison est révocable et isolée par utilisateur.
- **Lancement d'un cours** (REV-EM migrations 008/009) :
  - REV-EM crée une intention courte, avec un nonce stocké **haché**.
  - LexNote appelle `IDENTIFY_LAUNCH` puis `REDEEM_LAUNCH`. L'intention est à usage unique : un double clic, un rejeu ou une intention expirée sont refusés.
- **Connexion automatique :** seulement avec le consentement explicite de l'utilisateur et sur un appareil de confiance. Sans consentement, l'utilisateur revient à l'écran de connexion normal. Rien de sensible ne passe dans l'URL.
- Le code partagé du protocole est généré par `scripts/build-integration-bundle.mjs`, avec une vérification d'identité entre les deux dépôts.

---

## 4. Outillage de préparation à la production (ajouté dans #14)

- **Scripts** (`scripts/prod/`) :
  - `preflight`, `migration-status` (lecture seule) ;
  - `release-gates` et `evidence` (preuves dans `release/evidence.json`, non versionné) ;
  - `supabase-smoke`, `integration-diagnostic`, `real-e2e`, `study-ai-smoke` ;
  - `rehearsal` (sauvegarde/restauration, retour arrière de la base, migrations REV-EM) et `frontend-rollback-drill` ;
  - `local-stack` et `local-verify`.
- **Deux stacks Supabase locales :**
  - `node scripts/prod/local-stack.mjs up --revem-repo ../rev-em`, puis `verify --record`, puis `down`.
  - Ports : LexNote 54421/54422, REV-EM 54521/54522.
  - Clé HMAC de test aléatoire, jamais affichée.
  - Mode `INTEGRATION_LOCAL=1` qui n'accepte que les adresses de boucle locale.
- **Serveur :**
  - fonction `health` ;
  - budget IA global ;
  - interrupteur d'urgence `STUDY_AI_ENABLED=false` (répond `503 ai_disabled` avec `Retry-After`) ;
  - budgets par action ;
  - journaux sans contenu.
- **Application :**
  - page Diagnostic (version, build, aucun secret) ;
  - identifiants d'erreur ;
  - mise à jour PWA jamais imposée pendant une transcription ou une édition ;
  - gestion des conflits.
- **Documentation :**
  - `docs/PRODUCTION_RUNBOOK.md` : §I.1 ordre de fusion, §I.2 sauvegarde, §I.5 déploiement A–G, §I.7 retour arrière, §I.12 checklist PWA, §I.13 règle après chaque fusion, §I.14 répétitions locales à 0 €, Partie II intégration ;
  - `docs/TEST_ENVIRONMENT.md` et `docs/DATA_SAFETY_AUDIT.md`.

---

## 5. Portes de mise en production (`release/gates.json`, 23 portes)

Dernier état calculé : **15 PASS, 8 NOT_RUN, 0 FAIL → NOT READY.** Les preuves liées au SHA ont été établies sur `2cd7c88` ; le commit `caf8b40` les invalide, il faut donc les rejouer.

| Porte | État | Remarque |
|---|---|---|
| typecheck, unit-tests, build, bundle-check, preflight, e2e-critical, deno-tests | PASS | à rejouer sur le dernier SHA |
| merge-chain | PASS | chaîne vérifiée sur GitHub |
| migration-status | PASS | production en lecture seule : migrations 07→13 appliquées, 14→18 absentes, aucune divergence |
| migrations-on-test, supabase-smoke | PASS | Supabase **local** sur le Mac (12 migrations, smoke 25/25), exécuté par l'utilisateur |
| backup-restore-rehearsal, rollback-db-compat, rollback-frontend-local | PASS | PostgreSQL 16 local (10/10, 9/9) ; drill frontend 7/7 |
| revem-local-validation | PASS (local) | REV-EM `b7773d5` : 33 fichiers de tests, 0 échec ; migrations 000→009 18/18 sur un vrai PostgreSQL |
| integration-diagnostic, integration-real-e2e, ai-killswitch-local | NOT_RUN | demandent les deux stacks locales sur le Mac (`local-stack.mjs`) |
| ai-real-smoke | NOT_RUN | demande un vrai fournisseur IA, payant, donc hors budget 0 € |
| browsers-firefox-webkit | NOT_RUN | à lancer sur le Mac |
| pwa-manual | NOT_RUN | checklist PWA 1–9 sur un appareil réel |
| backup | NOT_RUN | sauvegarde réelle de production, en lecture seule, faite par l'utilisateur |
| rollback-rehearsed | NOT_RUN | exige un projet Supabase de TEST hébergé et Vercel ; proposition de scinder en local/cloud, non appliquée |

**Règle :** ne jamais marquer une porte PASS sans exécution réelle. Une validation locale n'est pas une validation cloud.

---

## 6. Dernier chantier : régression de la transcription (correctif `caf8b40`)

**Symptôme en production :** « Aucun microphone détecté » sur un Mac qui a un micro intégré.

**Cause :** trois erreurs différentes étaient toutes affichées comme « Aucun microphone détecté », sans vérification :
- `NotFoundError` de `getUserMedia`. Sur Mac, c'est le cas typique d'un navigateur non autorisé par macOS : il ne voit alors aucun micro.
- `OverconstrainedError`.
- API micro absente.

**Correctif :**
- `src/services/capture/mic.ts` vérifie la cause (permission, périphériques, système) avant d'afficher un message.
- Nouvel essai automatique avec `{ audio: true }`.
- Le flux de vérification est refermé quand aucun enregistrement audio n'est demandé.
- Messages de la reconnaissance vocale précis (`audio-capture`, `service-not-allowed` → Dictée sur Safari).
- Le panneau n'affiche plus d'états contradictoires ; un seul bouton « Réessayer ».

**Tests :** 753 tests unitaires et 129 tests Playwright Chromium passés.

**À valider sur le Mac réel**, sur la prévisualisation : Chrome, Safari, application installée, refus de permission, réglage macOS Confidentialité › Microphone.

---

## 7. Actions qui restent à l'utilisateur

1. **Tester le correctif micro** sur la prévisualisation (6 points : Chrome, Safari, PWA, refus, réglage macOS, pause/reprise).
2. **Lancer les deux stacks locales**, puis coller la sortie :
   ```bash
   cd lexnote && git pull && npm ci && node scripts/prod/local-stack.mjs up --revem-repo ../rev-em && node scripts/prod/local-stack.mjs verify --record ; node scripts/prod/local-stack.mjs down
   ```
3. **Firefox et WebKit :**
   ```bash
   cd lexnote && npm ci && ALL_BROWSERS=1 npx playwright install firefox webkit && npm run test:e2e:browsers 2>&1 | tail -30
   ```
4. **Checklist PWA 1–9** (runbook §I.12), avec PASS ou FAIL et ce qui est observé.
5. **Sauvegarde de production en lecture seule** (runbook §I.14.D) : `pg_dump`, SHA-256, taille et lecture du dump, mot de passe saisi localement de façon masquée.
6. **Décider** de la scission de `rollback-rehearsed` et du fournisseur IA (payant ou non).

---

## 8. Ordres futurs (quand toutes les portes bloquantes seront PASS)

- **Fusion :** LexNote `#12 → #10 → #11 → #13 → #14`, puis REV-EM `#24 → #25`. Commits de fusion uniquement, avec la règle §I.13 après chaque fusion.
- **Déploiement :**
  1. sauvegarde de production ;
  2. migrations Supabase LexNote 14→18 ;
  3. Edge Functions ;
  4. secrets ;
  5. Vercel (LexNote) ;
  6. GitHub Pages (REV-EM) ;
  7. smoke tests de production.
- **Retour arrière :**
  - la base est **additive**, donc l'ancien code reste compatible, sans retour arrière destructif ;
  - redéployer la version précédente des Edge Functions ;
  - Vercel *Instant Rollback* ;
  - interrupteur IA `STUDY_AI_ENABLED=false` sans redéploiement ;
  - clé d'intégration : remettre l'ancienne clé en `INTEGRATION_KEY`.

---

## 9. Contraintes permanentes

- **Budget : 0 €.** Pas de Supabase Branching, pas de nouveau projet payant, pas d'appel IA payant.
- **Ne rien fusionner, ne rien déployer** en production et ne modifier ni les données ni les secrets de production sans accord explicite.
- **Aucun secret** (mot de passe, `service_role`, clé HMAC, jeton) dans Git, les journaux, une URL ou le chat.
- **Jamais de preuve fabriquée.**
- **Pas encore commencé, volontairement :** cours intelligent complet, RAG global, recherche universelle, moteur de révision adaptatif, tableau de bord V2, fonctions sociales, collaboration.
- **Mode de travail attendu :** autonome. Inspecter, tester, corriger, documenter. Ne demander une action à l'utilisateur que si elle est physiquement impossible depuis l'environnement, et alors regrouper les demandes en une commande unique.
