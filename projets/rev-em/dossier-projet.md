# REV-EM — dossier complet du projet

> Dossier de passation à joindre au début d'une conversation avec Claude.
> État au **6 novembre 2026**. Dépôt : **github.com/Antsvfr/REV-EM** (ancien nom : `anaquizz`, l'ancienne adresse redirige).
> Il décrit ce qui existe réellement dans le code. Ce qui n'a pas été vérifié est signalé comme tel.

---

## 0. Pour Claude : comment utiliser ce dossier

- Tu reprends un projet **existant et volumineux**, développé sur plusieurs mois. **Lis ce dossier en entier avant de proposer du code.**
- L'utilisateur est l'auteur et le propriétaire du produit. Il écrit en **français** : réponds en français, simplement, sans jargon inutile.
- **N'invente jamais l'architecture.** Si tu as besoin d'un fichier, demande-le par son nom. Pour `index.html` (1,4 Mo, trop gros pour être lu en entier), demande la **section** voulue grâce à la carte du §4.3.
- **Règles non négociables** (détail au §11) :
  - pas de réécriture d'`index.html` ;
  - pas de second système quand un premier existe ;
  - pas de secret côté navigateur ;
  - `escapeHtml()` sur tout texte injecté ;
  - `lsGet`/`lsSet` (jamais `localStorage` en direct) ;
  - 5 langues pour tout nouveau texte ;
  - statuts de test honnêtes (PASS / PASS MOCK / NOT TESTED).
- Avant de dire qu'un correctif est « en ligne », vérifie qu'il est **fusionné dans `main`** : c'est la seule branche publiée (§2).

---

## 1. Le produit

**REV-EM** (anciens noms : *Anaquizz*, *Lyon Révision*) est une **plateforme de révision pour étudiants**, conçue autour de l'EM Lyon. Elle fonctionne dans le navigateur, comme application installable (PWA) et comme **application macOS native** (REV-EM.app, une WebView WKWebView qui charge le site).

**Objectif produit :** que l'étudiant sache toujours où il en est, ce qu'il maîtrise, ce qui reste fragile et quoi faire ensuite, **sans jamais lui présenter une donnée inventée comme réelle**.

### Fonctionnalités

| Domaine | Ce que l'étudiant fait |
|---|---|
| **Mes matières / Bibliothèque** | Matières → chapitres → cours ; recherche de matières |
| **Import de cours** | Import Center unique : PDF, Word (.docx), texte, Markdown, texte collé ; glisser-déposer ; anti-doublon ; matière imposée si l'import part d'une matière |
| **Page d'un cours (hub)** | 6 accès : Fiche, Résumé, Quiz, Quiz Flash, Flashcards, Questions (assistant) ; « Générer tout » |
| **Révision** | Quiz, Quiz Flash, flashcards, interrogation orale, examens blancs, onglet « À revoir » |
| **Banque de révision** | Chaque cours a une **banque** de questions et de flashcards ; chaque session est tirée et mélangée sans IA |
| **Révision intelligente** | Recommandations de quoi réviser (moteur déterministe) |
| **Ma progression / Mes statistiques** | Maîtrise par question, chapitre, matière ; activité ; réussites (badges) |
| **Planning** | Import .ics, fiche de cours, horloge « en cours », notes par cours |
| **Assistant IA local** | WebLLM **dans le navigateur** (aucune clé API, aucun serveur IA) ; page « Assistant IA » en espace de travail |
| **Maths & Stats** | Moteur mathématique exact (JS + SymPy via Pyodide), tuteur : Résoudre · Expliquer · M'entraîner |
| **Comptes** | Supabase Auth ; synchronisation multi-appareils ; mode invité 100 % local |
| **Sources connectées** | Brightspace (OAuth 2.0, Edge Functions) |
| **Applications connectées** | Liaison explicite d'un compte REV-EM avec un compte **LexNote** (autre produit de l'auteur) |
| **Command Center / « Que veux-tu faire ? »** | Palette de commandes ; actions rapides selon la situation |

---

## 2. Dépôt, branches, déploiement, état actuel

