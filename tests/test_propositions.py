"""Propositions soumises au président : circuit, décisions signées, autorité, traçabilité, serveur.
Chaque test travaille dans un registre temporaire avec une identité DE TEST (jamais celle du président)."""
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for _d in ("securite", "presidence", "orchestrateur"):
    sys.path.insert(0, str(RACINE / _d))
import ile  # noqa: E402
import organisation as org  # noqa: E402
import president  # noqa: E402
import propositions as P  # noqa: E402
from test_ile import Base, MAIRE, PHRASE, isoler  # noqa: E402
from test_travail import HOOK, run_de  # noqa: E402

president.ITERATIONS = 2000


def proposer(auteur=MAIRE, origine="rev-em", soumettre=True, **kw):
    d = dict(titre="Ouvrir un atelier qualité", description="Créer un atelier de relecture pour REV-EM.", categorie="projet",
             objectif="Réduire les régressions", consequences="Deux jours de travail de la Forge", cout="2 jours",
             risques=["retard sur la PR en cours"], institutions=["forge"])
    d.update(kw)
    ev = P.creer(origine, d.pop("titre"), d.pop("description"), d.pop("categorie"), d.pop("objectif"), d.pop("consequences"), auteur, soumettre=soumettre, **d)
    return ev["donnees"]["proposition"]


