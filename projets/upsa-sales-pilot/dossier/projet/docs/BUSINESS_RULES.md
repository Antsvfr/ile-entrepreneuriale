# Règles de calcul implémentées

Toutes les formules sont dans `src/domain/calc/` et testées (`calc.test.ts`). Référence de conception : `.claude/references/UPSA_REGLES_METIER.md`. **Aucune règle ci-dessous n’est une règle officielle UPSA** ; les points marqués ⚠ sont à confirmer.

## Familles et périmètres
- Taxonomie **exclusive** : PARA, VITALITE, SOMMEIL, HYDRAPHYSE, CERELYS (libellés OTC provisoires), AUTRE.
- « Paracétamol non remboursé » = sous-ensemble de PARA (`reimbursed = false`), affiché « dont », **jamais additionné**.
- Périmètre volumes paracétamol : famille PARA, **hors pédiatrie, hors codéine**, nomenclature vérifiée ; un attribut inconnu **exclut** la référence. Mêmes exclusions sur toutes les périodes comparées.
- ⚠ Le **CA** paracétamol affiché couvre toute la famille PARA (le filtre pédiatrie/codéine s’applique aux volumes et objectifs). À confirmer.

## Volumes et CA
- Grain : pharmacie × produit × mois × mesure (`facture` | `previsionnel`).
- `total estimé = facturé + prévisionnel` uniquement sur des clés disjointes : un prévisionnel dont la clé a déjà un facturé est écarté (`dedupeForecast`) et le nombre de lignes écartées est affiché.
- Unités hétérogènes → somme refusée (non calculable).
- 2027 : facturé = **exercice non ouvert** (jamais 0, jamais simulé) ; seul le prévisionnel existe.
- ⚠ Base 2026 = facturé janv.–sept. + prévisionnel oct.–déc. → marquée **provisoire** tant que 12 mois ne sont pas facturés.
- CA total = somme des familles exclusives = somme des faits. Montant manquant : non compté, signalé.

## Objectifs, restes, taux
- Scénarios 2027 : base 2026 × 1,03 et × 1,06 (scénarios, pas obligations).
- Écart : `reste` / `atteint` / `depasse` / `non_calculable` ; le reste opérationnel est `max(0, cible − réalisé)`, le dépassement affiché à part.
- Taux : dénominateur 0 ou absent → **non calculable** (jamais ∞, NaN ni 100 %).
- Évolution : uniquement sur les **mêmes mois calendaires** des deux années ; période de référence incomplète → refus.
- DN : variation exprimée en **points**.

## Engagements et conventions
- Un engagement ne compte que s’il est `signe_confirme` ; `a_verifier` / `non_signe` ne sont jamais traités comme signés.
- ⚠ Reste contractuel jugé sur le **facturé** (reste à facturer) et reste estimé sur facturé + prévisionnel. Si un contrat se juge en livré/commandé, la mesure devra être changée.
- Convention : signée seulement si `signe_confirme` et en cours de validité ; un document importé ou brouillon est « à vérifier ».

## Visites et rendez-vous
- RDV actif = visite `planifiee`, date ≥ date de référence ; annulée exclue.
- Taux de pharmacies avec RDV = pharmacies **distinctes** avec ≥ 1 RDV actif / pharmacies du périmètre.
- Couverture du plan = (réalisées + planifiées futures) / visites attendues ; une visite prévue puis réalisée compte une fois. Pharmacies sans objectif : exclues du dénominateur et signalées (objectif absent ≠ 0).

## Commandes, assortiment
- Reliquat = commandé − livré − annulé, sur lignes à livraison connue ; facture ≠ livraison.
- Assortiment : dernière observation par référence ; « à confirmer » ≠ « non » ; pas de matrice attendue → couverture non applicable (pas 0 %).

