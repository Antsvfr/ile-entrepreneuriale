"""Propositions soumises à l'autorité présidentielle : circuit institutionnel complet.

Une proposition est un dossier (titre, description, objectif, conséquences, coût, risques, pièces, institutions
concernées) qui suit son propre cycle de vie, entièrement inscrit au registre chaîné (aucune autre base) :

  créée → soumise → (transmise pour analyse · avis demandés / rendus) → en attente de décision
        → approuvée | refusée | modifications demandées (→ modifiée → resoumise)
  approuvée → mise en œuvre définie → exécution commencée → exécution terminée (résultats au président)

Opérations DISTINCTES, à ne pas confondre :
  - la validation d'un livrable ou d'une mission par un supérieur (organisation.py) ;
  - l'avis du Conseil des critiques (ou de la Forge, d'un directeur) : un AVIS, jamais une décision ;
  - la décision présidentielle (approuver, refuser, demander des modifications) : acte SIGNÉ de la clé du président ;
  - la publication et la transmission aux institutions : dérivées de la décision signée (destinataires inscrits).

Garanties :
  - les décisions sont des types présidentiels (ile.TYPES_PRESIDENTIELS) : sans signature valide de la clé en
    vigueur, l'événement est rejeté par la projection et signalé par « ile.py verifier » (journal non intègre) ;
  - elles exigent en plus l'activation explicite des décisions officielles par le président (acte signé) ;
  - une décision prise ne se modifie pas : une seconde décision est refusée ; toute correction passe par une
    rectification signée et motivée, nouvel événement qui laisse l'ancien en place ;
  - un avis favorable n'approuve rien, un avis défavorable ne refuse rien ;
  - chaque contrôle est fait SOUS LE VERROU du journal, sur la projection à jour (`completer` d'ile.ajouter) ;
  - la décision porte l'empreinte de la version du dossier examinée : si le dossier a changé, elle est refusée.
"""
import hashlib
import json
import re
import sys

if sys.modules.get("confinement") is not None:
    ile = sys.modules["confinement"].charger("ile")
    org = sys.modules["confinement"].charger("organisation")
else:
    import ile  # noqa: E402
    import organisation as org  # noqa: E402

TYPES = ("proposition.creee", "proposition.soumise", "proposition.modifiee", "proposition.transmise", "proposition.avis_demande",
         "proposition.avis_rendu", "proposition.mise_en_oeuvre", "proposition.execution", "proposition.reception", "proposition.archivee")
TYPES_DECISION = ("proposition.approuvee", "proposition.refusee", "proposition.modifications_demandees", "proposition.rectifiee")
ACTIVATION = "presidence.decisions_activees"
CATEGORIES = ("strategie", "organisation", "budget", "projet", "securite", "partenariat", "reglement", "decision", "autre")
SENS_AVIS = ("favorable", "defavorable", "reserve")
CHAMPS = ("titre", "description", "categorie", "objectif", "consequences", "cout", "risques", "pieces", "institutions")
STATUTS = {"brouillon": "Brouillon", "soumise": "Soumise", "en_analyse": "En cours d'analyse", "en_attente_decision": "En attente de décision",
           "modifications_demandees": "Modifications demandées", "approuvee": "Approuvée", "refusee": "Refusée",
           "en_execution": "En exécution", "executee": "Exécutée"}
OUVERTS = ("soumise", "en_analyse", "en_attente_decision")          # le président peut approuver ou demander des modifications
REFUSABLES = OUVERTS + ("modifications_demandees",)
FINAUX_DECISION = ("approuvee", "refusee", "en_execution", "executee")
DECLARATION = ("J'active les décisions officielles de la Présidence. Je sais que l'étape 2 de sécurité est déclarée NON VALIDÉE "
               "(garde contournable par des commandes lisibles, agents et président sous le même utilisateur système) ; chaque "
               "décision reste un acte signé de ma clé, vérifiable par tous.")


class ErreurProposition(ile.ErreurIle):
    pass


