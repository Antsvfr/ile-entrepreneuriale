PROMPT FONDATEUR OFFICIEL — UPSA SALES PILOT
Version 3.0 — Création de l'application de pilotage commercial pharmacie
1. TA MISSION
Tu es Claude Code, chargé de concevoir et développer une application professionnelle intitulée UPSA Sales Pilot.
Tu dois agir comme une équipe d'experts réunissant les compétences suivantes :

* Architecte logiciel senior.
* Développeur full-stack React / TypeScript.
* Expert CRM et gestion de portefeuilles commerciaux.
* Expert en analyse de données commerciales pharmaceutiques.
* Expert en modélisation de bases de données.
* Spécialiste Excel, CSV, PDF et ETL.
* Expert en calculs de performance commerciale.
* Expert UX/UI et design d'applications professionnelles premium.
* Expert en sécurité des données, qualité et tests automatisés.

Tu dois exploiter les skills et sous-agents déjà intégrés au projet.
Objectif : construire progressivement une véritable application utilisable, et non une simple maquette ou une succession de tableaux statiques.
Je veux un outil fiable, rapide, très bien organisé, visuellement haut de gamme et capable d'évoluer sur plusieurs années.
Tu dois commencer le développement dans cette session, tout en respectant une architecture évolutive.
2. CONTEXTE PROFESSIONNEL
L'utilisatrice est commerciale pour le laboratoire UPSA depuis 15 ans.
Elle vient de reprendre un nouveau secteur et souhaite disposer d'un outil complet pour connaître ses pharmacies, suivre ses engagements, identifier ses opportunités et piloter ses résultats commerciaux.
L'application doit permettre de répondre rapidement à ces questions :

* Qui sont mes clients ?
* Quels clients sont ACP1 ou ACP2 ?
* Quels clients sont à défendre, maintenir ou construire ?
* À quels groupements appartiennent-ils ?
* Quels accords commerciaux s'appliquent à chacun ?
* Quelles conventions sont signées ?
* Quels engagements ont été pris ?
* Quels volumes ont été réalisés ?
* Quels sont les volumes prévisionnels ?
* Combien reste-t-il à réaliser ?
* Quels assortiments sont présents ou incomplets ?
* Quelles références doivent être développées ?
* Quelles mises en avant du plan trade sont réalisées ?
* Quels clients doivent être visités ?
* Quand ont eu lieu les dernières visites ?
* Quels rendez-vous sont planifiés ?
* Quelles nouveautés sont référencées ?
* Quelle est l'évolution des DN ?
* Où en est mon chiffre d'affaires ?
* Quelles sont les actions commerciales prioritaires ?

L'objectif est de centraliser les informations, d'éviter les doubles saisies et de transformer des fichiers commerciaux dispersés en informations immédiatement exploitables.
3. ENVIRONNEMENT CLAUDE CODE ET SKILLS EXISTANTS
Un pack de skills a déjà été préparé pour ce projet.
Avant de développer :

1. Inspecte le dossier `.claude/skills/`.
2. Identifie tous les skills réellement présents.
3. Lis leurs descriptions et active les compétences pertinentes selon les tâches.
4. Inspecte `.claude/agents/`.
5. Identifie les sous-agents installés.
6. Analyse le fichier `CLAUDE.md` s'il existe.
7. Vérifie la cohérence entre le contexte métier et les instructions des skills.
8. Corrige uniquement les erreurs nécessaires, sans remplacer inutilement les fichiers valides.

Ne recrée pas les skills déjà existants.
Les compétences attendues couvrent notamment :

* Importation pharmaceutique.
* Qualité des données.
* Fiches clients.
* Classification commerciale.
* Assortiments.
* Sell-in et sell-out.
* Données Y2OBIC.
* Performance commerciale.
* Calcul des volumes restants.
* Scénarios de croissance.
* Conventions et engagements.
* Groupements.
* Plans trade.
* Factures.
* Livraisons et reliquats.
* Rendez-vous et visites.
* Lancements produits.
* Distribution numérique.
* Plans d'action.
* Reporting.
* Sécurité des données.

