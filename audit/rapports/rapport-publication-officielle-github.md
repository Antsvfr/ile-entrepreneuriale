# Rapport de publication officielle — Île entrepreneuriale sur GitHub (6 novembre 2026)

Dépôt : **https://github.com/Antsvfr/ile-entrepreneuriale** · branche `main`.
Aucune phrase secrète, clé privée, jeton ni donnée d'authentification ne figure dans ce rapport ni dans le dépôt.
Sorties brutes de toutes les vérifications citées : `audit/preuves-brutes/2026-11-06-publication/`.

## 1. État initial
- Ancien dépôt `Antsvfr/simulation-questionnaire` (public), branche `claude/bold-noether-l93mmy`, commit `a5c4d72`, île dans
  `ile-des-agents/`, corrections de sécurité de l'étape 2 **non commitées** (présentes seulement dans le conteneur de travail).
- Étape 2 déclarée **NON VALIDÉE** (contournements lisibles du garde, `audit/rapports/2026-11-06-finalisation-etape-2.md`).
- Dépôt cible `Antsvfr/ile-entrepreneuriale` : existant, **public**, vide (aucun commit, aucune branche).
- Migration locale faite au préalable (`audit/rapports/rapport-migration-nouveau-depot.md`), non commitée.
- Registre des opérations : 53 événements, intègre ; **aucune identité présidentielle inscrite**.

## 2. Bilan de la migration
| Contrôle | Résultat | Preuve |
|---|---|---|
| 118 fichiers migrés, présents et intègres | 118/118 présents ; 83 identiques octet pour octet à la source ; 35 adaptés (chemins) et listés | `audit/migration/correspondance.tsv` (SHA-256 source et copie), `fichiers-adaptes.txt` |
| Rien d'oublié | 121 suivis + 3 non suivis de l'ancien dépôt = 118 migrés + 10 fusionnés/exclus justifiés ; 0 sans correspondance | `exclusions.tsv` ; vérifié aussi par la Forge |
| 9 dossiers | `presidence/ securite/ orchestrateur/ residence/ agents/ projets/ audit/ docs/ tests/` | visibles sur GitHub |
| Chemins, imports, configurations | aucun chemin de l'ancien dépôt dans le code exécuté ; Python : bibliothèque standard seulement ; tous les fichiers Python valides en Python 3.9 | grep, analyse des imports, `ast` sous 3.9 |
| 4 artefacts gelés | intacts (empreinte identique à celle déposée au journal), au local comme sur le clone GitHub | `clone-dc3ee3e/geles.out` |
| Journal présidentiel | copié à l'octet près : SHA-256 `185f84d1…b22080` identique à l'ancien ; 53 événements ; dernière empreinte de chaîne `1c31913324d5a073…` | `empreintes-journal.out`, `clone-dc3ee3e/journal-sha.out`, `verifier.out` |
| Ancien dépôt | intact du début à la fin : 147/147 empreintes, `git status` identique, HEAD `a5c4d72`, remote inchangé ; il reste la référence historique | contrôles `sha256sum -c` |
| Inspection indépendante (Forge, 2 passages en lecture seule) | migration « TERMINÉE », puis correctifs « PUBLIABLE » | §3 |

Réserve : le dossier historique du Mac (`~/Developer/simulation-questionnaire`) n'était pas accessible depuis le conteneur
de travail. S'il contient des événements de journal absents d'ici, ils ne sont pas migrés (contrôle au §12).

