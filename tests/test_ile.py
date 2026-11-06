"""Tests du registre des opérations. Lancer : python3 -m unittest discover -s tests -v
Chaque test travaille dans un dossier temporaire : le vrai journal n'est jamais touché."""
import datetime as dt
import json
import multiprocessing as mp
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for _d in ("securite", "presidence", "orchestrateur"):      # modules de l'île (hors confinement : tests)
    sys.path.insert(0, str(RACINE / _d))
import ile  # noqa: E402
import president  # noqa: E402

president.ITERATIONS = 2000   # dérivation rapide pour les tests (la valeur réelle est inscrite dans chaque identité)
PHRASE = "phrase de test suffisamment longue"
MAIRE = {"role": "maire", "verifie": "declare"}


def isoler(dossier: Path):
    ile.OPS = dossier
    ile.JOURNAL, ile.ETAT, ile.VERROU, ile.COURANTE = dossier / "journal.jsonl", dossier / "etat.json", dossier / ".verrou", dossier / ".mission-courante"


def _ecrivain(dossier, k):
    isoler(Path(dossier))
    for i in range(25):
        ile.ajouter("test.parallele", {"processus": k, "i": i}, {"role": f"p{k}", "verifie": "declare"})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        isoler(Path(self.tmp.name))
        self.cle = ile.creer_identite(PHRASE)

    def tearDown(self):
        self.tmp.cleanup()

    def proposer(self, siege="rev-em", **kw):
        d = dict(valeur=3, urgence=3, effort=3, risque=2)
        d.update(kw)
        ev = ile.proposer_mission(siege, d.pop("titre", "Corriger un test"), "objectif", ["critère vérifiable"], MAIRE, **d)
        return ev["donnees"]["mission"]


class Chaine(Base):
    def test_journal_integre(self):
        for i in range(5):
            ile.ajouter("test", {"i": i}, MAIRE)
        r = ile.verifier()
        self.assertTrue(r["ok"], r["erreurs"])
        self.assertEqual(r["n"], 6)   # identité présidentielle + 5

    def _lignes(self):
        return ile.JOURNAL.read_text(encoding="utf-8").splitlines()

    def test_modification_detectee(self):
        for i in range(4):
            ile.ajouter("test", {"i": i}, MAIRE)
        L = self._lignes(); ev = json.loads(L[1]); ev["donnees"]["i"] = 99; L[1] = json.dumps(ev, ensure_ascii=False, sort_keys=True)
        ile.JOURNAL.write_text("\n".join(L) + "\n", encoding="utf-8")
        r = ile.verifier()
        self.assertFalse(r["ok"]); self.assertTrue(any("modifié" in e for e in r["erreurs"]))

    def test_suppression_detectee(self):
        for i in range(4):
            ile.ajouter("test", {"i": i}, MAIRE)
        L = self._lignes(); del L[2]
        ile.JOURNAL.write_text("\n".join(L) + "\n", encoding="utf-8")
        self.assertFalse(ile.verifier()["ok"])

    def test_reecriture_complete_detectee_par_empreinte_finale(self):
        """Un faussaire qui recalcule toute la chaîne change l'empreinte finale : elle est publiée (git, Résidence)."""
        for i in range(3):
            ile.ajouter("test", {"i": i}, MAIRE)
        avant = ile.verifier()["dernier"]
        evs = ile.lire(); evs[1]["donnees"]["i"] = 42; prec = ile.GENESE
        for e in evs:
            e["prec"] = prec; e["hash"] = ile.empreinte(e); prec = e["hash"]
        ile.JOURNAL.write_text("".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in evs), encoding="utf-8")
        r = ile.verifier()
        self.assertTrue(r["ok"])                 # cohérente en interne…
        self.assertNotEqual(r["dernier"], avant)  # …mais l'empreinte publiée ne correspond plus

    def test_ecritures_paralleles(self):
        ps = [mp.Process(target=_ecrivain, args=(self.tmp.name, k)) for k in range(4)]
        [p.start() for p in ps]; [p.join() for p in ps]
        r = ile.verifier()
        self.assertTrue(r["ok"], r["erreurs"]); self.assertEqual(r["n"], 101)

    def test_artefact_modifie_detecte(self):
        f = ile.RACINE / "tests" / ".artefact-test.md"
        try:
            f.write_text("proposition v1")
            ile.deposer_artefact("tests/.artefact-test.md", MAIRE, nature="proposition")
            self.assertTrue(ile.verifier()["ok"])
            f.write_text("proposition modifiée en douce")
            self.assertFalse(ile.verifier()["ok"])
        finally:
            f.unlink(missing_ok=True)

    def test_artefact_migre_leurre_detecte(self):
        """Artefact déposé avant une migration (ancien chemin dans le journal) : retrouvé au nouveau chemin ; une copie
        intacte laissée à l'ancien chemin ne masque pas une version modifiée au nouveau ; un artefact disparu est signalé."""
        import shutil
        ancien, nouveau = ile.RACINE / "tests" / ".ancien-test", ile.RACINE / "tests" / ".nouveau-test"
        sauve = ile.ANCIENS_CHEMINS
        try:
            ile.ANCIENS_CHEMINS = [("tests/.ancien-test/", "tests/.nouveau-test/")]
            ancien.mkdir(exist_ok=True); nouveau.mkdir(exist_ok=True)
            (ancien / "pv.md").write_text("procès-verbal v1")
            ile.deposer_artefact("tests/.ancien-test/pv.md", MAIRE, nature="proces-verbal")
            shutil.move(str(ancien / "pv.md"), str(nouveau / "pv.md"))                     # la migration déplace le fichier
            self.assertTrue(ile.verifier()["ok"], ile.verifier()["erreurs"])              # retrouvé au nouveau chemin
            (nouveau / "pv.md").write_text("procès-verbal falsifié")
            (ancien / "pv.md").write_text("procès-verbal v1")                             # leurre intact à l'ancien chemin
            r = ile.verifier()
            self.assertFalse(r["ok"]); self.assertTrue(any("a changé" in e for e in r["erreurs"]), r["erreurs"])
            (ancien / "pv.md").unlink(); (nouveau / "pv.md").unlink()
            r = ile.verifier()
            self.assertFalse(r["ok"]); self.assertTrue(any("introuvable" in e for e in r["erreurs"]), r["erreurs"])
        finally:
            ile.ANCIENS_CHEMINS = sauve
            shutil.rmtree(ancien, ignore_errors=True); shutil.rmtree(nouveau, ignore_errors=True)