Les skills guident le développement. Les fonctionnalités réelles doivent être implémentées dans le code de l'application.
Si des skills sont absents ou invalides, documente le problème et poursuis avec les instructions métier disponibles.
4. PRINCIPES FONDAMENTAUX
L'application devra respecter les priorités suivantes :

1. Fiabilité absolue des calculs.
2. Cohérence et traçabilité des données commerciales.
3. Simplicité d'utilisation quotidienne.
4. Rapidité d'accès aux informations clients.
5. Organisation claire des fonctionnalités.
6. Interface visuelle professionnelle et premium.
7. Performance technique.
8. Évolutivité et maintenabilité.

Ne privilégie jamais un affichage impressionnant au détriment de données exactes.
Une information inconnue doit rester inconnue.
Une information non confirmée ne doit jamais être présentée comme validée.
Une prévision ne doit jamais être assimilée à une facturation réelle.
PARTIE I — ARCHITECTURE DE L'APPLICATION
5. ARCHITECTURE TECHNIQUE
Je souhaite une application web locale, optimisée pour un ordinateur.
Elle devra pouvoir être exécutée sur mon ordinateur sans hébergement distant obligatoire.
Technologies envisagées :

* React.
* TypeScript strict.
* Vite.
* Tailwind CSS.
* Composants accessibles et réutilisables.
* TanStack Table.
* Recharts.
* Backend local Node.js si nécessaire.
* SQLite pour le stockage.
* Bibliothèques fiables pour les imports Excel et CSV.
* Module spécifique d'analyse des PDF.
* Tests automatisés avec Vitest et Playwright lorsque pertinent.

Tu peux adapter cette architecture si tu démontres qu'une autre solution est plus pertinente.
Sépare clairement :

* L'interface utilisateur.
* La logique commerciale.
* La gestion des fichiers.
* Les calculs.
* La base de données.
* Les règles de classification.
* Les modules d'analyse.
* Les exports.

Évite les fichiers géants, les composants monolithiques et les dépendances inutiles.
Prépare une architecture capable d'accueillir ultérieurement un assistant IA, mais sans connecter de service d'IA externe aux données commerciales dans la première version.
6. CONFIDENTIALITÉ ET SÉCURITÉ
Le projet peut, à terme, traiter des informations commerciales confidentielles.
Pour la phase de développement :

* Utilise exclusivement des données fictives.
* Ne demande pas d'exports UPSA réels.
* N'envoie aucune donnée métier à un service distant.
* Ne déploie pas l'application publiquement.
* Ne connecte pas de service cloud non autorisé.
* Ne publie aucune donnée commerciale sur GitHub.
* Ne crée pas de télémétrie ou de suivi externe.
* Ne charge pas de ressources tierces depuis l'interface sans nécessité validée.
* Ne traite aucune donnée individuelle de patient.
* Prévois des contrôles de sécurité des fichiers importés.
* Documente les risques du stockage local, notamment les sauvegardes et les accès non autorisés.

L'utilisation future de véritables données doit rester soumise à la validation des règles de sécurité et de confidentialité de l'entreprise.
PARTIE II — FICHE PHARMACIE À 360°
7. RÉFÉRENTIEL CLIENT
La fiche pharmacie est le cœur de l'application.
Chaque pharmacie doit disposer d'une fiche individuelle complète, organisée en plusieurs onglets.
Informations à enregistrer :

* Identifiant client stable.
* Nom de la pharmacie.
* Adresse.
* Téléphone.
* E-mail professionnel.
* Contact commercial principal, si disponible.
* Groupement.
* Cible ACP1 ou ACP2.
* Segmentation : à défendre, à maintenir, à construire.
* Historique des classifications.
* Informations complémentaires.
* Date de dernière actualisation.

Les règles officielles ACP1/ACP2 seront renseignées ultérieurement.
Prévois donc une classification manuelle et un moteur de règles paramétrable. N'invente pas les seuils.
Une pharmacie doit pouvoir être retrouvée facilement par recherche, identifiant, nom, groupement, cible ou segmentation.
8. MODULE PARACÉTAMOL
Créer un espace dédié au paracétamol dans chaque fiche client.
Volumes 2026
Afficher :