## 3. Corrections réalisées
| Constat | Correction | Vérification |
|---|---|---|
| D1 (moyen, introduit par la migration) : une copie intacte d'un artefact gelé laissée à son ancien chemin masquait une version falsifiée au nouveau | `verifier` contrôle **chaque** emplacement possible (ancien et nouveau chemin) et signale un artefact introuvable | test `test_artefact_migre_leurre_detecte` ; la Forge a remis l'ancienne version : le test échoue |
| D2 : l'arrêt d'urgence affiché dans la Résidence ne suivait plus exactement le garde | même règle que le garde (`securite/STOP` ou `ILE_OPS/STOP`) | serveur réel sur copie : affichage = décision du garde dans 4 cas |
| D3 : `residence/serveur.log` servi par le serveur | `*.log` et `*.pid` jamais servis | 404 |
| D4 : sauvegarde complète de l'ancien dépôt dans le dépôt | bundle **non publié** (ignoré) ; patchs et empreintes publiés comme preuves | `git add --dry-run` |
| D5, D6 : textes périmés, ouverture sans serveur | registre, copie de secours, commentaires ; `ville.js` essaie aussi `../../registre.json` | grep ; FALLBACK = registre |
| Test 3D instable (préexistant) | attente de l'état attendu (45 s au plus) au lieu d'un délai fixe de 12 s ; critère inchangé | avant : 2 réussites sur 3 dans l'ancien dépôt **et** dans le nouveau (pas une régression) ; après : 5/5 |
| Tests du garde dépendants de la branche (découvert **après** publication, sur clone neuf) | les cas « autorisés » simulent une branche de travail ; nouveau test : commit, fusion, push sans destination **sur main** exigent l'accord | 64/64 sur `main` et sur une branche de travail |

Aucune protection supprimée ni affaiblie (diffs relus par la Forge). Aucune règle du garde modifiée par ces correctifs.

## 4. Tests exécutés
| Vérification | Version auditée locale | Version publiée (clone neuf de `dc3ee3e`) |
|---|---|---|
| `python3 -I -S -m unittest discover -s tests` (3.13.18) | 63/63 avant 1er commit ; **2 échecs** une fois sur `main` → corrigé | **64/64 OK** |
| idem sous Python 3.9.25 (Python du Mac) | idem | **64/64 OK** |
| `python3 -I -S orchestrateur/ile.py verifier` | intègre, 53 événements | intègre, 53 événements |
| `python3 -I -S audit/preuves.py --claude` | 23 PASS · 1 PARTIEL · 0 FAIL · 0 NOT TESTED | **23 PASS · 1 PARTIEL · 0 FAIL · 0 NOT TESTED** |
| `bash audit/inspection.sh` | 45 éléments, 0 erreur (sur copie) | mode hook : code 0 |
| Lanceur `./ile demarrer` | — | `/api/sante` répond depuis le clone |
| Test 3D | 5/5 après correction | non relancé sur le clone |

Le seul PARTIEL (C3.2) : le fichier de démarrage automatique macOS est généré et valide, mais son chargement par
`launchctl` n'est pas testable sans Mac. Non testés ici : Tailscale, macOS lui-même.

## 5. Preuves de sécurité
- **Signatures Ed25519** : vecteurs officiels RFC 8032 reproduits (C2.1, tests).
- **Anti-usurpation** : un acte « présidentiel » non signé ou signé d'une autre clé est ignoré et signalé, même avec une
  chaîne recalculée (C2.4) ; une vraie session Claude Code qui tente `--auteur president` est bloquée par le garde (C3.4).
- **Phrase** : jamais sur disque ; saisie refusée hors d'un vrai terminal (C2.5) ; PBKDF2-HMAC-SHA256, 600 000 tours.
- **Résidence** : jeton anti-CSRF, session déverrouillée, origine, hôte ; accès distant derrière connexion ; 5 essais puis
  blocage (C0.3, C0.4, C2.6, C2.7, C3.3).
- **Garde** : interdits, opérations sensibles, file d'approbation à usage unique (C2.2, C2.3) ; détournement d'import
  rejoué avec modules piégés dans tous les dossiers privilégiés : aucun exécuté (C2.8, `test_confinement.py`).
- **Secrets** : 0 dans les 166 fichiers publiés et 0 dans l'historique de l'ancien dépôt (clés privées, jetons GitHub,
  OpenAI, AWS, Google, Slack, JWT, mots de passe) ; aucune adresse e-mail ni numéro de téléphone ; commits signés
  « Claude <noreply@anthropic.com> » (aucune adresse personnelle publiée).
- **Limites (étape 2 NON VALIDÉE)** : le garde lit des commandes et reste contournable par des commandes lisibles
  (`env cp`, `find -exec cp`, git `--git-dir`/`--work-tree`, `curl -o`, `patch`, `git push --all`, configuration
  `mirror`). Les agents tournent sous le même utilisateur système que le président.

