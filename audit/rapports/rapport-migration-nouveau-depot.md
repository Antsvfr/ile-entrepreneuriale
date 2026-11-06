# Rapport de migration — `simulation-questionnaire` → `ile-entrepreneuriale` (6 novembre 2026)

Mission présidentielle : « migration vers le nouveau dépôt `ile-entrepreneuriale` », exécutée en local (aucun commit,
aucun push pendant la migration ; la publication a fait l'objet d'une mission distincte, voir
`audit/rapports/rapport-publication-officielle-github.md`). Aucune phrase secrète, clé privée ni donnée
d'authentification ne figure dans ce rapport.

**Statut final : MIGRATION LOCALE TERMINÉE** — avec une réserve : le dossier historique du Mac
(`~/Developer/simulation-questionnaire`) n'était pas accessible depuis le conteneur où la migration a eu lieu (aucun
ordinateur rattaché) ; voir §10.

## 1. Architecture source et architecture cible

Source : dépôt `Antsvfr/simulation-questionnaire`, branche `claude/bold-noether-l93mmy`, commit `a5c4d72`, île dans
`ile-des-agents/`, plus les modifications de sécurité de l'étape 2 **non commitées** (13 fichiers modifiés, 3 nouveaux).

| Ancien emplacement (`ile-des-agents/…`) | Nouvel emplacement | Fichiers |
|---|---|---|
| `operations/president.py`, `signature.py` | `presidence/` | 2 |
| `operations/garde.py`, `confinement.py` | `securite/` | 2 |
| `operations/ile.py`, `operations/journal.jsonl`, `.claude/hooks/etat-ile.py`, `etat-de-l-ile.json` | `orchestrateur/` (`ile.py`, `registre/journal.jsonl`, `hooks/etat-ile.py`, `etat-de-l-ile.json`) | 4 |
| `serveur.py`, `village/` | `residence/` (`serveur.py`, `village/`) | 5 |
| `.claude/agents/`, `.claude/commands/` | `agents/definitions/`, `agents/commandes/` (liens `.claude/agents`, `.claude/commands`) | 16 |
| `maisons/`, `innovation/` | `projets/`, `projets/innovation/` | 58 |
| `forge/rapports/`, `forge/inspection.sh`, `conseil/`, `journal-de-l-ile.md`, `operations/preuves.py` | `audit/` | 15 |
| `architecture/`, `README.md` (île et racine) | `docs/` | 5 |
| `operations/tests/` | `tests/` | 6 |
| `CLAUDE.md`, `registre.json`, `ile`, `Ouvrir l'île.command`, `.claude/settings.json` | racine | 5 |

Correspondance fichier par fichier, avec l'empreinte SHA-256 de la source et de la copie : `audit/migration/correspondance.tsv`.
Script de migration (lecture seule sur la source, testé à blanc avant la copie) : `audit/migration/migrer.py`.

