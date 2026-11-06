# Connecteur « X20 Cockpit Territoire »

Import local, automatique et contrôlé du fichier `X20_Cockpit_Territoire_2026.xlsx` (1 onglet, 109 colonnes, une ligne par pharmacie).

## Reconnaissance automatique
- Le Centre d'importation reconnaît le format par ses en-têtes (accents, casse et ordre tolérés) : Code SAP présent et au moins 90 % des 109 colonnes attendues.
- Aucune correspondance de colonnes à saisir. L'aperçu présente les créations, mises à jour, différences, conflits, valeurs à vérifier et contrôles de cohérence. **Rien n'est écrit avant la validation explicite.**
- Avant l'enregistrement : sauvegarde `data/<espace>/backups/avant-import-x20-*.db` avec contrôle d'intégrité.

## Modèle de données (migration 3, additive)
| Table | Rôle |
|---|---|
| `cockpit_imports` | Un lot par fichier validé (empreinte SHA-256, en-têtes, rapport, sauvegarde préalable, statut actif/remplacé). |
| `cockpit_rows` | Les 109 valeurs brutes par pharmacie et par import (`values_json`, intitulés d'origine). Historique complet, différences entre versions. |
| `source_conflicts` | Écarts entre une saisie de l'application et une valeur importée (ouvert / résolu). |
| `groupements.parent_id`, `level`, `source` | Hiérarchie père → fils. |
| `pharmacy_aliases` (`sap`, `cip_origine`, `cip_actif`) | Rapprochement. Le **Code SAP** est l'identifiant (unicité contrôlée à chaque import ; doublon ou SAP vide = import bloqué). Les deux CIP sont conservés séparément. |

Les écrans calculent tout à la lecture (`src/domain/cockpit/`), à partir des valeurs brutes : aucune valeur source n'est écrasée.

## Règles de priorité des sources
- Identité (nom, CP, ville, téléphone, e-mail, titulaire) : mise à jour seulement si la valeur actuelle est vide ou identique au cockpit précédent. Une valeur modifiée dans l'application est conservée et un conflit est créé.
- Une valeur absente du fichier n'efface jamais une donnée existante.
- Groupement : un changement clôt l'ancien rattachement (`end_date`) et en ouvre un nouveau ; un rattachement saisi à la main n'est pas modifié (conflit).
- Visites : la dernière visite crée une visite réalisée (source `x20`) si aucune n'existe à cette date ; la prochaine visite crée ou déplace un rendez-vous `x20`. Un rendez-vous saisi ou déplacé à la main (`x20_modifie`) n'est jamais déplacé (conflit).
- ACP / stratégie : la décision saisie dans l'application prime ; à défaut, ACP lu dans Ciblage / Cible / Ciblage (concat) et stratégie depuis Segmentation (Build → construire, Maintain → maintenir, Defend → défendre ; Observe et Gain conservés tels quels, hors des trois axes).
- Conv 2026, remises, engagements : affichés comme données déclaratives ; aucune convention signée, aucun engagement ni remise n'est créé automatiquement.
- Espaces séparés : `npm start` = espace **réel** (`data/reel/`, jamais de jeu fictif) ; `npm run start:demo` = démonstration (port 4174).

## Règles de calcul (vérifiées sur le fichier de référence par comptage, sans lecture des valeurs)
| Indicateur | Définition | Vérification |
|---|---|---|
| RAF paracétamol ISO / +3 % / +6 % | Vol 2025 × (1 + p) − Vol 2026 Fact+Prev | 150/150 lignes concordent |
| RAF Sommeil ISO / +5 % / +10 % | Vol Sommeil 2025 × (1 + p) − Vol Sommeil Fact+Prev 2026 | 149/150 |
| RAF Vitalité ISO / +5 % / +10 % | idem Vitalité | 145/150 |
| RAF +15 % Vitalité (FOT) | **non documenté** : ne correspond pas à la formule ; affiché sans recalcul | — |
| RAF OTC S1 / FY +8 % / +12 % | CA 2025 × (1 + p) − CA 2026 Fact+Prev (S1 et FY jamais mélangés) | 144/150 (S1), 146/150 (FY) |
| Avancement | Réalisé estimé (Fact+Prev) / objectif | — |
| Prévisionnel restant | Fact+Prev − Fact (même périmètre « OTX + OTC ») | Fact+Prev ≥ Fact : 150/150 |

La valeur RAF du fichier est toujours conservée ; l'écran affiche fichier, recalcul, écart et statut (concorde, arrondi ≤ 1, écart, non documenté).

## Périmètres de CA (ne jamais additionner)
- `CA Paracétamol + Autres OTX` ≥ `CA Paracétamol OTX + OTC` sur toutes les lignes : le premier inclut le second.
- `CA OTC 2025/2026` = `CA OTC FY 2025/2026 (Fact+Prev)` sur toutes les lignes.
- La somme des 8 familles ne reproduit le CA OTC que sur une partie des lignes (≈ 2/3) : les familles ne servent pas à reconstituer le CA OTC.
- **CA global : non calculé** tant que son périmètre n'est pas défini.
- Paracétamol : le fichier ne permet pas de vérifier les exclusions pédiatrie / codéine → avertissement affiché.

## Qualité des données
- `132` dans un champ texte, catégorie ou date : signalé « à vérifier », jamais interprété. `132` dans une colonne quantitative reste une valeur valide. (Dans le fichier de référence analysé : aucun `132` texte ; quelques `132` numériques dans des volumes.)
- Négatifs conservés (RAF négatif = dépassement de l'objectif ; CA/volume négatif = à interpréter).
- Dates `JJ/MM/AAAA` normalisées ; date impossible = « à confirmer ».
- Remises/engagements textuels : nature déduite (taux, volume, condition, oui/non) sans application contractuelle.
- Aucune donnée 2027 fabriquée.

## À confirmer par l'utilisatrice
Signification de « Fréquence Visite », de « FOT », de « Ranking client NR+R », des valeurs de Ciblage, du périmètre de l'engagement OTC (le réalisé estimé utilise la somme des 8 familles, signalé « périmètre à confirmer »), définition du CA global, seuils des alertes (proche de l'objectif 90 %, baisse famille −20 % sur ≥ 50 unités : valeurs de démonstration).

## Tests
`src/domain/cockpit/x20.test.ts`, `src/server/__tests__/cockpit.test.ts`, parcours e2e « cockpit X20 fictif ». Fichier d'exemple 100 % fictif : `src/client/public/exemples/x20-cockpit-fictif.xlsx` (`npm run samples:x20`). Aucune donnée réelle dans les tests ni dans le jeu de démonstration.
