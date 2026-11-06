// Présidence → Décisions → Propositions à examiner.
// Lecture : /api/propositions (serveur local) ou instantané publié. Décisions : POST /api/proposition, seulement en local,
// avec session déverrouillée (clé présidentielle en mémoire du serveur), jeton anti-CSRF, confirmation explicite et
// version du dossier. Le serveur signe, inscrit, relit et vérifie ; cette page n'annonce une décision qu'après relecture.
"use strict";
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const quand = q => q ? new Date(q).toLocaleString("fr-FR", {dateStyle: "medium", timeStyle: "short"}) : "—";
const propre = (o, k) => o && Object.prototype.hasOwnProperty.call(o, k) ? o[k] : undefined;
const OUVERTS = ["soumise", "en_analyse", "en_attente_decision"], REFUSABLES = [...OUVERTS, "modifications_demandees"];
const FINAUX = ["approuvee", "refusee", "en_execution", "executee"];
const FILTRES = [
  ["toutes", "Toutes", p => true],
  ["attente", "En attente de décision", p => p.statut === "en_attente_decision"],
  ["analyse", "En cours d'analyse", p => p.statut === "soumise" || p.statut === "en_analyse"],
  ["modif", "Modifications demandées", p => p.statut === "modifications_demandees"],
  ["approuvees", "Approuvées", p => ["approuvee", "en_execution", "executee"].includes(p.statut)],
  ["refusees", "Refusées", p => p.statut === "refusee"],
  ["archivees", "Archivées", p => !!p.archivee],
];
const ACTIONS = {
  approuver: {libelle: "Approuver", cls: "ok"}, refuser: {libelle: "Refuser", cls: "bad"},
  modifier: {libelle: "Demander des modifications", cls: ""}, avis: {libelle: "Demander un avis", cls: ""},
};
let D = null, ORGA = null, MODE = null, FILTRE = "toutes", JETON = null;

const nomInst = id => (propre((ORGA || {}).entreprises, id) || {}).nom || id || "—";
const auteurTxt = a => a ? `${esc(a.role)} <span class="mono">(${esc({signature: "signé", run: "identité vérifiée", hook: "hook", declare: "identité déclarée"}[a.verifie] || a.verifie || "—")})</span>` : "—";
const soumises = () => Object.values(D.propositions).filter(p => p.statut !== "brouillon").sort((a, b) => (b.soumise || b.cree).localeCompare(a.soumise || a.cree));

// ------------------------------------------------------------------ accès : ce qui permet ou empêche une décision
function rendreAcces(){
  const a = D.acces, el = $("#acces");
  el.className = "acces" + (a.decision_possible ? " ok" : "");
  const boutons = [];
  if(a.mode === "local" && a.identite && !a.deverrouille) boutons.push(`<button class="btn dark" type="button" id="b-deverrouiller">Déverrouiller avec ma phrase</button>`);
  if(a.mode === "local" && a.identite && a.deverrouille && !a.activee) boutons.push(`<button class="btn dark" type="button" id="b-activer">Activer les décisions officielles</button>`);
  el.innerHTML = a.decision_possible
    ? `<b>Décisions officielles possibles.</b> Identité présidentielle inscrite, Présidence déverrouillée, décisions activées le ${esc(quand(D.activation.quand))} (<span class="mono">${esc(D.activation.evenement)}</span>). Chaque décision sera signée de votre clé.`
    : `<b>Décisions officielles bloquées.</b> Ce qui l'empêche aujourd'hui :<ol>${a.blocages.map(b => `<li>${esc(b)}</li>`).join("")}</ol>
       <div class="raison">Les boutons ci-dessous restent visibles mais inactifs : un bouton dans un navigateur ne prouve aucune autorité ; seule la signature de la clé présidentielle, vérifiée par le serveur, en est une.</div>
       ${boutons.length ? `<div class="actions">${boutons.join("")}</div>` : ""}`;
  $("#chip").innerHTML = a.mode === "publie" ? "🔒 Version publiée · lecture seule"
    : a.deverrouille ? `🔓 Déverrouillée <button type="button" id="b-verrouiller">Verrouiller</button>` : (a.identite ? "🔒 Verrouillée" : "🔒 Sans identité présidentielle");
  const pub = $("#public");
  pub.hidden = a.mode !== "publie";
  pub.innerHTML = `Version publiée (GitHub Pages) : instantané du registre en lecture seule. Le dépôt est <b>public</b> : propositions, avis et décisions sont lisibles par tous. Pour décider, ouvrez la Résidence locale avec <code>./ile</code>.`;
}

