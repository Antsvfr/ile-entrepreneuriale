# Maison — Labo Vétotri

**Mission** : développer le chatbot d'Anton (nom actuel : Vétotri, d'autres noms à l'étude).

## Structure
- `src/` — le code du chatbot
- `prompts/` — prompts système versionnés (`v1.md`, `v2.md`…) ; le fichier `actuel.md` indique la version en service
- `tests/` — conversations de test : question attendue → réponse attendue
- `noms.md` — idées de nom
- `journal.md`

## Règles
- Pas de clé d'API dans le code (fichier `.env`, ignoré par git).
- Un changement est **terminé** quand les tests de `tests/` passent et que la Forge l'a vérifié.
