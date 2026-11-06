# Données publiques — conséquence du dépôt public (décision présidentielle du 6 novembre 2026)

Le président a choisi de garder `Antsvfr/ile-entrepreneuriale` **public**. Conséquences, assumées :

- **Tout ce qui est au registre est public** : organisation (entreprises, départements, postes, agents), missions,
  livrables, validations, remontées, **messages internes**, réunions et comptes rendus, exécutions d'agents, refus du garde.
  Le journal est dans le dépôt ; la version web (GitHub Pages) l'affiche et le vérifie.
- **Aucune « confidentialité » n'est simulée** : pas de menu caché, pas de fausse connexion, pas de données présentées
  comme privées. Les bureaux affichent un bandeau rappelant que leurs données sont publiques.
- **Ne jamais écrire au registre** : secret, mot de passe, jeton, clé, variable d'environnement, donnée personnelle
  réelle d'un tiers. Les tests automatiques vérifient l'absence de secrets dans les instantanés publiés.
- **Fonctionnalités bloquées faute d'architecture confidentielle** : messagerie confidentielle, documents internes
  non publiables, données clients (UPSA…), évaluations nominatives de personnes réelles. Elles exigeraient un stockage
  hors du dépôt public (serveur privé ou dépôt privé) : **non construit**, à décider par le président.
