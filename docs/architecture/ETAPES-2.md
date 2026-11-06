# Étape 2 — garde-fous, identité présidentielle, accès direct (6 novembre 2026)

## Ouvrir l'île

| Besoin | Commande ou geste |
|---|---|
| Ouvrir l'île (démarre si besoin, ouvre le navigateur) | `./ile` ou double-clic sur **Ouvrir l'île.command** |
| Aller droit à la Résidence | `./ile residence` · http://localhost:7777/residence |
| Démarrage automatique à chaque ouverture de session (Mac) | `./ile installer` (une fois) : l'île reste joignable sur http://localhost:7777/ et un raccourci « Île des Agents » est posé sur le Bureau |
| Créer l'identité présidentielle (une fois) | `./ile president` (dans Terminal) |
| Accès privé depuis un autre appareil | `./ile distant activer` (Tailscale) |
| Arrêt d'urgence de tous les agents | `./ile arret-urgence on` / `off` |
| État, journal du serveur, arrêt | `./ile statut` · `./ile journal` · `./ile arreter` |

Adresses stables : `/` (métropole), `/residence`, `/batiment/<id>` (ex. `/batiment/rev-em`), `/connexion` (accès distant). Dans la métropole : bouton **Résidence ↗** ou touche **R**.

## Ce qui est construit

| Brique | Fichier | Mécanisme réel |
|---|---|---|
| Signature Ed25519 (RFC 8032) en Python standard | `presidence/signature.py` | vecteurs officiels reproduits (tests) |
| Identité présidentielle | `presidence/president.py` | phrase → PBKDF2-HMAC-SHA256 (600 000 tours) → graine Ed25519 ; seule la clé publique est au journal (`president.identite`) |
| Actes présidentiels signés | `orchestrateur/ile.py` | décisions, priorités, instructions, accords d'opération, arbitrages de missions : ignorés et signalés s'ils ne portent pas une signature valide |
| Le garde | `securite/garde.py`, hook `PreToolUse` (les deux `.claude/settings.json`) | lancé par Claude Code avant CHAQUE action de CHAQUE agent ; code 2 = refus ; toute erreur (même un `garde.py` illisible ou absent) = refus (`|| exit 2`) |
| Confinement des imports | `securite/confinement.py` + bloc en tête de `garde.py`, `ile.py`, `residence/serveur.py`, `etat-ile.py` | points d'entrée lancés en `python3 -I -S` ; chemin d'import réduit à la bibliothèque standard avant tout autre import ; modules de l'île chargés par chemin exact depuis la source (jamais un `.pyc`) |
| File d'approbations | `ile.py` (`approbation.*`), Résidence | opération sensible bloquée → demande → accord signé → la même opération exacte passe une fois (ou pendant une fenêtre pour un fichier) |
| Arrêt d'urgence | `securite/STOP` | le garde refuse toute action (lecture exceptée) tant que le fichier existe |
| Serveur | `residence/serveur.py` | port fixe 7777, une instance, 127.0.0.1 seulement, sessions déverrouillées par la phrase, accès distant derrière connexion, tentatives limitées |
| Lanceur | `ile`, `Ouvrir l'île.command` | démarrage, arrêt, LaunchAgent macOS, Tailscale, identité, arrêt d'urgence |
| Résidence | `residence/village/residence.html`, `residence/village/connexion.html` | centre de contrôle : à trancher, projets, rapports, missions, instructions, agents, tests, sécurité, historique, organisation, journal |

## Matrice des protections : ce qui est imposé, contournable, non testé

Les agents (Claude Code) tournent sur le même ordinateur et sous le même utilisateur système que le président : tout fichier que le président peut lire, un agent peut le lire. Le modèle de sécurité en tient compte.

