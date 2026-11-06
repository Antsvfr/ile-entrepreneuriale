# Addendum — étapes 0 et 1 réalisées (6 novembre 2026)

`ENTREPRISE-IA.md` est un artefact déposé au registre (E-000038) : il reste tel quel. Cet addendum consigne ce qui a été construit et les écarts avec le plan.

## Construit
| Brique | Fichier | Statut |
|---|---|---|
| Registre des opérations (journal chaîné SHA-256, projections, CLI) | `orchestrateur/ile.py` | EXISTE |
| Tests (17) et script de preuves (15 critères) | `tests/`, `audit/preuves.py` | EXISTE |
| Capteurs : agents identifiés (hooks Subagent*), briefing du DG (SessionStart) | `orchestrateur/hooks/etat-ile.py`, `ile.py capteur` | EXISTE |
| Île active à la racine du dépôt | `../CLAUDE.md`, `../.claude/` | EXISTE (vérifié par une vraie session `claude -p`) |
| API de la Résidence, écritures protégées | `residence/serveur.py` | EXISTE |
| Résidence présidentielle (supervision, décisions, priorités, instructions, missions, journal) | `residence/village/residence.html` | EXISTE |
| Îlot présidentiel et bâtiment 3D ; métropole lisant l'état v2 | `residence/village/ville.js` | EXISTE |
| Autonomie des directeurs : `/revue` ; classement du DG | `.claude/commands/revue.md`, `ile.py classer` | EXISTE |
| Emplacement Innovation & Business | `projets/innovation/`, registre (chantier) | PRÉVU (étape 6) |

## Écarts avec le plan
- **Pas de SQLite.** Le journal JSONL suffit à ces volumes et reste la seule source ; les projections sont recalculées en mémoire. SQLite reviendra comme index si le volume l'exige (avis de la Critique Stratège).
- **Instructions au DG :** inscrites et présentées au DG à chaque début de session ; elles ne déclenchent aucune exécution automatique avant l'étape 3 (`dg.py`). La Résidence affiche leur vrai statut (reçue / lue / traitée).
- **Activation à la racine sans déménagement** du dépôt : créer un dépôt dédié est une décision du président (N3).
- **Agents de démarrage :** les trois premières revues ont été lancées par le Maire depuis une session ouverte avant l'activation des hooks ; leurs exécutions R-0001 à R-0003 ont donc été ouvertes par le Maire (`run debut`), et chaque inscription des directeurs est confirmée par ces exécutions (`verifie: run`). Dans une nouvelle session, les hooks le font automatiquement (critère C1.4).

## Limites connues
- Le journal est versionné dans git : deux machines qui écrivent en parallèle produiraient deux chaînes à réconcilier. À traiter avant d'utiliser l'île à la fois sur le Mac et dans le cloud (étape 2 ou 5).
- L'identité « déclarée » (`--auteur` sans exécution) n'est pas vérifiée : elle est affichée comme telle.
- Une réécriture complète et cohérente du journal n'est détectable qu'en comparant l'empreinte finale à une empreinte publiée (commit git, Résidence).
