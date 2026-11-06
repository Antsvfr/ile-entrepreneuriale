// Bureaux des entreprises (phase 3.4) : lecture seule de la projection du registre.
"use strict";
/* Bureaux des entreprises : vues générées UNIQUEMENT à partir de la projection du registre chaîné
   (/api/organisation en local, residence/instantane/organisation.json en version publiée). Aucune donnée inventée :
   ce qui n'existe pas au registre s'affiche comme tel. Consultation seulement : les actes passent par la ligne de
   commande (ile.py org …) et ses contrôles d'autorisation. */
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const quand = q => q ? new Date(q).toLocaleString("fr-FR", {dateStyle:"medium", timeStyle:"short"}) : "—";
const couleur = c => /^#[0-9a-f]{3,8}$/i.test(c || "") ? c : "#b8891c";
const STATUT = {en_execution:"En cours d'exécution", en_reunion:"En réunion", en_attente_validation:"En attente de validation", bloque:"Bloqué", suspendu:"Suspendu", disponible:"Disponible", hors_ligne:"Hors ligne"};
const MST = {proposee:"proposée", attente_president:"attend le président", planifiee:"planifiée", reportee:"reportée", en_cours:"en cours", bloquee:"bloquée", verification:"en vérification", terminee:"terminée", rejetee:"rejetée", abandonnee:"abandonnée"};
let O = null, MODE = null, PROPS = null;

// ------------------------------------------------------------------ données dérivées (calculées, jamais saisies)
const propre = (o, k) => o && Object.prototype.hasOwnProperty.call(o, k) ? o[k] : undefined;   // jamais une clé héritée (constructor, __proto__…)
const ag = id => propre(O.agents, id), po = id => propre(O.postes, id), en = id => propre(O.entreprises, id);
// un événement appartient à l'agent s'il le désigne, ou si son auteur est l'agent (définition, ou identifiant pour un rôle sans définition comme le Maire)
const estDe = (a, x) => x.agent === a.id || (!!x.auteur && (x.auteur === a.definition || x.auteur === a.id));
const roleDe = h => (h.auteur || {}).role;
// actes d'organisation signés par l'agent lui-même (ex. le Maire qui affecte un agent), en plus de ceux qui le concernent
const historiqueDe = a => { const vus = new Set(); return [...(a.historique || []), ...O.historique.filter(h => roleDe(h) && (roleDe(h) === a.id || roleDe(h) === a.definition))]
  .filter(h => !vus.has(h.evenement) && vus.add(h.evenement)); };
const subordonnes = pid => Object.values(O.postes).filter(p => p.superieur === pid);
const agentsDe = e => Object.values(O.agents).filter(a => a.entreprise === e);
const missionsDe = e => Object.values(O.missions).filter(m => m.siege === e);
const dernierEvenement = a => {
  const d = [...historiqueDe(a).map(h => h.quand), ...O.activite.filter(x => estDe(a, x)).map(x => x.quand), a.depuis].filter(Boolean).sort();
  return d[d.length - 1] || null;
};
function sousArbre(pid, vus = new Set()){ if(vus.has(pid)) return []; vus.add(pid); return subordonnes(pid).flatMap(p => [p.id, ...sousArbre(p.id, vus)]); }
function incoherences(eid){
  const out = [], ps = en(eid).postes;
  for(const p of ps){
    const vus = new Set(); let x = p.id;
    while(x){ if(vus.has(x)){ out.push(`cycle hiérarchique autour du poste ${x}`); break; } vus.add(x); x = (po(x) || {}).superieur; }
    if(p.superieur && !po(p.superieur)) out.push(`le poste ${p.id} a un supérieur inconnu (${p.superieur})`);
    if(p.departement && !propre(O.departements, p.departement)) out.push(`le poste ${p.id} cite un département inconnu (${p.departement})`);
    if(!p.titulaire) out.push(`poste non pourvu : ${p.titre} (${p.id})`);
  }
  if(en(eid).direction === "collégiale") out.push("direction collégiale : plusieurs postes de tête au même niveau (aucun directeur unique)");
  return [...new Set(out)];
}

