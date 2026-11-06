"""Fixture de la phase 3.4 : un registre TEMPORAIRE rempli par les mécanismes réels (autorisations des phases 3.1–3.3),
puis l'instantané correspondant, dans une COPIE du site. Jamais le registre officiel.
    ILE_OPS=<dossier temporaire> python3 -I -S tests/fixture_bureaux.py <racine de la copie>
Le journal de départ (copie du journal officiel) doit déjà être dans ILE_OPS."""
import os
import sys
from pathlib import Path

copie = Path(sys.argv[1]).resolve()
for d in ("securite", "presidence", "orchestrateur", "residence"):
    sys.path.insert(0, str(copie / d))
assert os.environ.get("ILE_OPS") and Path(os.environ["ILE_OPS"]).resolve() != (copie / "orchestrateur" / "registre").resolve(), "ILE_OPS temporaire obligatoire"
import ile  # noqa: E402
import organisation as org  # noqa: E402

MAIRE, HOOK = ile._auteur("maire", "declare"), ile._auteur("claude-code", "hook")
run = lambda role: ile.auteur_cli(role, ile.run_debut(role, HOOK)["donnees"]["run"])
chef = run("chef-rev-em")                                                # reste ouverte : le directeur est réellement en exécution
org.creer_departement("rev-em", "rev-em-produit", "Produit", "Fonctionnalités, qualité et livraisons de REV-EM", chef)
org.creer_poste("rev-em", "rev-em-manager-produit", "manager", "rev-em-direction", chef, departement="rev-em-produit", competences=["pilotage"])
org.creer_poste("rev-em", "rev-em-dev", "developpeur-backend", "rev-em-manager-produit", chef, departement="rev-em-produit", competences=["python", "tests"])
org.creer_poste("rev-em", "rev-em-front", "developpeur-frontend", "rev-em-manager-produit", chef, departement="rev-em-produit")
org.creer_agent("manager-produit", "Manager Produit", "rev-em-manager-produit", chef, description="poste tenu sans définition exécutable (fixture)")
org.affecter_agent("architecte", "rev-em-dev", MAIRE, "renfort (fixture)")
dev = run("architecte")
livrable = copie / "projets" / "rev-em" / "livrables" / "fixture-note.md"
livrable.parent.mkdir(parents=True, exist_ok=True); livrable.write_text("# Note (fixture de test)\n")
m1 = ile.proposer_mission("rev-em", "Note de synthèse (fixture)", "Résumer l'état des lieux", ["fichier livré"], MAIRE, valeur=3, urgence=2, effort=1, risque=1)["donnees"]["mission"]
m2 = ile.proposer_mission("rev-em", "Chargement des fiches (fixture)", "Corriger le chargement", ["test vert"], MAIRE, valeur=4, urgence=3, effort=2, risque=2)["donnees"]["mission"]
for m in (m1, m2):
    ile.changer_statut(m, "planifiee", MAIRE)
org.attribuer_mission(m1, "architecte", chef, echeance="2099-12-31", priorite="P2")
org.demarrer_mission(m1, dev)
org.livrer(m1, "projets/rev-em/livrables/fixture-note.md", dev, note="première version")
org.envoyer_message("chef-rev-em", "Livrable transmis", "La note est prête pour validation.", dev, mission=m1)
org.valider(m1, chef, "conforme")
org.attribuer_mission(m2, "architecte", chef, priorite="P1")
org.demarrer_mission(m2, dev)
org.remonter(m2, "dépendance externe indisponible", dev, bloquer=True)
ile.run_fin(dev["run"], HOOK)                                            # l'agent n'est plus en exécution : statut « bloqué »
org.ouvrir_reunion("rev-em-point", "rev-em", "Point d'équipe Produit", ["chef-rev-em", "architecte"], chef)
org.ouvrir_reunion("rev-em-lancement", "rev-em", "Lancement du département", ["chef-rev-em", "manager-produit"], chef)
org.clore_reunion("rev-em-lancement", "Département Produit créé ; deux postes de développeurs ouverts.", chef)
import serveur  # noqa: E402
m = serveur.instantane(copie / "residence" / "instantane")
print(f"fixture : {m['evenements']} événements, journal {'intègre' if m['integre'] else 'ALTÉRÉ'}")
