"""Le garde : règles, et cycle complet blocage → demande → accord signé → passage unique."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
for _d in ("securite", "presidence", "orchestrateur"):
    sys.path.insert(0, str(RACINE / _d))
OPS = RACINE / "securite"
import garde  # noqa: E402
import ile  # noqa: E402
import president  # noqa: E402
from test_ile import Base, PHRASE  # noqa: E402

ILE = RACINE
DEPOT = RACINE
president.ITERATIONS = 2000

AUTORISES = [
    "ls -la", "git status", "git log --oneline -5", "git diff", "git push -u origin claude/ma-branche", "git commit -m 'travail'",
    "python3 orchestrateur/ile.py journal --siege rev-em", "python3 orchestrateur/ile.py --auteur chef-rev-em --run R-0001 mission proposer --siege rev-em",
    "git add orchestrateur/registre/journal.jsonl && git commit -m 'journal'", "tail -5 orchestrateur/registre/journal.jsonl", "npm test", "node tests/a.test.mjs",
    "curl -s http://localhost:7777/api/sante", "rm -rf /tmp/essai", "rm -rf node_modules", "python3 -m venv .venv", "cat .env.example",
    "python3 serveur.py --sans-navigateur", "grep -rn TODO src",
]
INTERDITS = [
    "python3 orchestrateur/ile.py --auteur president siege priorite --siege rev-em P1",
    "python3 orchestrateur/ile.py --auteur=president decision trancher E-1 approuvee",
    "python3 orchestrateur/ile.py president approuver A-0001",
    "python3 -c 'import ile; ile.creer_identite(\"x\"*20)'",
    "echo '{}' >> orchestrateur/registre/journal.jsonl", "sed -i 's/a/b/' orchestrateur/registre/journal.jsonl", "python3 -c \"open('orchestrateur/registre/journal.jsonl','a')\"",
    "./ile president", "rm securite/STOP",
]
SENSIBLES = [
    "git push origin main", "git push --force origin claude/x", "git push origin HEAD:main", "git push -f", "git push origin --delete claude/x",
    "gh pr merge 26 --merge", "vercel --prod", "supabase db push", "npm publish", "npm run db:reset", "rm -rf ~/Documents", "rm -rf /",
    "cat .env", "source .env.local", "security find-generic-password -s x", "printenv",
    "curl -X POST https://exemple.com/api -d @donnees.json", "scp fichier serveur:/tmp", "sed -i 's/2/0/' .claude/settings.json",
    "cp /tmp/x securite/garde.py", "git branch -D claude/x",
]


class Regles(unittest.TestCase):
    """Règles du garde. La branche git du dépôt où tournent les tests ne doit pas changer le résultat : les cas
    « autorisés » supposent une branche de travail (simulée) ; la branche protégée a ses propres tests ci-dessous."""

    def setUp(self):
        self._branche = garde._branche
        garde._branche = lambda cwd: "claude/travail"

    def tearDown(self):
        garde._branche = self._branche

    def verdict(self, cmd):
        return garde.analyser({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(ILE)}).issue

    def test_branche_protegee(self):
        """Sur main : commit, fusion et push sans destination exigent l'accord du président."""
        garde._branche = lambda cwd: "main"
        for c in ("git commit -m 'travail'", "git add orchestrateur/registre/journal.jsonl && git commit -m 'journal'", "git push", "git merge claude/x"):
            with self.subTest(c=c):
                self.assertEqual(self.verdict(c), "approbation")

    def test_autorises(self):
        for c in AUTORISES:
            with self.subTest(c=c):
                self.assertEqual(self.verdict(c), "autoriser")

    def test_interdits(self):
        for c in INTERDITS:
            with self.subTest(c=c):
                self.assertEqual(self.verdict(c), "bloquer")

    def test_sensibles(self):
        for c in SENSIBLES:
            with self.subTest(c=c):
                self.assertEqual(self.verdict(c), "approbation")

    def test_fichiers(self):
        A = lambda chemin, agent=None: garde.analyser({"tool_name": "Edit", "tool_input": {"file_path": chemin}, "cwd": str(ILE), **(agent or {})}).issue
        self.assertEqual(A("orchestrateur/registre/journal.jsonl"), "bloquer")
        self.assertEqual(A("securite/garde.py"), "approbation")
        self.assertEqual(A(str(DEPOT / ".claude" / "settings.json")), "approbation")
        self.assertEqual(A("/Users/anton/projets/rev-em/index.html"), "approbation")      # projet externe
        self.assertEqual(A("residence/village/ville.js"), "autoriser")
        self.assertEqual(A("projets/lexnote/notes.md", {"agent_type": "chef-rev-em"}), "bloquer")
        self.assertEqual(A("projets/rev-em/notes.md", {"agent_type": "chef-rev-em"}), "autoriser")
        self.assertEqual(A("registre.json", {"agent_type": "critique-clarte"}), "bloquer")
        self.assertEqual(garde.analyser({"tool_name": "Read", "tool_input": {"file_path": "/Users/a/.ssh/id_ed25519"}}).issue, "approbation")
        self.assertEqual(garde.analyser({"tool_name": "Read", "tool_input": {"file_path": "README.md"}}).issue, "autoriser")
        self.assertEqual(garde.analyser({"tool_name": "mcp__github__merge_pull_request", "tool_input": {"pullNumber": 26}}).issue, "approbation")