## Lancements et DN
- DN de référencement = pharmacies éligibles **référencées (constat confirmé)** / pharmacies éligibles. « À confirmer » n’est pas compté comme référencé ; non éligible = exclu du dénominateur. Aucune éligible → « non applicable », jamais 0 %.
- Dernier constat par pharmacie. Évolution mensuelle calculée uniquement avec les constats **datés**, à périmètre d’éligibilité actuel.
- Variation = DN actuelle − DN à la fin du mois précédent, **en points**. Non calculable si un référencement n’a pas de date (« périmètre incomplet ») ou si le produit n’était pas lancé.
- La DN de référencement n’est pas une DN de vente (sell-out) : celle-ci attend les formats réels (phase 4).

## Groupements et plan trade
- Accord « signé » seulement avec une référence de preuve ; un accord en vigueur = signé et date de référence dans sa période de validité.
- Taux de réalisation trade = réalisées confirmées / (réalisées + non réalisées confirmées). Les actions « prévues » ou « à vérifier » ne sont pas au dénominateur. Une action ne peut être déclarée réalisée à une date future.
- Les volumes d’un ancien adhérent restent rattachés à l’historique : ils ne sont pas réaffectés au nouveau groupement.

## Segmentation
- Regroupement par ACP, stratégie ou groupement à la date de référence ; la somme des segments égale le total secteur (testé). Les pharmacies non classées forment un segment visible.

## Opportunités et préparation de visite
- Score = **somme de composantes affichées** : écart au scénario +3 % 2027 (points par 100 boîtes), références attendues absentes, nouveautés non référencées, gammes OTC sans facturé dans l’année, mises en avant non réalisées. ⚠ Pondérations = **valeurs de démonstration** réglables. Donnée manquante → composante absente (rien d’inventé). Aucun critère ACP n’intervient.
- La fiche de préparation reprend priorités, opportunités, chiffres clés, assortiment, nouveautés, plan trade à 60 jours et tâches ; chaque point indique son origine.

## Saisies manuelles
- Rendez-vous planifié : date ≥ aujourd’hui ; visite réalisée : date ≤ aujourd’hui ; seul un RDV planifié change de statut ; un RDV passé non confirmé n’est pas compté comme réalisé.
- Convention « signée et confirmée » : date de signature, référence de preuve et nom de la personne qui confirme obligatoires. Engagement signé : volume et preuve obligatoires ; un seul engagement signé par pharmacie × famille × année.
- Volume ou objectif laissé vide = **non renseigné**, jamais 0. Toute saisie est inscrite au journal.

## Exports et sauvegardes
- Exports CSV (UTF-8 avec BOM, « ; », virgule décimale) et Excel produits à partir des mêmes calculs que les écrans ; une valeur absente est écrite avec son motif en clair ; les cellules commençant par `= + - @` sont neutralisées (préfixe `'`).
- Sauvegarde = copie cohérente de la base (`VACUUM INTO`) dans `data/backups/`. Restauration manuelle (application arrêtée).

## Classification et priorités
- ACP et stratégie : **saisie manuelle historisée**. Le moteur de règles n’applique que des règles `validee` ; **aucune règle n’est fournie** (critères UPSA non communiqués). ACP absent = « non classé ».
- 9 règles de priorité explicables (ACP1 sans RDV, à défendre avec CA en baisse, convention manquante, engagement à risque, assortiment incomplet, nouveauté non référencée, action trade en retard, reliquat important, objectif volume non atteint). ⚠ Seuils, activations et gravités = **valeurs de démonstration** modifiables dans « Paramètres métier ». Donnée manquante → la règle ne se déclenche pas.

## Points à confirmer (synthèse)
1. Périmètre du CA paracétamol (toute la famille ou hors pédiatrie/codéine).
2. Base 2026 provisoire (prévisionnel des derniers mois) ou base au 31/12 facturée uniquement.
3. Mesure de jugement des engagements (facturé, livré, commandé).
4. Seuils et gravités des priorités.
5. Critères ACP1/ACP2 et défendre/maintenir/construire.
6. Nomenclature et libellés OTC définitifs ; unité de volume des exports réels.
7. Traitement des valeurs négatives (retours, avoirs).
8. Pondérations des opportunités et fenêtre « plan trade à 60 jours » de la préparation de visite.
9. Définition officielle de la DN (référencement, sell-out, pondérée ?) et éligibilité des pharmacies aux nouveautés.
