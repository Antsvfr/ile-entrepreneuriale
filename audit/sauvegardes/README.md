# Sauvegardes

`2026-11-06/` : état de l'ancien dépôt `Antsvfr/simulation-questionnaire` au moment de la migration (branche
`claude/bold-noether-l93mmy`, commit `a5c4d72`) :
- `depot-complet.bundle` : tout l'historique git et toutes les branches. **Non publié** (ignoré par git) : c'est une copie
  de l'ancien dépôt, qui reste en ligne comme référence historique (`git clone https://github.com/Antsvfr/simulation-questionnaire`) ;
  son empreinte figure dans `EMPREINTES.sha256` ;
- `modifications-non-commitees.patch` : les corrections de sécurité de l'étape 2, jamais commitées dans l'ancien dépôt
  (les fichiers nouveaux, `confinement.py`, `test_confinement.py` et le rapport de finalisation, sont listés dans
  `non-suivis.txt` et migrés dans le dépôt) ;
- `modifications-forgeron.patch`, `garde.py.forgeron.txt`, `garde.py.commit-a5c4d72.txt` : la sauvegarde du Forgeron ;
- `empreintes-ancien-depot.sha256` : empreinte de chaque fichier de l'ancien dépôt avant la migration ;
- `EMPREINTES.sha256` : empreintes de ce dossier (sur un clone, le bundle n'étant pas publié : `sha256sum -c --ignore-missing EMPREINTES.sha256`).
