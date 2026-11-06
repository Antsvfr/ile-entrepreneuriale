# Phase 3 — Société numérique : audit et architecture cible

Statut : **architecture proposée, aucune modification structurelle faite** (6 novembre 2026).

## 1. Audit — ce qui existe réellement
| Domaine | Existant | Nature |
|---|---|---|
| Persistance | `orchestrateur/registre/journal.jsonl` : ajout seul, chaîné SHA-256, 53 événements ; projections recalculées (`ile.py projeter`) ; aucune base de données | **réel** |
| Entreprises | 7 maisons + 4 institutions + 6 chantiers dans `registre.json` (le cadastre) ; une fiche par projet (`projets/<id>/`) | réel (structure), sans organisation interne |
| Organisation | `registre.json → organisation` : 5 directions, dont 3 avec agents, 2 « prévues » | déclaratif |
| Agents | 12 définitions Claude Code (`agents/definitions/`) + le Maire (session principale) ; exécutions tracées par hooks (`run.debut`/`run.fin`, 5 runs) | **réel** (moteur = Claude Code) |
| Missions | 9 missions, statuts et transitions (`STATUTS`), classement public, transitions réservées au président | **réel** |
| Identités | président : signature Ed25519 (**non créée**) ; agents : vérifiés par leur exécution ouverte (`--run`) ; Maire : déclaré | réel, à trois niveaux de preuve |
| Présence | « actif » seulement pendant un run réel (2 h max) | réel |
| Interfaces | métropole 3D, Résidence (serveur local), version publique statique en lecture seule | réel / lecture seule en ligne |
| Absent | départements, postes, hiérarchie, identité détaillée des agents, affectation, livrables liés aux missions, validation hiérarchique, messagerie, bureaux, centre de contrôle | — |
| Uniquement visuel | courriers d'ambiance de la métropole hors registre ; chantiers | décor (déjà signalé comme tel) |

## 2. Principes non négociables
1. **Une seule source de vérité** : tout fait organisationnel est un événement du journal chaîné ; tout le reste est projection.
2. **Rien de simulé** : un statut, une présence, un chiffre n'existent que s'ils découlent d'un événement réel ; sinon « non disponible ».
3. **Poste ≠ agent** : un poste créé sans agent capable d'exécuter est affiché « non pourvu », jamais peuplé de noms inventés.
4. **Autorisation côté serveur** dans `ile.py` (CLI et API passent par les mêmes contrôles), selon la fonction et la hiérarchie.
5. Le président agit par signature ; les agents par leur exécution vérifiée ; le Maire est « déclaré » (limite connue, étape 2).

## 3. Modèle (nouveaux événements, ajout seul)
| Événement | Données | Qui peut l'inscrire |
|---|---|---|
| `org.departement.cree` | entreprise, id, nom, mission, directeur (poste) | président, DG, directeur de l'entreprise |
| `org.poste.cree` | entreprise, département, id, fonction (catalogue), supérieur (poste), compétences, description | président, DG, directeur ; manager pour son équipe |
| `org.agent.cree` | id, nom, fonction, poste, définition exécutable (`agents/definitions/x.md` ou aucune), compétences, apparence (graine stable, phase 4) | président, DG, directeur |
| `org.agent.affecte` / `org.agent.suspendu` / `org.agent.reactive` | agent, poste, motif | supérieur hiérarchique ou plus haut |
| `mission.attribuee` | mission, agent, par (manager), échéance, priorité | supérieur de l'agent |
| `mission.livrable` | mission, chemin, empreinte (document gelé) | l'agent attributaire, pendant son exécution |
| `mission.validee` / `mission.correction` | mission, motif | supérieur de l'attributaire |
| `message.envoye` | de, à (agent, poste, département), sujet, texte, mission | tout agent vérifié ; historisé |
| `reunion.ouverte` / `reunion.close` | participants (avec leurs exécutions), ordre du jour, compte rendu | organisateur vérifié |

Catalogue des fonctions (niveau, permissions) : DG, directeurs (opérations, finances, technique, RH), manager de département,
chef de projet, responsable d'équipe, responsable qualité, et les métiers d'expertise (développeur front/back, architecte,
analystes, marketing, commercial, communication, juriste, auditeur, chercheur). Les permissions dépendent de la fonction
**et** de la position dans la hiérarchie (un manager ne valide que le travail de son équipe).

## 4. Statuts des agents (dérivés, jamais saisis)
`en exécution` = run ouvert (hook) · `en attente de validation` = livrable soumis non validé · `bloqué` = mission bloquée ·
`en réunion` = réunion ouverte avec son exécution active · `suspendu` = événement de suspension · `disponible` = définition
exécutable, aucun run · `hors ligne` = aucune capacité d'exécution. Chaque statut affiche sa preuve (événement source) et
sa nature : présence technique, activité effective, déclarée.

## 5. Interfaces
- Bureaux : `residence/village/entreprise.html?id=…` (accueil, bureau du directeur, managers, équipes, réunions, missions,
  tableau de bord, organigramme, annuaire, historique) et fiche agent `agent.html?id=…` ; accès depuis le panneau du bâtiment.
- Centre de contrôle : section de la Résidence (consolidation des entreprises, alertes) ; actes présidentiels signés seulement.
- Version publique : mêmes pages, lecture seule, via l'instantané.

## 6. Ce qui demande une décision d'Anton
- **Moteur d'exécution** : aujourd'hui un agent travaille quand une session Claude Code le lance. Un répartiteur qui lance
  seul les agents sur les missions attribuées serait l'« étape 3 » (exécution autonome) : jamais autorisée, consomme de
  l'usage, et repose sur un garde non validé.
- **Données réelles** : écrire au journal officiel l'organisation de départ (les 13 agents réels, sans postes inventés).
- **Confidentialité** : le dépôt est public ; messages et missions internes y seraient publics.
- Pré-requis recommandés : identité présidentielle, protection de `main`, clôture de l'étape 2.

## 7. Phases
3.1 modèle et projections (tests sur journaux temporaires) → 3.2 identités et hiérarchie → 3.3 missions, livrables,
validation, messagerie → 3.4 bureaux → 3.5 présence et centre de contrôle → 3.6 tests, audit, déploiement → 4 avatars.
Chaque phase : fonctionnalités opérationnelles, tests exécutés, limites, rapport dans `audit/rapports/`.
