# UPSA Sales Pilot

Application **locale** de pilotage commercial pharmacie : tableau de bord secteur, portefeuille de pharmacies, fiche client, performance par famille, visites et rendez-vous, plan d’action priorisé et centre d’importation CSV/XLSX.

> **Version 1 — données 100 % fictives.** Aucune donnée réelle, aucun service distant, aucune télémétrie. Les seuils, classifications et libellés OTC présents sont des valeurs de démonstration, **pas des règles officielles UPSA**.

## Prérequis
- **Node.js ≥ 22.13** (utilise le module intégré `node:sqlite` : aucune dépendance native à compiler).
- npm (fourni avec Node). Python 3 + `openpyxl` uniquement pour régénérer les fichiers d’exemple (facultatif).

## Installation et lancement
```bash
cd upsa-sales-pilot
npm install
npm run dev          # interface http://127.0.0.1:5173  (API locale sur 127.0.0.1:5174)
```
Version « production locale » (un seul processus) :
```bash
npm start            # compile puis sert l’application sur http://127.0.0.1:4173
```
Au premier lancement, la base `data/upsa-sales-pilot.db` est créée et remplie avec le jeu fictif (30 pharmacies).

| Commande | Rôle |
|---|---|
| `npm run dev` | Développement (rechargement à chaud) |
| `npm start` | Build + serveur unique sur le port 4173 |
| `npm run db:reset` | Supprime la base locale et recharge le jeu fictif |
| `npm test` | Tests unitaires et d’intégration (Vitest) |
| `npm run test:e2e` | Parcours navigateur (Playwright, base en mémoire) |
| `npm run typecheck` | Vérification TypeScript stricte |
| `npm run test:all` | Les trois précédents |
| `npm run samples` | Régénère les fichiers d’import d’exemple |

Pour Playwright sur un poste neuf : `npx playwright install chromium` (une fois).

## Découvrir le jeu fictif
1. **Tableau de bord** : CA facturé / prévisionnel / estimé 2026, objectif, restes à faire par famille, rendez-vous, priorités. Chaque chiffre a une info-bulle de provenance (ⓘ).
2. **Mes pharmacies** : recherche, filtres ACP / stratégie / groupement / RDV ; cliquer sur le nom d’une pharmacie ouvre sa fiche.
3. **Fiche pharmacie** (ex. *Pharmacie des Tilleuls*, PH-001) : 10 onglets (Vue d’ensemble, Paracétamol, OTC, Assortiments, Conventions et engagements, Commandes et reliquats, Visites et RDV, Nouveautés, Plan trade, Journal). Saisie des RDV, comptes rendus, tâches, conventions, engagements, constats d’assortiment, référencements. Bouton **Préparer le rendez-vous** : fiche imprimable.
4. **Groupements** : fiche par groupement (accords, adhérents, plan trade mensuel, performance).
5. **Performance commerciale** : par famille, et par segment (ACP, stratégie, groupement).
6. **Assortiments** : matrice pharmacie × référence attendue. **Lancements et DN** : DN de référencement des nouveautés et son évolution.
7. **Visites**, **Plan d’action** (priorités, opportunités, tâches) avec exports Excel/CSV.
8. **Paramètres métier** : seuils des priorités, pondérations des opportunités (valeurs de démonstration), objectifs secteur, sauvegardes locales, exports, journal des saisies.

Non disponible : imports R sur O, sell-out, Y2OBIC et PDF (formats à fournir, phase 4).

La date de référence de la démonstration est le **18 octobre 2026** (facturé disponible jusqu’en septembre 2026).

## Tester un import
1. Ouvrir **Centre d’importation**.
2. Choisir `src/client/public/exemples/sellin-octobre-2026-fictif.csv` (aussi téléchargeable depuis l’écran).
3. Vérifier l’aperçu (encodage Windows-1252, séparateur « ; » détectés) → **Définir les correspondances**.
4. Choisir la mesure **Facturé (réalisé)**, cocher la confirmation des unités → **Contrôler le fichier**.
5. **Valider et enregistrer** : les indicateurs se recalculent ; le prévisionnel d’octobre des pharmacies concernées est écarté (pas de double comptage).
6. Réimporter le même fichier : il est signalé « Fichier déjà importé » et refusé.

Autres exemples : `sellin-octobre-2026-fictif.xlsx` (2 feuilles, colonne « Mesure ») et `sellin-anomalies-fictif.csv` (anomalies volontaires, enregistrement refusé).

## Documentation
`CLAUDE.md` (règles pour Claude Code) · `docs/PROJECT_VISION.md` · `docs/ARCHITECTURE.md` · `docs/DATA_MODEL.md` · `docs/BUSINESS_RULES.md` · `docs/IMPORT_SPEC.md` · `docs/SECURITY.md` · `docs/ROADMAP.md` · `docs/DECISIONS.md` · bilans `BILAN_SESSION_1.md`, `BILAN_SESSION_2.md`.