* Volumes facturés 2026.
* Volumes prévisionnels 2026.
* Total facturé + prévisionnel estimé au 31/12/2026.
* Périmètre et date d'actualisation.

Volumes 2027
Afficher :

* Volumes facturés 2027.
* Volumes prévisionnels 2027.
* Total facturé + prévisionnel 2027.
* Engagement contractuel signé.
* Pourcentage d'avancement.
* Volume restant à facturer par rapport à l'engagement.
* Volume restant estimé en intégrant le prévisionnel.
* Évolution par rapport à la base 2026 validée.
* Objectif de croissance +3 %.
* Objectif de croissance +6 %.
* Écart restant pour chacun de ces scénarios.

Exclusion obligatoire : les volumes paracétamol utilisés dans ces calculs doivent être hors pédiatrie et hors codéine, selon une nomenclature de références vérifiée.
Les mêmes critères d'exclusion doivent être appliqués aux périodes comparées.
Formules initiales :
Volume estimé = volume facturé + volume prévisionnel non déjà facturé.
Objectif +3 % = volume de référence 2026 × 1,03.
Objectif +6 % = volume de référence 2026 × 1,06.
Reste contractuel à facturer = engagement signé − facturé éligible.
Reste estimé = engagement signé − (facturé éligible + prévisionnel éligible non facturé).
Taux d'avancement = réalisé / objectif de référence × 100.
Le dénominateur utilisé doit toujours être indiqué.
Un reste négatif peut traduire un dépassement : l'interface doit distinguer clairement dépassement, reste à réaliser et absence de données.
Nous sommes actuellement en 2026 : les éventuelles données facturées 2027 ne doivent pas être inventées. Prépare le modèle pour les accueillir lorsqu'elles existeront.
9. MODULE OTC
Créer un espace comparable pour les familles :

* Vitalité.
* Sommeil.
* Hydraphyse.
* Cérélys.

Conserver provisoirement ces libellés, en attendant la validation des noms et correspondances produits.
Pour chaque gamme :

* Volume facturé 2026.
* Prévisionnel 2026.
* Total estimé 2026.
* Facturé 2027.
* Prévisionnel 2027.
* Total estimé 2027.
* Engagement signé.
* Pourcentage d'avancement.
* Reste à facturer.
* Reste estimé avec prévisionnel.
* Évolution par rapport à 2026.
* Objectif +3 %.
* Objectif +6 %.
* Écart aux objectifs.
* Nombre de références présentes.
* Nombre de références manquantes.
* Suivi de l'assortiment.

Les objectifs +3 % et +6 % sont des scénarios de croissance et non nécessairement des engagements signés.
Permettre une lecture par famille et une consolidation OTC sans double comptage.
10. ASSORTIMENTS ET RÉFÉRENCES
Chaque pharmacie devra disposer d'un tableau d'assortiment.
Pour chaque référence :

* Code produit.
* Libellé.
* Famille.
* Assortiment attendu.
* Statut de présence.
* Facturé 2026.
* Prévisionnel 2026.
* Total estimé au 31/12/2026.
* Indicateur d'assortiment Oui / Non / À confirmer.
* Date du dernier constat.
* Source de l'information.
* Action à entreprendre.

La présence effective d'une référence ne doit pas être déduite automatiquement d'un simple volume historique.
Les règles permettant de déterminer l'assortiment devront être paramétrables.
11. CONVENTIONS, COMMANDES ET ENGAGEMENTS
Dans la fiche client, afficher :

* Convention signée : Oui / Non / À vérifier.
* Date de signature.
* Dates de validité.
* Type de convention.
* Groupement associé.
* Contrats et engagements.
* Volumes engagés.
* Volumes commandés.
* Volumes facturés.
* Volumes livrés.
* Reliquats.
* Reste à honorer.
* Date de dernière facture.
* Documents justificatifs.
* Actions de suivi.

Ne confonds jamais commande, facture, livraison, reliquat et engagement.
Les engagements signés doivent pouvoir être reliés à des produits ou à des familles, sur des périodes clairement définies.
12. VISITES COMMERCIALES ET RENDEZ-VOUS
Chaque pharmacie doit afficher :

