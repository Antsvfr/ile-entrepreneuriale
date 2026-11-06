"""Fixture du pouvoir présidentiel d'approbation et de refus : un registre TEMPORAIRE, une identité présidentielle DE TEST
(phrase de test connue du seul test, jamais celle du président), des propositions soumises par les vrais mécanismes.
Jamais le registre officiel, jamais publié.
    ILE_OPS=<dossier temporaire> FIXTURE_PHRASE=<phrase de test> python3 -I -S tests/fixture_decisions.py
Le journal de départ (copie du journal officiel, sans identité présidentielle) doit déjà être dans ILE_OPS."""
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for d in ("securite", "presidence", "orchestrateur"):
    sys.path.insert(0, str(RACINE / d))
ops = Path(os.environ.get("ILE_OPS") or "/nulle-part").resolve()
assert os.environ.get("ILE_OPS") and ops != (RACINE / "orchestrateur" / "registre").resolve(), "ILE_OPS temporaire obligatoire"
assert os.environ.get("FIXTURE_PHRASE"), "FIXTURE_PHRASE (phrase DE TEST) obligatoire"
import ile  # noqa: E402
import president  # noqa: E402
import propositions as P  # noqa: E402

assert ile.JOURNAL.resolve().parent == ops, "le journal visé n'est pas celui du dossier temporaire"
president.ITERATIONS = 2000            # dérivation rapide (le nombre réel de tours est inscrit dans l'identité de test)
if not ile.identite_courante():
    ile.creer_identite(os.environ["FIXTURE_PHRASE"], canal="fixture de test")
MAIRE, HOOK = ile._auteur("maire", "declare"), ile._auteur("claude-code", "hook")
run = lambda role: ile.auteur_cli(role, ile.run_debut(role, HOOK)["donnees"]["run"])
chef = run("chef-rev-em")
p1 = P.creer("rev-em", "Atelier de relecture avec la Forge (fixture)", "Mettre en place une relecture hebdomadaire des PR de REV-EM par la Forge.",
             "projet", "Réduire les régressions avant fusion", "Une demi-journée par semaine de la Forge ; PR fusionnées plus lentement",
             chef, cout="une demi-journée par semaine", risques=["ralentissement des fusions"], pieces=["projets/rev-em/etat-des-lieux.md"],
             institutions=["forge"], soumettre=True)["donnees"]["proposition"]
p2 = P.creer("mairie", "Nouveau quartier d'innovation (fixture)", "Ouvrir le chantier « innovation » à une première entreprise.", "strategie",
             "Accueillir un nouveau projet", "Une maison de plus à suivre", MAIRE, risques=["dispersion"], institutions=["conseil"], soumettre=True)["donnees"]["proposition"]
p3 = P.creer("rev-em", "Budget d'outillage (fixture)", "Acheter un outil d'analyse statique.", "budget", "Détecter les erreurs plus tôt",
             "Abonnement mensuel", chef, soumettre=True)["donnees"]["proposition"]
P.transmettre(p2, "president", MAIRE)
v = ile.verifier()
print(f"fixture : {v['n']} événements, journal {'intègre' if v['ok'] else 'ALTÉRÉ'} · propositions {p1} {p2} {p3}")
