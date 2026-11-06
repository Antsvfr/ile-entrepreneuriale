# Branches de REV-EM

Relevé du 2026-11-06 (`git ls-remote`, SHA courts).

| Branche | SHA | Rôle d'après les dossiers |
|---|---|---|
| `main` | 763ad74 | **Seule branche publiée** (GitHub Pages) |
| `claude/lexnote-sso-launch` | b7773d5 | Branche de travail du dossier LexNote (PR #25, contient #24) |
| `claude/planning-lexnote-live-session` | 3e72c32 | PR #24 (brouillon) : « Prendre mes notes dans LexNote » depuis le planning |
| `claude/anaquizz-rebrand-restructure-ddinml` | ffd1f95 | PR #26 (ouverte, 5 commits devant `main` selon le dossier) : import fiable sans IA, correctifs d'import. **Identique au zip local.** |
| `claude/lexnote-link` | a1af8d5 | à qualifier |
| `claude/fix-connected-apps-ui` | 5993e65 | à qualifier |
| `claude/REV-EM-rebrand-restructure-ddinml` | 361bab9 | Ancienne branche publiée, ne l'est plus |
| `claude/reconcile-production-main` | 3553e95 | PR #23, fusionnée dans `main` |

## ⚠ Écart entre les deux dossiers de reprise
- Dossier LexNote : chaîne REV-EM `#24 → #25`, #25 sur `claude/lexnote-sso-launch`.
- Dossier REV-EM : PR #26 (rebrand), #24 (planning) ; ne mentionne pas #25.
Les SHA des deux branches existent bien, mais l'état et l'ordre réels des PR **doivent être vérifiés sur GitHub** avant toute fusion.
