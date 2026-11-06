# Pouvoir présidentiel d'approbation et de refus (6 novembre 2026)

Livraison : commit `11aebb5` (circuit, interface, tests), puis ce rapport. Le dépôt reste **public** ; sa visibilité n'a pas
été touchée. **Aucune identité présidentielle n'a été créée**, `./ile president` n'a pas été lancé, aucune phrase n'a été
générée ni demandée, aucune signature présidentielle n'a été fabriquée. Le registre officiel n'a pas été modifié
(79 événements, empreinte du fichier contrôlée avant et après chaque étape).

**Verdict : le circuit de décision est construit, testé de bout en bout avec une identité DE TEST, et publié. Les décisions
officielles restent BLOQUÉES sur le registre réel**, comme demandé, tant que le président n'a pas créé son identité et
activé lui-même les décisions (voir §8). Les boutons ne sont pas seulement visuels : en local, ils produisent des actes
signés, vérifiés et inscrits au registre (test 26/26) ; en ligne, ils sont inactifs et le disent.

## 1. Pourquoi le président ne pouvait pas approuver ou refuser
1. **Aucune identité présidentielle n'existe** au registre. Toute décision doit être signée par la clé Ed25519 du
   président, recréée en mémoire à partir de sa phrase. Sans identité, la Résidence ne peut pas se déverrouiller, et donc
   aucun acte ne peut être signé. C'est voulu, et ce n'est pas contourné.
2. **La version web (GitHub Pages) n'a pas de serveur.** C'est un instantané en lecture seule : ni session, ni signature,
   ni écriture possible.
3. **Il n'existait pas d'objet « proposition ».** Le registre ne connaissait que trois choses :
   - des *demandes de décision* (`decision.demandee`, 4 en attente, toutes venant du Maire) : un titre et une question,
     avec trois boutons dans la Résidence locale (motif de refus facultatif, pas de confirmation) ;
   - des *missions proposées* (statuts réservés au président) ;
   - des *approbations du garde*, qui portent sur des commandes et non sur des propositions.

   Il manquait le dossier complet, le motif de refus obligatoire, la demande de modifications, la demande d'avis, la
   notification aux institutions et le suivi de l'exécution.

**Opérations distinctes, désormais séparées dans le code** :

| Opération | Où |
|---|---|
| Validation d'un livrable, ou d'une mission par un supérieur | `organisation.py` (phase 3.3) |
| Avis du Conseil, de la Forge ou d'un directeur | `proposition.avis_rendu` (un avis, jamais une décision) |
| Approbation présidentielle | `proposition.approuvee` / `refusee` / `modifications_demandees` / `rectifiee` (actes signés) |
| Publication et transmission aux institutions | dérivées de l'acte signé (destinataires inscrits dans la décision), puis accusé de réception par l'institution |

## 2. Changements effectués
- `orchestrateur/propositions.py` (nouveau) : le circuit institutionnel.
  - Une proposition est un dossier : identifiant `P-AAAAMMJJ-NNN`, titre, description, catégorie, objectif, conséquences
    attendues, coût, risques, pièces justificatives (gelées par leur empreinte SHA-256), institutions concernées, origine
    et auteur.
  - Chaque étape est un événement du registre chaîné. Il n'y a aucune autre base de données.
- `orchestrateur/ile.py` :
  - nouveaux types présidentiels (signature obligatoire) : `presidence.decisions_activees`, `proposition.approuvee`,
    `proposition.refusee`, `proposition.modifications_demandees`, `proposition.rectifiee` ;
  - les demandes de décision de l'ancien format, tranchées par le nouveau circuit, sont vues de la même façon par la
    Résidence ;
  - nouvelles commandes `ile.py proposition …` (auteurs et institutions) et `ile.py president proposition …` et
    `president activer-decisions` (président, dans un vrai terminal).
- `residence/serveur.py` :
  - `GET /api/propositions` : la boîte de réception, plus la liste exacte de ce qui bloque une décision ;
  - `POST /api/proposition` : l'acte présidentiel (§5) ;
  - instantané `propositions.json` pour la version publiée.
- `residence/village/decisions.html` et `decisions.js` (nouveaux) : **Mon bureau → Décisions → Propositions à examiner**,
  avec une politique de sécurité de contenu stricte (aucun script intégré).
  - La Résidence y renvoie : lien « Décisions », et bouton « Examiner et décider » sur chaque demande, à la place des
    anciens boutons dont le motif de refus était facultatif.
  - La page de chaque entreprise affiche « Décisions présidentielles reçues ».
- `securite/garde.py` : un sous-agent n'agit sur une proposition que sous son identité vérifiée (`--run`), jamais comme
  le Maire.
- Tests : `tests/test_propositions.py` (21 tests), un test du garde, `tests/fixture_decisions.py`, `tests/decisions.js`.
  `tests/test_version_web.py` a été renforcé : l'instantané publié ne doit jamais permettre de décider.

