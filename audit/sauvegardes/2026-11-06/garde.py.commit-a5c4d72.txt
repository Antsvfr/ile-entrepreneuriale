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
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

OPS_DIR = Path(__file__).resolve().parent
ILE = OPS_DIR.parent
DEPOT = ILE.parent
STOP = OPS_DIR / "STOP"
PROTEGEES = ("main", "master", "production", "prod", "release")
LECTURE = {"Read", "Glob", "Grep", "LS", "WebSearch", "TodoWrite", "TodoRead", "Task", "Agent", "ExitPlanMode", "BashOutput", "KillShell", "NotebookRead"}
ECRITURE = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
FICHIERS_GARDE = [".claude/settings.json", ".claude/settings.local.json", ".claude/hooks/", "operations/garde.py", "operations/president.py",
                  "operations/signature.py", "operations/ile.py", "serveur.py"]
SECRETS = re.compile(r"(?:^|[\s/'\"=])(\.env(?!\.example\b)(?:\.[\w.-]+)?|id_rsa|id_ed25519|id_ecdsa|\.netrc|\.pgpass|\.npmrc|credentials\.json|service[-_]account[\w.-]*\.json|[\w.-]+\.pem|[\w.-]+\.p12|\.aws/credentials|\.ssh/)(?:$|[\s'\";|&)])")


class Verdict:
    def __init__(self, issue="autoriser", categorie=None, regle=None, raison=None, outil=None, cible=None, mode="unique"):
        self.issue, self.categorie, self.regle, self.raison, self.outil, self.cible, self.mode = issue, categorie, regle, raison, outil, cible, mode


