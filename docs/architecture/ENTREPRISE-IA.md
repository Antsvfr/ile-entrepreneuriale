# L'Entreprise des Agents — architecture fonctionnelle et technique

*Version 1 — 6 novembre 2026. Document de conception : rien de ce qui suit n'est encore construit, sauf mention « EXISTE ».*

**Règle de lecture.** Chaque composant indique **le mécanisme réel qui l'exécute** (hook, sous-agent, worktree, PR, test, fichier). Un composant sans mécanisme est marqué **« non réalisable aujourd'hui »**. Statuts : **EXISTE** (fichier qui le prouve), **À ADAPTER**, **À CRÉER**.

---

## 0. Résumé pour le président

1. **L'entreprise existe déjà en germe.** Le Maire, le Conseil, la Forge, les chefs de maison, les hooks d'état et la métropole 3D forment un circuit qui fonctionne (testé hier : un circuit simulé allume le bon siège). Le travail consiste à **l'industrialiser**, pas à le refaire.
2. **Un agent n'existe que pendant qu'il travaille.** Les 8 métiers sont des **rôles** : des définitions d'agents instanciées à la demande pour une mission, puis terminées. Personne n'est « en poste » à vide. C'est ce qui rend le principe « aucun agent ne prétend travailler » vérifiable, et le coût maîtrisable.
3. **Un registre des missions** (SQLite + journal append-only) devient la colonne vertébrale. Les agents s'y inscrivent, la 3D le lit, le président y approuve.
4. **L'exécution réelle** passe par Claude Code en mode non interactif. Chaque mission tourne dans un **worktree git isolé**, sur une **branche dédiée**, avec des **garde-fous exécutables** (hook `PreToolUse`) et pas seulement écrits.
5. **Le président garde la main** sur tout ce qui est irréversible ou extérieur : fusion, déploiement, migration, secret, dépense, envoi, création de projet.
6. **Projet pilote : REV-EM**, seul projet sur lequel cette session a aujourd'hui l'accès en écriture. LexNote reste en lecture seule tant que tu n'as pas autorisé l'accès. UPSA reste sur ton Mac.
7. **Coût : 0 € d'infrastructure.** Tout tourne en local (Python standard, SQLite, git). L'usage des modèles passe par ton abonnement Claude existant, avec des plafonds par mission et par jour, et un interrupteur d'arrêt.

---

## 1. Audit du village actuel

### 1.1 Ce qui fonctionne (réutilisable tel quel)

| Composant | Fichier | Rôle dans l'entreprise |
|---|---|---|
| Constitution et circuit Conseil → Maison → Forge → Journal | `CLAUDE.md` | Devient la **charte de la Direction générale** |
| Registre des bâtiments | `registre.json` | Reste la source de vérité des **sièges, services et chantiers** |
| 3 critiques | `.claude/agents/critique-*.md` | Deviennent le **Conseil de sélection** (réutilisés tels quels) |
| Forgeron + inspection | `.claude/agents/forgeron.md`, `forge/inspection.sh` | Deviennent le **Contrôle qualité** |
| 7 chefs de maison avec garde-fous | `.claude/agents/chef-*.md` | Deviennent les **directeurs de siège** |
| Architecte, `/nouvelle-maison` | `.claude/agents/architecte.md`, `.claude/commands/` | Deviennent la **création d'un projet** après décision du président |
| Hooks d'activité | `.claude/hooks/etat-ile.py`, `.claude/settings.json` | Base du **capteur d'événements** (écriture atomique et verrouillée, déjà testée en parallèle) |
| Serveur local | `serveur.py` | Base du **serveur du tableau de bord** |
| Métropole 3D | `village/ville.js` (870 lignes) | **Conservée.** Graphe routier, chemins entre bâtiments, sièges par projet, activité pilotée par fichier, qualité adaptative |
| Mémoire par maison | `maisons/<id>/` : `CLAUDE.md`, `journal.md`, `branches.md`, `etat-des-lieux.md`, dossier de reprise | Base de la **mémoire de projet** |
| Procès-verbaux, rapports | `conseil/proces-verbaux/`, `forge/rapports/` | Base de la **traçabilité des décisions** |

### 1.2 Ce qui bloque (à corriger avant toute autonomie)

