#!/usr/bin/env python3
"""Le garde : hook PreToolUse de Claude Code, exécuté AVANT chaque action d'un agent (session principale comprise).

Il ne dépend pas du modèle : Claude Code le lance lui-même et respecte son verdict (code de sortie 2 = action refusée,
le message est rendu à l'agent). Trois issues :
  - autoriser      : l'agent travaille librement dans ses limites ;
  - bloquer        : interdit dans tous les cas (usurper le président, réécrire le journal…) — refus inscrit au journal ;
  - approbation    : opération sensible (push sur une branche protégée, fusion, déploiement, suppression, secret,
                     envoi réseau, modification des garde-fous, écriture hors du dépôt…). Elle est bloquée et une
                     demande part dans la Résidence ; après l'accord SIGNÉ du président, la même opération exacte passe.

Limites assumées (voir architecture/ETAPES-2.md) : le garde lit des commandes, il ne peut pas deviner une commande
volontairement obscurcie (base64, script intermédiaire). La signature présidentielle, elle, ne se contourne pas :
un agent qui réussirait à écrire dans le journal ne pourrait toujours pas fabriquer un acte du président.
"""
# Pas de « from __future__ » ici : ce serait un import lancé AVANT toute protection, donc remplaçable par un fichier
# securite/__future__.py planté. `sys` est intégré à l'interpréteur ; `os` est déjà chargé au démarrage (ou, en `-I -S`,
# introuvable ailleurs que dans la bibliothèque standard). Limite : lancé en `-S` SANS `-I` sous Python 3.9, un os.py
# planté à côté du script serait chargé — aucun point d'entrée de l'île n'est lancé ainsi.
import os
import sys

_ICI = os.path.dirname(os.path.realpath(__file__))
if __name__ == "__main__":
    # Échec FERMÉ dès la première ligne : une exception avant main() (import cassé, module manquant…) donnerait le
    # code 1, que Claude Code laisse passer. Elle devient un refus (code 2).
    def _refus_par_prudence(genre, valeur, trace):
        sys.stderr.write(f"Garde de l'île : erreur interne au démarrage ({genre.__name__}: {valeur}) — action refusée par prudence.\n")
        os._exit(2)
    sys.excepthook = _refus_par_prudence
    # Lancé par Claude Code (`python3 -I -S …/garde.py`) : même sans -I, aucun module planté dans securite/ ou
    # ailleurs ne peut remplacer un module standard. Le chemin d'import est réduit à la bibliothèque standard AVANT
    # tout autre import ; les modules de l'île sont ensuite chargés par leur chemin exact (securite/confinement.py).
    _STD = os.path.dirname(os.path.realpath(os.__file__))
    sys.path[:] = [p for p in sys.path if p and (os.path.realpath(p) + os.sep).startswith(_STD + os.sep)
                   and "-packages" not in os.path.realpath(p)]
    sys.dont_write_bytecode = True

import json  # noqa: E402
import re  # noqa: E402
import shlex  # noqa: E402
import subprocess  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Optional  # noqa: E402

OPS_DIR = Path(__file__).resolve().parent          # securite/ : le garde, le confinement, l'arrêt d'urgence
ILE = OPS_DIR.parent                               # racine de l'île = racine du dépôt (ile-entrepreneuriale)
DEPOT = ILE
# L'arrêt d'urgence suit ILE_OPS comme le journal : les tests (copie temporaire) ne touchent jamais au vrai STOP.
# Le vrai securite/STOP arrête TOUJOURS les agents ; celui du dossier ILE_OPS (s'il diffère) aussi.
STOP_REEL = OPS_DIR / "STOP"
STOP = Path(os.environ.get("ILE_OPS") or OPS_DIR) / "STOP"
TEMPORAIRES = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")
PROTEGEES = ("main", "master", "production", "prod", "release")
LECTURE = {"Read", "Glob", "Grep", "LS", "WebSearch", "TodoWrite", "TodoRead", "Task", "Agent", "ExitPlanMode", "BashOutput", "KillShell", "NotebookRead"}
ECRITURE = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
# Séparation des privilèges : tout securite/ et presidence/ ; le cœur de l'orchestrateur (registre, capteurs) ; le serveur
# de la Résidence ; les tests et preuves (ils font foi). Le journal lui-même a sa règle (bloqué, jamais approuvable).
FICHIERS_GARDE = [".claude/settings.json", ".claude/settings.local.json", ".claude/hooks/", "securite/", "presidence/",
                  "orchestrateur/ile.py", "orchestrateur/hooks/", "residence/serveur.py", "audit/preuves.py", ".git/config", ".git/hooks/"]