def _branche(cwd: str | None) -> str | None:
    try:
        r = subprocess.run(["git", "-C", cwd or ".", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=3)
        return r.stdout.strip() or None
    except Exception:
        return None


def _segments(cmd: str):
    """Découpe une ligne de commande en commandes simples (&&, ||, ;, |, retours à la ligne)."""
    return [s.strip() for s in re.split(r"&&|\|\||;|\||\n", cmd) if s.strip()]


def _dans(chemin: str, cwd: str | None, base: Path) -> bool:
    try:
        p = Path(os.path.expanduser(chemin))
        if not p.is_absolute():
            p = Path(cwd or os.getcwd()) / p
        p = Path(os.path.normpath(str(p)))
        return p == base or base in p.parents
    except Exception:
        return False


def _relatif_ile(chemin: str, cwd: str | None) -> str | None:
    try:
        p = Path(os.path.expanduser(chemin))
        if not p.is_absolute():
            p = Path(cwd or os.getcwd()) / p
        return str(Path(os.path.normpath(str(p))).relative_to(ILE)).replace(os.sep, "/")
    except Exception:
        return None


def analyser_bash(cmd: str, cwd: str | None) -> Verdict:
    c = " ".join(cmd.split())
    V = lambda *a, **k: Verdict(*a, outil="Bash", cible=cmd.strip(), **k)
    # --- interdits absolus : usurper le président, toucher au journal ou à l'identité
    if re.search(r"--auteur(?:=|\s+)['\"]?president\b", c):
        return V("bloquer", "president", "usurpation", "seul le président peut agir en son nom (actes signés de sa clé)")
    if re.search(r"\b(creer_identite|changer_phrase|ClePresident|nouvelle_identite|_graine|demander_phrase)\b|\bile\.py\b.*\bpresident\b|(^|[\s/])ile\s+president\b", c):
        return V("bloquer", "president", "identite", "l'identité et les actes présidentiels ne se manipulent que par le président, dans un vrai terminal")
    if "journal.jsonl" in c and not all(re.match(r"^(git\s+(add|commit|diff|log|show|status|blame)\b|cat|head|tail|wc|grep|less|ls|stat|sha256sum|shasum)\b", s) and ">" not in s for s in _segments(c) if "journal.jsonl" in s):
        return V("bloquer", "journal", "ecriture-journal", "le journal des opérations ne s'écrit qu'à travers operations/ile.py")
    if re.search(r"\boperations/STOP\b", c) and re.search(r"\b(rm|mv|unlink|truncate)\b", c):
        return V("bloquer", "arret", "stop", "seul le président lève l'arrêt d'urgence (supprimer operations/STOP lui-même)")
    # --- opérations sensibles : approbation présidentielle, opération par opération
    for s in _segments(c):
        if re.match(r"^(sudo\s+)?git\b", s) or re.search(r"\bgit\s", s):
            if re.search(r"\bpush\b", s):
                if re.search(r"(--force\b|--force-with-lease|(\s|^)-[a-zA-Z]*f\b|\s\+\S|--delete\b|(\s|^)-d\b|\s:\S|--tags\b|--mirror\b)", s):
                    return V("approbation", "git", "push-force", "push forcé, suppression ou publication de tags sur un dépôt distant")
                if re.search(r"(^|[\s:/])(%s)\b" % "|".join(PROTEGEES), s):
                    return V("approbation", "git", "push-protege", "push vers une branche protégée (main, master, production…)")
                if not re.search(r"\bpush\s+\S+\s+\S+", s) and _branche(cwd) in PROTEGEES:
                    return V("approbation", "git", "push-protege", f"push depuis la branche protégée « {_branche(cwd)} »")
            if re.search(r"\b(merge|rebase|cherry-pick|reset\s+--hard|commit|am)\b", s) and _branche(cwd) in PROTEGEES and not re.search(r"\b(merge-base|--abort|--continue)\b", s):
                return V("approbation", "git", "branche-protegee", f"modification directe de la branche protégée « {_branche(cwd)} »")
            if re.search(r"\bbranch\s+(-D|--delete\s+--force|-d\s+-f)\b|\bclean\s+-[a-zA-Z]*f|\bfilter-(branch|repo)\b|\breflog\s+expire\b", s):
                return V("approbation", "git", "destruction-git", "suppression d'historique ou de fichiers non suivis")
        if re.search(r"\bgh\s+(pr\s+merge|pr\s+review\s+.*--approve|release\s+(create|delete)|repo\s+(create|delete|archive|edit)|secret\s+set|api\b.*(merge|-X\s*(DELETE|PUT)|--method\s*(DELETE|PUT)))", s):
            return V("approbation", "github", "github-sensible", "fusion, publication, création ou suppression sur GitHub")
        if re.search(r"\bvercel\b(?!\s+(dev|whoami|ls|list|logs|inspect|env\s+ls|--version|help)\b)|\bsupabase\s+(db\s+(push|reset)|functions\s+deploy|secrets\s+(set|unset)|projects\s+(create|delete)|link)\b|\bnpm\s+publish\b|\b(firebase|netlify|fly|flyctl|railway)\s+deploy\b|\bdocker\s+push\b|\bterraform\s+(apply|destroy)\b|\bkubectl\s+(apply|delete)\b|\bheroku\b", s):
            return V("approbation", "deploiement", "deploiement", "déploiement, migration ou publication en production")
        if re.search(r"\bnpm\s+run\s+db:reset\b|\bdropdb\b|\bDROP\s+(TABLE|DATABASE|SCHEMA)\b|\bTRUNCATE\s+TABLE\b", s, re.I):
            return V("approbation", "donnees", "destruction-donnees", "destruction ou réinitialisation de données")
        m = re.match(r"^(sudo\s+)?rm\s+(.*)$", s)
        if m and re.search(r"(^|\s)-[a-zA-Z]*[rR]", m.group(2)):
            cibles = [x for x in m.group(2).split() if not x.startswith("-")]
            dangereux = [x for x in cibles if x in ("/", "~", ".", "..", "*", "$HOME", "~/") or x.startswith(("~", "$HOME", "..")) or
                         (x.startswith("/") and not x.startswith(("/tmp/", "/private/tmp/", "/var/folders/")) and not _dans(x, cwd, DEPOT))]
            if dangereux or not cibles:
                return V("approbation", "suppression", "rm-hors-projet", f"suppression récursive hors du dépôt ou trop large : {' '.join(dangereux) or '(aucune cible)'}")
        if SECRETS.search(" " + s + " ") or re.search(r"\bsecurity\s+find-(generic|internet)-password\b|^printenv\b|^env\s*$|^export\s+-p\b", s):
            return V("approbation", "secret", "secret", "lecture d'un secret (clé, mot de passe, variables d'environnement)")
        if re.search(r"\b(curl|wget|http|https|xh)\b", s) and re.search(r"(\s-d\b|--data|\s-F\b|--form|\s-T\b|--upload-file|-X\s*(POST|PUT|PATCH|DELETE)|--request\s*(POST|PUT|PATCH|DELETE)|--post-data|--post-file)", s) \
                and not re.search(r"https?://(localhost|127\.0\.0\.1)(:\d+)?/", s):
            return V("approbation", "reseau", "envoi-reseau", "envoi de données vers un service extérieur")
        if re.match(r"^(scp|sftp|ssh|nc|ncat|telnet)\b", s) or re.match(r"^rsync\b.*\s\S+:\S*", s):
            return V("approbation", "reseau", "connexion-distante", "connexion ou copie vers une machine distante")
        if any(f in s for f in FICHIERS_GARDE) and re.search(r"(>|\btee\b|\bsed\s+[^|]*-i|\bperl\s+-[a-z]*i|\bmv\b|\bcp\b|\brm\b|\bchmod\b|\bln\b|\btruncate\b|\bpython[0-9.]*\s+-c\b|\bpatch\b|\bgit\s+(checkout|restore)\b)", s):
            return V("approbation", "garde-fous", "modif-garde-fous", "modification des garde-fous (hooks, réglages, registre, identité, serveur)")
    return Verdict()


def analyser_fichier(outil: str, chemin: str, cwd: str | None, agent: dict) -> Verdict:
    V = lambda *a, **k: Verdict(*a, outil="Edit", cible=os.path.normpath(os.path.join(cwd or os.getcwd(), os.path.expanduser(chemin))), **k)
    rel = _relatif_ile(chemin, cwd)
    try:
        rel_depot = str(Path(os.path.normpath(os.path.join(cwd or os.getcwd(), os.path.expanduser(chemin)))).relative_to(DEPOT)).replace(os.sep, "/")
    except ValueError:
        rel_depot = None
    if rel_depot in (".claude/settings.json", ".claude/settings.local.json"):
        return V("approbation", "garde-fous", "modif-garde-fous", f"modification d'un garde-fou : {rel_depot}", mode="fenetre")
    if rel == "operations/journal.jsonl":
        return V("bloquer", "journal", "ecriture-journal", "le journal des opérations ne s'écrit qu'à travers operations/ile.py")
    if rel and any(rel == f or (f.endswith("/") and rel.startswith(f)) for f in FICHIERS_GARDE):
        return V("approbation", "garde-fous", "modif-garde-fous", f"modification d'un garde-fou : {rel}", mode="fenetre")
    if _dans(chemin, cwd, DEPOT) is False and not str(Path(os.path.expanduser(chemin))).startswith(("/tmp/", "/private/tmp/", "/var/folders/")):
        if SECRETS.search(" " + chemin + " "):
            return V("approbation", "secret", "secret", "écriture d'un fichier de secrets")
        return V("approbation", "projet-externe", "ecriture-externe", "écriture hors du dépôt de l'île (projet externe)", mode="fenetre")
    role = (agent or {}).get("agent_type") or ""
    if rel is not None:
        if role.startswith("critique-") and not rel.startswith("conseil/"):
            return V("bloquer", "role", "critique-lecture", f"une critique ne modifie que les procès-verbaux du Conseil (tentative : {rel})")
        if role.startswith("chef-"):
            siege = _siege_du_chef(role)
            if siege and not (rel.startswith(f"maisons/{siege}/") or rel.startswith("conseil/")):
                return V("bloquer", "role", "chef-hors-maison", f"un directeur ne modifie que sa maison maisons/{siege}/ (tentative : {rel})")
    return Verdict()


def _siege_du_chef(role: str) -> str | None:
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
    if STOP.exists() and outil not in LECTURE:
        return Verdict("bloquer", "arret", "stop", "ARRÊT D'URGENCE actif (operations/STOP) : aucune action n'est permise tant que le président ne l'a pas levé", outil, str(ti)[:300])
    if outil == "Bash":
        return analyser_bash(ti.get("command") or "", cwd)
    if outil in ECRITURE:
        return analyser_fichier(outil, ti.get("file_path") or ti.get("notebook_path") or "", cwd, agent)
    if outil == "Read" and SECRETS.search(" " + (ti.get("file_path") or "") + " "):
        return Verdict("approbation", "secret", "secret", "lecture d'un fichier de secrets", "Read", ti.get("file_path"))
    if outil.startswith("mcp__") and re.search(r"merge|delete|create_repository|auto_merge|fork_repository|run_secret|actions_run_trigger", outil):
        return Verdict("approbation", "github", "mcp-sensible", f"outil distant sensible : {outil}", outil, json.dumps(ti, sort_keys=True, ensure_ascii=False)[:1500])
    if outil.startswith("mcp__") and re.search(r"push_files|create_or_update_file", outil) and str(ti.get("branch", "")) in PROTEGEES:
        return Verdict("approbation", "github", "mcp-branche-protegee", "écriture distante sur une branche protégée", outil, json.dumps(ti, sort_keys=True, ensure_ascii=False)[:1500])
    return Verdict()


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
    sys.path.insert(0, str(OPS_DIR))
    import ile
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
    sys.exit(main())