| # | Constat vérifié | Conséquence | Correction |
|---|---|---|---|
| A1 | **Pas de `.claude/` à la racine du dépôt** : l'île vit dans `ile-des-agents/`. | Dans une session ouverte sur le dépôt (comme celle-ci), **ni les hooks ni les agents de l'île ne sont chargés**. Les critiques ont dû être simulés par des agents génériques. | Lancer Claude Code depuis `ile-des-agents/`, ou faire de l'île la racine d'un dépôt dédié (recommandé, étape 1). |
| A2 | `etat-de-l-ile.json` n'a **qu'un champ `maison`** et une seule étape. | Impossible de représenter deux missions en parallèle. | Registre des missions + projection `etat.json` v2 (§4). |
| A3 | Le sujet d'une mission est **saisi à la main** (`etat-ile.py sujet`) ; les hooks ne connaissent que le nom de l'agent. | Traçabilité partielle. | La mission est créée **avant** l'agent ; l'agent reçoit son identifiant de mission (§5). |
| A4 | Le hook `Stop` marque « terminé » dès qu'aucun sous-agent n'est actif. | Une mission longue en plusieurs tours apparaît terminée trop tôt. | L'état d'une mission ne dépend plus du hook `Stop`, seulement du registre. |
| A5 | Les garde-fous des chefs (« jamais sur `main` ») sont **du texte**. | Rien n'empêche réellement un `git push origin main`. | Hook `PreToolUse` bloquant + règles de permission refusées (§9). |
| A6 | Les chefs ont `Write, Edit, Bash` mais **le code des projets n'est pas dans l'île**. | Ils ne peuvent travailler que sur la documentation. | Connecteurs + worktrees (§8). |
| A7 | `architecte.md` impose « rayon ≤ 13 » : règle de l'ancien village. | Une nouvelle maison serait mal placée dans la métropole. | Mettre à jour la règle (quartier des entreprises, positions libres). |
| A8 | Aucun budget, aucun compteur d'usage, aucun arrêt d'urgence. | Coût non maîtrisé dès qu'on automatise. | Budget + fichier `operations/STOP` (§9.4). |
| A9 | La 3D affiche un seul courrier pour une seule mission. | Pas de vue d'équipe. | Rendu piloté par la liste des exécutions actives (§12). |

### 1.3 Projets : vérification du 6 novembre 2026

Vérifié par `list_repos`, `list_computer_folders`, `git ls-remote` et inspection des clones :

| Projet | Où il existe vraiment | Accès réel depuis cette session | Preuve |
|---|---|---|---|
| **Île des Agents** (`simulation-questionnaire`) | GitHub, branche `claude/bold-noether-l93mmy` | **Écriture** | 5 branches distantes, poussée réussie aujourd'hui |
| **REV-EM** | GitHub `Antsvfr/REV-EM` | **Écriture attachée** à la session ; clone `/home/user/rev-em` sur la PR #26 (`ffd1f95`) | 8 branches ; tests rejoués : 50/55 fichiers OK |
| **LexNote** | GitHub `Antsvfr/LexNote` | **Lecture seule.** Ton compte GitHub peut écrire (`can_push: true`), mais le rattachement en écriture a été **refusé par le contrôle d'autorisation de la session**. | 15 branches ; clone de `main` (`981d9aa`) |
| **UPSA Sales Pilot** | **Uniquement sur ton Mac**, sans git | **Aucun** (dossier de documentation seulement) | Aucun dossier d'ordinateur connecté (`list_computer_folders` vide) |
| **EM'ERGENCY** et ses outils | **Introuvable** : aucun dépôt, aucun dossier | Aucun | La maison `bde-emergency` n'a que sa documentation |
| **Cuvée Campus, Vétotri, École** | **Introuvables** hors de l'île | Aucun | Maisons avec documentation seulement |

Il n'y a **aucun autre dépôt** visible sur ton compte.

---

## 2. Organigramme

```
                         ┌──────────────────────────┐
                         │   PRÉSIDENT — Anton      │  Résidence présidentielle
                         │   approuve · arbitre     │  (tableau de bord)
                         └────────────┬─────────────┘
                                      │ demandes · approbations
                         ┌────────────┴─────────────┐
                         │   DIRECTION GÉNÉRALE     │  = le Maire (session principale)
                         │   planifie · répartit    │  + orchestrateur `dg.py`
                         └─┬────────┬────────┬────┬─┘
        ┌──────────────────┘        │        │    └──────────────────────┐
┌───────┴────────┐      ┌───────────┴───┐ ┌──┴────────────┐   ┌──────────┴──────────┐
│ CONSEIL DE     │      │ CONTRÔLE      │ │ SÉCURITÉ      │   │ INNOVATION &        │
│ SÉLECTION      │      │ QUALITÉ       │ │ (transverse)  │   │ BUSINESS            │
│ clarté·exigence│      │ = la Forge    │ │ resp. sécurité│   │ veille · analyse ·  │
│ ·stratégie     │      │ testeurs QA   │ │               │   │ business case       │
└────────────────┘      └───────────────┘ └───────────────┘   └─────────────────────┘
                                      │
          ┌──────────────┬────────────┼─────────────┬──────────────┐
   ┌──────┴─────┐ ┌──────┴─────┐ ┌────┴──────┐ ┌────┴──────┐ ┌─────┴──────┐
   │ SIÈGE      │ │ SIÈGE      │ │ SIÈGE     │ │ SIÈGE     │ │ SIÈGES     │
   │ REV-EM     │ │ LexNote    │ │ UPSA      │ │ EM'ERGENCY│ │ Cuvée,     │
   │ (pilote)   │ │ (lecture)  │ │ (Mac)     │ │ (docs)    │ │ Vétotri,   │
   └──────┬─────┘ └────────────┘ └───────────┘ └───────────┘ │ École      │
          │                                                   └────────────┘
   Directeur de siège (chef-<id>)
     ├── Architecte logiciel
     ├── Développeur(s)        ← un par mission, dans son worktree
     ├── Designer UX/UI
     ├── Analyste
     ├── Testeur QA            ← rattaché fonctionnellement au Contrôle qualité
     └── Critique de projet    ← le Conseil, avec le contexte du siège
```

