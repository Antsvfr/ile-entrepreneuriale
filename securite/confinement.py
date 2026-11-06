"""Confinement des imports des processus privilégiés de l'île : garde, hooks, serveur, commandes présidentielles.

La faille : Python place le dossier du script lancé en tête de son chemin d'import. Un fichier `json.py`
(ou `hmac.py`, `getpass.py`…) déposé par un agent remplaçait donc le module standard du même nom et s'exécutait
DANS le garde (qui pouvait alors autoriser n'importe quoi), dans le serveur (qui garde la clé présidentielle en
mémoire) ou dans une commande présidentielle (qui lit la phrase).

Trois couches, indépendantes :
  1. tous les points d'entrée sont lancés en `python3 -I -S` (réglages des hooks, lanceur `ile`, LaunchAgent,
     inspection) : ni dossier du script, ni dossier courant, ni PYTHONPATH, ni site utilisateur, ni fichiers .pth,
     ni sitecustomize / usercustomize ;
  2. chaque point d'entrée réduit `sys.path` à la bibliothèque standard de l'interpréteur AVANT tout autre import
     (bloc en ligne en tête du script : il ne peut s'appuyer sur aucun module). Lancé sans `-I`, cette couche arrête
     encore les modules plantés dans le projet, mais pas ce que Python exécute avant le script (.pth, usercustomize,
     PYTHONPATH sous 3.9, os.py en `-S` seul) : seule la couche 1 couvre ces cas ;
  3. les modules de l'île (`signature`, `president`, `ile`) sont chargés ICI, par leur chemin exact et depuis leur
     SOURCE : jamais par le chemin d'import, jamais depuis un `.pyc` de `__pycache__` (qu'un agent pourrait
     falsifier en recopiant la date et la taille du source). Un module homonyme déjà chargé depuis un autre fichier
     est refusé.

Ce fichier est un garde-fou : sa modification exige l'accord du président (securite/garde.py, FICHIERS_GARDE).
Limite assumée : les agents tournent sous le même utilisateur système que le président. Ce confinement ferme le
détournement d'import ; il ne protège pas contre un agent qui remplacerait l'interpréteur lui-même ou réécrirait
un garde-fou par une commande obscurcie (voir docs/architecture/ETAPES-2.md).
"""
import os
import sys

ICI = os.path.dirname(os.path.realpath(__file__))          # securite/
RACINE = os.path.dirname(ICI)                              # racine de l'île
# Modules de l'île chargeables, et leur seul emplacement admis (séparation : présidence / orchestrateur).
MODULES = {"signature": "presidence/signature.py", "president": "presidence/president.py", "ile": "orchestrateur/ile.py",
           "organisation": "orchestrateur/organisation.py"}


class ErreurConfinement(ImportError):
    pass


def dossier_standard() -> str:
    """Dossier réel de la bibliothèque standard de l'interpréteur en cours (celui de `os`, chargé au démarrage)."""
    return os.path.dirname(os.path.realpath(os.__file__))


def bibliotheque_standard(chemins) -> list:
    """Ne garde que les entrées situées dans la bibliothèque standard (lib-dynload compris, site-packages exclus)."""
    std = dossier_standard()
    garder = []
    for p in chemins:
        if not p:
            continue                                   # "" = dossier courant
        r = os.path.realpath(p)
        if (r == std or r.startswith(std + os.sep)) and "site-packages" not in r and "dist-packages" not in r:
            garder.append(p)
    return garder


def confiner() -> None:
    sys.path[:] = bibliotheque_standard(sys.path)
    sys.dont_write_bytecode = True                     # un processus privilégié n'écrit aucun cache


def charger(nom: str):
    """Charge le module de l'île <nom> (presidence/ ou orchestrateur/) par son chemin exact, depuis la source, et l'inscrit dans sys.modules."""
    if nom not in MODULES:
        raise ErreurConfinement(f"module « {nom} » hors de la liste de l'île {tuple(MODULES)}")
    chemin = os.path.join(RACINE, MODULES[nom])
    deja = sys.modules.get(nom)
    if deja is not None:
        fichier = getattr(deja, "__file__", None)
        if fichier and os.path.realpath(fichier) == chemin:
            return deja
        raise ErreurConfinement(f"module « {nom} » déjà chargé depuis {fichier!r} au lieu de {chemin} : refusé")
    module = type(sys)(nom)
    module.__file__ = chemin
    with open(chemin, "rb") as f:
        code = compile(f.read(), chemin, "exec", dont_inherit=True)
    sys.modules[nom] = module
    try:
        exec(code, module.__dict__)
    except BaseException:
        sys.modules.pop(nom, None)
        raise
    return module
