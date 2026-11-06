# Maison LexNote

**Dépôt :** `Antsvfr/LexNote` (public) · **Branche de travail :** `claude/production-readiness-observability` (PR #14) · **Production :** `main`, plus ancienne.
Moteur de capture et de compréhension du cours : notes riches, transcription du professeur, documents, consolidation. Doit rester excellent **sans IA**. Complémentaire de REV-EM (maison `rev-em`) : **jamais de fonction en double** entre les deux.

Stack : React + TypeScript + Vite, PWA, IndexedDB local-first, Supabase (Auth, Postgres RLS, Edge Functions Deno), Vercel. Tests : Vitest, Playwright.

## Où lire
- `dossier-projet.md` : dossier de reprise du 6 nov. 2026 (LexNote + REV-EM).
- `branches.md` : toutes les branches, la chaîne de PR et l'ordre de fusion.
- `etat-des-lieux.md` : ce qui est vérifié, ce qui ne l'est pas.
- Le code reste la source de vérité : vérifier SHA, PR et CI sur GitHub avant d'agir. Copie de lecture : `/home/user/antsvfr/lexnote` (peut être absente).

## Priorités (dans l'ordre)
Fiabilité, sécurité, **conservation des données (une perte silencieuse de notes est un bug critique)**, fluidité REV-EM ⇄ LexNote, performance, expérience, nouvelles fonctions.

## Règles propres au projet
- Chaîne de PR empilées, en brouillon : fusion dans l'ordre `#12 → #10 → #11 → #13 → #14`, par commits de fusion uniquement, **jamais de rebase de la chaîne**.
- Budget **0 €** : pas de Supabase Branching, pas de nouveau projet payant, pas d'appel IA payant.
- Ne modifier ni les données ni les secrets de production.
- Portes de mise en production (`release/gates.json`) : ne jamais marquer PASS sans exécution réelle ; une validation locale n'est pas une validation cloud.
- Pas encore commencé, volontairement : cours intelligent complet, RAG global, recherche universelle, moteur de révision adaptatif, tableau de bord V2, fonctions sociales, collaboration.

## Règles communes à toutes les maisons-projets
- Jamais de travail direct sur `main`. Toute modification part d'une branche dédiée, en petits commits testés.
- Aucune fusion, aucun push vers `main`, aucun déploiement, aucune migration de production sans l'accord explicite d'Anton **dans le chat**.
- Aucun secret (mot de passe, `service_role`, clé HMAC, jeton) dans Git, un journal, une URL ou le chat. Aucun accès aux variables d'environnement de production.
- Jamais de preuve fabriquée : un test ou une porte n'est « PASS » que s'il a réellement été exécuté, et le dit (local, mock, réel).
- Chaque intervention est consignée dans `journal.md` de la maison.
