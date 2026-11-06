"""Version web publiée : instantané généré par le code du serveur, et vérification du journal dans le navigateur
(residence/village/verification.js) identique à orchestrateur/ile.py verifier."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for _d in ("securite", "presidence", "orchestrateur"):
    sys.path.insert(0, str(RACINE / _d))
import ile  # noqa: E402
import president  # noqa: E402
from test_ile import Base, PHRASE  # noqa: E402

president.ITERATIONS = 2000
NODE = shutil.which("node")


def _serveur():
    import importlib.util
    spec = importlib.util.spec_from_file_location("serveur_test", RACINE / "residence" / "serveur.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _verifier_js(journal: Path, meta: dict) -> dict:
    prog = ("const V = require(process.argv[1]), fs = require('fs');"
            "V.verifierJournal(fs.readFileSync(process.argv[2], 'utf8'), JSON.parse(process.argv[3])).then(r => console.log(JSON.stringify(r)));")
    out = subprocess.run([NODE, "-e", prog, str(RACINE / "residence" / "village" / "verification.js"), str(journal), json.dumps(meta)],
                         capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout)


class Instantane(Base):
    def setUp(self):
        super().setUp()
        ile.donner_instruction("Instruction de test signée", self.cle)
        ile.donner_instruction("Seconde instruction signée", self.cle)
        self.sortie = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.sortie, ignore_errors=True)
        super().tearDown()

    def test_fichiers_et_contenu(self):
        m = _serveur().instantane(self.sortie)
        noms = sorted(p.name for p in self.sortie.iterdir())
        self.assertEqual(noms, ["etat.json", "journal.json", "meta.json", "president.json", "residence.json", "verifier.json"])
        self.assertTrue(m["integre"]); self.assertEqual(m["evenements"], len(ile.lire()))
        self.assertEqual(set(m["types_presidentiels"]), ile.TYPES_PRESIDENTIELS)
        res = json.loads((self.sortie / "residence.json").read_text(encoding="utf-8"))
        self.assertFalse(res["president"]["deverrouille"])                    # jamais de session dans la version publiée
        self.assertEqual(res["securite"]["acces_distant"], [])                 # noms d'hôte de l'accès distant non publiés
        texte = "".join(p.read_text(encoding="utf-8") for p in self.sortie.iterdir())
        self.assertNotIn(PHRASE, texte)
        for interdit in ('"graine"', '"phrase"', '"cle_privee"', "BEGIN PRIVATE"):
            self.assertNotIn(interdit, texte)
        j = json.loads((self.sortie / "journal.json").read_text(encoding="utf-8"))
        self.assertEqual(j["total"], len(ile.lire())); self.assertEqual(j["evenements"][0]["n"], j["total"])   # plus récent d'abord

    @unittest.skipUnless(NODE, "node absent")
    def test_verification_navigateur_identique_a_python(self):
        m = _serveur().instantane(self.sortie)
        r = _verifier_js(ile.JOURNAL, m)
        v = ile.verifier()
        self.assertEqual((r["ok"], r["n"], r["dernier"]), (v["ok"], v["n"], v["dernier"]))
        self.assertEqual((r["actes_presidentiels"], r["actes_valides"]), (3, 3))   # identité + deux instructions signées
        # falsification d'un acte signé, signature remplacée, ligne retirée : détectées comme par Python
        lignes = ile.JOURNAL.read_text(encoding="utf-8").splitlines()
        for nom, alteration in (("acte modifié", lignes[:-1] + [lignes[-1].replace("Seconde instruction signée", "Instruction falsifiée")]),
                                ("ligne du milieu retirée", lignes[:1] + lignes[2:])):   # une fin tronquée se détecte par l'empreinte finale
            with self.subTest(nom=nom):
                f = self.sortie / "altere.jsonl"
                f.write_text("\n".join(alteration) + "\n", encoding="utf-8")
                self.assertFalse(_verifier_js(f, m)["ok"])

    @unittest.skipUnless(NODE, "node absent")
    def test_vrai_journal(self):
        """Sur le journal réel de l'île (lecture seule) : même verdict et même empreinte finale qu'en Python."""
        vrai = RACINE / "orchestrateur" / "registre" / "journal.jsonl"
        meta = json.loads((RACINE / "residence" / "instantane" / "meta.json").read_text(encoding="utf-8"))
        r = _verifier_js(vrai, meta)
        evs = [json.loads(l) for l in vrai.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertTrue(r["ok"], r["erreurs"]); self.assertEqual(r["n"], len(evs)); self.assertEqual(r["dernier"], evs[-1]["hash"])


if __name__ == "__main__":
    unittest.main()
