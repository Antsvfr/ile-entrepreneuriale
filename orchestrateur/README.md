# Orchestrateur

- `ile.py` : registre des opérations (missions, décisions, instructions, exécutions d'agents, approbations, artefacts).
- `registre/journal.jsonl` : le journal en ajout seul, chaîné SHA-256. **Ne jamais l'éditer à la main.** Copie à l'octet
  près du journal de l'ancien dépôt au moment de la migration ; les anciens chemins qu'il cite sont résolus par
  `ANCIENS_CHEMINS` (voir `audit/migration/`).
- `hooks/etat-ile.py` : capteurs des hooks Claude Code (SubagentStart/Stop, Stop) ; tient `etat-de-l-ile.json`.
L'orchestrateur coordonne sans aucun privilège présidentiel : il vérifie les signatures, il n'en produit pas.
