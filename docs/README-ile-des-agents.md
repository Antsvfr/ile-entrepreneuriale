# Île des Agents

Un village d'agents Claude Code, avec sa hiérarchie et sa carte en 3D.

## Démarrer
1. Dézippe le dossier, ouvre un terminal dedans.
2. `git init` (conseillé : la Forge peut alors annuler une réparation ratée).
3. `claude` — la session devient le Maire (voir `CLAUDE.md`).
4. Essaie : `/conseil fais-moi un plan pour l'entretien du BDE`

## Voir l'île en 3D
Depuis la racine : `python3 -m http.server 8000`, puis ouvre http://localhost:8000/village/
Le village lit `registre.json` : chaque maison ajoutée par l'Architecte y apparaît.

## Qui est qui
| Bâtiment | Agent | Rôle |
|---|---|---|
| Mairie | session principale | reçoit, route, synthétise |
| Conseil (3 tours) | critique-clarte / -exigence / -strategie | améliorent chaque prompt |
| Maisons | chef-<maison> | font le travail, chacun dans son dossier |
| Forge | forgeron + `audit/inspection.sh` + hook Stop | vérifie et répare |
| Atelier (invisible) | architecte | construit de nouvelles maisons |
