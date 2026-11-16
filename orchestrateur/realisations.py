"""Réalisation automatique d'une demande : Conseil → Concepteur → Développeur → Correcteurs, avec boucle de correction.

Une réalisation (X-AAAAMMJJ-NNN) est la trace, au registre chaîné, du passage d'un prompt par toute la chaîne
(commande /realiser). Ce module n'exécute AUCUN agent : il enregistre ce que les agents ont réellement rendu et
IMPOSE les règles du circuit, sous le verrou du journal :

  conseil (au moins un avis) → conception (plan + critères d'acceptation) → développement (tour 1)
      → correction (verdict de CHAQUE correcteur requis)
          ├─ tous « accepte »        → la réalisation peut être close « acceptee »
          └─ un seul « a_corriger »  → développement (tour suivant), TOURS_MAX au plus ; au-delà : close « bloquee »

Garanties (testées) :
  - pas de développement sans plan, pas de plan sans avis du Conseil, pas de verdict sans livraison à juger ;
  - une réalisation n'est « acceptee » que si chaque correcteur requis a accepté le DERNIER tour ;
  - un développeur ne se corrige jamais lui-même (rôles distincts dans une même réalisation) ;
  - la boucle s'arrête : pas de tour au-delà de TOURS_MAX ; le blocage est remonté, jamais masqué ;
  - une étape dit qui l'a inscrite : l'agent lui-même (identité vérifiée par son exécution) ou le Maire, qui
    rapporte alors le travail de l'agent ; dans ce cas l'exécution citée (--run-agent) doit exister au registre
    pour ce rôle, sinon l'étape est marquée « sans exécution au registre ».
"""
import sys

if sys.modules.get("confinement") is not None:
    ile = sys.modules["confinement"].charger("ile")
else:
    import ile  # noqa: E402

TYPES = ("realisation.ouverte", "realisation.etape", "realisation.close")
PHASES = ("conseil", "conception", "developpement", "correction")
VERDICTS = ("accepte", "a_corriger")
RESULTATS = ("acceptee", "bloquee", "abandonnee")
CORRECTEURS_REQUIS = ("forgeron", "relecteur")
TOURS_MAX = 3
LIBELLES = {"ouverte": "Ouverte", "conseil": "Avis du Conseil", "conception": "Plan établi", "developpement": "En développement",
            "correction": "En correction", "a_corriger": "À corriger", "prete": "Acceptée par les correcteurs",
            "acceptee": "Acceptée", "bloquee": "Bloquée", "abandonnee": "Abandonnée"}


class ErreurRealisation(ile.ErreurIle):
    pass


# ------------------------------------------------------------------ projection
def _verdicts(x, tour):
    """Dernier verdict de chaque correcteur pour un tour."""
    out = {}
    for e in x["etapes"]:
        if e["phase"] == "correction" and e["tour"] == tour:
            out[e["role"]] = e["verdict"]
    return out


def _situation(x):
    """État dérivé : où en est le circuit, et ce qui est attendu ensuite."""
    if x["close"]:
        return x["close"]["resultat"], None
    phases = [e["phase"] for e in x["etapes"]]
    if "conseil" not in phases:
        return "ouverte", "avis du Conseil"
    if "conception" not in phases:
        return "conseil", "plan du Concepteur"
    tour = x["tour"]
    if tour == 0:
        return "conception", "développement (tour 1)"
    v = _verdicts(x, tour)
    if "a_corriger" in v.values():
        return "a_corriger", (f"développement (tour {tour + 1})" if tour < TOURS_MAX else f"clôture « bloquee » ({TOURS_MAX} tours atteints)")
    manquants = [c for c in CORRECTEURS_REQUIS if c not in v]
    if manquants:
        return ("correction" if v else "developpement"), "verdict de " + ", ".join(manquants)
    return "prete", "clôture « acceptee »"