## 2. Éléments migrés
118 fichiers (121 suivis + 3 non suivis dans l'ancien dépôt, moins les fusions). 0 fichier sans correspondance
(le script s'arrête sinon). Après migration : 83 fichiers identiques octet pour octet à leur source, 35 adaptés
(chemins uniquement, liste : `audit/migration/fichiers-adaptes.txt`), 0 manquant.

## 3. Éléments exclus et justification (`audit/migration/exclusions.tsv`)
| Élément | Motif |
|---|---|
| `CLAUDE.md` (racine), `ile-des-agents/.claude/settings.json`, les deux `.gitignore` | fusionnés : la racine du dépôt est désormais l'île (une constitution, un jeu de hooks, un `.gitignore`) |
| liens `.claude/agents`, `.claude/commands` | recréés vers `agents/definitions` et `agents/commandes` |
| `operations/etat.json`, `serveur.log`, `.verrou`, `etat-de-l-ile.json.lock`, `__pycache__/` | fichiers d'exécution ignorés par git, recalculés ou propres à la machine |
| `audit/sauvegardes/2026-11-06/depot-complet.bundle` | copié localement mais **non publié** : copie complète de l'ancien dépôt, qui reste en ligne comme référence historique |

## 4. Modifications non commitées récupérées
Toutes : `confinement.py`, `test_confinement.py`, le rapport `2026-11-06-finalisation-etape-2.md`, et les 13 fichiers
modifiés (garde, ile, president, serveur, etat-ile, preuves, settings ×2, lanceur, inspection, CLAUDE.md, ETAPES-2,
rapport d'inspection). Trace exacte conservée : `audit/sauvegardes/2026-11-06/modifications-non-commitees.patch`
(identique au `git diff` de l'ancien dépôt, vérifié par la Forge), avec la sauvegarde du Forgeron
(`modifications-forgeron.patch`, `garde.py.forgeron.txt`, `garde.py.commit-a5c4d72.txt`).

## 5. Corrections de sécurité
Présentes et rejouées après déplacement : confinement des imports (`python3 -I -S`, chemin d'import réduit à la
bibliothèque standard, modules de l'île chargés par chemin exact depuis la source), garde à échec fermé
(`/usr/bin/python3 -I -S … || exit 2`, `sys.excepthook`), STOP réel + `ILE_OPS`, protections des écritures sensibles
(garde-fous nommés, `DOSSIERS_PRIVILEGIES`, copies/extractions/git vers les dossiers de garde-fous, `.git/config`).
Chemins des garde-fous transposés : `securite/`, `presidence/`, `orchestrateur/ile.py`, `orchestrateur/hooks/`,
`residence/serveur.py`, `audit/preuves.py`, `tests/`, lanceurs.

Renforcement lié à la migration : `ile.py verifier` signale désormais un artefact gelé **introuvable** (avant : ignoré
en silence) et vérifie **chaque** emplacement possible d'un artefact (ancien et nouveau chemin) ; correctif du constat
D1 de l'inspection (un leurre intact à l'ancien chemin masquait une version falsifiée au nouveau).

**L'étape 2 reste NON VALIDÉE.** Contournements toujours documentés (`docs/architecture/ETAPES-2.md`,
`audit/rapports/2026-11-06-finalisation-etape-2.md`, `audit/preuves-brutes/`) : `env cp` et `find -exec cp`,
git avec `--git-dir`/`--work-tree`, `curl -o` et `patch`, `git push --all` et la configuration `mirror`.

## 6. Tests
| Vérification | Résultat |
|---|---|
| `python3 -I -S -m unittest discover -s tests` | 63/63 OK sous Python 3.13.18 et sous Python 3.9.25 (62 migrés + 1 test du correctif D1) |
| `python3 -I -S orchestrateur/ile.py verifier` | journal intègre, 53 événements, dernière empreinte `1c31913324d5a073…` (identique à l'ancien dépôt) |
| `python3 -I -S audit/preuves.py --claude` | 23 PASS · 1 PARTIEL (C3.2 : chargement launchd non testable sans Mac) · 0 FAIL · 0 NOT TESTED (sorties brutes : `audit/preuves-brutes/2026-11-06-publication/`) |
| `bash audit/inspection.sh` (sur une copie : le mode complet écrit un rapport) | 45 éléments vérifiés, 0 erreur, 0 avertissement |
| Test 3D `tests/village_3d.js` | instable **avant comme après** la migration (ancien dépôt : 2 réussites sur 3 ; nouveau : 2 sur 3) — problème préexistant de délai fixe sous rendu logiciel, pas une régression ; corrigé (attente de l'état attendu, critère inchangé) : 5/5 |
| Adresses servies | `/` et `/residence` redirigent ; `/village/` servie (alias de `residence/village/`) ; journal brut, `securite/`, `presidence/`, code Python, `tests/`, journaux du serveur : 404 |
| Syntaxe Python 3.9 | tous les fichiers Python analysés avec l'interpréteur 3.9 : valides |

## 7. Secrets
Recherche par motifs (clés privées, jetons GitHub/OpenAI/AWS/Slack, JWT, mots de passe) dans l'arbre et dans
**tout l'historique** de l'ancien dépôt : 0 résultat. Seule occurrence : le mot `service_role` dans des consignes
(« ne jamais exposer… »), sans valeur. Aucun `.env`, `.pem`, `acces.json`, `STOP`. Aucune adresse e-mail ni numéro de
téléphone dans les fichiers publiés. `.gitignore` : règles Python, secrets, fichiers d'exécution de l'île.

## 8. Intégrité de l'ancien dépôt
Sauvegarde vérifiable avant toute copie : `/tmp/claude-0/sauvegarde-migration-20261106-115457/` (bundle git vérifié,
patch, archive de l'arbre, copie de `.git`, empreinte de chaque fichier) — dossier temporaire du conteneur ; les pièces
textuelles sont conservées dans `audit/sauvegardes/2026-11-06/`. Après migration : 147/147 empreintes identiques,
aucun fichier ajouté ni retiré, `git status` identique, HEAD `a5c4d72`, remote inchangé. L'ancien dépôt n'a jamais été
modifié.

## 9. Configuration Git locale (au terme de la migration)
`/home/user/ile-entrepreneuriale`, branche `main`, remote `origin` = `https://github.com/Antsvfr/ile-entrepreneuriale.git`
(le dépôt distant était vide), aucun commit.

## 10. Réserves et opérations restant à autoriser
- **Mac non examiné.** Si des événements ont été ajoutés au journal sur le Mac (identité présidentielle, missions…),
  ils ne sont pas dans cette migration. Contrôle : sur le Mac, `python3 -I -S operations/ile.py verifier` dans l'ancien
  dossier ; si la dernière empreinte est `1c31913324d5a073…` et le nombre d'événements 53, il n'y a rien à rapprocher.
- Commit et publication : autorisés ensuite par la mission « publication officielle ».
- Restent du ressort du président : créer son identité (`./ile president`), la protection de branche GitHub sur `main`,
  la séparation des privilèges (`docs/architecture/SEPARATION-DES-PRIVILEGES.md`).

## 11. Inspection indépendante (Forge)
Premier passage (lecture seule, copies dans /tmp) : complétude PASS, corrections de sécurité PASS, rejeu du garde PASS
(dont 13 modules standard piégés et de faux `president.py`/`signature.py`/`ile.py` : aucun exécuté), tests PASS,
secrets PARTIEL (décision sur le bundle), ancien dépôt intact PASS, autonomie PARTIEL (textes périmés). Défauts D1
(moyen) à D6 (faibles) : corrigés ensuite, voir le rapport de publication.