- **Dépôt :** `Antsvfr/REV-EM` (public).
- **Publication :** GitHub Pages publie **`main`**. C'est constaté sur l'exécution « pages build and deployment » n° 125 du 8 octobre 2026, commit `763ad74`. L'ancienne branche publiée, `claude/REV-EM-rebrand-restructure-ddinml`, **ne l'est plus**.
- **Adresse publique :** `https://antsvfr.github.io/REV-EM/`.
- **Cache :** `sw.js` sert la page et les modules `.js` en « réseau d'abord ». Une nouvelle version arrive donc **sans purge de cache ni de données**. Version de cache actuelle : `rev-em-v17` sur la branche de travail.

### Travaux en attente de fusion (non publiés)

| PR | Branche | Contenu | État |
|---|---|---|---|
| **#26** | `claude/anaquizz-rebrand-restructure-ddinml` (5 commits devant `main`) | Import fiable et supports de révision même sans IA ; correctif « Erreur — à relancer » ; ouverture directe du sélecteur de fichiers | **Ouverte, fusionnable** — à fusionner pour mettre en ligne |
| **#24** (brouillon) | `claude/planning-lexnote-live-session` | Bouton « Prendre mes notes dans LexNote » depuis le planning (migration 008, Edge Functions) | Brouillon ; exige le déploiement de la migration et des Edge Functions des deux côtés |
| LexNote **#10** (brouillon) | dépôt `Antsvfr/LexNote`, `claude/revem-course-launch` | Côté LexNote de l'intégration ci-dessus | Brouillon |

**Conséquence pratique :** tant que la PR #26 n'est pas fusionnée, le site en ligne a encore les bugs d'import décrits au §7.4.

---

## 3. Architecture générale

**Site statique, sans build, sans framework, sans bundler.** Un très gros `index.html` (HTML, CSS et JS inline, environ 25 000 lignes) et des modules JS autonomes chargés en `<script>` classique, dans cet ordre :

```
supabase-config.js → SDK Supabase (CDN) → auth.js → translations.js → smart-revision.js → statistics.js →
planning.js → content-sources.js → sync-engine.js → source-adapters.js → user-data.js → command-center.js →
quick-actions.js → subject-search.js → ai-engine.js → knowledge-engine.js → output-processor.js →
assistant-core.js → import-center.js → course-hub.js → connected-apps.js → revision-bank.js → math-core.js →
math-fast.js → math-verify.js → math-engine.js → math-tutor.js → math-cas-client.js → script principal d'index.html
```

Workers et fichiers à part :
- `ai-worker.js` : Web Worker qui importe `ai-host.js`, lui-même `ai-engine.js` (WebLLM hors du fil principal ; mode compatibilité possible sur le fil principal).
- `math-cas-worker.js` : Worker Pyodide + SymPy, créé à la demande (fichiers lourds dans `vendor/`, 21 Mo).
- `sw.js` : service worker (application hors ligne, mise à jour jamais imposée).
- `manifest.webmanifest`, `icons/` : PWA.

### Le patron « faits → moteur pur → pont → interface »

C'est la règle structurante du projet.
- **Moteur pur** (module `*.js`) : ne connaît ni le DOM, ni `state`, ni la navigation. Il reçoit des données et rend un résultat, et **se teste sous Node en quelques millisecondes**.
- **Pont** (dans `index.html`) : lit `state`, appelle le moteur, sait où mènent les choses.
- **Interface** : chaque onglet a sa paire `renderX()` (renvoie du HTML) et `attachXEvents()` ; `render()` dispatche selon `state.tab`.
- **Tout nouveau moteur suit ce découpage.**

---

## 4. Carte des fichiers

### 4.1 Modules JS (à la racine)

