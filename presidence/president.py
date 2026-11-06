"""Identité présidentielle : une phrase secrète que seul Anton connaît.

- La phrase n'est JAMAIS écrite sur disque. Elle sert à dériver (PBKDF2-HMAC-SHA256, 600 000 tours)
  une graine Ed25519, d'où une paire de clés. Seule la clé publique est inscrite au journal
  (événement `president.identite`).
- Toute action présidentielle est signée avec la clé privée, qui ne vit qu'en mémoire : le temps
  d'une commande dans un vrai terminal, ou d'une session déverrouillée de la Résidence.
- Tout le monde peut VÉRIFIER une signature avec la clé publique ; personne ne peut en FABRIQUER
  une sans la phrase. Un agent qui tourne sous le même utilisateur système peut lire tous les
  fichiers du projet : il n'y trouvera aucun secret.
"""
import hashlib
import hmac
import os
import secrets
import sys
import time
import unicodedata

# Processus confiné (garde, serveur, hooks, commandes présidentielles) : `signature` est chargé par son chemin exact,
# depuis la source (voir securite/confinement.py). Import ordinaire seulement hors confinement (tests).
if sys.modules.get("confinement") is not None:
    signature = sys.modules["confinement"].charger("signature")
else:
    import signature

ITERATIONS = 600_000
LONGUEUR_MIN = 12


class ErreurPresident(Exception):
    pass


def _graine(phrase: str, sel: bytes, iterations: int) -> bytes:
    p = unicodedata.normalize("NFC", phrase).encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", p, sel, int(iterations), 32)


def empreinte(publique_hex: str) -> str:
    return hashlib.sha256(bytes.fromhex(publique_hex)).hexdigest()[:16]


class ClePresident:
    """Clé privée en mémoire. Ne se sérialise pas, ne s'affiche pas."""

    def __init__(self, graine: bytes):
        self._graine = graine
        self.publique = signature.cle_publique(graine).hex()
        self.empreinte = empreinte(self.publique)
        self.creee = time.time()

    def signer(self, message: bytes) -> str:
        return signature.signer(self._graine, message).hex()

    def __repr__(self):
        return f"<ClePresident {self.empreinte}>"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("la clé présidentielle ne se sérialise pas")


def nouvelle_identite(phrase: str):
    """Crée une clé à partir d'une nouvelle phrase. Renvoie (clé, données publiques de l'identité)."""
    if len(phrase or "") < LONGUEUR_MIN:
        raise ErreurPresident(f"la phrase doit faire au moins {LONGUEUR_MIN} caractères (une phrase entière est idéale)")
    sel, iterations = secrets.token_bytes(16), ITERATIONS   # le nombre de tours réellement utilisé est inscrit dans l'identité
    cle = ClePresident(_graine(phrase, sel, iterations))
    return cle, {"cle_publique": cle.publique, "empreinte": cle.empreinte, "sel": sel.hex(),
                 "kdf": {"algo": "pbkdf2-hmac-sha256", "iterations": iterations}, "algo": "ed25519"}


def deverrouiller(phrase: str, identite: dict) -> ClePresident:
    """Recrée la clé à partir de la phrase et la compare à l'identité inscrite au journal."""
    if not identite:
        raise ErreurPresident("aucune identité présidentielle : la créer une fois avec « ./ile president » dans un terminal")
    cle = ClePresident(_graine(phrase or "", bytes.fromhex(identite["sel"]), int(identite["kdf"]["iterations"])))
    if not hmac.compare_digest(cle.publique, identite["cle_publique"]):
        raise ErreurPresident("phrase incorrecte")
    return cle


def verifier(publique_hex: str, message: bytes, sig_hex: str) -> bool:
    try:
        return signature.verifier(bytes.fromhex(publique_hex), message, bytes.fromhex(sig_hex))
    except (ValueError, TypeError):
        return False


def terminal_disponible() -> bool:
    """Vrai seulement dans un vrai terminal. Les agents (outil Bash de Claude Code) n'en ont pas."""
    try:
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
        os.close(fd)
        return True
    except OSError:
        return False


def demander_phrase(invite: str = "Phrase présidentielle : ") -> str:
    """Lit la phrase sur le terminal lui-même (jamais sur l'entrée standard, qu'un programme peut remplir)."""
    if not terminal_disponible():
        raise ErreurPresident("cette action exige un vrai terminal : lance-la toi-même dans Terminal (un agent ne le peut pas)")
    import getpass
    with open("/dev/tty", "r+") as tty:
        return getpass.getpass(invite, stream=tty)
