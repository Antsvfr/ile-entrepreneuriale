# Bilan de session 2 — UPSA Sales Pilot

Date de référence de la démonstration : 18 octobre 2026. **Données 100 % fictives.** Rien n'a été déployé ni poussé sur un dépôt distant.

## Ce qui a été réalisé

Demande : « réalise tout pour l'instant, on modifiera les erreurs après ». J'ai développé les phases 2, 3, 5, 6 et 7, et une partie de la phase 8. La phase 4 n'a pas été faite, volontairement (voir plus bas).

### Fiche pharmacie complète (phase 2)
- Les 10 onglets sont désormais opérationnels : Vue d'ensemble, Paracétamol, OTC, Assortiments, Conventions et engagements, Commandes et reliquats, Visites et RDV, Nouveautés, Plan trade, Journal.
- Saisies possibles :
  - coordonnées (e-mail contrôlé) ;
  - rendez-vous : planifier, déplacer, annuler, confirmer réalisé ;
  - visites réalisées avec compte rendu ;
  - tâches ;
  - objectif annuel de visites ;
  - conventions et engagements ;
  - constats d'assortiment, conservés dans un historique ;
  - référencement des nouveautés ;
  - mise à jour des actions trade.
- Règles de preuve appliquées par le serveur :
  - une convention « signée et confirmée » exige une date, une référence de preuve et le nom de la personne qui confirme ;
  - un engagement signé exige un volume et une preuve, et un seul engagement signé est accepté par famille et par année ;
  - un rendez-vous planifié ne peut pas être dans le passé, et une visite réalisée ne peut pas être dans le futur.
- Chaque saisie est inscrite dans un **journal**, consultable par pharmacie et globalement.
- Le bouton **Préparer le rendez-vous** ouvre une fiche imprimable (ou exportable en PDF via l'impression) avec :
  - les points à aborder, chacun avec son origine ;
  - les chiffres clés et les volumes par famille ;
  - les références à proposer ou à vérifier ;
  - les nouveautés ;
  - le plan trade des 60 prochains jours ;
  - les engagements et les tâches.

### Groupements et plan trade (phase 3)
- Une fiche par groupement, avec :
  - les accords (« signé » uniquement avec une preuve) ;
  - les adhérents et les anciens adhérents (leur historique n'est pas réaffecté) ;
  - le plan trade mensuel : taux de réalisation, retards, création d'une action pour tous les adhérents en une fois ;
  - la performance par famille.

### Performance et pilotage (phase 5)
- **Segmentation** par ACP, stratégie et groupement. La somme des segments est égale au total secteur, et c'est testé.
- **Objectifs secteur** saisissables. Un champ vide signifie « non renseigné », jamais 0.
- **Agenda** : prochains rendez-vous et rendez-vous passés à confirmer.
- **Plan d'action** en trois vues : priorités, opportunités, tâches.

### Lancements et DN (phase 6)
- **DN de référencement** par nouveauté : pharmacies éligibles référencées confirmées, divisées par les éligibles.
- Variation en points par rapport à la fin du mois précédent, évolution mensuelle, DN par groupement, mise à jour pharmacie par pharmacie.
- **Assortiments** : matrice pharmacie × référence attendue, avec la couverture par pharmacie et par référence.

### Intelligence commerciale (phase 7)
- **Opportunités** : un score décomposé en points visibles. Les composantes sont :
  - l'écart au scénario +3 % 2027 ;
  - les références absentes ;
  - les nouveautés non référencées ;
  - les gammes OTC sans facturé ;
  - les mises en avant non réalisées.
- Les pondérations sont réglables dans Paramètres. Ce sont des **valeurs de démonstration**.

### Optimisation (phase 8, partielle)
- **Exports Excel et CSV** pour : pharmacies, priorités, opportunités, performance par famille, segmentations, assortiment, DN et visites. Les valeurs absentes sont écrites en clair, et l'injection de formules est neutralisée.
- **Sauvegardes locales** de la base, en un clic depuis Paramètres, dans `data/backups/`.

## Tests
| Contrôle | Résultat |
|---|---|
| Typage strict (`npm run typecheck`) | ✅ aucune erreur |
| Tests unitaires et API (`npm test`) | ✅ 77/77 (54 en session 1, +23) |
| Parcours navigateur (`npm run test:e2e`) | ✅ 6/6 |
| `npm audit` | ✅ 0 vulnérabilité |

Les nouveaux tests couvrent :
- la DN : formule, « à confirmer » non compté, variation, référencements sans date ;
- le score d'opportunité : somme des composantes, donnée absente ;
- les règles de preuve et de dates ;
- le doublon d'engagement et le volume vide qui reste inconnu ;
- l'historique d'assortiment ;
- la DN recalculée après une saisie ;
- le plan trade ;
- la segmentation ;
- les exports CSV et Excel, y compris l'injection de formule ;
- les sauvegardes ;
- les parcours : planifier un rendez-vous, groupement, préparation de rendez-vous, téléchargement d'un export.

## Ce qui n'a pas été fait, volontairement
- **Phase 4, imports R sur O, sell-out, Y2OBIC et PDF.** Je ne connais pas ces formats, et le prompt fondateur interdit de les inventer. Il me faut un exemple fictif ou anonymisé de chaque fichier, avec les noms de colonnes réels.
- **DN de vente (sell-out)** : elle dépend de la phase 4.
- **Restauration d'une sauvegarde depuis l'écran** : elle reste manuelle (arrêter l'application puis remplacer le fichier). C'est plus sûr pour l'instant.
- **Chiffrement de la base et code d'accès** : ils restent à faire avant d'utiliser des données réelles (voir `docs/SECURITY.md`).

## Choix faits par défaut (à valider ou corriger)
1. Pondérations des opportunités : 2 points par 100 boîtes, 3 par référence absente, 4 par nouveauté, 5 par gamme OTC absente, 2 par mise en avant non réalisée.
2. La DN mesurée est une DN de **référencement**, établie par constat. Les pharmacies marquées « à confirmer » ne sont pas comptées.
3. Taux de réalisation trade = réalisées / (réalisées + non réalisées confirmées).
4. La fiche de préparation montre le plan trade sur 60 jours.
5. Les statuts possibles d'un accord de groupement : brouillon, à vérifier, signé et confirmé, expiré, annulé.
6. Un seul engagement signé par pharmacie, famille et année.

## Points à confirmer
Ils sont tous listés dans `docs/BUSINESS_RULES.md` § « Points à confirmer » (9 points). Deux nouveautés par rapport à la session 1 :
- la définition officielle de la DN et l'éligibilité des pharmacies aux nouveautés ;
- les pondérations des opportunités.

## Lancer l'application
```
npm install
npm start          # http://127.0.0.1:4173
```
Les tests se lancent avec `npm run test:all`.

## Prochaines étapes suggérées
1. Me signaler les erreurs et les écrans à ajuster (c'était prévu : « on modifiera les erreurs après »).
2. Fournir des exemples **fictifs** des exports R sur O, sell-out et Y2OBIC pour démarrer la phase 4.
3. Valider ou corriger les règles listées dans « Choix faits par défaut ».
