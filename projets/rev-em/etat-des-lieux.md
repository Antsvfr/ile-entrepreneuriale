# État des lieux — REV-EM (2026-11-06)

**Vérifié aujourd'hui :** 8 branches distantes ; `main` = 763ad74 (08/10/2026) ; `b7773d5` = tête de `claude/lexnote-sso-launch` ; copie de `main` : 228 fichiers, 2 marqueurs « à faire » ; `.claude/CLAUDE.md` et skills présents.

**Le zip du code source = la tête de la PR #26** (`claude/anaquizz-rebrand-restructure-ddinml`, commit `ffd1f95` du 27/10/2026). Comparé fichier par fichier aux 7 branches distantes : 1 seule différence sur 243 fichiers (le zip n'a pas le dossier `vendor/` ; il a en plus ton dossier de reprise). C'est donc le travail de la PR #26 en attente de fusion, **pas** l'état publié (`main` en diffère de ~20 fichiers). Rien n'est à importer : la branche existe sur GitHub.

**Repris des dossiers, non revérifié ici :** PR en attente (#24, #26, et #25 selon l'autre dossier), cache `rev-em-v17`, tests, absence de CI.

**Limite de cette session :** copie en lecture seule de `main`. Pour travailler sur une branche, il faut attacher le dépôt en écriture.

## Tests exécutés le 2026-11-06 sur la branche de la PR #26 (`ffd1f95`)

Environnement : Node 22, Playwright/Chromium du conteneur, dépôt servi sur `http://localhost:9109`, `pdfjs-dist@4.0.379` installé hors dépôt (`node_modules/` est ignoré par git). Aucun fichier du projet modifié.

- **55 fichiers de test** : 50 passent, 5 non.
- **`import-center-ui`** : 141 vérifications OK, **1 échec** (scénario 8, « Remplacer le fichier », délai de 15 s dépassé). **Même échec, à l'identique, sur `main` (`763ad74`)** : ce n'est donc pas une régression de la PR #26. Cause non établie (délai, possiblement lié au rendu logiciel de cet environnement).
- **`account-sync`** : a échoué lors d'un passage en parallèle (navigateur fermé), **passe seul** (exit 0). Faux échec dû à la parallélisation.
- **NON EXÉCUTÉS faute de dépendance** : `oauth-integration`, `user-data` (module `pg` manquant), `security-audit` (PostgreSQL absent), `real-sdk-sync` (SDK Supabase et `pg` absents ; le test se déclare lui-même « NOT TESTED »). Statut : **NOT TESTED**, pas PASS.