* Objectif annuel de visites.
* Nombre de visites réalisées.
* Visites restant à effectuer.
* Dernière visite.
* Prochaine visite.
* Rendez-vous planifié : Oui / Non.
* Date du prochain rendez-vous.
* Dernière facture.
* Historique des visites.
* Comptes rendus.
* Tâches à effectuer.
* Engagements issus des visites.

Une visite planifiée ne doit jamais être considérée comme réalisée.
Prévoir un calendrier commercial et des alertes sur les clients à visiter.
13. NOUVEAUTÉS ET DISTRIBUTION NUMÉRIQUE
Pour chaque pharmacie et chaque nouveauté :

* Produit concerné.
* Date de lancement.
* Référencement attendu.
* Référencement effectué : Oui / Non / À confirmer.
* Première commande.
* Première facture.
* Volume.
* Date du dernier constat.
* Action restant à réaliser.

Le système devra ultérieurement calculer la DN par produit, par groupement et sur l'ensemble du secteur.
PARTIE III — GROUPEMENTS ET PLAN TRADE
14. FICHE GROUPEMENT
Chaque groupement doit disposer d'une fiche complète.
Elle comprendra :

* Identifiant.
* Nom.
* Pharmacies rattachées.
* Accords applicables.
* Conventions.
* Dates de validité.
* Objectifs commerciaux.
* Documents sources.
* Plan trade.
* Performances consolidées.

Une pharmacie peut changer de groupement : conserve l'historique d'appartenance avec les dates d'effet.
15. PLAN TRADE MENSUEL
Je veux importer les plans trade et accords commerciaux pour suivre les actions prévues chaque mois.
Pour chaque action trade :

* Groupement.
* Mois.
* Pharmacie concernée.
* Famille.
* Produit.
* Type de mise en avant.
* Date prévue.
* Date réalisée.
* Engagement commercial.
* Volume prévu.
* Volume réalisé.
* Écart.
* Statut.
* Justificatif éventuel.

Prévois les statuts :

* Prévu.
* En cours.
* Réalisé et confirmé.
* Non réalisé confirmé.
* À vérifier.
* Annulé.

Je veux consulter les tâches à effectuer chaque mois, les mises en avant réalisées et les engagements commerciaux non honorés.
Une action présente dans la fiche groupement doit apparaître également dans la fiche de la pharmacie concernée.
Évite absolument les doubles saisies.
PARTIE IV — TABLEAU DE BORD SECTEUR
16. CHIFFRE D'AFFAIRES
Le tableau de bord doit présenter :

* CA total du secteur.
* CA paracétamol.
* CA paracétamol non remboursé.
* CA OTC.
* Objectif global.
* Taux d'avancement.
* Évolution par rapport à la période de référence.
* Reste à réaliser.

La sous-catégorie paracétamol non remboursé peut déjà appartenir au CA paracétamol.
Interdiction de la compter deux fois.
Construis une classification des produits permettant des consolidations sans double comptage.
Distingue facturé et prévisionnel.
17. RESTES À FAIRE
Présente un tableau détaillé pour :

* Paracétamol.
* Vitalité.
* Sommeil.
* Hydraphyse.
* Cérélys.

Pour chaque famille :

* Objectif.
* Facturé.
* Prévisionnel.
* Total estimé.
* Reste à facturer.
* Reste estimé après prévisionnel.
* Pourcentage d'atteinte.
* Évolution.

Permets de retrouver les pharmacies qui contribuent au résultat ou expliquent les écarts.
18. PILOTAGE DES RENDEZ-VOUS
Afficher :

* Nombre total de pharmacies.
* Pharmacies avec rendez-vous.
* Pharmacies sans rendez-vous.
* Pourcentage de pharmacies ayant un rendez-vous futur.
* Nombre annuel de visites attendues.
* Visites réalisées.
* Visites planifiées.
* Visites restant à effectuer.
* Liste des pharmacies à contacter.
* Répartition ACP1/ACP2.
* Répartition par segmentation commerciale.

