# UPSA Sales Pilot — Bilan de la session 1 (V1)

Date : 18 octobre 2026 · Données : **100 % fictives** · Rien n’a été déployé ni poussé sur un dépôt distant.

---

## 1. Architecture

**Technologies retenues**
- Interface : React 18, TypeScript strict, Vite 6, Tailwind CSS 4, TanStack Table, TanStack Query, Recharts, icônes lucide, police Inter embarquée (aucune ressource externe).
- Serveur local : Node.js ≥ 22.13, écoute uniquement sur `127.0.0.1`.
- Base : SQLite via le module intégré `node:sqlite` (rien à compiler), migrations versionnées.
- Import : lecteur CSV maison (UTF-8 / Windows-1252, « ; », virgule décimale) et `read-excel-file` pour XLSX.
- Tests : Vitest (unitaires et intégration) et Playwright (parcours navigateur).

**Organisation des dossiers**
```
src/domain/    logique métier pure : calc/ (formules) et analysis/ (assemblage écrans)
src/server/    base SQLite, migrations, import, jeu fictif, API locale
src/client/    écrans React (features/) et composants réutilisables (components/ui)
e2e/           parcours navigateur
docs/          documentation (vision, architecture, modèle, règles, import, sécurité, roadmap, décisions)
.claude/       skills, agents et références du pack installé
```

**Modèle de données** (détail dans `docs/DATA_MODEL.md`) : 21 tables. Les principales sont pharmacies + alias, groupements + adhésions datées, classifications historisées, produits (famille exclusive, pédiatrie, codéine, remboursement, statut de nomenclature), lots d’import (SHA-256), **faits mensuels** pharmacie × produit × mois × mesure (facturé / prévisionnel), conventions, engagements, commandes, factures, visites, assortiments, nouveautés, actions trade, objectifs et réglages.

**Décisions importantes** (détail dans `docs/DECISIONS.md`)
- Tous les calculs sont faits une seule fois dans `src/domain`. L’interface ne recalcule rien, ce qui garantit la cohérence entre écrans.
- Une valeur absente reste absente : le type `Maybe` porte toujours le motif (« pas encore importé », « non calculable », « exercice non ouvert »…), jamais 0.
- La taxonomie est exclusive. Le paracétamol non remboursé est affiché « dont » et n’est jamais additionné.
- Un prévisionnel est automatiquement écarté dès qu’un facturé existe sur la même clé.
- La classification ACP / stratégie est manuelle et historisée. Le moteur de règles est prêt, mais aucune règle UPSA n’est inventée.
- Les seuils de priorités sont paramétrables et présentés comme des valeurs de démonstration.
- La date de référence de la démo est fixée au 18/10/2026 (réglable).

## 2. Développement effectué

**Modules créés** : moteur de calcul (volumes, objectifs, CA, engagements, visites, commandes, assortiment, classification, priorités, périodes), couche d’analyse (tableau de bord, fiche, performance par famille), base et migrations, jeu fictif déterministe, pipeline d’import, API locale sécurisée, interface complète.

**Écrans fonctionnels**
| Écran | Contenu |
|---|---|
| Tableau de bord | CA facturé / prévisionnel / estimé 2026 vs objectif, avancement, CA mensuel, répartition par famille, restes à faire par famille, rendez-vous et couverture du plan de visites, priorités |
| Mes pharmacies | 30 pharmacies, recherche, filtres (ACP, stratégie, groupement, RDV) conservés dans l’URL, tri, contacts, dernière visite, prochain RDV, lien vers la fiche |
| Fiche pharmacie | Opérationnels : **Vue d’ensemble** (identification, contacts, groupement, classification manuelle avec historique), **Paracétamol** (2025/2026/2027, base, scénarios +3/+6 %, engagements), **OTC** (par gamme et consolidé), **Conventions et engagements**, **Visites et RDV**. Assortiments, Commandes et reliquats, Nouveautés et Plan trade sont des aperçus en lecture seule, marqués « non encore disponible » |
| Performance commerciale | Par famille : objectif, facturé, prévisionnel, restes, évolution, contribution de chaque pharmacie (somme = total secteur vérifiée) |
| Groupements | Liste et adhérents |
| Visites et rendez-vous | Agenda des pharmacies trié par prochain RDV, pharmacies à contacter (lecture seule : la saisie arrive plus tard) |
| Plan d’action | Priorités explicables, triées par gravité |
| Centre d’importation | Parcours en 5 étapes et historique des lots |
| Paramètres métier | Seuils, activation et gravité des 9 règles de priorité |
| Assortiments, Lancements et DN | Rubriques annoncées « bientôt », sans fausse donnée |

