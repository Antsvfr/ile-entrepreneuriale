# UPSA Sales Pilot — instructions pour Claude Code

Application **locale** de pilotage commercial pharmacie (React + TypeScript strict + Node 22 + SQLite). V1 sur **données fictives uniquement**.
Documentation détaillée : `docs/` (lire `docs/BUSINESS_RULES.md` et `docs/DECISIONS.md` avant de toucher un calcul).

## Rôle du projet
Outil desktop-first de pilotage commercial pharmacie : fiche client 360°, paracétamol 2026/2027, OTC Vitalité/Sommeil/Hydraphyse/Cérélys (libellés provisoires), assortiments, accords groupements/plans trade, facturé-prévisionnel, objectifs/engagements, livraisons/reliquats, visites, RDV et DN nouveautés.

## Règles absolues
- Développer et tester avec des données **fictives uniquement**, jusqu'à autorisation explicite des données professionnelles avec Claude Code ; pas de données patients.
- Ne connecter aucun cloud, API distante, synchronisation ou télémétrie sans accord préalable. Pas de déploiement public. Ne pousser aucun code sur un dépôt distant sans autorisation.
- Ne pas inventer la classification ACP1/ACP2, les critères « défendre/maintenir/construire », la nomenclature produits, les schémas « R sur O » ou « Y2OBIC » ni les termes contractuels. Y2OBIC n'est assimilé à aucun outil au nom proche.
- Distinguer réalisé/facturé, commandes, prévisions, livré, reliquats et signatures prouvées ; pas de double comptage CA.
- Calculer paracétamol **hors pédiatrie et codéine** sur un mapping produit validé.
- Stocker source, période, unité et date de chaque KPI ; préserver données manquantes et statut « à confirmer ». Une donnée absente n'est **jamais** remplacée par 0.
- L'application doit fonctionner sans assistant IA externe ; qualité des calculs avant sophistication graphique.
- Ne jamais présenter comme opérationnelle une fonctionnalité non développée (onglets/rubriques « non encore disponible »).
- Avant toute modification, inspecter les fichiers existants ; préserver l'architecture et les fonctionnalités testées ; tests automatisés et bilan de changements.

## Où se trouve quoi
- `src/domain/` : logique métier **pure** (aucun accès disque/réseau). `calc/` = formules unitaires, `analysis/` = assemblage pour les écrans. Toute formule vit ici une seule fois ; l'API et l'UI ne recalculent rien.
- `src/domain/maybe.ts` : type `Maybe` (valeur connue ou motif d'absence). L'utiliser pour toute valeur pouvant manquer.
- `src/server/` : HTTP local (127.0.0.1), SQLite (`node:sqlite`), migrations versionnées (`db/migrations.ts` : ajouter une version, ne jamais modifier une migration publiée), import (`import/`), jeu fictif (`seed/demo.ts`).
- `src/client/` : React (features par écran, `components/ui` réutilisables).
- `src/server/routes/` : routes d’écriture (validation + journal `audit_log`), analyses, exports, sauvegardes. `src/server/export/` : CSV/XLSX.
- `e2e/` : parcours Playwright ; tests unitaires à côté du code (`*.test.ts`).

## Commandes
- `npm run dev` (UI http://127.0.0.1:5173, API 5174) · `npm start` (build + http://127.0.0.1:4173)
- `npm test` · `npm run test:e2e` · `npm run typecheck` · `npm run db:reset` · `npm run samples`
- Date de référence de la démo : réglage `reference_date` (2026-10-18), surchargeable par `UPSA_TODAY`.

## Points à confirmer par l'utilisatrice (ne pas trancher seul)
Voir `docs/BUSINESS_RULES.md` § « À confirmer » : périmètre CA paracétamol, base 2026 provisoire, engagement jugé sur le facturé, seuils de priorités (valeurs de démonstration), règles ACP/stratégie (aucune règle validée → classification manuelle).

## Références
- `.claude/references/UPSA_REGLES_METIER.md`
- `.claude/references/CONTRATS_SOURCES.md`
- `.claude/references/TESTS_CRITIQUES.md`
- `.claude/skills/<nom>/SKILL.md` pour procédures spécialisées, invocation `/nom`.
- `.claude/agents/` pour audits délégués en lecture seule.
