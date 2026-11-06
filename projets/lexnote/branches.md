# Branches de LexNote

Relevé du 2026-11-06 (`git ls-remote`, SHA courts). Les rôles viennent du dossier de reprise ; « à qualifier » = rôle non documenté, à vérifier sur GitHub.

## Chaîne de PR empilées (ordre de fusion obligatoire)
| Ordre | PR | Branche | SHA | Contenu |
|---|---|---|---|---|
| 1 | #12 | `claude/reconcile-main-production-schema` | 05afdba | Réconciliation du schéma de production |
| 2 | #10 | `claude/revem-course-launch` | 8602eb6 | Lancement d'un cours depuis REV-EM |
| 3 | #11 | `claude/generalize-lexnote-smart-transcript` | 042b3b5 | Produit généralisé (toutes filières), actions sur la transcription |
| 4 | #13 | `claude/persistent-revem-auth` | 6e305fb | Session persistante, connexion automatique REV-EM → LexNote |
| 5 | **#14** | `claude/production-readiness-observability` | **caf8b40** | **Branche de travail actuelle** : préparation à la production, correctif micro |

`caf8b40` correspond bien au dernier SHA du dossier de reprise.

## Production
- `main` — 981d9aa — plus ancienne que la chaîne ; les correctifs de #14 n'y sont pas tant que la chaîne n'est pas fusionnée et déployée.

## Autres branches (à qualifier)
| Branche | SHA |
|---|---|
| `claude/auth-user-workspaces` | 7ff94f7 (PR #3, déjà fusionnée dans `main` d'après l'historique) |
| `claude/intelligent-course-engine` | 808da65 |
| `claude/smart-learning-outputs` | 0f9f7e9 |
| `claude/study-artifacts-from-course` | 7930818 |
| `claude/lexnote-premium-ui` | e6ca91c |
| `claude/revem-integration-contract` | 41ed2e8 |
| `claude/schema-reconciliation` | 7ee2fb7 |
| `claude/blissful-pasteur-5ffow8` | e57d8c1 |
| `chatgpt/lexnote-multiuser` | 7979cea |
