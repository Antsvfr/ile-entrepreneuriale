"""Phase 3.3 : missions attribuées, exécution, livrables, validation hiérarchique, remontées, messages, réunions."""
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for _d in ("securite", "presidence", "orchestrateur"):
    sys.path.insert(0, str(RACINE / _d))
import ile  # noqa: E402
import organisation as org  # noqa: E402
import president  # noqa: E402
from test_ile import Base  # noqa: E402

president.ITERATIONS = 2000
MAIRE = ile._auteur("maire", "declare")
HOOK = ile._auteur("claude-code", "hook")
LIVRABLE = RACINE / "tests" / ".livrable-test.md"


def run_de(role):
    r = ile.run_debut(role, HOOK)["donnees"]["run"]
    return r, ile.auteur_cli(role, r)


class Travail(Base):
    def setUp(self):
        super().setUp()
        org.amorcer(MAIRE)
        # équipe REV-EM : un poste de développeur sous le directeur, tenu par un agent réel (l'Architecte y est affecté)
        org.creer_poste("rev-em", "rev-em-dev", "developpeur-backend", "rev-em-direction", MAIRE)
        org.affecter_agent("architecte", "rev-em-dev", MAIRE, "renfort REV-EM")
        ev = ile.proposer_mission("rev-em", "Corriger le chargement des fiches", "objectif", ["les fiches se chargent"], MAIRE, valeur=4, urgence=3, effort=2, risque=2)
        self.m = ev["donnees"]["mission"]
        ile.changer_statut(self.m, "planifiee", MAIRE)
        self.r_chef, self.chef = run_de("chef-rev-em")
        self.r_dev, self.dev = run_de("architecte")
        LIVRABLE.write_text("correctif v1")

    def tearDown(self):
        LIVRABLE.unlink(missing_ok=True)
        super().tearDown()

    def test_cycle_complet_avec_correction(self):
        org.attribuer_mission(self.m, "architecte", self.chef, echeance="2099-12-31", priorite="P1")
        o = org.etat()
        self.assertEqual((o["missions"][self.m]["attributaire"], o["missions"][self.m]["attribuee_par"]), ("architecte", "chef-rev-em"))
        org.demarrer_mission(self.m, self.dev)
        org.livrer(self.m, "tests/.livrable-test.md", self.dev, note="première version")
        o = org.etat()
        self.assertEqual(o["missions"][self.m]["statut"], "verification")
        self.assertEqual(o["agents"]["architecte"]["statut"], "en_execution")            # son exécution est ouverte : c'est le fait le plus fort
        ile.run_fin(self.r_dev, HOOK)
        self.assertEqual(org.etat()["agents"]["architecte"]["statut"], "en_attente_validation")
        org.demander_correction(self.m, "il manque le test", self.chef)
        self.assertEqual(org.etat()["missions"][self.m]["statut"], "en_cours")
        _, self.dev = run_de("architecte")
        LIVRABLE.write_text("correctif v2 avec test")
        org.livrer(self.m, "tests/.livrable-test.md", self.dev)
        org.valider(self.m, self.chef, "conforme")
        o = org.etat()
        m = o["missions"][self.m]
        self.assertEqual((m["statut"], m["validee"]["par"], m["corrections"], len(m["livrables"])), ("terminee", "chef-rev-em", 1, 2))
        perf = o["agents"]["architecte"]["performance"]
        self.assertEqual((perf["missions_terminees"], perf["corrections_demandees"], perf["livrees_dans_les_delais"]), (1, 1, 1))
        self.assertTrue(ile.verifier()["ok"])

    def test_permissions_du_travail(self):
        with self.assertRaises(org.ErreurOrganisation):                                   # un expert n'attribue pas
            org.attribuer_mission(self.m, "architecte", self.dev)
        _, lex = run_de("chef-lexnote")
        with self.assertRaises(org.ErreurOrganisation):                                   # autre entreprise
            org.attribuer_mission(self.m, "architecte", lex)
        with self.assertRaises(org.ErreurOrganisation):                                   # identité seulement déclarée
            org.attribuer_mission(self.m, "architecte", ile.auteur_cli("chef-rev-em"))
        org.attribuer_mission(self.m, "architecte", self.chef)
        with self.assertRaises(org.ErreurOrganisation):                                   # seul l'attributaire démarre
            org.demarrer_mission(self.m, self.chef)
        org.demarrer_mission(self.m, self.dev)
        org.livrer(self.m, "tests/.livrable-test.md", self.dev)
        with self.assertRaises(org.ErreurOrganisation):                                   # pas d'auto-validation
            org.valider(self.m, self.dev)
        with self.assertRaises(org.ErreurOrganisation):                                   # correction sans motif
            org.demander_correction(self.m, "", self.chef)
        with self.assertRaises(org.ErreurOrganisation):                                   # livrable hors de l'île
            org.livrer(self.m, "../../etc/passwd", self.dev)

    def test_livrable_modifie_apres_transmission(self):
        org.attribuer_mission(self.m, "architecte", self.chef)
        org.demarrer_mission(self.m, self.dev)
        org.livrer(self.m, "tests/.livrable-test.md", self.dev)
        LIVRABLE.write_text("modifié en douce après transmission")
        with self.assertRaises(org.ErreurOrganisation):
            org.valider(self.m, self.chef)

    def test_remontee_et_blocage(self):
        org.attribuer_mission(self.m, "architecte", self.chef)
        org.demarrer_mission(self.m, self.dev)
        org.remonter(self.m, "dépendance externe indisponible", self.dev, bloquer=True)
        o = org.etat()
        self.assertEqual(o["missions"][self.m]["statut"], "bloquee")
        self.assertEqual(o["missions"][self.m]["remontees"][0]["vers"], "chef-rev-em")
        ile.run_fin(self.r_dev, HOOK)
        self.assertEqual(org.etat()["agents"]["architecte"]["statut"], "bloque")

    def test_messages_historises(self):
        org.envoyer_message("chef-rev-em", "Point d'avancement", "Le correctif est en cours.", self.dev, mission=self.m)
        msg = org.etat()["messages"][0]
        self.assertEqual((msg["de"], msg["a"], msg["verifie"]), ("architecte", "chef-rev-em", "run"))
        with self.assertRaises(org.ErreurOrganisation):
            org.envoyer_message("chef-rev-em", "x", "y", ile.auteur_cli("architecte"))     # identité déclarée
        with self.assertRaises(org.ErreurOrganisation):
            org.envoyer_message("inconnu", "x", "y", self.dev)

    def test_message_sans_mission_rattache_a_l_entreprise_du_poste(self):
        # l'entreprise d'un message sans mission vient du poste de l'expéditeur au registre (rev-em), jamais d'un préfixe deviné (« rev »)
        org.envoyer_message("chef-rev-em", "Question", "Sans mission.", self.dev)
        trace = [x for x in org.etat()["activite"] if x["type"] == "message.envoye"][-1]
        self.assertEqual(trace["entreprise"], "rev-em")

    def test_reunion_sans_fausse_presence(self):
        org.ouvrir_reunion("rev-em-point", "rev-em", "point hebdomadaire", ["chef-rev-em", "architecte"], self.chef)
        self.assertEqual(org.etat()["agents"]["architecte"]["statut"], "en_reunion")      # réunion ouverte + exécution réelle
        ile.run_fin(self.r_dev, HOOK)
        self.assertNotEqual(org.etat()["agents"]["architecte"]["statut"], "en_reunion")   # plus d'exécution : pas « en réunion »
        with self.assertRaises(org.ErreurOrganisation):
            org.clore_reunion("rev-em-point", "cr", self.dev)                             # seul l'organisateur
        org.clore_reunion("rev-em-point", "décisions : …", self.chef)
        self.assertIsNotNone(org.etat()["reunions"]["rev-em-point"]["close"])

    def test_validation_presidentielle_signee(self):
        org.attribuer_mission(self.m, "architecte", self.chef)
        org.demarrer_mission(self.m, self.dev)
        org.livrer(self.m, "tests/.livrable-test.md", self.dev)
        org.valider(self.m, {}, "validé par le président", cle=self.cle)
        o = org.etat()
        self.assertEqual(o["missions"][self.m]["statut"], "terminee")
        self.assertFalse([r for r in ile.etat()["rejets"]])                                # aucun acte rejeté
        self.assertTrue(ile.verifier()["ok"])


if __name__ == "__main__":
    unittest.main()
