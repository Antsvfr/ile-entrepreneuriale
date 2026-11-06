# Journal des décisions

| # | Décision | Raison | Alternative écartée |
|---|---|---|---|
| D1 | Application web locale : serveur Node sur 127.0.0.1 + UI React | Fonctionne sans hébergement ; données restent sur le poste | Electron (plus lourd), app 100 % navigateur (pas de SQLite fiable) |
| D2 | SQLite via `node:sqlite` intégré à Node 22 | Aucun module natif à compiler (installation simple sous Windows/macOS) | better-sqlite3 (compilation native) |
| D3 | Logique métier pure dans `src/domain`, calculée côté serveur une seule fois | Un seul calcul par indicateur, testable, cohérence entre écrans | Calculs dans les composants React |
| D4 | Type `Maybe` avec motif d’absence | Une donnée inconnue reste inconnue, jamais 0 | `null` / `0` par défaut |
| D5 | Grain mensuel pharmacie × produit × mois × mesure | Permet facturé/prévisionnel disjoints et périodes comparables | Agrégats annuels |
| D6 | Taxonomie exclusive + attribut « non remboursé » | Évite le double comptage du CA | Famille « para non remboursé » séparée |
| D7 | Prévisionnel écarté dès qu’un facturé existe sur la même clé | Pas de double comptage après import | Remplacement manuel |
| D8 | Base 2026 marquée « provisoire » tant que 12 mois ne sont pas facturés | Transparence ; à confirmer | Base silencieuse |
| D9 | Classification ACP/stratégie manuelle, moteur de règles vide | Critères UPSA non communiqués : ne pas les inventer | Règles supposées |
| D10 | Seuils de priorités paramétrables, présentés comme valeurs de démonstration | Pas de règle UPSA connue | Seuils codés en dur |
| D11 | Import en deux temps (contrôle sans écriture puis commit transactionnel) | Tout ou rien, aucune base corrompue | Écriture ligne à ligne |
| D12 | Doublon de fichier par SHA-256 ; versions par nom ; remplacement explicite | Réimport sûr, historique conservé | Écrasement silencieux |
| D13 | Rapprochement des pharmacies par identifiant / alias uniquement | Homonymes fréquents | Rapprochement par nom |
| D14 | PDF reconnu mais non lu (422) | Extraction fiable nécessite vérification humaine (phase 4) | Extraction approximative |
| D15 | Date de référence paramétrable (`reference_date`, `UPSA_TODAY`) fixée au 18/10/2026 pour la démo | Démo et tests reproductibles | `new Date()` partout |
| D16 | Onglets et rubriques non construits visibles mais marqués « non encore disponible » | Ne pas présenter de fonction factice | Les masquer / les simuler |
| D17 | Vite 6 conservé | Vite 8 incompatible avec @vitejs/plugin-react 4 au moment du build ; 0 vulnérabilité npm audit | Vite 8 |
| D18 | Pack `.claude` : correction minimale du skill `ubik-import` et de `CONTRATS_SOURCES.md` (Y2OBIC distingué de Yubik/Ubik) ; nom de dossier du skill conservé | Le prompt interdit de confondre Y2OBIC avec un outil au nom proche ; ne pas recréer les skills | Renommer / recréer le skill |
| D19 | Saisies manuelles via routes REST dédiées, validation serveur et journal `audit_log` | Traçabilité de chaque modification ; mêmes règles quelle que soit l’interface | Édition directe sans journal |
| D20 | Statut « signé et confirmé » refusé sans preuve (convention, engagement, accord) | Une signature non prouvée ne doit pas compter | Statut libre |
| D21 | Constat d’assortiment = nouvelle ligne, jamais une mise à jour | Historique des présences conservé | Écrasement |
| D22 | DN de référencement (constat) distincte d’une DN de vente ; « à confirmer » non compté | Seule mesure possible sans sell-out ; pas de surestimation | DN déduite des volumes |
| D23 | Score d’opportunité additif et décomposé, pondérations de démonstration réglables | Explicable ; aucun critère UPSA inventé | Score pondéré opaque |
| D24 | Exports générés côté serveur depuis `domain/analysis` (write-excel-file, sans dépendance réseau, 0 vulnérabilité) | Mêmes chiffres qu’à l’écran | Export depuis le navigateur |
| D25 | Sauvegarde par `VACUUM INTO`, restauration manuelle | Copie cohérente sans arrêter le serveur ; restauration à chaud risquée | Copie de fichier brute |
| D26 | Phase 4 (R sur O, Y2OBIC, PDF) non développée | Formats non communiqués : interdiction de les inventer | Formats supposés |
