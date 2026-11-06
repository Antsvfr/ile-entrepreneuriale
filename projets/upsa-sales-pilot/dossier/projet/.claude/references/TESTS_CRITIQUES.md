# Tests critiques à maintenir

Écrire des tests automatisés déterministes utilisant uniquement des données synthétiques ; ne pas limiter la vérification aux captures UI.

1. **Paracétamol filtré** : base 2026 de 1 000 après exclusions pédiatrie/codéine → objectifs 2027 +3 % = 1 030 ; +6 % = 1 060. La version non filtrée ne remplace jamais la base.
2. **Engagement** : 2027 signé 100, facturé 70, prévisionnel 20 disjoint → reste à facturer 30, reste projeté 10 ; un prévisionnel qui chevauche facturé bloque somme.
3. **Futur** : aucune facture 2027 réelle avant début 2027 ; démonstration clairement étiquetée.
4. **Taux** : 0 objectif ou valeur manquante → « non calculable », jamais infini/NaN ou 100 %.
5. **CA sans double compte** : si para total 1000 inclut para non remboursé 200 et OTC 300 → total 1300 (pas 1500).
6. **Rendez-vous** : 10 pharmacies, 6 ont ≥1 RDV futur actif → 60 % ; RDV annulé exclu, passé compté uniquement dans visites réalisées.
7. **Visites** : une visite prévue puis réalisée ne compte pas deux fois dans couverture annuelle.
8. **DN** : 8 pharmacies référencées / 20 éligibles = 40 % ; 9/20 = 45 % → évolution +5 points ; non éligibles exclus.
9. **Convention** : PDF importé sans confirmation → à vérifier, jamais signé.
10. **Assortiment** : export partiel ne prouve pas l'absence d'une référence ; inconnu ≠ non.
11. **Reliquat** : commande 100 livrée 70 → 30 uniquement en l'absence d'annulation/retour, avec même référence/unité ; facture ≠ livraison.
12. **Imports** : fichier identique réimporté = pas de doublon ; même nom mais contenu différent = version / décision utilisateur.
13. **Rapprochement** : noms de pharmacie identiques, identifiants différents → pas de fusion automatique.
14. **Cohérence écrans** : valeur par pharmacie = contribution utilisée au dashboard, dans le même périmètre.
15. **No network** : tests contrôlant l'absence de transmissions externes dans le prototype.