# Tout module Python déposé à côté des garde-fous (securite/, presidence/, orchestrateur/… et leurs caches .pyc) exige aussi l'accord : le
# confinement des imports le rend inerte pour le garde, mais on ne laisse pas un agent en semer sans le dire.
# Lanceurs : le président y tape sa phrase (./ile president) et ils fixent « python3 -I -S ». Comparés par chemin
# exact seulement (« ile » est un nom trop court pour une recherche dans le texte des commandes).
LANCEURS = ("ile", "Ouvrir l'île.command", "audit/inspection.sh")
DOSSIERS_PRIVILEGIES = ("securite", "presidence", "orchestrateur", "residence", "audit", "tests")
MOTIF_GARDE = re.compile(r"^(?:%s)/(?:.*/)?(?:[^/]+\.py[cod]?|__pycache__(?:/.*)?|[^/]+\.pth)$|^tests/|^[^/]+\.(?:py[cod]?|pth)$|^__pycache__/"
                         % "|".join(DOSSIERS_PRIVILEGIES))
# Dossiers qui contiennent des garde-fous : y copier, y déplacer ou y extraire « en vrac » (dossier, joker, archive,
# branche git) pourrait remplacer un garde-fou sans le nommer. Le dépôt et ses parents en font partie.
GIT = "/usr/bin/git" if os.path.exists("/usr/bin/git") else "git"   # pas un « git » placé avant dans le PATH
SECRETS = re.compile(r"(?:^|[\s/'\"=])(\.env(?!\.example\b)(?:\.[\w.-]+)?|id_rsa|id_ed25519|id_ecdsa|\.netrc|\.pgpass|\.npmrc|credentials\.json|service[-_]account[\w.-]*\.json|[\w.-]+\.pem|[\w.-]+\.p12|\.aws/credentials|\.ssh/)(?:$|[\s'\";|&)])")


class Verdict:
    def __init__(self, issue="autoriser", categorie=None, regle=None, raison=None, outil=None, cible=None, mode="unique"):
        self.issue, self.categorie, self.regle, self.raison, self.outil, self.cible, self.mode = issue, categorie, regle, raison, outil, cible, mode


