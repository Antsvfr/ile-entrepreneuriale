# Conseil — 2026-11-05 — Village reflétant l'activité réelle

## Prompt d'origine
Que le village 3D reflète l'activité réelle des agents : `etat-de-l-ile.json` mis à jour à chaque étape, hook qui l'écrit au début et à la fin des sous-agents (sans casser le hook Stop de la Forge), village qui le relit toutes les 3 s (fenêtres, fumée, vrai trajet du messager, 5 dernières entrées du journal), et `serveur.py`. Ne pas toucher `maisons/`.

## Avis
- **Clarté** : quel journal ? D'où viennent maison et sujet, puisque le hook ne connaît que le nom de l'agent ? Un fichier illisible compte-t-il comme absent ? Il faut un schéma JSON, l'heure en ISO 8601 et un port pour le serveur.
- **Exigence** : déduire l'étape du type d'agent ; écrire de façon atomique (les 3 critiques démarrent en parallèle) ; vérifier de bout en bout. Pièges : un sujet inventé, des chemins relatifs cassés. Ajout : un script de simulation du circuit.
- **Stratégie** : le vrai but est la confiance dans le circuit. L'île est neuve, donc il faut faire vite. Raccourci : SubagentStart/SubagentStop + correspondance des noms d'agents, et un sujet optionnel fourni par le Maire.

## Prompt final
Hooks SubagentStart/SubagentStop (et Stop, en plus de la Forge) → `.claude/hooks/etat-ile.py` écrit `etat-de-l-ile.json` {maison, sujet, etape, agents_actifs, maj ISO} de façon atomique et verrouillée. L'étape vient du nom de l'agent (`critique-*`, `chef-<id>` via le registre, `forgeron`) et le sujet vient du Maire (`etat-ile.py sujet "…"`). Le village relit le fichier toutes les 3 s via `serveur.py` (depuis la racine), lit le journal.md de la maison ouverte, et retombe sur le comportement actuel si le fichier est absent ou invalide. Commande `etat-ile.py simuler <maison>` pour tester.
