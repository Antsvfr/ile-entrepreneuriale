/* Vérification publique du registre de l'île — dans le navigateur (ou sous Node), sans rien envoyer nulle part.

   Reproduit orchestrateur/ile.py `verifier` : numérotation, chaînage (`prec`), empreinte SHA-256 de chaque événement,
   actes présidentiels (preuve de possession des identités, signature Ed25519 de la clé en vigueur, actes réservés).
   Ed25519 : vérification seulement (RFC 8032 §5.1.7), portage de presidence/signature.py. Aucune clé privée ici.

   Piège évité : Python écrit `39.0` là où JavaScript réécrirait `39`. La lecture garde donc le texte exact de chaque
   nombre, et la sérialisation canonique reproduit json.dumps(sort_keys=True, ensure_ascii=False, separators=(",", ":")).
   Les listes TYPES_PRESIDENTIELS et RESERVE_PRESIDENT viennent de l'instantané (exportées par le code Python lui-même). */
(function (racine) {
  "use strict";

  // ------------------------------------------------------------------ JSON fidèle au texte
  function lireJSON(t) {
    let i = 0;
    const erreur = () => new Error("JSON invalide (position " + i + ")");
    const blancs = () => { while (i < t.length && " \t\n\r".includes(t[i])) i++; };
    function chaine() {
      if (t[i] !== '"') throw erreur();
      const debut = i++;
      while (t[i] !== '"') { if (t[i] === "\\") i++; i++; if (i >= t.length) throw erreur(); }
      i++;
      return JSON.parse(t.slice(debut, i));
    }
    function valeur() {
      blancs();
      const c = t[i];
      if (c === "{") {
        i++; const o = new Map(); blancs();
        if (t[i] === "}") { i++; return o; }
        for (;;) {
          blancs(); const k = chaine(); blancs();
          if (t[i++] !== ":") throw erreur();
          o.set(k, valeur()); blancs();
          const s = t[i++]; if (s === "}") return o; if (s !== ",") throw erreur();
        }
      }
      if (c === "[") {
        i++; const a = []; blancs();
        if (t[i] === "]") { i++; return a; }
        for (;;) { a.push(valeur()); blancs(); const s = t[i++]; if (s === "]") return a; if (s !== ",") throw erreur(); }
      }
      if (c === '"') return chaine();
      for (const [mot, v] of [["true", true], ["false", false], ["null", null]]) if (t.startsWith(mot, i)) { i += mot.length; return v; }
      const m = /^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?/.exec(t.slice(i));
      if (!m) throw erreur();
      i += m[0].length;
      return { nombre: m[0] };
    }
    const v = valeur(); blancs();
    if (i !== t.length) throw erreur();
    return v;
  }

  const comparerPy = (a, b) => {   // ordre de Python : points de code (et non unités UTF-16)
    const A = [...a], B = [...b];
    for (let k = 0; k < Math.min(A.length, B.length); k++) { const d = A[k].codePointAt(0) - B[k].codePointAt(0); if (d) return d; }
    return A.length - B.length;
  };
  function echapper(s) {
    let r = '"';
    for (const ch of s) {
      const c = ch.codePointAt(0);
      if (ch === '"') r += '\\"'; else if (ch === "\\") r += "\\\\";
      else if (c === 8) r += "\\b"; else if (c === 12) r += "\\f"; else if (c === 10) r += "\\n"; else if (c === 13) r += "\\r"; else if (c === 9) r += "\\t";
      else if (c < 0x20) r += "\\u" + c.toString(16).padStart(4, "0");
      else r += ch;
    }
    return r + '"';
  }
  function canon(v, sans) {
    if (v instanceof Map) {
      const cles = [...v.keys()].filter(k => !(sans && sans.includes(k))).sort(comparerPy);
      return "{" + cles.map(k => echapper(k) + ":" + canon(v.get(k))).join(",") + "}";
    }
    if (Array.isArray(v)) return "[" + v.map(x => canon(x)).join(",") + "]";
    if (v === null) return "null";
    if (v === true) return "true";
    if (v === false) return "false";
    if (typeof v === "string") return echapper(v);
    return v.nombre;
  }
  const valeurJS = v => v instanceof Map ? Object.fromEntries([...v].map(([k, x]) => [k, valeurJS(x)])) :
    Array.isArray(v) ? v.map(valeurJS) : (v && typeof v === "object" ? Number(v.nombre) : v);

  // ------------------------------------------------------------------ empreintes
  const sousCrypto = () => {
    const c = racine.crypto && racine.crypto.subtle;
    if (!c) throw new Error("WebCrypto indisponible (page ouverte hors HTTPS ?)");
    return c;
  };
  const octets = s => new TextEncoder().encode(s);
  const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("");
  const deHex = h => { if (!/^([0-9a-f]{2})*$/i.test(h || "")) return null; const b = new Uint8Array(h.length / 2); for (let k = 0; k < b.length; k++) b[k] = parseInt(h.substr(2 * k, 2), 16); return b; };
  const sha256 = async b => hex(await sousCrypto().digest("SHA-256", b));
  const sha512 = async b => new Uint8Array(await sousCrypto().digest("SHA-512", b));
  const concat = (...l) => { const r = new Uint8Array(l.reduce((n, x) => n + x.length, 0)); let o = 0; for (const x of l) { r.set(x, o); o += x.length; } return r; };

  // ------------------------------------------------------------------ Ed25519 (vérification), BigInt
  const p = 2n ** 255n - 19n, L = 2n ** 252n + 27742317777372353535851937790883648493n;
  const mod = (a, m = p) => ((a % m) + m) % m;
  const puiss = (b, e, m = p) => { let r = 1n; b = mod(b, m); while (e > 0n) { if (e & 1n) r = r * b % m; b = b * b % m; e >>= 1n; } return r; };
  const d = mod(-121665n * puiss(121666n, p - 2n)), I = puiss(2n, (p - 1n) / 4n);
  const lireEntier = b => { let r = 0n; for (let k = b.length - 1; k >= 0; k--) r = (r << 8n) + BigInt(b[k]); return r; };
  function retrouverX(y, signe) {
    if (y >= p) return null;
    const x2 = mod((y * y - 1n) * puiss(d * y * y + 1n, p - 2n));
    if (x2 === 0n) return signe ? null : 0n;
    let x = puiss(x2, (p + 3n) / 8n);
    if (mod(x * x - x2) !== 0n) x = x * I % p;
    if (mod(x * x - x2) !== 0n) return null;
    if (Number(x & 1n) !== signe) x = p - x;
    return x;
  }
  const ajouter = (P, Q) => {
    const A = mod((P[1] - P[0]) * (Q[1] - Q[0])), B = mod((P[1] + P[0]) * (Q[1] + Q[0])), C = mod(2n * P[3] * Q[3] * d), D = mod(2n * P[2] * Q[2]);
    const E = B - A, F = D - C, G = D + C, H = B + A;
    return [mod(E * F), mod(G * H), mod(F * G), mod(E * H)];
  };
  const multiplier = (s, P) => { let Q = [0n, 1n, 1n, 0n]; while (s > 0n) { if (s & 1n) Q = ajouter(Q, P); P = ajouter(P, P); s >>= 1n; } return Q; };
  const egaux = (P, Q) => mod(P[0] * Q[2] - Q[0] * P[2]) === 0n && mod(P[1] * Q[2] - Q[1] * P[2]) === 0n;
  const gy = mod(4n * puiss(5n, p - 2n)), gx = retrouverX(gy, 0), G = [gx, gy, 1n, mod(gx * gy)];
  function decompresser(b) {
    if (!b || b.length !== 32) return null;
    let y = lireEntier(b); const signe = Number(y >> 255n); y &= (1n << 255n) - 1n;
    const x = retrouverX(y, signe);
    return x === null ? null : [x, y, 1n, mod(x * y)];
  }
  async function ed25519Verifier(publiqueHex, message, sigHex) {
    const A_ = deHex(publiqueHex), sig = deHex(sigHex);
    if (!A_ || !sig || A_.length !== 32 || sig.length !== 64) return false;
    const A = decompresser(A_), R = decompresser(sig.slice(0, 32));
    if (!A || !R) return false;
    const s = lireEntier(sig.slice(32));
    if (s >= L) return false;
    const h = lireEntier(await sha512(concat(sig.slice(0, 32), A_, message))) % L;
    return egaux(multiplier(s, G), ajouter(R, multiplier(h, A)));
  }

  // ------------------------------------------------------------------ vérification du journal (miroir de ile.py)
  const GENESE = "0".repeat(64);
  async function verifierJournal(texte, regles) {
    const typesPres = new Set(regles.types_presidentiels), reserve = new Set(regles.reserve_president.map(x => x.join(">")));
    const lignes = texte.split("\n").filter(l => l.trim());
    const erreurs = [];
    let prec = GENESE, ident = null, actes = 0, signes = 0;
    const cache = new Map();
    const signatureValide = async (ev, cle) => {
      const sig = ev.get("signature");
      if (!cle || !sig) return false;
      const k = ev.get("hash") + cle + sig;
      if (!cache.has(k)) cache.set(k, await ed25519Verifier(cle, octets(canon(ev, ["hash", "signature"])), sig));
      return cache.get(k);
    };
    for (let n = 1; n <= lignes.length; n++) {
      let ev;
      try { ev = lireJSON(lignes[n - 1]); } catch (e) { erreurs.push(`ligne ${n} illisible (${e.message})`); prec = null; continue; }
      const id = ev.get("id"), num = ev.get("n");
      if (!num || Number(num.nombre) !== n) erreurs.push(`${id} : numéro ${num && num.nombre} au lieu de ${n} (ligne insérée ou supprimée)`);
      if (ev.get("prec") !== prec) erreurs.push(`${id} : chaînage rompu (la ligne précédente a été modifiée ou retirée)`);
      if (await sha256(octets(canon(ev, ["hash"])))  !== ev.get("hash")) erreurs.push(`${id} : contenu modifié après écriture`);
      prec = ev.get("hash");
      // actes présidentiels
      const t = ev.get("type"), auteur = ev.get("auteur"), role = auteur instanceof Map ? auteur.get("role") : null, don = ev.get("donnees");
      const transition = don instanceof Map ? `${don.get("de")}>${don.get("vers")}` : "";
      const presidentiel = t === "president.identite" || role === "president" || typesPres.has(t) || (t === "mission.statut" && reserve.has(transition));
      if (!presidentiel) continue;
      actes++;
      let motif = null;
      if (t === "president.identite") {
        const nouvelle = don instanceof Map ? don.get("cle_publique") : null;
        if (!nouvelle || !(await ed25519Verifier(nouvelle, octets("possession:" + nouvelle), don.get("preuve") || ""))) motif = "preuve de possession de la nouvelle clé absente ou fausse";
        else if (ident === null) motif = (await signatureValide(ev, nouvelle)) ? null : "identité initiale non signée par sa propre clé";
        else motif = (await signatureValide(ev, ident)) ? null : "changement d'identité non signé par la clé présidentielle en vigueur";
        if (!motif) ident = nouvelle;
      } else if (ident === null) motif = "aucune identité présidentielle n'existait à ce moment";
      else if (role !== "president") motif = "acte réservé au président, inscrit par un autre auteur";
      else if (!(await signatureValide(ev, ident))) motif = "signature présidentielle absente ou falsifiée";
      if (motif) erreurs.push(`${id} : acte présidentiel invalide (${motif})`); else signes++;
    }
    return { ok: erreurs.length === 0, n: lignes.length, dernier: prec || GENESE, erreurs, actes_presidentiels: actes, actes_valides: signes, identite: ident };
  }

  // Artefacts gelés : empreinte du fichier publié comparée à celle inscrite au journal (chemins migrés résolus).
  function artefactsDuJournal(texte) {
    return texte.split("\n").filter(l => l.includes('"artefact.depose"')).map(l => valeurJS(lireJSON(l))).filter(e => e.type === "artefact.depose")
      .map(e => ({ id: e.id, chemin: e.donnees.chemin, sha256: e.donnees.sha256 }));
  }
  const emplacements = (chemin, anciens) => [chemin, ...anciens.filter(([a]) => chemin.startsWith(a)).map(([a, n]) => n + chemin.slice(a.length))];

  const api = { lireJSON, canon, valeurJS, sha256, ed25519Verifier, verifierJournal, artefactsDuJournal, emplacements, octets, deHex, hex };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else racine.IleVerification = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
