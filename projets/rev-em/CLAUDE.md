# Maison REV-EM

**Dépôt :** `Antsvfr/REV-EM` (public ; anciens noms : *Anaquizz*, *Lyon Révision*) · **Publiée :** `main` via GitHub Pages (`https://antsvfr.github.io/REV-EM/`) · **Branche de travail citée :** `claude/lexnote-sso-launch`.
Plateforme de révision pour étudiants (EM Lyon) : matières, import de cours, quiz, flashcards, planning, assistant IA local, maths, comptes Supabase, sources connectées (Brightspace), liaison avec LexNote. Aussi application macOS (WebView).

Stack : JavaScript sans bundler ni `package.json`, un gros `index.html` (~20 800 lignes) + modules autonomes ; Supabase (migrations `000`–`009`, Edge Functions). Tests : scripts `node tests/*.test.{js,mjs}`, pas de CI.

## Où lire
- `dossier-projet.md` : dossier complet (carte d'`index.html` au §4.3, règles au §11).
- `gouvernance-claude-projet.md` : le `.claude/CLAUDE.md` du projet.
- `branches.md`, `etat-des-lieux.md`, `../lexnote/dossier-projet.md` (intégration).
- Copie de lecture de `main` : `/home/user/antsvfr/rev-em` (peut être absente).

## Règles propres au projet (non négociables)
- Pas de réécriture d'`index.html` ; pas de second système quand un premier existe.
- Pas de secret côté navigateur ; `escapeHtml()` sur tout texte injecté ; `lsGet`/`lsSet`, jamais `localStorage` direct.
- 5 langues pour tout nouveau texte.
- Statuts de test honnêtes : PASS / PASS MOCK / NOT TESTED.
- Ne jamais dire qu'un correctif est « en ligne » avant qu'il soit fusionné dans `main`.
- Pas de fonction en double avec LexNote.
- Chaîne empilée : commits de fusion uniquement, jamais de rebase.

## Règles communes à toutes les maisons-projets
- Jamais de travail direct sur `main`. Toute modification part d'une branche dédiée, en petits commits testés.
- Aucune fusion, aucun push vers `main`, aucun déploiement, aucune migration de production sans l'accord explicite d'Anton **dans le chat**.
- Aucun secret (mot de passe, `service_role`, clé HMAC, jeton) dans Git, un journal, une URL ou le chat. Aucun accès aux variables d'environnement de production.
- Jamais de preuve fabriquée : un test ou une porte n'est « PASS » que s'il a réellement été exécuté, et le dit (local, mock, réel).
- Chaque intervention est consignée dans `journal.md` de la maison.
