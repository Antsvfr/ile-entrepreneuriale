// Test navigateur du pouvoir présidentiel d'approbation et de refus : node tests/decisions.js <url de base>
//  - serveur local sur une FIXTURE (tests/fixture_decisions.py) : FIXTURE_PHRASE et ILE_OPS du registre temporaire requis ;
//    parcours complet : boîte, fiche, verrou, activation, approuver, refuser, modifications, avis, double décision,
//    persistance, institutions informées, suivi de l'exécution, historique, refus sans session ;
//  - version publiée (GitHub Pages ou miroir) : tout est visible, aucune décision possible, aucune requête d'écriture.
// Codes : 0 PASS · 1 FAIL · 3 NOT TESTED (Playwright absent).
let chromium, devices;
try { ({chromium, devices} = require("playwright")); } catch { console.log("Playwright absent"); process.exit(3); }
const {execFileSync} = require("child_process"), path = require("path");
const base = (process.argv[2] || "").replace(/\/?$/, "/");
const R = []; const note = (n, ok, d) => { R.push(!!ok); console.log(`${ok ? "PASS" : "FAIL"}  ${n}${d ? " — " + d : ""}`); };
const local = /^https?:\/\/(127\.0\.0\.1|localhost)[:/]/.test(base) && !/\/ile-entrepreneuriale\/$/.test(base);
const B = local ? base + "village/decisions.html" : base + "residence/village/decisions.html";
const E = local ? base + "village/entreprise.html" : base + "residence/village/entreprise.html";

