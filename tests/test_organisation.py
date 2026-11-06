"""Phase 3.1–3.2 : organisation (entreprises, départements, postes, agents), hiérarchie, permissions, statuts réels."""
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


def run_de(role):
    """Exécution réelle ouverte (comme le fait le hook SubagentStart) → identité vérifiée de l'agent."""
    r = ile.run_debut(role, ile._auteur("claude-code", "hook"))["donnees"]["run"]
    return r, ile.auteur_cli(role, r)


class Organisation(Base):
    def setUp(self):
        super().setUp()
        org.amorcer(MAIRE)

    def test_amorce_faits_reels_seulement(self):
        o = org.etat()
        self.assertEqual(len(o["agents"]), 13)                                         # 12 définitions + le Maire
        self.assertEqual(o["entreprises"]["rev-em"]["directeur"]["agent"], "chef-rev-em")
        self.assertEqual(o["entreprises"]["conseil"]["direction"], "collégiale")
        self.assertTrue(all(p["titulaire"] for p in o["postes"].values()))             # aucun poste vacant inventé
        self.assertEqual(org.amorcer(MAIRE), [])                                       # idempotent
        self.assertTrue(ile.verifier()["ok"])

    def test_directeur_construit_son_entreprise(self):
        run, chef = run_de("chef-rev-em")
        org.creer_departement("rev-em", "rev-em-produit", "Produit", "Fonctionnalités et qualité", chef)
        org.creer_poste("rev-em", "rev-em-manager-produit", "manager", "rev-em-direction", chef, departement="rev-em-produit")
        org.creer_poste("rev-em", "rev-em-dev-front", "developpeur-frontend", "rev-em-manager-produit", chef, departement="rev-em-produit")
        o = org.etat()
        self.assertEqual(o["postes"]["rev-em-dev-front"]["superieur"], "rev-em-manager-produit")
        self.assertIsNone(o["postes"]["rev-em-dev-front"]["titulaire"])                # non pourvu, pas inventé
        self.assertEqual(o["entreprises"]["rev-em"]["postes_non_pourvus"], 2)
        ev = ile.lire()[-1]
        self.assertEqual(ev["auteur"]["verifie"], "run"); self.assertIn("rev-em-direction", ev["donnees"]["autorisation"])

    def test_identite_declaree_refusee(self):
        with self.assertRaises(org.ErreurOrganisation):                                  # pas d'exécution ouverte
            org.creer_departement("rev-em", "x-dep", "X", "", ile.auteur_cli("chef-rev-em"))
        with self.assertRaises(org.ErreurOrganisation):                                  # exécution d'un autre rôle
            r, _ = run_de("chef-lexnote")
            org.creer_departement("rev-em", "x-dep", "X", "", ile.auteur_cli("chef-rev-em", r))

    def test_cloisonnement_entre_entreprises(self):
        _, chef = run_de("chef-lexnote")
        with self.assertRaises(org.ErreurOrganisation):
            org.creer_departement("rev-em", "intrus", "Intrus", "", chef)
        with self.assertRaises(org.ErreurOrganisation):
            org.creer_poste("rev-em", "intrus", "manager", "rev-em-direction", chef)

    def test_hierarchie_et_permissions_par_fonction(self):
        _, chef = run_de("chef-rev-em")
        org.creer_poste("rev-em", "m1", "manager", "rev-em-direction", chef)
        org.creer_poste("rev-em", "dev1", "developpeur-backend", "m1", chef)
        with self.assertRaises(org.ErreurOrganisation):                                  # niveau supérieur sous un manager
            org.creer_poste("rev-em", "dir-sous-manager", "directeur-technique", "m1", chef)
        with self.assertRaises(org.ErreurOrganisation):                                  # un expert ne crée pas de poste
            _, critique = run_de("critique-clarte")
            org.creer_poste("conseil", "x", "agent-operationnel", "conseil-clarte", critique)
        with self.assertRaises(org.ErreurOrganisation):                                  # poste au-dessus de soi : non
            org.suspendre_agent("maire", "test", chef)

    def test_nomination_et_suspension(self):
        _, chef = run_de("chef-rev-em")
        org.creer_poste("rev-em", "m1", "manager", "rev-em-direction", chef)
        with self.assertRaises(org.ErreurOrganisation):                                  # définition inexistante
            org.creer_agent("fantome", "Fantôme", "m1", chef, definition="nexiste-pas")
        org.creer_agent("manager-sans-moteur", "Manager (à pourvoir en définition)", "m1", chef)
        a = org.etat()["agents"]["manager-sans-moteur"]
        self.assertEqual((a["statut"], a["superieur"], a["entreprise"]), ("hors_ligne", "chef-rev-em", "rev-em"))
        self.assertEqual(len(a["apparence"]["graine"]), 16)                             # identité visuelle stable (phase 4)
        org.suspendre_agent("manager-sans-moteur", "test", chef)
        self.assertEqual(org.etat()["agents"]["manager-sans-moteur"]["statut"], "suspendu")
        org.reactiver_agent("manager-sans-moteur", "fin du test", chef)
        self.assertEqual(org.etat()["agents"]["manager-sans-moteur"]["statut"], "hors_ligne")
        with self.assertRaises(org.ErreurOrganisation):
            org.creer_agent("doublon", "Doublon", "m1", chef)                            # poste déjà pourvu

    def test_statuts_derives_jamais_inventes(self):
        o = org.etat()
        self.assertEqual(o["agents"]["chef-rev-em"]["statut"], "disponible")
        r, _ = run_de("chef-rev-em")
        a = org.etat()["agents"]["chef-rev-em"]
        self.assertEqual((a["statut"], a["preuve"]), ("en_execution", r))                # preuve = l'exécution réelle
        ile.run_fin(r, ile._auteur("claude-code", "hook"))
        self.assertEqual(org.etat()["agents"]["chef-rev-em"]["statut"], "disponible")
        self.assertEqual(o["agents"]["maire"]["statut"], "hors_ligne")                   # aucune trace d'exécution : pas « actif »
        self.assertFalse([a for a in o["agents"].values() if a["statut"] in ("en_reunion", "en_execution")])

    def test_president_signe_et_usurpation(self):
        org.creer_departement("forge", "forge-audit", "Audit", "Contrôles", {}, cle=self.cle)
        ev = ile.lire()[-1]
        self.assertEqual((ev["auteur"]["role"], ev["auteur"]["verifie"]), ("president", "signature"))
        with self.assertRaises(org.ErreurOrganisation):                                  # « president » sans signature
            org.creer_departement("forge", "faux", "Faux", "", {"role": "president", "verifie": "declare"})
        self.assertTrue(ile.verifier()["ok"])

    def test_rejeu_identique(self):
        _, chef = run_de("chef-rev-em")
        org.creer_departement("rev-em", "d1", "D1", "", chef)
        evs = ile.lire()
        a, b = org.projeter(evs), org.projeter([dict(e) for e in evs])
        self.assertEqual({k: a[k] for k in ("departements", "postes")}, {k: b[k] for k in ("departements", "postes")})


if __name__ == "__main__":
    unittest.main()
