#!/usr/bin/env python3
"""Tient à jour etat-de-l-ile.json (ce que fait l'île en ce moment).

Appelé par les hooks Claude Code (payload JSON sur stdin) :
    etat-ile.py debut   -> SubagentStart
    etat-ile.py fin     -> SubagentStop
    etat-ile.py repos   -> Stop (la session principale a fini de répondre)
À la main (par le Maire) :
    etat-ile.py sujet "programme BDE chiffré" [--maison bde-emergency]
    etat-ile.py simuler [maison]   -> rejoue un circuit complet (pour tester le village)

Ne fait jamais échouer un hook : toute erreur est avalée (exit 0).
"""
import os
import sys

if __name__ == "__main__":
    # Hook lancé par Claude Code (`python3 -I -S …`) : confinement des imports AVANT tout autre import, pour qu'aucun
    # module planté (dans orchestrateur/hooks/, orchestrateur/ ou ailleurs) ne remplace un module standard
    # (voir securite/confinement.py).
    _STD = os.path.dirname(os.path.realpath(os.__file__))
    sys.path[:] = [p for p in sys.path if p and (os.path.realpath(p) + os.sep).startswith(_STD + os.sep)
                   and "-packages" not in os.path.realpath(p)]
    sys.dont_write_bytecode = True

import datetime  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

# Toujours relatif au script (orchestrateur/hooks/etat-ile.py → racine de l'île), quel que soit le dossier courant.
RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ETAT = os.path.join(RACINE, "orchestrateur", "etat-de-l-ile.json")
VERROU = ETAT + ".lock"
ETAT_VIDE = {"maison": None, "sujet": None, "etape": "terminé", "agents_actifs": [], "maj": None, "historique": []}


def maintenant():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def lire():
    try:
        with open(ETAT, encoding="utf-8") as f:
            e = json.load(f)
        if isinstance(e, dict):
            return {**ETAT_VIDE, **e}
    except Exception:
        pass
    return dict(ETAT_VIDE)


def ecrire(e):
    """Écriture atomique : fichier temporaire puis renommage."""
    e["maj"] = maintenant()
    e["historique"] = e.get("historique", [])[-20:]
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ETAT), prefix=".etat-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(tmp, 0o644)  # mkstemp crée en 600 : le serveur doit pouvoir lire
    os.replace(tmp, ETAT)


class verrou:
    """Verrou exclusif (les 3 critiques démarrent en même temps)."""
    def __enter__(self):
        self.f = open(VERROU, "w")
        try:
            import fcntl
            fcntl.flock(self.f, fcntl.LOCK_EX)
        except ImportError:  # Windows : pas de flock, on fait au mieux
            pass
        return self

    def __exit__(self, *a):
        self.f.close()


def maisons_par_agent():
    """chef-xxx -> id de maison, d'après registre.json."""
    try:
        with open(os.path.join(RACINE, "registre.json"), encoding="utf-8") as f:
            reg = json.load(f)
    except Exception:
        return {}
    out = {}
    for b in reg.get("batiments", []):
        if b.get("type") == "maison":
            nom = os.path.splitext(os.path.basename(b.get("agent", "")))[0]
            if nom:
                out[nom] = b["id"]
    return out


def etape_de(agent):
    """Renvoie (etape, maison) pour un nom d'agent, ou (None, None) si l'agent est hors circuit."""
    if agent.startswith("critique-"):
        return "conseil", None
    if agent == "forgeron":
        return "forge", None
    m = maisons_par_agent().get(agent)
    if m:
        return "maison", m
    return None, None


def nom_agent(payload):
    for k in ("agent_type", "subagent_type", "agent_name"):
        v = payload.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def evenement(e, texte):
    e.setdefault("historique", []).append({"quand": maintenant(), "quoi": texte})


