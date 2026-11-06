/* D'où viennent les données de l'île ?
   - « local »  : le serveur de l'île (./ile) répond sur /api/… — Résidence complète, actes signés possibles ;
   - « publie » : version web (GitHub Pages) — instantané en lecture seule (residence/instantane/), généré par
                  `./ile publier` avec le même code que le serveur. Aucune action, aucune signature, aucune connexion.
   Une seule règle pour toutes les pages (métropole, Résidence) : rien n'est simulé, ce qui n'est pas disponible le dit. */
(function (racine) {
  "use strict";
  const ICI = new URL(".", location.href);                       // dossier de la page : …/village/
  let INSTANTANE = new URL("../instantane/", ICI);                // …/residence/instantane/ en version publiée
  let mode = null, meta = null, journalComplet = null;

  async function detecter() {
    if (mode) return mode;
    if (!/\.github\.io$/i.test(location.hostname) && location.protocol !== "file:") {
      try {
        const r = await fetch("/api/sante", {cache: "no-store"});
        if (r.ok && ["Île Entrepreneuriale", "Île des Agents"].includes((await r.json()).ile)) {
          INSTANTANE = new URL("/residence/instantane/", location.origin);   // local : /village/ est un alias, l'instantané est sous /residence/
          return (mode = "local");
        }
      } catch (e) { /* pas de serveur */ }
    }
    return (mode = "publie");
  }
  async function lireInstantane(nom) {
    const r = await fetch(new URL(nom, INSTANTANE), {cache: "no-store"});
    if (!r.ok) throw new Error("instantané introuvable (" + nom + ")");
    return r.json();
  }
  async function infos() { await detecter(); if (!meta) meta = await lireInstantane("meta.json"); return meta; }
  // Fraîcheur : la dernière empreinte du journal publié doit être celle de l'instantané (pas seulement le même nombre de lignes).
  async function fraicheur() {
    const m = await infos(), t = await (await fetch(lien("fichier", m.journal), {cache: "no-store"})).text();
    const lignes = t.split("\n").filter(l => l.trim()); let dernier = null;
    try { dernier = JSON.parse(lignes[lignes.length - 1]).hash; } catch (e) {}
    return {a_jour: dernier === m.dernier_hash && lignes.length === m.evenements, evenements: lignes.length, dernier, instantane: m};
  }

  // Même contrat que les routes GET du serveur, servi depuis l'instantané en version publiée.
  async function get(chemin) {
    if ((await detecter()) === "local") {
      const r = await fetch(chemin, {cache: "no-store"});
      return r;
    }
    const u = new URL(chemin, location.origin), route = u.pathname;
    const fichiers = {"/api/residence": "residence.json", "/api/etat": "etat.json", "/api/verifier": "verifier.json", "/api/president": "president.json", "/api/organisation": "organisation.json"};
    let corps;
    if (route === "/api/journal") {
      if (!journalComplet) journalComplet = await lireInstantane("journal.json");
      let evs = journalComplet.evenements;                         // du plus récent au plus ancien
      const q = u.searchParams;
      if (q.get("siege")) evs = evs.filter(e => (e.donnees || {}).siege === q.get("siege"));
      if (q.get("type")) evs = evs.filter(e => e.type.startsWith(q.get("type")));
      const n = Math.max(1, Math.min(parseInt(q.get("n") || "200", 10) || 200, 2000));
      corps = {evenements: evs.slice(0, n), total: journalComplet.total};
    } else if (/^\/api\/agent\/[a-z0-9-]+$/.test(route)) {
      const o = await lireInstantane("organisation.json"), a = o.agents[route.split("/").pop()];
      if (!a) return new Response(JSON.stringify({erreur: "agent inconnu"}), {status: 404});
      corps = a;
    } else if (fichiers[route]) corps = await lireInstantane(fichiers[route]);
    else return new Response(JSON.stringify({erreur: "indisponible dans la version publiée"}), {status: 404});
    return new Response(JSON.stringify(corps), {status: 200, headers: {"Content-Type": "application/json"}});
  }

  // Adresses : courtes en local (/residence, /batiment/<id>), relatives en version publiée (sous-dossier GitHub Pages).
  function lien(cible, id) {
    const local = mode === "local";
    if (cible === "metropole") return local ? "/village/" : new URL("index.html", ICI).href;
    if (cible === "residence") return local ? "/residence" : new URL("residence.html", ICI).href;
    if (cible === "batiment") return local ? "/batiment/" + encodeURIComponent(id) : new URL("index.html?ouvrir=" + encodeURIComponent(id), ICI).href;
    if (cible === "verification") return new URL("verification.html", ICI).href;
    if (cible === "accueil") return local ? "/" : new URL("../../index.html", ICI).href;
    if (cible === "fichier") return local ? "/" + id : new URL("../../" + id, ICI).href;
    return "#";
  }

  racine.IleSource = {detecter, get, lien, infos, fraicheur, lireInstantane, get mode() { return mode; }};
})(window);
