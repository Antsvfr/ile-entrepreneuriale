"""Détournement d'import Python : régression de la faille de l'audit (json.py planté exécuté par le garde)
et de ses chemins indirects (garde → ile → president → hmac, hooks, serveur, commandes présidentielles).

Chaque test travaille sur une COPIE du dossier de l'île (jamais sur le vrai) : on y plante des modules piégés qui
laissent un marqueur puis terminent le processus avec le code 0 (pour le garde, 0 = « action autorisée »).
Une protection est prouvée quand le point d'entrée fait son travail normal ET qu'aucun marqueur n'apparaît.

ILE_SOURCE_TEST=<racine d'une île> fait tourner les mêmes tests sur une autre version (ex. le commit
d'avant la correction) pour constater qu'ils y échouent.
"""
import ast
import json
import marshal
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for _d in ("securite", "presidence", "orchestrateur"):
    sys.path.insert(0, str(RACINE / _d))
import ile  # noqa: E402
import president  # noqa: E402
from test_ile import Base, PHRASE  # noqa: E402

SOURCE = Path(os.environ.get("ILE_SOURCE_TEST") or RACINE).resolve()
president.ITERATIONS = 2000

# Modules standard importés par les points d'entrée et leurs dépendances (un fichier homonyme planté dans le
# dossier du script, ou le dossier courant, les remplaçait).
STANDARD = ["json", "re", "shlex", "subprocess", "pathlib", "typing", "hashlib", "hmac", "secrets", "unicodedata",
            "getpass", "argparse", "datetime", "tempfile", "fcntl", "functools", "threading", "posixpath",
            "webbrowser", "importlib", "__future__", "base64", "random", "struct", "contextlib", "plistlib"]
ILE_MODULES = ["ile", "president", "signature", "confinement"]
# Emplacement réel de chaque module de l'île : partout ailleurs, un homonyme est un piège.
VRAIS = {"securite": {"confinement", "garde"}, "presidence": {"president", "signature"}, "orchestrateur": {"ile"}}
CHEMINS_ILE = {"ile": "orchestrateur/ile.py", "president": "presidence/president.py", "signature": "presidence/signature.py"}


def _piege(nom: str, marqueurs: Path) -> str:
    """Source d'un module piégé : laisse un marqueur, puis termine le processus avec le code 0."""
    return ("import posix\n"
            f"fd = posix.open({str(marqueurs / ('MARQUEUR-' + nom))!r} + '-' + str(posix.getpid()), posix.O_WRONLY | posix.O_CREAT, 0o644)\n"
            "posix.close(fd)\n"
            "posix._exit(0)\n")


