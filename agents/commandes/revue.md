---
description: Revue d'un siège par son directeur : état, problèmes, missions proposées (lecture seule sur le projet)
argument-hint: <id-du-siège> (ex. rev-em) ou « toutes »
---

Revue demandée : $ARGUMENTS

Pour chaque siège concerné (« toutes » = chaque maison du registre ayant un `etat-des-lieux.md`) :

1. Lance le directeur du siège (`chef-<id>`) **en lecture seule sur le projet** avec cette consigne :
   - lis `projets/<id>/CLAUDE.md`, `etat-des-lieux.md`, `branches.md`, `journal.md`, puis le code du projet s'il est accessible (sans rien modifier) ;
   - établis l'avancement : `python3 orchestrateur/ile.py --auteur chef-<id> siege etat --siege <id> --phase "…" --resume "…" --indicateur "nom=valeur@source" …` ;
   - signale chaque problème vérifié : `… probleme signaler --siege <id> --titre "…" --gravite bloquant|majeur|mineur --source "fichier ou commande"` ;
   - propose au plus 3 missions, chacune avec critères d'acceptation vérifiables et notes 1–5 : `… mission proposer --siege <id> --titre "…" --objectif "…" --critere "…" --valeur N --urgence N --effort N --risque N --source "…" [--sensible]` (sensible = touche à `main`, à la production, à des données, à un secret ou coûte de l'argent) ;
   - si une décision revient au président, demande-la : `… decision demander --siege <id> --titre "…" --question "…" --source "…"`.
   - N'invente rien : ce que tu n'as pas vérifié n'est pas inscrit.
2. Puis, en directeur général : `python3 orchestrateur/ile.py classer`, et résume à Anton le classement (rang, score, siège, titre) en 10 lignes au plus.
3. Ne démarre aucune mission : la planification et les actions sensibles attendent la validation d'Anton (Résidence ou chat).
