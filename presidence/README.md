# Présidence

`president.py` (identité : phrase → PBKDF2-HMAC-SHA256 → graine Ed25519 ; seule la clé publique est inscrite au journal)
et `signature.py` (Ed25519, RFC 8032, Python standard). Aucun secret n'est stocké ici ni ailleurs sur disque.
Les décisions et autorisations présidentielles sont des événements signés du registre (`orchestrateur/registre/journal.jsonl`).
L'identité réelle n'existe pas encore : le président la crée lui-même (`./ile president`).
