#!/usr/bin/env python3
"""Serveur de l'Île des Agents : métropole 3D, Résidence présidentielle, API du registre.

    ./ile                         (recommandé : démarre si besoin et ouvre le navigateur)
    python3 serveur.py            port 7777 (ou ILE_PORT), écoute sur 127.0.0.1 uniquement
    python3 serveur.py --port 7780 --sans-navigateur

Adresses : http://localhost:7777/ (métropole) · /residence · /batiment/<id> · /connexion (accès distant)

Sécurité :
  - écoute sur 127.0.0.1 seulement ; un nom d'hôte inconnu est refusé (protection contre le « DNS rebinding ») ;
  - lecture locale libre ; tout acte du président exige une session DÉVERROUILLÉE par sa phrase (la clé privée
    ne vit qu'en mémoire du serveur, le temps de la session) + jeton anti-CSRF + origine vérifiée ;
  - accès distant (ex. Tailscale) : seulement pour les noms d'hôte inscrits dans securite/acces.json, et TOUT
    y exige une connexion par la phrase présidentielle ; tentatives limitées ;
  - les fichiers internes du registre ne sont jamais servis bruts.
"""
import os
import sys

if __name__ == "__main__":
    # Le serveur garde la clé présidentielle en mémoire pendant une session déverrouillée : aucun module planté
    # (json.py à la racine, orchestrateur/hmac.py…) ne doit pouvoir s'y exécuter. Lancé en `python3 -I -S`, et même
    # sans : chemin d'import réduit à la bibliothèque standard AVANT tout autre import (securite/confinement.py).
    _STD = os.path.dirname(os.path.realpath(os.__file__))
    sys.path[:] = [p for p in sys.path if p and (os.path.realpath(p) + os.sep).startswith(_STD + os.sep)
                   and "-packages" not in os.path.realpath(p)]
    sys.dont_write_bytecode = True

import functools  # noqa: E402
import http.server  # noqa: E402
import json  # noqa: E402
import posixpath  # noqa: E402
import re  # noqa: E402
import secrets  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import urllib.request  # noqa: E402
import webbrowser  # noqa: E402
from pathlib import Path  # noqa: E402
from urllib.parse import parse_qs, quote, unquote, urlparse  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent          # racine de l'île (le serveur vit dans residence/)


def _confinement():
    """securite/confinement.py, chargé par son chemin exact (jamais par le chemin d'import)."""
    chemin = str(RACINE / "securite" / "confinement.py")
    c = sys.modules.get("confinement")
    if c is None:
        c = type(sys)("confinement")
        c.__file__ = chemin
        with open(chemin, "rb") as f:
            exec(compile(f.read(), chemin, "exec", dont_inherit=True), c.__dict__)
        sys.modules["confinement"] = c
    elif os.path.realpath(getattr(c, "__file__", None) or "") != chemin:
        raise ImportError(f"module « confinement » inattendu ({getattr(c, '__file__', None)!r}) : refusé")
    return c


ile = _confinement().charger("ile")

PORT_DEFAUT = int(os.environ.get("ILE_PORT", "7777"))
SIGNATURE_SERVEUR = "Île des Agents"
JETON = secrets.token_urlsafe(24)                     # anti-CSRF, change à chaque démarrage
# Jamais servis bruts : le registre (sauf l'instantané etat.json), la sécurité, la présidence, le code Python, les fichiers cachés.
INTERDITS = re.compile(r"^/(orchestrateur/registre/(?!etat\.json$)|securite/|presidence/|orchestrateur/(?!registre/etat\.json$|etat-de-l-ile\.json$)|audit/(?!rapports/|conseil/)|tests/|\.|.*/\.|.*\.py$|.*\.log$|.*\.pid$|ile$)")
# La métropole et les pages de la Résidence vivent dans residence/village/ ; l'adresse publique reste /village/.
ALIAS_VILLAGE = "/village/"
SESSION_DUREE_S, SESSION_INACTIVITE_S = 12 * 3600, 2 * 3600
TENTATIVES_MAX, TENTATIVES_FENETRE_S = 5, 600
LIBRES_DISTANT = {"/connexion", "/village/connexion.html", "/residence/village/connexion.html", "/api/sante", "/api/president/deverrouiller", "/api/session", "/favicon.ico"}
_sessions, _echecs, _verrou = {}, [], threading.Lock()


def acces() -> dict:
    """Noms d'hôte distants autorisés (géré par « ./ile distant activer »). Absent = aucun accès distant."""
    try:
        d = json.loads((RACINE / "securite" / "acces.json").read_text(encoding="utf-8"))
        return {"hotes_distants": [h.lower().rstrip(".") for h in d.get("hotes_distants", [])], "tailscale_login": d.get("tailscale_login")}
    except (OSError, ValueError):
        return {"hotes_distants": [], "tailscale_login": None}