// ------------------------------------------------------------------ liste et filtres
function rendreFiltres(){
  const ps = soumises();
  $("#filtres").innerHTML = FILTRES.map(([k, l, f]) => `<button type="button" data-filtre="${k}" aria-pressed="${FILTRE === k}">${esc(l)} (${ps.filter(f).length})</button>`).join("");
}
function rendreListe(){
  const f = FILTRES.find(x => x[0] === FILTRE)[2], ps = soumises().filter(f), sel = selection();
  $("#liste").innerHTML = ps.length ? ps.map(p => `<button type="button" class="item" data-id="${esc(p.id)}" aria-current="${sel === p.id}">
      <span class="m">${esc(p.id)} · ${esc(nomInst(p.origine))}</span><br><span class="t">${esc(p.titre)}</span><br>
      <span class="statut ${esc(p.statut)}">${esc(p.libelle)}</span>${p.avis_en_attente.length ? ` <span class="m">· ${p.avis_en_attente.length} avis attendu(s)</span>` : ""}</button>`).join("")
    : `<p class="vide">Aucune proposition dans cette catégorie${soumises().length ? "" : " : aucune proposition n'a encore été soumise au registre"}.</p>`;
}
const selection = () => { try{ return decodeURIComponent(location.hash.slice(1)) || null; }catch(_){ return null; } };

