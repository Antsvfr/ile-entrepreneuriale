# Chantiers d'UPSA Sales Pilot

Aucun dépôt Git n'est connu pour ce projet : il n'existe donc **pas de branches** à lister. À la place, les chantiers de la feuille de route (`dossier/projet/docs/ROADMAP.md`) et l'état annoncé par le dossier du 6 nov. 2026.

| Chantier | État annoncé | Remarque |
|---|---|---|
| Phases 1, 2, 3, 5, 6, 7 | Faites | 99 tests et 7 parcours navigateur au vert le 22 oct., sur données fictives |
| Phase 4 — importations avancées | En attente | Volontaire : les formats (sell-in R sur O, sell-out, Y2OBIC, PDF) ne peuvent pas être inventés |
| Phase 8 — optimisation | Partielle | Reste : chiffrement, code d'accès, restauration depuis l'interface, sauvegarde automatique, revue ergonomique |
| Connecteur X20 Cockpit Territoire | Fait (22 oct.) | **Uniquement sur le Mac** : migration 3, `src/domain/cockpit/`, écrans Cockpit, `start:demo` |

**Proposition (à valider) :** initialiser Git **en local sur le Mac** (sans dépôt distant, la règle 4 interdit le push) pour avoir de vraies branches par chantier, avec `.gitignore` excluant `data/`.