class Missions(Base):
    def test_transition_interdite(self):
        m = self.proposer()
        with self.assertRaises(ile.ErreurIle):
            ile.changer_statut(m, "terminee", MAIRE)

    def test_cycle_complet(self):
        m = self.proposer()
        for s in ("planifiee", "en_cours", "verification", "terminee"):
            ile.changer_statut(m, s, MAIRE)
        self.assertEqual(ile.etat()["missions"][m]["statut"], "terminee")
        self.assertEqual(len(ile.etat()["missions"][m]["historique"]), 5)

    def test_mission_sensible_exige_le_president(self):
        m = self.proposer(sensible=True)
        with self.assertRaises(ile.ErreurIle):
            ile.changer_statut(m, "planifiee", MAIRE)
        ile.changer_statut(m, "attente_president", MAIRE)
        with self.assertRaises(ile.ErreurIle):
            ile.changer_statut(m, "planifiee", MAIRE)
        ile.changer_statut(m, "planifiee", {}, cle=self.cle)
        self.assertEqual(ile.etat()["missions"][m]["statut"], "planifiee")

    def test_siege_inconnu_refuse(self):
        with self.assertRaises(ile.ErreurIle):
            ile.proposer_mission("nulle-part", "t", "o", ["c"], MAIRE)

    def test_classement_objectif_et_explique(self):
        a = self.proposer(titre="faible", valeur=2, urgence=2, effort=5, risque=4)
        b = self.proposer(titre="forte", valeur=5, urgence=4, effort=2, risque=1)
        c = self.proposer(siege="lexnote", titre="forte mais siège P3", valeur=5, urgence=4, effort=2, risque=1)
        ile.fixer_priorite("lexnote", "P3", self.cle)
        ile.classer(MAIRE)
        ms = ile.etat()["missions"]
        self.assertEqual(ms[b]["rang"], 1)
        self.assertLess(ms[c]["score"], ms[b]["score"])
        self.assertIn("valeur", ms[a]["classement"]["detail"])
        self.assertTrue(ms[a]["classement"]["motif"])

    def test_priorite_reservee_au_president(self):
        with self.assertRaises(ile.ErreurIle):
            ile.fixer_priorite("rev-em", "P1", MAIRE)


