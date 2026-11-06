#!/usr/bin/env python3
"""Registre des opérations de l'Entreprise des Agents.

Source de vérité unique : orchestrateur/registre/journal.jsonl, un événement par ligne, AJOUT SEUL,
chaîné par empreintes (chaque ligne contient le SHA-256 de la précédente). Toute ligne
modifiée, supprimée ou insérée est détectée par `ile.py verifier`.

Tout le reste (état des sièges, missions, décisions, état 3D) est une PROJECTION recalculée
à partir du journal ; rien n'est stocké ailleurs. Python standard, aucune dépendance.

Usage rapide :
  python3 orchestrateur/ile.py etat
  python3 orchestrateur/ile.py instruction donner "Priorité à LexNote cette semaine"
  python3 orchestrateur/ile.py mission proposer --siege rev-em --titre "…" --objectif "…" --critere "…" \
          --valeur 4 --urgence 3 --effort 2 --risque 2 --auteur chef-rev-em --run R-0003
  python3 orchestrateur/ile.py classer
  python3 orchestrateur/ile.py verifier
"""
# Pas de « from __future__ » : ce serait un import exécuté avant le confinement ci-dessous.
import os
import sys

if __name__ == "__main__":
    # Commande lancée directement (hooks, président, lanceur) : confinement des imports AVANT tout autre import
    # (voir securite/confinement.py). `sys` est intégré ; `os` est préchargé, ou introuvable hors de la bibliothèque
    # standard en `-I -S` (limite : `-S` sans `-I` sous Python 3.9, voir garde.py).
    _STD = os.path.dirname(os.path.realpath(os.__file__))
    sys.path[:] = [p for p in sys.path if p and (os.path.realpath(p) + os.sep).startswith(_STD + os.sep)
                   and "-packages" not in os.path.realpath(p)]
    _CONF = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "securite", "confinement.py")
    _c = type(sys)("confinement")
    _c.__file__ = _CONF
    with open(_CONF, "rb") as _f:
        exec(compile(_f.read(), _CONF, "exec", dont_inherit=True), _c.__dict__)
    sys.modules["confinement"] = _c
    _c.confiner()

import argparse  # noqa: E402
import datetime as dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Optional  # noqa: E402

# Processus confiné (garde, serveur, hooks, commande directe) : `president` est chargé par son chemin exact, depuis
# la source. Import ordinaire seulement hors confinement (tests unitaires, outils de développement).
_CONFINEMENT = sys.modules.get("confinement")
if _CONFINEMENT is not None:
    president = _CONFINEMENT.charger("president")
else:
    import president  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent                      # racine de l'île
OPS = Path(os.environ.get("ILE_OPS") or (RACINE / "orchestrateur" / "registre"))   # données du registre ; surchargeable pour les tests
# Migration vers ile-entrepreneuriale : les événements déjà écrits citent les ANCIENS chemins (le journal ne se réécrit
# pas). Correspondance ancien → nouveau, utilisée pour retrouver les artefacts gelés (voir audit/migration/).
ANCIENS_CHEMINS = [("architecture/", "docs/architecture/"), ("conseil/", "audit/conseil/"), ("forge/rapports/", "audit/rapports/"),
                   ("maisons/", "projets/"), ("innovation/", "projets/innovation/"), ("operations/tests/", "tests/")]


def emplacements_artefact(chemin: str) -> list:
    """Tous les emplacements où un artefact inscrit au journal peut se trouver : son chemin d'origine et, s'il date
    d'avant la migration, son équivalent dans la nouvelle arborescence."""
    lieux = [RACINE / chemin]
    for ancien, nouveau in ANCIENS_CHEMINS:
        if chemin.startswith(ancien):
            lieux.append(RACINE / (nouveau + chemin[len(ancien):]))
    return lieux


def chemin_artefact(chemin: str) -> Path:
    """Emplacement actuel d'un artefact (le nouveau chemin d'abord, puis le chemin d'origine)."""
    lieux = emplacements_artefact(chemin)
    return next((p for p in reversed(lieux) if p.exists()), lieux[0])
JOURNAL = OPS / "journal.jsonl"
ETAT = OPS / "etat.json"
VERROU = OPS / ".verrou"
COURANTE = OPS / ".mission-courante"
GENESE = "0" * 64
RUN_ACTIF_MAX_S = 2 * 3600          # au-delà, une exécution sans fin est « expirée », pas active

# ---------------------------------------------------------------- vocabulaire
STATUTS = {
    "proposee":          {"planifiee", "attente_president", "rejetee", "reportee"},
    "reportee":          {"proposee", "rejetee"},
    "attente_president": {"planifiee", "rejetee"},
    "planifiee":         {"en_cours", "abandonnee"},
    "en_cours":          {"verification", "bloquee", "abandonnee"},
    "bloquee":           {"en_cours", "abandonnee"},
    "verification":      {"terminee", "en_cours"},
    "terminee": set(), "rejetee": set(), "abandonnee": set(),
}
FINAUX = {"terminee", "rejetee", "abandonnee"}
ACTIFS = {"planifiee", "en_cours", "bloquee", "verification"}
RESERVE_PRESIDENT = {("attente_president", "planifiee"), ("attente_president", "rejetee"), ("proposee", "rejetee"),
                     ("proposee", "reportee"), ("reportee", "proposee"), ("reportee", "rejetee")}
# Actes que SEUL le président peut accomplir : ils ne comptent que s'ils portent une signature valide de sa clé.
TYPES_PRESIDENTIELS = {"president.identite", "decision.tranchee", "siege.priorite", "instruction.donnee",
                       "approbation.accordee", "approbation.refusee",
                       # propositions (orchestrateur/propositions.py) : activation des décisions officielles et décisions
                       "presidence.decisions_activees", "proposition.approuvee", "proposition.refusee",
                       "proposition.modifications_demandees", "proposition.rectifiee"}
RESULTATS_TEST = ("PASS", "FAIL", "NOT TESTED", "PARTIEL")
DUREE_APPROBATION_H = 24
GRAVITES = ("bloquant", "majeur", "mineur")
PRIORITES = {"P1": 1.0, "P2": .65, "P3": .35}
VERIF = ("signature", "hook", "run", "declare")   # du plus fort au plus faible


class ErreurIle(Exception):
    pass