class Circuit(Base):
    def setUp(self):
        super().setUp()
        org.amorcer(MAIRE)
        P.activer_decisions(self.cle)

    def p(self, pid):
        return P.etat()["propositions"][pid]

    def test_01_02_03_soumise_visible_et_complete(self):
        pid = proposer()
        p = self.p(pid)
        self.assertEqual(p["statut"], "soumise")                                    # 1. soumise
        self.assertIn(pid, P.etat()["propositions"])                               # 2. dans la boîte (projection lue par la page)
        for k in ("titre", "description", "categorie", "objectif", "consequences", "cout", "risques", "institutions", "auteur", "origine", "soumise"):
            self.assertTrue(p[k], k)                                               # 3. dossier complet
        self.assertEqual(p["institutions"], ["forge", "rev-em"])
        self.assertEqual([h["action"] for h in p["historique"]], ["proposition créée", "soumise"])

    def test_04_approbation_signee(self):
        pid = proposer()
        ev = P.approuver(pid, self.cle, self.p(pid)["version"], motif="utile")
        self.assertEqual((ev["auteur"]["role"], ev["auteur"]["verifie"]), ("president", "signature"))
        self.assertTrue(ile.signature_valide(ev, self.cle.publique))
        p = self.p(pid)
        self.assertEqual((p["statut"], p["decision"]["evenement"], p["decision"]["destinataires"]), ("approuvee", ev["id"], ["forge", "rev-em"]))
        self.assertTrue(ile.verifier()["ok"])

    def test_05_06_refus_avec_motif_obligatoire(self):
        pid = proposer()
        v = self.p(pid)["version"]
        for motif in (None, "", "   "):
            with self.assertRaises(P.ErreurProposition):
                P.refuser(pid, self.cle, v, motif)                                 # 6. motif obligatoire
        P.refuser(pid, self.cle, v, "hors priorité")
        p = self.p(pid)
        self.assertEqual((p["statut"], p["decision"]["motif"]), ("refusee", "hors priorité"))   # 5.
        self.assertTrue(p["archivee"])

    def test_07_modifications_puis_resoumission(self):
        r, chef = run_de("chef-rev-em")
        pid = proposer(auteur=chef)
        P.demander_modifications(pid, self.cle, "Chiffrage absent", "Ajouter le coût détaillé", "2099-01-31")
        self.assertEqual(self.p(pid)["statut"], "modifications_demandees")
        with self.assertRaises(P.ErreurProposition):
            P.modifier(pid, {"cout": "3 jours"}, "x", MAIRE)                       # pas l'auteur
        P.modifier(pid, {"cout": "3 jours et 1 000 €"}, "chiffrage ajouté", chef)
        P.soumettre_(pid, chef)
        p = self.p(pid)
        self.assertEqual((p["statut"], p["cout"]), ("en_attente_decision", "3 jours et 1 000 €"))
        modif = next(h for h in p["historique"] if h["type"] == "proposition.modifiee")
        self.assertEqual(modif["avant"], {"cout": "2 jours"})                     # historique conservé

    def test_08_demande_d_avis_suivie_et_jamais_decisive(self):
        pid = proposer()
        dem = P.demander_avis(pid, "conseil", "Le Conseil est-il favorable ?", cle=self.cle)
        self.assertEqual(self.p(pid)["statut"], "en_analyse")
        with self.assertRaises(P.ErreurProposition):
            P.rendre_avis(pid, dem["id"], "favorable", "oui", MAIRE)               # le Maire n'est pas du Conseil
        r, critique = run_de("critique-clarte")
        P.rendre_avis(pid, dem["id"], "defavorable", "Trop tôt.", critique)
        p = self.p(pid)
        self.assertEqual((p["statut"], p["decision"]), ("en_attente_decision", None))   # avis défavorable ≠ refus
        self.assertEqual(p["avis"][0]["sens"], "defavorable")
        with self.assertRaises(P.ErreurProposition):
            P.rendre_avis(pid, dem["id"], "favorable", "bis", critique)            # un seul avis par demande
        pid2 = proposer(titre="Seconde")
        d2 = P.demander_avis(pid2, "conseil", "Avis ?", cle=self.cle)
        P.rendre_avis(pid2, d2["id"], "favorable", "Oui.", critique)
        self.assertEqual(self.p(pid2)["statut"], "en_attente_decision")             # avis favorable ≠ approbation

    def test_09_agent_ordinaire_ne_decide_pas(self):
        pid = proposer()
        r, chef = run_de("chef-rev-em")
        ev = ile.ajouter("proposition.approuvee", {"proposition": pid}, chef)
        self.assertIn(ev["id"], [x["id"] for x in ile.etat()["rejets"]])
        self.assertEqual(self.p(pid)["statut"], "soumise")
        self.assertFalse(ile.verifier()["ok"])
        with self.assertRaises(ile.ErreurIle):
            P.approuver(pid, None, self.p(pid)["version"])                         # sans clé : refusé avant écriture

    def test_10_le_maire_ne_se_fait_pas_passer_pour_le_president(self):
        pid = proposer()
        for auteur in ({"role": "president", "verifie": "declare"}, {"role": "president", "verifie": "signature"}, MAIRE):
            ile.ajouter("proposition.approuvee", {"proposition": pid}, auteur)    # écrit à la main, sans signature
        self.assertEqual(self.p(pid)["statut"], "soumise")
        self.assertEqual(len(ile.etat()["rejets"]), 3)
        # signature d'une autre clé (intrus) : rejetée aussi
        intrus, _ = president.nouvelle_identite("phrase d'un agent intrus")
        ile.ajouter("proposition.refusee", {"proposition": pid, "motif": "x"}, {}, cle=intrus)
        self.assertEqual(self.p(pid)["statut"], "soumise")

    def test_11_pas_de_double_approbation_silencieuse(self):
        pid = proposer()
        v = self.p(pid)["version"]
        P.approuver(pid, self.cle, v)
        with self.assertRaises(P.ErreurProposition) as e:
            P.approuver(pid, self.cle, v)
        self.assertIn("déjà approuvee", str(e.exception))
        # même un acte signé inscrit en contournant le module est ignoré ET signalé (anomalie)
        ile.ajouter("proposition.refusee", {"proposition": pid, "motif": "forcé"}, {}, cle=self.cle)
        e2 = P.etat()
        self.assertEqual(e2["propositions"][pid]["statut"], "approuvee")
        self.assertTrue(any("seconde décision" in a["motif"] for a in e2["anomalies"]))

    def test_12_decision_non_modifiable_rectification_motivee(self):
        pid = proposer()
        P.approuver(pid, self.cle, self.p(pid)["version"])
        avant = ile.JOURNAL.read_text(encoding="utf-8")
        with self.assertRaises(P.ErreurProposition):
            P.refuser(pid, self.cle, self.p(pid)["version"], "changement d'avis")
        with self.assertRaises(P.ErreurProposition):
            P.rectifier(pid, self.cle, "refusee", "")                              # motif obligatoire
        P.rectifier(pid, self.cle, "refusee", "erreur matérielle constatée")
        p = self.p(pid)
        self.assertTrue(ile.JOURNAL.read_text(encoding="utf-8").startswith(avant))   # rien de réécrit : ajout seul
        self.assertEqual((p["statut"], len(p["decisions"]), p["decision"]["rectifie"]), ("refusee", 2, p["decisions"][0]["evenement"]))
        self.assertTrue(ile.verifier()["ok"])

    def test_12b_dossier_modifie_apres_examen(self):
        r, chef = run_de("chef-rev-em")
        pid = proposer(auteur=chef)
        P.demander_modifications(pid, self.cle, "obs", "att")
        v_ancienne = self.p(pid)["version"]
        P.modifier(pid, {"description": "nouvelle description"}, "maj", chef)
        P.soumettre_(pid, chef)
        with self.assertRaises(P.ErreurProposition):
            P.approuver(pid, self.cle, v_ancienne)                                 # le président n'a pas vu cette version

    def test_13_historique_complet_au_registre(self):
        pid = proposer()
        P.transmettre(pid, "president", MAIRE)
        d = P.demander_avis(pid, "forge", "Faisable ?", cle=self.cle)
        r, forgeron = run_de("forgeron")
        P.rendre_avis(pid, d["id"], "reserve", "Faisable en deux temps.", forgeron)
        P.approuver(pid, self.cle, self.p(pid)["version"])
        types = [h["type"] for h in self.p(pid)["historique"]]
        self.assertEqual(types, ["proposition.creee", "proposition.soumise", "proposition.transmise", "proposition.avis_demande",
                                 "proposition.avis_rendu", "proposition.approuvee"])
        evs = [e for e in ile.lire() if e["donnees"].get("proposition") == pid]
        self.assertEqual([e["type"] for e in evs], types)                         # chaque étape est un événement chaîné
        self.assertTrue(ile.verifier()["ok"])

    def test_14_persistance(self):
        pid = proposer()
        P.approuver(pid, self.cle, self.p(pid)["version"])
        ile._SIG_OK.clear()                                                        # nouvelle lecture, sans cache
        self.assertEqual(P.projeter(ile.lire())["propositions"][pid]["statut"], "approuvee")

    def test_15_institutions_informees(self):
        pid = proposer()
        P.approuver(pid, self.cle, self.p(pid)["version"])
        b = P.etat()["boites"]
        self.assertEqual(sorted(b), ["forge", "rev-em"])
        self.assertFalse(b["forge"][0]["recue"])
        r, forgeron = run_de("forgeron")
        with self.assertRaises(P.ErreurProposition):
            P.accuser_reception(pid, "lexnote", forgeron)                          # non destinataire
        P.accuser_reception(pid, "forge", forgeron)
        self.assertTrue(P.etat()["boites"]["forge"][0]["recue"])

    def test_16_suivi_jusqu_a_l_execution(self):
        pid = proposer()
        with self.assertRaises(P.ErreurProposition):
            P.mettre_en_oeuvre(pid, "forge", "atelier", MAIRE)                     # pas encore approuvée
        P.approuver(pid, self.cle, self.p(pid)["version"])
        P.mettre_en_oeuvre(pid, "forge", "Atelier hebdomadaire de relecture", MAIRE, echeance="2099-02-01")
        r, chef = run_de("chef-rev-em")
        with self.assertRaises(P.ErreurProposition):
            P.executer(pid, "debut", chef)                                         # pas le responsable désigné
        r, forgeron = run_de("forgeron")
        P.executer(pid, "debut", forgeron)
        self.assertEqual(self.p(pid)["statut"], "en_execution")
        with self.assertRaises(P.ErreurProposition):
            P.executer(pid, "fin", forgeron, "")                                   # résultats obligatoires
        P.executer(pid, "fin", forgeron, "3 relectures faites, 2 régressions évitées")
        p = self.p(pid)
        self.assertEqual((p["statut"], p["execution"]["resultat"]), ("executee", "3 relectures faites, 2 régressions évitées"))
        P.archiver(pid, "cycle terminé", MAIRE)
        self.assertTrue(self.p(pid)["archivee"])

    def test_auteur_non_verifie_ne_propose_pas(self):
        with self.assertRaises(P.ErreurProposition):
            proposer(auteur={"role": "chef-rev-em", "verifie": "declare"})
        r, chef = run_de("chef-rev-em")
        with self.assertRaises(P.ErreurProposition):
            proposer(auteur=chef, origine="lexnote")                               # pas au nom d'une autre entreprise
        with self.assertRaises(P.ErreurProposition):
            proposer(auteur=chef, pieces=["../../etc/passwd"])                     # pièce hors de l'île

    def test_ancienne_demande_de_decision(self):
        d = ile.demander_decision("rev-em", "Fusionner ?", "Fusionner la PR ?", MAIRE)["id"]
        p = self.p(d)
        self.assertEqual((p["statut"], p["ancienne"]), ("en_attente_decision", True))
        with self.assertRaises(P.ErreurProposition):
            P.demander_modifications(d, self.cle, "o", "a")
        P.refuser(d, self.cle, p["version"], "pas maintenant")
        self.assertEqual(ile.etat()["decisions"][d]["verdict"], "refusee")         # la Résidence voit la même décision
        P.rectifier(d, self.cle, "approuvee", "erreur de lecture du dossier")
        self.assertEqual((ile.etat()["decisions"][d]["verdict"], self.p(d)["statut"]), ("approuvee", "approuvee"))