class Gouvernance(Base):
    def test_instruction_lue_puis_traitee(self):
        i = ile.donner_instruction("Priorité à LexNote", self.cle)["id"]
        self.assertEqual(ile.etat()["instructions"][i]["statut"], "recue")
        txt = ile.briefing_dg("session-test")
        self.assertIn("Priorité à LexNote", txt)
        self.assertEqual(ile.etat()["instructions"][i]["statut"], "lue")
        ile.traiter_instruction(i, MAIRE, "missions créées", ["M-x"])
        self.assertEqual(ile.etat()["instructions"][i]["statut"], "traitee")
        self.assertEqual(ile.briefing_dg(), "")

    def test_decision_reservee_au_president(self):
        d = ile.demander_decision("lexnote", "Autoriser l'écriture", "OK ?", MAIRE)["id"]
        with self.assertRaises(ile.ErreurIle):
            ile.trancher(d, "approuvee", MAIRE)
        ile.trancher(d, "approuvee", self.cle, "go")
        self.assertEqual(ile.etat()["decisions"][d]["verdict"], "approuvee")
        with self.assertRaises(ile.ErreurIle):
            ile.trancher(d, "refusee", self.cle)


class Agents(Base):
    def test_rattachement_automatique_et_parallele(self):
        m = self.proposer(); ile.changer_statut(m, "planifiee", MAIRE); ile.changer_statut(m, "en_cours", MAIRE)
        ile.capteur("debut", {"agent_type": "chef-rev-em", "agent_id": "a1", "session_id": "s"})
        ile.capteur("debut", {"agent_type": "critique-clarte", "agent_id": "a2", "session_id": "s"})
        ile.capteur("debut", {"agent_type": "critique-exigence", "agent_id": "a3", "session_id": "s"})
        p = ile.etat()
        self.assertEqual(len(p["runs_actifs"]), 3)
        chef = next(r for r in p["runs_actifs"] if r["role"] == "chef-rev-em")
        self.assertEqual((chef["siege"], chef["mission"], chef["agent_id"]), ("rev-em", m, "a1"))
        ile.capteur("fin", {"agent_type": "critique-exigence", "agent_id": "a3", "session_id": "s"})
        actifs = {r["agent_id"] for r in ile.etat()["runs_actifs"]}
        self.assertEqual(actifs, {"a1", "a2"})

    def test_aucun_agent_fantome(self):
        """La 3D ne reçoit que des exécutions ouvertes et récentes."""
        self.assertEqual(ile.etat_3d(ile.etat())["runs_actifs"], [])
        r = ile.run_debut("chef-lexnote", MAIRE)["donnees"]["run"]
        e3 = ile.etat_3d(ile.etat())
        self.assertEqual(e3["sieges_actifs"], ["lexnote"])
        ile.run_fin(r, MAIRE)
        e3 = ile.etat_3d(ile.etat())
        self.assertEqual((e3["runs_actifs"], e3["sieges_actifs"]), ([], []))
        vieux = (dt.datetime.now().astimezone() - dt.timedelta(hours=3)).isoformat(timespec="seconds")
        evs = [{"type": "run.debut", "quand": vieux, "auteur": MAIRE, "donnees": {"run": "R-9", "role": "chef-ecole", "siege": "ecole"}, "hash": "x"}]
        p = ile.projeter(evs)
        self.assertEqual(p["runs_actifs"], []); self.assertEqual(len(p["runs_expires"]), 1)

    def test_identite_confirmee_par_execution(self):
        r = ile.run_debut("chef-rev-em", MAIRE)["donnees"]["run"]
        self.assertEqual(ile.auteur_cli("chef-rev-em", r)["verifie"], "run")
        self.assertEqual(ile.auteur_cli("chef-lexnote", r)["verifie"], "declare")
        ile.run_fin(r, MAIRE)
        self.assertEqual(ile.auteur_cli("chef-rev-em", r)["verifie"], "declare")


if __name__ == "__main__":
    unittest.main()
