# Note de synthèse — état des lieux REV-EM (2026-11-06)

- Vérifié le 06/11 : 8 branches distantes ; `main` = 763ad74 (08/10/2026) ; la copie de `main` compte 228 fichiers et 2 marqueurs « à faire » ; `.claude/CLAUDE.md` et les skills sont présents.
- Le zip du code source correspond à la tête de la PR #26 (`ffd1f95`, 27/10/2026), à une différence près sur 243 fichiers (pas de `vendor/`, plus le dossier de reprise) : c'est du travail en attente de fusion, pas l'état publié, et il n'y a rien à importer.
- Points repris des dossiers sans nouvelle vérification : PR en attente (#24, #26, peut-être #25), cache `rev-em-v17`, tests, absence de CI.
- Limite : la session ne disposait que d'une copie en lecture seule de `main` ; il faut un accès en écriture au dépôt pour travailler sur une branche.
- Tests du 06/11 sur la PR #26 : 55 fichiers, dont 50 passent et 5 non.
- `import-center-ui` : 1 échec sur 142 vérifications (délai dépassé au scénario 8), identique sur `main`, donc pas une régression ; la cause n'est pas établie.
- `account-sync` échoue en parallèle mais passe seul : faux échec.
- 4 tests NOT TESTED faute de dépendances (`pg`, PostgreSQL, SDK Supabase) : `oauth-integration`, `user-data`, `security-audit`, `real-sdk-sync`.