class SansActivationNiIdentite(Base):
    def test_identite_absente(self):
        isoler(Path(tempfile.mkdtemp()))                                           # registre sans identité présidentielle
        org.amorcer(MAIRE)
        pid = proposer()
        intrus, _ = president.nouvelle_identite("phrase d'un agent intrus")
        with self.assertRaises(P.ErreurProposition) as e:
            P.approuver(pid, intrus, P.etat()["propositions"][pid]["version"])
        self.assertIn("aucune identité présidentielle", str(e.exception))
        P.activer_decisions(intrus)                                                # activation par une clé non inscrite : rejetée
        self.assertIsNone(P.etat()["activation"])
        self.assertFalse(ile.verifier()["ok"])
        with self.assertRaises(P.ErreurProposition):
            P.approuver(pid, intrus, P.etat()["propositions"][pid]["version"])
        self.assertEqual(P.etat()["propositions"][pid]["statut"], "soumise")

    def test_identite_invalide_et_non_activee(self):
        org.amorcer(MAIRE)
        pid = proposer()
        with self.assertRaises(P.ErreurProposition) as e:
            P.approuver(pid, self.cle, P.etat()["propositions"][pid]["version"])
        self.assertIn("pas activées", str(e.exception))
        with self.assertRaises(ile.ErreurIle):
            ile.deverrouiller("mauvaise phrase de test")                           # phrase invalide : aucune clé
        ile.ajouter(P.ACTIVATION, {"declaration": "x"}, MAIRE)                     # activation par le Maire : rejetée
        self.assertIsNone(P.etat()["activation"])
        P.activer_decisions(self.cle)
        with self.assertRaises(P.ErreurProposition):
            P.activer_decisions(self.cle)                                          # une seule fois