// ------------------------------------------------------------------ composants
const liens = {
  entreprise: e => `#/e/${encodeURIComponent(e)}`, agent: a => `#/agent/${encodeURIComponent(a)}`, mission: m => `#/mission/${encodeURIComponent(m)}`,
  dep: (e, d) => `#/e/${encodeURIComponent(e)}/departement/${encodeURIComponent(d)}`, equipe: (e, p) => `#/e/${encodeURIComponent(e)}/equipe/${encodeURIComponent(p)}`,
};
function monogramme(a, taille = 44){   // provisoire (phase 4 : avatar) — couleur dérivée de la graine STABLE de l'agent
  const g = (a.apparence || {}).graine || "888888"; const h = parseInt(g.slice(0, 6), 16) % 360;
  const mots = String(a.nom || a.id).replace(/^(L['’]|Le\s+|La\s+|Les\s+)/i, "").split(/\s+/);
  const ini = mots.filter(w => /^[A-ZÀ-Ý]/.test(w)).slice(0, 2).map(w => w[0]).join("") || a.id[0].toUpperCase();
  return `<span class="mono-av" style="background:hsl(${h} 38% 38%);width:${taille}px;height:${taille}px" title="Identité visuelle provisoire (graine ${esc(g)}) — avatar en phase 4" aria-hidden="true">${esc(ini)}</span>`;
}
const statut = a => `<span class="statut st-${esc(a.statut)}" title="${esc(a.nature || "")}">${esc(STATUT[a.statut] || a.statut)}</span>`;
function carteAgent(a){
  const p = po(a.poste) || {};
  return `<a class="carte agent" href="${liens.agent(a.id)}">${monogramme(a)}<span><b>${esc(a.nom)}</b><br><span class="s">${esc(p.titre || "sans poste")}</span><br>${statut(a)}</span></a>`;
}
function tableMissions(ms, vide = "Aucune mission enregistrée."){
  if(!ms.length) return `<p class="vide">${vide}</p>`;
  return `<div class="table"><table><thead><tr><th>Mission</th><th>Statut</th><th>Agent</th><th>Priorité · échéance</th><th>Livrables</th></tr></thead><tbody>${ms.map(m =>
    `<tr><td><a href="${liens.mission(m.id)}">${esc(m.id)}</a><br>${esc(m.titre)}</td><td>${esc(MST[m.statut] || m.statut)}</td>
     <td>${m.attributaire ? `<a href="${liens.agent(m.attributaire)}">${esc((ag(m.attributaire) || {}).nom || m.attributaire)}</a>` : "<span class='src'>non attribuée</span>"}</td>
     <td>${esc(m.priorite_travail || "—")} · ${esc(m.echeance || "—")}</td><td>${m.livrables.length}${m.validee ? " · validée" : ""}</td></tr>`).join("")}</tbody></table></div>`;
}
function tableActivite(xs, vide = "Aucune activité enregistrée au registre."){
  if(!xs.length) return `<p class="vide">${vide}</p>`;
  return `<div class="table"><table><thead><tr><th>Quand</th><th>Événement</th><th>Par</th><th>Objet</th></tr></thead><tbody>${xs.slice(0, 40).map(x =>
    `<tr><td>${quand(x.quand)}</td><td><code>${esc(x.type)}</code><br><span class="src">${esc(x.evenement)}</span></td><td>${esc(x.auteur || "—")} <span class="src">(${esc(x.verifie || (x.auteur && x.auteur.verifie) || "—")})</span></td>
     <td>${x.mission ? `<a href="${liens.mission(x.mission)}">${esc(x.mission)}</a>` : ""}${x.agent ? ` <a href="${liens.agent(x.agent)}">${esc(x.agent)}</a>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
}
const activiteEntreprise = eid => {
  const ids = new Set(agentsDe(eid).flatMap(a => [a.definition, a.id]).filter(Boolean));
  return [...O.activite.filter(x => x.entreprise === eid || ids.has(x.auteur)), ...O.historique.filter(h => h.entreprise === eid).map(h => ({...h, auteur: (h.auteur || {}).role, verifie: (h.auteur || {}).verifie}))]
    .sort((a, b) => (b.quand || "").localeCompare(a.quand || ""));
};
function ariane(parts){
  $("#ariane").innerHTML = [`<a href="${esc(IleSource.lien("metropole"))}">Métropole</a>`, ...parts.map(([t, h]) => h ? `<a href="${h}">${esc(t)}</a>` : `<span>${esc(t)}</span>`)].join('<span class="sep">›</span>');
}
const bandeauPublic = () => MODE === "publie" ? `<div class="public">Version publiée : données du registre à la date de l'instantané, en lecture seule. Le dépôt est <b>public</b> : tout ce qui figure ici (organisation, missions, messages, réunions) est public.</div>` : "";

// ------------------------------------------------------------------ vues
function vueListe(){
  ariane([["Entreprises"]]);
  const es = Object.values(O.entreprises);
  return `<div class="kicker">Économie de l'île</div><h1>Entreprises et institutions</h1>${bandeauPublic()}
    <p class="lead">${es.length} organisations inscrites au cadastre · ${Object.keys(O.agents).length} agents · ${Object.keys(O.postes).length} postes. Les chantiers de la métropole n'ont pas encore d'entreprise.</p>
    <div class="grille">${es.map(e => `<a class="carte" href="${liens.entreprise(e.id)}"><div class="l">${esc(e.type)}</div><div class="v" style="font-size:22px;display:flex;gap:8px;align-items:center"><span style="width:12px;height:12px;border-radius:50%;background:${couleur(e.couleur)}"></span>${esc(e.nom)}</div>
      <div class="s">${e.effectif} collaborateur(s) · ${e.departements.length} département(s) · ${e.missions.en_cours} mission(s) en cours</div></a>`).join("")}</div>`;
}
function situation(e){
  const ms = missionsDe(e.id), act = activiteEntreprise(e.id);
  if(e.missions.bloquees) return `<span style="color:var(--bad)">En difficulté : ${e.missions.bloquees} mission(s) bloquée(s)</span>`;
  if(e.problemes_ouverts) return `<span style="color:var(--warn)">${e.problemes_ouverts} problème(s) ouvert(s) signalé(s)</span>`;
  if(e.agents_en_execution) return `<span style="color:var(--ok)">${e.agents_en_execution} agent(s) en exécution réelle</span>`;
  if(!act.length && !ms.length) return "Aucune activité enregistrée au registre";
  return "Aucune exécution en cours";
}
function vueEntreprise(eid){
  const e = en(eid); if(!e) return vueIntrouvable(`Aucune entreprise « ${eid} » au cadastre.`);
  ariane([["Entreprises", "#/"], [e.nom]]);
  const d = e.directeur && e.directeur.agent ? ag(e.directeur.agent) : null, ms = missionsDe(eid);
  const inc = incoherences(eid);
  return `<div class="kicker">${esc(e.type === "projet" ? "Entreprise" : "Institution")} · accueil</div>
    <h1><span class="pastille" style="background:${couleur(e.couleur)}"></span>${esc(e.nom)}</h1>${bandeauPublic()}
    <p class="lead">${esc(e.role || "")}</p>
    <div class="grille">
      <div class="carte"><div class="l">Direction générale</div><div class="v" style="font-size:20px">${d ? `<a href="${liens.agent(d.id)}">${esc(d.nom)}</a>` : esc(e.direction === "collégiale" ? "Collégiale" : "Aucun directeur")}</div><div class="s">${d ? esc(e.directeur.titre) : "voir l'organigramme"}</div></div>
      <div class="carte"><div class="l">Collaborateurs</div><div class="v">${e.effectif}</div><div class="s">${e.postes_non_pourvus} poste(s) non pourvu(s)</div></div>
      <div class="carte"><div class="l">Missions</div><div class="v">${e.missions.en_cours}</div><div class="s">en cours · ${e.missions.terminees} terminée(s) · ${e.missions.bloquees} bloquée(s) · ${e.missions.proposees} proposée(s)</div></div>
      <div class="carte"><div class="l">Situation</div><div class="v" style="font-size:17px;line-height:1.3">${situation(e)}</div><div class="s">d'après le registre</div></div>
    </div>
    <nav class="salles" aria-label="Espaces de l'entreprise">
      <a class="salle" href="#/e/${esc(eid)}/direction"><b>Bureau du directeur</b><span>Profil, organigramme sous sa direction, validations</span></a>
      <a class="salle" href="#/e/${esc(eid)}/organigramme"><b>Organigramme</b><span>${Object.keys(e.postes).length} poste(s), calculé depuis le registre</span></a>
      <a class="salle" href="#/e/${esc(eid)}/departements"><b>Départements</b><span>${e.departements.length} enregistré(s)</span></a>
      <a class="salle" href="#/e/${esc(eid)}/equipes"><b>Équipes</b><span>responsables et leurs agents</span></a>
      <a class="salle" href="#/e/${esc(eid)}/missions"><b>Missions</b><span>${ms.length} au registre</span></a>
      <a class="salle" href="#/e/${esc(eid)}/reunions"><b>Salle de réunion</b><span>réunions réellement inscrites</span></a>
      <a class="salle" href="#/e/${esc(eid)}/annuaire"><b>Annuaire</b><span>tous les collaborateurs</span></a>
    </nav>
    <h2>Décisions présidentielles reçues</h2>${decisionsRecues(eid)}
    ${inc.length ? `<h2>Points à vérifier dans l'organisation</h2>${inc.map(x => `<div class="alerte">${esc(x)}</div>`).join("")}` : ""}
    <h2>Dernières activités enregistrées</h2>${tableActivite(activiteEntreprise(eid))}`;
}
// décisions présidentielles adressées à cette entreprise (dérivées des actes signés : /api/propositions)
function decisionsRecues(eid){
  if(!PROPS) return `<p class="vide">Boîte des décisions indisponible.</p>`;
  const ds = propre(PROPS.boites, eid) || [];
  return ds.length ? `<div class="table"><table><thead><tr><th>Quand</th><th>Proposition</th><th>Décision</th><th>Réception</th></tr></thead><tbody>${ds.slice().sort((a, b) => b.quand.localeCompare(a.quand)).map(d =>
    `<tr><td>${quand(d.quand)}</td><td><a href="decisions.html#${encodeURIComponent(d.proposition)}">${esc(d.proposition)}</a> — ${esc(d.titre)}</td><td><b>${d.sens === "approuvee" ? "approuvée" : "refusée"}</b> <span class="src">${esc(d.evenement)}</span></td><td>${d.recue ? "accusé de réception inscrit" : "transmise, pas encore d'accusé"}</td></tr>`).join("")}</tbody></table></div>`
    : `<p class="vide">Aucune décision présidentielle adressée à cette entreprise au registre.</p>`;
}
function vueDirection(eid){
  const e = en(eid); if(!e) return vueIntrouvable("Entreprise inconnue.");
  ariane([["Entreprises", "#/"], [e.nom, liens.entreprise(eid)], ["Bureau du directeur"]]);
  const dp = e.directeur ? po(e.directeur.poste) : null, d = dp && dp.titulaire ? ag(dp.titulaire) : null;
  if(!dp) return `<h1>Bureau du directeur</h1>${bandeauPublic()}<p class="vide">${e.direction === "collégiale" ? "Direction collégiale : aucun directeur unique n'est inscrit (voir l'organigramme)." : "Aucun poste de direction inscrit au registre pour cette organisation."}</p>`;
  const sous = sousArbre(dp.id).map(po).filter(Boolean), equipeIds = new Set(sous.map(p => p.titulaire).filter(Boolean));
  const suivies = Object.values(O.missions).filter(m => m.attribuee_par === (d && d.id) || equipeIds.has(m.attributaire));
  const recus = O.messages.filter(m => d && (m.a === d.id || m.a === dp.id));
  const livres = suivies.flatMap(m => m.livrables.map(l => ({...l, mission: m.id})));
  const validations = Object.values(O.missions).filter(m => m.validee && d && m.validee.par === d.id);
  return `<div class="kicker">${esc(e.nom)} · bureau du directeur</div><h1>${d ? esc(d.nom) : "Poste non pourvu"}</h1>${bandeauPublic()}
    <div class="grille"><div class="carte">${d ? `<div class="agent">${monogramme(d, 56)}<span><b>${esc(dp.titre)}</b><br>${statut(d)}<br><a href="${liens.agent(d.id)}">Profil complet →</a></span></div>` : `<b>${esc(dp.titre)}</b><br><span class="s">non pourvu</span>`}</div>
      <div class="carte"><div class="l">Responsabilités (fonction)</div><div class="s">${esc(((O.fonctions[dp.fonction] || {}).permissions || []).map(p => p.replace(/_/g, " ")).join(" · ") || "—")}</div></div>
      <div class="carte"><div class="l">Sous sa direction</div><div class="v">${sous.length}</div><div class="s">poste(s), dont ${sous.filter(p => !p.titulaire).length} non pourvu(s)</div></div></div>
    <h2>Organigramme sous sa direction</h2>${arbre(dp.id, false)}
    <h2>Missions suivies</h2>${tableMissions(suivies, "Aucune mission attribuée par ce directeur ou à son équipe.")}
    <h2>Rapports et messages reçus</h2>${listeMessages(recus)}
    <h2>Livrables de son équipe</h2>${listeLivrables(livres)}
    <h2>Validations et décisions relevant de sa fonction</h2>${validations.length ? validations.map(m => `<div class="carte" style="margin:4px 0"><a href="${liens.mission(m.id)}">${esc(m.id)}</a> validée le ${quand(m.validee.quand)} — ${esc(m.validee.motif || "")}</div>`).join("") : `<p class="vide">Aucune validation enregistrée.</p>`}
    <h2>Historique de ses activités</h2>${d ? tableActivite(activiteAgent(d)) : `<p class="vide">—</p>`}`;
}
function listeMessages(ms){
  if(!ms.length) return `<p class="vide">Aucun message enregistré.</p>`;
  return ms.map(m => `<div class="carte" style="margin:6px 0"><div class="l">${quand(m.quand)} · ${esc(m.nature || "message")} · <span class="src">${esc(m.id)}</span></div>
    <b>${esc(m.sujet)}</b> — de <a href="${liens.agent(m.de)}">${esc(m.de)}</a> à ${propre(O.agents, m.a) ? `<a href="${liens.agent(m.a)}">${esc(m.a)}</a>` : esc(m.a)}${m.mission ? ` · <a href="${liens.mission(m.mission)}">${esc(m.mission)}</a>` : ""}<br>${esc(m.texte)}</div>`).join("");
}
function listeLivrables(ls){
  if(!ls.length) return `<p class="vide">Aucun livrable transmis.</p>`;
  return `<div class="table"><table><thead><tr><th>Livrable</th><th>Mission</th><th>Transmis</th><th>Empreinte</th></tr></thead><tbody>${ls.map(l =>
    `<tr><td><a href="${esc(IleSource.lien("fichier", l.chemin))}" target="_blank" rel="noopener">${esc(l.chemin)}</a>${l.note ? `<br><span class="src">${esc(l.note)}</span>` : ""}</td><td><a href="${liens.mission(l.mission)}">${esc(l.mission)}</a></td><td>${quand(l.quand)} par ${esc(l.par || "—")}</td><td><code>${esc(String(l.sha256).slice(0, 12))}…</code></td></tr>`).join("")}</tbody></table></div>`;
}
function vueDepartements(eid){
  const e = en(eid); ariane([["Entreprises", "#/"], [e.nom, liens.entreprise(eid)], ["Départements"]]);
  return `<h1>Départements</h1>${bandeauPublic()}${e.departements.length ? `<div class="grille">${e.departements.map(d => {
    const ps = Object.values(O.postes).filter(p => p.departement === d.id);
    return `<a class="carte" href="${liens.dep(eid, d.id)}"><div class="l">département</div><div class="v" style="font-size:22px">${esc(d.nom)}</div><div class="s">${ps.filter(p => p.titulaire).length} membre(s) · ${esc(d.mission || "")}</div></a>`; }).join("")}</div>`
    : `<p class="vide">Aucun département n'est enregistré au registre pour ${esc(e.nom)}. Un directeur (exécution vérifiée) ou le DG peut en créer un : <code>ile.py org departement …</code></p>`}`;
}
function vueDepartement(eid, did){
  const e = en(eid), d = propre(O.departements, did); if(!d || d.entreprise !== eid) return vueIntrouvable("Département inconnu dans cette entreprise.");
  ariane([["Entreprises", "#/"], [e.nom, liens.entreprise(eid)], ["Départements", `#/e/${esc(eid)}/departements`], [d.nom]]);
  const ps = Object.values(O.postes).filter(p => p.departement === did), resp = ps.slice().sort((a, b) => (a.niveau ?? 9) - (b.niveau ?? 9))[0];
  const membres = ps.map(p => p.titulaire).filter(Boolean).map(ag), ids = new Set(membres.map(a => a.id));
  const ms = Object.values(O.missions).filter(m => ids.has(m.attributaire));
  return `<div class="kicker">${esc(e.nom)} · département</div><h1>${esc(d.nom)}</h1>${bandeauPublic()}<p class="lead">Objectifs : ${esc(d.mission || "non renseignés au registre")}</p>
    <div class="grille"><div class="carte"><div class="l">Responsable</div>${resp && resp.titulaire ? carteAgent(ag(resp.titulaire)).replace('class="carte agent"', 'class="agent"') : `<p class="vide">${resp ? esc(resp.titre) + " — non pourvu" : "aucun poste"}</p>`}</div>
    <div class="carte"><div class="l">Créé</div><div class="s">${quand(d.cree.quand)} par ${esc((d.cree.auteur || {}).role)} <span class="src">${esc(d.cree.evenement)}</span></div></div></div>
    <h2>Membres</h2>${membres.length ? `<div class="grille">${membres.map(carteAgent).join("")}</div>` : `<p class="vide">Aucun membre : ${ps.length} poste(s), tous non pourvus.</p>`}
    <h2>Missions</h2>${tableMissions(ms)}<h2>Livrables</h2>${listeLivrables(ms.flatMap(m => m.livrables.map(l => ({...l, mission: m.id}))))}
    <h2>Activités</h2>${tableActivite(O.activite.filter(x => ids.has(x.agent) || membres.some(a => estDe(a, x))))}`;
}
function equipesDe(eid){ return en(eid).postes.filter(p => subordonnes(p.id).some(s => s.entreprise === eid)); }
function vueEquipes(eid){
  const e = en(eid); ariane([["Entreprises", "#/"], [e.nom, liens.entreprise(eid)], ["Équipes"]]);
  const eq = equipesDe(eid);
  return `<h1>Équipes</h1>${bandeauPublic()}<p class="lead">Une équipe = un responsable et les postes placés directement sous le sien (registre).</p>${eq.length ? `<div class="grille">${eq.map(p => {
    const r = p.titulaire ? ag(p.titulaire) : null;
    return `<a class="carte" href="${liens.equipe(eid, p.id)}"><div class="l">équipe de</div><div class="v" style="font-size:20px">${esc(r ? r.nom : p.titre + " (non pourvu)")}</div><div class="s">${subordonnes(p.id).length} poste(s) rattaché(s)</div></a>`; }).join("")}</div>`
    : `<p class="vide">Aucune équipe : aucun poste de ${esc(e.nom)} n'a encore de subordonné inscrit au registre.</p>`}`;
}
function vueEquipe(eid, pid){
  const e = en(eid), p = po(pid); if(!p || p.entreprise !== eid) return vueIntrouvable("Équipe inconnue.");
  ariane([["Entreprises", "#/"], [e.nom, liens.entreprise(eid)], ["Équipes", `#/e/${esc(eid)}/equipes`], [p.titre]]);
  const tous = subordonnes(pid), membres = tous.filter(m => m.entreprise === eid), ailleurs = tous.filter(m => m.entreprise !== eid);
  const r = p.titulaire ? ag(p.titulaire) : null, agents = membres.map(m => m.titulaire).filter(Boolean).map(ag), ids = new Set(agents.map(a => a.id));
  const ms = Object.values(O.missions).filter(m => ids.has(m.attributaire));
  const msg = O.messages.filter(m => ids.has(m.de) || ids.has(m.a) || (r && (m.de === r.id || m.a === r.id)));
  return `<div class="kicker">${esc(e.nom)} · équipe</div><h1>Équipe de ${esc(r ? r.nom : p.titre)}</h1>${bandeauPublic()}
    <h2>Responsable</h2>${r ? `<div class="grille">${carteAgent(r)}</div>` : `<p class="vide">${esc(p.titre)} — non pourvu</p>`}
    <h2>Agents</h2>${membres.length ? "" : `<p class="vide">Aucun poste de ${esc(e.nom)} sous ce responsable.</p>`}<div class="grille">${membres.map(m => m.titulaire ? carteAgent(ag(m.titulaire)) : `<div class="carte"><b>${esc(m.titre)}</b><br><span class="s">non pourvu</span></div>`).join("")}</div>
    ${ailleurs.length ? `<p class="s">Postes d'autres entreprises rattachés à ce responsable (hors équipe) : ${ailleurs.map(m => m.titulaire ? `<a href="${liens.agent(m.titulaire)}">${esc((ag(m.titulaire) || {}).nom || m.titulaire)}</a>` : esc(m.titre)).join(", ")}.</p>` : ""}
    <h2>Missions attribuées</h2>${tableMissions(ms.filter(m => !["terminee", "bloquee"].includes(m.statut)), "Aucune mission active.")}
    <h2>Missions terminées</h2>${tableMissions(ms.filter(m => m.statut === "terminee"), "Aucune mission terminée.")}
    <h2>Missions bloquées</h2>${tableMissions(ms.filter(m => m.statut === "bloquee"), "Aucune mission bloquée.")}
    <h2>Livrables</h2>${listeLivrables(ms.flatMap(m => m.livrables.map(l => ({...l, mission: m.id}))))}
    <h2>Communications</h2>${listeMessages(msg)}`;
}
function vueMissions(eid){
  const e = en(eid); ariane([["Entreprises", "#/"], [e.nom, liens.entreprise(eid)], ["Missions"]]);
  const ms = missionsDe(eid);
  return `<h1>Missions</h1>${bandeauPublic()}<div class="oc-barre" role="group" aria-label="Filtrer"><button data-f="">Toutes (${ms.length})</button>${["proposee", "planifiee", "en_cours", "verification", "bloquee", "terminee"].map(s => `<button data-f="${s}">${esc(MST[s])} (${ms.filter(m => m.statut === s).length})</button>`).join("")}</div>
    <div id="liste-missions">${tableMissions(ms)}</div>`;
}
function vueReunions(eid){
  const e = en(eid); ariane([["Entreprises", "#/"], [e.nom, liens.entreprise(eid)], ["Salle de réunion"]]);
  const rs = Object.values(O.reunions).filter(r => r.entreprise === eid).sort((a, b) => b.ouverte.localeCompare(a.ouverte));
  return `<h1>Salle de réunion</h1>${bandeauPublic()}<p class="lead">Seules les réunions inscrites au registre apparaissent. « Ouverte » signifie inscrite et non close ; un participant n'est « en réunion » que s'il a aussi une exécution réelle en cours.</p>
    ${rs.length ? rs.map(r => { const presents = r.participants.filter(x => (ag(x) || {}).statut === "en_reunion");
      return `<div class="carte" style="margin:8px 0"><div class="l">${r.close ? "close" : "ouverte"} · ${quand(r.ouverte)}${r.close ? " → " + quand(r.close) : ""} · <span class="src">${esc(r.id)}</span></div>
      <b>${esc(r.objet)}</b> — organisée par ${esc(r.par)}<br>Participants : ${r.participants.map(x => `<a href="${liens.agent(x)}">${esc((ag(x) || {}).nom || x)}</a>`).join(", ")}
      ${!r.close ? `<br><span class="src">${presents.length ? presents.length + " participant(s) en exécution réelle" : "aucun participant n'a d'exécution en cours : personne n'est affiché « en réunion »"}</span>` : ""}
      ${r.compte_rendu ? `<p>${esc(r.compte_rendu)}</p>` : (r.close ? `<p class="vide">Pas de compte rendu.</p>` : "")}</div>`; }).join("") : `<p class="vide">Aucune réunion enregistrée pour ${esc(e.nom)}.</p>`}`;
}
function vueAnnuaire(eid){
  const e = en(eid); ariane([["Entreprises", "#/"], [e.nom, liens.entreprise(eid)], ["Annuaire"]]);
  const as = agentsDe(eid).sort((a, b) => ((po(a.poste) || {}).niveau ?? 9) - ((po(b.poste) || {}).niveau ?? 9));
  return `<h1>Annuaire</h1>${bandeauPublic()}${as.length ? `<div class="grille">${as.map(carteAgent).join("")}</div>` : `<p class="vide">Aucun collaborateur inscrit.</p>`}`;
}
function activiteAgent(a){
  return [...historiqueDe(a).map(h => ({...h, auteur: (h.auteur || {}).role, verifie: (h.auteur || {}).verifie})), ...O.activite.filter(x => estDe(a, x))]
    .sort((x, y) => (y.quand || "").localeCompare(x.quand || ""));
}
function vueAgent(aid){
  const a = ag(aid); if(!a) return vueIntrouvable(`Aucun agent « ${aid} » au registre.`);
  const p = po(a.poste) || {}, e = en(a.entreprise) || {}, sup = a.superieur ? ag(a.superieur) : null, dir = e.directeur && e.directeur.agent ? ag(e.directeur.agent) : null;
  ariane([["Entreprises", "#/"], [e.nom || "—", e.id ? liens.entreprise(e.id) : null], [a.nom]]);
  const directs = a.poste ? subordonnes(a.poste).map(x => x.titulaire).filter(Boolean).map(ag) : [];
  const ms = a.missions, dern = dernierEvenement(a), act = activiteAgent(a);
  const pairs = agentsDe(a.entreprise).filter(x => x.id !== a.id);
  const msgs = O.messages.filter(m => m.de === a.id || m.a === a.id || m.a === a.poste);
  const reus = Object.values(O.reunions).filter(r => r.participants.includes(a.id));
  const livres = ms.flatMap(m => m.livrables.filter(l => l.par === a.id).map(l => ({...l, mission: m.id})));
  const perf = a.performance || {};
  return `<div class="kicker">${esc(e.nom || "sans entreprise")} · profil d'agent</div>
    <h1>${monogramme(a, 54)} ${esc(a.nom)}</h1>${bandeauPublic()}
    <div class="grille">
      <div class="carte"><div class="l">Identité professionnelle</div><div class="s">Identifiant <code>${esc(a.id)}</code><br>Fonction : <b>${esc(p.titre || "—")}</b> (${esc(a.fonction || "—")}, niveau ${esc(p.niveau ?? "—")})<br>
        Département : ${a.departement ? `<a href="${liens.dep(a.entreprise, a.departement)}">${esc((propre(O.departements, a.departement) || {}).nom || a.departement)}</a>` : "aucun"}<br>
        Manager direct : ${sup ? `<a href="${liens.agent(sup.id)}">${esc(sup.nom)}</a>` : "aucun"}<br>Directeur : ${dir ? `<a href="${liens.agent(dir.id)}">${esc(dir.nom)}</a>` : "—"}<br>Créé le ${quand(a.cree.quand)} <span class="src">${esc(a.cree.evenement)}</span></div></div>
      <div class="carte"><div class="l">Situation opérationnelle</div><div style="margin:6px 0">${statut(a)}</div><div class="s">${esc(a.nature || "")}<br>Preuve : <code>${esc(a.preuve || "aucune")}</code><br>Dernier événement connu : ${dern ? quand(dern) : "aucun"}</div>
        <div class="s" style="margin-top:6px">${act.length ? "" : "<b>Aucune activité réelle enregistrée.</b> "}Capacité d'exécution : ${a.definition ? `définition <code>agents/definitions/${esc(a.definition)}.md</code>` : "aucune"}.</div></div>
      <div class="carte"><div class="l">Compétences et responsabilités</div><div class="s">${(a.competences || []).concat(p.competences || []).map(c => `<span class="tag">${esc(c)}</span>`).join("") || "compétences non renseignées"}<br>${esc(a.description || p.description || "")}<br>${((O.fonctions[a.fonction] || {}).permissions || []).map(x => `<span class="tag">${esc(x.replace(/_/g, " "))}</span>`).join("")}</div></div>
      <div class="carte"><div class="l">Activité (comptée au registre)</div><div class="s">${ms.length} mission(s) attribuée(s) · ${ms.filter(m => ["planifiee", "en_cours", "verification"].includes(m.statut)).length} en cours · ${ms.filter(m => m.statut === "terminee").length} terminée(s) · ${ms.filter(m => m.statut === "bloquee").length} bloquée(s)<br>
        ${livres.length} livrable(s) remis · ${ms.filter(m => m.validee).length} validé(s) · ${perf.corrections_demandees || 0} correction(s) demandée(s)</div></div>
    </div>
    <h2>Hiérarchie</h2><div class="grille">${sup ? carteAgent(sup) : `<div class="carte"><span class="s">Aucun supérieur au registre</span></div>`}${directs.map(carteAgent).join("") || `<div class="carte"><span class="s">Aucun collaborateur direct</span></div>`}</div>
    <h2>Missions</h2>${tableMissions(ms)}<h2>Livrables remis</h2>${listeLivrables(livres)}
    <h2>Messages</h2>${listeMessages(msgs)}
    <h2>Réunions</h2>${reus.length ? reus.map(r => `<div class="carte" style="margin:4px 0">${esc(r.objet)} — ${r.close ? "close" : "ouverte"} · ${quand(r.ouverte)} <span class="src">${esc(r.id)}</span></div>`).join("") : `<p class="vide">Aucune réunion enregistrée.</p>`}
    <h2>Historique des événements</h2>${tableActivite(act, "Aucune activité réelle enregistrée pour cet agent.")}
    ${pairs.length ? `<h2>Collègues de ${esc(e.nom)}</h2><div class="grille">${pairs.map(carteAgent).join("")}</div>` : ""}
    <p class="src">Identité visuelle : graine stable <code>${esc((a.apparence || {}).graine || "—")}</code> · avatar : ${a.apparence && a.apparence.avatar ? esc(a.apparence.avatar) : "aucun (phase 4)"}.</p>`;
}
function vueMission(mid){
  const m = propre(O.missions, mid); if(!m) return vueIntrouvable(`Aucune mission « ${mid} » au registre.`);
  const e = en(m.siege) || {};
  ariane([["Entreprises", "#/"], [e.nom || m.siege, e.id ? liens.entreprise(e.id) : null], ["Missions", e.id ? `#/e/${esc(e.id)}/missions` : null], [m.id]]);
  const evs = O.activite.filter(x => x.mission === mid).sort((a, b) => a.quand.localeCompare(b.quand));
  return `<div class="kicker">${esc(e.nom || m.siege)} · mission</div><h1 style="font-size:clamp(24px,4vw,36px)">${esc(m.titre)}</h1>${bandeauPublic()}
    <div class="grille">
      <div class="carte"><div class="l">Identifiant · statut</div><div class="v" style="font-size:20px">${esc(m.id)}</div><div class="s">${esc(MST[m.statut] || m.statut)}</div></div>
      <div class="carte"><div class="l">Responsable · agent</div><div class="s">Attribuée par : ${m.attribuee_par ? (ag(m.attribuee_par) ? `<a href="${liens.agent(m.attribuee_par)}">${esc(ag(m.attribuee_par).nom)}</a>` : esc(m.attribuee_par)) : "—"}<br>Agent : ${m.attributaire ? `<a href="${liens.agent(m.attributaire)}">${esc((ag(m.attributaire) || {}).nom || m.attributaire)}</a>` : "non attribuée"}</div></div>
      <div class="carte"><div class="l">Priorité · échéance</div><div class="s">${esc(m.priorite_travail || "—")} · ${esc(m.echeance || "—")}<br>score ${esc(m.score ?? "—")} · rang ${esc(m.rang ?? "—")}</div></div>
      <div class="carte"><div class="l">Validation</div><div class="s">${m.validee ? `validée le ${quand(m.validee.quand)} par ${esc(m.validee.par)} — ${esc(m.validee.motif || "")}` : "non validée"}<br>${m.corrections} correction(s) demandée(s)</div></div>
    </div>
    <h2>Description</h2><p class="lead">${esc(m.objectif || "—")}</p>${(m.criteres || []).length ? `<ul>${m.criteres.map(c => `<li>${esc(c)}</li>`).join("")}</ul>` : ""}
    <h2>Livrables</h2>${listeLivrables(m.livrables.map(l => ({...l, mission: m.id})))}
    ${m.remontees.length ? `<h2>Remontées</h2>${m.remontees.map(r => `<div class="alerte">${quand(r.quand)} : ${esc(r.de)} → ${esc(r.vers)} — ${esc(r.motif)}</div>`).join("")}` : ""}
    <h2>Historique des statuts</h2><div class="table"><table><thead><tr><th>Quand</th><th>Statut</th><th>Par</th><th>Motif</th></tr></thead><tbody>${(m.historique || []).map(h => `<tr><td>${quand(h.quand)}</td><td>${esc(MST[h.statut] || h.statut)}</td><td>${esc(h.par || "—")}</td><td>${esc(h.motif || "")}</td></tr>`).join("")}</tbody></table></div>
    <h2>Événements</h2>${tableActivite(evs.reverse(), "Aucun événement de travail (attribution, livrable, validation) pour cette mission.")}`;
}
function vueIntrouvable(msg){ ariane([["Introuvable"]]); return `<h1>Introuvable</h1><p class="vide">${esc(msg)}</p><p><a href="#/">← Toutes les entreprises</a></p>`; }

// ------------------------------------------------------------------ organigramme (calculé, jamais codé en dur)
function arbre(racine, interactif = true, eid = null){
  const vus = new Set();
  const noeud = p => {
    if(vus.has(p.id)) return `<li><span class="alerte">cycle : ${esc(p.id)}</span></li>`; vus.add(p.id);
    const a = p.titulaire ? ag(p.titulaire) : null, enf = subordonnes(p.id).filter(s => !eid || s.entreprise === eid || eid === "*");
    const dep = p.departement ? (propre(O.departements, p.departement) || {}).nom || p.departement : null;
    const carte = a ? `<a class="noeud" data-cherche="${esc((a.nom + " " + p.titre + " " + (dep || "")).toLowerCase())}" href="${liens.agent(a.id)}">${monogramme(a, 36)}<span><b>${esc(a.nom)}</b><br><span class="src">${esc(p.titre)}${dep ? " · " + esc(dep) : ""}</span><br>${statut(a)}</span></a>`
      : `<span class="noeud vacant" data-cherche="${esc(p.titre.toLowerCase())}"><span><b>${esc(p.titre)}</b><br><span class="src">poste non pourvu</span></span></span>`;
    return `<li data-poste="${esc(p.id)}">${carte}${enf.length && interactif ? `<button class="plier" type="button" aria-label="Replier ou déplier">${enf.length}</button>` : ""}${enf.length ? `<ul>${enf.map(noeud).join("")}</ul>` : ""}</li>`;
  };
  const r = po(racine);
  return r ? `<div class="oc" style="height:auto;max-height:52vh"><div class="oc-plan"><ul>${noeud(r)}</ul></div></div>` : `<p class="vide">—</p>`;
}
function vueOrganigramme(eid){
  const e = en(eid); ariane([["Entreprises", "#/"], [e.nom, liens.entreprise(eid)], ["Organigramme"]]);
  const ps = e.postes, tetes = ps.filter(p => !p.superieur || (po(p.superieur) || {}).entreprise !== eid);
  const inc = incoherences(eid);
  const ext = tetes.filter(p => p.superieur && po(p.superieur)).map(p => po(p.superieur));
  return `<div class="kicker">${esc(e.nom)}</div><h1>Organigramme</h1>${bandeauPublic()}
    <p class="lead">Calculé à partir des postes et des liens « supérieur » inscrits au registre (${ps.length} poste(s)). ${ext.length ? `Rattachement extérieur : ${[...new Set(ext.map(x => `${x.titre} (${(en(x.entreprise) || {}).nom || x.entreprise})`))].map(esc).join(", ")}.` : ""}</p>
    <div class="oc-barre"><button type="button" data-z="1.15" aria-label="Zoomer">＋</button><button type="button" data-z="0.87" aria-label="Dézoomer">－</button><button type="button" data-z="0" >Ajuster</button>
      <button type="button" data-tout="plier">Tout replier</button><button type="button" data-tout="deplier">Tout déplier</button><input id="oc-cherche" type="search" placeholder="Chercher dans l'organigramme" aria-label="Chercher dans l'organigramme"></div>
    ${ps.length ? `<div class="oc" id="oc"><div class="oc-plan" id="oc-plan"><ul>${tetes.map(t => arbre(t.id, true, eid).replace(/^<div class="oc"[^>]*><div class="oc-plan"><ul>/, "").replace(/<\/ul><\/div><\/div>$/, "")).join("")}</ul></div></div>` : `<p class="vide">Aucun poste inscrit.</p>`}
    ${inc.length ? `<h2>Incohérences signalées (non corrigées)</h2>${inc.map(x => `<div class="alerte">${esc(x)}</div>`).join("")}` : `<p class="src">Aucune incohérence détectée.</p>`}`;
}
let zoom = 1;
function brancherOrganigramme(){
  const oc = $("#oc"), plan = $("#oc-plan"); if(!oc) return;
  zoom = 1; const appliquer = () => plan.style.transform = `scale(${zoom})`;
  document.querySelectorAll("[data-z]").forEach(b => b.onclick = () => { const z = +b.dataset.z; zoom = z ? Math.min(2.5, Math.max(0.3, zoom * z)) : Math.min(1, oc.clientWidth / plan.scrollWidth); appliquer(); });
  oc.addEventListener("wheel", ev => { if(!ev.ctrlKey) return; ev.preventDefault(); zoom = Math.min(2.5, Math.max(0.3, zoom * (ev.deltaY < 0 ? 1.1 : 0.9))); appliquer(); }, {passive: false});
  let glisse = null;
  oc.addEventListener("pointerdown", ev => { if(ev.target.closest("a,button,input")) return; glisse = {x: ev.clientX, y: ev.clientY, l: oc.scrollLeft, t: oc.scrollTop}; oc.classList.add("saisi"); });
  addEventListener("pointermove", ev => { if(!glisse) return; oc.scrollLeft = glisse.l - (ev.clientX - glisse.x); oc.scrollTop = glisse.t - (ev.clientY - glisse.y); });
  addEventListener("pointerup", () => { glisse = null; oc.classList.remove("saisi"); });
  oc.addEventListener("click", ev => { const b = ev.target.closest(".plier"); if(b) b.parentElement.classList.toggle("plie"); });
  document.querySelectorAll("[data-tout]").forEach(b => b.onclick = () => oc.querySelectorAll("li").forEach(li => li.classList.toggle("plie", b.dataset.tout === "plier" && li.querySelector("ul"))));
  $("#oc-cherche").oninput = ev => { const q = ev.target.value.trim().toLowerCase(); let premier = null;
    oc.querySelectorAll("[data-cherche]").forEach(n => { const ok = q && n.dataset.cherche.includes(q); n.classList.toggle("trouve", ok); if(ok){ let li = n.closest("li"); while(li){ li.classList.remove("plie"); li = li.parentElement.closest("li"); } premier = premier || n; } });
    if(premier) premier.scrollIntoView({block: "center", inline: "center", behavior: "smooth"}); };
}

// ------------------------------------------------------------------ routeur
const ROUTES = [
  [/^#?\/?$/, () => vueListe()], [/^#\/e\/([^/]+)$/, m => vueEntreprise(m[1])], [/^#\/e\/([^/]+)\/direction$/, m => vueDirection(m[1])],
  [/^#\/e\/([^/]+)\/organigramme$/, m => vueOrganigramme(m[1])], [/^#\/e\/([^/]+)\/departements$/, m => vueDepartements(m[1])],
  [/^#\/e\/([^/]+)\/departement\/([^/]+)$/, m => vueDepartement(m[1], m[2])], [/^#\/e\/([^/]+)\/equipes$/, m => vueEquipes(m[1])],
  [/^#\/e\/([^/]+)\/equipe\/([^/]+)$/, m => vueEquipe(m[1], m[2])], [/^#\/e\/([^/]+)\/missions$/, m => vueMissions(m[1])],
  [/^#\/e\/([^/]+)\/reunions$/, m => vueReunions(m[1])], [/^#\/e\/([^/]+)\/annuaire$/, m => vueAnnuaire(m[1])],
  [/^#\/agent\/([^/]+)$/, m => vueAgent(m[1])], [/^#\/mission\/([^/]+)$/, m => vueMission(m[1])],
];
function afficher(){
  let h; try{ h = decodeURIComponent(location.hash || "#/"); }catch(_){ $("#vue").innerHTML = vueIntrouvable("Adresse mal formée."); return; }
  const r = ROUTES.find(([re]) => re.test(h)), v = $("#vue");
  const eid = (/^#\/e\/([^/]+)/.exec(h) || [])[1];
  if(eid && !en(eid)){ v.innerHTML = vueIntrouvable(`Aucune entreprise « ${eid} » au cadastre.`); return; }
  v.classList.add("sortie");
  setTimeout(() => {
    v.innerHTML = r ? r[0] && r[1](r[0].exec(h)) : vueIntrouvable("Adresse inconnue.");
    v.classList.remove("sortie"); scrollTo({top: 0}); document.title = ($("h1") ? $("h1").textContent.trim() + " — " : "") + "Île Entrepreneuriale";
    brancherOrganigramme();
    document.querySelectorAll("[data-f]").forEach(b => b.onclick = () => { const ms = missionsDe(eid).filter(m => !b.dataset.f || m.statut === b.dataset.f); $("#liste-missions").innerHTML = tableMissions(ms); });
  }, 120);
}
$("#cherche").addEventListener("change", ev => { const v = ev.target.value; const a = Object.values(O.agents).find(x => x.nom === v || x.id === v); if(a){ location.hash = liens.agent(a.id); ev.target.value = ""; } });
(async () => {
  try{
    MODE = await IleSource.detecter();
    $("#n-met").href = IleSource.lien("metropole"); $("#n-res").href = IleSource.lien("residence"); $("#n-acc").href = IleSource.lien("accueil");
    const r = await IleSource.get("/api/organisation"); if(!r.ok) throw new Error("organisation indisponible (" + r.status + ")");
    O = await r.json();
    PROPS = await IleSource.get("/api/propositions").then(x => x.ok ? x.json() : null).catch(() => null);
    $("#annuaire").innerHTML = Object.values(O.agents).map(a => `<option value="${esc(a.nom)}">${esc((po(a.poste) || {}).titre || "")}</option>`).join("");
    addEventListener("hashchange", afficher); afficher();
  }catch(e){ $("#vue").innerHTML = `<h1>Organisation indisponible</h1><p class="vide">${esc(e.message)}</p>`; }
})();