Distingue le taux de pharmacies ayant un rendez-vous et le taux de couverture du plan annuel de visites.
Ne compte pas plusieurs rendez-vous d'une même pharmacie comme plusieurs pharmacies couvertes.
19. PRIORITÉS COMMERCIALES
Prépare un système de priorisation basé sur des règles transparentes.
Exemples :

* ACP1 sans rendez-vous.
* Client à défendre avec CA en baisse.
* Convention manquante.
* Engagement non honoré.
* Assortiment incomplet.
* Nouveauté non référencée.
* Action trade en retard.
* Reliquat important.
* Objectif de volume non atteint.

Chaque priorité doit expliquer pourquoi elle est proposée.
Les seuils de décision doivent être configurables.
PARTIE V — IMPORTATIONS ET ANALYSE DES DONNÉES
20. CENTRE D'IMPORTATION
L'application devra prendre en charge :

1. Tableau sell-in, appelé notamment « R sur O ».
2. Tableau assortiment.
3. Tableau sell-out.
4. Tableau Y2OBIC.
5. Conventions.
6. Accords groupements.
7. Plans trade.

Formats :

* Excel.
* CSV.
* PDF.

La fréquence des exports est variable.
Les véritables structures des exports seront fournies plus tard, sous réserve des autorisations nécessaires.
Ne suppose pas connaître la signification de toutes leurs colonnes.
En particulier, ne confonds pas Y2OBIC avec un autre outil sur la base d'une ressemblance de nom.
21. PARCOURS D'IMPORTATION
Prévois :

1. Sélection du fichier.
2. Détection du format.
3. Identification des feuilles ou pages.
4. Prévisualisation.
5. Identification des colonnes.
6. Proposition de correspondances.
7. Choix de la période.
8. Vérification des unités.
9. Détection des doublons.
10. Vérification des anomalies.
11. Validation par l'utilisateur.
12. Enregistrement.
13. Mise à jour des tableaux concernés.
14. Conservation de l'historique.

Les importations doivent être répétables sans créer de doubles comptages.
Gère les particularités des fichiers français : virgules décimales, séparateurs, dates, espaces de milliers et encodages.
Pour les PDF, prévoir l'extraction du texte disponible et une étape de vérification humaine. L'OCR local pourra être ajouté ultérieurement.
22. TRAÇABILITÉ
Chaque chiffre important doit conserver :

* Sa source.
* Sa période.
* Sa date d'importation.
* Sa date de référence.
* Son unité.
* Son statut : réalisé, prévisionnel, objectif ou engagement.
* Les transformations appliquées.

Une donnée manquante ne doit jamais être remplacée silencieusement par zéro.
Ne mélange pas des périodes partielles et complètes sans le signaler.
PARTIE VI — EXPÉRIENCE UTILISATEUR
23. IDENTITÉ VISUELLE
Je souhaite une application d'une qualité visuelle comparable à celle d'un logiciel SaaS professionnel haut de gamme.
Le design doit être :

* Premium.
* Moderne.
* Élégant.
* Sobre.
* Très structuré.
* Lisible.
* Intuitif.
* Fluide.
* Rapide.

L'application ne doit pas ressembler à un prototype généré automatiquement.
Adopte une navigation latérale claire, des tableaux soignés, une typographie cohérente, des couleurs fonctionnelles, des cartes KPI et des graphiques utiles.
Utilise un accent rouge discret, sans reproduire une identité officielle UPSA non autorisée.
Le design doit avant tout être adapté à une utilisation quotidienne sur ordinateur.
24. NAVIGATION PRINCIPALE
Prévoir les sections :

1. Tableau de bord.
2. Mes pharmacies.
3. Groupements.
4. Performance commerciale.
5. Assortiments.
6. Lancements et DN.
7. Visites et rendez-vous.
8. Plan d'action.
9. Centre d'importation.
10. Paramètres métier.

Chaque rubrique doit avoir une structure claire.
Évite la multiplication des menus redondants.
25. FICHE CLIENT
La fiche client devra être organisée par onglets :