def _serveur():
    import importlib.util
    spec = importlib.util.spec_from_file_location("serveur_test_prop", RACINE / "residence" / "serveur.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Serveur(Base):
    """Le serveur exige session déverrouillée, jeton, confirmation et version ; il relit l'acte avant de répondre."""
    @classmethod
    def setUpClass(cls):
        import http.server
        cls.m = _serveur()
        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), cls.m.Gestionnaire)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def setUp(self):
        super().setUp()
        org.amorcer(MAIRE)
        self.pid = proposer()
        self.cookie = None

    def req(self, methode, chemin, corps=None, jeton=True):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = {"Host": f"127.0.0.1:{self.port}"}
        if corps is not None:
            h["Content-Type"] = "application/json"
            if jeton:
                h["X-Ile-Jeton"] = self.m.JETON
        if self.cookie:
            h["Cookie"] = self.cookie
        c.request(methode, chemin, body=json.dumps(corps) if corps is not None else None, headers=h)
        r = c.getresponse()
        ck = r.getheader("Set-Cookie")
        if ck and "ile_session=" in ck:
            self.cookie = ck.split(";")[0]
        return r.status, json.loads(r.read() or b"{}")

    def test_boite_et_blocages(self):
        s, d = self.req("GET", "/api/propositions")
        self.assertEqual(s, 200)
        self.assertIn(self.pid, d["propositions"])
        self.assertFalse(d["acces"]["decision_possible"])
        self.assertTrue(any("verrouillée" in b for b in d["acces"]["blocages"]))
        self.assertTrue(any("non activées" in b for b in d["acces"]["blocages"]))

    def test_sans_session_refuse(self):
        v = P.etat()["propositions"][self.pid]["version"]
        s, d = self.req("POST", "/api/proposition", {"action": "approuver", "id": self.pid, "version": v, "confirmation": self.pid})
        self.assertEqual(s, 401)
        s, d = self.req("POST", "/api/proposition", {"action": "approuver", "id": self.pid}, jeton=False)
        self.assertEqual(s, 403)
        self.assertEqual(P.etat()["propositions"][self.pid]["statut"], "soumise")

    def test_parcours_complet_signe(self):
        s, d = self.req("POST", "/api/president/deverrouiller", {"phrase": "mauvaise phrase de test"})
        self.assertEqual(s, 403)
        s, d = self.req("POST", "/api/president/deverrouiller", {"phrase": PHRASE})
        self.assertEqual(s, 200)
        v = P.etat()["propositions"][self.pid]["version"]
        s, d = self.req("POST", "/api/proposition", {"action": "approuver", "id": self.pid, "version": v, "confirmation": self.pid})
        self.assertEqual(s, 400); self.assertIn("pas activées", d["erreur"])
        s, d = self.req("POST", "/api/proposition", {"action": "activer", "confirmation": "oui"})
        self.assertEqual(s, 400)
        s, d = self.req("POST", "/api/proposition", {"action": "activer", "confirmation": "ACTIVER"})
        self.assertEqual((s, d["signature_verifiee"]), (200, True))
        s, d = self.req("POST", "/api/proposition", {"action": "approuver", "id": self.pid, "version": v})
        self.assertEqual(s, 400); self.assertIn("confirmation", d["erreur"])         # confirmation explicite exigée
        s, d = self.req("POST", "/api/proposition", {"action": "refuser", "id": self.pid, "version": v, "confirmation": self.pid, "motif": ""})
        self.assertEqual(s, 400); self.assertIn("motif", d["erreur"])
        s, d = self.req("POST", "/api/proposition", {"action": "approuver", "id": self.pid, "version": "0" * 64, "confirmation": self.pid})
        self.assertEqual(s, 400); self.assertIn("changé", d["erreur"])
        s, d = self.req("POST", "/api/proposition", {"action": "approuver", "id": self.pid, "version": v, "confirmation": self.pid, "motif": "accordé"})
        self.assertEqual((s, d["statut"], d["signature_verifiee"]), (200, "approuvee", True))
        ev = next(e for e in ile.lire() if e["id"] == d["evenement"])
        self.assertEqual((ev["type"], ev["auteur"]["role"], ev["auteur"]["canal"]), ("proposition.approuvee", "president", "Résidence"))
        s, d2 = self.req("POST", "/api/proposition", {"action": "approuver", "id": self.pid, "version": v, "confirmation": self.pid})
        self.assertEqual(s, 400); self.assertIn("déjà", d2["erreur"])
        s, d3 = self.req("GET", "/api/propositions")
        self.assertTrue(d3["acces"]["decision_possible"])
        self.assertEqual(d3["propositions"][self.pid]["statut"], "approuvee")
        self.assertTrue(ile.verifier()["ok"])


if __name__ == "__main__":
    unittest.main()