## 6. Identité présidentielle
| Point | Constat |
|---|---|
| Identité présidentielle | **Aucune n'existe.** Le registre ne contient aucun événement `president.identite` (vérifié dans l'ancien et dans le nouveau journal). Il n'y avait donc rien à « conserver » ; je n'en ai pas créé : cela exige ta phrase, tapée par toi dans un vrai terminal. |
| Clé publique Ed25519 | aucune pour l'instant ; elle sera inscrite au journal à la création (seule la clé publique est enregistrée) |
| Preuve cryptographique | le mécanisme est prouvé avec des identités de test (preuve de possession, signatures, rejet des faux actes) ; il n'existe pas encore de preuve pour **ton** identité |
| Droits présidentiels | définis dans le code : seul un acte signé de la clé présidentielle tranche une décision, fixe une priorité, donne une instruction, accorde une opération sensible |
| Capacité à signer, à administrer | opérationnelle **dès que l'identité existe** (terminal : `./ile president …` ; Résidence : déverrouillage par la phrase) |
| Traçabilité | chaque acte est un événement signé, chaîné SHA-256, vérifié par `verifier` |
| Indépendance vis-à-vis de GitHub | totale : l'identité présidentielle est une clé Ed25519 dérivée de ta phrase ; ton compte GitHub (Antsvfr) administre le dépôt mais ne peut ni signer ni prouver un acte présidentiel, et réciproquement |

**Tant que l'identité n'est pas créée, tu n'es pas encore reconnu cryptographiquement comme Président dans le système**,
et « le premier arrivé » pourrait la créer : à faire en priorité (§12).