* Vue d'ensemble.
* Paracétamol.
* OTC.
* Assortiments.
* Conventions et engagements.
* Commandes, factures et reliquats.
* Visites et rendez-vous.
* Nouveautés.
* Plan trade et actions.

Depuis chaque onglet, l'utilisateur doit pouvoir comprendre les informations affichées et accéder facilement à leur source.
PARTIE VII — PREMIÈRE VERSION À DÉVELOPPER IMMÉDIATEMENT
26. PÉRIMÈTRE DE CETTE SESSION
Je ne veux pas que tu essaies de programmer l'intégralité du logiciel d'un seul coup.
Je veux une première version solide, fonctionnelle et testée, qui servira de base aux développements suivants.
Développe immédiatement les éléments suivants.
A. Initialisation technique

* Projet React / TypeScript.
* Architecture modulaire.
* Configuration des dépendances.
* Persistance locale.
* Modèle de données initial.
* Migrations si nécessaire.
* Routage et navigation.
* Gestion des erreurs.
* Documentation.
* Scripts de lancement et de test.

B. Jeu de données fictives
Crée environ 30 pharmacies fictives.
Prévois plusieurs groupements fictifs.
Génère des scénarios commerciaux représentatifs :

* ACP1 et ACP2.
* À défendre, maintenir et construire.
* Pharmacies avec et sans rendez-vous.
* Engagements signés et non signés.
* Assortiments complets et incomplets.
* Volumes et objectifs différents.
* Actions trade réalisées ou en attente.
* Nouveautés référencées et non référencées.

Tous les chiffres doivent être clairement identifiés comme fictifs.
C. Tableau de bord
Crée une page d'accueil professionnelle comprenant :

* CA simulé.
* Objectif.
* Avancement.
* Performance par famille.
* Nombre de pharmacies.
* Rendez-vous.
* Visites.
* Priorités commerciales.

Tous les indicateurs doivent provenir du moteur de calcul et des données de démonstration, et non de valeurs écrites directement dans les composants.
D. Liste des pharmacies
Développe un tableau interactif avec :

* Recherche.
* Filtres.
* Classification ACP.
* Groupement.
* Segmentation.
* Informations de contact.
* Dernière visite.
* Prochain rendez-vous.
* Accès à la fiche client.

E. Fiche client V1
Développe les premiers onglets :

* Identification.
* Paracétamol.
* OTC.
* Visites.
* Conventions et engagements.

Les autres onglets peuvent être préparés et clairement indiqués comme non encore disponibles.
F. Moteur de calcul
Implémente et teste :

* Volumes facturés + prévisionnels sans double comptage.
* Objectifs +3 % et +6 %.
* Restes à faire.
* Taux d'avancement.
* Évolutions entre périodes comparables.
* Périmètres d'exclusion.
* Données manquantes.
* Calculs agrégés par gamme.

G. Importation initiale
Développe un premier parcours réel d'import CSV/XLSX fictif :

* Sélection.
* Aperçu.
* Correspondance des colonnes.
* Validation.
* Gestion du doublon de fichier.
* Persistance.
* Actualisation des indicateurs.

Les modules complexes PDF, Y2OBIC et plans trade multi-documents pourront être développés lors de chantiers ultérieurs.
27. TESTS
Exécute des tests pour les fonctions critiques :

* Calcul du CA.
* Absence de double comptage.
* Calcul des volumes.
* Exclusion des références non éligibles.
* Objectifs +3 % et +6 %.
* Engagements.
* Données manquantes.
* Division par zéro.
* Évolution des périodes.
* Import d'un fichier valide.
* Gestion des doublons.
* Persistance.
* Navigation.
* Affichage des fiches clients.

Ajoute des tests de parcours utilisateur lorsque l'environnement le permet.
Ne déclare pas une fonction opérationnelle si elle n'a pas été réellement développée.
PARTIE VIII — ROADMAP ET MAINTENANCE
28. DOCUMENTATION
Crée ou complète :

* `README.md`
* `CLAUDE.md`
* `docs/PROJECT_VISION.md`
* `docs/ARCHITECTURE.md`
* `docs/DATA_MODEL.md`
* `docs/BUSINESS_RULES.md`
* `docs/IMPORT_SPEC.md`
* `docs/SECURITY.md`
* `docs/ROADMAP.md`
* `docs/DECISIONS.md`

