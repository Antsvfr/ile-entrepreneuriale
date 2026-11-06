# Vision du projet

UPSA Sales Pilot doit devenir le **centre de pilotage commercial quotidien** d’une commerciale UPSA (15 ans d’expérience) qui reprend un nouveau secteur de pharmacies.

## Questions auxquelles l’outil doit répondre
Qui sont mes clients ? Lesquels sont ACP1/ACP2, à défendre/maintenir/construire ? À quels groupements appartiennent-ils et quels accords s’appliquent ? Quelles conventions sont signées, quels engagements pris ? Quels volumes réalisés, prévisionnels, restant à faire ? Quels assortiments sont incomplets, quelles nouveautés référencées, quelle évolution des DN ? Quelles mises en avant du plan trade sont réalisées ? Qui visiter, quand ont eu lieu les dernières visites, quels RDV sont planifiés ? Où en est mon CA ? Quelles actions sont prioritaires ?

## Principes (par ordre de priorité)
1. Fiabilité absolue des calculs.
2. Cohérence et traçabilité des données.
3. Simplicité d’usage quotidien.
4. Accès rapide à l’information client.
5. Organisation claire.
6. Interface professionnelle premium.
7. Performance technique.
8. Évolutivité et maintenabilité.

Une information inconnue reste inconnue ; une information non confirmée n’est jamais présentée comme validée ; une prévision n’est jamais assimilée à une facturation.

## Ce que la V1 couvre
Fondations techniques, jeu fictif de 30 pharmacies, tableau de bord, liste des pharmacies, fiche client (5 onglets opérationnels), moteur de calcul testé, import CSV/XLSX réel sur format fictif. Le reste suit `ROADMAP.md`.

## Hors périmètre volontaire
Données réelles (tant que non autorisées), cloud, IA connectée aux données, déploiement public. L’architecture prévoit un futur assistant (couche `domain/analysis` réutilisable) sans le connecter.
