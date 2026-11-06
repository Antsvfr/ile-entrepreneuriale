# Conseil — 2026-11-06 — Architecture de l'Entreprise des Agents

## Prompt d'origine
Sans développer : auditer le village et concevoir l'architecture complète d'une entreprise IA autonome dont Anton est président (direction générale, sièges et équipes par projet, Innovation & Business, critique et sélection, moteur de tâches, connecteurs, mémoire, résidence et tableau de bord, synchronisation 3D, roadmap). Vérifier les projets accessibles. Ne modifier aucun projet externe.

## Avis
- **Clarté** : « autonome » contredit « autorisation pour le sensible » : préciser ce qui est autonome. Moteur d'exécution, projets pilotes, plafond de coût et emplacement du livrable non précisés. Partir de l'existant (Maire → DG, maisons → sièges).
- **Exigence** : classer chaque brique en « existe / à adapter / à créer » avec le fichier qui le prouve ; matrice d'accès par projet ; roadmap avec critères de fin testables et portes d'autorisation. Pièges : organigramme sans mécanisme (agents fantômes), 3D qui invente de l'activité. Ajout : citer le mécanisme réel de chaque composant, sinon « non réalisable aujourd'hui ».
- **Stratégie** : risque de cérémonie sans fusion ; le plus utile est la prochaine action par projet (LexNote, REV-EM, UPSA sans git) ; budget 0 € : aucune autonomie payante. Raccourci : tableau de bord « prochaine action par siège ».

## Prompt final
Document d'architecture dans `architecture/ENTREPRISE-IA.md` : audit de l'existant avec preuves, matrice des projets vérifiée, rôles instanciés à la demande (pas d'agents permanents), mécanisme réel pour chaque composant, niveaux de permission N0–N3 appliqués par hook, coût 0 € d'infrastructure avec plafonds et arrêt d'urgence, pilote REV-EM. Roadmap par étapes à critère de fin testable, l'étape 0 étant le raccourci de la Stratégie.
