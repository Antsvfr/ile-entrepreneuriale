# Séparation des privilèges — architecture préparée, PAS encore en place

État au 6 novembre 2026 : l'étape 2 est **NON VALIDÉE**. Les agents (Claude Code) tournent sous le même utilisateur
système que le président : tout fichier que le président peut modifier, un agent peut le modifier, et le garde
(`securite/garde.py`) — qui lit des commandes — peut être contourné par des commandes lisibles (voir
`docs/architecture/ETAPES-2.md`, `audit/rapports/2026-11-06-finalisation-etape-2.md`). Ce document décrit la cible ;
**rien ici n'a été appliqué** (aucun utilisateur créé, aucune permission changée).

## Les quatre rôles

| Rôle | Ce qu'il possède | Ce qu'il ne doit jamais pouvoir faire | Dossiers |
|---|---|---|---|
| **Présidence** (Anton) | la phrase (dans sa tête), la clé dérivée en mémoire le temps d'un acte, les garde-fous | — | `presidence/`, `securite/` (propriétaire) |
| **Garde** | des contrôles exécutés avant chaque action d'agent ; code et réglages en lecture seule pour les agents | être modifié, désactivé ou contourné par un agent | `securite/`, `.claude/settings.json` |
| **Orchestrateur** | le registre (journal en ajout seul), les capteurs, l'état de l'île | signer un acte présidentiel ; réécrire le journal ; modifier un garde-fou | `orchestrateur/` |
| **Agents** | leur maison (`projets/<id>/`), les procès-verbaux (`audit/conseil/`), des copies de travail | lire un secret, écrire hors de leur périmètre, pousser sur `main`, toucher aux garde-fous | `projets/`, `audit/conseil/` |

## Ce que la séparation demandera (chaque point exige une autorisation distincte du président)

1. **Un utilisateur système dédié aux agents** (ex. `ile-agents` sur le Mac), qui lance Claude Code. Le président garde
   son propre compte.
2. **Propriété des garde-fous** : `securite/`, `presidence/`, `orchestrateur/ile.py`, `orchestrateur/hooks/`,
   `residence/serveur.py`, `tests/`, `audit/preuves.py`, `.claude/settings.json`, le lanceur `ile` appartiennent au
   compte du président, en lecture seule pour `ile-agents`. Le journal : écriture par ajout seulement, via un
   processus de l'orchestrateur (ou le président), jamais par le compte des agents.
3. **Interpréteur hors de portée** : les hooks appellent `/usr/bin/python3` (système, non modifiable par les agents).
4. **Protection de branche GitHub sur `main`** (REV-EM, LexNote, ile-entrepreneuriale) : la seule barrière contre un
   push qui tient même si tout le reste tombe.
5. **Secrets** : hors du dépôt, lisibles par le seul compte du président.

## Ce qui est déjà vrai aujourd'hui
- Aucun acte présidentiel ne peut être fabriqué sans la phrase (signatures Ed25519 vérifiées à chaque projection).
- Les modules de l'île sont chargés par leur chemin exact (`securite/confinement.py`) et les points d'entrée sont lancés
  en `python3 -I -S` : un module Python planté n'est pas exécuté par les processus privilégiés.
- Les chemins des garde-fous sont centralisés dans `securite/garde.py` (`FICHIERS_GARDE`, `DOSSIERS_PRIVILEGIES`),
  ce qui permettra d'en dériver les permissions système.
