# Spécification de l’import (V1)

Format pris en charge : **« ventes sell-in » fictif** (mapping `sellin-fictif-v1`). Les formats réels (R sur O, sell-out, assortiment, Y2OBIC, PDF) restent **inconnus** et ne sont pas implémentés (voir `.claude/references/CONTRATS_SOURCES.md`).

## Parcours (UI « Centre d’importation » et API)
1. **Sélection** — `POST /api/imports/preview` (corps binaire, en-tête `X-File-Name`, `?sheet=` pour XLSX).
2. **Aperçu** — format, encodage, séparateur, en-têtes, 15 premières lignes, feuilles, statut doublon.
3. **Correspondances** — proposition automatique par intitulé, toujours modifiable ; mesure et mois à choisir si absents du fichier ; confirmation obligatoire des unités (boîtes, € HT).
4. **Contrôle** — `POST /api/imports/check` : statistiques, anomalies ligne par ligne, chevauchements. Rien n’est écrit.
5. **Enregistrement** — `POST /api/imports/commit` : transaction **tout ou rien** ; indicateurs recalculés.

Un fichier en attente est conservé en mémoire 30 minutes (jeton SHA-256), jamais écrit sur disque avant validation.

## Champs canoniques
| Champ | Obligatoire | Notes |
|---|---|---|
| Identifiant pharmacie | oui | `PH-xxx` ou alias source (ex. code client). Pas de rapprochement par nom. |
| Code produit | oui | doit exister dans la nomenclature |
| Période | colonne ou mois choisi | AAAA-MM, MM/AAAA, JJ/MM/AAAA, AAAAMM |
| Quantité (boîtes) | quantité ou montant | virgule décimale, espaces (y c. insécables) de milliers ; vide = inconnu |
| Montant (€ HT) | quantité ou montant | idem |
| Mesure | colonne ou choix | facturé / prévisionnel |

## Contrôles
Bloquants : colonne requise manquante, unités non confirmées, pharmacie inconnue, produit hors nomenclature, période ou nombre illisible, mesure inconnue, **facturé postérieur à la date de référence**, doublon interne (même pharmacie/produit/mois/mesure), recouvrement de données de démonstration de même mesure, recouvrement d’un import actif non remplacé, **fichier identique déjà importé**.
Avertissements : nomenclature non vérifiée, ligne sans valeur (conservée inconnue), valeur négative (convention à confirmer), cellule de type formule (conservée en texte), nouvelle version d’un fichier du même nom.

## Doublons et versions
- Même SHA-256 → « déjà importé », refusé (409).
- Même nom, contenu différent → nouvelle version ; si elle recouvre l’ancien lot, l’utilisatrice coche « Remplacer » : l’ancien lot passe `remplace` (conservé dans l’historique, exclu des calculs).
- Facturé importé sur un mois prévisionnel → le prévisionnel de la même clé est automatiquement écarté des totaux.

## Fichiers d’exemple (`src/client/public/exemples/`)
- `sellin-octobre-2026-fictif.csv` — Windows-1252, « ; », alias `CLI5000…CLI5014`, octobre 2026, 75 lignes.
- `sellin-octobre-2026-fictif.xlsx` — feuilles « Lisez-moi » et « Ventes », colonne « Mesure », PH-016…PH-030, 75 lignes.
- `sellin-anomalies-fictif.csv` — anomalies volontaires (enregistrement refusé).
Régénération : `npm run samples` (Python 3 + openpyxl).
