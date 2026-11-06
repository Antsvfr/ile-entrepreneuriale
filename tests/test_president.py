"""Identité présidentielle, signatures, approbations. Lancer : python3 -m unittest discover -s tests -v"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for _d in ("securite", "presidence", "orchestrateur"):      # modules de l'île (hors confinement : tests)
    sys.path.insert(0, str(RACINE / _d))
import ile  # noqa: E402
import president  # noqa: E402
import signature  # noqa: E402
from test_ile import Base, MAIRE, PHRASE, isoler  # noqa: E402

president.ITERATIONS = 2000


class Ed25519(unittest.TestCase):
    VECTEURS = [  # RFC 8032 §7.1, tests 1 et 2
        ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60", "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
         "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
        ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb", "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
         "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ]

    def test_vecteurs_rfc8032(self):
        for sk, pk, m, sig in self.VECTEURS:
            sk, pk, m, sig = map(bytes.fromhex, (sk, pk, m, sig))
            self.assertEqual(signature.cle_publique(sk), pk)
            self.assertEqual(signature.signer(sk, m), sig)
            self.assertTrue(signature.verifier(pk, m, sig))
            self.assertFalse(signature.verifier(pk, m + b"!", sig))
            self.assertFalse(signature.verifier(pk, m, sig[:-1] + bytes([sig[-1] ^ 1])))


class Identite(Base):
    def test_deverrouillage(self):
        self.assertEqual(ile.deverrouiller(PHRASE).publique, self.cle.publique)
        with self.assertRaises(ile.ErreurIle):
            ile.deverrouiller("mauvaise phrase de test")
        with self.assertRaises(ile.ErreurIle):
            ile.creer_identite("une autre phrase bien longue")   # une seule identité

    def test_phrase_trop_courte(self):
        isoler(Path(tempfile.mkdtemp()))
        with self.assertRaises(president.ErreurPresident):
            ile.creer_identite("court")

    def test_cle_jamais_sur_disque(self):
        brut = ile.JOURNAL.read_text(encoding="utf-8")
        self.assertNotIn(PHRASE, brut)
        self.assertNotIn(self.cle._graine.hex(), brut)
        with self.assertRaises(TypeError):
            import pickle
            pickle.dumps(self.cle)

    def test_changement_de_phrase_signe_par_l_ancienne(self):
        nouvelle = ile.changer_phrase(self.cle, "nouvelle phrase présidentielle")
        self.assertEqual(ile.identite_courante()["cle_publique"], nouvelle.publique)
        with self.assertRaises(ile.ErreurIle):
            ile.deverrouiller(PHRASE)
        self.assertTrue(ile.verifier()["ok"])

    def test_changement_non_signe_rejete(self):
        intrus, pub = president.nouvelle_identite("phrase d'un agent intrus")
        pub["preuve"] = intrus.signer(("possession:" + intrus.publique).encode())
        ile.ajouter("president.identite", pub, {}, cle=intrus)    # signé par l'intrus, pas par la clé en vigueur
        self.assertEqual(ile.identite_courante()["cle_publique"], self.cle.publique)
        self.assertFalse(ile.verifier()["ok"])


class Falsification(Base):
    def setUp(self):
        super().setUp()
        self.d = ile.demander_decision("rev-em", "Fusionner ?", "OK ?", MAIRE)["id"]

    def test_acte_non_signe_ignore(self):
        ile.ajouter("decision.tranchee", {"decision": self.d, "siege": "rev-em", "verdict": "approuvee"}, {"role": "president", "verifie": "signature"})
        p = ile.etat()
        self.assertIsNone(p["decisions"][self.d]["verdict"])
        self.assertEqual(len(p["rejets"]), 1)
        self.assertFalse(ile.verifier()["ok"])

    def test_signature_d_un_autre_cle_ignoree(self):
        intrus, _ = president.nouvelle_identite("phrase d'un agent intrus")
        ile.ajouter("siege.priorite", {"siege": "rev-em", "priorite": "P1"}, {}, cle=intrus)
        self.assertIsNone(ile.etat()["sieges"].get("rev-em", {}).get("priorite"))

    def test_acte_presidentiel_par_un_autre_role(self):
        ile.ajouter("decision.tranchee", {"decision": self.d, "siege": "rev-em", "verdict": "approuvee"}, {"role": "maire", "verifie": "declare"})
        self.assertIsNone(ile.etat()["decisions"][self.d]["verdict"])

    def test_chaine_recalculee_ne_suffit_pas(self):
        """Un agent qui réécrit le journal avec une chaîne cohérente ne peut pas fabriquer de signature."""
        ile.ajouter("decision.tranchee", {"decision": self.d, "siege": "rev-em", "verdict": "approuvee"}, {"role": "president", "verifie": "signature"})
        evs = ile.lire(); evs[-1]["signature"] = "00" * 64; prec = ile.GENESE
        for e in evs:
            e["prec"] = prec; e["hash"] = ile.empreinte(e); prec = e["hash"]
        ile.JOURNAL.write_text("".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in evs), encoding="utf-8")
        self.assertIsNone(ile.etat()["decisions"][self.d]["verdict"])
        self.assertTrue(any("signature" in e for e in ile.verifier()["erreurs"]))

    def test_acte_signe_accepte(self):
        ile.trancher(self.d, "approuvee", self.cle, "go")
        p = ile.etat()
        self.assertEqual(p["decisions"][self.d]["verdict"], "approuvee")
        self.assertEqual(p["decisions"][self.d]["par"]["verifie"], "signature")
        self.assertTrue(ile.verifier()["ok"])


class Approbations(Base):
    def test_cycle_usage_unique(self):
        cmd = "git push origin main"
        aid, neuve = ile.demander_approbation("git", "push-protege", "push", "Bash", cmd, MAIRE)
        self.assertTrue(neuve)
        self.assertEqual(ile.demander_approbation("git", "push-protege", "push", "Bash", cmd, MAIRE), (aid, False))   # pas de doublon
        self.assertIsNone(ile.approbation_valide("Bash", cmd))
        ile.accorder(aid, self.cle, "ok")
        a = ile.approbation_valide("Bash", cmd)
        self.assertEqual(a["id"], aid)
        self.assertIsNone(ile.approbation_valide("Bash", cmd + " --force"))   # opération exacte uniquement
        ile.utiliser_approbation(aid, {"agent_type": "test"}, MAIRE)
        self.assertIsNone(ile.approbation_valide("Bash", cmd))
        self.assertEqual(ile.etat()["approbations"][aid]["statut"], "utilisee")

    def test_accord_falsifie_sans_effet(self):
        aid, _ = ile.demander_approbation("git", "push-protege", "push", "Bash", "git push origin main", MAIRE)
        ile.ajouter("approbation.accordee", {"approbation": aid, "expire": "2099-01-01T00:00:00+00:00"}, {"role": "president", "verifie": "signature"})
        self.assertIsNone(ile.approbation_valide("Bash", "git push origin main"))

    def test_expiration(self):
        aid, _ = ile.demander_approbation("deploiement", "d", "d", "Bash", "vercel --prod", MAIRE)
        ile.accorder(aid, self.cle, duree_h=.1)
        evs = ile.projeter(ile.lire())
        self.assertEqual(evs["approbations"][aid]["statut"], "accordee")
        ile._age_s_orig = ile._age_s
        try:
            ile._age_s = lambda q: 10 ** 6
            self.assertEqual(ile.projeter(ile.lire())["approbations"][aid]["statut"], "expiree")
        finally:
            ile._age_s = ile._age_s_orig

    def test_reserve_au_president(self):
        aid, _ = ile.demander_approbation("git", "push", "push", "Bash", "git push origin main", MAIRE)
        with self.assertRaises(ile.ErreurIle):
            ile.accorder(aid, MAIRE)


class Terminal(unittest.TestCase):
    def test_phrase_exige_un_terminal(self):
        code = "import sys; sys.path.insert(0, %r); import president\ntry:\n    president.demander_phrase()\n    print('LUE')\nexcept president.ErreurPresident:\n    print('REFUS')" % str(Path(__file__).resolve().parents[1] / "presidence")
        sans = subprocess.run(["setsid", sys.executable, "-c", code], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=20)
        self.assertEqual(sans.stdout.strip(), "REFUS")
        if not shutil.which("script"):
            self.skipTest("commande script absente")
        PRESIDENCE = Path(__file__).resolve().parents[1] / "presidence"
        avec = subprocess.run(["script", "-qec", f"{sys.executable} -c \"import sys; sys.path.insert(0, '{PRESIDENCE}'); import president; print('TTY', president.terminal_disponible())\"", "/dev/null"],
                              capture_output=True, text=True, timeout=20)
        self.assertIn("TTY True", avec.stdout)


if __name__ == "__main__":
    unittest.main()