(async () => {
  const b = await chromium.launch({...(!/127\.0\.0\.1|localhost/.test(base) && process.env.HTTPS_PROXY ? {proxy: {server: process.env.HTTPS_PROXY}} : {})});
  const page = async (opts) => {
    const ctx = await b.newContext(opts || {viewport: {width: 1360, height: 900}}); const p = await ctx.newPage(); p.erreurs = []; p.posts = [];
    p.on("pageerror", e => p.erreurs.push(e.message));
    p.on("request", r => { if (r.method() !== "GET") p.posts.push(r.method() + " " + new URL(r.url()).pathname); });
    p.on("response", r => { if (r.status() >= 500 && !/favicon/.test(r.url())) p.erreurs.push(`HTTP ${r.status()} ${r.url()}`); });
    return p;
  };
  const p = await page();
  const ouvrir = async (h) => { await p.goto(B + (h || ""), {waitUntil: "networkidle"}); await p.waitForFunction(() => !/Chargement/.test(document.querySelector("#acces").textContent), null, {timeout: 30000}); };
  const api = async () => p.evaluate(() => IleSource.get("/api/propositions").then(r => r.json()));
  const fiche = async id => { await p.goto("about:blank"); await ouvrir("#" + id); await p.waitForSelector("#fiche h2"); return p.textContent("#fiche"); };
  await ouvrir();
  let D = await api();
  const soumises = Object.values(D.propositions).filter(x => x.statut !== "brouillon");
  const items = await p.$$eval("#liste .item", l => l.map(x => x.dataset.id));
  note("2. Les propositions soumises apparaissent dans la boîte présidentielle", items.length === soumises.length && soumises.every(x => items.includes(x.id)), `${items.length}/${soumises.length}`);
  note("Fil d'Ariane Mon bureau → Décisions → Propositions à examiner", /Mon bureau → Décisions → Propositions à examiner/.test(await p.textContent(".ariane")));
  const filtres = await p.$$eval("#filtres button", l => l.map(x => x.textContent));
  note("Filtres : toutes, en attente, analyse, modifications, approuvées, refusées, archivées", filtres.length === 7 && ["Toutes", "En attente de décision", "En cours d'analyse", "Modifications demandées", "Approuvées", "Refusées", "Archivées"].every((f, i) => filtres[i].startsWith(f)), filtres.join(" | "));

  if (!local) {    // ------------------------------------------------ version publiée
    const id = items[0];
    const t = id ? await fiche(id) : "";
    const actives = await p.$$eval("#fiche [data-action]", l => l.filter(x => !x.disabled).length);
    note("Publié : chaque proposition s'ouvre avec son dossier", !id || t.includes(D.propositions[id].titre), id || "aucune proposition");
    note("Publié : aucune décision possible (boutons inactifs, raison affichée)", actives === 0 && /GitHub Pages/.test(await p.textContent("#acces")) && !D.acces.decision_possible, `${actives} bouton(s) actif(s)`);
    note("Publié : aucun déverrouillage ni activation proposés", !(await p.$("#b-deverrouiller")) && !(await p.$("#b-activer")));
    note("Publié : explication de l'absence d'identité présidentielle", D.acces.identite || /identité présidentielle/.test(await p.textContent("#acces")));
    note("Publié : aucune requête d'écriture", !p.posts.length, p.posts.join(" | "));
    const m = await page({...devices["Pixel 7"]}); await m.goto(B + (id ? "#" + id : ""), {waitUntil: "networkidle"}); await m.waitForTimeout(800);
    note("Publié : mobile sans débordement ni erreur", await m.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1) && !m.erreurs.length && !p.erreurs.length, [...m.erreurs, ...p.erreurs].join(" | "));
  } else {         // ------------------------------------------------ Résidence locale (fixture)
    const phrase = process.env.FIXTURE_PHRASE, ops = process.env.ILE_OPS;
    if (!phrase || !ops) { console.log("FIXTURE_PHRASE et ILE_OPS requis en local"); process.exit(1); }
    const parId = t => Object.values(D.propositions).find(x => x.titre && x.titre.startsWith(t));
    const P1 = parId("Atelier de relecture"), P2 = parId("Nouveau quartier"), P3 = parId("Budget d'outillage");
    let t = await fiche(P1.id);
    const champs = [P1.titre, P1.description, P1.objectif, P1.consequences, P1.cout, P1.risques[0], "La Forge", "REV-EM", P1.pieces[0].chemin, "chef-rev-em", "identité vérifiée"];
    note("3. Une proposition se consulte intégralement", champs.every(c => t.includes(c)), champs.filter(c => !t.includes(c)).join(", ") || `${champs.length} éléments`);
    let actives = await p.$$eval("#fiche [data-action]", l => l.filter(x => !x.disabled).length);
    note("Verrouillée : boutons inactifs et raison affichée", actives === 0 && /verrouillée/i.test(await p.textContent("#acces")), `${actives} actif(s)`);
    note("Avant authentification : aucune requête d'écriture", !p.posts.length, p.posts.join(" | "));
    // 9-10 au niveau HTTP : sans session et sans jeton
    const sans = await p.evaluate(async ([id, v]) => {
      const j = (await (await fetch("/api/session")).json()).jeton;
      const a = await fetch("/api/proposition", {method: "POST", headers: {"Content-Type": "application/json", "X-Ile-Jeton": j}, body: JSON.stringify({action: "approuver", id, version: v, confirmation: id})});
      const b2 = await fetch("/api/proposition", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({action: "approuver", id, version: v, confirmation: id})});
      return [a.status, b2.status];
    }, [P1.id, P1.version]);
    note("9-10. Sans session présidentielle (ou sans jeton), le serveur refuse toute décision", sans[0] === 401 && sans[1] === 403, sans.join(", "));
    // déverrouillage : mauvaise phrase puis phrase de test
    await p.click("#b-deverrouiller"); await p.fill("#phrase", "mauvaise phrase de test"); await p.click("#lock-f button[type=submit]");
    await p.waitForFunction(() => document.querySelector("#lock-err").textContent.length > 0);
    const errVerrou = await p.textContent("#lock-err");
    await p.fill("#phrase", phrase); await p.click("#lock-f button[type=submit]");
    await p.waitForSelector("#b-activer", {timeout: 30000});
    note("Identité invalide refusée, identité valide déverrouille", /incorrecte/.test(errVerrou), errVerrou);
    note("Déverrouillée mais non activée : décisions toujours bloquées", (await p.$$eval("#fiche [data-action]", l => l.filter(x => !x.disabled).length)) === 0 && /non activées/.test(await p.textContent("#acces")));
    await p.click("#b-activer"); await p.fill("#dlg-f input[name=confirmation]", "oui"); await p.click("#dlg-f button[type=submit]");
    const errAct = await p.textContent("#dlg-err");
    await p.fill("#dlg-f input[name=confirmation]", "ACTIVER"); await p.click("#dlg-f button[type=submit]");
    await p.waitForSelector("#resultat .resultat", {timeout: 30000});
    note("Activation : confirmation explicite, acte signé relu au registre", /ACTIVER/.test(errAct) && /Décisions officielles activées/.test(await p.textContent("#resultat")), (await p.textContent("#resultat")).slice(0, 120));
    // 4. approuver
    t = await fiche(P1.id);
    await p.click("#fiche [data-action=approuver]");
    const dlg = await p.textContent("#dlg-f");
    note("Avant confirmation : contenu intégral, conséquences, institutions concernées", [P1.description, P1.objectif, "ne pourra plus être modifiée", "La Forge", "REV-EM"].every(c => dlg.includes(c)));
    await p.click("#dlg-f button[type=submit]");
    const errConf = await p.textContent("#dlg-err");
    await p.fill("#dlg-f input[name=confirmation]", P1.id); await p.fill("#dlg-f textarea[name=motif]", "Utile et peu coûteux (test)");
    await p.click("#dlg-f button[type=submit]"); await p.waitForSelector("#resultat .resultat", {timeout: 30000});
    const res = await p.textContent("#resultat");
    D = await api();
    const j = await p.evaluate(() => IleSource.get("/api/journal?type=proposition.approuvee").then(r => r.json()));
    const evA = j.evenements.find(e => e.donnees.proposition === P1.id);
    note("Sans confirmation recopiée, rien n'est envoyé", /Confirmation incorrecte/.test(errConf));
    note("4. Le président authentifié approuve (acte signé, relu au registre)", D.propositions[P1.id].statut === "approuvee" && evA && evA.auteur.role === "president" && evA.auteur.verifie === "signature" && evA.signature && res.includes(evA.id) && /Décision enregistrée au registre/.test(res),
      res.slice(0, 160));
    // 11-12. double décision
    actives = await p.$$eval("#fiche [data-action=approuver]:not([disabled]),#fiche [data-action=refuser]:not([disabled])", l => l.length);
    const double = await p.evaluate(async ([id, v]) => { const jt = (await (await fetch("/api/session")).json()).jeton;
      const r = await fetch("/api/proposition", {method: "POST", headers: {"Content-Type": "application/json", "X-Ile-Jeton": jt}, body: JSON.stringify({action: "refuser", id, version: v, confirmation: id, motif: "forcer"})});
      return [r.status, (await r.json()).erreur]; }, [P1.id, D.propositions[P1.id].version]);
    note("11. Pas de seconde décision silencieuse (refusée par le serveur, message explicite)", double[0] === 400 && /déjà/.test(double[1]), double.join(" — "));
    note("12. Une décision prise ne se modifie pas depuis l'interface", actives === 0);
    // 5-6. refuser : motif obligatoire (client et serveur)
    await fiche(P2.id); await p.click("#fiche [data-action=refuser]");
    await p.fill("#dlg-f input[name=confirmation]", P2.id);
    await p.$eval("#dlg-f textarea[name=motif]", x => x.removeAttribute("required"));
    await p.click("#dlg-f button[type=submit]"); const errMotif = await p.textContent("#dlg-err");
    const motifServeur = await p.evaluate(async ([id, v]) => { const jt = (await (await fetch("/api/session")).json()).jeton;
      const r = await fetch("/api/proposition", {method: "POST", headers: {"Content-Type": "application/json", "X-Ile-Jeton": jt}, body: JSON.stringify({action: "refuser", id, version: v, confirmation: id, motif: "  "})});
      return [r.status, (await r.json()).erreur]; }, [P2.id, P2.version]);
    note("6. Le motif de refus est obligatoire (interface et serveur)", /obligatoire/.test(errMotif) && motifServeur[0] === 400 && /motif/.test(motifServeur[1]), motifServeur.join(" — "));
    await p.fill("#dlg-f textarea[name=motif]", "Pas avant la fin du trimestre (test)"); await p.click("#dlg-f button[type=submit]");
    await p.waitForSelector("#resultat .resultat", {timeout: 30000}); D = await api();
    note("5. Le président authentifié refuse (motif inscrit, archivée)", D.propositions[P2.id].statut === "refusee" && D.propositions[P2.id].decision.motif.startsWith("Pas avant") && !!D.propositions[P2.id].archivee);
    // 7. modifications
    await fiche(P3.id); await p.click("#fiche [data-action=modifier]");
    await p.fill("#dlg-f textarea[name=observations]", "Coût non chiffré (test)"); await p.fill("#dlg-f textarea[name=attendus]", "Indiquer le prix mensuel (test)");
    await p.fill("#dlg-f input[name=echeance]", "2099-12-31"); await p.fill("#dlg-f input[name=confirmation]", P3.id); await p.click("#dlg-f button[type=submit]");
    await p.waitForSelector("#resultat .resultat", {timeout: 30000}); D = await api();
    note("7. Une proposition peut être retournée pour modification", D.propositions[P3.id].statut === "modifications_demandees" && D.propositions[P3.id].demandes_modification[0].echeance === "2099-12-31");
    // 8. avis, sur une demande de décision réelle de l'ancien format (dans la copie temporaire)
    const ancienne = Object.values(D.propositions).find(x => x.ancienne && x.statut === "en_attente_decision");
    await fiche(ancienne.id); await p.click("#fiche [data-action=avis]");
    await p.selectOption("#dlg-f select[name=destinataire]", "conseil"); await p.fill("#dlg-f textarea[name=question]", "Le Conseil est-il favorable ? (test)");
    await p.fill("#dlg-f input[name=confirmation]", ancienne.id); await p.click("#dlg-f button[type=submit]");
    await p.waitForSelector("#resultat .resultat", {timeout: 30000}); D = await api();
    const dem = D.propositions[ancienne.id].demandes_avis[0];
    note("8. Une demande d'avis est enregistrée et suivie", D.propositions[ancienne.id].statut === "en_analyse" && dem && dem.destinataire === "conseil" && !dem.rendu && (await p.textContent("#fiche")).includes("en attente"));
    // 13. historique
    await fiche(P1.id); await p.click("#b-historique");
    const lignes = await p.$$eval("#historique tbody tr", l => l.length);
    note("13. L'historique complet est consultable", lignes === D.propositions[P1.id].historique.length && lignes >= 3, `${lignes} étape(s)`);
    // 14. persistance : rechargement et navigateur neuf
    await p.reload({waitUntil: "networkidle"}); await p.waitForSelector("#fiche h2");
    const q = await page(); await q.goto(B + "#" + P1.id, {waitUntil: "networkidle"}); await q.waitForSelector("#fiche h2");
    note("14. La décision persiste (rechargement, navigateur neuf sans session)", /Approuvée/.test(await p.textContent("#fiche .statut")) && /Approuvée/.test(await q.textContent("#fiche .statut")) && /Verrouillée/.test(await q.textContent("#chip")));
    // 15. institutions concernées
    await q.goto(E + "#/e/forge", {waitUntil: "networkidle"}); await q.waitForSelector("#vue h1");
    const tf = await q.textContent("#vue");
    note("15. Les institutions concernées reçoivent la décision", tf.includes("Décisions présidentielles reçues") && tf.includes(P1.id) && tf.includes("approuvée"));
    // 16. suivi jusqu'à l'exécution (mise en œuvre par le DG, exécution par le responsable à l'identité vérifiée)
    const ile = (args) => execFileSync("python3", ["-I", "-S", path.join(__dirname, "..", "orchestrateur", "ile.py"), ...args], {env: {...process.env, ILE_OPS: ops}, encoding: "utf8"});
    ile(["proposition", "mettre-en-oeuvre", P1.id, "--responsable", "forge", "--modalites", "Relecture chaque lundi (test)", "--echeance", "2099-01-31"]);
    const rd = ile(["run", "debut", "--role", "forgeron"]).match(/R-\d+/)[0];
    ile(["--auteur", "forgeron", "--run", rd, "proposition", "executer", P1.id, "debut"]);
    ile(["--auteur", "forgeron", "--run", rd, "proposition", "executer", P1.id, "fin", "--resultat", "4 PR relues, 1 régression évitée (test)"]);
    t = await fiche(P1.id);
    note("16. Une décision approuvée se suit jusqu'à l'exécution et ses résultats", /Exécutée/.test(await p.textContent("#fiche .statut")) && t.includes("Relecture chaque lundi") && t.includes("4 PR relues"));
    const m = await page({...devices["Pixel 7"]}); await m.goto(B + "#" + P1.id, {waitUntil: "networkidle"}); await m.waitForSelector("#fiche h2");
    note("Mobile sans débordement", await m.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    note("Aucune erreur dans le navigateur", !p.erreurs.length && !q.erreurs.length && !m.erreurs.length, [...p.erreurs, ...q.erreurs, ...m.erreurs].join(" | "));
    const v = await p.evaluate(() => IleSource.get("/api/verifier").then(r => r.json()));
    note("Registre (temporaire) intègre après toutes les décisions", v.ok, v.erreurs && v.erreurs[0]);
  }
  await b.close();
  const ok = R.filter(Boolean).length;
  console.log(`Bilan : ${ok}/${R.length} PASS`);
  process.exit(ok === R.length ? 0 : 1);
})().catch(e => { console.log("échec : " + e.message); process.exit(1); });