## 3. Fonctionnement réel des propositions
```
créée ─ soumise ─┬─ transmise pour analyse ─ avis demandés → avis rendus ─┐
                 └─ transmise au président ────────────────────────────────┴→ en attente de décision
en attente de décision ─ (président, acte signé) ─┬→ APPROUVÉE → mise en œuvre définie → exécution commencée → exécution terminée (résultats au président) → archivée
                                                  ├→ REFUSÉE (motif obligatoire) → archivée
                                                  └→ MODIFICATIONS DEMANDÉES → modifiée par l'auteur → resoumise → en attente de décision
```
- **Qui peut soumettre** :
  - un agent dont l'identité est vérifiée par son exécution (`--run`), au nom de sa seule entreprise ;
  - le Maire (directeur général, identité déclarée).

  Le président ne soumet rien à lui-même.
- **Avis** :
  - demandés par le président (acte signé) ou par le directeur général ;
  - rendus uniquement par un membre vérifié de l'institution interrogée (Conseil, Forge, entreprise) ;
  - un seul avis par demande.

  Un avis favorable **n'approuve rien**, un avis défavorable **ne refuse rien** : la proposition revient seulement dans la
  boîte du président (testé).
- **Les 4 demandes de décision réelles** (E-000002 à E-000005, du Maire) apparaissent dans la boîte, telles qu'elles ont
  été inscrites. Le président peut les approuver, les refuser ou demander un avis. Il ne peut pas demander de
  modifications, car il n'y a pas d'auteur vérifié pour les modifier.
- **Suites données** :
  - modalités de mise en œuvre fixées par le président ou le directeur général ;
  - exécution rendue par l'institution responsable (identité vérifiée) ;
  - résultats obligatoires à la fin ;
  - accusé de réception par chaque institution destinataire.

## 4. Les quatre actions présidentielles
Dans la fiche détaillée de chaque proposition :

| Action | Avant confirmation | Après confirmation (registre) |
|---|---|---|
| **Approuver** | contenu intégral, conséquences de la décision, institutions concernées ; motif et conditions facultatifs ; identifiant à recopier | `proposition.approuvee` signé : identité du décideur (clé), date, identifiant, version du dossier examinée, destinataires ; statut « Approuvée » ; transmise aux institutions ; suivi de la mise en œuvre |
| **Refuser** | idem ; **motif obligatoire** (vérifié dans la page ET sur le serveur) | `proposition.refusee` signé avec son motif ; statut « Refusée » ; archivée ; transmise aux institutions et à l'auteur |
| **Demander des modifications** | observations et modifications attendues obligatoires, échéance facultative | `proposition.modifications_demandees` signé ; statut « Modifications demandées » ; historique conservé (valeurs avant/après de chaque modification) |
| **Demander un avis** | destinataire (Conseil, Forge, n'importe quelle entreprise ou institution), question, échéance | `proposition.avis_demande` signé ; demande suivie jusqu'à la réponse |

S'y ajoutent :
- **Consulter l'historique** : toutes les étapes, avec l'auteur, son niveau de vérification et l'identifiant d'événement.
- **Filtres** : toutes, en attente de décision, en cours d'analyse, modifications demandées, approuvées, refusées,
  archivées.

Une décision prise **ne se modifie pas**. Une seconde décision est refusée par le serveur avec un message explicite. Un
acte signé forcé dans le journal est ignoré par la projection **et signalé** comme anomalie. Toute correction passe par
une **rectification** signée et motivée : un nouvel événement, l'ancien restant au registre.

La page n'affiche « Décision enregistrée au registre » qu'après deux contrôles :
- le serveur a relu l'acte dans le journal et vérifié sa signature ;
- la page a relu la proposition et y retrouve cet acte.

Dans le cas contraire, elle dit explicitement que rien n'est enregistré.

## 5. Contrôles de sécurité
- **L'autorité est vérifiée par le serveur et par la cryptographie, pas par le navigateur.** Une décision exige :
  1. une session déverrouillée par la phrase présidentielle (la clé n'existe qu'en mémoire du serveur local) ;
  2. un jeton anti-CSRF et une origine vérifiée ;
  3. l'identifiant de la proposition recopié (confirmation explicite) ;
  4. la version du dossier examinée (refusée si le dossier a changé depuis) ;
  5. l'activation préalable des décisions officielles par un acte signé du président.

  Les règles du circuit sont ensuite contrôlées sous le verrou du journal, sur l'état à jour.
- Un acte présidentiel sans signature valide de la clé en vigueur est concerné quel que soit son auteur : un agent, le
  Maire, un faux « président » déclaré, ou une clé intruse. Un tel acte est **rejeté** par la projection, et
  `ile.py verifier` déclare alors le journal non intègre. Tous ces cas sont testés.
- Sans session ou sans jeton, le serveur refuse (401 / 403).
- Le journal n'est jamais réécrit : ajout seul, vérifié par test octet par octet.
- **Version publiée** : aucune session, aucun déverrouillage, aucune écriture. Les boutons sont inactifs, la raison est
  affichée, et aucune requête autre que GET n'est envoyée (testé en ligne).
- **Dépôt public** : propositions, avis et décisions sont publics par construction (`docs/architecture/DONNEES-PUBLIQUES.md`)
  et la page le rappelle. Aucun secret n'est publié : seules la clé publique et les signatures figurent au registre.
- **Limite connue** : l'étape 2 de sécurité reste **NON VALIDÉE** (garde contournable par des commandes lisibles ; agents
  et président sous le même utilisateur système). La signature protège l'authenticité des décisions : personne ne peut en
  fabriquer une sans la phrase. En revanche, elle ne protège pas la machine elle-même. C'est pourquoi l'activation est un
  acte explicite du président, dont la déclaration signée mentionne cet état.

