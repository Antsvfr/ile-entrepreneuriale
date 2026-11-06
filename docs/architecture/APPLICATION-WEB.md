# Application web de l'Île entrepreneuriale

État au 6 novembre 2026. Chaque élément porte un statut : **DÉPLOYÉ** (en ligne, vérifié depuis l'extérieur),
**PRÊT** (fait et testé, en attente d'une action), **BLOQUÉ** (dépend d'une décision ou d'un compte d'Anton).

## 1. Ce qui existait (audit)
| Élément | Fonctionnement | Exposable sur Internet ? |
|---|---|---|
| `residence/serveur.py` | serveur Python standard, **127.0.0.1 seulement** ; sert les fichiers de l'île et une API : `GET /api/sante, /api/etat, /api/residence, /api/president, /api/verifier, /api/session, /api/journal` ; `POST` d'actes présidentiels (décision, priorité, instruction, mission, approbation) après **déverrouillage par la phrase** — la clé est **dérivée côté serveur** et gardée en mémoire | les lectures, oui ; les actes, **non** tels quels (la phrase partirait vers le serveur) |
| `residence/village/` | métropole 3D (`ville.js`, three.js 0.147 par CDN), Résidence (`residence.html`), connexion distante | oui (fichiers statiques) |
| `orchestrateur/` | registre en fichier JSONL chaîné, projections recalculées à chaque lecture | lecture : oui (déjà public dans le dépôt) ; écriture : jamais depuis Internet sans authentification forte |
| `securite/`, hooks | garde des agents Claude Code, sur la machine des agents | **non** : ce sont des contrôles locaux |
| Agents | lancés par Claude Code sur la machine d'Anton ou dans une session cloud | **non** : les lancer depuis le web reviendrait à exécuter du code à distance |

Dépendances au système de fichiers local : le journal (`orchestrateur/registre/journal.jsonl`), l'arrêt d'urgence
(`securite/STOP`), l'accès distant (`securite/acces.json`), les verrous. Aucune base de données.

## 2. Architecture retenue

```
 Visiteur (tout navigateur)                         Anton, sur son ordinateur
        │ HTTPS                                             │
        ▼                                                   ▼
 GitHub Pages ─ fichiers statiques du dépôt        ./ile ─ serveur local 127.0.0.1:7777
   index.html (accueil)                               Résidence complète : déverrouillage par la phrase,
   residence/village/  (métropole, Résidence,         actes signés, approbations, instructions
                        vérification) — LECTURE SEULE        │
   residence/instantane/*.json  ◄── ./ile publier ───────────┘ (même code de projection que l'API)
   orchestrateur/registre/journal.jsonl  ──► vérifié dans le navigateur (verification.js)
```

| Couche | Choix | Statut |
|---|---|---|
| **Frontend** | les pages existantes de l'île (métropole 3D, Résidence, nouvelle page de vérification, accueil), servies par GitHub Pages ; un module `source.js` choisit la source des données : serveur local s'il répond, sinon instantané publié | **DÉPLOYÉ** |
| **Données publiées** | `residence/instantane/` : résidence, état 3D, journal, vérification, identité — générés par `residence/serveur.py --instantane` (= `./ile publier`), c'est-à-dire par **le même code** que les routes de l'API ; les noms d'hôte de l'accès distant sont retirés | **DÉPLOYÉ** |
| **Vérification publique** | `verification.js` recalcule dans le navigateur la chaîne SHA-256, la numérotation, les actes présidentiels (Ed25519, preuve de possession, clé en vigueur) et les empreintes des documents gelés — résultats identiques à `ile.py verifier` (testé) | **DÉPLOYÉ** |
| **Backend en ligne** | aucun. La Résidence qui agit reste le serveur local d'Anton | **BLOQUÉ** (§4) |
| **Base de données** | aucune : le journal chaîné en fichier reste la source de vérité (le migrer vers une base casserait sa preuve) | — |
| **Authentification en ligne** | aucune, **parce qu'il n'y a rien à protéger en ligne** : la version publiée ne contient que des données déjà publiques (dépôt public) et n'expose aucune action. Une connexion sur un site statique ne protégerait rien : elle n'existe donc pas | — |
| **Système présidentiel** | consultation et vérification en ligne ; **signature uniquement en local** (la phrase ne quitte pas l'ordinateur d'Anton) | consultation **DÉPLOYÉ** · signature en ligne **BLOQUÉ** |
| **Agents** | non exposés sur Internet | volontaire |

## 3. Sécurité de la version publiée
- **HTTPS** : imposé par GitHub Pages sur `*.github.io`.
- **Aucune exécution** : site statique ; aucune route d'écriture, aucun terminal, aucun accès au système de fichiers de
  la machine d'Anton. Toutes les commandes de la Résidence sont désactivées et l'expliquent.
- **Aucun secret** : la phrase et la clé privée n'existent jamais côté serveur ni dans le dépôt ; l'instantané ne
  contient que des projections du journal (déjà public) ; test automatique (`tests/test_version_web.py`).
- **Anti-usurpation** : un faux acte présidentiel est signalé par la vérification dans le navigateur (signature Ed25519
  contrôlée avec la clé publique inscrite) — testé avec des actes signés puis falsifiés.
- **Injection** : tout texte du journal est échappé avant affichage (`esc`) ; pages publiées avec une politique de
  sécurité du contenu (`<meta http-equiv="Content-Security-Policy">` : scripts et requêtes limités au site).
- **Limite** : GitHub Pages ne permet pas d'en-têtes HTTP personnalisés (HSTS est géré par GitHub ; pas de CSP en
  en-tête, seulement en balise).
