# Agents

- `definitions/` : un fichier par agent (Conseil des critiques, Forge, Architecte, chefs de maison). Claude Code les voit
  par le lien `.claude/agents`.
- `commandes/` : commandes `/conseil`, `/inspection`, `/nouvelle-maison`, `/revue` (lien `.claude/commands`).
Rôles et capacités : `registre.json` (directions, sièges) et la constitution `CLAUDE.md`. Les limites de rôle (critique en
lecture, directeur limité à `projets/<id>/`) sont appliquées par le garde quand Claude Code transmet le type d'agent.
