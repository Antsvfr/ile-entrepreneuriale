# Modèle de données

Base SQLite locale (`data/upsa-sales-pilot.db`, mode WAL, clés étrangères actives). Schéma créé par des **migrations versionnées** (`src/server/db/migrations.ts`, table `schema_migrations`). Règle : on ajoute une migration, on ne modifie jamais une migration déjà appliquée.

## Tables (migration v1)
| Table | Contenu | Points clés |
|---|---|---|
| `pharmacies` | identité, adresse, contacts | identifiant interne `PH-xxx` ; `is_demo` |
| `pharmacy_aliases` | identifiants sources (ex. code client) | rapprochement **par identifiant uniquement**, jamais par nom |
| `groupements`, `groupement_memberships` | groupements et adhésions datées | `valid_from` / `valid_to` (changement de groupement historisé) |
| `classifications` | ACP et stratégie, historisées | `dimension ∈ {acp, strategy}`, `origin ∈ {manuel, regle, demo}` ; jamais écrasées |
| `classification_rules` | règles de classification | `status ∈ {brouillon, validee}` ; seules les règles validées s’appliquent ; aucune fournie |
| `products` | nomenclature | famille exclusive, `is_pediatric`, `contains_codeine`, `reimbursed` (NULL = inconnu), `nomenclature_status ∈ {verifiee, a_confirmer}`, unité |
| `import_batches` | lots importés | nom d’origine, SHA-256, période, mesure, version de mapping, `status ∈ {actif, remplace}` |
| `volume_facts` | **fait mensuel** pharmacie × produit × mois × mesure | `measure ∈ {facture, previsionnel}` ; quantité et montant **nullables** (NULL = inconnu, ≠ 0) ; `batch_id` (provenance) |
| `conventions` | conventions et accords | `status ∈ {brouillon, a_verifier, signe_confirme, expire, annule, remplace}`, preuve, confirmé par |
| `commitments` | engagements chiffrés | famille, année, cible, `status ∈ {signe_confirme, a_verifier, non_signe}` |
| `order_lines` | commandes / livraisons | commandé, livré, annulé : reliquat ≠ facture |
| `invoices` | factures (dates) | « dernière facture » = date de facture, jamais date d’import |
| `visits`, `visit_objectives` | visites / RDV et objectif annuel | `status ∈ {planifiee, realisee, annulee}` |
| `tasks` | tâches issues des visites | `a_faire` / `fait` |
| `assortment_lines` | présence de références | `presence ∈ {oui, non, a_confirmer}` |
| `launch_listings` | référencement des nouveautés | `listed ∈ {oui, non, a_confirmer}` |
| `trade_actions` | actions du plan trade | `prevu … realise_confirme / non_realise_confirme / a_verifier` |
| `objectives` | objectifs secteur / pharmacie | `metric ∈ {volume, ca}` |
| `settings` | réglages (date de référence, seuils de priorités) | JSON |

## Migration v2 (`saisie_groupements_dn_audit`)
| Table / colonne | Rôle | Contraintes clés |
|---|---|---|
| `launch_listings.listed_date` | date du constat de référencement (sert à l’évolution des DN) | nulle si inconnue ; obligatoire pour une saisie « référencée » |
| `groupement_agreements` | accords commerciaux d’un groupement (intitulé, année, validité, termes, preuve) | `status ∈ {brouillon, a_verifier, signe_confirme, expire, annule}` ; « signé » exige une référence de preuve (contrôle API) |
| `audit_log` | journal de chaque saisie manuelle (date, entité, pharmacie, action, détail) | ajout seul, jamais modifié |

Réglage supplémentaire : `opportunity_settings` (pondérations des opportunités, JSON).
Les constats d’assortiment ne sont jamais écrasés : chaque saisie ajoute une ligne, la plus récente fait foi.

## Valeurs absentes
Dans le domaine, toute valeur pouvant manquer est un `Maybe` : `{known: true, value}` ou `{known: false, reason}` avec `reason ∈ non_renseigne | pas_encore_importe | non_applicable | a_confirmer | conflictuel | perimetre_incomplet | exercice_non_ouvert | non_calculable`.

## Jeu fictif
`src/server/seed/demo.ts`, aléatoire **déterministe** (graine 20261018) : 30 pharmacies (villes « -Démo », codes postaux 99xxx, téléphones 01 99 00…, e-mails `@exemple.test`), 5 groupements fictifs, 21 références `DEMO-*`, facturé 2025 complet, facturé 2026 janv.–sept., prévisionnel oct.–déc. 2026 et 2027, conventions, engagements, visites, commandes, assortiments, nouveautés, actions trade. Une valeur volontairement absente (PH-012, DEMO-VIT-02, mai 2026) et un changement de groupement (PH-006 au 01/04/2026) servent de cas de test.