| Fichier | Global exposé | Rôle |
|---|---|---|
| `auth.js` | `LyonAuth` | Authentification Supabase et profil (`profiles`, bucket `avatars`) |
| `translations.js` | `LyonI18n` | i18n : `t(clé, vars)`, `setLang`, 5 langues (fr, en, es, de, it), environ 6 300 entrées |
| `user-data.js` | `LyonUserData` | **Synchronisation des données produit avec Supabase** (source de vérité pour un compte connecté), file d'attente, diagnostic |
| `sync-engine.js` | `LyonSync` | Couche de synchronisation des sources externes |
| `content-sources.js`, `source-adapters.js` | `LyonContentSources`, `LyonSourceAdapters` | Sources de contenu (Brightspace, etc.) |
| `smart-revision.js` | `LyonSmartRevision` | Moteur de recommandation « Révision intelligente » |
| `statistics.js` | `LyonStatistics` | Moteur « Mes statistiques » (réutilise les seuils de smart-revision) |
| `planning.js` | `LyonPlanning` | Logique du planning (.ics) |
| `command-center.js` | `LyonCommand` | Palette de commandes |
| `quick-actions.js` | `LyonQuickActions` | « Que veux-tu faire ? » : catalogue, conditions, poids |
| `subject-search.js` | `LyonSubjectSearch` | Recherche de matières ; `bestMatch` (exact > préfixe > mot), réutilisé par l'import |
| `import-center.js` | `RevemImport` | Import Center : validation du fichier, machine d'états, `ImportResult`, verdict du sélecteur de fichiers |
| `course-hub.js` | `RevemHub` | États des 6 ressources d'un cours, file séquentielle de génération |
| `revision-bank.js` | `RevemBank` | Banques quiz et flashcards : validation, dédoublonnage, lots, sessions, **banque extractive sans IA** |
| `ai-engine.js` | `RevemAI` | Moteur IA : paliers, erreurs, budget de contexte, machine d'états, diagnostic |
| `ai-host.js` / `ai-worker.js` | — | Hôte WebLLM (dans le worker) : chargement, génération en flux, arrêt |
| `output-processor.js` | `RevemOutput` | Sortie du modèle : filtre `<think>`, boucles, répétitions, alphabets étrangers, **lecture JSON tolérante** |
| `assistant-core.js` | `RevemAssistant` | Questions libres : analyse, stratégie, contexte, prompt, verrou de langue, calcul local |
| `knowledge-engine.js` | `RevemKnowledge` | Base de connaissances `ai-knowledge/` : schéma, index, recherche (provenance, `verified`) |
| `math-core.js`, `math-fast.js`, `math-verify.js`, `math-engine.js` | `RevemMath` | Maths exactes : parseur AST, rationnels, analyse, statistiques, probabilités, finance, vérificateur |
| `math-tutor.js` | `RevemMath` | Tuteur Maths & Stats (exercices, équivalence, indices, maîtrise) |
| `math-cas-client.js` / `math-cas-worker.js` / `math-cas.py` | `RevemMath` | CAS SymPy dans Pyodide, à la demande, avec délai et arrêt |
| `connected-apps.js` | `RevemLinks` | Interface pure « Applications connectées » (LexNote) |
| `sw.js` | — | Service worker |

### 4.2 Autres dossiers

- `supabase/migrations/` : schéma, **à appliquer dans l'ordre** (§5).
- `supabase/functions/` : Edge Functions Deno (§5).
- `ai-knowledge/` : connaissances structurées (finance, économie, statistiques), `index.json`, `topics.json`.
- `vendor/` : Pyodide, SymPy, KaTeX, auto-hébergés.
- `macos/REVEMOpenPanel.swift` : code natif **à intégrer** dans l'app macOS (§9).
- `tests/` : 64 fichiers (§12).
- `.claude/CLAUDE.md` et `.claude/skills/*/SKILL.md` : règles du projet pour Claude Code (16 skills par domaine).
- `scripts/` : `setup-supabase.sh`, `verify-setup.sh`.
- Documents `*.md` à la racine (§15).

### 4.3 Carte d'`index.html` (sections, numéros de ligne sur la branche de travail)

Chaque section commence par un bandeau de commentaire `/* ===== N. TITRE ===== */`.