**Correspondance avec l'existant :** Président = Anton. DG = le Maire. Conseil de sélection = le Conseil. Contrôle qualité = la Forge. Directeurs de siège = `chef-*`. Création de projet = l'Architecte.

**Principe d'économie.** Un siège n'a **pas** d'équipe permanente. Le directeur de siège compose, pour chaque mission, l'équipe minimale nécessaire. Une correction de bug, par exemple, mobilise un développeur, un testeur QA et un critique, et rien de plus.

---

## 3. Métiers

Chaque métier est un fichier `.claude/agents/<role>.md` (**mécanisme : sous-agent Claude Code**) avec des outils limités. Les niveaux de permission N0 à N3 sont définis au §9. Le « niveau de modèle » est une indication de coût : *rapide* (le plus économique), *équilibré*, *puissant* (réservé aux décisions difficiles).

| Métier | Mission | Entrées → Sorties | Outils | Niv. | Modèle | Statut |
|---|---|---|---|---|---|---|
| **Président** (Anton) | Fixe les priorités, approuve le sensible, arbitre les égalités | Tableau de bord → approbations signées | Tableau de bord, chat | N3 | — | — |
| **Direction générale** | Transforme une demande en missions, choisit le siège, ordonnance, rend compte | Demande → missions dans le registre, compte rendu | Registre, sous-agents | N1 | puissant | À ADAPTER (le Maire) |
| **Directeur de siège** | Connaît les objectifs et les règles du projet ; découpe une mission en tâches avec critères d'acceptation ; compose l'équipe ; décide si le livrable est présentable | Mission → plan de tâches ; livrables → décision « proposer au président / refaire » | Lecture du projet, registre | N0 | équilibré | À ADAPTER (`chef-*`) |
| **Architecte logiciel** | Propose 1 à 3 solutions techniques chiffrées (fichiers touchés, risques, plan de test) | Tâche → `proposition-<n>.md` | Lecture, recherche | N0 | puissant | À CRÉER (≠ Architecte de l'île) |
| **Développeur** | Réalise la proposition retenue, dans son worktree uniquement, en petits commits | Proposition retenue → commits sur `ile/<mission>` | Lecture, écriture **dans le worktree**, Bash filtré | N1 | équilibré | À CRÉER |
| **Designer UX/UI** | Revoit écrans et parcours selon le standard du projet (ex. REV-EM : 5 langues, dark mode) ; produit maquette ou correctifs CSS | Tâche UI → recommandations ou commits | Lecture, écriture worktree, navigateur headless pour les captures | N1 | équilibré | À CRÉER |
| **Analyste** | Mesure avant d'agir : tests, couverture, TODO, dette, écarts entre la doc et le code | Projet → `rapport-analyse.md` chiffré | Lecture, Bash lecture seule | N0 | rapide | À CRÉER |
| **Critique** | Évalue les propositions selon la grille du §7, à l'aveugle et sans connaître l'auteur | Propositions → `evaluation.json` | Lecture | N0 | équilibré | EXISTE (Conseil) |
| **Testeur QA** | Exécute **réellement** les tests du projet et des tests de non-régression, avec des statuts honnêtes (PASS / FAIL / NOT TESTED + raison) | Branche → `rapport-tests.json` + journaux bruts | Bash (commandes de test autorisées) | N1 | rapide | À ADAPTER (Forge) |
| **Responsable sécurité** | Relit chaque diff : secrets, XSS, RLS, dépendances, règles absolues du projet ; dispose d'un **droit de veto** | Diff → `revue-securite.md` (OK / veto motivé) | Lecture, outils d'analyse statique s'ils existent | N0 | équilibré | À CRÉER |
| **Contrôle qualité** | Inspection finale : structure, tests rejoués, journal à jour, rien d'oublié | Mission → rapport Forge | Lecture, Bash | N1 | rapide | EXISTE (Forgeron) |
| **Archiviste** | Met à jour la mémoire du projet après chaque mission : faits, décisions, état des lieux | Mission close → mémoire du siège | Écriture dans `maisons/<id>/` | N1 | rapide | À CRÉER |
| **Veilleur** (Innovation) | Repère des opportunités à partir de sources publiques citées | Thème → `signal-*.md` | Recherche web, lecture | N0 | rapide | À CRÉER |
| **Analyste business** (Innovation) | Transforme un signal en business case chiffré, sans inventer de chiffre | Signal → `opportunite-*.md` | Recherche web, lecture | N0 | équilibré | À CRÉER |

---

## 4. Architecture technique

```
 Anton ──► Tableau de bord (village/ + résidence) ◄── lit ── operations/etat.json  (projection)
              │ approuve (127.0.0.1 + jeton)                     ▲
              ▼                                                  │ recalculée
        serveur.py ──► operations/ile.db (SQLite) ◄────── dg.py (orchestrateur)
                         missions · tâches · exécutions          │ lance
                         propositions · évaluations              ▼
                         approbations · budget        claude -p … (mode non interactif)
                              ▲                        cwd = worktree de la mission
                              │ append-only            agent = rôle (.claude/agents)
                    operations/evenements.jsonl ◄───── hooks : SubagentStart/Stop,
                                                       PreToolUse (garde.py), PostToolUse
                                                              │
                                     worktrees/<projet>/<mission>  (branche ile/<id>)
                                     └─ connecteur : GitHub · dossier local · docs seuls
```

| Brique | Technologie | Mécanisme | Statut |
|---|---|---|---|
| **Registre des missions** | SQLite (`sqlite3` de Python, aucune dépendance) | Fichier `operations/ile.db` | À CRÉER |
| **Journal d'événements** | JSON Lines append-only, un événement par ligne, horodaté, avec `mission_id` et `run_id` | Hooks + orchestrateur | À ADAPTER (`etat-ile.py`) |
| **Projection pour la 3D** | `operations/etat.json`, recalculé à chaque événement, écrit de façon atomique | Hook / orchestrateur | À ADAPTER |
| **Orchestrateur** `dg.py` | Python standard ; boucle de file d'attente ; lance des processus | Processus local | À CRÉER |
| **Exécution d'un agent** | `claude -p "<consigne>"` dans le worktree, sortie JSON, nombre de tours plafonné, outils restreints | Claude Code non interactif | À CRÉER |
| **Isolation** | `git worktree add worktrees/<projet>/<mission> -b ile/<mission>-<slug>` | git | À CRÉER |
| **Garde-fous** | `garde.py` en hook `PreToolUse` + règles de refus dans `settings.json` | Hook bloquant (code de sortie 2) | À CRÉER |
| **Serveur du tableau de bord** | `serveur.py` étendu : `GET /api/etat`, `GET /api/missions`, `POST /api/approbation` (local uniquement, jeton) | HTTP standard | À ADAPTER |
| **Métropole 3D** | `village/ville.js` | Lit `etat.json` toutes les 3 s | À ADAPTER (§12) |
| **Interface en ligne de commande** `ile` | `ile mission creer/liste/voir`, `ile approuver <id>`, `ile stop` | Python | À CRÉER |

**Où ça tourne.**
- **Sur ton Mac** : c'est le mode principal, sans coût d'hébergement. Il est le seul à voir UPSA et tes dossiers locaux.
- **En session cloud Claude Code** (comme celle-ci) : pour les projets GitHub uniquement, à la demande ou en tâche planifiée.

Le même code sert les deux modes, car les chemins viennent du registre.

**Évolution possible (étape 8, si nécessaire).** Remplacer `claude -p` par le **Claude Agent SDK** pour un service permanent : contrôle fin des permissions par appel, sous-agents et hooks programmatiques. Cette évolution n'est à faire que si le mode non interactif atteint ses limites.

---

## 5. Moteur d'agents

1. **Création.** Une mission est créée (par toi, la DG ou l'Innovation) avec un identifiant `M-2026-11-06-001`, un siège, un objectif et des critères d'acceptation. Elle démarre au statut `proposee`.
2. **Planification.** La DG lance le directeur de siège, en lecture seule. Il produit le plan : tâches, rôles et ordre.
3. **Exécution d'un rôle.** `dg.py` ouvre une *exécution* (`run_id`), écrit `run.debut` dans le journal, puis lance :
   `claude -p` avec la consigne du rôle. La consigne contient le contexte du siège, les identifiants de mission et d'exécution, et le chemin du worktree. Le répertoire de travail est le worktree. Les limites sont un nombre de tours maximal et un temps maximal.
4. **Capteurs.** Les hooks émettent des événements réels pendant l'exécution, c'est-à-dire seulement quand un outil est vraiment utilisé :
   - `PostToolUse` sur `Edit` ou `Write` : l'agent est en développement ;
   - `Bash` sur une commande de test : il est en test ;
   - `Read`, `Grep` ou `Glob` : il est en analyse.
5. **Battement de cœur.** Une exécution sans événement depuis 120 s est marquée `inactive`. Après 15 min, elle est `expiree` : le processus est arrêté et la tâche revient dans la file.
6. **Fin.** L'exécution se termine par `run.fin`, avec un code de sortie, les fichiers produits et un résumé. Le directeur de siège décide de la suite.

**Communication entre agents : pas de messagerie libre.** Les agents communiquent par **artefacts déposés dans le dossier de la mission** (tableau noir) : `plan.md`, `proposition-1.md`, `evaluation-critique-clarte.json`, `rapport-tests.json`, `revue-securite.md`. Chaque dépôt est un événement du journal. C'est traçable, relisible, et ça évite les conversations coûteuses entre agents.

---

## 6. Système de tâches et cycle de production

**États d'une mission**

```
proposee ─► approuvee* ─► planifiee ─► conception ─► selection ─► realisation
   │            (*si coût > seuil ou siège sensible)                     │
   └─► rejetee                                                           ▼
                 abandonnee ◄──── refaire ◄──── verification (tests + sécurité + Forge)
                                                                         │ OK
                                       fusionnee ◄── PRÉSIDENT ◄── prete (PR brouillon)
```

**Cycle d'une mission type** (correction d'un défaut sur REV-EM) :

| Étape | Qui | Mécanisme réel | Artefact |
|---|---|---|---|
| 1. Cadrage | Directeur de siège | Sous-agent en lecture | `plan.md` + critères d'acceptation |
| 2. Mesure | Analyste | Lecture + tests existants | `rapport-analyse.md` (état avant) |
| 3. Conception | Architecte ×1 à 3 | Sous-agents en parallèle, lecture seule | `proposition-<n>.md` |
| 4. Sélection | 3 critiques | Sous-agents en parallèle, à l'aveugle | `evaluation-*.json` → score (§7) |
| 5. Réalisation | Développeur | Worktree `ile/<mission>`, commits | Diff |
| 6. Vérification | Testeur QA + Sécurité + Forge | Tests **réellement exécutés**, revue du diff, inspection | `rapport-tests.json`, `revue-securite.md` |
| 7. Décision | Directeur de siège | Lecture des rapports | « prête » ou « refaire » (2 essais au maximum, puis escalade) |
| 8. Publication | Orchestrateur (N2) | Push de la branche de travail + **PR en brouillon** | Lien de PR |
| 9. Fusion | **Président** | Tableau de bord → approbation → fusion (ou toi sur GitHub) | Approbation signée |
| 10. Mémoire | Archiviste | Mise à jour du siège | `journal.md`, `decisions/`, état des lieux |

**Parallélisme sans conflit.**
- **Une mission = un worktree = une branche** : deux développeurs ne touchent jamais le même répertoire de travail.
- **Verrous par zone** : le plan déclare les fichiers ou dossiers visés, et deux missions dont les zones se recouvrent ne tournent pas en même temps.
- **Limite par siège.** Pour REV-EM, elle est d'**une** mission de développement à la fois au départ, parce que `index.html` pèse 1,4 Mo et concentre presque tout le code. La limite globale est de N exécutions simultanées (réglable).
- **Chaînes de PR empilées (LexNote)** : jamais de rebase, des commits de fusion uniquement, et l'ordre de fusion est respecté (règle du projet).

---

## 7. Critique et sélection des propositions

**Grille objective** (chaque critère est noté de 0 à 5 par chaque critique ; les poids sont réglables par siège) :

| Critère | Poids | Mesure |
|---|---|---|
| Répond aux critères d'acceptation | 25 % | Liste cochée, point par point |
| Risque de régression | 20 % | Fichiers touchés, couverture de tests existante |
| Respect des règles du projet | 15 % | `CLAUDE.md` du siège (ex. REV-EM : `escapeHtml`, `lsGet`/`lsSet`, 5 langues) |
| Plan de test vérifiable | 15 % | Tests nommés, commandes exactes |
| Taille du changement | 10 % | Plus petit = mieux, à résultat égal |
| Coût d'exécution estimé | 10 % | Tours et temps estimés |
| Valeur pour le produit | 5 % | Lien avec les priorités du dossier du projet |

**Vetos (élimination directe, quel que soit le score) :** risque de perte de données, secret exposé, règle absolue du projet violée (ex. UPSA : lire des données réelles), travail sur `main`, fonction en double entre REV-EM et LexNote.

**Signaux automatiques ajoutés au score :** tests verts ou rouges, diff vide, motifs interdits détectés par recherche (`localStorage.` direct dans REV-EM, `innerHTML` non échappé…).

**Règle de décision.** On retient le score pondéré le plus élevé. Si l'écart avec la proposition suivante est inférieur à 5 %, ou si un critique met un veto contesté, la décision **remonte au président**. La décision est enregistrée en ADR dans `maisons/<id>/decisions/` avec les scores, les vetos et la raison du choix.

---

## 8. Connecteurs et plan de connexion

**Trois types de connecteurs**, une interface commune (`lire`, `branches`, `etat_git`, `tests`, `ouvrir_worktree`, `publier_branche`, `ouvrir_pr_brouillon`) :

| Type | Mécanisme | Pour |
|---|---|---|
| **GitHub** | `git` + outils GitHub (MCP) ; push **uniquement** sur `ile/*` ; PR en brouillon | REV-EM, LexNote, l'île |
| **Dossier local** | Chemin du Mac dans le registre + `permissions.additionalDirectories` ; ou dossier partagé par Remote Control vers une session cloud | UPSA, projets locaux |
| **Documentation seule** | `maisons/<id>/` uniquement | Projets introuvables |

Une panne de connecteur ne bloque que son siège : chaque connecteur s'exécute dans son propre processus, et une erreur passe la mission en `bloquee`, pas l'orchestrateur.

**Plan de connexion par projet**

| Projet | Connecteur | Niveau autorisé | Préalable | Contraintes du projet |
|---|---|---|---|---|
| **Île des Agents** | GitHub | N2 | Aucun | — |
| **REV-EM** (pilote) | GitHub | N2 (PR brouillon), N3 = toi | Aucun : écriture attachée | Pas de CI, tests `node tests/*` + serveur sur 9109 ; 1 mission de dev à la fois ; ne jamais réécrire `index.html` ; vérifier l'écart entre les deux dossiers de reprise sur les PR #24/#25/#26 avant toute fusion |
| **LexNote** | GitHub | N0 aujourd'hui | **Ton autorisation d'écriture** dans les réglages de session, ou travail sur le Mac | Chaîne #12→#10→#11→#13→#14 ; jamais de rebase ; budget 0 € ; portes de production jamais marquées PASS sans exécution |
| **UPSA Sales Pilot** | Dossier local (Mac) | N1 **local**, jamais N2 | `git init` **local** sur ton Mac (sans dépôt distant), avec un `.gitignore` excluant `data/` | Pas de push, pas de cloud, **lecture interdite des données réelles** (règle 6), jamais `db:reset` sans accord |
| **EM'ERGENCY** | Documentation seule | N0 | Que tu indiques où sont ses outils | — |
| **Cuvée Campus, Vétotri, École** | Documentation seule | N0 | Que tu indiques s'ils ont du code | — |

---

## 9. Permissions et sécurité

### 9.1 Niveaux

| Niveau | Autorisé | Qui |
|---|---|---|
| **N0 lecture** | Lire le projet et la mémoire du siège ; lancer des commandes en lecture | Tous les rôles |
| **N1 écriture isolée** | Écrire **dans le worktree de la mission**, commits locaux, lancer les tests | Développeur, Designer, Testeur, Archiviste (mémoire) |
| **N2 publication** | Pousser une branche `ile/*`, ouvrir une PR **en brouillon** | Orchestrateur uniquement, après vérification verte |
| **N3 présidentiel** | Fusionner, déployer, migrer une base, toucher aux secrets, dépenser, envoyer à l'extérieur, créer un dépôt ou une maison, supprimer | **Toi seul**, une approbation par action |

### 9.2 Application réelle (pas seulement écrite)

- **`garde.py` (hook `PreToolUse`)** refuse, avec un code de sortie 2 :
  - `git push` vers `main`/`master`, `--force`, `git rebase` sur une branche empilée ;
  - `rm -rf` hors du worktree ;
  - lecture de `.env*` et `supabase-config.js` ;
  - `supabase db push`, `vercel --prod`, `npm publish` ;
  - `curl`/`wget` vers des hôtes non listés ;
  - toute écriture hors du worktree de la mission ;
  - pour UPSA, toute lecture de `data/`.
- **Règles de refus** dans `.claude/settings.json` (double sécurité).
- **Protection de branche GitHub** sur `main` : **c'est toi qui l'actives** sur chaque dépôt. C'est la seule protection qui tient même si tout le reste échoue.
- **File d'approbations.** Chaque demande N3 crée une ligne (quoi, pourquoi, diff, risques) et ne s'exécute qu'après ton approbation : bouton du tableau de bord, servi sur `127.0.0.1` avec un jeton, ou `ile approuver <id>`.

### 9.3 Secrets

Aucun agent ne lit ni ne reçoit de secret. Les commandes qui en ont besoin (déploiement, migration) sont des opérations N3 que **tu** exécutes.

### 9.4 Maîtrise du coût

- **Plafonds :** nombre de tours par exécution, nombre d'exécutions par mission, nombre de missions par jour, avec un compteur dans `ile.db`.
- **Niveau de modèle par rôle** (§3) : le niveau *puissant* est réservé à l'architecture et aux arbitrages.
- **Interrupteur d'arrêt :** si le fichier `operations/STOP` existe, aucune exécution ne démarre et les exécutions en cours s'arrêtent.
- **Pas d'appel facturé à l'usage** (API payante, hébergement, service) sans approbation N3. Les plafonds d'usage de ton abonnement restent la limite naturelle. Je n'ai pas de chiffre de coût fiable à te donner à l'avance : le tableau de bord **mesurera** l'usage réel par mission dès l'étape 1.

---

## 10. Mémoire et stockage

| Niveau | Emplacement | Contenu | Qui écrit |
|---|---|---|---|
| **Entreprise** | `registre.json`, `journal-de-l-ile.md`, `operations/ile.db`, `operations/evenements.jsonl` | Sièges, missions, historique complet | DG, orchestrateur, hooks |
| **Siège** (isolé) | `maisons/<id>/` : `CLAUDE.md` (règles), `etat-des-lieux.md`, `branches.md`, `journal.md`, `decisions/` (ADR), `memoire/faits.md` (chaque fait avec sa source et sa date) | Contexte propre au projet | Archiviste, directeur de siège |
| **Mission** | `maisons/<id>/missions/<mission>/` | Plan, propositions, évaluations, rapports de tests, compte rendu | Rôles de la mission |
| **Exécution** | `operations/runs/<run_id>.jsonl` | Sortie brute de l'agent | Orchestrateur |

**Isolation du contexte.** Une exécution reçoit uniquement le `CLAUDE.md` et la mémoire **de son siège**, plus le worktree de sa mission. Elle n'a aucun accès en lecture aux autres sièges (règle de `garde.py`).

**Compaction.** Après N missions, l'Archiviste résume le journal du siège et l'archive. Les ADR ne sont jamais compactées.

**Volume prévu.** Quelques Mo par mois (texte et JSON). Les journaux bruts d'exécution sont purgés au-delà de 90 jours, mais le résumé est conservé.

---

## 11. Département Innovation & Business

**Mission :** proposer de nouveaux projets à valeur, **sans dépenser, sans contacter personne, sans rien créer** sans ton accord.

1. **Veille** (Veilleur) : thèmes que tu fixes, par exemple tes études, tes compétences, tes projets existants. Il produit des signaux avec **sources citées**.
2. **Fiche opportunité** (Analyste business) : problème, cible, solution, concurrence, synergies avec tes projets, effort, risques, et chiffres **sourcés ou marqués « estimation »**.
3. **Score** (grille dédiée) : marché 25 %, faisabilité avec tes moyens 25 %, synergie avec l'existant 20 %, coût 15 %, alignement avec tes objectifs 15 %.
4. **Conseil de sélection** : les 3 critiques relisent la fiche.
5. **Décision du président** : go / no-go / à creuser. Un go déclenche `/nouvelle-maison` (Architecte), et le projet apparaît comme **chantier** dans la métropole.

**Mécanisme :** sous-agents avec recherche web, lancés à la demande ou par une tâche planifiée hebdomadaire (optionnelle et plafonnée). **Stockage :** `innovation/signaux/`, `innovation/opportunites/`, `innovation/decisions/`.

---

## 12. Résidence présidentielle, tableau de bord et synchronisation 3D

**Résidence présidentielle** : un nouveau bâtiment `type: "residence"` dans `registre.json`, placé dans le quartier stratégique, avec un builder dédié dans `ville.js` (ajout d'une entrée dans `HQ`, le moteur ne change pas). Un clic ouvre le **tableau de bord** dans le carnet :

- **À approuver** (N3), avec diff, risques et bouton d'approbation ;
- **Prochaine action par siège**, calculée à partir des états des lieux (c'est le premier livrable, étape 0) ;
- **Missions en cours**, avec leur étape et les agents actifs ;
- **Tests** : derniers résultats par siège (PASS / FAIL / NOT TESTED) ;
- **Alertes** : test rouge, veto de sécurité, exécution expirée, budget proche du plafond ;
- **Usage** : exécutions et tours du jour par rapport au plafond, et l'interrupteur d'arrêt ;
- **Innovation** : opportunités en attente de décision.

**Synchronisation avec la 3D** (`etat.json` v2, projection du registre) :

| Ce qu'on voit | Source réelle |
|---|---|
| Un agent à pied ou en véhicule | Une exécution **active** (événement depuis moins de 120 s) |
| Son état : réflexion / développement / test / bloqué / terminé | Dernier type d'outil utilisé (§5), ou approbation en attente |
| Siège éclairé, faisceau | Au moins une exécution active pour ce siège |
| Réunion au Conseil | Au moins 2 critiques actifs sur la même mission |
| Alerte rouge sur un siège | Test échoué ou veto de sécurité non traité |
| Notification « terminé » | Événement `mission.prete` ou `mission.fusionnee` |
| Courrier sur la route | Passage de témoin entre rôles (artefact déposé) |

**Rétrocompatibilité :** tant que `etat.json` n'existe pas, le village continue de lire `etat-de-l-ile.json`. **Aucun agent n'est dessiné sans exécution active** : c'est le principe central, et il sera vérifié par un test automatique.

---

## 13. Roadmap priorisée

Chaque étape a un **critère de fin testable** et une **porte** : tu valides avant de passer à la suivante.

| Étape | Contenu | Critère de fin | Porte |
|---|---|---|---|
| **0. Immédiat** | Tableau de bord « prochaine action par siège » dans la Résidence (lecture seule : registre + états des lieux). Tes actions en attente : `git init` local d'UPSA sur le Mac, décision sur la PR #26 de REV-EM, autorisation d'écriture sur LexNote. | La page affiche une action vérifiable par siège | Toi |
| **1. Fondations** | Rendre l'île active à la racine (A1). Registre SQLite + journal JSONL + CLI `ile`. Hooks généralisés à N missions (A2–A4). `etat.json` v2 lu par la 3D. Mise à jour de l'Architecte (A7). | Deux missions en parallèle visibles correctement ; test « aucun agent sans exécution » au vert | Toi |
| **2. Garde-fous** | `garde.py` + règles de refus + file d'approbations + plafonds + `STOP`. | Batterie de commandes interdites **réellement bloquées** (test automatisé) | Toi |
| **3. Pilote REV-EM** | Orchestrateur `dg.py`, worktree, rôles Développeur / Testeur QA / Sécurité ; une mission réelle de petite taille jusqu'à la PR en brouillon. | **Une PR brouillon réelle** produite de bout en bout, tests réellement exécutés, approbation tracée | Toi (fusion) |
| **4. Sélection** | Architecte ×N + grille du §7 + ADR. | 3 missions décidées avec scores enregistrés | Toi |
| **5. Équipes** | Rôles Designer, Analyste, Archiviste ; verrous par zone ; mémoire et compaction ; ouverture à LexNote (si autorisé) et UPSA (local). | 2 sièges en parallèle sans conflit | Toi |
| **6. Innovation** | Veille, fiches, score, décision. | 3 fiches sourcées, 1 décision du président | Toi |
| **7. Métropole vivante** | Résidence 3D, avatars par exécution, réunions, alertes, notifications. | Chaque élément animé correspond à un événement réel (test) | Toi |
| **8. Option** | Passage au Claude Agent SDK si le mode non interactif atteint ses limites. | Mesure d'une limite réelle avant décision | Toi |

**Ce qui n'est pas réalisable aujourd'hui, et pourquoi :**
- **Travailler sur UPSA** : le code est seulement sur ton Mac, sans dossier connecté.
- **Modifier LexNote** : l'accès en écriture a été refusé dans cette session.
- **Les outils d'EM'ERGENCY** : introuvables.
- **Une autonomie 24 h/24 sans ordinateur allumé** : il faudrait des tâches planifiées cloud, qui ne couvrent que les projets GitHub et consomment ton quota d'usage.

---

## 14. Composants réutilisés : récapitulatif

**Réutilisés tels quels :**
- les 3 critiques et le Forgeron ;
- `forge/inspection.sh` ;
- le moteur 3D (`ville.js` : graphe routier, chemins, sièges, qualité adaptative) ;
- `serveur.py` ;
- les maisons et leurs dossiers de reprise ;
- les procès-verbaux.

**Adaptés :**
- `etat-ile.py`, qui devient le capteur d'événements multi-missions ;
- les `chef-*`, qui deviennent les directeurs de siège ;
- le Maire, qui devient la Direction générale ;
- l'Architecte, avec ses règles de placement ;
- le village, qui doit lire `etat.json` v2 ;
- `settings.json`, avec de nouveaux hooks et des règles de refus.

**Créés :**
- `operations/` (SQLite, journal, projection) ;
- `dg.py`, `garde.py` et le CLI `ile` ;
- 8 nouveaux rôles ;
- la Résidence et son tableau de bord ;
- le département `innovation/`.