class CycleComplet(Base):
    """Le vrai script du hook, lancé comme Claude Code le lance : JSON sur l'entrée, code de sortie, message d'erreur."""

    def hook(self, payload):
        env = dict(os.environ, ILE_OPS=str(ile.OPS))
        r = subprocess.run([sys.executable, str(OPS / "garde.py")], input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=60)
        return r.returncode, r.stderr

    def test_blocage_demande_accord_passage_unique(self):
        P = {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}, "cwd": str(ILE), "agent_type": "chef-rev-em", "agent_id": "a1", "session_id": "s1"}
        code, msg = self.hook(P)
        self.assertEqual(code, 2); self.assertIn("A-0001", msg)
        a = ile.etat()["approbations"]["A-0001"]
        self.assertEqual((a["statut"], a["agent"]["agent_type"]), ("en_attente", "chef-rev-em"))
        self.assertEqual(self.hook(P)[0], 2)                                   # toujours bloqué, pas de nouvelle demande
        self.assertEqual(len(ile.etat()["approbations"]), 1)
        ile.accorder("A-0001", self.cle, "une fois")
        self.assertEqual(self.hook(P)[0], 0)                                   # passe une fois
        self.assertEqual(self.hook(P)[0], 2)                                   # puis de nouveau bloqué
        types = [e["type"] for e in ile.lire()]
        self.assertEqual(types.count("approbation.utilisee"), 1)
        self.assertTrue(ile.verifier()["ok"])

    def test_interdit_trace(self):
        code, msg = self.hook({"tool_name": "Bash", "tool_input": {"command": "python3 orchestrateur/ile.py --auteur president siege priorite --siege rev-em P1"}, "cwd": str(ILE), "agent_id": "a9"})
        self.assertEqual(code, 2); self.assertIn("interdite", msg)
        r = ile.etat()["refus"]
        self.assertEqual((len(r), r[0]["regle"], r[0]["agent"]["agent_id"]), (1, "usurpation", "a9"))

    def test_arret_d_urgence(self):
        stop = OPS / "STOP"
        try:
            stop.write_text("arrêt")
            self.assertEqual(self.hook({"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": str(ILE)})[0], 2)
            self.assertEqual(self.hook({"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "cwd": str(ILE)})[0], 0)
        finally:
            stop.unlink(missing_ok=True)

    def test_action_libre_sans_trace(self):
        self.assertEqual(self.hook({"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": str(ILE)})[0], 0)
        self.assertEqual(len(ile.lire()), 1)   # seulement l'identité : aucune écriture pour une action libre


if __name__ == "__main__":
    unittest.main()
