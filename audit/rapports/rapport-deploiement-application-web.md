# Rapport de déploiement — application web de l'Île Entrepreneuriale (6 novembre 2026)

**URL : https://antsvfr.github.io/ile-entrepreneuriale/** — en ligne, vérifiée depuis un navigateur extérieur à
l'environnement de développement (Chromium passant par Internet, vérification TLS active).

Statuts : **DÉPLOYÉ** (en ligne, vérifié) · **PRÊT** (fait, en attente d'une action) · **BLOQUÉ** (dépend d'Anton).

## 1. Architecture retenue
L'application est **l'île existante**, transformée — pas une maquette. Détail : `docs/architecture/APPLICATION-WEB.md`.

| Couche | Réalisation | Statut |
|---|---|---|
| Frontend | pages existantes de l'île (métropole 3D `residence/village/index.html` + `ville.js`, Résidence `residence.html`) + accueil `index.html` + page `verification.html`, servies par GitHub Pages ; `source.js` choisit la source : serveur local s'il répond, sinon instantané publié | DÉPLOYÉ |
| Données en ligne | `residence/instantane/*.json`, produits par `residence/serveur.py --instantane` (= `./ile publier`) avec **le code même des routes de l'API** ; noms d'hôte de l'accès distant retirés | DÉPLOYÉ |
| Vérification publique | `verification.js` : chaîne SHA-256, numérotation, actes présidentiels (Ed25519 RFC 8032, preuve de possession, clé en vigueur), documents gelés — résultats identiques à `ile.py verifier` | DÉPLOYÉ |
| Backend en ligne, base de données, comptes | aucun — voir §3 et §5 | BLOQUÉ (compte et décision d'Anton) |
| Système présidentiel | consultation et vérification en ligne ; **signature uniquement dans la Résidence locale** | consultation DÉPLOYÉ · signature en ligne BLOQUÉ |
| Agents | jamais exposés sur Internet (ce serait de l'exécution de code à distance) | volontaire |
| Mode local (`./ile`) | inchangé : Résidence complète, déverrouillage, actes signés | conservé, testé |

## 2. Fonctionnalités opérationnelles (en ligne)
| Fonction | Où | Vérifié |
|---|---|---|
| Accueil : état réel (registre intègre, 79 événements, 7 projets, 9 missions, 4 décisions en attente, agents au travail, date de l'instantané) et les 17 institutions du registre | `/` | test navigateur |
| Métropole 3D interactive : quartiers, sièges, jour/nuit, visite guidée, état réel figé à la date de l'instantané | `residence/village/index.html` | test navigateur (three.js depuis le vrai CDN) |
| Navigation entre bâtiments ; chaque bâtiment ouvre ses fonctions réelles (section de la Résidence, vérification, dossier dans le dépôt) ; journal des 5 dernières entrées de chaque maison | panneau « Accéder » | test navigateur |
| Résidence en consultation : à trancher, projets, rapports des directeurs, missions, instructions, agents (exécutions), tests, sécurité, historique, organisation, journal des opérations filtrable | `residence/village/residence.html` | test navigateur (47 commandes, 0 active) |
| Vérification publique du registre et des documents gelés | `residence/village/verification.html` | test navigateur + tests automatisés contre Python |
| Affichage mobile (390 px, sans débordement) | accueil, Résidence, vérification | test navigateur |

## 3. Fonctionnalités non disponibles en ligne (et pourquoi)
| Fonction | Disponible où | Raison |
|---|---|---|
| Signer une décision, fixer une priorité, donner une instruction, accorder une opération | Résidence locale (`./ile`) | le serveur actuel dérive la clé de la phrase **côté serveur** : l'exposer ferait voyager la phrase vers un serveur ; la version en ligne n'a pas de backend |
| Se connecter / comptes et rôles en ligne | — | sans backend, une « connexion » sur un site statique ne protégerait rien : elle n'existe donc pas plutôt que d'être factice |
| Administrer ou lancer des agents depuis le web | Claude Code sur la machine d'Anton | exécution de code à distance : exclu |
| Données en temps réel | Résidence locale | la version en ligne montre l'instantané ; elle signale si le journal publié est plus récent |
| Identité présidentielle | — | **pas encore créée** (à faire par Anton : `./ile president`) ; la version en ligne l'affiche honnêtement |

## 4. Infrastructure et coûts
- **GitHub Pages** (déjà actif sur le dépôt public) : **0 €**. HTTPS imposé, en-tête HSTS envoyé par GitHub
  (`strict-transport-security: max-age=31556952`, constaté). Publication automatique de `main` (≈ 5 min constatées).
- Dépendances en ligne : three.js 0.147.0 (licence MIT) et Google Fonts (OFL), chargés depuis leurs CDN.
- Aucun abonnement, aucune carte bancaire, aucun compte supplémentaire utilisé.
- Options pour un backend (phase 2), coûts indicatifs à vérifier : Tailscale (gratuit, privé), petit serveur virtuel
  ≈ 4–7 €/mois, Fly.io ≈ 2–3 $/mois + volume, Render (gratuit sans disque persistant, inutilisable pour le journal) ;
  domaine personnalisé ≈ 10–15 €/an. Détails et sources : `docs/architecture/APPLICATION-WEB.md` §4.

## 5. Configuration de sécurité
- Site statique : aucune route d'écriture, aucun terminal, aucun accès au système de fichiers de l'ordinateur d'Anton ;
  aucun utilisateur anonyme ne peut exécuter quoi que ce soit (il n'y a rien à exécuter).
- Aucun secret publié : la phrase et la clé privée n'existent ni en ligne ni dans le dépôt ; l'instantané est contrôlé
  par un test automatique (absence de phrase, de graine, de clé privée ; accès distant masqué ; aucune session).
- Anti-usurpation : tout acte présidentiel est revérifié dans le navigateur avec la clé publique inscrite ; un acte
  falsifié, une signature remplacée ou une ligne retirée sont signalés (testé).
- Anti-injection : textes du registre échappés à l'affichage (y compris les noms de bâtiments de la métropole) ; politique
  de sécurité du contenu en balise `meta` sur **toutes** les pages ; three.js chargé avec contrôle d'intégrité (SRI).
  Limite : `script-src 'unsafe-inline'` reste nécessaire (scripts intégrés aux pages).
- Compte GitHub (Antsvfr, administrateur du dépôt) et identité présidentielle (clé Ed25519 dérivée de la phrase) restent
  distincts : être administrateur GitHub ne donne aucun pouvoir présidentiel dans l'île.
- Limites : GitHub Pages ne permet pas d'en-têtes HTTP personnalisés ; tout le contenu est public (comme le dépôt).
- Mode local inchangé (sessions, jeton anti-CSRF, 5 essais puis blocage, accès distant derrière connexion).

## 6. Résultats des tests
Sorties brutes : `audit/preuves-brutes/2026-11-06-phase-3/`.

| Vérification | Résultat |
|---|---|
| Tests automatisés (`python3 -I -S -m unittest discover -s tests`) | **79/79** sous Python 3.13 et 3.9 (dont vérification navigateur = Python, signature forgée, clé d'ordre faible, instantané sans secret) |
| Preuves (`audit/preuves.py --claude`) | **23 PASS · 1 PARTIEL** (démarrage automatique : pas de Mac) **· 0 FAIL · 0 NOT TESTED** |
| Version en ligne (`tests/version_publiee.js` sur https://antsvfr.github.io/ile-entrepreneuriale/) | **21/21** : accueil, institutions, Résidence lecture seule (47 commandes, 0 active), vérification (79 événements, 4 documents gelés intacts), métropole, liens des bâtiments, nom officiel, **rechargement**, **nouvel appareil** (iPhone 13 et Pixel 7 émulés, sans cache ni stockage), diagnostic, mobile 390 px |
| Mode local (`./ile`) | Résidence complète (déverrouillage, accord signé), vérification locale réparée, métropole 3D : OK |
| Routes | `/`, `/residence`, `/village/`, `/batiment/<id>`, `/api/residence`, `/api/organisation`, `/api/agent/<id>` : OK ; agent inconnu → 404 ; écriture anonyme → 403 ; fichiers internes → 404 |

**Performances.** Pages légères (29 à 82 Ko transférés), prêtes en 1 à 2 s depuis Internet. La métropole 3D a été
mesurée ici **en rendu logiciel** (SwiftShader, sans carte graphique, identifié par le diagnostic) : 17 à 88 s et
≈ 1 image/s selon la charge — **ce chiffre ne dit rien d'un ordinateur réel et n'est pas extrapolé**. **Performance
sur un ordinateur réel : NON TESTÉE par moi** (aucun appareil réel accessible). Mesure en un clic, sur ton appareil :
https://antsvfr.github.io/ile-entrepreneuriale/residence/village/index.html?diagnostic=1 (affiche le temps de
préparation, les images/s et la carte graphique utilisée).

**Inspection indépendante** (agent distinct, lecture seule, sur la version `4c00ec8` alors en ligne) : aucun danger
(rien ne s'exécute, rien ne se signe, aucun secret), mais non conforme sur des points corrigés depuis : bouton
« Vérifier » qui relisait l'instantané, fraîcheur jugée au nombre de lignes, page de vérification cassée en local,
documents gelés hors du verdict, CSP partielle, injection possible par un nom de bâtiment, page de connexion en ligne,
lien mort, clé d'ordre faible acceptée (défaut ancien, sans identité réelle donc non exploité). Toutes ces corrections
sont testées (tests automatiques et 21/21 en ligne).

## 7. Commits publiés
| Commit | Contenu |
|---|---|
| [`4c00ec8`](https://github.com/Antsvfr/ile-entrepreneuriale/commit/4c00ec8bf66306c48178a300a01a6f9aabc0d06c) | version web lecture seule, vérification publique |
| [`99bc008`](https://github.com/Antsvfr/ile-entrepreneuriale/commit/99bc008e2bd96c7ea4ab6c95ba9baffd1c27f93b) | corrections de l'inspection, renommage, diagnostic, phase 3.1–3.2 (organisation) — **version vérifiée en ligne 21/21** |
| commit suivant | ce rapport, le rapport de phase 3.1–3.2 et les sorties brutes |

## 8. URL finale
https://antsvfr.github.io/ile-entrepreneuriale/ — accueil · `residence/village/index.html` (métropole) ·
`residence/village/residence.html` (Résidence) · `residence/village/verification.html` (vérification).

## 9. Maintenance
- Mettre la version web à jour après un travail de l'île : `./ile publier`, puis
  `git add residence/instantane && git commit -m "Instantané de l'île" && git push` ; GitHub Pages republie en quelques minutes.
- Tester la version en ligne : `node tests/version_publiee.js https://antsvfr.github.io/ile-entrepreneuriale/`.
- Tests et preuves : `python3 -I -S -m unittest discover -s tests` · `python3 -I -S audit/preuves.py`.
- Paramètres GitHub Pages : *Settings → Pages* (source : branche `main`, dossier racine).

## 10. Ce qui reste à faire par Anton
1. **Ouvrir l'URL depuis ton propre ordinateur et ton téléphone** — mon test « extérieur » vient d'un navigateur
   automatisé passant par Internet, pas de tes appareils.
2. **Créer ton identité présidentielle** (`./ile president`, dans Terminal) — puis `./ile publier` et push : la version
   web affichera son empreinte et vérifiera tes actes signés.
3. Protéger `main` (*Settings → Branches*).
4. Décider de la phase 2 (signature dans le navigateur + backend minimal) et de son hébergeur : nécessite ton compte et,
   selon l'option, une carte bancaire.
5. Domaine personnalisé (facultatif) : acheter un domaine, puis *Settings → Pages → Custom domain*.

## 11. Bilan
| Catégorie | Fonctionnalités |
|---|---|
| **Opérationnelles (vérifiées en ligne)** | accueil avec état réel ; métropole 3D ; navigation entre bâtiments et accès à leurs fonctions ; Résidence en consultation (projets, missions, décisions, rapports, tests, sécurité, historique, organisation, journal) ; vérification publique du journal, des signatures et des documents gelés ; organisation consultable par l'API et l'instantané ; rechargement et nouvel appareil ; mobile ; diagnostic de performance |
| **Partielles** | performance sur ordinateur réel (outil fourni, non mesurée par moi) ; données en ligne figées à la date de l'instantané (`./ile publier`) ; fiches entreprise et agent sans interface dédiée (phase 3.4) |
| **À développer** | signature présidentielle dans le navigateur + backend minimal (phase 2 de l'application web) ; bureaux des entreprises (3.4) ; missions attribuées, livrables, validation, messagerie (3.3) ; centre de contrôle (3.5) ; avatars (phase 4) |

**Verdict du déploiement : RÉUSSI pour une application publique en lecture seule** (en ligne, vérifiée 21/21 depuis
Internet, aucune donnée sensible, aucune action possible). **Pas une application interactive en ligne** : agir et
signer restent locaux, par choix de sécurité tant que la signature ne se fait pas dans le navigateur.