## 6. Tests
| Suite | Résultat |
|---|---|
| Unitaires Python 3.13 | **109/109** (87 avant cette mission, aucun supprimé ni affaibli) |
| Unitaires Python 3.9 | **109/109** |
| `tests/decisions.js`, serveur local de l'île, registre temporaire, identité DE TEST | **26/26** |
| `tests/decisions.js`, miroir de la version publiée | **9/9** |
| `tests/decisions.js`, **site public** | **9/9** |
| Mutation : copie dont les boutons sont toujours actifs | **8/9 : défaut détecté** |
| `tests/version_publiee.js`, miroir / **site public** | 21/21 / **21/21** |
| `tests/bureaux.js`, miroir / **site public** | 29/29 / **29/29** |
| `audit/preuves.py` (étapes 0–2) | 22 PASS · 1 PARTIEL · 0 FAIL · 1 NOT TESTED (inchangé) |

Les 16 points demandés (unitaires, avec le serveur HTTP, et dans le navigateur sur la fixture) :

| # | Point demandé | Résultat |
|---|---|---|
| 1 | Soumission | PASS |
| 2 | Présence dans la boîte | PASS |
| 3 | Consultation intégrale | PASS |
| 4 | Approbation signée | PASS |
| 5 | Refus | PASS |
| 6 | Motif de refus obligatoire (page et serveur) | PASS |
| 7 | Retour pour modifications, puis resoumission | PASS |
| 8 | Demande d'avis enregistrée et suivie | PASS |
| 9 | Un agent ordinaire ne décide pas | PASS |
| 10 | Le Maire ne se fait pas passer pour le président (déclaré, signature forgée, clé intruse) | PASS |
| 11 | Pas de double approbation silencieuse | PASS |
| 12 | Décision non modifiable ; rectification motivée | PASS |
| 13 | Historique complet au registre | PASS |
| 14 | Persistance après rechargement et dans un navigateur neuf | PASS |
| 15 | Les institutions concernées reçoivent la décision (et peuvent en accuser réception) | PASS |
| 16 | Suivi jusqu'à l'exécution et aux résultats | PASS |

Cas d'identité couverts :
- identité absente : aucune décision possible ; une activation signée par une clé non inscrite est rejetée ;
- phrase invalide : refusée ;
- décisions non activées : refusées ;
- activation par le Maire : rejetée ;
- double activation : refusée.

Aucun test échoué dans la version livrée. Deux relances ont été nécessaires en ligne : l'une après le blocage d'une police
Google, l'autre après des délais de connexion dépassés via le proxy. Ces relances sont passées sans modification du code.

Sorties brutes : `audit/preuves-brutes/2026-11-06-pouvoir-presidentiel/`.

## 7. Limites liées à GitHub Pages
- Pas de serveur : **aucune décision n'est possible en ligne**. Cela ne peut pas changer sans un serveur, et un serveur
  public représenterait un coût et un risque (non engagés).
- Les données en ligne sont l'instantané du dernier `./ile publier`.
- Décider se fait dans la **Résidence locale** (`./ile`, page Décisions), ou dans un vrai terminal
  (`./ile president proposition <id> approuver|refuser|modifier|avis`).

## 8. Conditions restantes pour activer les décisions officielles (toutes entre les mains du président)
1. **Créer l'identité présidentielle**, une fois, soi-même, dans un vrai terminal : `./ile president`.
2. Ouvrir la Résidence locale (`./ile`) → **Décisions** → **Déverrouiller avec ma phrase**.
3. **Activer les décisions officielles** : un acte signé, une seule fois, en connaissance de l'état de l'étape 2.
4. Ensuite, chaque proposition se décide individuellement, et chaque décision est un acte officiel signé.

Recommandé, mais non bloquant pour le mécanisme : protéger la branche `main` et clore l'étape 2.

## 9. Publication
- Commit publié : `11aebb5` sur `main` (ce rapport suit dans le commit suivant).
- URL publique testée le 6 novembre 2026 à 17:15–17:24 UTC :
  https://antsvfr.github.io/ile-entrepreneuriale/residence/village/decisions.html.
  - `tests/decisions.js` : 9/9 ;
  - `tests/version_publiee.js` : 21/21 ;
  - `tests/bureaux.js` : 29/29.
