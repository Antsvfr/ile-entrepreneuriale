# Conseil — 2026-11-06 — Refonte en métropole insulaire 3D

## Prompt d'origine
Transformer l'île tropicale en métropole insulaire futuriste : gratte-ciel variés, quartiers (centre-ville, technologique, entreprises avec un siège par projet, résidentiel, stratégique avec un « cerveau », nature), routes, ponts, ports, véhicules, matériaux PBR, jour/nuit, instancing, LOD, qualité adaptative, caméra cinématique. Conserver tout le système d'agents ; tester dans le navigateur après chaque étape.

## Avis
- **Clarté** : remplacer ou faire coexister ? quel critère de réussite ? quelles données pilotent les véhicules ? Besoin de jalons et de points de validation.
- **Exigence** : preuves visuelles par quartier, de jour et de nuit ; checklist de non-régression ; budget de performance chiffré. Pièges : tout en un bloc, rendu logiciel trop lent pour tester, décor sans lien avec les vraies missions.
- **Stratégie** : mauvais moment (LexNote et REV-EM ont du travail réel bloquant) ; raccourci proposé : jour/nuit + quelques gratte-ciel + caméra. **Écarté : Anton a demandé explicitement la métropole complète.**

## Prompt final
Refondre `village/` par jalons testés dans le navigateur, sans toucher à `registre.json` (source de vérité) ni au système d'agents. Jalon 1 : trois terrains et deux ponts, réseau routier, six quartiers, un siège unique par projet, jour/nuit, caméra cinématique. Jalon 2 : véhicules, ports, instancing, LOD, qualité adaptative, chargement progressif. Sièges, critiques et courriers restent branchés sur `registre.json` et `etat-de-l-ile.json`.
