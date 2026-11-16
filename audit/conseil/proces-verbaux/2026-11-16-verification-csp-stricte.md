# Conseil — Vérification publique en politique de sécurité stricte (16 novembre 2026)

Réalisation X-20261116-001 (`/realiser`).

## Demande d'origine
« Passe la page Vérification publique en politique de sécurité de contenu stricte, comme les pages Entreprises et Décisions, sans rien casser. »

## Avis
- **Clarté** — « Stricte » n'est pas défini (`script-src 'self'` seul, ou aussi `object-src 'none'` ?) ; « sans rien casser » n'a pas de critère ; un `verification.js` existe déjà : fusionner ou créer un autre fichier ? Il manque la preuve attendue et le sort de l'instantané publié.
- **Exigence** — Plus aucun script intégré ni attribut `on…=` ; CSP identique à celle d'`entreprise.html` ; preuve en navigateur sans violation CSP, tests réellement exécutés ; un test de non-régression qui interdit le retour de `'unsafe-inline'`. Piège : loger le script dans `verification.js`, moteur pur testé sous Node.
- **Stratégie** — La page qui prouve l'intégrité du registre ne doit pas être le maillon faible ; demande bornée, idéale pour éprouver la chaîne. Déplacer le script tel quel, pas de refonte, ne pas toucher aux styles ; s'arrêter avant commit, push et publication.

## Prompt amélioré
Dans `residence/village/verification.html`, déplace **tel quel** le script intégré dans un nouveau fichier de branchement
servi en `'self'` (distinct de `verification.js`, qui reste le moteur pur), et aligne la balise CSP sur celle
d'`entreprise.html` (`script-src 'self'`, `object-src 'none'` ; `style-src` inchangé). Aucun attribut `on…=`. Ajoute un test
de non-régression qui échoue si un script intégré ou `'unsafe-inline'` revient dans `script-src` de cette page. Prouve, tests
réellement exécutés (unitaires et navigateur), que la page fonctionne à l'identique et sans violation CSP. Travail sur la
branche en cours, sans commit, push ni publication.