Les instructions importantes doivent pouvoir être retrouvées dans de futures sessions Claude Code.
29. ORDRE DE DÉVELOPPEMENT FUTUR
Prépare la roadmap suivante :
Phase 1 — Fondations et premiers écrans
Architecture, données fictives, dashboard, clients, calculs et import initial.
Phase 2 — Fiche pharmacie complète
Paracétamol 2026/2027, OTC, assortiments, contrats, visites et nouveautés.
Phase 3 — Groupements et plans trade
Accords, tâches mensuelles, mises en avant et suivi des engagements.
Phase 4 — Importations avancées
Sell-in R sur O, sell-out, assortiment, Y2OBIC et documents PDF.
Phase 5 — Performances et pilotage
Tableaux de bord complets, objectifs, restes à faire, segmentation et rendez-vous.
Phase 6 — Lancements et DN
Suivi par client, nouveautés et évolutions temporelles.
Phase 7 — Intelligence commerciale
Analyse des opportunités, préparation de visite et recommandations explicables.
Phase 8 — Optimisation finale
Fiabilité, performance, ergonomie, sécurité, tests et documentation.
Les phases pourront être ajustées selon l'avancement réel.
30. RÈGLES DE DÉVELOPPEMENT
Respecte les exigences suivantes :

* Inspecte le projet avant chaque modification importante.
* Réutilise les modules existants.
* Ne duplique pas les fonctions de calcul.
* Préserve la compatibilité des données.
* Réalise des modifications progressives.
* Écris du code maintenable.
* Ajoute des tests pour les fonctions critiques.
* Mets à jour la documentation.
* Conserve les décisions d'architecture.
* Utilise les skills appropriés.
* Ne crée pas de fonctionnalités factices présentées comme opérationnelles.
* N'invente jamais de règles métier officielles UPSA.
* Ne manipule pas de données réelles sans autorisation.
* Ne déploie rien et ne pousse aucun code sur un dépôt distant sans autorisation.
* Signale clairement les informations à confirmer.

Tu peux réaliser de manière autonome les opérations de développement locales, non destructives et réversibles.
31. RÉSULTAT ATTENDU À LA FIN DE CETTE SESSION
Je veux que tu m'indiques précisément :
1. Architecture

* Technologies retenues.
* Organisation des dossiers.
* Modèle de données.
* Décisions importantes.

2. Développement effectué

* Modules créés.
* Écrans fonctionnels.
* Calculs disponibles.
* Importation disponible.

3. Skills et agents

* Compétences détectées.
* Compétences utilisées.
* Éventuelles corrections nécessaires.

4. Tests

* Tests exécutés.
* Réussites.
* Échecs éventuels.
* Fonctionnalités non encore testées.

5. Utilisation

* Commandes exactes pour installer et lancer le projet.
* Adresse locale de l'application.
* Procédure de découverte du jeu fictif.
* Méthode pour tester une importation.

6. Suite

* Fonctionnalités terminées.
* Fonctionnalités restant à développer.
* Trois prochaines priorités.
* Proposition du prochain chantier.

INSTRUCTION FINALE
UPSA Sales Pilot doit devenir mon véritable centre de pilotage commercial quotidien.
Je veux pouvoir ouvrir une pharmacie et comprendre immédiatement sa situation commerciale, ses volumes, ses engagements, ses assortiments, ses visites, ses nouveautés et ses opportunités.
Je veux aussi pouvoir analyser l'ensemble de mon secteur en quelques clics.
Le logiciel doit être construit comme un produit professionnel, et non comme une démonstration technique.
Commence maintenant.
Inspecte les skills installés et le dossier du projet, définis les fondations techniques, puis développe la première version fonctionnelle décrite dans ce prompt.
Ne te limite pas à une analyse : crée réellement le projet, les composants, les calculs, les données de démonstration et les tests.
À la fin, fournis un bilan complet du travail réalisé et les instructions exactes pour lancer l'application.
