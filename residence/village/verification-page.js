"use strict";
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const carte = (l, v, cls, sous) => `<div class="carte"><div class="l">${esc(l)}</div><div class="v ${cls || ""}">${v}</div>${sous ? `<div class="note">${sous}</div>` : ""}</div>`;
async function texte(url){ const r = await fetch(url, {cache:"no-store"}); if(!r.ok) throw new Error(url + " : " + r.status); return r.text(); }
async function verifier(){
  $("#go").disabled = true; $("#cartes").innerHTML = carte("Vérification", "…"); $("#erreurs").innerHTML = "";
  try{
    const mode = await IleSource.detecter();
    $("#n-acc").href = IleSource.lien("accueil"); $("#n-met").href = IleSource.lien("metropole"); $("#n-res").href = IleSource.lien("residence");
    const m = await IleSource.infos();
    let r;
    if(mode === "publie"){
      r = await IleVerification.verifierJournal(await texte(IleSource.lien("fichier", m.journal)), m);
      $("#source").innerHTML = `Journal vérifié : <code>${esc(m.journal)}</code> tel que publié dans le dépôt. Instantané de la version web : ${esc(new Date(m.genere).toLocaleString("fr-FR"))}, ${esc(m.evenements)} événements, dernière empreinte <code>${esc(m.dernier_hash.slice(0,16))}…</code>.`;
    } else {   // le serveur local ne sert pas le journal brut : il le vérifie lui-même
      const v = await (await IleSource.get("/api/verifier")).json();
      r = {ok: v.ok, n: v.n, dernier: v.dernier, erreurs: v.erreurs, actes_presidentiels: null, actes_valides: null, identite: null};
      $("#source").textContent = "Résidence locale : vérification faite par le serveur de l'île (ile.py verifier).";
    }
    const accord = mode !== "publie" || r.dernier === m.dernier_hash;
    $("#cartes").innerHTML =
      carte("Journal", r.ok ? "Intègre" : "Altéré", r.ok ? "ok" : "ko", `${r.n} événements vérifiés`) +
      carte("Dernière empreinte", `<span class="mono">${esc(r.dernier.slice(0, 16))}…</span>`, accord ? "" : "att", accord ? "identique à celle de l'instantané publié" : "différente de l'instantané : régénérer la version web (./ile publier)") +
      (r.actes_presidentiels === null ? "" : carte("Actes présidentiels", `${esc(r.actes_valides)}/${esc(r.actes_presidentiels)}`, !r.actes_presidentiels ? "" : r.actes_valides === r.actes_presidentiels ? "ok" : "ko", r.actes_presidentiels ? "signatures Ed25519 valides" : "aucun acte présidentiel signé à vérifier"));
    $("#erreurs").innerHTML = r.erreurs.slice(0, 20).map(e => `<li>${esc(e)}</li>`).join("");
    $("#identite").innerHTML = r.identite ? `Clé publique en vigueur : <code>${esc(r.identite)}</code>`
      : (r.actes_presidentiels === null ? "Voir la Résidence locale." : "Aucune identité présidentielle n'est encore inscrite au journal : aucun acte ne peut être signé au nom du président. Le président la crée lui-même, dans un vrai terminal : <code>./ile president</code>.");
    const docs = await artefacts(mode === "publie" ? await texte(IleSource.lien("fichier", m.journal)) : null, m);
    if(docs && docs.alteres.length){   // un document gelé modifié ou disparu rend le registre NON intègre, comme ile.py verifier
      $("#cartes").firstElementChild.outerHTML = carte("Journal", "Altéré", "ko", `${esc(r.n)} événements · ${docs.alteres.length} document(s) gelé(s) modifié(s) ou introuvable(s)`);
      $("#erreurs").innerHTML += docs.alteres.map(x => `<li>${esc(x)}</li>`).join("");
    }
  }catch(e){ $("#cartes").innerHTML = carte("Vérification impossible", "—", "ko", esc(e.message)); }
  finally{ $("#go").disabled = false; }
}
async function artefacts(journalTexte, m){
  const tb = $("#artefacts");
  if(!journalTexte){ tb.innerHTML = `<tr><td colspan="3">Contrôlés par le serveur local (voir ci-dessus).</td></tr>`; return null; }
  const liste = IleVerification.artefactsDuJournal(journalTexte);
  if(!liste.length){ tb.innerHTML = `<tr><td colspan="3">Aucun document gelé.</td></tr>`; return {alteres: []}; }
  const lignes = [], alteres = [];
  for(const a of liste){
    const etats = [];
    for(const chemin of IleVerification.emplacements(a.chemin, m.anciens_chemins)){
      try{ const r = await fetch(IleSource.lien("fichier", chemin), {cache:"no-store"}); if(!r.ok) continue;
           const s = await IleVerification.sha256(new Uint8Array(await r.arrayBuffer())); etats.push([chemin, s === a.sha256]); }catch(_){}
    }
    if(!etats.length) alteres.push(`${a.id} : l'artefact ${a.chemin} est introuvable`);
    etats.filter(([, ok]) => !ok).forEach(([c]) => alteres.push(`${a.id} : l'artefact ${a.chemin} a changé depuis son dépôt (${c})`));
    const res = !etats.length ? `<span class="ko">introuvable</span>` : etats.map(([c, ok]) => `<span class="${ok ? "ok" : "ko"}">${ok ? "intact" : "MODIFIÉ"}</span> <code>${esc(c)}</code>`).join("<br>");
    lignes.push(`<tr><td><code>${esc(a.id)}</code></td><td><code>${esc(a.chemin)}</code></td><td>${res}</td></tr>`);
  }
  tb.innerHTML = lignes.join("");
  return {alteres};
}
$("#go").onclick = verifier;
verifier();