def _chemin_normalise(path: str) -> str:
    return "/" + posixpath.normpath(unquote(path)).lstrip("/").lower()


def _premieres_lignes(p: Path, n=4):
    try:
        return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")][:n]
    except OSError:
        return None


def organisation():
    """Directions de l'entreprise (registre.json) ; « actif » seulement si chaque agent nommé existe vraiment."""
    agents = {p.stem for p in (RACINE / ".claude" / "agents").glob("*.md")}
    out = []
    for d in ile.registre().get("organisation", []):
        presents = [a for a in d.get("agents", []) if a in agents or a.startswith("(")]
        out.append({**d, "agents_presents": presents, "statut_reel": "actif" if d.get("agents") and len(presents) == len(d["agents"]) else "prévu"})
    return out


def protections():
    settings = {}
    for f in (RACINE / ".claude" / "settings.json",):
        try:
            settings[str(f.relative_to(RACINE))] = "garde.py" in f.read_text(encoding="utf-8")
        except OSError:
            settings[str(f.relative_to(RACINE))] = False
    return {"garde_branche": settings, "arret_urgence": (RACINE / "securite" / "STOP").exists() or (Path(os.environ.get("ILE_OPS") or (RACINE / "securite")) / "STOP").exists(), "acces_distant": acces()["hotes_distants"]}


def residence(session=None):
    p = ile.etat()
    v = ile.verifier()
    titres_pb = {k: x["titre"] for k, x in p["problemes"].items()}
    titres_m = {k: m["titre"] for k, m in p["missions"].items()}
    sieges = []
    for b in ile.registre().get("batiments", []):
        if b.get("type") != "maison":
            continue
        sid, s = b["id"], p["sieges"].get(b["id"], {})
        edl = RACINE / b.get("dossier", "") / "etat-des-lieux.md"
        ms = [m for m in p["missions"].values() if m["siege"] == sid]
        sieges.append({
            "id": sid, "nom": b["nom"], "couleur": b.get("couleur"), "role": b.get("role"), "depot": b.get("depot") or None,
            "priorite": s.get("priorite"), "priorite_motif": s.get("priorite_motif"), "etat": s.get("etat"),
            "etat_des_lieux": {"chemin": str(edl.relative_to(RACINE)), "extrait": _premieres_lignes(edl)} if edl.exists() else None,
            "prochaines_actions": sorted([m for m in ms if m["statut"] in ("proposee", "attente_president", "planifiee", "reportee")], key=lambda m: (m["rang"] or 999, m["id"])),
            "missions_en_cours": [m for m in ms if m["statut"] in ("en_cours", "verification", "bloquee")],
            "problemes": [x for x in p["problemes"].values() if x["siege"] == sid and x["ouvert"]],
            "decisions": [d for d in p["decisions"].values() if d["siege"] == sid and d["verdict"] is None],
            "agents_actifs": [r for r in p["runs_actifs"] if r["siege"] == sid],
            "tests": [t for t in p["tests"] if t["siege"] == sid][-3:],
            "derniere_activite": s.get("derniere_activite"),
        })
    ordre = {"P1": 0, "P2": 1, "P3": 2, None: 3}
    sieges.sort(key=lambda x: (ordre.get(x["priorite"], 3), -len(x["decisions"]) - len([q for q in x["problemes"] if q["gravite"] == "bloquant"]), x["nom"]))
    rapports = [{**r, "problemes": [{"id": i, "titre": titres_pb.get(i)} for i in r["problemes"]], "missions": [{"id": i, "titre": titres_m.get(i)} for i in r["missions"]]}
                for r in sorted(p["rapports"], key=lambda r: r["debut"], reverse=True)]
    historique = sorted([{"type": "decision", **d} for d in p["decisions"].values() if d["verdict"]] +
                        [{"type": "approbation", **a, "titre": a["raison"], "tranchee": a["verdict"]["quand"]} for a in p["approbations"].values() if a["verdict"]],
                        key=lambda x: x.get("tranchee") or "", reverse=True)
    ident = p["identite"]
    return {
        "maj": p["maj"], "integrite": {"ok": v["ok"], "evenements": v["n"], "dernier_hash": v["dernier"], "erreurs": v["erreurs"][:5]},
        "president": {"identite": {"empreinte": ident["empreinte"], "quand": ident["quand"]} if ident else None,
                      "deverrouille": bool(session), "expire": session and time.strftime("%H:%M", time.localtime(min(session["cree"] + SESSION_DUREE_S, session["vu"] + SESSION_INACTIVITE_S)))},
        "sieges": sieges,
        "approbations": sorted([a for a in p["approbations"].values() if a["statut"] == "en_attente"], key=lambda a: a["quand"]),
        "decisions": sorted([d for d in p["decisions"].values() if d["verdict"] is None], key=lambda d: d["quand"]),
        "historique": historique[:60],
        "instructions": sorted(p["instructions"].values(), key=lambda i: i["quand"], reverse=True),
        "missions": sorted(p["missions"].values(), key=lambda m: (m["rang"] or 999, m["id"])),
        "rapports": rapports, "tests": list(reversed(p["tests"]))[:40],
        "agents_actifs": p["runs_actifs"], "agents_expires": p["runs_expires"],
        "runs": sorted(p["runs"].values(), key=lambda r: r["debut"], reverse=True)[:30],
        "securite": {"refus": list(reversed(p["refus"]))[:30], "rejets": p["rejets"][-30:], **protections()},
        "organisation": organisation(),
        "innovation": {"statut": "prévu — étape 6 de la roadmap", "dossier": "projets/innovation/"},
    }


