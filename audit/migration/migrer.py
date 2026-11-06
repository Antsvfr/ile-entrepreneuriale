#!/usr/bin/env python3
"""Migration locale de l'île : ancien dépôt (simulation-questionnaire) → nouveau dossier (ile-entrepreneuriale).

Lecture seule sur la source. Copie selon une correspondance explicite, ne copie aucun fichier d'exécution ignoré
(caches, journaux du serveur, verrous, état recalculé), écrit audit/migration/correspondance.tsv avec l'empreinte
SHA-256 de chaque fichier source et de sa copie.

    python3 -I -S migrer.py <source: racine de l'ancien dépôt> <destination: nouveau dossier> [--a-blanc]
"""
import hashlib
import os
import shutil
import sys

# (ancien chemin, nouveau chemin) ; un chemin finissant par « / » est un préfixe de dossier. Premier qui correspond.
CORRESPONDANCE = [
    ("ile-des-agents/operations/garde.py", "securite/garde.py"),
    ("ile-des-agents/operations/confinement.py", "securite/confinement.py"),
    ("ile-des-agents/operations/president.py", "presidence/president.py"),
    ("ile-des-agents/operations/signature.py", "presidence/signature.py"),
    ("ile-des-agents/operations/ile.py", "orchestrateur/ile.py"),
    ("ile-des-agents/operations/journal.jsonl", "orchestrateur/registre/journal.jsonl"),
    ("ile-des-agents/operations/preuves.py", "audit/preuves.py"),
    ("ile-des-agents/operations/tests/", "tests/"),
    ("ile-des-agents/.claude/hooks/etat-ile.py", "orchestrateur/hooks/etat-ile.py"),
    ("ile-des-agents/.claude/agents/", "agents/definitions/"),
    ("ile-des-agents/.claude/commands/", "agents/commandes/"),
    ("ile-des-agents/serveur.py", "residence/serveur.py"),
    ("ile-des-agents/village/", "residence/village/"),
    ("ile-des-agents/maisons/", "projets/"),
    ("ile-des-agents/innovation/", "projets/innovation/"),
    ("ile-des-agents/architecture/", "docs/architecture/"),
    ("ile-des-agents/README.md", "docs/README-ile-des-agents.md"),
    ("README.md", "docs/README-depot-historique.md"),
    ("ile-des-agents/CLAUDE.md", "CLAUDE.md"),
    ("ile-des-agents/conseil/", "audit/conseil/"),
    ("ile-des-agents/forge/rapports/", "audit/rapports/"),
    ("ile-des-agents/forge/inspection.sh", "audit/inspection.sh"),
    ("ile-des-agents/journal-de-l-ile.md", "audit/journal-de-l-ile.md"),
    ("ile-des-agents/etat-de-l-ile.json", "orchestrateur/etat-de-l-ile.json"),
    ("ile-des-agents/registre.json", "registre.json"),
    ("ile-des-agents/ile", "ile"),
    ("ile-des-agents/Ouvrir l'île.command", "Ouvrir l'île.command"),
    (".claude/settings.json", ".claude/settings.json"),
]
# Remplacés par une version fusionnée ou recréés (motif écrit dans la table).
FUSIONNES = {
    "CLAUDE.md": "fusionné dans CLAUDE.md (l'ancien ne faisait qu'importer ile-des-agents/CLAUDE.md)",
    "ile-des-agents/.claude/settings.json": "fusionné dans .claude/settings.json (un seul jeu de hooks : la racine est l'île)",
    ".gitignore": "fusionné dans .gitignore (règles Python + fichiers d'exécution de la nouvelle architecture)",
    "ile-des-agents/.gitignore": "fusionné dans .gitignore",
    ".claude/agents": "lien recréé : .claude/agents → ../agents/definitions",
    ".claude/commands": "lien recréé : .claude/commands → ../agents/commandes",
}
EXCLUS_NOMS = {"__pycache__", ".git", "node_modules"}
EXCLUS_FICHIERS = {"etat.json", "serveur.log", ".verrou", ".mission-courante", ".serveur.pid", "capteurs-erreurs.log",
                   "etat-de-l-ile.json.lock", "STOP", "acces.json"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 16), b""):
            h.update(bloc)
    return h.hexdigest()


def cible(rel):
    for ancien, nouveau in CORRESPONDANCE:
        if ancien.endswith("/") and rel.startswith(ancien):
            return nouveau + rel[len(ancien):]
        if rel == ancien:
            return nouveau
    return None


def main():
    src, dst = os.path.realpath(sys.argv[1]), os.path.realpath(sys.argv[2])
    a_blanc = "--a-blanc" in sys.argv
    lignes, exclus, orphelins = [], [], []
    for racine, dossiers, fichiers in os.walk(src):
        dossiers[:] = sorted(d for d in dossiers if d not in EXCLUS_NOMS)
        for nom in sorted(fichiers) + sorted(d for d in os.listdir(racine) if os.path.islink(os.path.join(racine, d)) and os.path.isdir(os.path.join(racine, d))):
            p = os.path.join(racine, nom)
            rel = os.path.relpath(p, src)
            if rel in FUSIONNES:
                exclus.append((rel, FUSIONNES[rel]))
                continue
            if nom in EXCLUS_FICHIERS or nom.endswith((".pyc", ".pyo")) or nom.startswith(".etat-"):
                exclus.append((rel, "fichier d'exécution (ignoré par git, recalculé ou propre à la machine)"))
                continue
            c = cible(rel)
            if c is None:
                orphelins.append(rel)
                continue
            if not a_blanc:
                os.makedirs(os.path.dirname(os.path.join(dst, c)) or dst, exist_ok=True)
                shutil.copy2(p, os.path.join(dst, c))
            lignes.append((rel, c, sha(p)))
    if orphelins:
        print("SANS CORRESPONDANCE (rien n'est perdu en silence) :", *orphelins, sep="\n  ")
        sys.exit(1)
    if not a_blanc:
        os.makedirs(os.path.join(dst, "audit", "migration"), exist_ok=True)
        with open(os.path.join(dst, "audit", "migration", "correspondance.tsv"), "w", encoding="utf-8") as f:
            f.write("ancien_chemin\tnouveau_chemin\tsha256_source\tsha256_copie_initiale\n")
            for rel, c, h in lignes:
                f.write(f"{rel}\t{c}\t{h}\t{sha(os.path.join(dst, c))}\n")
        with open(os.path.join(dst, "audit", "migration", "exclusions.tsv"), "w", encoding="utf-8") as f:
            f.write("ancien_chemin\tmotif\n")
            for rel, motif in exclus:
                f.write(f"{rel}\t{motif}\n")
    print(f"{len(lignes)} fichiers {'à copier' if a_blanc else 'copiés'} · {len(exclus)} exclus ou fusionnés · 0 sans correspondance")


if __name__ == "__main__":
    main()
