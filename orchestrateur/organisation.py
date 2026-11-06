"""Organisation de l'Île Entrepreneuriale : entreprises, départements, postes, agents, hiérarchie (phase 3.1–3.2).

Aucune base de données : chaque fait est un événement du registre chaîné (orchestrateur/registre/journal.jsonl, via
ile.ajouter) et l'organisation est une PROJECTION recalculée à partir du journal. Rien n'est simulé :
  - une entreprise est un bâtiment du cadastre (registre.json : maisons et institutions) ;
  - un poste sans titulaire est « non pourvu » (jamais peuplé de noms inventés) ;
  - le statut d'un agent est DÉRIVÉ d'événements réels (exécution ouverte par un hook, suspension…), jamais saisi.

Autorisation côté serveur : chaque écriture est contrôlée SOUS LE VERROU du journal (dans `completer`), d'après la
projection à jour. Peuvent agir : le président (acte signé), le DG de l'île (le Maire, identité déclarée — limite connue
de l'étape 2), et un agent dont l'identité est VÉRIFIÉE par son exécution ouverte (`--run`), seulement sur les postes
placés sous le sien et si sa fonction le permet. Une identité seulement déclarée ne suffit pas pour un agent.
"""
import hashlib
import re
import sys
from pathlib import Path

if sys.modules.get("confinement") is not None:
    ile = sys.modules["confinement"].charger("ile")
else:
    import ile  # noqa: E402

DEFINITIONS = ile.RACINE / "agents" / "definitions"