// ------------------------------------------------------------------ fiche détaillée
function possibles(p){
  return {approuver: OUVERTS.includes(p.statut), refuser: REFUSABLES.includes(p.statut), modifier: OUVERTS.includes(p.statut) && !p.ancienne, avis: !FINAUX.includes(p.statut)};
}
function raisonAction(p, k){
  if(!possibles(p)[k]) return k === "modifier" && p.ancienne ? "demande de l'ancien format : pas d'auteur pour la modifier" : `impossible : proposition ${p.libelle.toLowerCase()}`;
  if(!D.acces.decision_possible) return D.acces.blocages[0];
  return "";
}
function rendreFiche(){
  const p = propre(D.propositions, selection());
  $("#a-p").textContent = p ? p.id : "Propositions à examiner";
  if(!p){ $("#fiche").innerHTML = `<p class="vide">${selection() ? "Proposition inconnue au registre." : "Choisissez une proposition."}</p>`; return; }
  const dec = p.decision;
  const pieces = p.pieces.length ? `<ul>${p.pieces.map(x => `<li><a href="${esc(IleSource.lien("fichier", x.chemin))}">${esc(x.chemin)}</a>${x.sha256 ? ` <span class="mono">sha256 ${esc(x.sha256.slice(0, 12))}…</span>` : ""}</li>`).join("")}</ul>` : `<p class="vide">Aucune pièce justificative.</p>`;
  const avis = p.avis.length ? p.avis.map(a => `<div class="avis ${esc(a.sens)}"><b>${esc(nomInst(a.institution))}</b> — avis <b>${esc(a.sens)}</b> · ${esc(quand(a.quand))} · ${auteurTxt(a.par)} <span class="mono">${esc(a.evenement)}</span><div class="texte">${esc(a.texte)}</div></div>`).join("") : `<p class="vide">Aucun avis rendu.</p>`;
  const demandes = p.demandes_avis.length ? `<ul>${p.demandes_avis.map(x => `<li>à <b>${esc(nomInst(x.destinataire))}</b> le ${esc(quand(x.quand))} par ${auteurTxt(x.par)} : « ${esc(x.question)} » — ${x.rendu ? `rendu (<span class="mono">${esc(x.rendu)}</span>)` : "<b>en attente</b>"}</li>`).join("")}</ul>` : `<p class="vide">Aucune demande d'avis.</p>`;
  const modifs = p.demandes_modification.map(m => `<div class="avis reserve"><b>Modifications demandées</b> le ${esc(quand(m.quand))}${m.echeance ? ` · échéance ${esc(m.echeance)}` : ""}<div class="texte">Observations : ${esc(m.observations)}\nAttendu : ${esc(m.attendus)}</div></div>`).join("");
  const suivi = dec && dec.sens === "approuvee" || p.mise_en_oeuvre || p.execution.debut ? `<h3>Suites données</h3>
    <p>Mise en œuvre : ${p.mise_en_oeuvre ? `confiée à <b>${esc(nomInst(p.mise_en_oeuvre.responsable))}</b>${p.mise_en_oeuvre.echeance ? `, échéance ${esc(p.mise_en_oeuvre.echeance)}` : ""} — ${esc(p.mise_en_oeuvre.modalites)}` : `<span class="vide">modalités pas encore définies</span>`}<br>
    Exécution : ${p.execution.debut ? `commencée le ${esc(quand(p.execution.debut.quand))}` : `<span class="vide">pas commencée</span>`}${p.execution.fin ? `, terminée le ${esc(quand(p.execution.fin.quand))}` : ""}<br>
    ${p.execution.resultat ? `Résultats transmis au président : <span class="texte">${esc(p.execution.resultat)}</span><br>` : ""}
    Réception par les institutions : ${dec ? (dec.destinataires || []).map(i => `${esc(nomInst(i))} ${p.receptions.some(r => r.institution === i) ? "✔ accusé de réception" : "(transmise, pas encore d'accusé)"}`).join(" · ") : "—"}</p>` : "";
  const barre = Object.entries(ACTIONS).map(([k, a]) => { const r = raisonAction(p, k);
    return `<button class="btn ${a.cls}" type="button" data-action="${k}" ${r ? `disabled title="${esc(r)}" aria-describedby="raison-${k}"` : ""}>${esc(a.libelle)}</button>`; }).join("")
    + `<button class="btn" type="button" id="b-historique" aria-controls="historique">Consulter l'historique</button>`;
  const raisons = Object.keys(ACTIONS).map(k => raisonAction(p, k)).filter(Boolean);
  $("#fiche").innerHTML = `<div class="mono">${esc(p.id)} · version du dossier <span title="${esc(p.version)}">${esc(p.version.slice(0, 12))}…</span></div>
    <h2 style="margin-top:4px">${esc(p.titre)}</h2>
    <span class="statut ${esc(p.statut)}">${esc(p.libelle)}</span>${p.archivee ? ` <span class="statut">Archivée</span>` : ""}${p.ancienne ? ` <span class="mono">demande de décision de l'ancien format</span>` : ""}
    <div class="meta">
      <div><b>Auteur</b>${auteurTxt(p.auteur)}</div><div><b>Origine</b>${esc(nomInst(p.origine))}</div>
      <div><b>Soumise le</b>${esc(quand(p.soumise))}</div><div><b>Catégorie</b>${esc(p.categorie)}</div>
      <div><b>Coût ou ressources</b>${esc(p.cout || "non renseigné par l'auteur")}</div>
      <div><b>Institutions concernées</b>${p.institutions.map(i => esc(nomInst(i))).join(", ") || "—"}</div>
    </div>
    ${dec ? `<div class="resultat ${dec.sens === "approuvee" ? "ok" : "ko"}"><b>Décision : ${dec.sens === "approuvee" ? "approuvée" : "refusée"}</b> le ${esc(quand(dec.quand))} par ${auteurTxt(dec.par)} — acte <span class="mono">${esc(dec.evenement)}</span>${dec.motif ? `<br>Motif : ${esc(dec.motif)}` : ""}${dec.conditions ? `<br>Conditions : ${esc(dec.conditions)}` : ""}${dec.rectifie ? `<br>Rectifie la décision <span class="mono">${esc(dec.rectifie)}</span>` : ""}</div>` : ""}
    <h3>Description</h3><div class="texte">${esc(p.description)}</div>
    <h3>Objectif</h3><div class="texte">${esc(p.objectif)}</div>
    <h3>Conséquences attendues</h3><div class="texte">${esc(p.consequences || "non renseignées")}</div>
    <h3>Risques identifiés</h3>${p.risques.length ? `<ul>${p.risques.map(r => `<li>${esc(r)}</li>`).join("")}</ul>` : `<p class="vide">Aucun risque déclaré par l'auteur.</p>`}
    <h3>Avis</h3>${avis}<h3>Demandes d'avis</h3>${demandes}
    ${modifs ? `<h3>Demandes de modification</h3>${modifs}` : ""}
    <h3>Pièces justificatives</h3>${pieces}
    ${suivi}
    <div class="barre" role="group" aria-label="Décision présidentielle">${barre}</div>
    ${raisons.length ? `<p class="raison" id="raison-approuver">${esc([...new Set(raisons)].join(" · "))}</p>` : ""}
    <section id="historique" hidden><h3>Historique complet (registre)</h3><div class="table"><table><thead><tr><th>Quand</th><th>Action</th><th>Par</th><th>Événement</th></tr></thead><tbody>
      ${p.historique.map(h => `<tr><td>${esc(quand(h.quand))}</td><td>${esc(h.action)}${h.motif ? `<br><span class="mono">motif : ${esc(h.motif)}</span>` : ""}${h.note ? `<br><span class="mono">note : ${esc(h.note)}</span>` : ""}</td><td>${esc(h.par)} <span class="mono">(${esc(h.verifie)})</span></td><td class="mono">${esc(h.evenement)}</td></tr>`).join("")}
    </tbody></table></div></section>`;
}

// ------------------------------------------------------------------ fenêtres de confirmation
function dialogue(k, p){
  $("#resultat").innerHTML = "";                            // aucun ancien résultat ne peut passer pour celui de cette décision
  const dest = (p.institutions.length ? p.institutions : [p.origine]).map(nomInst).join(", ");
  const conseq = {
    approuver: `La proposition devient <b>approuvée</b>. La décision, signée de votre clé, est inscrite au registre et transmise à : <b>${esc(dest)}</b>. Elle ne pourra plus être modifiée ; seule une rectification signée et motivée, nouvel acte, pourra la corriger. Les modalités de mise en œuvre seront ensuite définies et l'exécution suivie jusqu'aux résultats.`,
    refuser: `La proposition devient <b>refusée</b> et est archivée. Le motif est inscrit au registre avec la décision signée et transmis à : <b>${esc(dest)}</b> (dont l'auteur). Elle ne pourra plus être modifiée ; seule une rectification signée et motivée pourra la corriger.`,
    modifier: `La proposition retourne à son auteur, en <b>attente de modifications</b>. Vos observations sont inscrites au registre ; l'historique du dossier est conservé. L'auteur la modifie puis la resoumet ; elle reviendra dans votre boîte.`,
    avis: `La demande d'avis est inscrite au registre et suivie jusqu'à la réponse. Un avis, favorable ou défavorable, <b>ne décide rien</b> : la décision reste la vôtre.`,
  }[k];
  const champs = {
    approuver: `<label>Motif (facultatif) <textarea name="motif" rows="2" maxlength="2000"></textarea></label><label>Conditions de mise en œuvre (facultatif) <textarea name="conditions" rows="2" maxlength="2000"></textarea></label>`,
    refuser: `<label>Motif du refus (obligatoire) <textarea name="motif" rows="3" maxlength="2000" required></textarea></label>`,
    modifier: `<label>Observations (obligatoire) <textarea name="observations" rows="3" maxlength="4000" required></textarea></label><label>Modifications attendues (obligatoire) <textarea name="attendus" rows="3" maxlength="4000" required></textarea></label><label>Échéance (facultatif) <input type="date" name="echeance"></label>`,
    avis: `<label>Destinataire <select name="destinataire" required>${Object.values((ORGA || {}).entreprises || {}).sort((a, b) => (a.type === b.type ? a.nom.localeCompare(b.nom) : a.type === "institution" ? -1 : 1)).map(e => `<option value="${esc(e.id)}">${esc(e.nom)}</option>`).join("")}</select></label><label>Question posée (obligatoire) <textarea name="question" rows="3" maxlength="2000" required></textarea></label><label>Échéance (facultatif) <input type="date" name="echeance"></label>`,
  }[k];
  $("#dlg-f").innerHTML = `<h3 id="dlg-t">${esc(ACTIONS[k].libelle)} — ${esc(p.id)}</h3>
    <div class="recap"><b>${esc(p.titre)}</b> · ${esc(nomInst(p.origine))} · ${esc(p.libelle)}<div class="texte" style="margin-top:6px">${esc(p.description)}</div>
      <div style="margin-top:6px"><b>Objectif :</b> ${esc(p.objectif)}<br><b>Conséquences attendues :</b> ${esc(p.consequences || "—")}<br><b>Coût :</b> ${esc(p.cout || "non renseigné")}<br><b>Risques :</b> ${esc(p.risques.join(" ; ") || "aucun déclaré")}<br><b>Institutions concernées :</b> ${esc(dest)}</div>
      ${p.avis_en_attente.length ? `<div class="raison">Attention : ${p.avis_en_attente.length} avis demandé(s) ne sont pas encore rendus.</div>` : ""}</div>
    <div class="consequence">${conseq}</div>${champs}
    <label>Confirmation : recopiez l'identifiant <span class="mono">${esc(p.id)}</span> <input name="confirmation" autocomplete="off"></label>
    <div class="barre"><button class="btn ${ACTIONS[k].cls || "dark"}" type="submit" value="ok">Confirmer : ${esc(ACTIONS[k].libelle.toLowerCase())}</button><button class="btn" type="button" id="dlg-annuler">Annuler</button></div>
    <p class="raison" id="dlg-err" role="alert"></p>`;
  $("#dlg-annuler").onclick = () => $("#dlg").close();
  $("#dlg-f").onsubmit = async ev => {
    ev.preventDefault();
    const f = new FormData($("#dlg-f")), corps = {action: k, id: p.id, version: p.version};
    for(const [n, v] of f.entries()) corps[n] = String(v).trim();
    if(corps.confirmation !== p.id){ $("#dlg-err").textContent = "Confirmation incorrecte : recopiez exactement l'identifiant."; return; }
    if(k === "refuser" && !corps.motif){ $("#dlg-err").textContent = "Le motif du refus est obligatoire."; return; }
    await envoyer(corps, p.id);
  };
  $("#dlg").showModal();
}
function dialogueActivation(){
  $("#resultat").innerHTML = "";
  $("#dlg-f").innerHTML = `<h3 id="dlg-t">Activer les décisions officielles</h3>
    <div class="consequence">${esc(D.acces.declaration)}</div>
    <p>Cet acte est signé de votre clé, inscrit au registre, et ne se fait qu'une fois. Ensuite, chacune de vos décisions sur une proposition sera un acte officiel signé.</p>
    <label>Confirmation : saisissez <span class="mono">ACTIVER</span> <input name="confirmation" autocomplete="off" required></label>
    <div class="barre"><button class="btn dark" type="submit">Activer</button><button class="btn" type="button" id="dlg-annuler">Annuler</button></div><p class="raison" id="dlg-err" role="alert"></p>`;
  $("#dlg-annuler").onclick = () => $("#dlg").close();
  $("#dlg-f").onsubmit = async ev => { ev.preventDefault(); const c = new FormData($("#dlg-f")).get("confirmation");
    if(c !== "ACTIVER"){ $("#dlg-err").textContent = "Saisissez exactement ACTIVER."; return; } await envoyer({action: "activer", confirmation: "ACTIVER"}, null); };
  $("#dlg").showModal();
}