| Ligne ≈ | Section |
|---|---|
| 1–5600 | `<head>`, **design system** (jetons CSS), styles de chaque fonctionnalité, structure HTML |
| 5619 | 1. Données — questions de quiz intégrées |
| 6242 | 1bis. Bibliothèque de matières — semestres et matières |
| 6285 / 6499 | 2. Fiches · 3. Flashcards (données intégrées) |
| 6568 | 4. **État global (`state`)** |
| 6991 | 4ter. Bibliothèque — helpers (`allSubjects`, `findSubject`…) |
| 7123 | 5. **Persistance** (`lsGet`/`lsSet`, cloisonnement par compte, synchronisation cloud) |
| 8188 | 5bis. Moteur de maîtrise par question |
| 8320 / 8356 | Réussites · suivi des activités |
| 8446 | 6. Quiz — logique |
| 8588 | 7. Navigation générale (`switchTab`, `render`) |
| 8824 | 7bis. Modes de révision intelligents |
| 9084 | 7ter. Tableau de bord — rendu |
| 9896 | 7quinto. Mes matières — bibliothèque de cours |
| 10869 | 7ter. **Importation de cours** (extraction, détection, génération, mode simplifié) |
| 12054 | 7ter-ter. **Hub de révision d'un cours** (`courseHubGenerate`, `courseHubPump`) |
| 12478 | 7ter-bis. **Import Center** (`openImportCenter`, `icOpenPicker`, `icWatchPicker`, `icHandoff`) |
| 13464 / 13602 | Onglet « À revoir » · mode examen |
| 14024 / 14504 | Quiz — rendu · fiches — rendu |
| 14668 | Sources connectées — Brightspace |
| 15161–15785 | Flashcards (liaison « Dans ton cours », logique, rendu) |
| 15785 | 11bis. **Assistant IA — moteur local WebLLM** (`aiHostGenerate`, `webllmChat`, `aiLoadModel`) |
| 16712–18297 | Assistant IA : contexte, exécution, questions libres, branchement du moteur mathématique |
| 18716 | 14ter. **AI Workspace V2** (page Assistant IA) |
| 19298–19413 | Activités, interrogation orale, progression |
| 21016 | Paramètres (export / import / réinitialisation) |
| 21130 | Applications connectées — LexNote |
| 21395 | Mon espace (profil) |
| 22096 / 22594 | Planning (.ics) · assistant IA dans la fiche de cours |
| 23913 / 23999 | Documents · examens |
| 24062 | Navigation principale (menus, mobile) |
| 24454 | Command Center |
| 24874 | 16. **INIT** |
| 25095 | 17. PWA (installation, hors ligne, mise à jour) |

---

## 5. Données et backend (Supabase)

- **Projet Supabase :** `otlkvlmzakklhugvaxeg.supabase.co`. La clé publiable / `anon` est dans `supabase-config.js`. **Elle n'est pas un secret**, puisque la sécurité repose **uniquement** sur les politiques RLS. Jamais de `service_role` côté navigateur.
- **Compte connecté :** Supabase est la **source de vérité**, `localStorage` n'est qu'un cache, cloisonné par compte (`currentStorageNamespace()` ; toujours `lsGet`/`lsSet`).
- **Invité :** tout reste local. C'est un état normal, pas une erreur.
- **Restent locaux** (volume) : binaires des documents et **PDF importés** (IndexedDB `em-lyon-revision-files`, magasin `pdfs`, indexé par identifiant de chapitre). Non cloisonné par compte : point d'attention.