def projeter(evs: list, p_ile: dict = None) -> dict:
    p_ile = p_ile if p_ile is not None else ile.projeter(evs)
    runs, out = p_ile["runs"], {}
    for ev in evs:
        t, d, q, au = ev["type"], ev["donnees"], ev["quand"], ev.get("auteur") or {}
        if t == "realisation.ouverte":
            out[d["realisation"]] = {"id": d["realisation"], "siege": d.get("siege"), "titre": d.get("titre"), "prompt": d.get("prompt"),
                                     "ouverte": q, "evenement": ev["id"], "auteur": au, "etapes": [], "tour": 0, "close": None}
        elif t == "realisation.etape" and d.get("realisation") in out:
            x = out[d["realisation"]]
            r = runs.get(d.get("run_agent")) if d.get("run_agent") else None
            if au.get("verifie") == "run" and au.get("role") == d.get("role"):
                preuve = {"niveau": "agent", "texte": f"inscrit par l'agent lui-même, exécution {au.get('run')}"}
            elif r and r.get("role") == d.get("role"):
                preuve = {"niveau": "execution", "texte": f"rapporté par {au.get('role')} ; exécution {r['run']} de {r['role']} au registre"}
            else:
                preuve = {"niveau": "declare", "texte": f"rapporté par {au.get('role')} ; sans exécution au registre"}
            x["etapes"].append({"quand": q, "evenement": ev["id"], "phase": d["phase"], "role": d.get("role"), "tour": d.get("tour", 0),
                                "verdict": d.get("verdict"), "resume": d.get("resume"), "defauts": d.get("defauts", []),
                                "artefact": d.get("artefact"), "criteres": d.get("criteres", []), "preuve": preuve})
            if d["phase"] == "developpement":
                x["tour"] = d["tour"]
        elif t == "realisation.close" and d.get("realisation") in out:
            out[d["realisation"]]["close"] = {"quand": q, "evenement": ev["id"], "resultat": d["resultat"], "resume": d.get("resume"), "par": au}
    for x in out.values():
        x["statut"], x["attendu"] = _situation(x)
        x["libelle"] = LIBELLES[x["statut"]]
        x["criteres"] = next((e["criteres"] for e in reversed(x["etapes"]) if e["phase"] == "conception"), [])
    return {"realisations": out, "tours_max": TOURS_MAX, "correcteurs_requis": list(CORRECTEURS_REQUIS)}


def etat() -> dict:
    evs = ile.lire()
    return projeter(evs, ile.projeter(evs))


# ------------------------------------------------------------------ écritures (règles sous le verrou)
def _texte(x, quoi, n=4000, obligatoire=True):
    x = (x or "").strip()
    if obligatoire and not x:
        raise ErreurRealisation(f"{quoi} obligatoire")
    if len(x) > n:
        raise ErreurRealisation(f"{quoi} trop long ({n} caractères au plus)")
    return x or None


def _orchestrateur(auteur, role=None):
    """Le Maire (session principale) rapporte ; un agent n'inscrit que SA propre étape, identité vérifiée."""
    if auteur.get("role") == "maire":
        return
    if not (role and auteur.get("role") == role and auteur.get("verifie") == "run"):
        raise ErreurRealisation(f"« {auteur.get('role')} » ne peut pas inscrire cette étape : le Maire rapporte, ou l'agent concerné l'inscrit sous son identité vérifiée (--run)")


def _sous_verrou(regle):
    def controle(evs):
        return regle(projeter(evs)) or {}
    return controle


def _get(e, xid):
    x = e["realisations"].get(xid)
    if not x:
        raise ErreurRealisation(f"réalisation inconnue : {xid}")
    if x["close"]:
        raise ErreurRealisation(f"{xid} est close ({x['close']['resultat']}) : ouvrez une nouvelle réalisation")
    return x


def ouvrir(siege, titre, prompt, auteur):
    ile._siege_valide(siege)
    _orchestrateur(auteur)
    titre, prompt = _texte(titre, "titre", 200), _texte(prompt, "prompt", 8000)

    def regle(e):
        jour = ile.maintenant()[:10].replace("-", "")
        n = sum(1 for k in e["realisations"] if k.startswith("X-" + jour)) + 1
        return {"realisation": f"X-{jour}-{n:03d}"}
    return ile.ajouter("realisation.ouverte", {"siege": siege, "titre": titre, "prompt": prompt}, auteur, completer=_sous_verrou(regle))


