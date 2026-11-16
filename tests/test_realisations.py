"""Réalisation automatique (/realiser) : règles du circuit imposées par le registre. Registre temporaire uniquement."""
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for _d in ("securite", "presidence", "orchestrateur"):
    sys.path.insert(0, str(RACINE / _d))
import ile  # noqa: E402
import realisations as X  # noqa: E402
from test_ile import Base, MAIRE  # noqa: E402

HOOK = ile._auteur("claude-code", "hook")


class Circuit(Base):
    def ouvrir(self):
        return X.ouvrir("rev-em", "Corriger le chargement", "Corrige le chargement des fiches", MAIRE)["donnees"]["realisation"]

    def x(self, xid):
        return X.etat()["realisations"][xid]

    def jusqu_au_dev(self, xid, dev="chef-rev-em"):
        X.etape(xid, "conseil", "critique-clarte", MAIRE, "Préciser quelles fiches")
        X.etape(xid, "conception", "concepteur", MAIRE, "Plan en 2 étapes", criteres=["le test de chargement passe"])
        X.etape(xid, "developpement", dev, MAIRE, "Correctif livré sur la branche de travail")

    def test_ordre_impose(self):
        xid = self.ouvrir()
        self.assertEqual((self.x(xid)["statut"], self.x(xid)["attendu"]), ("ouverte", "avis du Conseil"))
        for phase, kw in (("conception", {"criteres": ["c"]}), ("developpement", {}), ("correction", {"verdict": "accepte"})):
            with self.assertRaises(X.ErreurRealisation):
                X.etape(xid, phase, "x", MAIRE, "trop tôt", **kw)                 # rien ne saute le Conseil
        X.etape(xid, "conseil", "critique-clarte", MAIRE, "avis")
        with self.assertRaises(X.ErreurRealisation):
            X.etape(xid, "developpement", "chef-rev-em", MAIRE, "sans plan")      # pas de développement sans plan
        with self.assertRaises(X.ErreurRealisation):
            X.etape(xid, "conception", "concepteur", MAIRE, "plan sans critère")  # critères obligatoires
        X.etape(xid, "conception", "concepteur", MAIRE, "plan", criteres=["le test passe"])
        with self.assertRaises(X.ErreurRealisation):
            X.etape(xid, "correction", "forgeron", MAIRE, "rien à juger", verdict="accepte")
        X.etape(xid, "developpement", "chef-rev-em", MAIRE, "livré")
        self.assertEqual((self.x(xid)["tour"], self.x(xid)["attendu"]), (1, "verdict de forgeron, relecteur"))

    def test_acceptation_exige_tous_les_correcteurs(self):
        xid = self.ouvrir(); self.jusqu_au_dev(xid)
        X.etape(xid, "correction", "forgeron", MAIRE, "tests verts", verdict="accepte")
        with self.assertRaises(X.ErreurRealisation):
            X.clore(xid, "acceptee", "fini", MAIRE)                               # il manque le relecteur
        with self.assertRaises(X.ErreurRealisation):
            X.etape(xid, "correction", "forgeron", MAIRE, "bis", verdict="accepte")   # un verdict par tour
        X.etape(xid, "correction", "relecteur", MAIRE, "code relu", verdict="accepte")
        self.assertEqual(self.x(xid)["statut"], "prete")
        with self.assertRaises(X.ErreurRealisation):
            X.clore(xid, "bloquee", "x", MAIRE)
        X.clore(xid, "acceptee", "livré et vérifié", MAIRE)
        self.assertEqual(self.x(xid)["statut"], "acceptee")
        with self.assertRaises(X.ErreurRealisation):
            X.etape(xid, "conseil", "critique-clarte", MAIRE, "après clôture")
        self.assertTrue(ile.verifier()["ok"])

    def test_boucle_de_correction_bornee(self):
        xid = self.ouvrir(); self.jusqu_au_dev(xid)
        with self.assertRaises(X.ErreurRealisation):
            X.etape(xid, "correction", "forgeron", MAIRE, "refus sans défaut", verdict="a_corriger")
        with self.assertRaises(X.ErreurRealisation):
            X.etape(xid, "developpement", "chef-rev-em", MAIRE, "tour 2 sans refus")   # pas de nouveau tour sans refus
        for tour in (1, 2, 3):
            X.etape(xid, "correction", "forgeron", MAIRE, "un test échoue", verdict="a_corriger", defauts=[f"test X rouge (tour {tour})"])
            with self.assertRaises(X.ErreurRealisation):
                X.clore(xid, "acceptee", "forcé", MAIRE)                          # un refus n'est jamais une acceptation
            if tour < 3:
                X.etape(xid, "developpement", "chef-rev-em", MAIRE, f"correction {tour}")
        with self.assertRaises(X.ErreurRealisation) as e:
            X.etape(xid, "developpement", "chef-rev-em", MAIRE, "tour 4")
        self.assertIn("la boucle s'arrête", str(e.exception))
        self.assertIn("bloquee", self.x(xid)["attendu"])
        X.clore(xid, "bloquee", "3 tours sans accord : blocage remonté à Anton", MAIRE)
        self.assertEqual(self.x(xid)["statut"], "bloquee")

    def test_refus_puis_acceptation_au_tour_suivant(self):
        xid = self.ouvrir(); self.jusqu_au_dev(xid)
        X.etape(xid, "correction", "forgeron", MAIRE, "ok", verdict="accepte")
        X.etape(xid, "correction", "relecteur", MAIRE, "faille", verdict="a_corriger", defauts=["entrée non échappée"])
        self.assertEqual(self.x(xid)["statut"], "a_corriger")                     # un seul refus suffit
        X.etape(xid, "developpement", "chef-rev-em", MAIRE, "échappement ajouté")
        with self.assertRaises(X.ErreurRealisation):
            X.clore(xid, "acceptee", "x", MAIRE)                                  # les verdicts du tour 1 ne valent pas pour le tour 2
        X.etape(xid, "correction", "forgeron", MAIRE, "ok", verdict="accepte")
        X.etape(xid, "correction", "relecteur", MAIRE, "ok", verdict="accepte")
        X.clore(xid, "acceptee", "accepté au tour 2", MAIRE)
        self.assertEqual((self.x(xid)["statut"], self.x(xid)["tour"]), ("acceptee", 2))

    def test_independance_developpeur_correcteur(self):
        xid = self.ouvrir(); self.jusqu_au_dev(xid, dev="forgeron")
        with self.assertRaises(X.ErreurRealisation):
            X.etape(xid, "correction", "forgeron", MAIRE, "je me corrige", verdict="accepte")
        xid2 = self.ouvrir(); self.jusqu_au_dev(xid2)
        X.etape(xid2, "correction", "relecteur", MAIRE, "défaut", verdict="a_corriger", defauts=["d"])
        with self.assertRaises(X.ErreurRealisation):
            X.etape(xid2, "developpement", "relecteur", MAIRE, "je corrige moi-même")

    def test_qui_inscrit_et_preuve_d_execution(self):
        xid = self.ouvrir()
        with self.assertRaises(X.ErreurRealisation):                              # un agent sans identité vérifiée n'inscrit rien
            X.etape(xid, "conseil", "critique-clarte", {"role": "critique-clarte", "verifie": "declare"}, "avis")
        with self.assertRaises(X.ErreurRealisation):
            X.ouvrir("rev-em", "t", "p", {"role": "chef-rev-em", "verifie": "declare"})
        r = ile.run_debut("critique-clarte", HOOK)["donnees"]["run"]
        agent = ile.auteur_cli("critique-clarte", r)
        with self.assertRaises(X.ErreurRealisation):                              # pas au nom d'un autre rôle
            X.etape(xid, "conseil", "critique-exigence", agent, "avis d'un autre")
        X.etape(xid, "conseil", "critique-clarte", agent, "avis inscrit par l'agent")
        X.etape(xid, "conseil", "critique-exigence", MAIRE, "rapporté, avec exécution", run_agent=ile.run_debut("critique-exigence", HOOK)["donnees"]["run"])
        X.etape(xid, "conseil", "critique-strategie", MAIRE, "rapporté, exécution d'un autre rôle", run_agent=r)
        niveaux = [e["preuve"]["niveau"] for e in self.x(xid)["etapes"]]
        self.assertEqual(niveaux, ["agent", "execution", "declare"])              # jamais d'exécution prétendue


if __name__ == "__main__":
    unittest.main()