def debut(agent):
    etape, maison = etape_de(agent)
    with verrou():
        e = lire()
        if etape is None:
            return
        if etape == "conseil" and e["etape"] in ("terminé", None):
            e["maison"], e["sujet"] = None, e.get("sujet_suivant") or None
            e.pop("sujet_suivant", None)
        e["etape"] = etape
        if maison:
            e["maison"] = maison
        if agent not in e["agents_actifs"]:
            e["agents_actifs"].append(agent)
        evenement(e, f"{agent} démarre ({etape})")
        ecrire(e)


def fin(agent):
    etape, _ = etape_de(agent)
    with verrou():
        e = lire()
        if etape is None:
            return
        if agent in e["agents_actifs"]:
            e["agents_actifs"].remove(agent)
        if etape == "forge" and not e["agents_actifs"]:
            e["etape"] = "terminé"
        evenement(e, f"{agent} termine")
        ecrire(e)


def repos():
    with verrou():
        e = lire()
        if e["etape"] == "terminé" or e["agents_actifs"]:
            return
        e["etape"] = "terminé"
        evenement(e, "le Maire a répondu à Anton")
        ecrire(e)


def sujet(texte, maison=None):
    with verrou():
        e = lire()
        if e["etape"] == "terminé":
            e["sujet_suivant"] = texte  # repris au prochain Conseil
        e["sujet"] = texte
        if maison:
            e["maison"] = maison
        evenement(e, f"sujet : {texte}")
        ecrire(e)


def simuler(maison="bde-emergency", pause=4.0):
    chef = next((a for a, m in maisons_par_agent().items() if m == maison), None)
    if not chef:
        sys.exit(f"maison inconnue dans registre.json : {maison}")
    sujet(f"Simulation du circuit pour {maison}")
    pas = [("debut", c) for c in ("critique-clarte", "critique-exigence", "critique-strategie")]
    pas += [("fin", c) for c in ("critique-clarte", "critique-exigence", "critique-strategie")]
    pas += [("debut", chef), ("fin", chef), ("debut", "forgeron"), ("fin", "forgeron")]
    for action, agent in pas:
        (debut if action == "debut" else fin)(agent)
        print(f"{action:5} {agent:22} -> étape {lire()['etape']}")
        time.sleep(pause if action == "debut" or agent == chef else 0.3)
    print("circuit terminé")


def registre_operations(cmd, payload):
    """Inscrit l'exécution dans le registre des opérations (journal chaîné). Ne bloque jamais."""
    try:
        # `ile` par son chemin exact, depuis la source (securite/confinement.py), jamais par le chemin d'import.
        chemin = os.path.join(os.path.realpath(RACINE), "securite", "confinement.py")
        conf = sys.modules.get("confinement")
        if conf is None:
            conf = type(sys)("confinement")
            conf.__file__ = chemin
            with open(chemin, "rb") as f:
                exec(compile(f.read(), chemin, "exec", dont_inherit=True), conf.__dict__)
            sys.modules["confinement"] = conf
        elif os.path.realpath(getattr(conf, "__file__", None) or "") != chemin:
            raise ImportError("module « confinement » inattendu : refusé")
        conf.charger("ile").capteur(cmd, payload)
    except Exception as e:
        try:
            with open(os.path.join(RACINE, "orchestrateur", "registre", "capteurs-erreurs.log"), "a", encoding="utf-8") as f:
                f.write(f"{maintenant()} {cmd} {type(e).__name__}: {e}\n")
        except Exception:
            pass


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else ""
    if cmd == "sujet" and len(args) > 1:
        m = args[args.index("--maison") + 1] if "--maison" in args else None
        return sujet(args[1], m)
    if cmd == "simuler":
        return simuler(*(args[1:2] or []))
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    if cmd in ("debut", "fin"):
        (debut if cmd == "debut" else fin)(nom_agent(payload))
        registre_operations(cmd, payload)
    elif cmd == "repos":
        repos()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("sujet", "simuler"):
        main()
    else:
        try:
            main()
        except Exception:
            pass
        sys.exit(0)
