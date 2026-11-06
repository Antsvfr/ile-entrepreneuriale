---
description: Faire passer un prompt devant le Conseil des Critiques et obtenir une version améliorée
argument-hint: <ton prompt>
---

Prompt soumis au Conseil :

$ARGUMENTS

1. Lance EN PARALLÈLE les sous-agents `critique-clarte`, `critique-exigence` et `critique-strategie` avec ce prompt.
2. Fusionne leurs avis en un **prompt amélioré**.
3. Affiche : le prompt amélioré, puis 3 puces « ce qui a changé et pourquoi », puis la maison qui devrait s'en charger.
4. Enregistre le procès-verbal dans `audit/conseil/proces-verbaux/<date>-<sujet-court>.md` (prompt d'origine, 3 avis, prompt final).
5. N'exécute PAS la tâche : demande à Anton s'il veut l'envoyer à la maison.