# ------------------------------------------------------------------ projection
def version(p: dict) -> str:
    """Empreinte du contenu du dossier (ce que le président examine et signe)."""
    return hashlib.sha256(json.dumps({k: p.get(k) for k in CHAMPS}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _neuve(pid, q, auteur, ev_id, **champs):
    p = {"id": pid, "statut": "brouillon", "cree": q, "evenement": ev_id, "auteur": auteur, "origine": None, "soumise": None,
         "titre": None, "description": None, "categorie": None, "objectif": None, "consequences": None, "cout": None, "risques": [],
         "pieces": [], "institutions": [], "avis": [], "demandes_avis": [], "decision": None, "decisions": [], "rectifications": [],
         "demandes_modification": [], "transmissions": [], "mise_en_oeuvre": None, "execution": {"debut": None, "fin": None, "resultat": None},
         "receptions": [], "archivee": None, "historique": [], "ancienne": False}
    p.update(champs)
    return p


def projeter(evs: list, p_ile: dict = None) -> dict:
    """Propositions, demandes de décision antérieures (decision.demandee), activation des décisions, anomalies."""
    p_ile = p_ile if p_ile is not None else ile.projeter(evs)
    rejetes = {r["id"] for r in p_ile["rejets"]}
    props, anomalies, activation = {}, [], None

    def H(p, ev, action, **detail):
        p["historique"].append({"quand": ev["quand"], "evenement": ev["id"], "type": ev["type"], "action": action,
                                "par": (ev.get("auteur") or {}).get("role"), "verifie": (ev.get("auteur") or {}).get("verifie"), **detail})

    for ev in evs:
        if ev["id"] in rejetes:                     # acte présidentiel sans signature valide : jamais pris en compte
            continue
        t, d, q, au = ev["type"], ev["donnees"], ev["quand"], ev.get("auteur") or {}
        if t == ACTIVATION:
            activation = {"quand": q, "evenement": ev["id"], "declaration": d.get("declaration"), "cle": au.get("cle")}
            continue
        if t == "decision.demandee":                # demandes de décision antérieures : déjà adressées au président
            p = _neuve(ev["id"], q, au, ev["id"], origine=d.get("siege"), titre=d.get("titre"), categorie="decision",
                       description=d.get("question"), objectif=d.get("question"), consequences=d.get("contexte"),
                       pieces=[{"chemin": d["source"], "sha256": None}] if d.get("source") else [], institutions=[d["siege"]] if d.get("siege") else [],
                       statut="en_attente_decision", soumise=q, ancienne=True, mission=d.get("mission"))
            props[p["id"]] = p
            H(p, ev, "demande de décision inscrite (ancien format : soumise directement au président)")
            continue
        if t == "decision.tranchee" and d.get("decision") in props:
            p = props[d["decision"]]
            vers = {"approuvee": "approuvee", "refusee": "refusee"}.get(d.get("verdict"))
            if vers and p["decision"] is None:
                p["decision"] = {"sens": vers, "quand": q, "evenement": ev["id"], "motif": d.get("motif"), "par": au, "destinataires": p["institutions"]}
                p["decisions"].append(p["decision"]); p["statut"] = vers
                if vers == "refusee":
                    p["archivee"] = {"quand": q, "evenement": ev["id"], "motif": "refus archivé"}
            H(p, ev, f"décision (ancien format) : {d.get('verdict')}", motif=d.get("motif"))
            continue
        if not t.startswith("proposition."):
            continue
        if t == "proposition.creee":
            p = _neuve(d["proposition"], q, au, ev["id"], origine=d.get("origine"), **{k: d.get(k) for k in CHAMPS})
            p["risques"], p["pieces"], p["institutions"] = p["risques"] or [], p["pieces"] or [], p["institutions"] or []
            props[p["id"]] = p
            H(p, ev, "proposition créée")
            continue
        p = props.get(d.get("proposition"))
        if p is None:
            anomalies.append({"evenement": ev["id"], "motif": f"{t} vise une proposition inconnue ({d.get('proposition')})"})
            continue
        if t == "proposition.soumise":
            p["soumise"] = p["soumise"] or q
            p["statut"] = "en_attente_decision" if p["demandes_modification"] else "soumise"
            H(p, ev, "resoumise après modifications" if p["demandes_modification"] else "soumise", version=d.get("version"))
        elif t == "proposition.modifiee":
            avant = {k: p.get(k) for k in d.get("champs", {})}
            p.update(d.get("champs", {}))
            H(p, ev, "dossier modifié par son auteur", note=d.get("note"), champs=sorted(d.get("champs", {})), avant=avant)
        elif t == "proposition.transmise":
            p["transmissions"].append({"quand": q, "evenement": ev["id"], "vers": d.get("vers"), "destinataires": d.get("destinataires", []), "par": au})
            if p["statut"] in ("soumise", "en_analyse", "en_attente_decision"):
                p["statut"] = "en_attente_decision" if d.get("vers") == "president" else "en_analyse"
            H(p, ev, "transmise au président" if d.get("vers") == "president" else "transmise pour analyse", destinataires=d.get("destinataires", []))
        elif t == "proposition.avis_demande":
            p["demandes_avis"].append({"id": ev["id"], "quand": q, "destinataire": d.get("destinataire"), "question": d.get("question"),
                                       "par": au, "echeance": d.get("echeance"), "rendu": None})
            if p["statut"] in ("soumise", "en_attente_decision"):
                p["statut"] = "en_analyse"
            H(p, ev, f"avis demandé à {d.get('destinataire')}", question=d.get("question"))
        elif t == "proposition.avis_rendu":
            dem = next((x for x in p["demandes_avis"] if x["id"] == d.get("demande")), None)
            a = {"quand": q, "evenement": ev["id"], "demande": d.get("demande"), "institution": dem and dem["destinataire"], "sens": d.get("sens"), "texte": d.get("texte"), "par": au}
            p["avis"].append(a)
            if dem and dem["rendu"] is None:
                dem["rendu"] = ev["id"]
            # un avis n'est jamais une décision : le dossier revient seulement dans la boîte du président
            if p["statut"] == "en_analyse" and all(x["rendu"] for x in p["demandes_avis"]):
                p["statut"] = "en_attente_decision"
            H(p, ev, f"avis {d.get('sens')} de {a['institution']}", texte=d.get("texte"))
        elif t in ("proposition.approuvee", "proposition.refusee"):
            sens = "approuvee" if t.endswith("approuvee") else "refusee"
            if p["decision"] is not None:           # jamais d'écrasement silencieux : l'acte est ignoré ET signalé
                anomalies.append({"evenement": ev["id"], "proposition": p["id"], "motif": f"seconde décision ({sens}) ignorée : déjà {p['decision']['sens']} par {p['decision']['evenement']}"})
                H(p, ev, f"seconde décision ignorée ({sens})")
                continue
            p["decision"] = {"sens": sens, "quand": q, "evenement": ev["id"], "motif": d.get("motif"), "par": au,
                             "destinataires": d.get("destinataires", []), "version": d.get("version"), "conditions": d.get("conditions")}
            p["decisions"].append(p["decision"]); p["statut"] = sens
            if sens == "refusee":
                p["archivee"] = {"quand": q, "evenement": ev["id"], "motif": "refus archivé"}
            H(p, ev, "APPROUVÉE par le président" if sens == "approuvee" else "REFUSÉE par le président", motif=d.get("motif"), destinataires=d.get("destinataires", []))
        elif t == "proposition.modifications_demandees":
            p["demandes_modification"].append({"quand": q, "evenement": ev["id"], "observations": d.get("observations"), "attendus": d.get("attendus"), "echeance": d.get("echeance"), "par": au})
            p["statut"] = "modifications_demandees"
            H(p, ev, "modifications demandées par le président", observations=d.get("observations"), attendus=d.get("attendus"), echeance=d.get("echeance"))
        elif t == "proposition.rectifiee":
            ancienne = p["decision"]
            p["rectifications"].append({"quand": q, "evenement": ev["id"], "remplace": d.get("remplace"), "vers": d.get("vers"), "motif": d.get("motif"), "par": au})
            p["decision"] = {"sens": d.get("vers"), "quand": q, "evenement": ev["id"], "motif": d.get("motif"), "par": au,
                             "destinataires": d.get("destinataires", []), "rectifie": ancienne and ancienne["evenement"]}
            p["decisions"].append(p["decision"]); p["statut"] = d.get("vers")
            p["archivee"] = {"quand": q, "evenement": ev["id"], "motif": "refus archivé"} if d.get("vers") == "refusee" else None
            H(p, ev, f"décision rectifiée par le président → {d.get('vers')}", motif=d.get("motif"), remplace=d.get("remplace"))
        elif t == "proposition.mise_en_oeuvre":
            p["mise_en_oeuvre"] = {"quand": q, "evenement": ev["id"], **{k: d.get(k) for k in ("responsable", "modalites", "echeance", "mission")}, "par": au}
            H(p, ev, f"mise en œuvre confiée à {d.get('responsable')}", modalites=d.get("modalites"))
        elif t == "proposition.execution":
            if d.get("etape") == "debut":
                p["execution"]["debut"] = {"quand": q, "evenement": ev["id"], "par": au}
                p["statut"] = "en_execution"
                H(p, ev, "exécution commencée")
            else:
                p["execution"].update(fin={"quand": q, "evenement": ev["id"], "par": au}, resultat=d.get("resultat"))
                p["statut"] = "executee"
                H(p, ev, "exécution terminée — résultats transmis au président", resultat=d.get("resultat"))
        elif t == "proposition.reception":
            p["receptions"].append({"quand": q, "evenement": ev["id"], "institution": d.get("institution"), "par": au, "decision": d.get("decision")})
            H(p, ev, f"décision reçue par {d.get('institution')}")
        elif t == "proposition.archivee":
            p["archivee"] = {"quand": q, "evenement": ev["id"], "motif": d.get("motif")}
            H(p, ev, "archivée", motif=d.get("motif"))

    for p in props.values():
        p["version"] = version(p)
        p["libelle"] = STATUTS.get(p["statut"], p["statut"])
        p["avis_en_attente"] = [x for x in p["demandes_avis"] if not x["rendu"]]
    # boîte de réception de chaque institution : décisions qui la concernent (dérivées de l'acte signé)
    boites = {}
    for p in props.values():
        if p["decision"]:
            for inst in sorted(set(p["decision"].get("destinataires") or [])):
                boites.setdefault(inst, []).append({"proposition": p["id"], "titre": p["titre"], "sens": p["decision"]["sens"],
                                                    "quand": p["decision"]["quand"], "evenement": p["decision"]["evenement"],
                                                    "recue": any(r["institution"] == inst for r in p["receptions"])})
    return {"propositions": props, "activation": activation, "anomalies": anomalies, "boites": boites,
            "identite": bool(p_ile.get("identite")), "statuts": STATUTS, "categories": CATEGORIES}


def etat() -> dict:
    evs = ile.lire()
    return projeter(evs, ile.projeter(evs))


# ------------------------------------------------------------------ contrôles (sous le verrou)
def _texte(x, quoi, n=4000, obligatoire=True):
    x = (x or "").strip()
    if obligatoire and not x:
        raise ErreurProposition(f"{quoi} obligatoire")
    if len(x) > n:
        raise ErreurProposition(f"{quoi} trop long ({n} caractères au plus)")
    return x or None


def _institution(i):
    if i not in org.entreprises_du_cadastre():
        raise ErreurProposition(f"institution ou entreprise inconnue au cadastre : {i}")
    return i


def _agent_de(o_org, auteur):
    """Agent dont l'identité est VÉRIFIÉE par une exécution ouverte (--run), ou None."""
    if auteur.get("verifie") != "run":
        return None
    return next((a for a in o_org["agents"].values() if a.get("definition") == auteur.get("role") and not a["suspendu"]), None)


def _membre(o_org, auteur, institution):
    """Vrai si l'auteur peut parler au nom de l'institution : agent vérifié qui y travaille, ou le Maire pour la Mairie."""
    if auteur.get("role") == "maire":
        return institution == "mairie"
    a = _agent_de(o_org, auteur)
    return bool(a and a["entreprise"] == institution)


def _completer(auteur, regle):
    """`completer` d'ile.ajouter : la règle s'applique à la projection À JOUR, sous le verrou ; renvoie des champs."""
    def controle(evs):
        p_ile = ile.projeter(evs)
        etat_p = projeter(evs, p_ile)
        o_org = org.projeter(evs, p_ile)
        return regle(etat_p, o_org) or {}
    return controle


def _get(etat_p, pid):
    p = etat_p["propositions"].get(pid)
    if not p:
        raise ErreurProposition(f"proposition inconnue : {pid}")
    return p


def _president(cle):
    ile._cle_requise(cle)
    return {"role": "president", "verifie": "signature"}


def _activee(etat_p):
    if not etat_p["identite"]:
        raise ErreurProposition("aucune identité présidentielle n'est inscrite au registre : aucune décision officielle n'est possible")
    if not etat_p["activation"]:
        raise ErreurProposition("les décisions officielles ne sont pas activées : le président doit d'abord les activer (acte signé)")


# ------------------------------------------------------------------ circuit : auteurs et institutions
def creer(origine, titre, description, categorie, objectif, consequences, auteur, cout=None, risques=(), pieces=(), institutions=(), soumettre=False):
    _institution(origine)
    if categorie not in CATEGORIES:
        raise ErreurProposition(f"catégorie : {', '.join(CATEGORIES)}")
    champs = {"titre": _texte(titre, "titre", 200), "description": _texte(description, "description", 8000), "categorie": categorie,
              "objectif": _texte(objectif, "objectif", 2000), "consequences": _texte(consequences, "conséquences attendues", 4000),
              "cout": _texte(cout, "coût", 1000, obligatoire=False), "risques": [_texte(r, "risque", 1000) for r in risques],
              "pieces": [_piece(c) for c in pieces], "institutions": sorted({_institution(i) for i in institutions} | {origine})}

    def regle(etat_p, o_org):
        if auteur.get("role") == "president":
            raise ErreurProposition("le président décide des propositions ; il n'en soumet pas à lui-même")
        if auteur.get("role") != "maire" and not _membre(o_org, auteur, origine):
            raise ErreurProposition(f"« {auteur.get('role')} » ne peut pas proposer au nom de {origine} : identité vérifiée (--run) d'un agent de {origine} requise")
        n = sum(1 for k in etat_p["propositions"] if k.startswith("P-" + ile.maintenant()[:10].replace("-", ""))) + 1
        return {"proposition": f"P-{ile.maintenant()[:10].replace('-', '')}-{n:03d}"}
    ev = ile.ajouter("proposition.creee", {"origine": origine, **champs}, auteur, completer=_completer(auteur, regle))
    if soumettre:
        soumettre_(ev["donnees"]["proposition"], auteur)
    return ev


def _piece(chemin):
    chemin = (chemin or "").strip().lstrip("/")
    p = (ile.RACINE / chemin).resolve()
    if not str(p).startswith(str(ile.RACINE.resolve()) + "/") or not p.is_file():
        raise ErreurProposition(f"pièce justificative introuvable dans l'île : {chemin}")
    return {"chemin": str(p.relative_to(ile.RACINE.resolve())), "sha256": ile._sha_fichier(p)}


def _auteur_de(p, auteur):
    return (p["auteur"] or {}).get("role") == auteur.get("role") and (auteur.get("verifie") == "run" or auteur.get("role") == "maire")


def soumettre_(pid, auteur):
    def regle(etat_p, o_org):
        p = _get(etat_p, pid)
        if not _auteur_de(p, auteur):
            raise ErreurProposition("seul l'auteur de la proposition (identité vérifiée) peut la soumettre")
        if p["statut"] not in ("brouillon", "modifications_demandees"):
            raise ErreurProposition(f"proposition {pid} déjà {STATUTS[p['statut']].lower()}")
        return {"version": p["version"]}
    return ile.ajouter("proposition.soumise", {"proposition": pid}, auteur, completer=_completer(auteur, regle))


def modifier(pid, champs, note, auteur):
    champs = {k: v for k, v in champs.items() if v not in (None, [], ())}
    if not champs or set(champs) - set(CHAMPS) - {"risques", "pieces"}:
        raise ErreurProposition(f"champs modifiables : {', '.join(CHAMPS)}")
    if "pieces" in champs:
        champs["pieces"] = [_piece(c) for c in champs["pieces"]]
    if "categorie" in champs and champs["categorie"] not in CATEGORIES:
        raise ErreurProposition(f"catégorie : {', '.join(CATEGORIES)}")
    if "institutions" in champs:
        champs["institutions"] = sorted({_institution(i) for i in champs["institutions"]})

    def regle(etat_p, o_org):
        p = _get(etat_p, pid)
        if not _auteur_de(p, auteur):
            raise ErreurProposition("seul l'auteur de la proposition (identité vérifiée) peut la modifier")
        if p["statut"] not in ("brouillon", "modifications_demandees"):
            raise ErreurProposition(f"une proposition {STATUTS[p['statut']].lower()} ne se modifie pas (seulement en brouillon ou après une demande de modifications)")
    return ile.ajouter("proposition.modifiee", {"proposition": pid, "champs": champs, "note": _texte(note, "note de modification", 2000)}, auteur,
                       completer=_completer(auteur, regle))


def transmettre(pid, vers, auteur, destinataires=()):
    if vers not in ("analyse", "president"):
        raise ErreurProposition("transmettre vers : analyse ou president")
    dest = [_institution(x) for x in destinataires]

    def regle(etat_p, o_org):
        p = _get(etat_p, pid)
        if auteur.get("role") != "maire":
            raise ErreurProposition("la transmission d'un dossier relève du directeur général de l'île (le Maire)")
        if p["statut"] not in ("soumise", "en_analyse", "en_attente_decision"):
            raise ErreurProposition(f"proposition {STATUTS[p['statut']].lower()} : rien à transmettre")
    return ile.ajouter("proposition.transmise", {"proposition": pid, "vers": vers, "destinataires": dest}, auteur, completer=_completer(auteur, regle))


def demander_avis(pid, destinataire, question, auteur=None, cle=None, echeance=None, canal=None):
    _institution(destinataire)
    question = _texte(question, "question posée", 2000)
    eff = _president(cle) if cle is not None else auteur

    def regle(etat_p, o_org):
        p = _get(etat_p, pid)
        if eff.get("role") not in ("president", "maire"):
            raise ErreurProposition("seuls le président (acte signé) et le directeur général de l'île peuvent demander un avis")
        if eff.get("role") == "president":
            _activee(etat_p)
        if p["statut"] in FINAUX_DECISION:
            raise ErreurProposition(f"proposition déjà {STATUTS[p['statut']].lower()}")
    return ile.ajouter("proposition.avis_demande", {"proposition": pid, "destinataire": destinataire, "question": question, "echeance": echeance},
                       ({"canal": canal} if canal else {}) if cle is not None else auteur, completer=_completer(eff, regle), cle=cle)


def rendre_avis(pid, demande, sens, texte, auteur):
    if sens not in SENS_AVIS:
        raise ErreurProposition(f"sens de l'avis : {', '.join(SENS_AVIS)}")
    texte = _texte(texte, "texte de l'avis", 8000)

    def regle(etat_p, o_org):
        p = _get(etat_p, pid)
        dem = next((x for x in p["demandes_avis"] if x["id"] == demande), None)
        if not dem:
            raise ErreurProposition(f"aucune demande d'avis {demande} sur {pid}")
        if dem["rendu"]:
            raise ErreurProposition(f"l'avis demandé par {demande} a déjà été rendu ({dem['rendu']})")
        if not _membre(o_org, auteur, dem["destinataire"]):
            raise ErreurProposition(f"seul un membre de {dem['destinataire']} à l'identité vérifiée (--run) peut rendre cet avis")
    return ile.ajouter("proposition.avis_rendu", {"proposition": pid, "demande": demande, "sens": sens, "texte": texte}, auteur, completer=_completer(auteur, regle))


# ------------------------------------------------------------------ décisions présidentielles (actes signés)
def activer_decisions(cle, canal=None):
    """Activation explicite des décisions officielles par le président (une fois)."""
    _president(cle)

    def regle(etat_p, o_org):
        if etat_p["activation"]:
            raise ErreurProposition(f"décisions déjà activées le {etat_p['activation']['quand'][:16]} ({etat_p['activation']['evenement']})")
    return ile.ajouter(ACTIVATION, {"declaration": DECLARATION}, {"canal": canal} if canal else {}, completer=_completer({"role": "president"}, regle), cle=cle)


def _destinataires(p):
    return sorted(set(p["institutions"]) | ({p["origine"]} if p["origine"] else set()))


def approuver(pid, cle, version_examinee, motif=None, conditions=None, canal=None):
    _president(cle)

    def regle(etat_p, o_org):
        _activee(etat_p)
        p = _get(etat_p, pid)
        if p["decision"] is not None:
            raise ErreurProposition(f"{pid} est déjà {p['decision']['sens']} ({p['decision']['evenement']}) : une décision ne se modifie pas ; seule une rectification motivée est possible")
        if p["statut"] not in OUVERTS:
            raise ErreurProposition(f"{pid} est {STATUTS[p['statut']].lower()} : elle ne peut pas être approuvée dans cet état")
        if version_examinee != p["version"]:
            raise ErreurProposition("le dossier a changé depuis votre examen : rouvrez-le avant de décider")
        return {"version": p["version"], "destinataires": _destinataires(p)}
    return ile.ajouter("proposition.approuvee", {"proposition": pid, "motif": _texte(motif, "motif", 2000, obligatoire=False),
                                                 "conditions": _texte(conditions, "conditions", 2000, obligatoire=False)},
                       {"canal": canal} if canal else {}, completer=_completer({"role": "president"}, regle), cle=cle)


def refuser(pid, cle, version_examinee, motif, canal=None):
    _president(cle)
    motif = _texte(motif, "motif du refus", 2000)

    def regle(etat_p, o_org):
        _activee(etat_p)
        p = _get(etat_p, pid)
        if p["decision"] is not None:
            raise ErreurProposition(f"{pid} est déjà {p['decision']['sens']} ({p['decision']['evenement']}) : une décision ne se modifie pas ; seule une rectification motivée est possible")
        if p["statut"] not in REFUSABLES:
            raise ErreurProposition(f"{pid} est {STATUTS[p['statut']].lower()} : elle ne peut pas être refusée dans cet état")
        if version_examinee != p["version"]:
            raise ErreurProposition("le dossier a changé depuis votre examen : rouvrez-le avant de décider")
        return {"version": p["version"], "destinataires": _destinataires(p)}
    return ile.ajouter("proposition.refusee", {"proposition": pid, "motif": motif}, {"canal": canal} if canal else {},
                       completer=_completer({"role": "president"}, regle), cle=cle)


def demander_modifications(pid, cle, observations, attendus, echeance=None, canal=None):
    _president(cle)
    observations, attendus = _texte(observations, "observations", 4000), _texte(attendus, "modifications attendues", 4000)
    if echeance and not re.match(r"^\d{4}-\d{2}-\d{2}$", echeance):
        raise ErreurProposition("échéance : AAAA-MM-JJ")

    def regle(etat_p, o_org):
        _activee(etat_p)
        p = _get(etat_p, pid)
        if p["ancienne"]:
            raise ErreurProposition("demande de décision de l'ancien format : pas d'auteur pour la modifier ; approuvez, refusez ou demandez un avis")
        if p["statut"] not in OUVERTS:
            raise ErreurProposition(f"{pid} est {STATUTS[p['statut']].lower()} : impossible de demander des modifications")
    return ile.ajouter("proposition.modifications_demandees", {"proposition": pid, "observations": observations, "attendus": attendus, "echeance": echeance},
                       {"canal": canal} if canal else {}, completer=_completer({"role": "president"}, regle), cle=cle)


def rectifier(pid, cle, vers, motif, canal=None):
    """Correction d'une décision déjà prise : nouvel acte signé et motivé ; l'ancien reste au registre."""
    _president(cle)
    motif = _texte(motif, "motif de la rectification", 2000)
    if vers not in ("approuvee", "refusee"):
        raise ErreurProposition("rectifier vers : approuvee ou refusee")

    def regle(etat_p, o_org):
        _activee(etat_p)
        p = _get(etat_p, pid)
        if p["decision"] is None:
            raise ErreurProposition(f"{pid} n'a pas encore de décision à rectifier")
        if p["decision"]["sens"] == vers:
            raise ErreurProposition(f"{pid} est déjà {vers}")
        if p["statut"] in ("en_execution", "executee"):
            raise ErreurProposition(f"{pid} est {STATUTS[p['statut']].lower()} : la rectification n'annule pas une exécution ; ouvrez une nouvelle proposition")
        return {"remplace": p["decision"]["evenement"], "destinataires": _destinataires(p)}
    return ile.ajouter("proposition.rectifiee", {"proposition": pid, "vers": vers, "motif": motif}, {"canal": canal} if canal else {},
                       completer=_completer({"role": "president"}, regle), cle=cle)


# ------------------------------------------------------------------ suites données
def mettre_en_oeuvre(pid, responsable, modalites, auteur=None, cle=None, echeance=None, mission=None, canal=None):
    _institution(responsable)
    modalites = _texte(modalites, "modalités de mise en œuvre", 4000)
    eff = _president(cle) if cle is not None else auteur

    def regle(etat_p, o_org):
        p = _get(etat_p, pid)
        if eff.get("role") not in ("president", "maire"):
            raise ErreurProposition("les modalités de mise en œuvre sont fixées par le président ou le directeur général de l'île")
        if p["statut"] != "approuvee":
            raise ErreurProposition(f"seule une proposition approuvée se met en œuvre ({pid} est {STATUTS[p['statut']].lower()})")
    return ile.ajouter("proposition.mise_en_oeuvre", {"proposition": pid, "responsable": responsable, "modalites": modalites, "echeance": echeance, "mission": mission},
                       ({"canal": canal} if canal else {}) if cle is not None else auteur, completer=_completer(eff, regle), cle=cle)


def executer(pid, etape, auteur, resultat=None):
    if etape not in ("debut", "fin"):
        raise ErreurProposition("étape : debut ou fin")
    if etape == "fin":
        resultat = _texte(resultat, "résultats", 8000)

    def regle(etat_p, o_org):
        p = _get(etat_p, pid)
        moe = p["mise_en_oeuvre"]
        if not moe:
            raise ErreurProposition(f"{pid} n'a pas de modalités de mise en œuvre définies")
        if not (auteur.get("role") == "maire" or _membre(o_org, auteur, moe["responsable"])):
            raise ErreurProposition(f"seul le responsable désigné ({moe['responsable']}, identité vérifiée) ou le directeur général peut rendre compte de l'exécution")
        attendu = "approuvee" if etape == "debut" else "en_execution"
        if p["statut"] != attendu:
            raise ErreurProposition(f"{pid} est {STATUTS[p['statut']].lower()} : étape « {etape} » impossible")
    return ile.ajouter("proposition.execution", {"proposition": pid, "etape": etape, "resultat": resultat}, auteur, completer=_completer(auteur, regle))


def accuser_reception(pid, institution, auteur):
    def regle(etat_p, o_org):
        p = _get(etat_p, pid)
        if not p["decision"] or institution not in (p["decision"].get("destinataires") or []):
            raise ErreurProposition(f"aucune décision sur {pid} n'a été adressée à {institution}")
        if not _membre(o_org, auteur, institution):
            raise ErreurProposition(f"seul un membre de {institution} à l'identité vérifiée peut accuser réception")
        return {"decision": p["decision"]["evenement"]}
    return ile.ajouter("proposition.reception", {"proposition": pid, "institution": institution}, auteur, completer=_completer(auteur, regle))


def archiver(pid, motif, auteur=None, cle=None, canal=None):
    eff = _president(cle) if cle is not None else auteur

    def regle(etat_p, o_org):
        p = _get(etat_p, pid)
        if eff.get("role") not in ("president", "maire"):
            raise ErreurProposition("archivage réservé au président ou au directeur général de l'île")
        if p["statut"] not in ("executee", "refusee") or p["archivee"]:
            raise ErreurProposition(f"seule une proposition exécutée ou refusée, non archivée, peut l'être ({pid} : {STATUTS[p['statut']].lower()})")
    return ile.ajouter("proposition.archivee", {"proposition": pid, "motif": _texte(motif, "motif", 1000)},
                       ({"canal": canal} if canal else {}) if cle is not None else auteur, completer=_completer(eff, regle), cle=cle)