**Migrations (dans l'ordre, chacune vérifie ses prérequis) :**
`000_schema` · `001_brightspace` · `002_centralisation` · `003_sync_layer` · `004_oauth_hardening` · `005_user_sync` · `006_integration_links` · `007_math_practice` (+ `008_integration_launch` dans la PR #24, non fusionnée).

**Tables :** `profiles`, `subjects`, `chapters` (le chapitre **est** le cours : fiche, résumé, `ai_quiz`, `ai_flashcards`, `original_text`…), `progress`, `question_stats`, `exam_history`, `activities`, `daily_stats`, `user_stats`, `badges`, `chapter_visits`, `course_notes`, `planning_events`, `documents`, `preferences`, `study_plans`, `ai_history`, `ai_cards`, `math_practice`, `brightspace_connections`, `oauth_states`, `sync_runs`, `integration_links`, `integration_link_intents`, `integration_nonces`.

**Edge Functions (Deno) :**
- `brightspace-connect / callback / refresh / status / disconnect / api` : OAuth 2.0 Brightspace.
- `integration-link` : actions de l'étudiant, avec son jeton.
- `integration-gateway` : serveur à serveur, signé HMAC, déployée en `--no-verify-jwt`. Protocole **`lexnote-revem/v1`** ; paquet partagé **généré** depuis le dépôt LexNote : `supabase/functions/_shared/integration/lexnote-revem-v1.mjs`.

---

## 6. Assistant IA (local)

- **WebLLM 0.2.85**, exécuté **dans le navigateur** (WebGPU), dans un Web Worker. Aucune clé, aucun serveur.
- **Trois paliers**, choisis par l'étudiant, **jamais de téléchargement automatique** :

| Palier | Modèle | Taille |
|---|---|---|
| Rapide | Llama 3.2 1B Instruct | ≈ 0,9 Go |
| Avancé | Phi-4 Mini Instruct | ≈ 3,4 Go |
| Expert | DeepSeek-R1 Distill Qwen 7B (raisonnement `<think>`) | ≈ 5,1 Go |

- **Fenêtre de contexte : 4 096 jetons** pour les trois (vérifié dans les sources de WebLLM). Au-delà, la réponse est coupée (`finish_reason: "length"`) ou la requête refusée.
- **Chaîne :**
  1. Questions libres : `assistant-core.js` (analyse → stratégie → contexte → prompt).
  2. Moteur : `aiHostGenerate` → worker.
  3. Sortie : `output-processor.js` (raisonnement filtré, boucles, doublons).
  4. Connaissances : `knowledge-engine.js`.
  5. Maths : `math-*.js` (calcul exact, l'IA n'explique que ce qui est vérifié).
- **États :** `state.aiStatus` ∈ `checking | nogpu | idle | loading | ready | error`. Toute fonctionnalité IA doit avoir un comportement **sans IA** (mode simplifié).
- **Une seule génération à la fois.** `aiWaitGenIdle` attend l'arrêt réel d'une génération interrompue.

---

## 7. Import de cours et révision (le cœur du produit)

### 7.1 Chaîne complète

```
Bouton « Importer un cours » (data-import-center / openImportCenter({pick:true}))
 → sélecteur de fichiers ouvert DIRECTEMENT, Import Center derrière (validation format/taille/contenu, remplacer, glisser, coller)
 → extraction réelle (pdf.js, mammoth) → icHandoff(ImportResult)
 → courseImportStart → courseImportProcessFile (détection : IA si DÉJÀ prête, sinon détection simple immédiate)
 → écran de confirmation (titre, matière, chapitre ; matière imposée si l'import part d'une matière)
 → courseImportResolveTarget : matière/chapitre, anti-doublon (dsConfirm), ENREGISTREMENT IMMÉDIAT (texte + PDF en IndexedDB)
 → IA prête : courseHubGenerate (file séquentielle : fiche, résumé, quiz, flashcards, questions de révision)
   IA pas prête : courseImportSaveWithoutAI → supports simplifiés (fiche, résumé, banque extractive)
 → page du cours (hub) → courseQuizStart / courseFlashStart (sessions tirées de la banque, sans IA)
```

### 7.2 Règles du domaine

- Le texte source n'est **jamais détruit**. La condensation (au-delà de 20 000 caractères) ne sert qu'à construire un texte de travail.
- Pas de doublon silencieux. Comparaison de noms par `LyonSubjectSearch.bestMatch`, jamais par `includes()` bidirectionnel.
- Les états des ressources du hub (`NOT_GENERATED / QUEUED / GENERATING / READY / ERROR`) sont **déduits** des champs du chapitre, jamais stockés.
- Quiz et flashcards : on joue **toujours** via le SessionBuilder (`courseQuizStart`, `courseFlashStart`), jamais la banque brute. Mélange par `RevemBank.shuffleArray` (Fisher-Yates).

### 7.3 Mode simplifié, sans IA (ajouté en PR #26)

`RevemBank.extractiveBank(texte)` produit du contenu **extractif, jamais inventé** :
- les notions sont des groupes nominaux qui reviennent dans le cours ;
- chaque question ou flashcard est **une phrase exacte du cours** avec une notion à compléter ;
- les mauvais choix sont **d'autres notions du même cours**, absentes de la phrase ;
- tout passe par les mêmes contrôles que le contenu IA (`parseQuizBatch`, `parseCardBatch`).

« Générer tout » remplace ensuite les supports simplifiés par la version IA.

### 7.4 Bugs corrigés dans la PR #26 (non encore en ligne)

1. **Import figé sur « Analyse du contenu… »** : la détection lançait le téléchargement du modèle (0,9 à 5 Go) et l'attendait. L'import n'utilise désormais l'IA que si elle est déjà prête.
2. **Cours en PDF sans quiz ni flashcards** en mode simplifié. Corrigé par la banque extractive.
3. **Les cinq supports en « Erreur — à relancer »** :
   - délais fixes sur le temps total, qui coupaient un modèle lent alors qu'il écrivait encore ;
   - échec signalé avant l'arrêt réel du moteur, d'où une cascade sur les étapes suivantes.

   Corrections : délai basé sur le silence du moteur, attente de l'arrêt réel, lecture JSON tolérante, budget de prompt correct, raison affichée sur la carte.
4. **Sélecteur de fichiers** : le bouton ouvre directement le sélecteur ; un sélecteur qui ne s'ouvre pas est détecté et expliqué (§9).

---

## 8. Intégration LexNote

- **LexNote** est un **produit séparé** de l'auteur (React, Vite, TypeScript, TipTap, IndexedDB, Supabase propre) : prise de notes de cours, transcription.
- **Une seule architecture d'échange : `lexnote-revem/v1`.**
  - Liaison **explicite** compte ↔ compte, jamais par e-mail.
  - Messages serveur à serveur signés (HMAC, nonce, expiration).
  - Intentions à usage unique.
  - Jamais d'identifiant, d'e-mail ni de donnée de cours dans une URL.
  - Jamais de secret inter-applications dans le navigateur.
  - Jamais de lecture de la base de l'autre application.
- Côté REV-EM : « Paramètres → Applications connectées » (`connected-apps.js`, `renderConnectedApps()`), migration `006_integration_links.sql`.
- En cours (brouillons) : « Prendre mes notes dans LexNote » depuis le planning (PR REV-EM #24 + LexNote #10). Détails dans `INTEGRATION_LEXNOTE.md`.

---

## 9. Application macOS (REV-EM.app)

- WebView **WKWebView** qui charge le site publié. Il existe aussi un widget macOS.
- **Le projet Xcode n'est pas dans ce dépôt**, ni dans aucun dépôt accessible aux sessions précédentes.
- **Problème connu, cause établie :** sur macOS, WKWebView n'ouvre **aucun** panneau de fichiers sans la méthode `WKUIDelegate.webView(_:runOpenPanelWith:initiatedByFrame:completionHandler:)`. Sans elle, « Choisir un fichier » ne fait rien, et WebKit se comporte comme « Annuler ».
- **À faire dans Xcode** (code prêt, **non compilé**) : intégrer `macos/REVEMOpenPanel.swift`, ajouter la méthode au délégué existant, et si l'app est sandboxée, activer `com.apple.security.files.user-selected.read-only`. Étapes exactes : `IMPORT_CENTER.md` §9.
- En attendant, le glisser-déposer et le texte collé fonctionnent dans l'app. La page détecte le sélecteur qui ne s'ouvre pas et l'explique.
- Rien n'a jamais été testé dans la vraie app depuis ces sessions : **NOT TESTED WKWEBVIEW**.

---

## 10. Design system, interface, langues

- **Jetons CSS** en tête d'`index.html` (« DESIGN SYSTEM REV-EM — SOURCE UNIQUE DES VALEURS ») : couleurs (`--ink`, `--surface`, `--red`…), rayons, ombres, échelle typographique, courbe `--ease` unique.
- **Tests de garde du design** : `design-system`, `detail`, `motion` (rayons plafonnés, pas de boîte dans la boîte, une seule ombre, échelle de police, durées d'animation).
- **Préfixes CSS** par fonctionnalité : `dash-`, `qz-`, `flash-`, `exam-`, `lib-`, `ai-`/`aiw-`, `pg-`, `sr-`, `st-`, `hub-`, `ic-`, `cw-`…
- **Priorités UX** : compréhension > efficacité > simplicité > cohérence > esthétique > innovation. « Premium » ne veut pas dire décoratif. Mobile d'abord (375 px), cibles tactiles de 44 px, `prefers-reduced-motion`, focus visible.
- **i18n :** tout texte visible passe par `t("namespace.cle", vars)`, avec **parité stricte dans les 5 langues** (fr, en, es, de, it). Le contenu pédagogique n'est jamais traduit automatiquement. Tester l'allemand pour les débordements.
- Voir `DIRECTION_ARTISTIQUE.md` et `COMPOSANTS.md`.

---

## 11. Règles de développement (extrait de `.claude/CLAUDE.md`)

1. **Analyser avant de modifier.** Lire le code réel et ses dépendances ; ne jamais deviner une architecture.
2. **Réutiliser l'existant.** Chercher la fonction équivalente avant d'en écrire une. Pour la maîtrise et la progression : `smart-revision.js` et `statistics.js`.
3. **Ne jamais casser l'existant**, ni réécrire `index.html`, ni remplacer une technologie sans raison vérifiable.
4. **Compatibilité ascendante** : valeur par défaut pour les données existantes (patron de `loadAllData()`).
5. **Sécurité** : aucun secret ni `service_role` côté navigateur ; `escapeHtml()` sur tout HTML dynamique ; RLS côté base.
6. **Performance** : pas d'appel IA ou réseau superflu, pas d'écouteur dupliqué ; pas de cache sans mesure.
7. **IA** : elle complète les systèmes déterministes ; comportement défini sans IA ; jamais de téléchargement de modèle non demandé ; une génération à la fois.
8. **Compatibilité WebKit** : pas d'API réservée à Chromium (pas de `showOpenFilePicker` seul) ; **pas de lookbehind** dans les expressions régulières (Safari / WKWebView < 16.4, vérifié par `compat-syntax`).
9. **Tests honnêtes** : PASS / PASS MOCK / NOT TESTED (REAL WEBLLM, GPU, MAC, WKWEBVIEW, SAFARI). Une compilation ou un double ne prouvent pas le comportement réel.
10. **Git** : ne jamais pousser sur `main` sans accord ; commits en français, avec trailer `Co-Authored-By` ; PR seulement sur demande.
11. **Fin de tâche** : résumer modifications, fichiers, fonctionnalités préservées, vérifications, limites, suite possible.

---

## 12. Tests

- **64 fichiers** dans `tests/`.
  - Moteurs purs sous Node : `*.test.js`, ex. `revision-bank.test.js`, `output-processor.test.js`, `ai-engine.test.js`, `math-engine.test.js`.
  - Interfaces dans un vrai Chromium (Playwright) : `*.test.mjs`, ex. `import-center-ui`, `course-hub-ui`, `ai-workspace-ui`, `dashboard`.
- **Lancer :**
  ```bash
  python3 -m http.server 9109            # à la racine du dépôt
  NODE_PATH=/opt/node22/lib/node_modules node tests/<fichier>
  ```
- **Dépendances de test** (non versionnées) :
  - `npm install --no-save --no-package-lock pdfjs-dist@4.0.379 mammoth pg @supabase/supabase-js` ;
  - `pip install reportlab python-docx` ;
  - PostgreSQL démarré pour `account-sync`, `security-audit`, `user-data`.
- **Suites ajoutées récemment :** `import-without-ai` (23), `import-picker` (45), `course-generation-engine` (37 ; moteur IA simulé fidèle au protocole d'`ai-host.js`).
- **Échec connu, antérieur et sans rapport avec ces changements :** `oauth-integration` (modules chargés par URL https, refusés par Node).
- **Instabilité connue du harnais :** un sélecteur de fichiers rouvert juste après un autre fermé « à vide » peut être annulé par Chromium/Playwright. Le test relance une fois.

---

## 13. Historique récent (sessions Claude Code)

- Comptes multi-appareils : synchronisation Supabase, cloisonnement par compte, indicateur de synchronisation.
- PWA (service worker, installation, hors ligne).
- Import Center unique ; hub de cours ; banque de révision et sessions mélangées.
- Assistant IA : audit et nouvelle architecture (paliers, worker, diagnostic) ; pipeline de sortie ; Knowledge Engine ; questions libres.
- Moteur mathématique exact et CAS SymPy ; tuteur Maths & Stats.
- AI Workspace V2 (page Assistant IA en espace de travail).
- Liaison LexNote `lexnote-revem/v1` (fusionnée), puis lancement depuis le planning (brouillons #24 / LexNote #10).
- Octobre 2026 (PR #26, ouverte) : supports en erreur, sélecteur de fichiers, import figé et mode simplifié extractif.

---

## 14. Limites connues et prochaines étapes

1. **Fusionner la PR #26** pour mettre en ligne les correctifs d'import, puis vérifier l'exécution Pages sur `main`.
2. **App macOS** : intégrer `macos/REVEMOpenPanel.swift` dans Xcode, compiler, tester l'import dans REV-EM.app.
3. **Valider sur le vrai matériel**, jamais fait depuis ces sessions : vrai WebLLM sur le Mac (temps de génération réels par palier), Safari, WKWebView.
4. **PR #24 / LexNote #10** : décider ; si on poursuit, appliquer la migration 008 et redéployer les Edge Functions des deux projets.
5. PDF en IndexedDB non cloisonné par compte (plusieurs comptes sur un même navigateur).
6. Mode simplifié : la qualité dépend du texte. Un cours très court ou très peu répétitif peut donner peu de questions.
7. `oauth-integration` à adapter (imports https sous Node).

---

## 15. Documents de référence (racine du dépôt)

| Document | Sujet |
|---|---|
| `IMPORT_CENTER.md` | Import Center : architecture, compatibilité, **WKWebView et étapes Xcode (§9)** |
| `COURSE_HUB.md` | Hub d'un cours, file de génération, **pannes corrigées et leurs causes** |
| `COURSE_PIPELINE_AUDIT.md` | Audit du pipeline import → fiche / flashcards / quiz |
| `REVISION_BANK.md` | Banques et sessions de révision |
| `AI_AUDIT.md` | Assistant IA : audit, cause racine, architecture (paliers, worker) |
| `AI_CHAT.md` | Questions libres (mode Général) |
| `AI_OUTPUT.md` | Pipeline de sortie du modèle ; JSON tolérant (§16) |
| `AI_KNOWLEDGE.md` | Knowledge Engine |
| `AI_WORKSPACE.md` | Page Assistant IA (espace de travail) |
| `AI_MATH.md`, `MATH_TUTOR.md` | Moteur mathématique, tuteur |
| `SYNC_UTILISATEUR.md`, `SYNC_ARCHITECTURE.md`, `SYNC_AUDIT.md`, `SUPABASE_DATA_ARCHITECTURE.md`, `SETUP_SUPABASE.md` | Données, synchronisation, Supabase |
| `INTEGRATION_LEXNOTE.md` | Liaison LexNote |
| `BRIGHTSPACE_SETUP.md`, `DEMANDE_ADMIN_BRIGHTSPACE.md`, `VALIDATION_ETAPE5.md` | Brightspace |
| `PWA.md` | Application installable, service worker |
| `COMMAND_CENTER.md`, `QUICK_ACTIONS.md`, `SUBJECT_SEARCH.md` | Navigation et recherche |
| `DIRECTION_ARTISTIQUE.md`, `COMPOSANTS.md` | Design |

---

## 16. Glossaire

- **Chapitre = cours** : un chapitre utilisateur porte le cours importé (`content` = fiche, `summary`, `aiQuiz`, `aiFlashcards`, `originalText`, `heuristicMode`…).
- **Banque** : ensemble des questions ou flashcards d'un cours ; une **session** en est un tirage mélangé.
- **Mode simplifié / heuristique** : supports produits sans IA, à partir du texte du cours.
- **Hub** : section « Outils de révision » de la page d'un cours.
- **Import Center** : la fenêtre d'import unique.
- **Palier** : Rapide / Avancé / Expert (modèle IA local).
- **Pages** : GitHub Pages, qui publie `main`.
- **REV-EM.app** : application macOS (WKWebView).