def _branche(cwd: Optional[str]) -> Optional[str]:
    try:
        r = subprocess.run([GIT, "-c", "core.fsmonitor=false", "-C", cwd or ".", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=3)
        return r.stdout.strip() or None
    except Exception:
        return None


def _push_implicite_protege(cwd: Optional[str]) -> Optional[str]:
    """Pour un « git push » sans destination explicite : la configuration (remote.*.push, branche suivie) vise-t-elle
    une branche protégée ? (ex. remote.origin.push = HEAD:refs/heads/main posé dans .git/config)."""
    try:
        r = subprocess.run([GIT, "-c", "core.fsmonitor=false", "-C", cwd or ".", "config", "--get-regexp", r"^(remote\..*\.push|branch\..*\.merge)$"],
                           capture_output=True, text=True, timeout=3)
    except Exception:
        return None
    branche = _branche(cwd) or ""
    for ligne in r.stdout.splitlines():
        cle, _, valeur = ligne.partition(" ")
        if cle.endswith(".merge") and cle != f"branch.{branche}.merge":
            continue
        if re.search(r"(^|[\s:/])(%s)$" % "|".join(PROTEGEES), valeur.strip()):
            return f"{cle} = {valeur.strip()}"
    return None


def _dossiers_garde():
    return [ILE] + [ILE / d for d in DOSSIERS_PRIVILEGIES] + [ILE / d / "__pycache__" for d in DOSSIERS_PRIVILEGIES] + \
        [ILE / "orchestrateur" / "hooks", ILE / ".claude", ILE / ".claude" / "hooks", ILE / ".git", ILE / ".git" / "hooks"]


def _dossier_sensible(chemin: str, cwd: Optional[str]) -> bool:
    """Vrai si le dossier contient (directement ou plus bas) des garde-fous : le dépôt, ses parents, securite/…"""
    try:
        p = Path(_norm(chemin, cwd))
    except Exception:
        return True
    return any(d == p or p in d.parents for d in _dossiers_garde())


def _copie_vers_garde(verbe: str, args: list, cwd: Optional[str]) -> Optional[str]:
    """cp / mv / install / ln / rsync : une destination DOSSIER est résolue (dossier/nom de la source) ; une copie en
    vrac (récursive, joker, « . ») vers un dossier qui contient des garde-fous exige l'accord. Pour mv, déplacer un
    garde-fou ou un dossier qui en contient aussi."""
    options = [a for a in args if a.startswith("-")]
    operandes = [a for a in args if not a.startswith("-")]
    cible_dossier = None
    for i, a in enumerate(args):
        if a in ("-t", "--target-directory") and i + 1 < len(args):
            cible_dossier = args[i + 1]
            operandes = [x for x in operandes if x != cible_dossier]
        elif a.startswith("--target-directory="):
            cible_dossier = a.split("=", 1)[1]
    if cible_dossier is None:
        if len(operandes) < 2:
            return None
        dest, sources = operandes[-1], operandes[:-1]
    else:
        dest, sources = cible_dossier, operandes
    recursif = verbe in ("rsync",) or any(re.match(r"^(-[a-zA-Z]*[rRa]|--recursive|--archive)", o) for o in options)
    if verbe == "mv":
        for src in sources:
            if _est_garde(src, cwd) or _dossier_sensible(src, cwd):
                return f"déplacement d'un garde-fou ou d'un dossier qui en contient : {src}"
    if _est_garde(dest, cwd):
        return f"écriture d'un garde-fou : {dest}"
    est_dossier = cible_dossier is not None or dest.endswith("/") or len(sources) > 1 or os.path.isdir(_norm(dest, cwd))
    if not est_dossier:
        return None
    for src in sources:
        nom = os.path.basename(src.rstrip("/"))
        en_vrac = recursif or verbe == "mv" and os.path.isdir(_norm(src, cwd)) or nom in ("", ".", "..") or any(c in src for c in "*?[{")
        if en_vrac and _dossier_sensible(dest, cwd):
            return f"copie en vrac vers un dossier qui contient des garde-fous : {src} → {dest}"
        if _est_garde(os.path.join(dest, nom), cwd):
            return f"écriture d'un garde-fou : {os.path.join(dest, nom)}"
    return None


def _extraction_vers_garde(cl: str, mots: list, cwd: Optional[str]) -> Optional[str]:
    """tar / unzip / bsdtar / cpio / 7z : une archive extraite dans un dossier qui contient des garde-fous (ou un de
    ses parents) peut en remplacer un sans le nommer."""
    if not mots:
        return None
    outil = os.path.basename(mots[0])
    dest = None
    if outil in ("tar", "bsdtar", "gtar") and (re.search(r"(^|\s)-?[a-zA-Z]*x[a-zA-Z]*(\s|$)", " ".join(mots[1:2])) or "--extract" in mots or "-x" in mots
                                              or any(re.match(r"^-[a-zA-Z]*x", m) for m in mots[1:])):
        for i, m in enumerate(mots):
            if m in ("-C", "--directory") and i + 1 < len(mots):
                dest = mots[i + 1]
            elif m.startswith("--directory="):
                dest = m.split("=", 1)[1]
    elif outil == "unzip":
        for i, m in enumerate(mots):
            if m == "-d" and i + 1 < len(mots):
                dest = mots[i + 1]
    elif outil in ("cpio", "7z", "7za", "ditto"):
        if outil == "ditto" and len([m for m in mots[1:] if not m.startswith("-")]) >= 2:
            dest = [m for m in mots[1:] if not m.startswith("-")][-1]
        elif outil == "7z" and len(mots) > 1 and mots[1] not in ("x", "e"):
            return None
        else:
            dest = next((m[2:] for m in mots if m.startswith("-o")), None)
    else:
        return None
    dest = dest or cwd or os.getcwd()
    if _dossier_sensible(dest, cwd):
        return f"extraction d'archive dans un dossier qui contient des garde-fous : {dest}"
    return None


def _git_arbre_garde(s: str, cwd: Optional[str]) -> Optional[str]:
    """Dans le dépôt de l'île : une commande git qui réécrit l'arbre de travail (changer de branche ou de commit,
    restaurer un dossier, appliquer un correctif, tirer…) peut remettre un ancien garde-fou ou en installer un
    autre ; écrire la configuration git (.git/config) peut détourner un push. Les deux exigent l'accord."""
    m = re.search(r"\bgit((?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*)\s+([\w-]+)(.*)$", s)
    if not m:
        return None
    globales, sous, reste = m.group(1), m.group(2), m.group(3).split()
    mc = re.search(r"-C\s+(\S+)", globales)
    ici = _norm(mc.group(1), cwd) if mc else cwd
    if not _dans(ici or os.getcwd(), None, DEPOT):
        return None
    if sous == "config":
        lecture = not reste or any(o in reste for o in ("--get", "--get-all", "--get-regexp", "--list", "-l", "--show-origin", "--name-only")) \
            or len([x for x in reste if not x.startswith("-")]) <= 1 and not any(o in reste for o in ("--unset", "--unset-all", "--add", "--replace-all", "--remove-section", "--rename-section", "-e", "--edit"))
        return None if lecture else "écriture de la configuration git du dépôt de l'île (.git/config)"
    if sous in ("remote",) and reste[:1] and reste[0] in ("add", "set-url", "rename", "set-head", "set-branches"):
        return "modification des dépôts distants de l'île"
    if sous in ("switch", "checkout"):
        args = [x for x in reste if x not in ("-q", "--quiet")]
        if len(args) == 2 and args[0] in ("-b", "-c", "--create"):   # nouvelle branche au même commit : arbre inchangé
            return None
        if "--" in args:
            chemins = args[args.index("--") + 1:]
            source = [x for x in args[:args.index("--")] if not x.startswith("-")]
            if not source and chemins and not any(_dossier_sensible(c, ici) or _est_garde(c, ici) or any(j in c for j in "*?[") for c in chemins):
                return None
        return "réécriture de l'arbre de travail de l'île (changement de branche ou restauration) : les garde-fous pourraient être remplacés"
    if sous == "restore":
        if any(x.startswith(("--source", "-s")) for x in reste):
            return "restauration de fichiers de l'île depuis un autre commit"
        chemins = [x for x in reste if not x.startswith("-")]
        if chemins and not any(_dossier_sensible(c, ici) or _est_garde(c, ici) or any(j in c for j in "*?[") for c in chemins):
            return None
        return "restauration d'un garde-fou ou d'un dossier qui en contient"
    if sous in ("reset",) and any(x in reste for x in ("--hard", "--merge", "--keep")):
        return "réinitialisation de l'arbre de travail de l'île"
    if sous == "stash" and reste[:1] and reste[0] in ("pop", "apply", "branch"):
        return "réapplication d'un remisage dans l'arbre de travail de l'île"
    if sous in ("pull", "merge", "rebase", "cherry-pick", "revert", "apply", "am", "read-tree", "checkout-index", "worktree", "update-index", "filter-branch", "filter-repo"):
        return f"git {sous} dans le dépôt de l'île : modifie l'arbre de travail ou l'index (garde-fous compris)"
    return None


def _segments(cmd: str):
    """Découpe une ligne de commande en commandes simples (&&, ||, ;, |, retours à la ligne)."""
    return [s.strip() for s in re.split(r"&&|\|\||;|\||\n", cmd) if s.strip()]


def _sans_bruit(s: str) -> str:
    """Retire les redirections inoffensives (2>&1, >&2, 2>/dev/null…) qui ne sont pas des écritures de fichier."""
    return re.sub(r"(?:\d*|&)>>?\s*/dev/(?:null|stdout|stderr|tty)\b|\d*>&\s*(?:\d+|-)(?![\w./-])", " ", s)


def _cibles_ecriture(s: str):
    """Fichiers visés par une redirection (>, >>, &>) ou par tee dans une commande simple."""
    cibles = re.findall(r"(?:\d*|&)>>?\|?\s*([^\s;&|<>()]+)", s)
    m = re.search(r"\btee\s+(.*)$", s)
    if m:
        cibles += [x for x in m.group(1).split() if not x.startswith("-")]
    return [c.strip("'\"") for c in cibles if c.strip("'\"")]


def _norm(chemin: str, cwd: Optional[str]) -> str:
    """Chemin absolu réel : « .. » résolus et liens symboliques suivis (un /tmp/../ ou un lien ne trompe pas le garde)."""
    p = os.path.expanduser(chemin.strip("'\""))
    if not os.path.isabs(p):
        p = os.path.join(cwd or os.getcwd(), p)
    return os.path.realpath(p)


def _temporaire(chemin: str, cwd: Optional[str]) -> bool:
    return (_norm(chemin, cwd) + "/").startswith(TEMPORAIRES)


def _dans(chemin: str, cwd: Optional[str], base: Path) -> bool:
    try:
        p = Path(_norm(chemin, cwd))
        return p == base or base in p.parents
    except Exception:
        return False


def _relatif_ile(chemin: str, cwd: Optional[str]) -> Optional[str]:
    try:
        return str(Path(_norm(chemin, cwd)).relative_to(ILE)).replace(os.sep, "/")
    except Exception:
        return None


def _hors_depot(chemin: str, cwd: Optional[str]) -> bool:
    """Vrai si le chemin sort du dépôt de l'île (hors fichiers temporaires et /dev)."""
    if chemin.startswith("$") and not chemin.startswith(("$HOME", "${HOME}")):
        return False   # variable inconnue : on ne devine pas
    chemin = chemin.replace("${HOME}", "~").replace("$HOME", "~")
    n = _norm(chemin, cwd)
    return not (_dans(n, None, DEPOT) or (n + "/").startswith(TEMPORAIRES) or n.startswith("/dev/"))


def analyser_bash(cmd: str, cwd: Optional[str]) -> Verdict:
    c = " ".join(cmd.split())
    V = lambda *a, **k: Verdict(*a, outil="Bash", cible=cmd.strip(), **k)
    # --- interdits absolus : usurper le président, toucher au journal ou à l'identité
    if re.search(r"--auteur(?:=|\s+)['\"]?president\b", c):
        return V("bloquer", "president", "usurpation", "seul le président peut agir en son nom (actes signés de sa clé)")
    if re.search(r"\b(creer_identite|changer_phrase|ClePresident|nouvelle_identite|_graine|demander_phrase)\b"
                 r"|\bile\.py\b(?:\s+--?[\w-]+(?:[=\s]+(?!-)[^\s;|&]+)?)*\s+['\"]?president\b|(^|[\s/])ile\s+['\"]?president\b", c):
        return V("bloquer", "president", "identite", "l'identité et les actes présidentiels ne se manipulent que par le président, dans un vrai terminal")
    if "journal.jsonl" in c and not all(re.match(r"^(git\s+(add|commit|diff|log|show|status|blame)\b|cat|head|tail|wc|grep|less|ls|stat|sha256sum|shasum)\b", s) and ">" not in _sans_bruit(s) for s in _segments(c) if "journal.jsonl" in s):
        return V("bloquer", "journal", "ecriture-journal", "le journal des opérations ne s'écrit qu'à travers orchestrateur/ile.py")
    if re.search(r"\bsecurite/STOP\b", c) and re.search(r"\b(rm|mv|unlink|truncate)\b", c):
        return V("bloquer", "arret", "stop", "seul le président lève l'arrêt d'urgence (supprimer securite/STOP lui-même)")
    # --- opérations sensibles : approbation présidentielle, opération par opération
    ici = cwd
    for s in _segments(c):
        cl = _sans_bruit(s)
        try:
            mots = shlex.split(cl)
        except ValueError:
            mots = cl.split()
        if mots[:1] == ["cd"]:   # « cd operations && sed -i … garde.py » : le dossier courant suit la commande
            ici = _norm(mots[1], ici) if len(mots) > 1 else os.path.expanduser("~")
            continue
        mc = re.match(r"^(?:sudo\s+)?(?:\S*/)?(cp|mv|install|ln|rsync|gcp|gmv)\s+(.*)$", cl)
        if mc:
            try:
                args_copie = shlex.split(mc.group(2))
            except ValueError:
                args_copie = mc.group(2).split()
            motif = _copie_vers_garde({"gcp": "cp", "gmv": "mv"}.get(mc.group(1), mc.group(1)), args_copie, ici)
            if motif:
                return V("approbation", "garde-fous", "modif-garde-fous", f"modification des garde-fous — {motif}")
        motif = _extraction_vers_garde(cl, mots, ici)
        if motif:
            return V("approbation", "garde-fous", "modif-garde-fous", f"modification des garde-fous — {motif}")
        if re.search(r"\bgit\b", s):
            motif = _git_arbre_garde(s, ici)
            if motif:
                return V("approbation", "garde-fous", "git-garde-fous", motif)
        if re.match(r"^(?:sudo\s+)?(?:\S*/)?(rm|unlink|shred)\b", cl) and any(_est_garde(x, ici) or _dossier_sensible(x, ici) for x in mots[1:] if not x.startswith("-")):
            return V("approbation", "garde-fous", "modif-garde-fous", "suppression d'un garde-fou ou d'un dossier qui en contient")
        if re.search(r"\b(rm|mv|unlink|truncate)\b", cl) and any(_norm(x, ici) in (str(STOP_REEL), str(STOP)) for x in mots if not x.startswith("-")):
            return V("bloquer", "arret", "stop", "seul le président lève l'arrêt d'urgence (supprimer securite/STOP lui-même)")
        if re.match(r"^(sudo\s+)?git\b", s) or re.search(r"\bgit\s", s):
            if re.search(r"\bpush\b", s):
                if re.search(r"(--force\b|--force-with-lease|(\s|^)-[a-zA-Z]*f\b|\s\+\S|--delete\b|(\s|^)-d\b|\s:\S|--tags\b|--mirror\b)", s):
                    return V("approbation", "git", "push-force", "push forcé, suppression ou publication de tags sur un dépôt distant")
                if re.search(r"(^|[\s:/])(%s)\b" % "|".join(PROTEGEES), s):
                    return V("approbation", "git", "push-protege", "push vers une branche protégée (main, master, production…)")
                if not re.search(r"\bpush\s+\S+\s+\S+", s) and _branche(ici) in PROTEGEES:
                    return V("approbation", "git", "push-protege", f"push depuis la branche protégée « {_branche(ici)} »")
                if not re.search(r"\bpush(?:\s+-\S+)*\s+[^-\s]\S*\s+[^-\s]", s):
                    conf = _push_implicite_protege(ici)
                    if conf:
                        return V("approbation", "git", "push-protege", f"push sans destination explicite, mais la configuration vise une branche protégée ({conf})")
            if re.search(r"\b(merge|rebase|cherry-pick|reset\s+--hard|commit|am)\b", s) and _branche(ici) in PROTEGEES and not re.search(r"\b(merge-base|--abort|--continue)\b", s):
                return V("approbation", "git", "branche-protegee", f"modification directe de la branche protégée « {_branche(ici)} »")
            if re.search(r"\bbranch\s+(-D|--delete\s+--force|-d\s+-f)\b|\bclean\s+-[a-zA-Z]*f|\bfilter-(branch|repo)\b|\breflog\s+expire\b", s):
                return V("approbation", "git", "destruction-git", "suppression d'historique ou de fichiers non suivis")
        if re.search(r"\bgh\s+(pr\s+merge|pr\s+review\s+.*--approve|release\s+(create|delete)|repo\s+(create|delete|archive|edit)|secret\s+set|api\b.*(merge|-X\s*(DELETE|PUT)|--method\s*(DELETE|PUT)))", s):
            return V("approbation", "github", "github-sensible", "fusion, publication, création ou suppression sur GitHub")
        if re.search(r"\bvercel\b(?!\s+(dev|whoami|ls|list|logs|inspect|env\s+ls|--version|help)\b)|\bsupabase\s+(db\s+(push|reset)|functions\s+deploy|secrets\s+(set|unset)|projects\s+(create|delete)|link)\b|\bnpm\s+publish\b|\b(firebase|netlify|fly|flyctl|railway)\s+deploy\b|\bdocker\s+push\b|\bterraform\s+(apply|destroy)\b|\bkubectl\s+(apply|delete)\b|\bheroku\b", s):
            return V("approbation", "deploiement", "deploiement", "déploiement, migration ou publication en production")
        if re.search(r"\bnpm\s+run\s+db:reset\b|\bdropdb\b|\bDROP\s+(TABLE|DATABASE|SCHEMA)\b|\bTRUNCATE\s+TABLE\b", s, re.I):
            return V("approbation", "donnees", "destruction-donnees", "destruction ou réinitialisation de données")
        # rm récursif, y compris « /bin/rm », « command rm », « xargs rm », « (rm … ) », « --recursive »
        m = re.match(r"^(?:[({`]|\$\()*\s*(?:(?:sudo|command|builtin|exec|nohup|time|nice|env|xargs(?:\s+-\S+)*)\s+)*(?:\S*/)?rm\s+(.*)$", cl)
        if m and re.search(r"(^|\s)(-[a-zA-Z]*[rR]|--recursive\b)", m.group(1)):
            cibles = [x.strip("'\")`") for x in m.group(1).split() if not x.startswith("-")]
            cibles = [x for x in cibles if x]
            dangereux = [x for x in cibles if x in ("/", "~", ".", "..", "*", "~/") or _hors_depot(x, ici) or _norm(x, ici) in (str(DEPOT), str(ILE))]
            if dangereux or not cibles:
                return V("approbation", "suppression", "rm-hors-projet", f"suppression récursive hors du dépôt ou trop large : {' '.join(dangereux) or '(aucune cible)'}")
        m = re.match(r"^(?:sudo\s+)?find\s+(.*)$", cl)
        if m and re.search(r"\s-delete\b|\s-exec(dir)?\s+(\S*/)?rm\b", cl):
            racines = []
            for x in m.group(1).split():
                if x.startswith(("-", "(", "!")):
                    break
                racines.append(x.strip("'\""))
            dangereux = [x for x in (racines or ["."]) if _hors_depot(x, ici)]
            if dangereux:
                return V("approbation", "suppression", "rm-hors-projet", f"suppression (find) hors du dépôt : {' '.join(dangereux)}")
        if SECRETS.search(" " + s + " ") or re.search(r"\bsecurity\s+find-(generic|internet)-password\b|^printenv\b|^env\s*$|^export\s+-p\b", s):
            return V("approbation", "secret", "secret", "lecture d'un secret (clé, mot de passe, variables d'environnement)")
        if re.search(r"\b(curl|wget|http|https|xh)\b", s) and re.search(r"(\s-[a-zA-Z]*[dFT]\b|--data|--json\b|--form|--upload-file|-X\s*(POST|PUT|PATCH|DELETE)|--request[=\s]*(POST|PUT|PATCH|DELETE)|--post-data|--post-file|--body-data|--body-file)", s):
            hotes = [h.rsplit("@", 1)[-1].rsplit(":", 1)[0].lower() for h in re.findall(r"https?://([^/\s'\"?#]+)", s)]
            if not hotes or any(h not in ("localhost", "127.0.0.1", "[::1]") for h in hotes):
                return V("approbation", "reseau", "envoi-reseau", "envoi de données vers un service extérieur")
        if re.match(r"^(scp|sftp|ssh|nc|ncat|telnet)\b", s) or re.match(r"^rsync\b.*\s\S+:\S*", s):
            return V("approbation", "reseau", "connexion-distante", "connexion ou copie vers une machine distante")
        cibles = _cibles_ecriture(cl)
        verbe = re.search(r"(\btee\b|\bsed\s+[^|]*-i|\bperl\s+-[a-z]*i|\bmv\b|\bcp\b|\brm\b|\bchmod\b|\bln\b|\btruncate\b|\bpython[0-9.]*\s+-c\b|\bpatch\b|\bgit\s+(checkout|restore)\b|\binstall\b|\bdd\b)", cl)
        if any(_est_garde(x, ici) for x in cibles) or (verbe and (any(f in cl for f in FICHIERS_GARDE) or re.search(r"\b(?:%s)/(?:[\w./-]*/)?(?:[\w.-]+\.py[cod]?|__pycache__|[\w.-]+\.pth)\b" % "|".join(DOSSIERS_PRIVILEGIES), cl)
                                                                   or any(_est_garde(x, ici) for x in mots[1:] if not x.startswith("-")))):
            return V("approbation", "garde-fous", "modif-garde-fous", "modification des garde-fous (hooks, réglages, registre, identité, serveur)")
        m = re.match(r"^(?:sudo\s+)?(cp|mv|install|ln)\s+(.*)$", cl)
        dest = [x for x in (m.group(2).split() if m else []) if not x.startswith("-")]
        externes = [x for x in cibles if _hors_depot(x, ici)] + ([dest[-1]] if len(dest) >= 2 and _hors_depot(dest[-1], ici) else [])
        if externes:
            return V("approbation", "projet-externe", "ecriture-externe", f"écriture hors du dépôt de l'île : {' '.join(externes)}")
    return Verdict()


def _est_garde(chemin: str, cwd: Optional[str]) -> Optional[str]:
    """Chemin (relatif) du garde-fou visé, ou None."""
    rel = _relatif_ile(chemin, cwd)
    if rel and (any(rel == f or (f.endswith("/") and rel.startswith(f)) for f in FICHIERS_GARDE) or rel in LANCEURS or MOTIF_GARDE.match(rel)):
        return rel
    try:
        rel_depot = str(Path(_norm(chemin, cwd)).relative_to(DEPOT)).replace(os.sep, "/")
    except ValueError:
        return None
    if rel_depot in (".claude/settings.json", ".claude/settings.local.json", ".git/config") or rel_depot.startswith((".git/hooks/", ".git/info/")):
        return rel_depot
    return None


def analyser_fichier(outil: str, chemin: str, cwd: Optional[str], agent: dict) -> Verdict:
    V = lambda *a, **k: Verdict(*a, outil="Edit", cible=os.path.normpath(os.path.join(cwd or os.getcwd(), os.path.expanduser(chemin))), **k)
    rel = _relatif_ile(chemin, cwd)
    if rel == "orchestrateur/registre/journal.jsonl":
        return V("bloquer", "journal", "ecriture-journal", "le journal des opérations ne s'écrit qu'à travers orchestrateur/ile.py")
    garde_fou = _est_garde(chemin, cwd)
    if garde_fou:
        return V("approbation", "garde-fous", "modif-garde-fous", f"modification d'un garde-fou : {garde_fou}", mode="fenetre")
    if not _dans(chemin, cwd, DEPOT) and not _temporaire(chemin, cwd):
        if SECRETS.search(" " + chemin + " "):
            return V("approbation", "secret", "secret", "écriture d'un fichier de secrets")
        return V("approbation", "projet-externe", "ecriture-externe", "écriture hors du dépôt de l'île (projet externe)", mode="fenetre")
    role = (agent or {}).get("agent_type") or ""
    if rel is not None:
        if role.startswith("critique-") and not rel.startswith("audit/conseil/"):
            return V("bloquer", "role", "critique-lecture", f"une critique ne modifie que les procès-verbaux du Conseil (tentative : {rel})")
        if role.startswith("chef-"):
            siege = _siege_du_chef(role)
            if siege and not (rel.startswith(f"projets/{siege}/") or rel.startswith("audit/conseil/")):
                return V("bloquer", "role", "chef-hors-maison", f"un directeur ne modifie que sa maison projets/{siege}/ (tentative : {rel})")
    return Verdict()


def _siege_du_chef(role: str) -> Optional[str]:
    try:
        for b in json.loads((ILE / "registre.json").read_text(encoding="utf-8")).get("batiments", []):
            if Path(b.get("agent", "")).stem == role:
                return b.get("dossier", "").split("/")[-1] or b["id"]
    except Exception:
        pass
    return None


def analyser(payload: dict) -> Verdict:
    outil = payload.get("tool_name") or ""
    ti = payload.get("tool_input") or {}
    cwd = payload.get("cwd")
    agent = {k: payload.get(k) for k in ("agent_type", "agent_id", "session_id") if payload.get(k)}
    if (STOP_REEL.exists() or STOP.exists()) and outil not in LECTURE:
        return Verdict("bloquer", "arret", "stop", "ARRÊT D'URGENCE actif (securite/STOP) : aucune action n'est permise tant que le président ne l'a pas levé", outil, str(ti)[:300])
    if outil == "Bash":
        cmd = ti.get("command") or ""
        # Organisation (phase 3) : un agent (sous-agent) n'agit que sous SA identité vérifiée par son exécution (--run),
        # jamais comme le Maire (DG de l'île, identité seulement déclarée, valeur par défaut de --auteur).
        if agent.get("agent_type") and re.search(r"\bile\.py\b.*\borg\s+(departement|poste|nommer|affecter|suspendre|reactiver|amorcer|attribuer|demarrer|livrer|valider|corriger|remonter|message|reunion|clore-reunion)\b", cmd):
            if not re.search(r"--run(?:=|\s+)['\"]?R-\d+", cmd) or re.search(r"--auteur(?:=|\s+)['\"]?maire\b", cmd) or not re.search(r"--auteur(?:=|\s+)", cmd):
                return Verdict("bloquer", "organisation", "usurpation-dg", "un agent agit sur l'organisation sous sa propre identité vérifiée (--auteur <son rôle> --run R-…), jamais comme le Maire", "Bash", cmd.strip())
        # Propositions au président : même règle (un agent propose, rend un avis ou rend compte sous SA identité vérifiée).
        if agent.get("agent_type") and re.search(r"\bile\.py\b.*\bproposition\s+(creer|soumettre|modifier|transmettre|avis-demander|avis-rendre|mettre-en-oeuvre|executer|recevoir|archiver)\b", cmd):
            if not re.search(r"--run(?:=|\s+)['\"]?R-\d+", cmd) or re.search(r"--auteur(?:=|\s+)['\"]?maire\b", cmd) or not re.search(r"--auteur(?:=|\s+)", cmd):
                return Verdict("bloquer", "propositions", "usurpation-dg", "un agent agit sur une proposition sous sa propre identité vérifiée (--auteur <son rôle> --run R-…), jamais comme le Maire", "Bash", cmd.strip())
        return analyser_bash(cmd, cwd)
    if outil in ECRITURE:
        return analyser_fichier(outil, ti.get("file_path") or ti.get("notebook_path") or "", cwd, agent)
    if outil in ("Read", "Grep") and SECRETS.search(" " + (ti.get("file_path") or ti.get("path") or "") + " "):
        return Verdict("approbation", "secret", "secret", "lecture d'un fichier de secrets", outil, ti.get("file_path") or ti.get("path"))
    if outil.startswith("mcp__") and re.search(r"merge|delete|create_repository|auto_merge|fork_repository|run_secret|actions_run_trigger", outil):
        return Verdict("approbation", "github", "mcp-sensible", f"outil distant sensible : {outil}", outil, json.dumps(ti, sort_keys=True, ensure_ascii=False)[:1500])
    if outil.startswith("mcp__") and re.search(r"push_files|create_or_update_file", outil) and re.sub(r"^refs/heads/", "", str(ti.get("branch", ""))) in PROTEGEES:
        return Verdict("approbation", "github", "mcp-branche-protegee", "écriture distante sur une branche protégée", outil, json.dumps(ti, sort_keys=True, ensure_ascii=False)[:1500])
    return Verdict()


def _confinement():
    """securite/confinement.py, chargé par son chemin exact (jamais par le chemin d'import)."""
    chemin = str(OPS_DIR / "confinement.py")
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


def _module_ile():
    return _confinement().charger("ile")


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    agent = {k: payload.get(k) for k in ("agent_type", "agent_id", "session_id") if payload.get(k)} or {"agent_type": "session principale"}
    try:
        v = analyser(payload)
    except Exception as e:   # prudence : en cas d'erreur interne, on refuse et on le dit
        print(f"Garde de l'île : erreur interne ({type(e).__name__}: {e}) — action refusée par prudence.", file=sys.stderr)
        return 2
    if v.issue == "autoriser":
        return 0
    ile = _module_ile()
    if v.issue == "approbation":
        a = ile.approbation_valide(v.outil, v.cible)
        if a:
            ile.utiliser_approbation(a["id"], agent, ile._auteur("garde", "hook", session_id=agent.get("session_id")))
            return 0
        aid, neuve = ile.demander_approbation(v.categorie, v.regle, v.raison, v.outil, v.cible, ile._auteur("garde", "hook", session_id=agent.get("session_id")),
                                              cwd=payload.get("cwd"), agent=agent, mode=v.mode)
        print(f"Garde de l'île — opération sensible ({v.raison}). Demande {aid} {'transmise' if neuve else 'déjà en attente'} au président dans la Résidence. "
              f"Ne cherche pas à la contourner : continue le reste du travail et réessaie exactement la même opération après son accord.", file=sys.stderr)
        return 2
    try:
        ile.inscrire_refus(v.categorie, v.regle, v.raison, v.outil, v.cible, agent)
    except Exception:
        pass
    print(f"Garde de l'île — action interdite : {v.raison}.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    # Claude Code ne bloque que sur le code 2 : toute autre sortie (exception, import cassé, sys.exit(1)…) laisserait
    # passer l'action. Le garde échoue donc FERMÉ : tout incident devient un refus.
    try:
        code = main()
    except BaseException as e:   # noqa: BLE001 — y compris SystemExit : main() ne quitte jamais elle-même
        print(f"Garde de l'île : erreur interne ({type(e).__name__}: {e}) — action refusée par prudence.", file=sys.stderr)
        code = 2
    sys.exit(code if code in (0, 2) else 2)
