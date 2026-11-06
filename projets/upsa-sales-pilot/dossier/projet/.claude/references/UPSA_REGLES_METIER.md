# UPSA Sales Pilot — règles métier de référence (proposition de conception)

> DOCUMENT DE TRAVAIL. Les classifications ACP, codes produits, périmètres contractuels, correspondances sources et règles de calcul contractuelles doivent être validés par la commerciale puis, si nécessaire, par UPSA. Les termes et formules ci-dessous servent à **concevoir et tester** le prototype, pas à certifier des données commerciales UPSA.

## Périmètre et catégories
- Années ciblées : **2026** (référence au 31/12/2026) et **2027** (facturé + prévisionnel, en respectant l'état réel de chaque année).
- Paracétamol : périmètre hors **pédiatrie** et hors **codéine**, à implémenter à partir de références officielles vérifiées, pas d'une détection approximative du nom.
- OTC : Vitalité, Sommeil, **Hydraphyse** et **Cérélys**, libellés utilisateur **provisoires**, à rapprocher d'une nomenclature approuvée. Ne pas corriger silencieusement les noms.
- Le **paracétamol non remboursé** est une sous-catégorie potentielle du paracétamol ; ne jamais le compter deux fois dans le CA total. Utiliser une taxonomie avec catégories exclusives et indicateurs de sous-ensemble.
- Toute unité de volume doit être définie (boîte, unité, carton, unité commerciale, etc.). Pas d'addition d'unités incompatibles.

## Dimensions indépendantes
- `acp_classification ∈ {ACP1, ACP2, inconnu}` ; critères communiqués plus tard.
- `commercial_strategy ∈ {defendre, maintenir, construire, inconnu}` ; règles distinctes de l'ACP.
- `groupement_membership` avec début/fin ; accords potentiellement datés et versionnés.

## Définitions de mesures
- `facture_2027` : uniquement les factures réellement observées pour 2027, non le montant prévu ou commandé.
- `previsionnel_2027` : estimation future sur période définie, avec version, source et méthode ; ne doit pas contenir du facturé déjà inclus.
- `projete_2027 = facture_2027 + previsionnel_2027` seulement si les périmètres sont disjoints, les unités équivalentes et les périodes compatibles.
- `engagement_signe` : objectif contractuel confirmé avec preuve, période et mesure d'exécution.
- `reste_facture_brut = engagement_signe - facture_2027` si le contrat se juge sur le facturé.
- `reste_projete_brut = engagement_signe - projete_2027` dans le même périmètre. Afficher `max(0, reste_brut)` pour le **reste opérationnel** et le dépassement éventuel séparément.
- Si contrat jugé en livré/commandé plutôt qu'en facturé, remplacer la mesure selon sa **définition validée** ; ne pas appliquer universellement la formule facturé.
- `objectif_3 = volume_base_2026 * 1.03`; `objectif_6 = volume_base_2026 * 1.06`. Scénarios, pas obligations.
- `evolution_pct = (courant - reference) / reference * 100` uniquement si référence renseignée et non nulle, périmètre comparable.
- `avancement_pct = mesure_retenue / objectif_retenu * 100` avec indication visible du dénominateur. Si objectif non disponible/0 => non calculable.
- `assortiment_couverture = nombre_de_references_confirmees / nombre_de_references_attendues_eligibles * 100` ; ne pas considérer absences dans export partiel comme référence absente.
- `DN_ref = pharmacies_eligibles_referencees / pharmacies_eligibles * 100` ; variation de DN exprimée en **points**, avec le même périmètre si comparaison historique. DN de référencement ≠ DN ventes ≠ distribution valeur.
- `rdv_pharmacies_pct = pharmacies_avec_au_moins_un_rdv_futur_actif / pharmacies_dans_le_perimetre * 100` ; annulations exclues.
- `plan_visites_pct = (visites_realisees_et_visites_futures_planifiees_distinctes_de_l_annee) / visites_requises_annuelles * 100`. Prévenir en cas de dépassement, pas de double compte.
- `derniere_facture` provient d'une date de facture validée, jamais de la date d'import.
- `reliquat` doit provenir de la source ou être calculé via commande confirmée - livraison confirmée après annulations/retours selon contrat ; facture ≠ livraison.

## Données absentes
Toujours distinguer : `valeur=0 confirmée`, `non renseigné`, `pas encore importé`, `non applicable`, `à confirmer`, `conflictuel`, `périmètre incomplet`. Aucun `coalesce(0)` aveugle. Une convention importée sans preuve n'est pas « signée ».

## Temps et versionnement
- Afficher date de réalisation **et** date de mise à jour ; une période de fait distincte de la période importée.
- Une date future `2027` ne doit pas contenir de vraies factures avant l'année 2027 ; seules prévisions ou données de démonstration clairement étiquetées peuvent être présentes.
- Tous les chiffres affichent : mesure, source, période, unité, statut (réalisé/prévisionnel), date import, éventuelle estimation et règle de calcul.

## Sécurité
- Ne pas utiliser de vrais fichiers commerciaux avant autorisation ; Claude Code lui-même peut envoyer les éléments lus au modèle distant.
- Interdire données de patients. Pas d'upload, déploiement, télémétrie, connexion réseau ou MCP externe par défaut. Pas de secrets ni d'informations commerciales en dépôt Git.
