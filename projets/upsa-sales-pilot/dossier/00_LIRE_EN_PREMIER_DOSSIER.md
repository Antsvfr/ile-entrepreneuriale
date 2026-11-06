# Dossier de reprise — UPSA Sales Pilot

> **À l'attention de Claude.** Ce document résume tout le projet UPSA Sales Pilot à la date du 6 novembre 2026. Lis-le en entier avant de répondre. Il contient le contexte métier, l'architecture, les fonctionnalités, les règles de calcul, les règles absolues à respecter, l'état actuel et les questions encore ouvertes. Réponds en français.
>
> Ce dossier ne contient **aucune donnée commerciale réelle** (aucun nom de pharmacie réelle, aucun chiffre de vente). Tous les exemples cités sont fictifs.

---

## 1. En une phrase

UPSA Sales Pilot est une **application web locale** (React + TypeScript + Node + SQLite) qui sert de centre de pilotage commercial quotidien à une commerciale du laboratoire UPSA (15 ans d'expérience) qui reprend un nouveau secteur de pharmacies : fiche client 360°, paracétamol 2026/2027, gammes OTC, conventions et engagements, visites et RDV, groupements et plans trade, DN des nouveautés, plan d'action, exports, et depuis octobre 2026 l'import automatique du fichier « X20 Cockpit Territoire ».

## 2. Contexte et historique

| Date | Étape |
|---|---|
| Sessions 1 et 2 (avant oct. 2026) | Développement initial dans un autre environnement (Windows), à partir du **prompt fondateur v3.0**. Phases 1, 2, 3, 5, 6, 7 faites, phase 8 partielle, phase 4 en attente. 77 tests unitaires/API + 6 parcours navigateur au vert. |
| 19 oct. 2026 | Transfert du projet sur le **Mac** de l'utilisateur (archive `UPSA-Sales-Pilot-transfert.zip`). Installation, tests (typecheck OK, 77/77, 6/6), lancement sur `http://127.0.0.1:4173`. **L'archive ne contenait aucune base de données réelle** : la base a été recréée avec le jeu fictif (30 pharmacies). |
| 22 oct. 2026 | Intégration du **connecteur X20 Cockpit Territoire** (fichier Excel de 109 colonnes, une ligne par pharmacie). Séparation des espaces **réel** et **démo**. 99/99 tests et 7/7 parcours au vert, uniquement sur données fictives. |
| 6 nov. 2026 | Rédaction de ce dossier. |

**Où vit le code aujourd'hui :** sur le Mac de l'utilisateur, dans
`~/Downloads/upsa copilot/UPSA-Sales-Pilot-transfert/1-projet/upsa-sales-pilot`

⚠ L'archive zip du projet date du 19 octobre et **ne contient pas le travail X20** du 22 octobre (migration 3, `src/domain/cockpit/`, écrans Cockpit, script `start:demo`, etc.). La version à jour est uniquement sur le Mac. Pour toute modification de code, il faut travailler sur ce dossier (via Claude Code sur le Mac), pas sur le zip.

## 3. Règles absolues (à respecter dans toute réponse ou modification)

Ces règles viennent de l'utilisateur et du prompt fondateur. Elles priment sur tout le reste.

1. **Ne jamais réinitialiser la base** pour corriger une erreur (pas de `npm run db:reset` sur l'espace réel) sans autorisation explicite.
2. **Ne jamais supprimer** de données, de sauvegardes (`data/backups/`, `data/<espace>/backups/`), de skills ni de fichier important.
3. **Avant toute migration de base** : sauvegarde vérifiée, puis présentation des changements prévus et accord de l'utilisateur.
4. **Pas de push GitHub, pas de déploiement, pas de service cloud**, pas de télémétrie, pas de ressource tierce chargée par l'interface.
5. **Aucune donnée commerciale réelle envoyée à un service externe.** Les tests, le jeu de démo et les fichiers d'exemple restent 100 % fictifs.
6. **Données réelles et Claude :** l'autorisation de l'entreprise pour que Claude lise les valeurs réelles du cockpit **n'a jamais été confirmée**. Tant qu'elle ne l'est pas, Claude ne lit que les en-têtes et des comptages, et c'est l'utilisateur qui lance l'import réel dans l'application.
7. **Ne rien inventer** : ni les critères ACP1/ACP2, ni défendre/maintenir/construire, ni la nomenclature produits, ni les formats « R sur O » ou « Y2OBIC » (qui n'est assimilé à aucun outil au nom proche), ni les termes contractuels.
8. **Une donnée absente n'est jamais remplacée par 0.** Une donnée non confirmée n'est jamais présentée comme validée. Une prévision n'est jamais assimilée à du facturé.
9. **Pas de double comptage du CA** (paracétamol non remboursé = « dont », jamais additionné ; les périmètres de CA X20 ne s'additionnent pas).
10. **Ne jamais présenter comme opérationnelle une fonction non développée** (rubriques marquées « non encore disponible »).
11. **Ne pas recréer le projet ni modifier l'architecture inutilement.** Inspecter avant de modifier, préserver les fonctionnalités testées, ne revendiquer que les tests réellement exécutés.

## 4. Lancer, arrêter, tester

Prérequis : **Node.js ≥ 22.13** (utilise le module intégré `node:sqlite`, aucune dépendance native). Sur le Mac : Node 26.12.0 (arm64), npm 11.20.0, 0 vulnérabilité npm.

```bash
cd ~/Downloads/upsa\ copilot/UPSA-Sales-Pilot-transfert/1-projet/upsa-sales-pilot
npm install            # une fois
npm start              # espace RÉEL : build + http://127.0.0.1:4173  (données dans data/reel/)
npm run start:demo     # espace DÉMO (jeu fictif) : port 4174
```

Arrêter : Ctrl+C dans le Terminal, ou
```bash
pkill -f "src/server/index.ts --serve-static"
```

| Commande | Rôle |
|---|---|
| `npm run dev` | Développement (UI 5173, API 5174) |
| `npm test` | Tests unitaires et API (Vitest) |
| `npm run test:e2e` | Parcours navigateur (Playwright, base en mémoire) |
| `npm run typecheck` | TypeScript strict |
| `npm run test:all` | Les trois |
| `npm run samples` / `npm run samples:x20` | Régénère les fichiers d'exemple fictifs (Python 3 + openpyxl) |
| `npm run db:reset` | ⚠ Supprime la base et recharge le jeu fictif. **Interdit sur l'espace réel sans accord.** |

L'adresse locale ne marche que sur le Mac lui-même (serveur lié à 127.0.0.1).

## 5. Architecture technique

| Couche | Choix |
|---|---|
| UI | React 18, TypeScript strict, Vite 6, Tailwind CSS v4, react-router 7, TanStack Query 5 / Table 8, Recharts 2, lucide-react, police Inter embarquée |
| Serveur | Node `node:http` + tsx, sans framework, lié à 127.0.0.1 |
| Base | SQLite via `node:sqlite`, mode WAL, migrations versionnées |
| Import | parseur CSV maison (UTF-8 / Windows-1252), `read-excel-file` pour XLSX |
| Export | `write-excel-file` (XLSX) et CSV (UTF-8 BOM, « ; », virgule décimale) |
| Tests | Vitest 5, Playwright 1.56 |

Organisation du code :
```
src/
  domain/          logique métier PURE (aucun accès disque/réseau)
    maybe.ts       valeur connue | absente avec motif
    calc/          formules unitaires (volumes, objectifs, CA, engagements, visites, DN…)
    analysis/      assemblage pour les écrans (dashboard, fiche, famille, segmentation…)
    cockpit/       calculs X20 (RAF, familles, groupements) — ajouté le 22/10
  server/
    db/            connexion, migrations.ts (on ajoute une version, on ne modifie jamais une migration publiée), repository
    import/        lecture, parseurs FR, mapping, pipeline aperçu/contrôle/commit
    routes/        écritures validées + journal audit_log, analyses, exports, sauvegardes
    export/        CSV / XLSX
    seed/demo.ts   jeu fictif déterministe
  client/          React : features/<écran>, components/ui réutilisables
e2e/               parcours Playwright
docs/              documentation détaillée
.claude/           26 skills, 4 agents, 3 références métier
```

Principes clés :
- **Toute formule vit une seule fois dans `src/domain/`.** L'API et l'UI ne recalculent rien ; le client ne fait que du formatage.
- Les valeurs voyagent avec leur **provenance** (source, période, règle) et sous forme `Maybe` : `{known: true, value}` ou `{known: false, reason}` avec `reason ∈ non_renseigne | pas_encore_importe | non_applicable | a_confirmer | conflictuel | perimetre_incomplet | exercice_non_ouvert | non_calculable`.
- Date de référence paramétrable (`reference_date`, surchargeable par `UPSA_TODAY`) ; la démo est figée au 18/10/2026.

## 6. Fonctionnalités

### 6.1 Écrans
1. **Tableau de bord** : pilotage cockpit X20 et alertes cliquables (en tête), CA facturé / prévisionnel / estimé 2026, objectif, restes à faire par famille, RDV, priorités. Info-bulle de provenance (ⓘ) sur chaque chiffre.
2. **Mes pharmacies** : recherche, filtres ACP / stratégie / groupement / RDV.
3. **Fiche pharmacie** (onglets) : Vue d'ensemble, Paracétamol, OTC, Assortiments, Conventions et engagements, Commandes et reliquats, Visites et RDV, Nouveautés, Plan trade, Journal, **Cockpit X20**. Saisies : coordonnées, RDV (planifier, déplacer, annuler, confirmer), comptes rendus, tâches, objectif de visites, conventions, engagements, constats d'assortiment (historisés), référencements, actions trade. Bouton **Préparer le rendez-vous** (fiche imprimable).
4. **Groupements** : fiche par groupement (accords avec preuve, adhérents et anciens adhérents, plan trade mensuel, performance par famille), hiérarchie père → fils depuis X20.
5. **Cockpit X20** (menu) : 5 onglets — synthèse secteur, pharmacies filtrables, groupements père/fils, les 109 colonnes complètes, imports et conflits.
6. **Performance commerciale** : par famille et par segment (ACP, stratégie, groupement ; somme des segments = total secteur, testé).
7. **Assortiments** (matrice pharmacie × référence) et **Lancements et DN** (DN de référencement, variation en points, évolution mensuelle, DN par groupement).
8. **Visites / agenda**, **Plan d'action** (priorités, opportunités, tâches).
9. **Centre d'importation** : CSV/XLSX sell-in (mapping manuel) et X20 (reconnu automatiquement).
10. **Paramètres métier** : seuils des priorités, pondérations des opportunités (valeurs de démonstration), objectifs secteur, sauvegardes, exports, journal des saisies.

### 6.2 Exports et sauvegardes
- Exports CSV et Excel (pharmacies, priorités, opportunités, performance, segmentations, assortiment, DN, visites) calculés comme à l'écran ; injection de formules neutralisée ; valeurs absentes écrites en clair avec leur motif.
- Sauvegarde en un clic (`VACUUM INTO`) dans le dossier `backups/` de l'espace. Restauration **manuelle** (application arrêtée, remplacement du fichier).

### 6.3 Non disponible (volontairement)
- **Phase 4** : imports R sur O, sell-out, Y2OBIC et lecture des PDF. Formats inconnus, il faut des exemples fictifs ou anonymisés avec les vrais noms de colonnes.
- DN de vente (sell-out), qui dépend de la phase 4.
- Restauration depuis l'interface, sauvegarde automatique, chiffrement applicatif, code d'accès.

## 7. Connecteur X20 Cockpit Territoire (ajouté le 22/10/2026)

Fichier source : `X20_Cockpit_Territoire_2026.xlsx` — 1 onglet, **109 colonnes**, une ligne par pharmacie. Le fichier réel de l'utilisateur couvre environ 150 pharmacies ; les 150 Codes SAP y sont uniques et les 109 colonnes sont reconnues (vérifié par comptage, sans lecture des valeurs).

### Reconnaissance et import
- Reconnu automatiquement par ses en-têtes (accents, casse, ordre tolérés) : présence du **Code SAP** et d'au moins 90 % des 109 colonnes. **Aucune correspondance de colonnes à saisir.**
- Aperçu : créations, mises à jour, différences, conflits, valeurs à vérifier, contrôles de cohérence. **Rien n'est écrit avant la validation explicite** (case « J'ai vérifié l'aperçu » puis « Valider et importer »).
- Avant l'écriture : sauvegarde `data/<espace>/backups/avant-import-x20-*.db` avec contrôle d'intégrité.
- Réimport du même fichier (même SHA-256) refusé ; une nouvelle version montre les différences.

### Modèle de données (migration 3, additive)
| Table / colonne | Rôle |
|---|---|
| `cockpit_imports` | Un lot par fichier validé (SHA-256, en-têtes, rapport, sauvegarde préalable, statut actif/remplacé) |
| `cockpit_rows` | Les 109 valeurs brutes par pharmacie et par import (`values_json`) ; historique complet |
| `source_conflicts` | Écarts entre saisie de l'application et valeur importée (ouvert / résolu) |
| `groupements.parent_id`, `level`, `source` | Hiérarchie père → fils |
| `pharmacy_aliases` (`sap`, `cip_origine`, `cip_actif`) | Le **Code SAP** est l'identifiant (doublon ou SAP vide = import bloqué) ; les deux CIP sont conservés |

Les écrans calculent tout à la lecture (`src/domain/cockpit/`) à partir des valeurs brutes : aucune valeur source n'est écrasée.

### Priorité des sources
- Identité (nom, CP, ville, téléphone, e-mail, titulaire) : mise à jour seulement si la valeur actuelle est vide ou identique au cockpit précédent ; sinon la saisie de l'application est conservée et un conflit est créé.
- Une valeur absente du fichier n'efface jamais une donnée existante.
- Groupement : un changement clôt l'ancien rattachement et en ouvre un nouveau ; un rattachement saisi à la main n'est pas modifié (conflit).
- Visites : la dernière visite crée une visite réalisée (source `x20`) si aucune n'existe à cette date ; la prochaine visite crée ou déplace un RDV `x20`. Un RDV saisi ou déplacé à la main n'est jamais déplacé (conflit).
- ACP / stratégie : la décision saisie dans l'application prime ; à défaut, ACP lu dans Ciblage et stratégie depuis Segmentation (Build → construire, Maintain → maintenir, Defend → défendre ; Observe et Gain conservés tels quels).
- Conv 2026, remises, engagements : affichés comme données déclaratives ; **aucune convention, remise ni engagement n'est créé automatiquement**.

### Calculs X20
| Indicateur | Définition | Concordance avec le fichier |
|---|---|---|
| RAF paracétamol ISO / +3 % / +6 % | Vol 2025 × (1 + p) − Vol 2026 Fact+Prev | 150/150 |
| RAF Sommeil ISO / +5 % / +10 % | idem sur Sommeil | 149/150 |
| RAF Vitalité ISO / +5 % / +10 % | idem sur Vitalité | 145/150 |
| RAF +15 % Vitalité (FOT) | **non documenté**, affiché sans recalcul | — |
| RAF OTC S1 / FY +8 % / +12 % | CA 2025 × (1 + p) − CA 2026 Fact+Prev (S1 et FY jamais mélangés) | 144/150 (S1), 146/150 (FY) |
| Avancement | Fact+Prev / objectif | — |
| Prévisionnel restant | Fact+Prev − Fact | — |

L'écran affiche toujours la valeur du fichier, le recalcul, l'écart et un statut (concorde, arrondi ≤ 1, écart, non documenté).

Périmètres de CA (ne jamais additionner) : `CA Paracétamol + Autres OTX` inclut `CA Paracétamol OTX + OTC` ; `CA OTC` = `CA OTC FY (Fact+Prev)` ; la somme des 8 familles ne reconstitue le CA OTC que sur environ 2/3 des lignes ; **CA global non calculé** tant que son périmètre n'est pas défini.

Qualité : la valeur `132` dans un champ texte, catégorie ou date est signalée « à vérifier » (jamais interprétée) ; dans une colonne quantitative elle reste valide. Négatifs conservés (RAF négatif = objectif dépassé). Dates `JJ/MM/AAAA` normalisées. Aucune donnée 2027 fabriquée.

Tests : `src/domain/cockpit/x20.test.ts`, `src/server/__tests__/cockpit.test.ts`, parcours e2e « cockpit X20 fictif ». Exemple 100 % fictif : `src/client/public/exemples/x20-cockpit-fictif.xlsx`.

## 8. Espaces réel et démo

| | Espace réel | Espace démo |
|---|---|---|
| Commande | `npm start` | `npm run start:demo` |
| Port | 4173 | 4174 |
| Données | `data/reel/` (jamais de jeu fictif) | jeu fictif : 30 pharmacies, 5 groupements, 21 références `DEMO-*` |

Le jeu fictif est déterministe (graine 20261018) : villes « -Démo », CP 99xxx, e-mails `@exemple.test`. Exemple : « Pharmacie des Tilleuls » (PH-001). Cas de test intégrés : valeur volontairement absente (PH-012, DEMO-VIT-02, mai 2026) et changement de groupement (PH-006 au 01/04/2026).

Au 22/10, l'espace réel était **vide** ; c'est l'utilisateur qui doit y déposer le fichier X20 via le Centre d'importation. On ne sait pas à ce jour si cet import a été fait.

## 9. Règles de calcul générales (hors X20)

Aucune n'est une règle officielle UPSA ; les points ⚠ sont à confirmer.

- **Familles exclusives** : PARA, VITALITE, SOMMEIL, HYDRAPHYSE, CERELYS (libellés OTC provisoires), AUTRE. Paracétamol non remboursé = sous-ensemble de PARA.
- **Paracétamol hors pédiatrie et hors codéine** sur nomenclature vérifiée ; attribut inconnu → référence exclue. ⚠ Le CA paracétamol affiché couvre toute la famille.
- **Grain** : pharmacie × produit × mois × mesure (`facture` | `previsionnel`). Total estimé = facturé + prévisionnel sur clés disjointes (le prévisionnel d'une clé déjà facturée est écarté).
- **2027** : facturé = « exercice non ouvert » (jamais 0, jamais simulé).
- ⚠ **Base 2026** = facturé janv.–sept. + prévisionnel oct.–déc., marquée provisoire.
- Scénarios 2027 : base 2026 × 1,03 et × 1,06 (scénarios, pas obligations).
- Taux avec dénominateur 0 ou absent → non calculable. Évolution uniquement sur les mêmes mois calendaires.
- Engagement compté seulement s'il est `signe_confirme` (preuve exigée). ⚠ Reste contractuel jugé sur le facturé.
- RDV actif = visite planifiée, date ≥ date de référence. Une visite planifiée n'est jamais réalisée.
- Reliquat = commandé − livré − annulé ; facture ≠ livraison.
- DN de référencement = éligibles référencées (constat confirmé) / éligibles ; « à confirmer » non compté ; variation en points.
- ACP et stratégie : saisie manuelle historisée ; moteur de règles vide (critères UPSA non communiqués).
- 9 règles de priorité et score d'opportunité additif : seuils et pondérations = **valeurs de démonstration** réglables.

## 10. Sécurité

- Serveur sur 127.0.0.1, protection DNS rebinding (Host) et Origin, CSP stricte, aucune URL distante dans le code (test automatique).
- Imports : ≤ 10 Mo, ≤ 100 000 lignes, vérification de signature, `.xls`/`.xlsm` refusés, cellules jamais évaluées, fichier en attente gardé en mémoire 30 min.
- Risques connus : base et sauvegardes **en clair** sur le disque (FileVault conseillé), pas d'authentification, ne pas placer le projet dans un dossier synchronisé (iCloud, OneDrive, Dropbox). À faire avant usage réel prolongé : chiffrement applicatif ou disque, code d'accès.

## 11. Outils Claude intégrés au projet (`.claude/`)

- **26 skills** (invocation `/nom`) : action-plan, assortment-tracker, client-360, client-identity, client-segmentation, commercial-assistant, commercial-performance, commercial-reporting, commitment-tracker, convention-tracker, data-quality, data-security, delivery-backorder, dn-launch-tracker, groupement-agreements, growth-scenarios, invoice-tracker, launch-compliance, opportunity-scoring, pharma-import, sell-in-analysis, sell-out-analysis, trade-plan-manager, ubik-import (= préparation Y2OBIC), visit-coverage, visit-preparation, volume-gap.
- **4 agents** d'audit en lecture seule : business-rules-auditor, commercial-data-architect, premium-ui-designer, security-quality-reviewer.
- **3 références** : `UPSA_REGLES_METIER.md`, `CONTRATS_SOURCES.md`, `TESTS_CRITIQUES.md`.
- Documentation : `CLAUDE.md`, `docs/` (PROJECT_VISION, ARCHITECTURE, DATA_MODEL, BUSINESS_RULES, IMPORT_SPEC, SECURITY, ROADMAP, DECISIONS — 26 décisions D1 à D26), `BILAN_SESSION_1.md`, `BILAN_SESSION_2.md`, `COCKPIT_X20.md`.

## 12. Feuille de route

| Phase | Contenu | État |
|---|---|---|
| 1 | Fondations, données fictives, dashboard, fiche, calculs, import | ✅ |
| 2 | Fiche pharmacie complète (10 onglets, saisies, preuves, journal) | ✅ |
| 3 | Groupements et plans trade | ✅ |
| 4 | Imports R sur O, sell-out, Y2OBIC, PDF | ⏳ en attente d'exemples de formats |
| 5 | Segmentation, objectifs, agenda | ✅ |
| 6 | Lancements et DN de référencement | ✅ |
| 7 | Opportunités, préparation de RDV | ✅ |
| 8 | Exports, sauvegardes ✅ ; chiffrement, code d'accès, restauration UI, sauvegarde auto | 🟡 partielle |
| X20 | Connecteur cockpit, espaces réel/démo | ✅ (22/10/2026) |

## 13. Questions ouvertes (à trancher par l'utilisateur, ne pas décider seul)

**Données et autorisation**
1. L'entreprise autorise-t-elle Claude à lire les valeurs réelles du cockpit X20 ? (jamais confirmé)
2. L'import réel du fichier X20 a-t-il été fait dans l'espace réel ?
3. Existe-t-il une ancienne base `.db` avec des saisies de l'ancien poste ? (l'archive n'en contenait pas)

**Cockpit X20**
4. Signification de « Fréquence Visite », « FOT », « Ranking client NR+R » et des valeurs de Ciblage.
5. Formule du RAF +15 % Vitalité (FOT).
6. Périmètre de l'engagement OTC (le réalisé estimé utilise provisoirement la somme des 8 familles).
7. Définition du CA global.
8. Seuils des alertes (proche de l'objectif 90 %, baisse famille −20 % sur ≥ 50 unités : valeurs de démo).

**Règles métier générales**
9. Périmètre du CA paracétamol (toute la famille ou hors pédiatrie/codéine).
10. Base 2026 provisoire ou facturé au 31/12 uniquement.
11. Mesure de jugement des engagements (facturé, livré, commandé).
12. Seuils et gravités des priorités ; pondérations des opportunités ; fenêtre plan trade 60 jours.
13. Critères ACP1/ACP2 et défendre/maintenir/construire.
14. Nomenclature et libellés OTC définitifs ; unité de volume des exports réels.
15. Traitement des valeurs négatives (retours, avoirs).
16. Définition officielle de la DN et éligibilité des pharmacies aux nouveautés.

**Phase 4**
17. Exemples fictifs ou anonymisés des exports R sur O, sell-out et Y2OBIC (vrais noms de colonnes).

## 14. Comment m'aider efficacement (consignes pour Claude)

- Si on te demande une **modification de code**, rappelle que la version à jour est sur le Mac et qu'il faut la faire via Claude Code dans le dossier du projet ; commence par inspecter les fichiers concernés, sauvegarde avant toute migration, ajoute des tests, et ne revendique que les tests réellement lancés.
- Si on te demande une **règle de calcul**, appuie-toi sur les sections 7 et 9 et signale si elle touche un point ouvert de la section 13.
- Si on te demande d'**analyser des données réelles**, rappelle la règle 6 (autorisation non confirmée) avant d'aller plus loin.
- Réponds en français, de façon claire et concrète.
