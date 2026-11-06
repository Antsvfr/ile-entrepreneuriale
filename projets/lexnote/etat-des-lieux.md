# État des lieux — LexNote (2026-11-06)

**Vérifié aujourd'hui :** 15 branches distantes ; `main` = 981d9aa ; `caf8b40` = tête de `claude/production-readiness-observability` ; stack confirmée par `package.json` (React, Tiptap, Supabase, Vite ; scripts `dev build preview typecheck test test:e2e build:mock`) ; `supabase/` et `vercel.json` présents ; 283 fichiers, 1 marqueur « à faire » dans le code de `main`.

**Repris du dossier, non revérifié ici :** état des PR et de la CI, 15 PASS / 8 NOT_RUN / 0 FAIL sur les 23 portes (NOT READY), preuves liées au SHA `2cd7c88` invalidées par `caf8b40` (à rejouer).

**Reste à Anton (hors de portée d'ici) :** tester le correctif micro sur la prévisualisation, lancer les deux stacks Supabase locales, Firefox/WebKit, checklist PWA, sauvegarde de production en lecture seule, décider de la scission de `rollback-rehearsed` et du fournisseur IA.

**Limite de cette session :** copie en lecture seule de `main` (ancienne). Pour travailler sur la chaîne de PR, il faut attacher le dépôt en écriture ou travailler sur le Mac.
