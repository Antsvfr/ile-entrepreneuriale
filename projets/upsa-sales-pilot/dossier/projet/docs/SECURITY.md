# Sécurité et confidentialité

## Principes appliqués en V1
- **Données fictives uniquement** ; aucune donnée patient ; aucun export réel UPSA demandé ni utilisé.
- **Aucune connexion sortante** : pas de cloud, d’API distante, de télémétrie, de CDN ni de police distante (police Inter embarquée). Test automatique `security.test.ts` : aucune URL distante dans le code client/serveur et aucune dépendance de télémétrie.
- Serveur lié à **127.0.0.1** uniquement (inaccessible depuis le réseau).
- En-tête `Host` non local → 403 (protection DNS rebinding) ; requêtes d’écriture avec `Origin` étranger → 403.
- En-têtes : `Content-Security-Policy` (`default-src 'self'`, `frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`.
- Journaux d’erreurs sans contenu métier.
- Aucun déploiement, aucun dépôt distant.

## Fichiers importés
- Taille ≤ 10 Mo, ≤ 100 000 lignes ; corps de requête borné.
- Liste blanche d’extensions + **vérification de signature** : XLSX = archive ZIP (`PK`), CSV = texte sans octet nul, PDF = `%PDF` (reconnu mais non lu en V1).
- `.xls` / `.xlsm` refusés (pas de macros). Les cellules ne sont jamais évaluées ; les cellules commençant par `= + - @` sont signalées (injection de formules) et stockées en texte.
- Nom de fichier assaini ; fichier en attente gardé **en mémoire** 30 min, jamais écrit sur disque avant validation.
- Écriture transactionnelle tout ou rien.

## Risques du stockage local (à connaître)
| Risque | Mesure actuelle | À prévoir avant données réelles |
|---|---|---|
| La base `data/*.db` est **en clair** sur le disque | dossier ignoré par Git | chiffrement du disque (FileVault/BitLocker) obligatoire ; option de chiffrement applicatif |
| Copie / sauvegarde involontaire (cloud de synchronisation, clé USB) | aucune | placer le projet hors des dossiers synchronisés (OneDrive, iCloud, Dropbox) |
| Autre session sur l’ordinateur | serveur local sans authentification | session OS verrouillée ; envisager un code d’accès |
| Perte de données | sauvegarde manuelle locale (`data/backups/`, bouton dans Paramètres) ; pas d’automatisme | sauvegarde régulière vers un support chiffré ; les sauvegardes sont **en clair** comme la base |
| Fichiers exportés (CSV/Excel) | téléchargés dans le dossier choisi par le navigateur ; injection de formule neutralisée | ne pas les envoyer par messagerie ou cloud non autorisé ; les supprimer après usage |
| Saisies modifiables par toute personne ayant accès au poste | journal des saisies (`audit_log`) consultable | code d’accès si poste partagé |
| Claude Code lit les fichiers du projet | données fictives seulement | **ne pas placer de vrais exports dans le projet** sans autorisation explicite ; dossier `real-data/` ignoré par Git |
| Fichiers d’exemple publics dans `public/exemples` | 100 % fictifs | ne jamais y déposer de fichier réel |

Les routes d’écriture reprennent les protections existantes (Host/Origin, JSON uniquement, taille limitée, requêtes SQL paramétrées) et valident chaque champ (`src/server/routes/validate.ts`). Les noms d’export sont pris dans une liste fermée (pas de chemin libre).

## Règles pour les sessions futures
Pas de secret ni de donnée commerciale dans Git ; pas d’ajout de dépendance réseau, d’analytics ou de service d’IA connecté aux données sans accord explicite ; tout nouvel import passe par les mêmes contrôles (`src/server/import/reader.ts`).