- **Exposition** : tout le contenu de l'île est lisible par tous — c'était déjà le cas avec le dépôt public.

## 4. Pour aller plus loin : un vrai backend en ligne (BLOQUÉ — décision et compte d'Anton)

**Règle de conception non négociable** : la clé présidentielle ne doit **jamais** être dérivée par un serveur tiers.
La phrase → PBKDF2 → graine Ed25519 doit se faire **dans le navigateur** du président (WebCrypto PBKDF2 + Ed25519 en
JavaScript, déjà écrit pour la vérification) ; le serveur ne reçoit que des actes **déjà signés** et les vérifie avec la
clé publique. Le serveur actuel (déverrouillage côté serveur) ne doit pas être exposé tel quel sur Internet.

| Option | Ce que ça donne | Coût indicatif (à vérifier au moment de souscrire) | Ce qu'il faut d'Anton |
|---|---|---|---|
| **A. Tailscale (déjà codé)** | la Résidence complète du Mac, joignable depuis ses appareils (privé) ; en *Funnel*, joignable de tout Internet avec la connexion par phrase existante | gratuit (plan personnel) ; Funnel : bande passante limitée, non publiée | compte Tailscale, `./ile distant activer`, Mac allumé ; Funnel déconseillé tant que la signature n'est pas faite dans le navigateur |
| **B. Petit serveur virtuel (Hetzner…)** | backend permanent, disque persistant pour le journal, domaine personnalisé | ≈ 4–7 €/mois (prix 2026 en hausse, à vérifier sur hetzner.com) | compte, carte bancaire, administration système (mises à jour, sauvegardes) |
| **C. Fly.io** | conteneur + volume persistant | ≈ 2–3 $/mois (VM 256 Mo) + 0,15 $/Go/mois de volume | compte, carte bancaire |
| **D. Render** | service web managé | offre gratuite **sans disque persistant** (inutilisable pour le journal) ; disque 0,25 $/Go/mois sur offre payante | compte, carte bancaire |

Recommandation : **phase 2** = signature dans le navigateur + backend minimal (option B ou C) qui n'accepte que des
actes signés, sur un sous-domaine personnel ; d'ici là, option A (privée) pour agir à distance.

Domaine : l'adresse permanente actuelle est `https://antsvfr.github.io/ile-entrepreneuriale/`. Un domaine personnalisé
(ex. `ile.<domaine-d-anton>`) s'ajoute dans *Settings → Pages → Custom domain* après l'achat d'un domaine
(≈ 10–15 €/an selon l'extension) et un enregistrement DNS `CNAME` vers `antsvfr.github.io`.

## 5. Maintenance
- Mettre à jour la version web après un travail de l'île : `./ile publier`, puis commit et push de `residence/instantane/`
  (GitHub Pages republie `main` en une à deux minutes). La page indique si l'instantané est en retard sur le journal publié.
- Tester la version publiée : `node tests/version_publiee.js https://antsvfr.github.io/ile-entrepreneuriale/`.
- Tests : `python3 -I -S -m unittest discover -s tests` ; preuves : `python3 -I -S audit/preuves.py`.

Sources des prix (consultées le 6 novembre 2026, non officielles pour la plupart) :
[Fly.io — tarifs](https://fly.io/pricing), [Fly.io — documentation des prix](https://fly.io/docs/about/pricing/),
[Render — prix 2026](https://temps.sh/blog/render-pricing-2026), [Hetzner — comparatif 2026-08](https://kimmo.suominen.com/stuff/cpc-2026-08.txt),
[Tailscale — Funnel](https://tailscale.com/docs/features/tailscale-funnel.md), [Tailscale — offres](https://tailscale.com/plans/).
