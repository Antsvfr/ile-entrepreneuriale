# Architecture

## Technologies
| Couche | Choix | Raison |
|---|---|---|
| UI | React 18, TypeScript strict, Vite 6, Tailwind CSS v4 | Demandé ; build rapide, typage strict |
| Navigation / données | react-router 7, TanStack Query 5 | Cache et invalidation après import |
| Tableaux / graphiques | TanStack Table 8, Recharts 2 | Demandé |
| Icônes / police | lucide-react, Inter (fichiers locaux via @fontsource) | Aucune ressource tierce chargée par l’UI |
| Serveur local | Node 22 `node:http` + tsx | Pas de framework : surface minimale |
| Base | SQLite via `node:sqlite` (intégré à Node ≥ 22.13) | Aucun module natif à compiler, fichier local unique |
| Import | parseur CSV maison (RFC 4180, UTF-8/Windows-1252), `read-excel-file` (XLSX) | Pas d’exécution de macros ; dépendance légère |
| Tests | Vitest 5, Playwright 1.56 | Demandé |

`node:sqlite` est marqué expérimental par Node 22 ; l’avertissement est masqué dans les scripts. Si son API changeait, seul `src/server/db/connection.ts` serait à adapter.

## Organisation
```
src/
  domain/            logique métier PURE (testable sans base ni réseau)
    maybe.ts         valeur connue | absente avec motif
    types.ts         entités
    taxonomy.ts      familles exclusives, périmètre paracétamol
    calc/            formules : volumes, targets, revenue, commitments, visits,
                     orders, assortment, classification, priorities, periods
    analysis/        assemblage pour les écrans : dashboard, pharmacy, family, dataset
  server/
    db/              connexion, migrations versionnées, repository (lecture → SectorData)
    import/          lecture fichier, parseurs FR, mapping, pipeline (aperçu/contrôle/commit)
    seed/            jeu fictif déterministe
    http/            mini-routeur JSON
    app.ts           routes API + fichiers statiques + en-têtes de sécurité
    index.ts         point d’entrée (127.0.0.1)
  client/
    app/             shell, routes, ErrorBoundary
    api/             client fetch + hooks TanStack Query
    components/ui/   composants réutilisables (Kpi, Value, Provenance, Tabs, Table…)
    features/<écran> une page par dossier
    public/exemples/ fichiers d’import fictifs
e2e/                 parcours Playwright
docs/                documentation
.claude/             skills, agents, références (pack installé)
```

## Flux de données
1. Le serveur charge la base en un `SectorData` (`repository.loadSectorData`) puis construit un index en mémoire (invalidé après chaque import, classification ou réglage).
2. Les routes appellent `domain/analysis/*` : **toutes** les valeurs affichées sont calculées là, une seule fois. Le client n’effectue aucun calcul métier (seulement du formatage).
3. Les valeurs voyagent sous forme `Maybe` + provenance (source, période, règle) pour que l’UI affiche « non calculable », « pas encore importé », etc.

## API locale (127.0.0.1 uniquement)
Lecture : `GET /api/meta`, `/api/dashboard`, `/api/pharmacies`, `/api/pharmacies/:id`, `/api/pharmacies/:id/preparation`, `/api/pharmacies/:id/audit`, `/api/performance/:family`, `/api/segmentation/:dimension`, `/api/groupements`, `/api/groupements/:id`, `/api/assortments`, `/api/launches`, `/api/opportunities`, `/api/agenda`, `/api/audit`, `/api/settings`, `/api/imports`, `/api/exports`, `/api/exports/:nom.csv|xlsx`, `/api/backups`.

Écriture (routes dans `src/server/routes/`, validation `validate.ts`, chaque écriture journalisée dans `audit_log` puis index invalidé) : `PATCH /api/pharmacies/:id` · `POST /api/pharmacies/:id/visits|tasks|conventions|commitments|assortment|classifications` · `PATCH /api/visits/:id`, `/api/tasks/:id`, `/api/conventions/:id`, `/api/commitments/:id`, `/api/launches/:id`, `/api/trade-actions/:id`, `/api/agreements/:id` · `POST /api/groupements/:id/trade-actions|agreements` · `PUT /api/pharmacies/:id/visit-objective`, `/api/objectives`, `/api/settings/priorities`, `/api/settings/opportunities` · `POST /api/backups`, `/api/imports/preview|check|commit`.

Exports : `src/server/export/` (`tables.ts` construit chaque tableau depuis `domain/analysis`, `writers.ts` écrit CSV/XLSX).

## Gestion des erreurs
`HttpError` côté serveur (codes 400, 403, 404, 409, 410, 413, 422), journalisation sans contenu métier ; `ErrorBoundary` et états `ErrorState`/`EmptyState` côté UI.