| Protection | Réellement imposé | Contournable par un agent ? | Testé |
|---|---|---|---|
| Identité présidentielle | Oui, cryptographiquement : sans la phrase, impossible de produire une signature valide. La phrase n'existe nulle part sur disque. | **Non** (sauf si l'agent obtient la phrase : ne jamais la taper dans un chat ni la donner à un agent) | Oui (C2.1, C2.4, tests) |
| Actes présidentiels falsifiés | Oui : ignorés par toutes les projections, signalés par `ile.py verifier`, la Forge et la Résidence | **Non** : même un agent qui réécrirait le journal avec une chaîne cohérente ne peut pas fabriquer de signature | Oui (C2.4) |
| Saisie de la phrase | Seulement dans un vrai terminal (`/dev/tty`) ou la Résidence | Un agent n'a pas de terminal | Oui (C2.5) |
| `--auteur president`, écriture du journal à la main, manipulation de l'identité | Bloqués par le garde, refus inscrits | Le garde lit les commandes : une commande volontairement obscurcie (base64, script intermédiaire) peut lui échapper. **Mais** l'effet reste nul : sans signature, l'acte est rejeté. | Oui, y compris par une vraie session Claude Code (C3.4) |
| Détournement d'import Python (module planté : `json.py`, `hmac.py`, `getpass.py`…, `.pyc` forgé, `PYTHONPATH`, `usercustomize`, `.pth`) | Oui : aucun module planté n'est exécuté par le garde, les hooks, le serveur ni les commandes présidentielles ; écrire un `.py`/`.pyc`/`.pth` dans `operations/` exige ton accord | Seulement en remplaçant l'interpréteur lui-même (bibliothèque standard modifiable, ex. Homebrew ; les hooks appellent `/usr/bin/python3`, pas le premier `python3` du `PATH`) : écriture hors du dépôt, donc soumise au garde, sauf commande obscurcie | Oui (`test_confinement.py`, 21 tests, sous Python 3.13 et 3.9 ; preuve C2.8 ; échec démontré sur les versions d'avant ; inspection indépendante de la Forge) |
| Opérations sensibles (push sur `main`, y compris un `git push` sans destination dont la configuration vise `main`, push forcé, fusion, déploiement, suppression large, secrets, envoi réseau, modification des garde-fous, écriture hors du dépôt) | Bloquées par le garde jusqu'à l'accord signé | **Oui, par des commandes lisibles** : `git push origin --all`, `git push origin 'refs/heads/*'`, `remote.origin.mirror` posé par `git config --global` (prouvé par la Forge sur un dépôt de test). Seule protection fiable : **protection de branche GitHub sur `main`** (à activer par toi), qui tient même si tout le reste échoue. | Oui (C2.2, C2.3, tests) |
| Rôles (critique en lecture, directeur limité à sa maison) | Appliqués quand Claude Code transmet le type d'agent au hook | Si le champ n'est pas transmis par la version de Claude Code, la limite de rôle ne s'applique pas (les autres protections, si) | Règle testée ; transmission du champ par Claude Code non vérifiée |
| Garde-fous modifiables par un agent ? | Y compris sans les nommer : copie ou déplacement vers leur dossier (`cp x securite/`), copie récursive, extraction d'archive, `git checkout`/`restore`/`reset`/`pull`/`merge`/`apply` dans le dépôt, configuration git (`.git/config`, `.git/hooks`). `garde.py`, `ile.py`, `president.py`, `signature.py`, `confinement.py`, `residence/serveur.py`, les `settings.json`, les hooks, le lanceur `ile`, `Ouvrir l'île.command`, `audit/inspection.sh`, tout `.py` de `securite/`, `presidence/`, `orchestrateur/`, `residence/`, `audit/`, et `tests/` : toute modification exige ton accord | **Oui, par des commandes lisibles** (inspection de la Forge, 6 novembre) : préfixe devant la copie (`env cp …`, `find … -exec cp`), `curl -o`, `patch`, git lancé hors du dépôt avec `--git-dir`/`--work-tree`. Le garde lit des commandes : il ne peut pas les énumérer toutes. git garde l'historique | Oui |
| Arrêt d'urgence | Le garde refuse tout tant que `securite/STOP` existe ; un agent ne peut pas le supprimer par une commande lisible | Même limite | Oui |
| Résidence en local | Lecture libre sur cet ordinateur ; tout acte exige la session déverrouillée + jeton anti-CSRF + origine | Un agent local peut LIRE l'API (comme les fichiers) ; il ne peut pas AGIR sans la phrase | Oui (C0.4) |
| Accès distant | Jamais ouvert par défaut ; seulement pour les noms d'hôte inscrits par `./ile distant activer` ; tout y exige la connexion ; cookie `Secure`, `HttpOnly`, `SameSite=Strict` ; 5 essais puis 10 min de blocage | Le serveur n'écoute que sur 127.0.0.1 : il n'est joignable de l'extérieur que par Tailscale | Logique serveur testée (C2.6, C2.7) ; **Tailscale lui-même non testé ici** |
| Démarrage automatique (launchd) | Fichier généré et validé | — | **Partiel** : chargement par `launchctl` non testable sans Mac (C3.2) |

## Limites connues
- **Création de l'identité** : la première identité est acceptée telle quelle (« premier arrivé »). Crée-la toi-même dès la première ouverture (`./ile` te le propose) ; la Résidence affiche son empreinte et sa date pour que tu la reconnaisses.
- **Phrase perdue** : aucune récupération possible (c'est le prix de la sécurité). Changer de phrase : `./ile president changer-phrase` (signé par l'ancienne).
- **Accès distant et journal** : l'accès distant montre le serveur de ton Mac (un seul journal). Travailler en parallèle depuis le cloud et depuis le Mac produirait encore deux chaînes à réconcilier.
- **Instructions** : présentées au DG à chaque début de session ; pas d'exécution sans session ouverte avant l'étape 3.
- **Le garde n'est pas une frontière de sécurité complète** : il reconnaît des commandes, et des formes lisibles lui échappent encore (voir la matrice). Ce qui tient réellement : la signature présidentielle (aucun acte sans ta phrase) et, à activer, la protection de branche GitHub. Rendre les garde-fous inaccessibles aux agents demande de les faire tourner sous un autre utilisateur système que les agents (décision d'architecture à prendre).
- **Confinement des imports** : il suppose que les points d'entrée sont lancés comme prévu (`python3 -I -S`, réglages et lanceur). Lancé à la main sans `-I`, le bloc en tête de chaque script protège encore contre les modules plantés dans le projet, mais pas contre un `usercustomize`/`.pth` du site utilisateur, ni contre `PYTHONPATH` sous Python 3.9 (exécutés par Python avant le script). Lancé en `-S` sans `-I`, un `os.py` planté à côté du script serait chargé. L'interpréteur lui-même (`python3` trouvé par le `PATH`, bibliothèque standard d'une installation Homebrew modifiable par l'utilisateur) reste hors de portée : même utilisateur système.
- **Python sur Mac** : compatible avec le python3 système (3.9). Si le projet est dans Documents, Bureau ou Téléchargements, macOS peut refuser l'accès au service lancé en arrière-plan : `./ile installer` le signale et propose deux solutions.
