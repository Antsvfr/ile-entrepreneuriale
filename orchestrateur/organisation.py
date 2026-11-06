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
    runs_actifs = {r["role"]: r for r in p["runs_actifs"]}
    for a in agents.values():
        a.update(_statut(a, runs_actifs))
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
    return {"entreprises": ents, "departements": deps, "postes": postes, "agents": agents, "historique": histo[-200:][::-1],
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


def _statut(a: dict, runs_actifs: dict) -> dict:
    """Statut DÉRIVÉ, avec sa preuve. Jamais « actif » sans exécution réelle ouverte par un hook."""
    if a["suspendu"]:
        return {"statut": "suspendu", "preuve": a["suspendu"]["evenement"], "nature": "administratif"}
    r = runs_actifs.get(a.get("definition") or "")
    if r:
        return {"statut": "en_execution", "preuve": r["run"], "nature": "présence technique (exécution ouverte par un hook)", "depuis": r["debut"]}
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
