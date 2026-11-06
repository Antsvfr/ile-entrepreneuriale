# Île entrepreneuriale

L'entreprise d'agents d'Anton : une île gouvernée par un Maire (Claude Code), un Conseil des critiques, une Forge, des
directeurs de projet, sous l'autorité d'un président dont les actes sont signés (Ed25519).

Migrée le 6 novembre 2026 depuis `Antsvfr/simulation-questionnaire` (dossier `ile-des-agents/`), corrections de sécurité
de l'étape 2 comprises. **Étape 2 : NON VALIDÉE** — voir `audit/rapports/2026-11-06-finalisation-etape-2.md`.

## Version web (lecture seule)
**https://antsvfr.github.io/ile-entrepreneuriale/** — métropole 3D, Résidence en consultation, vérification publique du
registre dans le navigateur. Les actes présidentiels se signent dans la Résidence locale (ci-dessous). Détails :
`docs/architecture/APPLICATION-WEB.md`. Mettre à jour la version web : `./ile publier`, puis commit et push.

## Ouvrir l'île
```bash
./ile
```
Puis http://localhost:7777/ (métropole), `/residence` (Résidence), `/batiment/<id>`. `./ile aide` pour le reste.
Python 3.9 ou plus récent, sans dépendance. Le premier lancement propose de créer l'identité présidentielle (`./ile president`).

## Architecture
| Dossier | Contenu |
|---|---|
| `presidence/` | identité et signatures présidentielles |
| `securite/` | garde, confinement des imports, arrêt d'urgence |
| `orchestrateur/` | registre des opérations (journal chaîné), capteurs des hooks |
| `residence/` | serveur local, Résidence, métropole 3D |
| `agents/` | définitions des agents et commandes (liens `.claude/agents`, `.claude/commands`) |
| `projets/` | une maison par projet |
| `audit/` | rapports, procès-verbaux, preuves, inspection, sauvegardes, migration |
| `docs/` | architecture et procédures |
| `tests/` | tests automatisés et scénarios d'attaque |

Constitution des agents : `CLAUDE.md`. Correspondance avec l'ancien dépôt : `audit/migration/correspondance.tsv`.

## Vérifier
```bash
python3 -I -S -m unittest discover -s tests
```
```bash
python3 -I -S orchestrateur/ile.py verifier
```
```bash
python3 -I -S audit/preuves.py
```