class Confinement(Base):
    def setUp(self):
        super().setUp()                                       # journal temporaire + identité de test (ile.OPS)
        self.racine = Path(tempfile.mkdtemp(prefix="ile-confinement-"))
        self.ile_dir = self.racine / "depot"                  # la racine du dépôt est l'île
        shutil.copytree(SOURCE, self.ile_dir, ignore=shutil.ignore_patterns(".git", "__pycache__", "journal.jsonl", "STOP",
                                                                            "*.log", ".serveur.pid", "node_modules"))
        self.marqueurs = self.racine / "marqueurs"
        self.marqueurs.mkdir()
        self.env = dict(os.environ, ILE_OPS=str(ile.OPS))
        for k in ("PYTHONPATH", "PYTHONSTARTUP", "PYTHONUSERBASE", "PYTHONHOME"):
            self.env.pop(k, None)

    def tearDown(self):
        shutil.rmtree(self.racine, ignore_errors=True)
        super().tearDown()

    # ------------------------------------------------------------------ outils
    def planter(self, dossiers, noms):
        for d in dossiers:
            d.mkdir(parents=True, exist_ok=True)
            for n in noms:
                (d / f"{n}.py").write_text(_piege(f"{d.name}-{n}", self.marqueurs), encoding="utf-8")

    def planter_partout(self, noms=None):
        noms = noms or (STANDARD + ILE_MODULES)
        # Dossiers des modules de l'île : noms standard + homonymes des modules de l'île qui n'y vivent pas (ex. un faux
        # president.py à côté d'ile.py) ; les vrais modules ne sont jamais écrasés.
        for d, vrais in VRAIS.items():
            self.planter([self.ile_dir / d], [n for n in noms if n not in vrais])
        self.planter([self.ile_dir / "orchestrateur" / "hooks", self.ile_dir / "residence", self.ile_dir / "audit", self.ile_dir], noms)

    def marques(self):
        return sorted(p.name for p in self.marqueurs.iterdir())

    def lancer(self, args, entree="", drapeaux=("-I", "-S"), env=None, cwd=None, timeout=60):
        r = subprocess.run([sys.executable, *drapeaux, *map(str, args)], input=entree, capture_output=True, text=True,
                           env=env or self.env, cwd=str(cwd or self.ile_dir), timeout=timeout)
        return r.returncode, r.stdout, r.stderr

    def garde(self, commande, drapeaux=("-I", "-S"), env=None, **extra):
        payload = {"tool_name": "Bash", "tool_input": {"command": commande}, "cwd": str(self.ile_dir), "agent_id": "a-test", **extra}
        return self.lancer([self.ile_dir / "securite" / "garde.py"], json.dumps(payload), drapeaux, env)

    def vider(self):
        for m in self.marqueurs.iterdir():
            m.unlink()

    def assertPropre(self):
        trouves = self.marques()
        for m in self.marqueurs.iterdir():                     # remis à zéro : chaque vérification est indépendante
            m.unlink()
        self.assertEqual(trouves, [], "un module planté s'est exécuté")

    # ------------------------------------------------------------------ l'attaque de l'audit
    def test_attaque_audit_json(self):
        """json.py planté à côté du garde (securite/) → le garde l'exécutait et laissait passer « git push origin main » (code 0)."""
        self.planter([self.ile_dir / "securite"], ["json"])
        for drapeaux in (("-I", "-S"), ()):                   # tel que lancé par les réglages, et même sans -I
            with self.subTest(drapeaux=drapeaux):
                self.vider()
                code, _, err = self.garde("git push origin main", drapeaux)
                self.assertEqual(code, 2, err)
                self.assertIn("opération sensible", err)
                self.assertPropre()

    def test_garde_tous_modules_plantes(self):
        self.planter_partout()
        for drapeaux in (("-I", "-S"), ()):
            for cmd, attendu in (("git push origin main", 2), ("ls", 0)):
                with self.subTest(drapeaux=drapeaux, cmd=cmd):
                    self.vider()
                    code, _, err = self.garde(cmd, drapeaux)
                    self.assertEqual(code, attendu, err)
                    self.assertPropre()

    def test_chemin_indirect_ile_president(self):
        """Le chemin de l'audit complémentaire : garde → ile → president → hmac / secrets / unicodedata plantés."""
        self.planter_partout()
        for drapeaux in (("-I", "-S"), ()):
            with self.subTest(drapeaux=drapeaux):
                self.vider()
                code, _, err = self.garde("python3 orchestrateur/ile.py --auteur president siege priorite --siege rev-em P1", drapeaux)
                self.assertEqual(code, 2, err)                 # refus inscrit : ile ET president ont été chargés
                self.assertIn("interdite", err)
                self.assertPropre()
        self.assertEqual(len(ile.etat()["refus"]), 2)

    def test_accord_president_puis_passage_unique(self):
        self.planter_partout()
        code, _, err = self.garde("git push origin main")
        self.assertEqual(code, 2, err)
        aid = re.search(r"A-\d+", err).group(0)
        ile.accorder(aid, self.cle, "test confinement")
        self.assertEqual(self.garde("git push origin main")[0], 0)   # passe une fois, signature vérifiée confinée
        self.assertEqual(self.garde("git push origin main")[0], 2)
        self.assertPropre()
        self.assertTrue(ile.verifier()["ok"])

    def test_arret_d_urgence_confine(self):
        self.planter_partout()
        stop = ile.OPS / "STOP"
        stop.write_text("arrêt")
        try:
            self.assertEqual(self.garde("ls")[0], 2)
            payload = {"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "cwd": str(self.ile_dir)}
            self.assertEqual(self.lancer([self.ile_dir / "securite" / "garde.py"], json.dumps(payload))[0], 0)
        finally:
            stop.unlink()
        self.assertPropre()

    def test_garde_echoue_ferme_au_demarrage(self):
        """Une erreur AVANT main() (import cassé) donnait le code 1, que Claude Code laisse passer : c'est un refus."""
        g = self.ile_dir / "securite" / "garde.py"
        g.write_text(g.read_text(encoding="utf-8").replace("import shlex  # noqa: E402", "import shlex_absent  # noqa: E402"), encoding="utf-8")
        code, _, err = self.garde("git push origin main")
        self.assertEqual(code, 2, err)
        self.assertIn("refusée par prudence", err)

    def test_commande_hook_echoue_fermee(self):
        """Commande exacte des réglages : même un garde.py illisible (SyntaxError, code 1) ou un python3 absent devient un refus."""
        reglages = self.racine / "depot" / ".claude"                    # copiés avec l'île (la racine du dépôt est l'île)
        reglages.mkdir(parents=True, exist_ok=True)
        shutil.copy(SOURCE / ".claude" / "settings.json", reglages / "settings.json")
        cmd = json.loads((reglages / "settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        env = dict(self.env, CLAUDE_PROJECT_DIR=str(self.racine / "depot"))
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": str(self.ile_dir)})
        lancer = lambda: subprocess.run(["bash", "-c", cmd], input=payload, capture_output=True, text=True, env=env, timeout=60).returncode
        self.assertEqual(lancer(), 0)                                              # fonctionnement normal
        g = self.ile_dir / "securite" / "garde.py"
        g.write_text("def (\n", encoding="utf-8")                                 # garde illisible
        self.assertEqual(lancer(), 2)
        g.unlink()                                                                 # garde absent
        self.assertEqual(lancer(), 2)

    def test_copie_extraction_git_vers_garde_fous(self):
        """Écritures de garde-fous qui ne les nomment pas (constat D1/D4 de l'inspection) : accord exigé."""
        sys.path.insert(0, str(self.ile_dir / "securite"))
        try:
            g = _charger_par_chemin("garde_copie2", self.ile_dir / "securite" / "garde.py")
        finally:
            sys.path.remove(str(self.ile_dir / "securite"))
        cwd = str(self.ile_dir)
        A = lambda cmd: g.analyser({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}).issue
        for cmd in ("cp /tmp/evil/garde.py securite/", "cp /tmp/x/confinement.py securite", "install -m 644 /tmp/e/garde.py securite/",
                    "mv /tmp/e/hmac.py orchestrateur/", "cp -r /tmp/evil/. securite/", "cp -a /tmp/evil/* presidence/", "cp -t orchestrateur /tmp/e/ile.py",
                    "rsync -a /tmp/evil/ securite/", "tar -xf /tmp/e.tar -C securite", "tar xzf /tmp/e.tgz", "unzip /tmp/e.zip -d presidence",
                    "cp /tmp/x/serveur.py residence/", "ln -sf /tmp/evil.py securite/", "mv securite /tmp/ailleurs", "rm -rf presidence",
                    "rm securite/garde.py", "cp -r /tmp/depot/. ..",
                    "git checkout autre -- securite", "git checkout a5c4d72", "git checkout a5c4d72 -- .", "git restore --source=a5c4d72 securite",
                    "git reset --hard HEAD~3", "git stash pop", "git apply /tmp/x.patch", "git pull", "git merge autre",
                    "git config remote.origin.push HEAD:refs/heads/main", "git config --add branch.claude/x.merge refs/heads/main", "git remote set-url origin /tmp/x"):
            with self.subTest(cmd=cmd):
                self.assertEqual(A(cmd), "approbation")
        for chemin in (str(self.racine / "depot" / ".git" / "config"), str(self.racine / "depot" / ".git" / "hooks" / "pre-push"),
                       "tests/test_x.py", "tests/hmac.py", "tests/residence_ui.js"):
            with self.subTest(chemin=chemin):
                self.assertEqual(g.analyser({"tool_name": "Write", "tool_input": {"file_path": chemin}, "cwd": cwd}).issue, "approbation")
        for cmd in ("cp /tmp/notes.md projets/rev-em/", "cp -r /tmp/docs projets/rev-em/", "mv projets/rev-em/a.md projets/rev-em/b.md",
                    "cp residence/village/ville.js /tmp/", "tar -xf /tmp/a.tar -C /tmp/x", "unzip /tmp/a.zip -d /tmp/x", "rm -rf node_modules", "rm projets/rev-em/a.md",
                    "git status", "git commit -m x", "git checkout -b claude/nouvelle", "git checkout -- projets/rev-em/a.md", "git config --get user.name",
                    "git config user.name", "git log --oneline", "git stash", "git push -u origin claude/x", "git -C /tmp/autre checkout main"):
            with self.subTest(cmd=cmd):
                self.assertEqual(A(cmd), "autoriser")

    def test_push_implicite_vers_main(self):
        """remote.origin.push = HEAD:refs/heads/main dans .git/config : « git push origin » depuis une branche de travail."""
        depot = self.racine / "git"
        subprocess.run(["git", "init", "-q", "--bare", str(depot / "distant.git")], check=True)
        subprocess.run(["git", "init", "-q", "-b", "claude/x", str(depot / "local")], check=True)
        local = str(depot / "local")
        subprocess.run(["git", "-C", local, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty", "-m", "x"], check=True)
        subprocess.run(["git", "-C", local, "remote", "add", "origin", str(depot / "distant.git")], check=True)
        sys.path.insert(0, str(self.ile_dir / "securite"))
        try:
            g = _charger_par_chemin("garde_copie3", self.ile_dir / "securite" / "garde.py")
        finally:
            sys.path.remove(str(self.ile_dir / "securite"))
        A = lambda cmd: g.analyser({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": local}).issue
        self.assertEqual(A("git push origin"), "autoriser")
        subprocess.run(["git", "-C", local, "config", "remote.origin.push", "HEAD:refs/heads/main"], check=True)
        self.assertEqual(A("git push origin"), "approbation")
        self.assertEqual(A("git push"), "approbation")
        self.assertEqual(A("git push origin claude/x"), "autoriser")             # destination explicite : la config ne joue pas
        subprocess.run(["git", "-C", local, "config", "--unset", "remote.origin.push"], check=True)
        subprocess.run(["git", "-C", local, "config", "branch.claude/x.merge", "refs/heads/main"], check=True)
        self.assertEqual(A("git push"), "approbation")

    # ------------------------------------------------------------------ hooks et commandes
    def test_hooks_etat_ile(self):
        self.planter_partout()
        hook = self.ile_dir / "orchestrateur" / "hooks" / "etat-ile.py"
        for drapeaux in (("-I", "-S"), ()):
            for cmd in ("debut", "fin", "repos"):
                with self.subTest(drapeaux=drapeaux, cmd=cmd):
                    self.vider()
                    payload = {"agent_type": "forgeron", "agent_id": f"a-{cmd}", "session_id": "s-test"}
                    code, _, err = self.lancer([hook, cmd], json.dumps(payload), drapeaux)
                    self.assertEqual(code, 0, err)
                    self.assertPropre()
        self.assertFalse((self.ile_dir / "orchestrateur" / "registre" / "capteurs-erreurs.log").exists(),
                         (self.ile_dir / "orchestrateur" / "registre" / "capteurs-erreurs.log").read_text() if (self.ile_dir / "orchestrateur" / "registre" / "capteurs-erreurs.log").exists() else "")
        types = [e["type"] for e in ile.lire()]
        self.assertIn("run.debut", types)                      # le registre a bien été écrit par le hook confiné

    def test_capteur_session_et_verifier(self):
        self.planter_partout()
        for args in (["capteur", "session"], ["verifier"], ["etat"]):
            for drapeaux in (("-I", "-S"), ()):
                with self.subTest(args=args, drapeaux=drapeaux):
                    self.vider()
                    code, out, err = self.lancer([self.ile_dir / "orchestrateur" / "ile.py", *args], "{}", drapeaux)
                    self.assertEqual(code, 0, err)
                    self.assertPropre()

    def test_commande_presidentielle(self):
        """`./ile president statut` : la commande où le président tape sa phrase charge getpass, hmac, president."""
        self.planter_partout()
        code, out, err = self.lancer([self.ile_dir / "orchestrateur" / "ile.py", "president", "statut"])
        self.assertEqual(code, 0, err)
        self.assertIn("Identité présidentielle", out)
        self.assertPropre()
        # chemin complet de lecture de la phrase, sans terminal : refus propre, aucun module planté (getpass…)
        code, out, err = self.lancer([self.ile_dir / "orchestrateur" / "ile.py", "president", "approuver", "A-9999"])
        self.assertNotEqual(code, 0)
        self.assertPropre()

    def test_lanceur_statut(self):
        self.planter_partout()
        r = subprocess.run(["bash", str(self.ile_dir / "ile"), "statut"], capture_output=True, text=True, env=dict(self.env, ILE_PORT=str(_port_libre())),
                           cwd=str(self.ile_dir), timeout=60)
        self.assertIn("Identité présidentielle", r.stdout + r.stderr)
        self.assertPropre()

    # ------------------------------------------------------------------ serveur
    def test_serveur(self):
        self.planter_partout()
        for drapeaux in (("-I", "-S"), ()):
            with self.subTest(drapeaux=drapeaux):
                self.vider()
                port = _port_libre()
                p = subprocess.Popen([sys.executable, *drapeaux, str(self.ile_dir / "residence" / "serveur.py"), "--port", str(port), "--sans-navigateur"],
                                     cwd=str(self.ile_dir), env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                try:
                    sante = None
                    for _ in range(100):
                        try:
                            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/sante", timeout=1) as r:
                                sante = json.load(r)
                            break
                        except Exception:
                            if p.poll() is not None:
                                break
                            time.sleep(0.1)
                    self.assertIsNotNone(sante, p.stdout.read() if p.poll() is not None else "pas de réponse")
                    self.assertEqual(sante.get("ile"), "Île Entrepreneuriale")
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/etat", timeout=5) as r:
                        self.assertIn("approbations_en_attente", json.load(r))   # a lu le journal (ile confiné)
                    self.assertPropre()
                finally:
                    p.terminate()
                    p.wait(timeout=10)
                    p.stdout.close()

    # ------------------------------------------------------------------ autres vecteurs d'import
    def test_pythonpath_et_site_utilisateur(self):
        """PYTHONPATH, usercustomize et fichiers .pth du site utilisateur : ignorés par « -I -S »."""
        pp = self.racine / "pythonpath"
        self.planter([pp], STANDARD)
        base = self.racine / "userbase"
        env = dict(self.env, PYTHONPATH=str(pp), PYTHONUSERBASE=str(base))
        site_u = subprocess.run([sys.executable, "-c", "import site; print(site.getusersitepackages())"], capture_output=True, text=True,
                                env=dict(env, PYTHONPATH="")).stdout.strip()
        Path(site_u).mkdir(parents=True)
        (Path(site_u) / "usercustomize.py").write_text(_piege("usercustomize", self.marqueurs), encoding="utf-8")
        (Path(site_u) / "piege.pth").write_text("import posix; posix.close(posix.open(%r, posix.O_WRONLY | posix.O_CREAT, 0o644))\n"
                                                 % str(self.marqueurs / "MARQUEUR-pth"), encoding="utf-8")
        # Témoin : sans drapeaux, ces vecteurs s'exécutent bien (le test n'est pas vide).
        self.garde("ls", (), env)
        self.assertTrue(self.marques(), "témoin : le site utilisateur aurait dû s'exécuter sans -I")
        for p in self.marqueurs.iterdir():
            p.unlink()
        for cible in ([self.ile_dir / "securite" / "garde.py"], [self.ile_dir / "orchestrateur" / "ile.py", "verifier"],
                      [self.ile_dir / "orchestrateur" / "hooks" / "etat-ile.py", "repos"]):
            with self.subTest(cible=cible[0].name):
                self.vider()
                payload = {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}, "cwd": str(self.ile_dir)}
                code, _, err = self.lancer(cible, json.dumps(payload), ("-I", "-S"), env)
                self.assertIn(code, (0, 2) if cible[0].name != "garde.py" else (2,), err)
                self.assertPropre()

    def test_pyc_falsifie(self):
        """Un .pyc forgé dans le __pycache__ d'un module de l'île (date et taille du source recopiées) : jamais chargé."""
        import importlib.util
        for nom in ("ile", "president", "signature"):
            source = self.ile_dir / CHEMINS_ILE[nom]
            st = source.stat()
            code = compile(_piege(f"pyc-{nom}", self.marqueurs), str(source), "exec")
            entete = importlib.util.MAGIC_NUMBER + (0).to_bytes(4, "little") + (int(st.st_mtime) & 0xFFFFFFFF).to_bytes(4, "little") \
                + (st.st_size & 0xFFFFFFFF).to_bytes(4, "little")
            pyc = Path(importlib.util.cache_from_source(str(source)))
            pyc.parent.mkdir(exist_ok=True)
            pyc.write_bytes(entete + marshal.dumps(code))
        # Témoin : un import ordinaire charge bien le .pyc forgé (le vecteur est réel).
        subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(self.ile_dir / 'presidence')!r}); import signature"],
                       env=self.env, capture_output=True, timeout=30)
        self.assertTrue(self.marques(), "témoin : le .pyc forgé aurait dû être chargé par un import ordinaire")
        for p in self.marqueurs.iterdir():
            p.unlink()
        self.assertEqual(self.garde("git push origin main")[0], 2)
        self.assertEqual(self.garde("python3 orchestrateur/ile.py --auteur president x")[0], 2)
        self.assertEqual(self.lancer([self.ile_dir / "orchestrateur" / "ile.py", "verifier"])[0], 0)
        self.assertEqual(self.lancer([self.ile_dir / "orchestrateur" / "ile.py", "president", "statut"])[0], 0)
        self.assertPropre()

    def test_charger_refuse_module_inattendu(self):
        prog = ("import sys\n"
                f"sys.path.insert(0, {str(self.ile_dir / 'securite')!r})\n"
                "faux = type(sys)('ile'); faux.__file__ = '/tmp/ailleurs/ile.py'; sys.modules['ile'] = faux\n"
                "import confinement\n"
                "try:\n    confinement.charger('ile')\n    print('ACCEPTE')\nexcept confinement.ErreurConfinement as e:\n    print('REFUSE')\n"
                "try:\n    confinement.charger('json')\n    print('ACCEPTE')\nexcept confinement.ErreurConfinement:\n    print('REFUSE')\n")
        out = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, env=self.env, timeout=30).stdout.split()
        self.assertEqual(out, ["REFUSE", "REFUSE"])

    # ------------------------------------------------------------------ ce qui empêche de semer des modules
    def test_garde_soumet_modules_a_accord(self):
        sys.path.insert(0, str(self.ile_dir / "securite"))
        try:
            g = _charger_par_chemin("garde_copie", self.ile_dir / "securite" / "garde.py")
        finally:
            sys.path.remove(str(self.ile_dir / "securite"))
        cwd = str(self.ile_dir)
        for cmd in ("cat > securite/json.py <<EOF\nx\nEOF", "echo x > orchestrateur/hmac.py", "cp /tmp/x.py presidence/getpass.py",
                    "printf x > orchestrateur/__pycache__/ile.cpython-39.pyc", "echo x > securite/x.pth", "sed -i 's/-I -S//' ile",
                    "echo x >> audit/inspection.sh", "cp /tmp/c.py securite/confinement.py"):
            with self.subTest(cmd=cmd):
                self.vider()
                self.assertEqual(g.analyser({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}).issue, "approbation")
        for chemin in ("securite/json.py", "orchestrateur/__pycache__/ile.cpython-313.pyc", "securite/confinement.py", "ile", "audit/inspection.sh", "presidence/hmac.py", "residence/x.py"):
            with self.subTest(chemin=chemin):
                self.vider()
                self.assertEqual(g.analyser({"tool_name": "Write", "tool_input": {"file_path": chemin}, "cwd": cwd}).issue, "approbation")
        for cmd in ("python3 orchestrateur/ile.py journal", "cat orchestrateur/ile.py", "ls securite", "python3 -I -S audit/preuves.py"):
            with self.subTest(cmd=cmd):
                self.vider()
                self.assertEqual(g.analyser({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}).issue, "autoriser")


class Invocations(unittest.TestCase):
    """Tous les points d'entrée privilégiés sont lancés en « python3 -I -S » ; aucun ne réordonne sys.path."""

    def test_reglages_hooks(self):
        for f in (SOURCE / ".claude" / "settings.json",):
            if not f.exists():
                continue
            with self.subTest(f=str(f)):
                cmds = [h["command"] for groupe in json.loads(f.read_text(encoding="utf-8"))["hooks"].values() for g in groupe for h in g["hooks"]]
                py = [c for c in cmds if "python" in c.split()[0]]
                self.assertTrue(py)
                for c in py:
                    # interpréteur système (pas un « python3 » placé avant dans le PATH), mode isolé, sans site
                    self.assertTrue(c.startswith("/usr/bin/python3 -I -S "), c)
                garde = [c for c in cmds if "garde.py" in c]
                self.assertTrue(garde and all(c.endswith(" || exit 2") for c in garde), garde)   # échec fermé

    def test_lanceur(self):
        texte = (SOURCE / "ile").read_text(encoding="utf-8")
        # "$PY" en position de commande (hors « [ -n "$PY" ] » et hors argument passé au générateur du LaunchAgent)
        appels = re.findall(r'(?<!-n )(?<!"\$LABEL" )"\$PY"([^\n]{0,8})', texte)
        self.assertGreaterEqual(len(appels), 10)
        for a in appels:
            self.assertTrue(a.startswith(" -I -S "), a)
        self.assertIn('"ProgramArguments": [py, "-I", "-S", ici + "/residence/serveur.py"', texte)
        insp = (SOURCE / "audit" / "inspection.sh").read_text(encoding="utf-8")
        execs = re.findall(r'(?:^|\bif |\$\()\s*python3\b([^\n]{0,8})', insp, re.M)
        self.assertGreaterEqual(len(execs), 3)
        for a in execs:
            self.assertTrue(a.startswith(" -I -S "), a)

    def test_aucun_future_ni_sys_path_insert(self):
        for rel in ("securite/garde.py", "orchestrateur/ile.py", "presidence/president.py", "presidence/signature.py",
                    "securite/confinement.py", "residence/serveur.py", "orchestrateur/hooks/etat-ile.py", "audit/preuves.py"):
            with self.subTest(rel=rel):
                src = (SOURCE / rel).read_text(encoding="utf-8")
                arbre = ast.parse(src)
                self.assertFalse([n for n in ast.walk(arbre) if isinstance(n, ast.ImportFrom) and n.module == "__future__"])
                self.assertNotIn("sys.path.insert", src)
                self.assertNotIn("sys.path.append", src)


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _charger_par_chemin(nom, chemin):
    import importlib.util
    spec = importlib.util.spec_from_file_location(nom, chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


if __name__ == "__main__":
    unittest.main()