**Calculs disponibles**
- Facturé + prévisionnel sans double comptage.
- Base 2026 marquée provisoire.
- 2027 : facturé « exercice non ouvert ».
- Objectifs +3 % et +6 %.
- Restes à facturer et restes estimés, avec états atteint / dépassé / non calculable.
- Taux protégés contre la division par zéro.
- Évolutions sur les mêmes mois, DN en points.
- Périmètre paracétamol hors pédiatrie et hors codéine, appliqué à toutes les périodes.
- Agrégats par gamme et secteur.
- Couverture des visites et taux de pharmacies avec RDV.
- Reliquats.
- 9 règles de priorité.

**Importation disponible** : CSV et XLSX au format fictif « ventes sell-in ».
- Le parcours enchaîne la sélection, l’aperçu, la correspondance des colonnes, le contrôle ligne par ligne et l’enregistrement tout ou rien, puis recalcule les indicateurs.
- Un fichier identique est refusé. Un fichier de même nom au contenu différent est traité comme une nouvelle version, avec un remplacement explicite qui conserve l’historique.
- Un PDF est reconnu mais pas lu (prévu en phase 4).

## 3. Skills et agents

**Détectés** : pack installé depuis `upsa-pack` avec `installer.py`. Il contient 27 skills, 4 agents (business-rules-auditor, commercial-data-architect, premium-ui-designer, security-quality-reviewer) et 3 références (règles métier, contrats de sources, tests critiques). Le contexte `CONTEXTE_CLAUDE_A_FUSIONNER.md` a été fusionné dans le nouveau `CLAUDE.md`. Aucun `CLAUDE.md` préexistant n’a été écrasé.

**Utilisés comme guides** : pharma-import, data-quality, client-identity, client-360, client-segmentation, sell-in-analysis, volume-gap, growth-scenarios, commitment-tracker, convention-tracker, commercial-performance, visit-coverage, delivery-backorder, assortment-tracker, opportunity-scoring, action-plan et data-security. Les 15 tests critiques de `TESTS_CRITIQUES.md` sont tous couverts par des tests automatisés. Les consignes des 4 agents ont servi de grille de relecture. Aucun audit délégué séparé n’a été lancé.

**Correction effectuée** (minimale, seulement dans la copie installée du projet ; `upsa-pack` n’a pas été modifié) :
- Le skill `ubik-import` et `CONTRATS_SOURCES.md` regroupaient « Y2OBIC / Yubik / Ubik » comme une seule source. Le prompt fondateur interdit de confondre Y2OBIC avec un outil au nom proche.
- La description, la ligne de référence et une règle explicite ont donc été corrigées.
- Le nom du dossier du skill (`ubik-import`) a été conservé pour ne pas recréer le skill. Il pourra être renommé si tu le souhaites.

**Aucune autre incohérence bloquante** n’a été trouvée entre le contexte métier et les skills.

## 4. Tests

**Exécutés** (dernière exécution complète en fin de session) :
- `npm run typecheck` : OK (TypeScript strict).
- `npm test` : **54 / 54 réussis** sur 5 fichiers.
  - Moteur de calcul : 29 tests (CA, double comptage, volumes, exclusions, +3/+6 %, engagements, données manquantes, division par zéro, évolutions, DN, visites, reliquats, assortiment, classification, conventions, priorités).
  - Formats français et sécurité des fichiers.
  - API (cohérence entre écrans, fiche, liste, classification, réglages, protection de l’hôte).
  - Import réel (aperçu, contrôle, enregistrement, réimport refusé, nouvelle version, anomalies, XLSX multi-feuilles, PDF, homonymes non fusionnés).
  - Persistance SQLite après fermeture.
  - Absence de connexion externe.
- `npm run test:e2e` : **4 / 4 réussis** dans un vrai Chromium.
  - Navigation dans tous les écrans sans erreur console.
  - Recherche dans la liste et ouverture d’une fiche.
  - Onglets de la fiche, y compris les onglets non disponibles.
  - Import CSV complet dans l’interface : indicateurs recalculés, historique persistant après rechargement, doublon signalé.
- `npm audit` : 0 vulnérabilité.