class Gestionnaire(http.server.SimpleHTTPRequestHandler):
    server_version = "IleDesAgents"

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass

    # ---------------------------------------------------------------- utilitaires
    def _json(self, code, obj, cookie=None):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(b)

    def _rediriger(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _hote(self):
        """local, distant (autorisé dans acces.json) ou None (refusé)."""
        h = (self.headers.get("Host") or "").lower()
        nom = h[1:h.index("]")] if h.startswith("[") else h.rsplit(":", 1)[0] if ":" in h else h
        if nom in ("localhost", "127.0.0.1", "::1", ""):
            return "local"
        if nom.rstrip(".") in acces()["hotes_distants"]:
            if acces()["tailscale_login"] and self.headers.get("Tailscale-User-Login") != acces()["tailscale_login"]:
                return None
            return "distant"
        return None

    def _origine_ok(self, hote):
        o = self.headers.get("Origin")
        if o is None:
            return True
        port = self.server.server_address[1]
        if o in (f"http://localhost:{port}", f"http://127.0.0.1:{port}"):
            return True
        return hote == "distant" and urlparse(o).hostname in acces()["hotes_distants"] and o.startswith("https://")

    def _session(self):
        c = self.headers.get("Cookie") or ""
        m = re.search(r"(?:^|;\s*)ile_session=([A-Za-z0-9_\-]+)", c)
        if not m:
            return None
        with _verrou:
            s = _sessions.get(m.group(1))
            now = time.time()
            if not s or now - s["cree"] > SESSION_DUREE_S or now - s["vu"] > SESSION_INACTIVITE_S:
                _sessions.pop(m.group(1), None)
                return None
            s["vu"] = now
            return s

    def _lire_json(self):
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            raise ValueError("JSON attendu")
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > 16384:
            raise ValueError("taille de requête invalide")
        d = json.loads(self.rfile.read(n) or b"{}")
        if not isinstance(d, dict):
            raise ValueError("objet JSON attendu")
        return d

    # ---------------------------------------------------------------- GET
    def do_GET(self):
        u = urlparse(self.path)
        hote = self._hote()
        if hote is None:
            return self._json(403, {"erreur": "hôte refusé"})
        chemin = u.path.rstrip("/") or "/"
        session = self._session()
        if hote == "distant" and not session and chemin not in LIBRES_DISTANT:
            if chemin.startswith("/api/"):
                return self._json(401, {"erreur": "connexion présidentielle requise"})
            return self._rediriger("/connexion?suite=" + quote(self.path, safe=""))
        # adresses courtes
        if chemin == "/":
            return self._rediriger("/village/")
        if chemin in ("/residence", "/ville", "/connexion"):
            return self._rediriger({"/residence": "/village/residence.html", "/ville": "/village/", "/connexion": "/village/connexion.html" + ("?" + u.query if u.query else "")}[chemin])
        m = re.match(r"^/batiment/([a-z0-9-]+)$", chemin)
        if m:
            return self._rediriger("/village/?ouvrir=" + m.group(1))
        if INTERDITS.match(_chemin_normalise(u.path)):
            return self._json(404, {"erreur": "introuvable"})
        try:
            if chemin == "/api/sante":
                return self._json(200, {"ile": SIGNATURE_SERVEUR, "port": self.server.server_address[1], "journal": ile.JOURNAL.exists()})
            if chemin == "/api/etat":
                return self._json(200, ile.etat_3d(ile.etat()))
            if chemin == "/api/residence":
                return self._json(200, residence(session))
            if chemin == "/api/president":
                i = ile.identite_courante()
                return self._json(200, {"identite": {"empreinte": i["empreinte"], "quand": i["quand"]} if i else None, "deverrouille": bool(session)})
            if chemin == "/api/verifier":
                return self._json(200, ile.verifier())
            if chemin == "/api/session":
                if self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
                    return self._json(403, {"erreur": "origine refusée"})
                return self._json(200, {"jeton": JETON})
            if chemin == "/api/journal":
                q = parse_qs(u.query)
                evs = ile.lire()
                if q.get("siege"):
                    evs = [e for e in evs if e["donnees"].get("siege") == q["siege"][0]]
                if q.get("type"):
                    evs = [e for e in evs if e["type"].startswith(q["type"][0])]
                try:
                    n = max(1, min(int(q.get("n", ["200"])[0]), 2000))
                except ValueError:
                    return self._json(400, {"erreur": "n doit être un entier"})
                return self._json(200, {"evenements": evs[-n:][::-1], "total": len(evs)})
        except ile.ErreurIle as e:
            return self._json(500, {"erreur": str(e)})
        if chemin.startswith("/api/"):
            return self._json(404, {"erreur": "introuvable"})
        if u.path.startswith(ALIAS_VILLAGE):                       # /village/… → residence/village/…
            self.path = "/residence" + self.path
        return super().do_GET()

    # ---------------------------------------------------------------- POST
    def do_POST(self):
        u = urlparse(self.path)
        hote = self._hote()
        if hote is None:
            return self._json(403, {"erreur": "hôte refusé"})
        if not self._origine_ok(hote):
            return self._json(403, {"erreur": "origine refusée"})
        if not secrets.compare_digest(self.headers.get("X-Ile-Jeton", ""), JETON):
            return self._json(403, {"erreur": "jeton absent ou invalide (recharge la page)"})
        try:
            d = self._lire_json()
        except ValueError as e:
            return self._json(400, {"erreur": str(e)})
        if u.path == "/api/president/deverrouiller":
            return self._deverrouiller(d, hote)
        session = self._session()
        if u.path == "/api/president/verrouiller":
            if session:
                with _verrou:
                    for k in [k for k, v in _sessions.items() if v is session]:
                        _sessions.pop(k)
            return self._json(200, {"ok": True}, cookie="ile_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict")
        if not session:
            return self._json(401, {"erreur": "Résidence verrouillée : déverrouille-la avec ta phrase présidentielle"})
        cle, canal = session["cle"], "Résidence (distante)" if hote == "distant" else "Résidence"
        txt = lambda k, n: ((d.get(k) or "")[:n] or None)
        try:
            if u.path == "/api/instruction":
                ev = ile.donner_instruction(d.get("texte"), cle, d.get("siege") or None, canal=canal)
            elif u.path == "/api/decision":
                ev = ile.trancher(d.get("id"), d.get("verdict"), cle, txt("motif", 2000), canal=canal)
            elif u.path == "/api/priorite":
                ev = ile.fixer_priorite(d.get("siege"), d.get("priorite"), cle, txt("motif", 500), canal=canal)
            elif u.path == "/api/mission":
                if d.get("vers") not in ("planifiee", "rejetee", "attente_president", "reportee", "proposee"):
                    return self._json(400, {"erreur": "le président peut retenir, rejeter, reporter ou remettre en proposition une mission"})
                ev = ile.changer_statut(d.get("id"), d.get("vers"), {"canal": canal}, txt("motif", 1000), cle=cle)
            elif u.path == "/api/approbation":
                if d.get("verdict") == "accordee":
                    ev = ile.accorder(d.get("id"), cle, txt("motif", 1000), d.get("heures") or ile.DUREE_APPROBATION_H, canal=canal)
                elif d.get("verdict") == "refusee":
                    ev = ile.refuser(d.get("id"), cle, txt("motif", 1000), canal=canal)
                else:
                    return self._json(400, {"erreur": "verdict : accordee ou refusee"})
            else:
                return self._json(404, {"erreur": "introuvable"})
        except (ile.ErreurIle, ValueError, TypeError) as e:
            return self._json(400, {"erreur": str(e)})
        return self._json(200, {"ok": True, "evenement": ev["id"], "hash": ev["hash"]})

    def _deverrouiller(self, d, hote):
        now = time.time()
        with _verrou:
            _echecs[:] = [t for t in _echecs if now - t < TENTATIVES_FENETRE_S]
            if len(_echecs) >= TENTATIVES_MAX:
                attente = int(TENTATIVES_FENETRE_S - (now - _echecs[0]))
                return self._json(429, {"erreur": f"trop de tentatives : réessaie dans {attente // 60 + 1} min"})
        try:
            cle = ile.deverrouiller(d.get("phrase") or "")
        except ile.ErreurIle as e:
            with _verrou:
                _echecs.append(time.time())
            return self._json(403, {"erreur": str(e)})
        sid = secrets.token_urlsafe(32)
        with _verrou:
            _sessions[sid] = {"cle": cle, "cree": now, "vu": now, "distant": hote == "distant"}
        cookie = f"ile_session={sid}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_DUREE_S}" + ("; Secure" if hote == "distant" else "")
        return self._json(200, {"ok": True, "empreinte": cle.empreinte}, cookie=cookie)


def deja_lance(port) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/sante", timeout=1.5) as r:
            return json.loads(r.read()).get("ile") == SIGNATURE_SERVEUR
    except Exception:
        return False


def instantane(dossier: Path) -> dict:
    """Écrit la version publiée (lecture seule) des données de la Résidence : les MÊMES projections que les routes
    /api/… du serveur, calculées par le même code, figées dans des fichiers JSON que la version web (GitHub Pages) lit.
    Rien de secret : le journal est déjà dans le dépôt ; seuls les noms d'hôte de l'accès distant (non versionnés)
    sont retirés. Aucune session n'est ouverte : la version publiée ne peut ni signer ni agir."""
    dossier.mkdir(parents=True, exist_ok=True)
    evs = ile.lire()
    v = ile.verifier(evs)
    res = residence(None)
    res["securite"]["acces_distant_masques"] = len(res["securite"].get("acces_distant") or [])   # noms d'hôte non publiés
    res["securite"]["acces_distant"] = []
    i = ile.identite_courante()
    fichiers = {
        "residence.json": res,
        "etat.json": ile.etat_3d(ile.etat()),
        "journal.json": {"evenements": evs[::-1], "total": len(evs)},
        "verifier.json": v,
        "president.json": {"identite": {"empreinte": i["empreinte"], "quand": i["quand"]} if i else None, "deverrouille": False},
        "meta.json": {
            "version": 1, "genere": ile.maintenant(), "evenements": v["n"], "dernier_hash": v["dernier"], "integre": v["ok"],
            "journal": "orchestrateur/registre/journal.jsonl",
            # règles du registre, exportées par le code Python lui-même pour la vérification dans le navigateur
            "types_presidentiels": sorted(ile.TYPES_PRESIDENTIELS), "reserve_president": sorted(map(list, ile.RESERVE_PRESIDENT)),
            "anciens_chemins": [list(x) for x in ile.ANCIENS_CHEMINS],
        },
    }
    for nom, contenu in fichiers.items():
        (dossier / nom).write_text(json.dumps(contenu, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return fichiers["meta.json"]


def main():
    args = sys.argv[1:]
    if "--instantane" in args:                                   # ./ile publier
        i = args.index("--instantane")
        cible = Path(args[i + 1]) if i + 1 < len(args) else RACINE / "residence" / "instantane"
        m = instantane(cible)
        print(f"Instantané publié dans {cible} : {m['evenements']} événements, journal {'intègre' if m['integre'] else 'ALTÉRÉ'}, dernière empreinte {m['dernier_hash'][:16]}…")
        return 0 if m["integre"] else 1
    port = PORT_DEFAUT
    if "--port" in args:
        port = int(args[args.index("--port") + 1])
    elif args and args[0].isdigit():
        port = int(args[0])
    base = f"http://localhost:{port}"
    try:
        serveur = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Gestionnaire, directory=str(RACINE)))
    except OSError:
        if deja_lance(port):
            print(f"L'île est déjà ouverte : {base}/")
            if "--sans-navigateur" not in args:
                webbrowser.open(base + "/")
            return 0
        print(f"Le port {port} est occupé par un autre programme. Choisis-en un autre : python3 serveur.py --port 7780", file=sys.stderr)
        return 1
    serveur.daemon_threads = True
    if ile.JOURNAL.exists():
        try:
            ile._ecrire_etat(ile.etat())
        except Exception as e:
            print(f"Avertissement : projection non recalculée ({e})", file=sys.stderr)
    print(f"Île des Agents ouverte : {base}/   ·   Résidence : {base}/residence   (Ctrl+C pour arrêter)", flush=True)
    if "--sans-navigateur" not in args:
        threading.Timer(0.6, lambda: webbrowser.open(base + "/")).start()
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nServeur arrêté.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