# ------------------------------------------------------------------ catalogue des fonctions
# niveau : 0 île · 1 direction générale · 2 direction · 3 management · 4 responsable d'équipe · 5 expertise · 6 opérationnel
P_DIRECTION = {"creer_departement", "creer_poste", "nommer_agent", "suspendre_agent", "attribuer_mission", "valider_livrable"}
P_MANAGEMENT = {"creer_poste", "nommer_agent", "attribuer_mission", "valider_livrable"}
P_EQUIPE = {"attribuer_mission", "valider_livrable"}
P_EXECUTION = {"executer_mission"}
FONCTIONS = {
    "dg-ile":                    {"titre": "Directeur général de l'île", "niveau": 0, "famille": "direction", "permissions": P_DIRECTION},
    "directeur-general":         {"titre": "Directeur général", "niveau": 1, "famille": "direction", "permissions": P_DIRECTION},
    "directeur-operations":      {"titre": "Directeur des opérations", "niveau": 2, "famille": "direction", "permissions": P_DIRECTION},
    "directeur-financier":       {"titre": "Directeur financier", "niveau": 2, "famille": "direction", "permissions": P_DIRECTION},
    "directeur-technique":       {"titre": "Directeur technique", "niveau": 2, "famille": "direction", "permissions": P_DIRECTION},
    "directeur-rh":              {"titre": "Directeur des ressources humaines", "niveau": 2, "famille": "direction", "permissions": P_DIRECTION},
    "manager":                   {"titre": "Manager de département", "niveau": 3, "famille": "management", "permissions": P_MANAGEMENT},
    "chef-de-projet":            {"titre": "Chef de projet", "niveau": 3, "famille": "management", "permissions": P_MANAGEMENT},
    "responsable-equipe":        {"titre": "Responsable d'équipe", "niveau": 4, "famille": "management", "permissions": P_EQUIPE},
    "responsable-qualite":       {"titre": "Responsable qualité", "niveau": 4, "famille": "management", "permissions": P_EQUIPE | {"auditer"}},
    "developpeur-frontend":      {"titre": "Développeur frontend", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "developpeur-backend":       {"titre": "Développeur backend", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "architecte-logiciel":       {"titre": "Architecte logiciel", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "analyste-financier":        {"titre": "Analyste financier", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "analyste-donnees":          {"titre": "Analyste de données", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "responsable-marketing":     {"titre": "Responsable marketing", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "commercial":                {"titre": "Commercial", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "charge-communication":      {"titre": "Chargé de communication", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "juriste":                   {"titre": "Juriste", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "auditeur":                  {"titre": "Auditeur", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION | {"auditer"}},
    "chercheur":                 {"titre": "Chercheur", "niveau": 5, "famille": "expertise", "permissions": P_EXECUTION},
    "agent-operationnel":        {"titre": "Agent opérationnel", "niveau": 6, "famille": "operationnel", "permissions": P_EXECUTION},
}
TYPES_ORG = ("org.departement.cree", "org.poste.cree", "org.agent.cree", "org.agent.affecte", "org.agent.suspendu", "org.agent.reactive")
# Phase 3.3 : travail et communication (toujours des événements du même registre chaîné)
TYPES_TRAVAIL = ("mission.attribuee", "mission.livrable", "mission.validee", "mission.correction", "mission.remontee",
                 "message.envoye", "reunion.ouverte", "reunion.close")
IDENT = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")


class ErreurOrganisation(ile.ErreurIle):
    pass


# ------------------------------------------------------------------ projection
def entreprises_du_cadastre() -> dict:
    """Les entreprises sont les maisons et institutions du cadastre (registre.json), pas une liste parallèle."""
    out = {}
    for b in ile.registre().get("batiments", []):
        if b.get("type") in ("maison", "mairie", "conseil", "forge", "residence"):
            out[b["id"]] = {"id": b["id"], "nom": b.get("nom", b["id"]), "type": "projet" if b["type"] == "maison" else "institution",
                            "role": b.get("role"), "couleur": b.get("couleur"), "dossier": b.get("dossier"), "batiment": b["id"]}
    return out


def projeter(evs: list, p: dict = None) -> dict:
    """État organisationnel à partir des événements (et de la projection générale `p` pour les exécutions)."""
    p = p or ile.projeter(evs)
    ents = entreprises_du_cadastre()
    deps, postes, agents, histo = {}, {}, {}, []
    for ev in evs:
        t, d = ev["type"], ev["donnees"]
        if t not in TYPES_ORG or any(r["id"] == ev["id"] for r in p["rejets"]):
            continue
        trace = {"evenement": ev["id"], "quand": ev["quand"], "type": t, "auteur": ev.get("auteur")}
        if t == "org.departement.cree":
            deps[d["id"]] = {**{k: d.get(k) for k in ("id", "entreprise", "nom", "mission")}, "cree": trace}
        elif t == "org.poste.cree":
            postes[d["id"]] = {**{k: d.get(k) for k in ("id", "entreprise", "departement", "fonction", "titre", "superieur", "competences", "description")},
                               "titulaire": None, "cree": trace}
        elif t == "org.agent.cree":
            agents[d["id"]] = {**{k: d.get(k) for k in ("id", "nom", "definition", "competences", "description", "apparence")},
                               "poste": None, "suspendu": None, "cree": trace, "historique": []}
            if d.get("poste") in postes:
                _affecter(agents, postes, d["id"], d["poste"])
        elif t == "org.agent.affecte" and d.get("agent") in agents and d.get("poste") in postes:
            _affecter(agents, postes, d["agent"], d["poste"])
        elif t == "org.agent.suspendu" and d.get("agent") in agents:
            agents[d["agent"]]["suspendu"] = {"motif": d.get("motif"), **trace}
        elif t == "org.agent.reactive" and d.get("agent") in agents:
            agents[d["agent"]]["suspendu"] = None
        if d.get("agent") in agents:
            agents[d["agent"]]["historique"].append(trace)
        elif t == "org.agent.cree":
            agents[d["id"]]["historique"].append(trace)
        histo.append({**trace, "entreprise": d.get("entreprise") or (postes.get(d.get("poste")) or {}).get("entreprise")})
    travail = _projeter_travail(evs, p, agents, postes)
    runs_actifs = {r["role"]: r for r in p["runs_actifs"]}
    for a in agents.values():
        a.update(_statut(a, runs_actifs, travail))
        a["missions"] = [m for m in travail["missions"].values() if m.get("attributaire") == a["id"]]
        fin = [m for m in a["missions"] if m["statut"] == "terminee"]
        a["performance"] = {   # faits comptés, jamais estimés
            "missions_attribuees": len(a["missions"]), "missions_terminees": len(fin),
            "corrections_demandees": sum(m["corrections"] for m in a["missions"]),
            "livrees_dans_les_delais": sum(1 for m in fin if m.get("echeance") and m.get("livree") and m["livree"][:10] <= m["echeance"]),
            "avec_echeance": sum(1 for m in fin if m.get("echeance")), "nature": "comptage d'événements du registre"}
        po = postes.get(a["poste"]) or {}
        a["entreprise"], a["departement"], a["fonction"] = po.get("entreprise"), po.get("departement"), po.get("fonction")
        a["superieur"] = _titulaire(postes, po.get("superieur"))
    for po in postes.values():
        f = FONCTIONS.get(po["fonction"], {})
        po["niveau"], po["famille"] = f.get("niveau"), f.get("famille")
    for e in ents.values():
        e["departements"] = [x for x in deps.values() if x["entreprise"] == e["id"]]
        e["postes"] = [x for x in postes.values() if x["entreprise"] == e["id"]]
        e["agents"] = [a for a in agents.values() if a["entreprise"] == e["id"]]
        tete = [x for x in e["postes"] if not x["superieur"] or (postes.get(x["superieur"]) or {}).get("entreprise") != e["id"]]
        niv = lambda x: FONCTIONS.get(x["fonction"], {}).get("niveau", 9)
        hauts = [x for x in tete if niv(x) == min(map(niv, tete))] if tete else []
        dir_ = hauts[0] if len(hauts) == 1 else None          # plusieurs têtes au même niveau : direction collégiale
        e["direction"] = "collégiale" if len(hauts) > 1 else ("unique" if dir_ else "aucune")
        e["directeur"] = {"poste": dir_["id"], "titre": dir_["titre"], "agent": dir_["titulaire"]} if dir_ else None
        e["effectif"] = len(e["agents"])
        e["postes_non_pourvus"] = len([x for x in e["postes"] if not x["titulaire"]])
        e["agents_en_execution"] = len([a for a in e["agents"] if a["statut"] == "en_execution"])
    for e in ents.values():
        ms = [m for m in travail["missions"].values() if m["siege"] == e["id"]]
        e["missions"] = {k: len([m for m in ms if m["statut"] in v]) for k, v in
                         {"en_cours": ("planifiee", "en_cours", "verification"), "bloquees": ("bloquee",), "terminees": ("terminee",), "proposees": ("proposee", "attente_president", "reportee")}.items()}
        e["problemes_ouverts"] = len([x for x in p["problemes"].values() if x["siege"] == e["id"] and x["ouvert"]])
        e["activite_recente"] = [h for h in travail["activite"] if h.get("entreprise") == e["id"]][:15]
    return {"entreprises": ents, "departements": deps, "postes": postes, "agents": agents, "historique": histo[-200:][::-1],
            "missions": travail["missions"], "messages": travail["messages"][-300:][::-1], "reunions": travail["reunions"], "activite": travail["activite"][:200],
            "fonctions": {k: {**v, "permissions": sorted(v["permissions"])} for k, v in FONCTIONS.items()}}


def _affecter(agents, postes, aid, pid):
    ancien = agents[aid]["poste"]
    if ancien in postes and postes[ancien]["titulaire"] == aid:
        postes[ancien]["titulaire"] = None
    if postes[pid]["titulaire"] and postes[pid]["titulaire"] in agents:
        agents[postes[pid]["titulaire"]]["poste"] = None
    postes[pid]["titulaire"] = aid
    agents[aid]["poste"] = pid


def _titulaire(postes, pid):
    return (postes.get(pid) or {}).get("titulaire") if pid else None


def _projeter_travail(evs, p, agents, postes=None):
    """Missions (avec attribution, livrables, validations), messages et réunions, d'après le journal."""
    missions = {k: {**m, "attributaire": None, "attribuee_par": None, "echeance": None, "priorite_travail": None,
                    "livrables": [], "corrections": 0, "validee": None, "remontees": [], "livree": None} for k, m in p["missions"].items()}
    messages, reunions, activite = [], {}, []
    for ev in evs:
        t, d, q = ev["type"], ev["donnees"], ev["quand"]
        if t not in TYPES_TRAVAIL and t != "mission.statut":
            continue
        m = missions.get(d.get("mission"))
        trace = {"evenement": ev["id"], "quand": q, "type": t, "auteur": (ev.get("auteur") or {}).get("role"), "verifie": (ev.get("auteur") or {}).get("verifie"),
                 "entreprise": (m or {}).get("siege") or d.get("entreprise"), "mission": d.get("mission"), "agent": d.get("agent")}
        if t == "mission.attribuee" and m:
            m.update(attributaire=d["agent"], attribuee_par=d.get("par"), echeance=d.get("echeance"), priorite_travail=d.get("priorite"))
        elif t == "mission.livrable" and m:
            m["livrables"].append({"chemin": d["chemin"], "sha256": d["sha256"], "note": d.get("note"), "evenement": ev["id"], "quand": q, "par": d.get("agent")})
            m["livree"] = q
        elif t == "mission.validee" and m:
            m["validee"] = {"par": d.get("par"), "motif": d.get("motif"), "evenement": ev["id"], "quand": q}
        elif t == "mission.correction" and m:
            m["corrections"] += 1
        elif t == "mission.remontee" and m:
            m["remontees"].append({"de": d.get("de"), "vers": d.get("vers"), "motif": d.get("motif"), "evenement": ev["id"], "quand": q})
        elif t == "message.envoye":
            messages.append({"id": ev["id"], "quand": q, **{k: d.get(k) for k in ("de", "a", "sujet", "texte", "mission", "nature")}, "verifie": trace["verifie"]})
            # entreprise du message : celle de la mission, sinon celle du poste de l'expéditeur (lue au registre, jamais devinée)
            trace["entreprise"] = trace["entreprise"] or ((postes or {}).get((agents.get(d.get("de")) or {}).get("poste")) or {}).get("entreprise")
        elif t == "reunion.ouverte":
            reunions[d["id"]] = {"id": d["id"], "entreprise": d.get("entreprise"), "objet": d.get("objet"), "participants": d.get("participants", []),
                                 "par": d.get("par"), "ouverte": q, "close": None, "compte_rendu": None}
        elif t == "reunion.close" and d.get("id") in reunions:
            reunions[d["id"]].update(close=q, compte_rendu=d.get("compte_rendu"))
        activite.append(trace)
    return {"missions": missions, "messages": messages, "reunions": reunions, "activite": activite[::-1]}


def _statut(a: dict, runs_actifs: dict, travail: dict = None) -> dict:
    """Statut DÉRIVÉ, avec sa preuve. Jamais « actif » sans exécution réelle ouverte par un hook."""
    travail = travail or {"missions": {}, "reunions": {}}
    if a["suspendu"]:
        return {"statut": "suspendu", "preuve": a["suspendu"]["evenement"], "nature": "administratif"}
    r = runs_actifs.get(a.get("definition") or "")
    reu = next((x for x in travail["reunions"].values() if x["close"] is None and a["id"] in x["participants"]), None)
    if r and reu:   # en réunion seulement si la réunion est ouverte ET l'agent a une exécution réelle en cours
        return {"statut": "en_reunion", "preuve": f"{reu['id']} + {r['run']}", "nature": "présence technique + réunion inscrite au registre", "depuis": reu["ouverte"]}
    mine = [m for m in travail["missions"].values() if m.get("attributaire") == a["id"]]
    if r:
        return {"statut": "en_execution", "preuve": r["run"], "nature": "présence technique (exécution ouverte par un hook)", "depuis": r["debut"]}
    att = next((m for m in mine if m["statut"] == "verification"), None)
    if att:
        return {"statut": "en_attente_validation", "preuve": att["livrables"][-1]["evenement"] if att["livrables"] else att["id"], "nature": "livrable transmis, validation attendue", "mission": att["id"]}
    bl = next((m for m in mine if m["statut"] == "bloquee"), None)
    if bl:
        return {"statut": "bloque", "preuve": bl["id"], "nature": "mission bloquée inscrite au registre", "mission": bl["id"]}
    if a.get("definition") and (DEFINITIONS / f"{a['definition']}.md").exists():
        return {"statut": "disponible", "preuve": f"agents/definitions/{a['definition']}.md", "nature": "capacité d'exécution, aucune exécution en cours"}
    if a["id"] == "maire":
        return {"statut": "hors_ligne", "preuve": None, "nature": "session principale de Claude Code : aucune exécution tracée par les hooks"}
    return {"statut": "hors_ligne", "preuve": None, "nature": "aucune capacité d'exécution (pas de définition d'agent)"}


def etat() -> dict:
    evs = ile.lire()
    return projeter(evs, ile.projeter(evs))


# ------------------------------------------------------------------ autorisation
def _poste_de_auteur(org: dict, auteur: dict):
    """Poste occupé par l'auteur, si son identité est VÉRIFIÉE (exécution ouverte du même rôle)."""
    if auteur.get("verifie") != "run":
        return None
    for a in org["agents"].values():
        if a.get("definition") == auteur.get("role") and a["poste"] and not a["suspendu"]:
            return org["postes"][a["poste"]]
    return None


def _sous(org, pid_haut, pid):
    """Vrai si le poste `pid` est (strictement ou non) placé sous `pid_haut` dans la chaîne des supérieurs."""
    vus = set()
    while pid and pid not in vus:
        if pid == pid_haut:
            return True
        vus.add(pid)
        pid = (org["postes"].get(pid) or {}).get("superieur")
    return False


def autoriser(org: dict, auteur: dict, permission: str, poste_cible=None, entreprise=None, strict=True) -> str:
    """Renvoie le motif de l'autorisation, ou lève ErreurOrganisation. Président (signé) et DG de l'île : tout."""
    if auteur.get("role") == "president" and auteur.get("verifie") == "signature":
        return "acte présidentiel signé"
    if auteur.get("role") == "maire":
        return "directeur général de l'île (identité déclarée)"
    po = _poste_de_auteur(org, auteur)
    if po is None:
        raise ErreurOrganisation(f"« {auteur.get('role')} » n'a pas d'identité vérifiée (exécution ouverte --run) ou n'occupe aucun poste : action refusée")
    if permission not in FONCTIONS[po["fonction"]]["permissions"]:
        raise ErreurOrganisation(f"la fonction « {po['titre']} » n'a pas la permission « {permission} »")
    if entreprise and po["entreprise"] != entreprise:
        raise ErreurOrganisation(f"« {po['titre']} » de {po['entreprise']} ne peut pas agir dans l'entreprise {entreprise}")
    if poste_cible:
        if not _sous(org, po["id"], poste_cible) or (strict and poste_cible == po["id"]):
            raise ErreurOrganisation(f"le poste {poste_cible} n'est pas placé sous « {po['titre']} » dans la hiérarchie")
    return f"poste {po['id']} ({po['titre']})"


def _verif(auteur, permission, **kw):
    """`completer` d'ile.ajouter : contrôle exécuté SOUS LE VERROU, sur la projection à jour du journal."""
    def controle(evs):
        org = projeter(evs, ile.projeter(evs))
        kw.get("avant", lambda o: None)(org)
        motif = autoriser(org, auteur, permission, kw.get("poste"), kw.get("entreprise"), kw.get("strict", True))
        return {"autorisation": motif}
    return controle


def _id(x, quoi):
    if not x or not IDENT.match(x):
        raise ErreurOrganisation(f"identifiant de {quoi} invalide : {x!r} (minuscules, chiffres, tirets, 2 à 48 caractères)")
    return x


def _auteur_effectif(auteur, cle):
    if cle is not None:
        ile._cle_requise(cle)
        return {"role": "president", "verifie": "signature"}
    return auteur


# ------------------------------------------------------------------ écritures
def creer_departement(entreprise, did, nom, mission, auteur, cle=None):
    _id(did, "département")
    if entreprise not in entreprises_du_cadastre():
        raise ErreurOrganisation(f"entreprise inconnue au cadastre : {entreprise}")

    def avant(org):
        if did in org["departements"]:
            raise ErreurOrganisation(f"département déjà existant : {did}")
    return ile.ajouter("org.departement.cree", {"id": did, "entreprise": entreprise, "nom": nom, "mission": mission}, auteur,
                       completer=_verif(_auteur_effectif(auteur, cle), "creer_departement", entreprise=entreprise, avant=avant), cle=cle)


def creer_poste(entreprise, pid, fonction, superieur, auteur, departement=None, titre=None, competences=(), description=None, cle=None):
    _id(pid, "poste")
    if fonction not in FONCTIONS:
        raise ErreurOrganisation(f"fonction inconnue : {fonction} (voir « ile.py org fonctions »)")
    if entreprise not in entreprises_du_cadastre():
        raise ErreurOrganisation(f"entreprise inconnue au cadastre : {entreprise}")

    def avant(org):
        if pid in org["postes"]:
            raise ErreurOrganisation(f"poste déjà existant : {pid}")
        if superieur and superieur not in org["postes"]:
            raise ErreurOrganisation(f"poste supérieur inconnu : {superieur}")
        if departement and (org["departements"].get(departement) or {}).get("entreprise") != entreprise:
            raise ErreurOrganisation(f"département {departement} inconnu dans {entreprise}")
        if superieur and FONCTIONS[fonction]["niveau"] <= FONCTIONS[org["postes"][superieur]["fonction"]]["niveau"]:
            raise ErreurOrganisation("un poste doit être d'un niveau inférieur à celui de son supérieur")
    eff = _auteur_effectif(auteur, cle)
    perm = "creer_poste"
    return ile.ajouter("org.poste.cree", {"id": pid, "entreprise": entreprise, "departement": departement, "fonction": fonction,
                                          "titre": titre or FONCTIONS[fonction]["titre"], "superieur": superieur,
                                          "competences": list(competences), "description": description}, auteur,
                       completer=_verif(eff, perm, entreprise=entreprise, poste=superieur, strict=False, avant=avant)
                       if superieur else _verif(eff, "creer_departement", entreprise=entreprise, avant=avant), cle=cle)


def creer_agent(aid, nom, poste, auteur, definition=None, competences=(), description=None, cle=None):
    _id(aid, "agent")
    if definition and not (DEFINITIONS / f"{definition}.md").exists():
        raise ErreurOrganisation(f"définition d'agent introuvable : agents/definitions/{definition}.md")

    def avant(org):
        if aid in org["agents"]:
            raise ErreurOrganisation(f"agent déjà existant : {aid}")
        if poste not in org["postes"]:
            raise ErreurOrganisation(f"poste inconnu : {poste}")
        if org["postes"][poste]["titulaire"]:
            raise ErreurOrganisation(f"poste déjà pourvu : {poste}")
        if definition and any(a.get("definition") == definition for a in org["agents"].values()):
            raise ErreurOrganisation(f"la définition {definition} incarne déjà un agent")
    apparence = {"graine": hashlib.sha256(aid.encode()).hexdigest()[:16], "avatar": None}   # phase 4 : identité visuelle stable
    org0 = etat()
    entreprise = (org0["postes"].get(poste) or {}).get("entreprise")
    return ile.ajouter("org.agent.cree", {"id": aid, "nom": nom, "poste": poste, "definition": definition, "competences": list(competences),
                                          "description": description, "apparence": apparence}, auteur,
                       completer=_verif(_auteur_effectif(auteur, cle), "nommer_agent", entreprise=entreprise, poste=poste, avant=avant), cle=cle)


def _agir_sur_agent(type_, aid, permission, auteur, motif=None, cle=None, poste=None):
    org0 = etat()
    a = org0["agents"].get(aid)
    if not a:
        raise ErreurOrganisation(f"agent inconnu : {aid}")
    cible = poste or a["poste"]

    def avant(org):
        if type_ == "org.agent.suspendu" and org["agents"][aid]["suspendu"]:
            raise ErreurOrganisation(f"agent déjà suspendu : {aid}")
        if type_ == "org.agent.reactive" and not org["agents"][aid]["suspendu"]:
            raise ErreurOrganisation(f"agent non suspendu : {aid}")
        if type_ == "org.agent.affecte" and (poste not in org["postes"] or org["postes"][poste]["titulaire"]):
            raise ErreurOrganisation(f"poste inconnu ou déjà pourvu : {poste}")
    don = {"agent": aid, "motif": motif, **({"poste": poste} if poste else {})}
    return ile.ajouter(type_, don, auteur, completer=_verif(_auteur_effectif(auteur, cle), permission,
                                                              entreprise=(org0["postes"].get(cible) or {}).get("entreprise"), poste=cible, avant=avant), cle=cle)


def affecter_agent(aid, poste, auteur, motif=None, cle=None):
    return _agir_sur_agent("org.agent.affecte", aid, "nommer_agent", auteur, motif, cle, poste=poste)


def suspendre_agent(aid, motif, auteur, cle=None):
    return _agir_sur_agent("org.agent.suspendu", aid, "suspendre_agent", auteur, motif, cle)


def reactiver_agent(aid, motif, auteur, cle=None):
    return _agir_sur_agent("org.agent.reactive", aid, "suspendre_agent", auteur, motif, cle)


# ------------------------------------------------------------------ organisation de départ (faits existants seulement)
def plan_amorce() -> list:
    """L'organisation qui EXISTE déjà : chaque maison a un directeur (son chef, agent réel) ; le Conseil, la Forge et la
    Mairie gardent leurs agents réels. Aucun poste vacant ni agent inventé."""
    plan, ents = [], entreprises_du_cadastre()
    plan.append(("poste", "mairie", "dg-ile", "dg-ile", None, "Maire — directeur général de l'île"))
    plan.append(("agent", "maire", "Le Maire", "dg-ile", None))
    plan.append(("poste", "mairie", "architecte", "architecte-logiciel", "dg-ile", "Architecte de l'île"))
    plan.append(("agent", "architecte", "L'Architecte", "architecte", "architecte"))
    plan.append(("poste", "forge", "forge-direction", "responsable-qualite", "dg-ile", "Forgeron — responsable qualité"))
    plan.append(("agent", "forgeron", "Le Forgeron", "forge-direction", "forgeron"))
    for c, nom in (("critique-clarte", "Critique de la clarté"), ("critique-exigence", "Critique de l'exigence"), ("critique-strategie", "Critique de la stratégie")):
        plan.append(("poste", "conseil", f"conseil-{c.split('-')[1]}", "auditeur", "dg-ile", nom))
        plan.append(("agent", c, nom, f"conseil-{c.split('-')[1]}", c))
    for b in ile.registre().get("batiments", []):
        if b.get("type") == "maison" and b["id"] in ents:
            role = Path(b.get("agent", "")).stem
            if (DEFINITIONS / f"{role}.md").exists():
                plan.append(("poste", b["id"], f"{b['id']}-direction", "directeur-general", "dg-ile", f"Directeur général — {b.get('nom', b['id'])}"))
                plan.append(("agent", role, f"Directeur {b.get('nom', b['id'])}", f"{b['id']}-direction", role))
    return plan


def amorcer(auteur) -> list:
    """Inscrit l'organisation de départ (idempotent : ce qui existe déjà est sauté). Réservé au DG de l'île ou au président."""
    if auteur.get("role") != "maire":
        raise ErreurOrganisation("l'organisation de départ est inscrite par le DG de l'île (le Maire)")
    faits, org = [], etat()
    for item in plan_amorce():
        if item[0] == "poste" and item[2] not in org["postes"]:
            faits.append(creer_poste(item[1], item[2], item[3], item[4], auteur, titre=item[5]))
        elif item[0] == "agent" and item[1] not in org["agents"]:
            faits.append(creer_agent(item[1], item[2], item[3], auteur, definition=item[4]))
        org = etat()
    return faits


# ------------------------------------------------------------------ travail : missions, livrables, validation, communication
def _agent_de_auteur(org, auteur):
    """Agent incarné par l'auteur VÉRIFIÉ (exécution ouverte de sa définition), ou None."""
    if auteur.get("verifie") != "run":
        return None
    return next((a for a in org["agents"].values() if a.get("definition") == auteur.get("role") and not a["suspendu"]), None)


def _ctl(fn):
    def controle(evs):
        org = projeter(evs, ile.projeter(evs))
        return fn(org) or {}
    return controle


def _sup_de(org, agent_id):
    po = org["postes"].get((org["agents"].get(agent_id) or {}).get("poste"))
    return _titulaire(org["postes"], po.get("superieur")) if po else None


def attribuer_mission(mission, agent_id, auteur, echeance=None, priorite=None, cle=None):
    """Un supérieur (poste au-dessus de celui de l'agent, avec la permission) confie une mission planifiée ou en cours."""
    if echeance and not re.match(r"^\d{4}-\d{2}-\d{2}$", echeance):
        raise ErreurOrganisation("échéance au format AAAA-MM-JJ")
    if priorite and priorite not in ("P1", "P2", "P3"):
        raise ErreurOrganisation("priorité : P1, P2 ou P3")
    eff = _auteur_effectif(auteur, cle)

    def c(org):
        m, a = org["missions"].get(mission), org["agents"].get(agent_id)
        if not m:
            raise ErreurOrganisation(f"mission inconnue : {mission}")
        if not a or a["suspendu"]:
            raise ErreurOrganisation(f"agent inconnu ou suspendu : {agent_id}")
        if m["statut"] not in ("planifiee", "en_cours", "bloquee"):
            raise ErreurOrganisation(f"mission {mission} au statut « {m['statut']} » : seule une mission planifiée (retenue) s'attribue")
        motif = autoriser(org, eff, "attribuer_mission", a["poste"], a["entreprise"])
        par = (_agent_de_auteur(org, eff) or {}).get("id") or eff.get("role")
        return {"autorisation": motif, "par": par}
    return ile.ajouter("mission.attribuee", {"mission": mission, "agent": agent_id, "echeance": echeance, "priorite": priorite}, auteur, completer=_ctl(c), cle=cle)


def _attributaire_verifie(org, auteur, mission, statuts):
    m = org["missions"].get(mission)
    if not m:
        raise ErreurOrganisation(f"mission inconnue : {mission}")
    a = _agent_de_auteur(org, auteur)
    if not a or m.get("attributaire") != a["id"]:
        raise ErreurOrganisation("seul l'agent attributaire, pendant son exécution vérifiée (--run), peut agir sur cette mission")
    if m["statut"] not in statuts:
        raise ErreurOrganisation(f"mission au statut « {m['statut']} » (attendu : {', '.join(statuts)})")
    return m, a


def _statut_mission(mission, siege, de, vers, auteur, motif=None, cle=None):
    return ile.ajouter("mission.statut", {"mission": mission, "siege": siege, "de": de, "vers": vers, "motif": motif}, auteur, cle=cle)


def demarrer_mission(mission, auteur):
    """L'attributaire commence (planifiée → en cours) : preuve = son exécution ouverte."""
    def c(org):
        m, a = _attributaire_verifie(org, auteur, mission, ("planifiee",))
        return {"de": "planifiee", "vers": "en_cours", "motif": f"démarrée par {a['id']} ({auteur.get('run')})", "mission": mission, "siege": m["siege"]}
    m = etat()["missions"].get(mission) or {}
    return ile.ajouter("mission.statut", {"mission": mission, "siege": m.get("siege")}, auteur, completer=_ctl(c))


def livrer(mission, chemin, auteur, note=None):
    """L'attributaire transmet un livrable (document du dépôt, gelé par son empreinte) ; la mission passe en vérification."""
    pth = (ile.RACINE / chemin).resolve()
    if ile.RACINE not in pth.parents or not pth.is_file():
        raise ErreurOrganisation(f"livrable introuvable dans l'île : {chemin}")
    rel = str(pth.relative_to(ile.RACINE))

    def c(org):
        m, a = _attributaire_verifie(org, auteur, mission, ("en_cours",))
        return {"agent": a["id"], "siege": m["siege"]}
    ev = ile.ajouter("mission.livrable", {"mission": mission, "chemin": rel, "sha256": ile._sha_fichier(pth), "note": note}, auteur, completer=_ctl(c))
    _statut_mission(mission, ev["donnees"]["siege"], "en_cours", "verification", auteur, f"livrable {ev['id']}")
    return ev


def _superieur_controle(org, auteur, mission, cle):
    m = org["missions"].get(mission)
    if not m or not m.get("attributaire"):
        raise ErreurOrganisation(f"mission inconnue ou non attribuée : {mission}")
    if m["statut"] != "verification" or not m["livrables"]:
        raise ErreurOrganisation("aucun livrable en attente de validation pour cette mission")
    a = org["agents"][m["attributaire"]]
    eff = _auteur_effectif(auteur, cle)
    if (_agent_de_auteur(org, eff) or {}).get("id") == a["id"]:
        raise ErreurOrganisation("un agent ne valide pas son propre livrable")
    motif = autoriser(org, eff, "valider_livrable", a["poste"], a["entreprise"])
    # le document livré ne doit pas avoir changé depuis sa transmission
    l = m["livrables"][-1]
    pth = ile.RACINE / l["chemin"]
    if not pth.is_file() or ile._sha_fichier(pth) != l["sha256"]:
        raise ErreurOrganisation(f"le livrable {l['chemin']} a changé ou disparu depuis sa transmission")
    return m, motif, (_agent_de_auteur(org, eff) or {}).get("id") or eff.get("role")


def valider(mission, auteur, motif=None, cle=None):
    """Le supérieur valide : vérification → terminée (archivée)."""
    def c(org):
        m, aut, par = _superieur_controle(org, _auteur_effectif(auteur, cle), mission, cle)
        return {"autorisation": aut, "par": par, "siege": m["siege"]}
    ev = ile.ajouter("mission.validee", {"mission": mission, "motif": motif}, auteur, completer=_ctl(c), cle=cle)
    _statut_mission(mission, ev["donnees"]["siege"], "verification", "terminee", auteur, f"validée ({ev['id']})", cle=cle)
    return ev


def demander_correction(mission, motif, auteur, cle=None):
    """Le supérieur refuse le livrable et demande une correction : vérification → en cours."""
    if not motif:
        raise ErreurOrganisation("une demande de correction exige un motif")

    def c(org):
        m, aut, par = _superieur_controle(org, _auteur_effectif(auteur, cle), mission, cle)
        return {"autorisation": aut, "par": par, "siege": m["siege"]}
    ev = ile.ajouter("mission.correction", {"mission": mission, "motif": motif}, auteur, completer=_ctl(c), cle=cle)
    _statut_mission(mission, ev["donnees"]["siege"], "verification", "en_cours", auteur, f"correction ({ev['id']})", cle=cle)
    return ev


def remonter(mission, motif, auteur, bloquer=False):
    """Un agent ou un manager fait remonter un problème ou une décision à son supérieur (et peut bloquer la mission)."""
    def c(org):
        m = org["missions"].get(mission)
        a = _agent_de_auteur(org, auteur)
        if not m or not a:
            raise ErreurOrganisation("remontée : mission inconnue ou identité non vérifiée (--run)")
        if m.get("attributaire") != a["id"] and not _sous(org, a["poste"], org["agents"].get(m.get("attributaire") or "", {}).get("poste")):
            raise ErreurOrganisation("on ne fait remonter que ses propres missions ou celles de son équipe")
        sup = _sup_de(org, a["id"])
        if not sup:
            raise ErreurOrganisation("aucun supérieur au-dessus de ce poste")
        return {"de": a["id"], "vers": sup, "siege": m["siege"], "statut_avant": m["statut"]}
    ev = ile.ajouter("mission.remontee", {"mission": mission, "motif": motif}, auteur, completer=_ctl(c))
    if bloquer and ev["donnees"]["statut_avant"] == "en_cours":
        _statut_mission(mission, ev["donnees"]["siege"], "en_cours", "bloquee", auteur, f"remontée {ev['id']}")
    return ev


def envoyer_message(destinataire, sujet, texte, auteur, mission=None, nature="message", cle=None):
    """Communication interne historisée : de l'agent vérifié (ou DG / président) vers un agent, un poste ou un département."""
    if not texte or len(texte) > 4000:
        raise ErreurOrganisation("message vide ou trop long (4000 caractères au plus)")
    eff = _auteur_effectif(auteur, cle)

    def c(org):
        if not (destinataire in org["agents"] or destinataire in org["postes"] or destinataire in org["departements"]):
            raise ErreurOrganisation(f"destinataire inconnu : {destinataire}")
        if eff.get("role") == "president" or eff.get("role") == "maire":
            de = eff["role"]
        else:
            a = _agent_de_auteur(org, eff)
            if not a:
                raise ErreurOrganisation("un message part d'une identité vérifiée (--run)")
            de = a["id"]
        return {"de": de}
    return ile.ajouter("message.envoye", {"a": destinataire, "sujet": sujet, "texte": texte, "mission": mission, "nature": nature}, auteur, completer=_ctl(c), cle=cle)


def ouvrir_reunion(rid, entreprise, objet, participants, auteur):
    _id(rid, "réunion")

    def c(org):
        if rid in org["reunions"]:
            raise ErreurOrganisation(f"réunion déjà existante : {rid}")
        inconnus = [x for x in participants if x not in org["agents"]]
        if inconnus or not participants:
            raise ErreurOrganisation(f"participants inconnus : {', '.join(inconnus) or '(aucun)'}")
        a = _agent_de_auteur(org, auteur)
        if auteur.get("role") != "maire" and not a:
            raise ErreurOrganisation("une réunion est ouverte par une identité vérifiée (--run) ou par le DG")
        return {"par": (a or {}).get("id") or auteur.get("role")}
    return ile.ajouter("reunion.ouverte", {"id": rid, "entreprise": entreprise, "objet": objet, "participants": list(participants)}, auteur, completer=_ctl(c))


def clore_reunion(rid, compte_rendu, auteur):
    def c(org):
        r = org["reunions"].get(rid)
        if not r or r["close"]:
            raise ErreurOrganisation(f"réunion inconnue ou déjà close : {rid}")
        a = _agent_de_auteur(org, auteur)
        if auteur.get("role") != "maire" and (not a or a["id"] != r["par"]):
            raise ErreurOrganisation("seul l'organisateur (ou le DG) clôt la réunion")
        return {}
    return ile.ajouter("reunion.close", {"id": rid, "compte_rendu": compte_rendu}, auteur, completer=_ctl(c))