## 7. Configuration GitHub
| Point | Constat (vérifié par l'API GitHub) |
|---|---|
| Dépôt | `Antsvfr/ile-entrepreneuriale` existe ; aucun doublon créé |
| Remote local | `origin` = `https://github.com/Antsvfr/ile-entrepreneuriale.git` |
| Compte authentifié | `Antsvfr` |
| Droits | `Antsvfr` : rôle **admin**, seul collaborateur ; aucune permission modifiée |
| Visibilité | **publique** (inchangée, comme demandé) — tout le contenu est lisible sur Internet |
| Branche principale | `main` (branche par défaut), seule branche |
| Protection de `main` | **aucune** (`protected: false`) — je n'ai pas d'outil pour la configurer et ne l'ai pas modifiée ; à activer par toi (§12) |
| Fichiers exclus | `.gitignore` : secrets, fichiers d'exécution (`securite/STOP`, `securite/acces.json`, `etat.json`, journaux du serveur, verrous), caches Python, bundle de sauvegarde |
| Garde de l'île et push | le push n'a **pas** été soumis à une approbation signée : les hooks de l'île n'étaient pas actifs dans la session de travail (le push n'a déclenché aucune demande `A-…`), et aucune identité présidentielle n'existe pour signer. L'autorisation est ton message explicite (« Tu es autorisé à effectuer les commits et le push »), conforme à la règle de l'île (« accord explicite d'Anton dans le chat »). |

## 8. Commits publiés
| Commit | Contenu |
|---|---|
| [`7bfbd9b`](https://github.com/Antsvfr/ile-entrepreneuriale/commit/7bfbd9b005183af2f7167498c1a8ab774507e0f1) | migration intégrale, corrections après inspection, rapports, preuves (166 fichiers) |
| [`dc3ee3e`](https://github.com/Antsvfr/ile-entrepreneuriale/commit/dc3ee3e7bb7d6aa6167150787109972f2e292813) | tests du garde indépendants de la branche + test de la branche protégée — **version auditée et vérifiée sur clone neuf** (arbre `c0e0333c…`, identique au local) |
| commit suivant (le dernier de `main`) | ajoute uniquement ce rapport et les sorties brutes du clone (`audit/preuves-brutes/2026-11-06-publication/clone-dc3ee3e/`) |

Aucun historique détruit, aucun push forcé ; l'ancien dépôt n'a reçu aucun commit.

## 9. Droits administrateur
Confirmés par l'API GitHub : compte authentifié `Antsvfr`, rôle `admin` sur `Antsvfr/ile-entrepreneuriale`.

## 10. Risques résiduels
1. **Identité présidentielle absente** : quiconque exécute `./ile president` en premier devient président (règle du premier arrivé).
2. **Garde contournable** par des commandes lisibles ; agents et président partagent le même utilisateur système (étape 2 NON VALIDÉE).
3. **`main` non protégée** sur GitHub : un push forcé ou une suppression reste possible depuis tout accès en écriture.
4. **Dépôt public** : missions, projets, journal et rapports (y compris la liste des contournements du garde) sont lisibles par tous. Le serveur n'écoute que sur 127.0.0.1 : ces informations ne donnent pas d'accès à distance, mais le contenu des maisons (projets d'études, UPSA, BDE…) est public — déjà le cas dans l'ancien dépôt public.
5. **Mac non rapproché** (§2).
6. Test 3D dépendant du rendu logiciel (rendu stable 5/5 depuis la correction, à surveiller).

**Publication ≠ déploiement.** Ce qui est **publié** : le code source et les documents, sur GitHub. Ce qui est
**déployé** : **rien**. Aucune application n'est accessible sur Internet ; le serveur de l'île tourne sur la machine
qui le lance, en local (127.0.0.1:7777) ; aucun GitHub Pages ni workflow n'a été configuré par cette mission.

## 11. Fonctionnalités restant à développer
- Étape 3 : exécution des instructions présidentielles par les agents (aujourd'hui présentées au DG, jamais exécutées automatiquement).
- Séparation réelle des privilèges (utilisateur système dédié aux agents, garde-fous en lecture seule pour eux) : `docs/architecture/SEPARATION-DES-PRIVILEGES.md`.
- Direction Innovation & Business (prévue), direction technique (prévue).
- Accès distant Tailscale et démarrage automatique macOS : à tester sur le Mac.
- Ouverture de la métropole sans serveur (`file://`) : animation d'ambiance seulement.

## 12. Récupérer et lancer le projet — et actions qui te reviennent
Sur le Mac (dossier hors de Documents, Bureau, Téléchargements) :
```bash
git clone https://github.com/Antsvfr/ile-entrepreneuriale.git ~/Developer/ile-entrepreneuriale
```
```bash
cd ~/Developer/ile-entrepreneuriale && ./ile
```
Puis http://localhost:7777/ (métropole) et http://localhost:7777/residence. Vérifier : `python3 -I -S -m unittest discover -s tests`.

Actions manuelles, dans cet ordre :
1. **Créer ton identité présidentielle**, toi-même, dans Terminal (jamais dans un chat, jamais par un agent) :
   `./ile president` — choisis une phrase longue que tu n'oublieras pas (aucune récupération possible). La Résidence
   affichera ensuite l'empreinte de ta clé publique et sa date : note-les.
2. **Protéger `main`** sur GitHub : *Settings → Branches → Add branch ruleset* (ou *Branch protection rule*) sur `main` :
   interdire les push forcés et la suppression, exiger une pull request.
3. **Décider de la visibilité** : le dépôt est public ; *Settings → General → Danger Zone → Change visibility* si tu le veux privé.
4. **Rapprocher le Mac** : dans l'ancien dossier, `python3 -I -S operations/ile.py verifier`. Si la sortie indique
   53 événements et `1c31913324d5a073…`, rien à faire ; sinon, signale-le avant d'utiliser le nouveau dépôt.
5. Si tu avais installé le démarrage automatique depuis l'ancien dossier : `./ile installer` depuis le nouveau le remplace
   (même nom de service).

## Statuts
- **MIGRATION : VALIDÉE** — 118/118 fichiers présents et intègres, journal identique à l'octet, artefacts gelés intacts,
  ancien dépôt intact, inspection indépendante favorable, tests et preuves au vert sur la version publiée (réserve : Mac non examiné).
- **SÉCURITÉ ET IDENTITÉ PRÉSIDENTIELLE : PARTIELLES** — mécanismes cryptographiques et anti-usurpation prouvés ; mais
  **aucune identité présidentielle n'existe encore**, l'étape 2 reste NON VALIDÉE (garde contournable) et `main` n'est pas protégée.
- **PUBLICATION GITHUB : RÉUSSIE** — `main` publiée, commits visibles, contenu identique à la version auditée, dépôt
  récupérable et testé depuis un clone neuf, compte `Antsvfr` administrateur.