def etape(xid, phase, role, auteur, resume, tour=None, verdict=None, defauts=(), criteres=(), artefact=None, run_agent=None):
    if phase not in PHASES:
        raise ErreurRealisation(f"phase : {', '.join(PHASES)}")
    role = _texte(role, "rôle de l'agent", 60)
    _orchestrateur(auteur, role)
    resume = _texte(resume, "résumé de ce que l'agent a rendu", 4000)
    defauts = [_texte(x, "défaut", 1000) for x in defauts]
    criteres = [_texte(x, "critère d'acceptation", 500) for x in criteres]
    if phase == "correction":
        if verdict not in VERDICTS:
            raise ErreurRealisation(f"verdict d'un correcteur : {', '.join(VERDICTS)}")
        if verdict == "a_corriger" and not defauts:
            raise ErreurRealisation("un verdict « a_corriger » liste les défauts à corriger (--defaut)")
        if verdict == "accepte" and defauts:
            raise ErreurRealisation("un verdict « accepte » ne porte pas de défaut bloquant : corrigez le verdict ou retirez les défauts")
    elif verdict:
        raise ErreurRealisation("seule une étape de correction porte un verdict")
    if phase == "conception" and not criteres:
        raise ErreurRealisation("le plan du Concepteur fixe au moins un critère d'acceptation vérifiable (--critere)")

    def regle(e):
        x = _get(e, xid)
        phases = [s["phase"] for s in x["etapes"]]
        devs = {s["role"] for s in x["etapes"] if s["phase"] == "developpement"}
        cors = {s["role"] for s in x["etapes"] if s["phase"] == "correction"}
        if phase == "conseil":
            if "conception" in phases:
                raise ErreurRealisation("le plan est déjà établi : l'avis du Conseil se rend avant la conception")
            return {"tour": 0}
        if phase == "conception":
            if "conseil" not in phases:
                raise ErreurRealisation("pas de plan sans avis du Conseil")
            if "developpement" in phases:
                raise ErreurRealisation("le développement a commencé : le plan ne se réécrit plus (ouvrez une nouvelle réalisation)")
            return {"tour": 0}
        if phase == "developpement":
            if "conception" not in phases:
                raise ErreurRealisation("pas de développement sans plan du Concepteur")
            if role in cors:
                raise ErreurRealisation(f"« {role} » est correcteur de cette réalisation : il ne peut pas en être le développeur")
            attendu = x["tour"] + 1
            if x["tour"] and "a_corriger" not in _verdicts(x, x["tour"]).values():
                raise ErreurRealisation(f"le tour {x['tour']} n'a pas été refusé par un correcteur : pas de nouveau tour de développement")
            if attendu > TOURS_MAX:
                raise ErreurRealisation(f"{TOURS_MAX} tours de correction atteints : la boucle s'arrête ; clore la réalisation « bloquee » et remonter le blocage à Anton")
            if tour not in (None, attendu):
                raise ErreurRealisation(f"tour attendu : {attendu}")
            return {"tour": attendu}
        if not x["tour"]:
            raise ErreurRealisation("rien à corriger : aucune livraison du développeur")
        if role in devs:
            raise ErreurRealisation(f"« {role} » a développé cette réalisation : il ne peut pas en être le correcteur")
        if tour not in (None, x["tour"]):
            raise ErreurRealisation(f"le tour en cours est le {x['tour']}")
        if role in _verdicts(x, x["tour"]):
            raise ErreurRealisation(f"« {role} » a déjà rendu son verdict sur le tour {x['tour']}")
        return {"tour": x["tour"]}
    d = {"realisation": xid, "phase": phase, "role": role, "resume": resume}
    for k, v in (("verdict", verdict), ("defauts", defauts), ("criteres", criteres), ("artefact", artefact), ("run_agent", run_agent)):
        if v:
            d[k] = v
    return ile.ajouter("realisation.etape", d, auteur, completer=_sous_verrou(regle))


def clore(xid, resultat, resume, auteur):
    if resultat not in RESULTATS:
        raise ErreurRealisation(f"résultat : {', '.join(RESULTATS)}")
    _orchestrateur(auteur)
    resume = _texte(resume, "résumé final", 4000)

    def regle(e):
        x = _get(e, xid)
        if resultat == "acceptee" and x["statut"] != "prete":
            raise ErreurRealisation(f"{xid} ne peut pas être close « acceptee » : {x['libelle'].lower()} ; attendu : {x['attendu']}")
        if resultat == "bloquee" and x["statut"] == "prete":
            raise ErreurRealisation(f"{xid} a été acceptée par tous les correcteurs : elle ne se clôt pas « bloquee »")
    return ile.ajouter("realisation.close", {"realisation": xid, "resultat": resultat, "resume": resume}, auteur, completer=_sous_verrou(regle))