// ------------------------------------------------------------------ envoi : jamais d'annonce sans confirmation du registre
async function jeton(){ if(!JETON){ const r = await fetch("/api/session", {cache: "no-store"}); JETON = (await r.json()).jeton; } return JETON; }
async function post(chemin, corps){
  const r = await fetch(chemin, {method: "POST", headers: {"Content-Type": "application/json", "X-Ile-Jeton": await jeton()}, body: JSON.stringify(corps), cache: "no-store"});
  let j = {}; try{ j = await r.json(); }catch(_){}
  return {status: r.status, j};
}
async function envoyer(corps, pid){
  if(MODE !== "local"){ $("#dlg-err").textContent = "Version publiée : aucune décision n'est possible ici."; return; }
  const bouton = $("#dlg-f button[type=submit]"); bouton.disabled = true; $("#dlg-err").textContent = "Signature et inscription au registre…";
  let r;
  try{ r = await post("/api/proposition", corps); }catch(e){ $("#dlg-err").textContent = "Le serveur de l'île ne répond pas : rien n'a été enregistré."; bouton.disabled = false; return; }
  if(r.status === 401){ $("#dlg").close(); ouvrirVerrou(); return; }
  if(r.status !== 200 || !r.j.ok || !r.j.evenement || !r.j.hash){ $("#dlg-err").textContent = "Refusé, rien n'a été enregistré : " + (r.j.erreur || "erreur " + r.status); bouton.disabled = false; return; }
  await charger();                                         // relecture du registre avant toute annonce
  const p = pid ? propre(D.propositions, pid) : null;
  const confirme = pid ? !!(p && p.historique.some(h => h.evenement === r.j.evenement)) : !!(D.activation && D.activation.evenement === r.j.evenement);
  $("#dlg").close();
  $("#resultat").innerHTML = confirme
    ? `<div class="resultat ok"><b>${pid ? "Décision enregistrée au registre" : "Décisions officielles activées"}</b> : acte <span class="mono">${esc(r.j.evenement)}</span> (${esc(r.j.type)}), signé de votre clé et vérifié par le serveur, empreinte <span class="mono">${esc(r.j.hash.slice(0, 16))}…</span>${p ? ` — relu au registre : statut « ${esc(p.libelle)} »` : ""}.</div>`
    : `<div class="resultat ko"><b>Le serveur a répondu, mais la relecture du registre ne retrouve pas l'acte ${esc(r.j.evenement)}.</b> Ne considérez pas la décision comme prise : rechargez la page et vérifiez le journal.</div>`;
}

