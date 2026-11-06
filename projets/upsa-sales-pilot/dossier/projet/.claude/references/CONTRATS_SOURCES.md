# Contrats de données — sources à confirmer

## Principes
Chaque adaptateur conserve : `source_type`, `source_version`, `original_filename`, `sha256`, `imported_at`, `period_start`, `period_end`, `currency`, `volume_unit`, `grain`, `column_map_version`, `mapping_status`, `source_row_id`.

Ne pas mélanger des agrégats de granularités différentes (facture, pharmacie/mois, pharmacie/produit) sans méthode contrôlée. Retours, avoirs, annulations et dates d'effet sont explicités.

## Sources initiales
| Source utilisateur | Statut du format | Données attendues (hypothèses à confirmer) |
|---|---|---|
| Sell-in / « R sur O » | INCONNU jusqu'à exemple validé | facturation, CA, volumes, dates, client, référence |
| Assortiment | INCONNU jusqu'à exemple validé | référence attendue, statut, pharmacie, date |
| Sell-out | INCONNU jusqu'à exemple validé | sorties, volume, CA éventuel, client, produit, période |
| Y2OBIC (nom exact à confirmer) | NOM EXACT ET FORMAT INCONNUS | aucune sémantique imposée ; ne pas l’assimiler à un outil au nom proche (Yubik, Ubik…) sans confirmation |
| Conventions et accords PDF | semi-structuré | groupement, signature, périmètre, dates, obligations sous validation |
| Plan trade | semi-structuré | groupement, mois, pharmacies éligibles, mises en avant, volumes |

## Procédure avant création du mapping définitif
1. Obtenir **un modèle fictif ou anonymisé autorisé** ; documenter feuille, colonnes et exemples.
2. Valider clé client, clé produit, unité, périodes, TVA/HT, montant, signe, agrégation.
3. Afficher un aperçu et faire valider le mapping par l'utilisatrice.
4. Identifier conflits, champs non compris et cas « à confirmer ».
5. Archiver version des règles utilisées et tests de réimport.

## Contrôle de provenance
Tout indicateur calculé doit remonter à (a) ID d'import, (b) lignes du fichier source ou agrégat justifié, (c) version de mapping, (d) version de la formule métier, (e) date et périmètre.
