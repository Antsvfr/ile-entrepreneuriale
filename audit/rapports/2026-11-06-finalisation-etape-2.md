# Finalisation sécurisée de l'étape 2 — rapport (6 novembre 2026)

Non commité, non poussé, non inscrit au journal ; R-0005 reste ouverte ; aucune identité réelle créée ; aucun secret dans ce rapport.

## A. État initial
- Commit `a5c4d72` (branche `claude/bold-noether-l93mmy`). Modifications non commitées du Forgeron : `operations/garde.py` (durcissement partiel) et le rapport d'inspection. Sauvegarde : `/tmp/claude-0/sauvegarde-forge-20261106-101315/` (patch, garde.py du Forgeron, garde.py du commit, rapport).
- Faille de l'audit (reproduite) : `operations/json.py` planté → exécuté par le garde → `git push origin main` code 0.
- Correction du Forgeron : bloquait `json.py`, mais **pas le chemin indirect** (garde → `ile` → `ile.py` remettait `operations/` en tête de `sys.path` → `president` → `hmac` planté exécuté, code 0, même en `python3 -I`). `serveur.py`, `etat-ile.py`, `ile.py` (commandes présidentielles) avaient la même faille. Un test cassé (`test_arret_d_urgence`).
- Journal réel : intègre, 53 événements, empreinte `1c31913324d5a073…`.

## B. Corrections
| Couche | Fichiers | Effet |
|---|---|---|
| 1. `python3 -I -S` partout | les deux `.claude/settings.json` (hooks en `/usr/bin/python3 -I -S`), `ile` (13 appels + LaunchAgent), `forge/inspection.sh` | ni dossier du script, ni dossier courant, ni `PYTHONPATH`, ni site utilisateur, `.pth`, `usercustomize`, `sitecustomize` |
| 2. Chemin d'import réduit à la bibliothèque standard avant tout import | en tête de `garde.py`, `ile.py`, `serveur.py`, `etat-ile.py`, `preuves.py` | protège même lancé sans `-I` contre les modules plantés dans le projet |
| 3. Chargement par chemin exact, depuis la source | `operations/confinement.py` (nouveau) ; `ile.py`, `president.py`, `serveur.py`, `etat-ile.py`, `garde.py`, `preuves.py` | `signature`, `president`, `ile` jamais pris au chemin d'import ni à un `.pyc` ; homonyme refusé |
| Nettoyage | `ile.py`, `president.py` | `from __future__` retiré (annotations `Optional`, compatible 3.9) ; plus aucun `sys.path.insert` dans les fichiers privilégiés |
| Échec fermé | `garde.py` (`sys.excepthook`), commande du hook `… || exit 2` | toute erreur, garde illisible ou absent → refus |
| Arrêt d'urgence | `garde.py`, `serveur.py` | vrai `operations/STOP` ET celui de `ILE_OPS` ; `test_arret_d_urgence` repasse **sans modification** |
| Garde (suite de l'inspection) | `garde.py` | accord exigé pour : `.py/.pyc/.pth/__pycache__` sous `operations/`, `operations/tests/`, `confinement.py`, lanceurs ; copie/déplacement/extraction vers un dossier de garde-fous ; `git checkout/restore/reset/pull/merge/apply…` et `git config` en écriture dans le dépôt ; `.git/config`, `.git/hooks` ; push sans destination dont la configuration vise `main` ; `/usr/bin/git` |
| Preuves | `preuves.py` | nouveau critère C2.8 (attaque de l'audit rejouée avec les commandes exactes des réglages) ; C3.2 vérifie enfin le fichier généré (son résultat était ignoré) |
| Documentation | `architecture/ETAPES-2.md`, `CLAUDE.md` | matrice corrigée, contournements restants écrits en clair |

## C. Tests
- Suite : **62/62** sous Python 3.13 et **62/62** sous Python 3.9.25 (41 d'origine + 21 de `test_confinement.py`).
- Sur les versions d'avant, les nouveaux tests échouent : 49 échecs sur le commit `a5c4d72`, 47 sur la version du Forgeron.
- Preuves : **23 PASS · 1 PARTIEL (C3.2, pas de Mac) · 0 FAIL · 0 NOT TESTED** avec `--claude` (vraie session Claude Code bloquée) ; sous 3.9 : 22 PASS · 1 PARTIEL · 0 FAIL · 1 NOT TESTED (C3.4 non relancée).
- Audit d'origine : authentification, Ed25519, intégrité, usurpation par signature, approbation à usage unique : toujours PASS. Faille d'import : réussie avant, bloquée après.
- `ile.py verifier` sur le vrai journal : intègre, 53 événements ; empreinte du fichier inchangée du début à la fin.
- `forge/inspection.sh` : 43 éléments, 0 erreur (ce passage a régénéré `2026-11-06-inspection.md`, rapport produit par ce même script).

## D. Inspection indépendante (Forge, deux passages, lecture seule, copies dans /tmp)
- Import : **bloqué** pour les ~95 homonymes de la bibliothèque standard, `encodings/`, `.pyc` forgés, `PYTHONPATH`, site utilisateur, `.pth`, sous 3.13 et 3.9, contre le garde, les hooks, le serveur, les commandes présidentielles.
- Résiduel import : `-S` sans `-I` sous 3.9 (aucun point d'entrée ne le fait) ; interpréteur ou bibliothèque standard modifiables (Homebrew ; agents root dans ce conteneur).
- **Contournements lisibles restants du garde** (prouvés) : `env cp …` / `find -exec cp` vers `operations/` ; `curl -o`, `wget -O`, `patch`, `find -exec sed -i` ; git hors du dépôt avec `--git-dir/--work-tree` (remet un ancien `garde.py`) ; `git push origin --all`, `'refs/heads/*'`, `remote.origin.mirror` en configuration globale (main écrasée sur un dépôt de test) ; la suite de tests et la preuve C1.1 restent falsifiables une fois un module planté par ces voies.

## E. Conclusion : ÉTAPE 2 NON VALIDÉE
La faille de l'audit et toute la classe « détournement d'import » sont corrigées et prouvées. Mais la mission demande que le garde ne puisse pas être contourné et qu'aucun push vers `main` ne passe sans accord : l'inspection indépendante prouve que c'est encore possible par des commandes lisibles. Un garde qui lit des commandes ne peut pas toutes les énumérer : ce n'est pas une frontière de sécurité.

Ce qui tient réellement : la signature présidentielle (aucun acte en ton nom sans ta phrase, même avec un garde contourné).

Décisions qui te reviennent :
1. **Protection de branche GitHub sur `main`** (REV-EM, LexNote, ce dépôt) : la seule barrière contre un push qui tienne même si le garde tombe.
2. **Créer toi-même ton identité** (`./ile president`) avant toute session d'agents.
3. Architecture : faire tourner les agents sous un autre utilisateur système que celui qui possède les garde-fous (fichiers en lecture seule pour eux). Seule façon de rendre les garde-fous réellement intouchables.
4. Autoriser ou non le commit de ces corrections (elles améliorent la sécurité, même sans valider l'étape).