# ---------------------------------------------------------------- journal
def maintenant() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _canon(ev: dict) -> str:
    return json.dumps({k: v for k, v in ev.items() if k != "hash"}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def empreinte(ev: dict) -> str:
    return hashlib.sha256(_canon(ev).encode("utf-8")).hexdigest()


def _message_signe(ev: dict) -> bytes:
    """Ce que le président signe : l'événement complet, chaînage compris, sans l'empreinte ni la signature."""
    return json.dumps({k: v for k, v in ev.items() if k not in ("hash", "signature")}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


_SIG_OK: dict = {}   # cache (empreinte d'événement, clé) -> bool, en mémoire seulement


def signature_valide(ev: dict, publique: Optional[str]) -> bool:
    if not publique or not ev.get("signature"):
        return False
    k = (ev.get("hash"), publique, ev.get("signature"))
    if k not in _SIG_OK:
        _SIG_OK[k] = president.verifier(publique, _message_signe(ev), ev["signature"])
    return _SIG_OK[k]


class _Verrou:
    def __enter__(self):
        OPS.mkdir(parents=True, exist_ok=True)
        self.f = open(VERROU, "a+")
        try:
            import fcntl
            fcntl.flock(self.f, fcntl.LOCK_EX)
        except ImportError:   # Windows : pas de flock
            pass
        return self

    def __exit__(self, *a):
        self.f.close()


def lire() -> list[dict]:
    if not JOURNAL.exists():
        return []
    out = []
    with open(JOURNAL, encoding="utf-8") as f:
        for i, ligne in enumerate(f, 1):
            ligne = ligne.strip()
            if ligne:
                try:
                    out.append(json.loads(ligne))
                except json.JSONDecodeError as e:
                    raise ErreurIle(f"ligne {i} illisible : {e}")
    return out


def ajouter(type_: str, donnees: dict, auteur: dict, completer=None, cle=None) -> dict:
    """Ajoute un événement chaîné (sous verrou) puis recalcule les projections.
    `completer(evs)` (facultatif) renvoie les champs à calculer SOUS le verrou (identifiants R-…, M-…) :
    deux écrivains parallèles ne peuvent alors pas obtenir le même numéro."""
    with _Verrou():
        evs = lire()
        if completer:
            donnees = {**donnees, **completer(evs)}
        prec = evs[-1]["hash"] if evs else GENESE
        n = len(evs) + 1
        if cle is not None:
            auteur = {"role": "president", "verifie": "signature", "cle": cle.empreinte, **{k: v for k, v in auteur.items() if k == "canal"}}
        ev = {"n": n, "id": f"E-{n:06d}", "quand": maintenant(), "type": type_, "auteur": auteur, "donnees": donnees, "prec": prec}
        if cle is not None:
            ev["signature"] = cle.signer(_message_signe(ev))
        ev["hash"] = empreinte(ev)
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        evs.append(ev)
        _ecrire_etat(projeter(evs))
    return ev


def verifier(evs: Optional[list] = None) -> dict:
    """Recalcule la chaîne. Renvoie {ok, n, erreurs[]} ; vérifie aussi les artefacts encore présents."""
    erreurs = []
    try:
        evs = lire() if evs is None else evs
    except ErreurIle as e:
        return {"ok": False, "n": 0, "erreurs": [str(e)]}
    prec, ident = GENESE, None
    for i, ev in enumerate(evs, 1):
        if ev.get("n") != i:
            erreurs.append(f"{ev.get('id')} : numéro {ev.get('n')} au lieu de {i} (ligne insérée ou supprimée)")
        if ev.get("prec") != prec:
            erreurs.append(f"{ev.get('id')} : chaînage rompu (la ligne précédente a été modifiée ou retirée)")
        if empreinte(ev) != ev.get("hash"):
            erreurs.append(f"{ev.get('id')} : contenu modifié après écriture")
        prec = ev.get("hash")
        motif = _rejet_presidentiel(ev, ident)
        if motif:
            erreurs.append(f"{ev.get('id')} : acte présidentiel invalide ({motif})")
        elif ev.get("type") == "president.identite":
            ident = ev["donnees"]["cle_publique"]
        if ev.get("type") == "artefact.depose":
            # Chaque emplacement existant doit porter l'empreinte déposée : une copie intacte laissée à l'ancien chemin
            # ne masque pas une version modifiée au nouveau (et inversement). Aucun emplacement : artefact introuvable.
            lieux = [p for p in emplacements_artefact(ev["donnees"].get("chemin", "")) if p.exists()]
            if not lieux:
                erreurs.append(f"{ev['id']} : l'artefact {ev['donnees']['chemin']} est introuvable")
            for p in lieux:
                if _sha_fichier(p) != ev["donnees"].get("sha256"):
                    erreurs.append(f"{ev['id']} : l'artefact {ev['donnees']['chemin']} a changé depuis son dépôt ({p.relative_to(RACINE)})")
    return {"ok": not erreurs, "n": len(evs), "erreurs": erreurs, "dernier": evs[-1]["hash"] if evs else GENESE}


def _rejet_presidentiel(ev: dict, publique: Optional[str]) -> Optional[str]:
    """None si l'événement est acceptable ; sinon la raison du rejet. Seuls les actes présidentiels sont concernés."""
    t, role = ev.get("type"), ev.get("auteur", {}).get("role")
    if t != "president.identite" and role != "president" and t not in TYPES_PRESIDENTIELS and not (t == "mission.statut" and (ev["donnees"].get("de"), ev["donnees"].get("vers")) in RESERVE_PRESIDENT):
        return None
    if t == "president.identite":
        d = ev["donnees"]
        nouvelle = d.get("cle_publique")
        if not nouvelle or not president.verifier(nouvelle, ("possession:" + nouvelle).encode(), d.get("preuve", "")):
            return "preuve de possession de la nouvelle clé absente ou fausse"
        if publique is None:
            return None if signature_valide(ev, nouvelle) else "identité initiale non signée par sa propre clé"
        return None if signature_valide(ev, publique) else "changement d'identité non signé par la clé présidentielle en vigueur"
    if publique is None:
        return "aucune identité présidentielle n'existait à ce moment"
    if role != "president":
        return "acte réservé au président, inscrit par un autre auteur"
    if not signature_valide(ev, publique):
        return "signature présidentielle absente ou falsifiée"
    return None


def _sha_fichier(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- registre (sièges)
def registre() -> dict:
    try:
        return json.loads((RACINE / "registre.json").read_text(encoding="utf-8"))
    except Exception:
        return {"batiments": []}


def sieges_connus() -> dict:
    return {b["id"]: b for b in registre().get("batiments", [])}


def siege_de_role(role: str) -> Optional[str]:
    """chef-rev-em -> rev-em, d'après le champ `agent` du registre."""
    for b in registre().get("batiments", []):
        if Path(b.get("agent", "")).stem == role and b.get("type") == "maison":
            return b["id"]
    return {"forgeron": "forge"}.get(role) or ("conseil" if role.startswith("critique-") else None)


# ---------------------------------------------------------------- projection
def _age_s(quand: str) -> float:
    try:
        return (dt.datetime.now().astimezone() - dt.datetime.fromisoformat(quand)).total_seconds()
    except Exception:
        return 1e9


def projeter(evs: list[dict]) -> dict:
    missions, instructions, decisions, problemes, runs, artefacts = {}, {}, {}, {}, {}, []
    sieges, approbations, tests, refus, rejets = {}, {}, [], [], []
    identite, identites = None, []

    def S(sid):
        return sieges.setdefault(sid, {"id": sid, "priorite": None, "priorite_motif": None, "etat": None, "derniere_activite": None})

    for ev in evs:
        t, d, q = ev["type"], ev["donnees"], ev["quand"]
        motif = _rejet_presidentiel(ev, identite["cle_publique"] if identite else None)
        if motif:
            rejets.append({"id": ev["id"], "type": t, "quand": q, "auteur": ev.get("auteur"), "motif": motif})
            continue
        sid = d.get("siege")
        if t == "president.identite":
            identite = {k: d[k] for k in ("cle_publique", "empreinte", "sel", "kdf", "algo") if k in d}
            identite.update(quand=q, evenement=ev["id"], canal=d.get("canal"))
            identites.append(identite)
            continue
        if sid:
            S(sid)["derniere_activite"] = q
        if t == "instruction.donnee":
            instructions[ev["id"]] = {"id": ev["id"], "texte": d["texte"], "siege": sid, "quand": q, "auteur": ev["auteur"], "statut": "recue", "lue": None, "reponse": None, "missions": []}
        elif t == "instruction.lue" and d["instruction"] in instructions:
            i = instructions[d["instruction"]]
            if i["statut"] == "recue":
                i["statut"], i["lue"] = "lue", {"quand": q, "session": d.get("session")}
        elif t == "instruction.traitee" and d["instruction"] in instructions:
            i = instructions[d["instruction"]]
            i.update(statut="traitee", reponse=d.get("reponse"), missions=d.get("missions", []), traitee=q)
        elif t == "mission.proposee":
            missions[d["mission"]] = {"id": d["mission"], "siege": sid, "titre": d["titre"], "objectif": d.get("objectif"), "criteres": d.get("criteres", []),
                                      "valeur": d.get("valeur"), "urgence": d.get("urgence"), "effort": d.get("effort"), "risque": d.get("risque"),
                                      "sensible": d.get("sensible", False), "sources": d.get("sources", []), "origine": d.get("origine"),
                                      "auteur": ev["auteur"], "proposee": q, "statut": "proposee", "historique": [{"quand": q, "statut": "proposee", "par": ev["auteur"].get("role")}],
                                      "score": None, "rang": None, "classement": None, "artefacts": []}
        elif t == "mission.statut" and d["mission"] in missions:
            m = missions[d["mission"]]
            m["statut"] = d["vers"]
            m["historique"].append({"quand": q, "statut": d["vers"], "par": ev["auteur"].get("role"), "motif": d.get("motif")})
        elif t == "mission.classee":
            for r in d["classement"]:
                if r["mission"] in missions:
                    missions[r["mission"]].update(score=r["score"], rang=r["rang"], classement={"detail": r["detail"], "motif": r["motif"], "quand": q, "par": ev["auteur"].get("role")})
        elif t == "probleme.signale":
            problemes[ev["id"]] = {"id": ev["id"], "siege": sid, "titre": d["titre"], "gravite": d["gravite"], "source": d.get("source"), "preuve": d.get("preuve"), "quand": q, "auteur": ev["auteur"], "ouvert": True}
        elif t == "probleme.resolu" and d["probleme"] in problemes:
            problemes[d["probleme"]].update(ouvert=False, resolution=d.get("motif"), resolu=q)
        elif t == "decision.demandee":
            decisions[ev["id"]] = {"id": ev["id"], "siege": sid, "titre": d["titre"], "question": d.get("question"), "contexte": d.get("contexte"), "source": d.get("source"),
                                   "mission": d.get("mission"), "quand": q, "auteur": ev["auteur"], "verdict": None}
        elif t == "decision.tranchee" and d["decision"] in decisions and decisions[d["decision"]]["verdict"] is None:
            decisions[d["decision"]].update(verdict=d["verdict"], motif=d.get("motif"), tranchee=q, par=ev["auteur"], evenement=ev["id"])
        elif t in ("proposition.approuvee", "proposition.refusee") and d.get("proposition") in decisions and decisions[d["proposition"]]["verdict"] is None:
            # demande de décision (ancien format) tranchée par le circuit des propositions : même verdict, même acte signé
            decisions[d["proposition"]].update(verdict="approuvee" if t.endswith("approuvee") else "refusee", motif=d.get("motif"), tranchee=q, par=ev["auteur"], evenement=ev["id"])
        elif t == "proposition.rectifiee" and d.get("proposition") in decisions and d.get("vers") in ("approuvee", "refusee"):
            decisions[d["proposition"]].update(verdict=d["vers"], motif=d.get("motif"), tranchee=q, par=ev["auteur"], evenement=ev["id"], rectifie=True)
        elif t == "approbation.demandee":
            approbations[d["approbation"]] = {"id": d["approbation"], "evenement": ev["id"], "quand": q, "auteur": ev["auteur"], "statut": "en_attente",
                                             **{k: d.get(k) for k in ("categorie", "regle", "raison", "outil", "commande", "empreinte", "cwd", "agent", "siege", "mode")},
                                             "verdict": None, "utilisations": []}
        elif t in ("approbation.accordee", "approbation.refusee") and d["approbation"] in approbations:
            a = approbations[d["approbation"]]
            if a["statut"] == "en_attente":
                a.update(statut="accordee" if t.endswith("accordee") else "refusee", verdict={"quand": q, "motif": d.get("motif"), "expire": d.get("expire"), "evenement": ev["id"], "par": ev["auteur"]})
        elif t == "approbation.utilisee" and d["approbation"] in approbations:
            a = approbations[d["approbation"]]
            if a["statut"] == "accordee":
                a["utilisations"].append({"quand": q, "agent": d.get("agent"), "evenement": ev["id"]})
                if a.get("mode") != "fenetre":
                    a["statut"] = "utilisee"
        elif t == "test.execute":
            tests.append({"id": ev["id"], "quand": q, "auteur": ev["auteur"], **{k: d.get(k) for k in ("siege", "mission", "intitule", "commande", "resultat", "resume", "details", "execute_le", "preuve")}})
        elif t == "garde.refus":
            refus.append({"id": ev["id"], "quand": q, **{k: d.get(k) for k in ("categorie", "regle", "raison", "outil", "extrait", "agent", "approbation")}})
        elif t == "siege.etat":
            S(sid)["etat"] = {"phase": d.get("phase"), "resume": d.get("resume"), "indicateurs": d.get("indicateurs", []), "source": d.get("source"), "quand": q, "par": ev["auteur"].get("role")}
        elif t == "siege.priorite":
            S(sid).update(priorite=d["priorite"], priorite_motif=d.get("motif"), priorite_quand=q)
        elif t == "run.debut":
            runs[d["run"]] = {"run": d["run"], "role": d.get("role"), "siege": sid, "mission": d.get("mission"), "agent_id": d.get("agent_id"),
                              "session_id": d.get("session_id"), "transcript": d.get("transcript"), "debut": q, "fin": None, "resultat": None, "source": ev["auteur"].get("verifie")}
        elif t == "run.fin" and d["run"] in runs:
            runs[d["run"]].update(fin=q, resultat=d.get("resultat"))
        elif t == "artefact.depose":
            artefacts.append({"id": ev["id"], "mission": d.get("mission"), "chemin": d["chemin"], "nature": d.get("nature"), "sha256": d["sha256"], "quand": q, "auteur": ev["auteur"]})
            if d.get("mission") in missions:
                missions[d["mission"]]["artefacts"].append(d["chemin"])

    for a in approbations.values():
        if a["statut"] == "accordee" and a["verdict"].get("expire") and _age_s(a["verdict"]["expire"]) > 0:
            a["statut"] = "expiree"
    rapports = []
    for r in runs.values():
        if not (r["role"] or "").startswith("chef-"):
            continue
        evr = [e for e in evs if e["auteur"].get("run") == r["run"]]
        rapports.append({"run": r["run"], "role": r["role"], "siege": r["siege"], "debut": r["debut"], "fin": r["fin"], "resultat": r["resultat"],
                         "etat": next((e["donnees"] for e in reversed(evr) if e["type"] == "siege.etat"), None),
                         "problemes": [e["id"] for e in evr if e["type"] == "probleme.signale"],
                         "missions": [e["donnees"]["mission"] for e in evr if e["type"] == "mission.proposee"],
                         "decisions": [e["id"] for e in evr if e["type"] == "decision.demandee"]})
    actifs = [r for r in runs.values() if r["fin"] is None and _age_s(r["debut"]) < RUN_ACTIF_MAX_S]
    expires = [r for r in runs.values() if r["fin"] is None and _age_s(r["debut"]) >= RUN_ACTIF_MAX_S]
    return {"version": 2, "maj": maintenant(), "evenements": len(evs), "dernier_hash": evs[-1]["hash"] if evs else GENESE,
            "sieges": sieges, "missions": missions, "instructions": instructions, "decisions": decisions, "problemes": problemes,
            "runs": runs, "runs_actifs": actifs, "runs_expires": expires, "artefacts": artefacts,
            "identite": identite, "identites": identites, "approbations": approbations, "tests": tests, "refus": refus, "rejets": rejets, "rapports": rapports}


def etat_3d(p: dict) -> dict:
    """Projection minimale pour la métropole : seulement ce qui est RÉELLEMENT en cours."""
    actifs = [{"run": r["run"], "role": r["role"], "siege": r["siege"], "mission": r["mission"], "depuis": r["debut"]} for r in p["runs_actifs"]]
    missions = [{"id": m["id"], "siege": m["siege"], "titre": m["titre"], "statut": m["statut"]} for m in p["missions"].values() if m["statut"] in ACTIFS]
    alertes = [{"siege": x["siege"], "titre": x["titre"], "gravite": x["gravite"]} for x in p["problemes"].values() if x["ouvert"] and x["gravite"] == "bloquant"]
    return {"version": 2, "maj": p["maj"], "mode": "reel", "evenements": p["evenements"], "runs_actifs": actifs,
            "sieges_actifs": sorted({a["siege"] for a in actifs if a["siege"]}), "missions_actives": missions, "alertes": alertes,
            "decisions_en_attente": sum(1 for x in p["decisions"].values() if x["verdict"] is None) + sum(1 for x in p["approbations"].values() if x["statut"] == "en_attente"),
            "approbations_en_attente": sum(1 for x in p["approbations"].values() if x["statut"] == "en_attente"),
            "instructions_non_traitees": sum(1 for x in p["instructions"].values() if x["statut"] != "traitee")}


def _ecrire_etat(p: dict):
    fd, tmp = tempfile.mkstemp(dir=OPS, prefix=".etat-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(etat_3d(p), f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o644)
    os.replace(tmp, ETAT)


def etat() -> dict:
    return projeter(lire())


# ---------------------------------------------------------------- opérations métier
def _auteur(role: str, verifie: str = "declare", **extra) -> dict:
    a = {"role": role, "verifie": verifie}
    a.update({k: v for k, v in extra.items() if v})
    return a


def auteur_cli(role: str, run: Optional[str] = None) -> dict:
    """Identité déclarée en ligne de commande, confirmée si elle correspond à une exécution ouverte."""
    if role == "president":
        raise ErreurIle("« --auteur president » n'existe plus : les actes du président sont signés (Résidence déverrouillée, ou « ile.py president … » dans un vrai terminal)")
    if run:
        r = etat()["runs"].get(run)
        if r and r["fin"] is None and r["role"] == role:
            return _auteur(role, "run", run=run, agent_id=r.get("agent_id"))
        return _auteur(role, "declare", run=run, note="exécution inconnue, close ou d'un autre rôle")
    return _auteur(role, "declare")


def _siege_valide(sid: Optional[str], obligatoire=True):
    if sid is None and not obligatoire:
        return
    if sid not in sieges_connus():
        raise ErreurIle(f"siège inconnu : {sid!r} (voir registre.json)")


def _note(x, nom):
    if x is None:
        return None
    x = int(x)
    if not 1 <= x <= 5:
        raise ErreurIle(f"{nom} doit être entre 1 et 5")
    return x


def proposer_mission(siege, titre, objectif, criteres, auteur, valeur=None, urgence=None, effort=None, risque=None, sensible=False, sources=(), origine=None):
    _siege_valide(siege)
    if not titre or not criteres:
        raise ErreurIle("une mission exige un titre et au moins un critère d'acceptation")
    def numero(evs):
        connues = {e["donnees"]["mission"] for e in evs if e["type"] == "mission.proposee"}
        n = len(connues) + 1
        mid = f"M-{dt.date.today():%Y%m%d}-{n:03d}"
        while mid in connues:
            n += 1
            mid = f"M-{dt.date.today():%Y%m%d}-{n:03d}"
        return {"mission": mid}
    return ajouter("mission.proposee", {"siege": siege, "titre": titre, "objectif": objectif, "criteres": list(criteres),
                                        "valeur": _note(valeur, "valeur"), "urgence": _note(urgence, "urgence"), "effort": _note(effort, "effort"),
                                        "risque": _note(risque, "risque"), "sensible": bool(sensible), "sources": list(sources),
                                        "origine": origine or auteur.get("role")}, auteur, completer=numero)


def _cle_requise(cle):
    if not isinstance(cle, president.ClePresident):
        raise ErreurIle("acte présidentiel : la clé du président (déverrouillée) est requise")


def changer_statut(mission, vers, auteur, motif=None, cle=None):
    m = etat()["missions"].get(mission)
    if not m:
        raise ErreurIle(f"mission inconnue : {mission}")
    de = m["statut"]
    if vers not in STATUTS.get(de, set()):
        raise ErreurIle(f"transition interdite : {de} → {vers} (permises : {', '.join(sorted(STATUTS[de])) or 'aucune'})")
    if (de, vers) in RESERVE_PRESIDENT and cle is None:
        raise ErreurIle("seul le président (signature) peut retenir, rejeter, reporter ou trancher cette mission")
    if de == "proposee" and vers == "planifiee" and m["sensible"]:
        raise ErreurIle("mission sensible : elle doit passer par « attente_president »")
    if cle is not None:
        _cle_requise(cle)
    return ajouter("mission.statut", {"mission": mission, "siege": m["siege"], "de": de, "vers": vers, "motif": motif}, auteur or {}, cle=cle)


def score_mission(m: dict, priorite: Optional[str]) -> tuple:
    """Score objectif et explicable (0–100). Les notes manquantes valent 3 et sont signalées."""
    manq = [k for k in ("valeur", "urgence", "effort", "risque") if m.get(k) is None]
    v, u, e, r = (m.get(k) if m.get(k) is not None else 3 for k in ("valeur", "urgence", "effort", "risque"))
    base = .40 * v + .30 * u + .30 * (6 - e)            # 1..5
    coef_p = PRIORITES.get(priorite or "P2", PRIORITES["P2"])
    coef_r = 1 - .08 * (r - 1)                            # risque 5 → ×0,68
    s = round(base / 5 * coef_p * coef_r * 100, 1)
    detail = {"valeur": v, "urgence": u, "effort": e, "risque": r, "priorite_siege": priorite or "P2 (non fixée)", "coef_priorite": coef_p, "coef_risque": round(coef_r, 2), "notes_manquantes": manq}
    motif = f"0,40×valeur + 0,30×urgence + 0,30×(6−effort), × priorité du siège {detail['priorite_siege']}, × (1 − 0,08×(risque−1))"
    return s, detail, motif


def classer(auteur):
    """Le directeur général classe toutes les missions proposées, tous sièges confondus."""
    p = etat()
    candidates = [m for m in p["missions"].values() if m["statut"] in ("proposee", "attente_president", "planifiee")]
    lignes = []
    for m in candidates:
        s, det, motif = score_mission(m, p["sieges"].get(m["siege"], {}).get("priorite"))
        lignes.append({"mission": m["id"], "score": s, "detail": det, "motif": motif})
    lignes.sort(key=lambda x: (-x["score"], x["mission"]))
    for i, l in enumerate(lignes, 1):
        l["rang"] = i
    if not lignes:
        raise ErreurIle("aucune mission à classer")
    return ajouter("mission.classee", {"classement": lignes}, auteur)


def signaler_probleme(siege, titre, gravite, auteur, source=None, preuve=None):
    _siege_valide(siege)
    if gravite not in GRAVITES:
        raise ErreurIle(f"gravité : {', '.join(GRAVITES)}")
    return ajouter("probleme.signale", {"siege": siege, "titre": titre, "gravite": gravite, "source": source, "preuve": preuve}, auteur)


def resoudre_probleme(pid, auteur, motif):
    x = etat()["problemes"].get(pid)
    if not x or not x["ouvert"]:
        raise ErreurIle(f"problème inconnu ou déjà résolu : {pid}")
    return ajouter("probleme.resolu", {"probleme": pid, "siege": x["siege"], "motif": motif}, auteur)


def demander_decision(siege, titre, question, auteur, contexte=None, source=None, mission=None):
    _siege_valide(siege)
    return ajouter("decision.demandee", {"siege": siege, "titre": titre, "question": question, "contexte": contexte, "source": source, "mission": mission}, auteur)


def trancher(did, verdict, cle, motif=None, canal=None):
    _cle_requise(cle)
    x = etat()["decisions"].get(did)
    if not x or x["verdict"] is not None:
        raise ErreurIle(f"décision inconnue ou déjà tranchée : {did}")
    if verdict not in ("approuvee", "refusee", "reportee"):
        raise ErreurIle("verdict : approuvee, refusee ou reportee")
    return ajouter("decision.tranchee", {"decision": did, "siege": x["siege"], "verdict": verdict, "motif": motif}, {"canal": canal} if canal else {}, cle=cle)


def donner_instruction(texte, cle, siege=None, canal=None):
    _cle_requise(cle)
    texte = (texte or "").strip()
    if not texte or len(texte) > 4000:
        raise ErreurIle("instruction vide ou trop longue (4000 caractères au plus)")
    _siege_valide(siege, obligatoire=False)
    return ajouter("instruction.donnee", {"texte": texte, "siege": siege}, {"canal": canal} if canal else {}, cle=cle)


def traiter_instruction(iid, auteur, reponse, missions=()):
    x = etat()["instructions"].get(iid)
    if not x or x["statut"] == "traitee":
        raise ErreurIle(f"instruction inconnue ou déjà traitée : {iid}")
    return ajouter("instruction.traitee", {"instruction": iid, "siege": x["siege"], "reponse": reponse, "missions": list(missions)}, auteur)


def fixer_priorite(siege, priorite, cle, motif=None, canal=None):
    _cle_requise(cle)
    _siege_valide(siege)
    if priorite not in PRIORITES:
        raise ErreurIle("priorité : P1, P2 ou P3")
    return ajouter("siege.priorite", {"siege": siege, "priorite": priorite, "motif": motif}, {"canal": canal} if canal else {}, cle=cle)


# ---------------------------------------------------------------- identité présidentielle
def identite_courante():
    return etat()["identite"]


def creer_identite(phrase: str, canal="terminal"):
    """Première identité (ou nouvelle phrase, si l'ancienne clé signe le changement — voir changer_phrase)."""
    if identite_courante():
        raise ErreurIle("une identité présidentielle existe déjà : pour changer de phrase, utilise « president changer-phrase »")
    cle, pub = president.nouvelle_identite(phrase)
    pub.update(preuve=cle.signer(("possession:" + cle.publique).encode()), canal=canal)
    ajouter("president.identite", pub, {"canal": canal}, cle=cle)
    return cle


def changer_phrase(ancienne: president.ClePresident, nouvelle_phrase: str, canal="terminal"):
    cle, pub = president.nouvelle_identite(nouvelle_phrase)
    pub.update(preuve=cle.signer(("possession:" + cle.publique).encode()), canal=canal, remplace=ancienne.empreinte)
    ajouter("president.identite", pub, {"canal": canal}, cle=ancienne)
    return cle


def deverrouiller(phrase: str) -> president.ClePresident:
    try:
        return president.deverrouiller(phrase, identite_courante())
    except president.ErreurPresident as e:
        raise ErreurIle(str(e))


# ---------------------------------------------------------------- file d'approbations
def empreinte_commande(outil: str, cible: str) -> str:
    return hashlib.sha256(f"{outil}\n{(cible or '').strip()}".encode("utf-8")).hexdigest()


def demander_approbation(categorie, regle, raison, outil, commande, auteur, cwd=None, agent=None, siege=None, mode="unique"):
    """Inscrit une demande (ou renvoie celle qui attend déjà pour la même opération exacte)."""
    emp = empreinte_commande(outil, commande)
    for a in etat()["approbations"].values():
        if a["empreinte"] == emp and a["statut"] == "en_attente":
            return a["id"], False
    numero = lambda evs: {"approbation": f"A-{sum(1 for e in evs if e['type'] == 'approbation.demandee') + 1:04d}"}
    ev = ajouter("approbation.demandee", {"categorie": categorie, "regle": regle, "raison": raison, "outil": outil, "commande": (commande or "")[:2000],
                                         "empreinte": emp, "cwd": cwd, "agent": agent, "siege": siege, "mode": mode}, auteur, completer=numero)
    return ev["donnees"]["approbation"], True


def accorder(aid, cle, motif=None, duree_h=DUREE_APPROBATION_H, canal=None):
    _cle_requise(cle)
    a = etat()["approbations"].get(aid)
    if not a or a["statut"] != "en_attente":
        raise ErreurIle(f"demande inconnue ou déjà traitée : {aid}")
    duree_h = max(.1, min(float(duree_h or DUREE_APPROBATION_H), 24 * 7))
    expire = (dt.datetime.now().astimezone() + dt.timedelta(hours=duree_h)).isoformat(timespec="seconds")
    return ajouter("approbation.accordee", {"approbation": aid, "siege": a.get("siege"), "motif": motif, "expire": expire, "empreinte": a["empreinte"]}, {"canal": canal} if canal else {}, cle=cle)


def refuser(aid, cle, motif=None, canal=None):
    _cle_requise(cle)
    a = etat()["approbations"].get(aid)
    if not a or a["statut"] != "en_attente":
        raise ErreurIle(f"demande inconnue ou déjà traitée : {aid}")
    return ajouter("approbation.refusee", {"approbation": aid, "siege": a.get("siege"), "motif": motif, "empreinte": a["empreinte"]}, {"canal": canal} if canal else {}, cle=cle)


def approbation_valide(outil, commande):
    """Approbation présidentielle signée, non expirée, non consommée, pour CETTE opération exacte."""
    emp = empreinte_commande(outil, commande)
    for a in etat()["approbations"].values():
        if a["empreinte"] == emp and a["statut"] == "accordee":
            return a
    return None


def utiliser_approbation(aid, agent, auteur):
    return ajouter("approbation.utilisee", {"approbation": aid, "agent": agent}, auteur)


def inscrire_refus(categorie, regle, raison, outil, extrait, agent, approbation=None):
    return ajouter("garde.refus", {"categorie": categorie, "regle": regle, "raison": raison, "outil": outil, "extrait": (extrait or "")[:300], "agent": agent, "approbation": approbation},
                   _auteur("garde", "hook", session_id=(agent or {}).get("session_id")))


# ---------------------------------------------------------------- tests exécutés
def enregistrer_test(siege, intitule, resultat, auteur, commande=None, resume=None, details=None, mission=None, execute_le=None, preuve=None):
    _siege_valide(siege)
    if resultat not in RESULTATS_TEST:
        raise ErreurIle(f"résultat : {', '.join(RESULTATS_TEST)}")
    return ajouter("test.execute", {"siege": siege, "mission": mission, "intitule": intitule, "commande": commande, "resultat": resultat,
                                    "resume": resume, "details": details, "execute_le": execute_le or maintenant(), "preuve": preuve}, auteur)


def etat_siege(siege, phase, resume, auteur, indicateurs=(), source=None):
    _siege_valide(siege)
    return ajouter("siege.etat", {"siege": siege, "phase": phase, "resume": resume, "indicateurs": list(indicateurs), "source": source}, auteur)


def deposer_artefact(chemin, auteur, mission=None, nature=None):
    p = (RACINE / chemin).resolve()
    if RACINE not in p.parents or not p.is_file():
        raise ErreurIle(f"artefact introuvable dans l'île : {chemin}")
    return ajouter("artefact.depose", {"chemin": str(p.relative_to(RACINE)), "sha256": _sha_fichier(p), "mission": mission, "nature": nature}, auteur)


def run_debut(role, auteur, siege=None, mission=None, agent_id=None, session_id=None, transcript=None):
    p = etat()
    siege = siege or siege_de_role(role)
    if mission is None:
        mission = _mission_courante(p, siege)
    numero = lambda evs: {"run": f"R-{len({e['donnees']['run'] for e in evs if e['type'] == 'run.debut'}) + 1:04d}"}
    return ajouter("run.debut", {"role": role, "siege": siege, "mission": mission, "agent_id": agent_id, "session_id": session_id, "transcript": transcript}, auteur, completer=numero)


def run_fin(rid, auteur, resultat=None):
    r = etat()["runs"].get(rid)
    if not r or r["fin"]:
        raise ErreurIle(f"exécution inconnue ou déjà close : {rid}")
    return ajouter("run.fin", {"run": rid, "siege": r["siege"], "resultat": resultat}, auteur)


def _mission_courante(p, siege):
    """Mission rattachée par défaut : la mission en cours du siège, sinon la mission désignée par le DG."""
    enc = [m for m in p["missions"].values() if m["statut"] == "en_cours" and m["siege"] == siege and siege]
    if enc:
        return sorted(enc, key=lambda m: m["historique"][-1]["quand"])[-1]["id"]
    try:
        mid = COURANTE.read_text().strip()
        return mid if p["missions"].get(mid, {}).get("statut") in ACTIFS else None
    except OSError:
        return None


def demarrer(mission, auteur):
    m = etat()["missions"].get(mission)
    if not m:
        raise ErreurIle(f"mission inconnue : {mission}")
    ev = changer_statut(mission, "en_cours", auteur) if m["statut"] != "en_cours" else None
    COURANTE.write_text(mission)
    return ev


# ---------------------------------------------------------------- capteurs (hooks Claude Code)
def capteur(evenement: str, payload: dict):
    """Appelé par les hooks. N'échoue jamais bruyamment : un hook ne doit pas bloquer le travail."""
    role = payload.get("agent_type") or payload.get("subagent_type") or ""
    a = _auteur("claude-code", "hook", session_id=payload.get("session_id"))
    if evenement == "debut" and role:
        return run_debut(role, a, agent_id=payload.get("agent_id"), session_id=payload.get("session_id"), transcript=payload.get("transcript_path"))
    if evenement == "fin" and role:
        p = etat()
        ouverts = [r for r in p["runs"].values() if r["fin"] is None and r["role"] == role]
        if payload.get("agent_id"):
            ouverts = [r for r in ouverts if r.get("agent_id") == payload["agent_id"]] or ouverts
        if payload.get("session_id"):
            ouverts = [r for r in ouverts if r.get("session_id") in (payload["session_id"], None)] or ouverts
        if ouverts:
            return run_fin(sorted(ouverts, key=lambda r: r["debut"])[-1]["run"], a, resultat="terminé (SubagentStop)")
    return None


def briefing_dg(session_id=None) -> str:
    """Texte injecté au démarrage d'une session (hook SessionStart) : ce que le président attend du DG."""
    p = etat()
    ins = [i for i in p["instructions"].values() if i["statut"] != "traitee"]
    dec = [d for d in p["decisions"].values() if d["verdict"] is None]
    pb = [x for x in p["problemes"].values() if x["ouvert"] and x["gravite"] == "bloquant"]
    props = sorted([m for m in p["missions"].values() if m["statut"] == "proposee"], key=lambda m: (m["rang"] or 999))
    apr = [a for a in p["approbations"].values() if a["statut"] == "en_attente"]
    if not (ins or dec or pb or props or apr):
        return ""
    L = ["# Briefing du directeur général (registre des opérations)", ""]
    if ins:
        L.append("## Instructions du président à traiter")
        for i in ins:
            L.append(f"- {i['id']} ({i['quand'][:16]}{', siège ' + i['siege'] if i['siege'] else ''}) : {i['texte']}")
        L.append("→ Traite-les puis enregistre-le : `python3 orchestrateur/ile.py instruction traiter <id> --reponse \"…\" [--mission M-…]` (depuis la racine de l'île)")
        L.append("")
    if dec:
        L.append(f"## Décisions en attente du président : {len(dec)} (ne rien faire de sensible à leur place)")
        L += [f"- {d['id']} [{d['siege']}] {d['titre']}" for d in dec]
        L.append("")
    if apr:
        L.append(f"## Opérations sensibles en attente d'approbation : {len(apr)} (le garde les bloque jusqu'à l'accord signé du président)")
        L += [f"- {a['id']} [{a['categorie']}] {(a['commande'] or '')[:100]}" for a in apr]
        L.append("")
    if pb:
        L.append("## Problèmes bloquants ouverts")
        L += [f"- {x['id']} [{x['siege']}] {x['titre']}" for x in pb]
        L.append("")
    if props:
        L.append("## Missions proposées (à classer avec `ile.py classer`, puis à planifier)")
        L += [f"- {m['id']} [{m['siege']}] {m['titre']} — score {m['score'] if m['score'] is not None else 'non classé'}" for m in props[:8]]
    for i in ins:
        if i["statut"] == "recue":
            ajouter("instruction.lue", {"instruction": i["id"], "siege": i["siege"], "session": session_id}, _auteur("claude-code", "hook", session_id=session_id))
    return "\n".join(L)


# ---------------------------------------------------------------- ligne de commande
def _resume(ev) -> str:
    d, t = ev["donnees"], ev["type"]
    return {
        "instruction.donnee": lambda: d["texte"][:90],
        "mission.proposee": lambda: f"{d['mission']} {d['titre'][:70]}",
        "mission.statut": lambda: f"{d['mission']} {d['de']} → {d['vers']}",
        "mission.classee": lambda: f"{len(d['classement'])} missions classées",
        "mission.attribuee": lambda: f"{d['mission']} → {d['agent']}" + (f" (échéance {d['echeance']})" if d.get("echeance") else ""),
        "mission.livrable": lambda: f"{d['mission']} : {d['chemin']}",
        "mission.validee": lambda: f"{d['mission']} validée par {d.get('par')}",
        "mission.correction": lambda: f"{d['mission']} : correction — {d.get('motif', '')[:60]}",
        "mission.remontee": lambda: f"{d['mission']} : {d.get('de')} → {d.get('vers')}",
        "message.envoye": lambda: f"{d.get('de')} → {d.get('a')} : {d.get('sujet', '')[:60]}",
        "reunion.ouverte": lambda: f"{d['id']} : {d.get('objet', '')[:60]}",
        "reunion.close": lambda: f"{d['id']} close",
        "org.departement.cree": lambda: f"{d['entreprise']} / {d['id']}",
        "org.poste.cree": lambda: f"{d['entreprise']} / {d['id']} ({d['fonction']})",
        "org.agent.cree": lambda: f"{d['id']} → {d.get('poste')}",
        "org.agent.affecte": lambda: f"{d['agent']} → {d.get('poste')}",
        "org.agent.suspendu": lambda: f"{d['agent']} suspendu",
        "org.agent.reactive": lambda: f"{d['agent']} réactivé",
        "decision.demandee": lambda: d["titre"][:90], "decision.tranchee": lambda: f"{d['decision']} → {d['verdict']}",
        "probleme.signale": lambda: f"[{d['gravite']}] {d['titre'][:80]}", "run.debut": lambda: f"{d['run']} {d['role']} → {d.get('siege') or '—'}",
        "run.fin": lambda: f"{d['run']} {d.get('resultat') or ''}"[:90],
        "approbation.demandee": lambda: f"{d['approbation']} [{d['categorie']}] {(d.get('commande') or '')[:70]}",
        "approbation.accordee": lambda: f"{d['approbation']} accordée", "approbation.refusee": lambda: f"{d['approbation']} refusée",
        "approbation.utilisee": lambda: f"{d['approbation']} utilisée", "garde.refus": lambda: f"[{d['categorie']}] {d['raison'][:80]}",
        "test.execute": lambda: f"[{d['resultat']}] {d['intitule'][:80]}", "president.identite": lambda: f"identité {d['empreinte']}",
    }.get(t, lambda: (d.get("titre") or d.get("siege") or "")[:90])()


def _cli_org(a, who):
    conf = sys.modules.get("confinement")
    if conf is not None:
        org = conf.charger("organisation")
    else:
        import organisation as org
    if a.sous == "fonctions":
        for k, f in org.FONCTIONS.items():
            print(f"{k:24} niveau {f['niveau']}  {f['titre']:36} {', '.join(sorted(f['permissions']))}")
        return 0
    if a.sous in ("etat", "agent"):
        o = org.etat()
        if a.sous == "agent":
            ag = o["agents"].get(a.id)
            if not ag:
                raise ErreurIle(f"agent inconnu : {a.id}")
            print(json.dumps(ag, ensure_ascii=False, indent=2)); return 0
        for e in o["entreprises"].values():
            if a.entreprise and e["id"] != a.entreprise:
                continue
            d = e["directeur"]
            print(f"{e['nom']} ({e['id']}) — direction {e['direction']}{' : ' + d['agent'] if d and d.get('agent') else ''} · {e['effectif']} agent(s) · {len(e['departements'])} département(s) · {e['postes_non_pourvus']} poste(s) non pourvu(s)")
            for po in sorted(e["postes"], key=lambda x: (9 if x["niveau"] is None else x["niveau"], x["id"])):
                ag = o["agents"].get(po["titulaire"]) if po["titulaire"] else None
                print(f"   {'  ' * min(4, max(0, (po['niveau'] or 0) - 1))}{po['titre']} [{po['id']}] : {ag['nom'] + ' — ' + ag['statut'] if ag else 'non pourvu'}")
        return 0
    if a.sous == "amorcer":
        faits = org.amorcer(who()); print(f"{len(faits)} événement(s) inscrit(s)" + (" : " + ", ".join(e['id'] for e in faits) if faits else " (déjà à jour)")); return 0
    acte = {"departement": lambda: org.creer_departement(a.entreprise, a.id, a.nom, a.mission, who()),
            "poste": lambda: org.creer_poste(a.entreprise, a.id, a.fonction, a.superieur, who(), departement=a.departement, titre=a.titre, competences=a.competence, description=a.description),
            "nommer": lambda: org.creer_agent(a.id, a.nom, a.poste, who(), definition=a.definition, competences=a.competence, description=a.description),
            "affecter": lambda: org.affecter_agent(a.id, a.poste, who(), a.motif),
            "suspendre": lambda: org.suspendre_agent(a.id, a.motif, who()),
            "reactiver": lambda: org.reactiver_agent(a.id, a.motif, who()),
            "attribuer": lambda: org.attribuer_mission(a.mission, a.agent, who(), a.echeance, a.priorite),
            "demarrer": lambda: org.demarrer_mission(a.mission, who()),
            "livrer": lambda: org.livrer(a.mission, a.chemin, who(), a.note),
            "valider": lambda: org.valider(a.mission, who(), a.motif),
            "corriger": lambda: org.demander_correction(a.mission, a.motif, who()),
            "remonter": lambda: org.remonter(a.mission, a.motif, who(), a.bloquer),
            "message": lambda: org.envoyer_message(a.a, a.sujet, a.texte, who(), a.mission),
            "reunion": lambda: org.ouvrir_reunion(a.id, a.entreprise, a.objet, a.participant, who()),
            "clore-reunion": lambda: org.clore_reunion(a.id, a.compte_rendu, who())}[a.sous]
    try:
        ev = acte()
    except org.ErreurOrganisation as e:     # même message propre que les autres refus (module chargé à part)
        raise ErreurIle(str(e))
    d = ev["donnees"]
    print(f"{ev['id']} {ev['type']} — " + (f"autorisé : {d['autorisation']}" if d.get("autorisation") else f"par {ev['auteur'].get('role')} ({ev['auteur'].get('verifie')})")); return 0


def _propositions():
    conf = sys.modules.get("confinement")
    if conf is not None:
        return conf.charger("propositions")
    import propositions
    return propositions


def _cli_proposition(a, who):
    P = _propositions()
    if a.sous in ("liste", "voir"):
        e = P.etat()
        if a.sous == "voir":
            x = e["propositions"].get(a.id)
            if not x:
                raise ErreurIle(f"proposition inconnue : {a.id}")
            print(json.dumps(x, ensure_ascii=False, indent=2)); return 0
        for x in sorted(e["propositions"].values(), key=lambda x: x["cree"]):
            print(f"{x['id']:<16} [{x['libelle']:<24}] {x['origine'] or '—':<16} {(x['titre'] or '')[:70]}")
        print(f"Décisions officielles : {'activées le ' + e['activation']['quand'][:16] if e['activation'] else 'NON activées'} · identité présidentielle : {'inscrite' if e['identite'] else 'absente'}")
        return 0
    acte = {"creer": lambda: P.creer(a.origine, a.titre, a.description, a.categorie, a.objectif, a.consequences, who(), a.cout, a.risque, a.piece, a.institution, a.soumettre),
            "soumettre": lambda: P.soumettre_(a.id, who()),
            "modifier": lambda: P.modifier(a.id, {**{k: getattr(a, k) for k in ("titre", "description", "categorie", "objectif", "consequences", "cout")},
                                                  "risques": a.risque, "pieces": a.piece, "institutions": a.institution}, a.note, who()),
            "transmettre": lambda: P.transmettre(a.id, a.vers, who(), a.destinataire),
            "avis-demander": lambda: P.demander_avis(a.id, a.destinataire, a.question, who(), echeance=a.echeance),
            "avis-rendre": lambda: P.rendre_avis(a.id, a.demande, a.sens, a.texte, who()),
            "mettre-en-oeuvre": lambda: P.mettre_en_oeuvre(a.id, a.responsable, a.modalites, who(), echeance=a.echeance, mission=a.mission),
            "executer": lambda: P.executer(a.id, a.etape, who(), a.resultat),
            "recevoir": lambda: P.accuser_reception(a.id, a.institution_, who()),
            "archiver": lambda: P.archiver(a.id, a.motif, who())}[a.sous]
    try:
        ev = acte()
    except P.ErreurProposition as e:
        raise ErreurIle(str(e))
    print(f"{ev['id']} {ev['type']} — {ev['donnees'].get('proposition', '')} (par {ev['auteur'].get('role')}, {ev['auteur'].get('verifie')})")
    return 0


def _cli_president_proposition(a, cle):
    """Décisions du président sur les propositions, dans un vrai terminal (phrase saisie sur /dev/tty)."""
    P = _propositions()
    try:
        if a.sous == "activer-decisions":
            print(P.DECLARATION)
            return P.activer_decisions(cle, canal="terminal")
        x = P.etat()["propositions"].get(a.id)
        if not x:
            raise ErreurIle(f"proposition inconnue : {a.id}")
        if a.action == "approuver":
            return P.approuver(a.id, cle, x["version"], a.motif, a.conditions, canal="terminal")
        if a.action == "refuser":
            return P.refuser(a.id, cle, x["version"], a.motif, canal="terminal")
        if a.action == "modifier":
            return P.demander_modifications(a.id, cle, a.observations, a.attendus, a.echeance, canal="terminal")
        if a.action == "avis":
            return P.demander_avis(a.id, a.destinataire, a.question, cle=cle, echeance=a.echeance, canal="terminal")
        return P.rectifier(a.id, cle, a.vers, a.motif, canal="terminal")
    except P.ErreurProposition as e:
        raise ErreurIle(str(e))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ile.py", description="Registre des opérations de l'Entreprise des Agents")
    ap.add_argument("--auteur", default="maire", help="rôle de l'auteur (maire, president, chef-rev-em, critique-clarte…)")
    ap.add_argument("--run", help="exécution en cours de l'auteur (R-0001…), pour vérifier son identité")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("etat"); sp.add_parser("verifier"); sp.add_parser("projeter"); sp.add_parser("classer")
    j = sp.add_parser("journal"); j.add_argument("--siege"); j.add_argument("--type"); j.add_argument("-n", type=int, default=30)
    i = sp.add_parser("instruction"); isp = i.add_subparsers(dest="sous", required=True)
    x = isp.add_parser("donner"); x.add_argument("texte"); x.add_argument("--siege")
    x = isp.add_parser("traiter"); x.add_argument("id"); x.add_argument("--reponse", required=True); x.add_argument("--mission", action="append", default=[])
    isp.add_parser("liste")
    m = sp.add_parser("mission"); msp = m.add_subparsers(dest="sous", required=True)
    x = msp.add_parser("proposer")
    for a in ("--siege", "--titre", "--objectif"):
        x.add_argument(a, required=True)
    x.add_argument("--critere", action="append", required=True); x.add_argument("--source", action="append", default=[])
    for a in ("--valeur", "--urgence", "--effort", "--risque"):
        x.add_argument(a, type=int)
    x.add_argument("--sensible", action="store_true"); x.add_argument("--origine")
    x = msp.add_parser("statut"); x.add_argument("id"); x.add_argument("vers"); x.add_argument("--motif")
    x = msp.add_parser("demarrer"); x.add_argument("id")
    x = msp.add_parser("voir"); x.add_argument("id")
    x = msp.add_parser("liste"); x.add_argument("--siege"); x.add_argument("--statut")
    pb = sp.add_parser("probleme"); psp = pb.add_subparsers(dest="sous", required=True)
    x = psp.add_parser("signaler"); x.add_argument("--siege", required=True); x.add_argument("--titre", required=True); x.add_argument("--gravite", required=True, choices=GRAVITES); x.add_argument("--source"); x.add_argument("--preuve")
    x = psp.add_parser("resoudre"); x.add_argument("id"); x.add_argument("--motif", required=True)
    de = sp.add_parser("decision"); dsp = de.add_subparsers(dest="sous", required=True)
    x = dsp.add_parser("demander"); x.add_argument("--siege", required=True); x.add_argument("--titre", required=True); x.add_argument("--question", required=True); x.add_argument("--contexte"); x.add_argument("--source"); x.add_argument("--mission")
    x = dsp.add_parser("trancher"); x.add_argument("id"); x.add_argument("verdict", choices=("approuvee", "refusee", "reportee")); x.add_argument("--motif")
    si = sp.add_parser("siege"); ssp = si.add_subparsers(dest="sous", required=True)
    x = ssp.add_parser("etat"); x.add_argument("--siege", required=True); x.add_argument("--phase", required=True); x.add_argument("--resume", required=True); x.add_argument("--indicateur", action="append", default=[], help="nom=valeur@source"); x.add_argument("--source")
    x = ssp.add_parser("priorite"); x.add_argument("--siege", required=True); x.add_argument("priorite", choices=tuple(PRIORITES)); x.add_argument("--motif")
    ar = sp.add_parser("artefact"); x = ar.add_subparsers(dest="sous", required=True).add_parser("deposer"); x.add_argument("chemin"); x.add_argument("--mission"); x.add_argument("--nature")
    ru = sp.add_parser("run"); rsp = ru.add_subparsers(dest="sous", required=True)
    x = rsp.add_parser("debut"); x.add_argument("--role", required=True); x.add_argument("--siege"); x.add_argument("--mission"); x.add_argument("--agent-id")
    x = rsp.add_parser("fin"); x.add_argument("id"); x.add_argument("--resultat")
    ca = sp.add_parser("capteur", help="réservé aux hooks : lit le JSON du hook sur stdin"); ca.add_argument("evenement", choices=("debut", "fin", "session"))
    ap_ = sp.add_parser("approbation", help="file d'approbations"); asp = ap_.add_subparsers(dest="sous", required=True)
    asp.add_parser("liste")
    x = asp.add_parser("demander"); x.add_argument("--categorie", required=True); x.add_argument("--raison", required=True); x.add_argument("--commande", required=True); x.add_argument("--outil", default="Bash"); x.add_argument("--siege")
    te = sp.add_parser("test", help="résultats de tests réellement exécutés"); x = te.add_subparsers(dest="sous", required=True).add_parser("enregistrer")
    x.add_argument("--siege", required=True); x.add_argument("--intitule", required=True); x.add_argument("--resultat", required=True, choices=RESULTATS_TEST)
    x.add_argument("--commande"); x.add_argument("--resume"); x.add_argument("--mission"); x.add_argument("--execute-le"); x.add_argument("--preuve")
    pr = sp.add_parser("president", help="actes du président (phrase saisie dans un vrai terminal)"); prs = pr.add_subparsers(dest="sous", required=True)
    prs.add_parser("creer"); prs.add_parser("statut"); prs.add_parser("changer-phrase")
    x = prs.add_parser("approuver"); x.add_argument("id"); x.add_argument("--motif"); x.add_argument("--heures", type=float, default=DUREE_APPROBATION_H)
    x = prs.add_parser("refuser"); x.add_argument("id"); x.add_argument("--motif")
    x = prs.add_parser("mission"); x.add_argument("id"); x.add_argument("vers", choices=("planifiee", "rejetee", "reportee", "proposee", "attente_president")); x.add_argument("--motif")
    prs.add_parser("activer-decisions", help="active les décisions officielles sur les propositions (acte signé, une fois)")
    x = prs.add_parser("proposition", help="décider d'une proposition (acte signé)"); x.add_argument("id")
    x.add_argument("action", choices=("approuver", "refuser", "modifier", "avis", "rectifier")); x.add_argument("--motif"); x.add_argument("--conditions")
    x.add_argument("--observations"); x.add_argument("--attendus"); x.add_argument("--echeance"); x.add_argument("--destinataire"); x.add_argument("--question")
    x.add_argument("--vers", choices=("approuvee", "refusee"))
    po = sp.add_parser("proposition", help="propositions soumises au président : créer, soumettre, avis, exécution"); psp2 = po.add_subparsers(dest="sous", required=True)
    psp2.add_parser("liste"); x = psp2.add_parser("voir"); x.add_argument("id")
    for nom in ("creer", "modifier"):
        x = psp2.add_parser(nom)
        if nom == "creer":
            x.add_argument("--origine", required=True); x.add_argument("--soumettre", action="store_true")
        else:
            x.add_argument("id"); x.add_argument("--note", required=True)
        for c in ("--titre", "--description", "--categorie", "--objectif", "--consequences"):
            x.add_argument(c, required=(nom == "creer"))
        x.add_argument("--cout"); x.add_argument("--risque", action="append", default=[]); x.add_argument("--piece", action="append", default=[]); x.add_argument("--institution", action="append", default=[])
    x = psp2.add_parser("soumettre"); x.add_argument("id")
    x = psp2.add_parser("transmettre"); x.add_argument("id"); x.add_argument("--vers", required=True, choices=("analyse", "president")); x.add_argument("--destinataire", action="append", default=[])
    x = psp2.add_parser("avis-demander"); x.add_argument("id"); x.add_argument("--destinataire", required=True); x.add_argument("--question", required=True); x.add_argument("--echeance")
    x = psp2.add_parser("avis-rendre"); x.add_argument("id"); x.add_argument("--demande", required=True); x.add_argument("--sens", required=True, choices=("favorable", "defavorable", "reserve")); x.add_argument("--texte", required=True)
    x = psp2.add_parser("mettre-en-oeuvre"); x.add_argument("id"); x.add_argument("--responsable", required=True); x.add_argument("--modalites", required=True); x.add_argument("--echeance"); x.add_argument("--mission")
    x = psp2.add_parser("executer"); x.add_argument("id"); x.add_argument("etape", choices=("debut", "fin")); x.add_argument("--resultat")
    x = psp2.add_parser("recevoir"); x.add_argument("id"); x.add_argument("--institution", dest="institution_", required=True)
    x = psp2.add_parser("archiver"); x.add_argument("id"); x.add_argument("--motif", required=True)
    og = sp.add_parser("org", help="organisation : entreprises, départements, postes, agents, hiérarchie"); osp = og.add_subparsers(dest="sous", required=True)
    osp.add_parser("fonctions"); osp.add_parser("amorcer")
    x = osp.add_parser("etat"); x.add_argument("--entreprise")
    x = osp.add_parser("agent"); x.add_argument("id")
    x = osp.add_parser("departement"); x.add_argument("entreprise"); x.add_argument("id"); x.add_argument("--nom", required=True); x.add_argument("--mission", default="")
    x = osp.add_parser("poste"); x.add_argument("entreprise"); x.add_argument("id"); x.add_argument("--fonction", required=True); x.add_argument("--superieur")
    x.add_argument("--departement"); x.add_argument("--titre"); x.add_argument("--competence", action="append", default=[]); x.add_argument("--description")
    x = osp.add_parser("nommer", help="crée l'agent sur un poste"); x.add_argument("id"); x.add_argument("--nom", required=True); x.add_argument("--poste", required=True)
    x.add_argument("--definition", help="agents/definitions/<nom>.md : capacité d'exécution"); x.add_argument("--competence", action="append", default=[]); x.add_argument("--description")
    x = osp.add_parser("affecter"); x.add_argument("id"); x.add_argument("--poste", required=True); x.add_argument("--motif")
    x = osp.add_parser("suspendre"); x.add_argument("id"); x.add_argument("--motif", required=True)
    x = osp.add_parser("reactiver"); x.add_argument("id"); x.add_argument("--motif", required=True)
    x = osp.add_parser("attribuer"); x.add_argument("mission"); x.add_argument("--agent", required=True); x.add_argument("--echeance"); x.add_argument("--priorite")
    x = osp.add_parser("demarrer"); x.add_argument("mission")
    x = osp.add_parser("livrer"); x.add_argument("mission"); x.add_argument("--chemin", required=True); x.add_argument("--note")
    x = osp.add_parser("valider"); x.add_argument("mission"); x.add_argument("--motif")
    x = osp.add_parser("corriger"); x.add_argument("mission"); x.add_argument("--motif", required=True)
    x = osp.add_parser("remonter"); x.add_argument("mission"); x.add_argument("--motif", required=True); x.add_argument("--bloquer", action="store_true")
    x = osp.add_parser("message"); x.add_argument("a"); x.add_argument("--sujet", required=True); x.add_argument("--texte", required=True); x.add_argument("--mission")
    x = osp.add_parser("reunion"); x.add_argument("id"); x.add_argument("--entreprise", required=True); x.add_argument("--objet", required=True); x.add_argument("--participant", action="append", default=[])
    x = osp.add_parser("clore-reunion"); x.add_argument("id"); x.add_argument("--compte-rendu", required=True)
    a = ap.parse_args(argv)
    who = lambda: auteur_cli(a.auteur, a.run)

    def cle_terminal():
        try:
            return deverrouiller(president.demander_phrase())
        except president.ErreurPresident as e:
            raise ErreurIle(str(e))
    try:
        if a.cmd == "verifier":
            r = verifier()
            print(("✔ journal intègre" if r["ok"] else "✘ JOURNAL ALTÉRÉ") + f" — {r['n']} événements, dernière empreinte {r['dernier'][:16]}…")
            for e in r["erreurs"]:
                print("  -", e)
            return 0 if r["ok"] else 1
        if a.cmd == "projeter":
            _ecrire_etat(etat()); print(f"projection écrite : {ETAT}"); return 0
        if a.cmd == "capteur":
            try:
                payload = json.loads(sys.stdin.read() or "{}")
            except Exception:
                payload = {}
            try:
                if a.evenement == "session":
                    txt = briefing_dg(payload.get("session_id"))
                    if txt:
                        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": txt}}, ensure_ascii=False))
                else:
                    capteur(a.evenement, payload)
            except Exception as e:   # un capteur ne bloque jamais le travail ; l'erreur est gardée pour la Forge
                with open(OPS / "capteurs-erreurs.log", "a", encoding="utf-8") as f:
                    f.write(f"{maintenant()} {a.evenement} {type(e).__name__}: {e}\n")
            return 0
        if a.cmd == "org":
            return _cli_org(a, who)
        if a.cmd == "proposition":
            return _cli_proposition(a, who)
        if a.cmd == "etat":
            p = etat(); v = verifier()
            print(f"Journal : {p['evenements']} événements — {'intègre' if v['ok'] else 'ALTÉRÉ'}")
            print(f"Identité présidentielle : {p['identite']['empreinte'] if p['identite'] else 'non créée'} · actes rejetés : {len(p['rejets'])} · refus du garde : {len(p['refus'])}")
            print(f"Instructions non traitées : {sum(1 for x in p['instructions'].values() if x['statut'] != 'traitee')} · décisions en attente : {sum(1 for x in p['decisions'].values() if x['verdict'] is None)} · approbations en attente : {sum(1 for x in p['approbations'].values() if x['statut'] == 'en_attente')} · problèmes ouverts : {sum(1 for x in p['problemes'].values() if x['ouvert'])}")
            print(f"Exécutions actives : {len(p['runs_actifs'])} · missions : " + ", ".join(f"{s} {sum(1 for m in p['missions'].values() if m['statut'] == s)}" for s in STATUTS if any(m['statut'] == s for m in p['missions'].values())))
            return 0
        if a.cmd == "journal":
            evs = [e for e in lire() if (not a.siege or e["donnees"].get("siege") == a.siege) and (not a.type or e["type"].startswith(a.type))]
            for e in evs[-a.n:]:
                au = e["auteur"]
                print(f"{e['id']} {e['quand'][:19]} {e['type']:<20} {au.get('role'):<22} [{au.get('verifie')}] {_resume(e)}")
            return 0
        if a.cmd == "classer":
            ev = classer(who())
            for l in ev["donnees"]["classement"]:
                print(f"#{l['rang']:<2} {l['score']:>5}  {l['mission']}")
            return 0
        if a.cmd == "instruction":
            if a.sous == "donner":
                ev = donner_instruction(a.texte, cle_terminal(), a.siege, canal="terminal")
            elif a.sous == "traiter":
                ev = traiter_instruction(a.id, who(), a.reponse, a.mission)
            else:
                for x in etat()["instructions"].values():
                    print(f"{x['id']} [{x['statut']}] {x['texte'][:90]}")
                return 0
        elif a.cmd == "mission":
            if a.sous == "proposer":
                ev = proposer_mission(a.siege, a.titre, a.objectif, a.critere, who(), a.valeur, a.urgence, a.effort, a.risque, a.sensible, a.source, a.origine)
            elif a.sous == "statut":
                ev = changer_statut(a.id, a.vers, who(), a.motif)
            elif a.sous == "demarrer":
                ev = demarrer(a.id, who())
            elif a.sous == "voir":
                print(json.dumps(etat()["missions"].get(a.id) or {}, ensure_ascii=False, indent=2)); return 0
            else:
                for x in sorted(etat()["missions"].values(), key=lambda m: (m["rang"] or 999, m["id"])):
                    if (not a.siege or x["siege"] == a.siege) and (not a.statut or x["statut"] == a.statut):
                        print(f"{x['id']} [{x['statut']:<17}] {x['siege']:<16} score {x['score'] if x['score'] is not None else '—':>5}  {x['titre'][:70]}")
                return 0
        elif a.cmd == "probleme":
            ev = signaler_probleme(a.siege, a.titre, a.gravite, who(), a.source, a.preuve) if a.sous == "signaler" else resoudre_probleme(a.id, who(), a.motif)
        elif a.cmd == "decision":
            ev = demander_decision(a.siege, a.titre, a.question, who(), a.contexte, a.source, a.mission) if a.sous == "demander" else trancher(a.id, a.verdict, cle_terminal(), a.motif, canal="terminal")
        elif a.cmd == "siege":
            if a.sous == "etat":
                inds = []
                for s in a.indicateur:
                    mm = re.match(r"^([^=]+)=([^@]*)(?:@(.+))?$", s)
                    if not mm:
                        raise ErreurIle(f"indicateur mal formé (nom=valeur@source) : {s}")
                    inds.append({"nom": mm[1].strip(), "valeur": mm[2].strip(), "source": (mm[3] or "").strip() or None})
                ev = etat_siege(a.siege, a.phase, a.resume, who(), inds, a.source)
            else:
                ev = fixer_priorite(a.siege, a.priorite, cle_terminal(), a.motif, canal="terminal")
        elif a.cmd == "artefact":
            ev = deposer_artefact(a.chemin, who(), a.mission, a.nature)
        elif a.cmd == "approbation":
            if a.sous == "liste":
                for x in etat()["approbations"].values():
                    print(f"{x['id']} [{x['statut']:<10}] {x['categorie']:<14} {(x['commande'] or '')[:90]}")
                return 0
            aid, neuve = demander_approbation(a.categorie, "demande manuelle", a.raison, a.outil, a.commande, who(), cwd=os.getcwd(), agent={"role": a.auteur}, siege=a.siege)
            print(f"{aid} {'inscrite' if neuve else 'déjà en attente'} — en attente de l'accord signé du président"); return 0
        elif a.cmd == "test":
            ev = enregistrer_test(a.siege, a.intitule, a.resultat, who(), a.commande, a.resume, None, a.mission, a.execute_le, a.preuve)
        elif a.cmd == "president":
            if a.sous == "statut":
                i = identite_courante()
                print(f"Identité présidentielle : {i['empreinte']} (créée le {i['quand'][:16]}, {i.get('canal') or '—'})" if i else "Aucune identité présidentielle. Crée-la avec : ./ile president"); return 0
            if a.sous == "creer":
                if identite_courante():
                    raise ErreurIle("une identité présidentielle existe déjà (empreinte " + identite_courante()["empreinte"] + ")")
                p1 = president.demander_phrase("Choisis ta phrase présidentielle (12 caractères au moins) : ")
                if president.demander_phrase("Répète-la : ") != p1:
                    raise ErreurIle("les deux saisies diffèrent")
                try:
                    cle = creer_identite(p1)
                except president.ErreurPresident as e:
                    raise ErreurIle(str(e))
                print(f"✔ Identité présidentielle créée — empreinte {cle.empreinte}. Retiens ta phrase : elle n'est écrite nulle part et ne peut pas être récupérée."); return 0
            cle = cle_terminal()
            if a.sous == "changer-phrase":
                p1 = president.demander_phrase("Nouvelle phrase : ")
                if president.demander_phrase("Répète-la : ") != p1:
                    raise ErreurIle("les deux saisies diffèrent")
                try:
                    n = changer_phrase(cle, p1)
                except president.ErreurPresident as e:
                    raise ErreurIle(str(e))
                print(f"✔ Nouvelle identité {n.empreinte}, signée par l'ancienne."); return 0
            if a.sous in ("activer-decisions", "proposition"):
                ev = _cli_president_proposition(a, cle)
                print(f"{ev['id']} {ev['type']} — acte signé (clé {ev['auteur'].get('cle')})"); return 0
            if a.sous == "approuver":
                ev = accorder(a.id, cle, a.motif, a.heures, canal="terminal")
            elif a.sous == "refuser":
                ev = refuser(a.id, cle, a.motif, canal="terminal")
            else:
                ev = changer_statut(a.id, a.vers, {}, a.motif, cle=cle)
        elif a.cmd == "run":
            ev = run_debut(a.role, who(), a.siege, a.mission, a.agent_id) if a.sous == "debut" else run_fin(a.id, who(), a.resultat)
        else:
            return 2
        print(f"{ev['id']} {ev['type']} — {_resume(ev)}")
        return 0
    except ErreurIle as e:
        print(f"refusé : {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
