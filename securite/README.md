# Sécurité

- `garde.py` : hook `PreToolUse` (autoriser / bloquer / approbation présidentielle). Échoue fermé (`|| exit 2`).
- `confinement.py` : confinement des imports des processus privilégiés (`python3 -I -S`, chargement par chemin exact).
- `STOP` (absent par défaut, non versionné) : arrêt d'urgence ; `./ile arret-urgence on|off`.
- `acces.json` (non versionné) : noms d'hôte de l'accès distant (`./ile distant activer`).

Étape 2 **NON VALIDÉE** : le garde reste contournable par des commandes lisibles (`env cp`, `find -exec cp`,
`git --git-dir/--work-tree`, `curl -o`, `patch`, `git push --all`, configuration `mirror`). Preuves :
`audit/rapports/2026-11-06-finalisation-etape-2.md`, `audit/preuves-brutes/`. Cible : `docs/architecture/SEPARATION-DES-PRIVILEGES.md`.