**Échecs** : aucun à la dernière exécution.

**Non encore testé**
- Import XLSX via l’interface (testé seulement via l’API).
- Installation sur Windows ou macOS (testée sous Linux uniquement).
- Volumétrie réelle (au-delà de 30 pharmacies).
- Affichage sur petit écran.
- Audit d’accessibilité complet.
- Données réelles : volontairement exclues.

## 5. Utilisation

**Installation et lancement** (Node.js 22.13 ou plus récent requis) :
```bash
cd upsa-sales-pilot
npm install
npm run dev
```
→ ouvrir **http://127.0.0.1:5173** (l’API locale tourne sur 127.0.0.1:5174).

Version « un seul processus » : `npm start` → **http://127.0.0.1:4173**.

Autres commandes : `npm test`, `npm run test:e2e` (première fois sur un poste neuf : `npx playwright install chromium`), `npm run db:reset` (repart du jeu fictif), `npm run typecheck`.

**Découvrir le jeu fictif**
1. Tableau de bord : survoler les ⓘ pour voir la source, la période et la règle de chaque chiffre.
2. Mes pharmacies : chercher « Tilleuls », filtrer par ACP ou par « sans RDV ».
3. Ouvrir *Pharmacie des Tilleuls* (PH-001) et parcourir les onglets. Dans Vue d’ensemble, essayer la classification manuelle.
4. Performance commerciale : changer de famille et vérifier que la somme des pharmacies égale le total.
5. Paramètres métier : modifier un seuil et voir le plan d’action changer.

**Tester une importation**
1. Centre d’importation → Choisir un fichier → `src/client/public/exemples/sellin-octobre-2026-fictif.csv`. Il est aussi téléchargeable depuis l’écran.
2. Définir les correspondances, puis choisir la mesure « Facturé (réalisé) » et cocher la confirmation des unités.
3. Contrôler le fichier : 75 lignes, 0 anomalie bloquante. Puis Valider et enregistrer.
4. Revenir au tableau de bord : le facturé augmente et le prévisionnel d’octobre concerné disparaît.
5. Réimporter le même fichier : « Fichier déjà importé ». Essayer aussi `sellin-anomalies-fictif.csv`, refusé avec les anomalies détaillées, et le `.xlsx`, qui permet le choix de la feuille.
6. `npm run db:reset` pour revenir à l’état initial.

## 6. Suite

**Terminé** : phase 1 complète (fondations, données fictives, tableau de bord, clients, fiche V1, moteur de calcul, import initial, documentation).

**Restant à développer**
- Onglets Assortiments, Commandes et reliquats, Nouveautés et Plan trade, en version complète.
- Saisie des visites et comptes rendus.
- Édition des conventions et engagements.
- Groupements et plans trade (phase 3).
- Imports R sur O, sell-out, assortiment, Y2OBIC et PDF (phase 4).
- DN de lancement (phase 6).
- Préparation de visite et recommandations (phase 7).
- Exports CSV, XLSX et PDF.
- Sauvegarde locale.

**Points à me confirmer** (détail dans `docs/BUSINESS_RULES.md`)
1. Le CA paracétamol couvre-t-il toute la famille ou seulement le périmètre hors pédiatrie et hors codéine ?
2. La base 2026 est-elle provisoire (prévisionnel des derniers mois) ou uniquement le facturé au 31/12 ?
3. Les engagements sont-ils jugés sur le facturé, le livré ou le commandé ?
4. Quels seuils de priorités retenir ?
5. Quels sont les critères ACP et défendre / maintenir / construire ?
6. Quelle est la nomenclature OTC définitive ?

**Trois prochaines priorités**
1. Obtenir un **modèle fictif ou anonymisé** de l’export R sur O, puis l’adaptateur d’import correspondant.
2. Compléter la fiche pharmacie (phase 2) : saisie des visites et comptes rendus, édition des conventions et engagements, onglet Assortiments.
3. Trancher les points à confirmer ci-dessus pour figer les calculs.

**Prochain chantier proposé** : *Phase 2 — Fiche pharmacie complète.* Elle comprend la saisie des visites et RDV, l’édition des conventions et engagements avec preuve, l’onglet Assortiments opérationnel (matrice attendue, statuts oui / non / à confirmer) et l’onglet Commandes et reliquats. En parallèle, préparer l’adaptateur R sur O dès réception d’un exemple fictif.