// ------------------------------------------------------------------ verrou
function ouvrirVerrou(){ $("#lock-err").textContent = ""; $("#dlg-lock").showModal(); $("#phrase").focus(); }
$("#lock-annuler").onclick = () => $("#dlg-lock").close();
$("#lock-f").onsubmit = async ev => {
  ev.preventDefault();
  const r = await post("/api/president/deverrouiller", {phrase: $("#phrase").value}); $("#phrase").value = "";
  if(r.status !== 200){ $("#lock-err").textContent = r.j.erreur || "Échec du déverrouillage."; return; }
  $("#dlg-lock").close(); await charger();
};

// ------------------------------------------------------------------ chargement et événements
async function charger(){
  const [d, o] = await Promise.all([IleSource.get("/api/propositions").then(r => r.json()), IleSource.get("/api/organisation").then(r => r.json()).catch(() => null)]);
  D = d; ORGA = o;
  rendreAcces(); rendreFiltres(); rendreListe(); rendreFiche();
}
document.addEventListener("click", async ev => {
  const b = ev.target.closest("button"); if(!b) return;
  if(b.dataset.filtre){ FILTRE = b.dataset.filtre; rendreFiltres(); rendreListe(); }
  else if(b.dataset.id){ location.hash = b.dataset.id; }
  else if(b.dataset.action){ const p = propre(D.propositions, selection()); if(p && !raisonAction(p, b.dataset.action)) dialogue(b.dataset.action, p); }
  else if(b.id === "b-historique"){ const h = $("#historique"); h.hidden = !h.hidden; if(!h.hidden) h.scrollIntoView({behavior: "smooth", block: "start"}); }
  else if(b.id === "b-deverrouiller") ouvrirVerrou();
  else if(b.id === "b-activer") dialogueActivation();
  else if(b.id === "b-verrouiller"){ await post("/api/president/verrouiller", {}); await charger(); }
});
addEventListener("hashchange", () => { if(D){ rendreListe(); rendreFiche(); } });
(async () => {
  try{
    MODE = await IleSource.detecter();
    $("#n-met").href = IleSource.lien("metropole"); $("#n-res").href = IleSource.lien("residence"); $("#a-res").href = IleSource.lien("residence");
    await charger();
  }catch(e){ $("#acces").innerHTML = `<b>Propositions indisponibles</b> : ${esc(e.message)}`; }
})();
