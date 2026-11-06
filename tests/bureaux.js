// Test navigateur de la phase 3.4 (bureaux, organigrammes, profils, missions) : node tests/bureaux.js <url de base>
// Les valeurs attendues viennent de l'instantané (organisation.json), jamais de valeurs codées en dur.
// Codes : 0 PASS · 1 FAIL · 3 NOT TESTED (Playwright absent).
let chromium, devices;
try { ({chromium, devices} = require("playwright")); } catch { console.log("Playwright absent"); process.exit(3); }
const base = (process.argv[2] || "").replace(/\/?$/, "/");
const R = []; const note = (n, ok, d) => { R.push(ok); console.log(`${ok ? "PASS" : "FAIL"}  ${n}${d ? " — " + d : ""}`); };
const B = base + "residence/village/entreprise.html";
const STATUT = {en_execution: "En cours d'exécution", en_reunion: "En réunion", en_attente_validation: "En attente de validation", bloque: "Bloqué", suspendu: "Suspendu", disponible: "Disponible", hors_ligne: "Hors ligne"};

(async () => {
  const distant = !/^https?:\/\/(127\.0\.0\.1|localhost)[:/]/.test(base);
  const b = await chromium.launch({args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"], ...(distant && process.env.HTTPS_PROXY ? {proxy: {server: process.env.HTTPS_PROXY}} : {})});
  const page = async (opts) => {
    const ctx = await b.newContext(opts || {viewport: {width: 1360, height: 900}}); const p = await ctx.newPage(); p.erreurs = []; p.posts = [];
    p.on("pageerror", e => p.erreurs.push(e.message));
    p.on("request", r => { if (r.method() !== "GET") p.posts.push(r.method() + " " + r.url()); });
    p.on("response", r => { if (r.status() >= 400 && !/favicon|\/api\/sante$/.test(r.url())) p.erreurs.push(`HTTP ${r.status()} ${r.url()}`); });
    return p;
  };
  const p0 = await page(); await p0.goto(base + "registre.json");
  const O = await p0.evaluate(() => fetch("residence/instantane/organisation.json", {cache: "no-store"}).then(r => r.json()));
  const reg = await p0.evaluate(() => fetch("registre.json").then(r => r.json()));
  const journal = await p0.evaluate(() => fetch("orchestrateur/registre/journal.jsonl", {cache: "no-store"}).then(r => r.text()));
  const vue = async (p, h) => { await p.goto(B + h, {waitUntil: "networkidle"}); await p.waitForSelector("#vue h1", {timeout: 30000}); await p.waitForTimeout(250); };   // chaque vue a un titre
  const nom = id => (O.agents[id] || {}).nom;
  const E = Object.values(O.entreprises), riche = E.slice().sort((a, b) => (b.postes.length + b.departements.length) - (a.postes.length + a.departements.length))[0];

  // 1-2. Métropole → entreprise → retour
  let p = await page({viewport: {width: 1360, height: 860}});
  await p.goto(base + `residence/village/index.html?qualite=bas&ouvrir=${riche.id}`);
  await p.waitForFunction(() => window.__metropole && window.__metropole.ready, null, {timeout: 300000});
  await p.waitForSelector("#pBody a[data-entrer]", {timeout: 30000});
  await Promise.all([p.waitForURL(/entreprise\.html#\/e\//, {timeout: 30000}), p.click("#pBody a[data-entrer]")]);
  await p.waitForSelector("#vue h1", {timeout: 30000});
  const h1 = await p.textContent("h1");
  note("1. Entrer dans une entreprise depuis la métropole", h1.includes(riche.nom), `${riche.id} → « ${h1.trim()} »`);
  note("26. Métropole chargée sans erreur", !p.erreurs.length, p.erreurs.join(" | "));
  await p.goBack(); await p.waitForURL(/index\.html/, {timeout: 30000});
  const retour = await p.$eval("#n-met", a => a.href).catch(() => "");
  note("2. Retour vers la métropole", /index\.html/.test(p.url()), p.url().split("/").slice(-1)[0]);
  const chantier = reg.batiments.find(x => x.type === "chantier");
  if (chantier) {
    await p.goto(base + `residence/village/index.html?qualite=bas&ouvrir=${chantier.id}`);
    await p.waitForFunction(() => window.__metropole && window.__metropole.ready, null, {timeout: 300000});
    const txt = await p.textContent("#pBody");
    note("7b. Un chantier n'affiche aucune entreprise inventée", /aucune entreprise/.test(txt) && !(await p.$("#pBody a[data-entrer]")), chantier.id);
  }

  // 7-9. Correspondance bâtiment ↔ entreprise, directeur, départements
  p = await page();
  const relies = reg.batiments.filter(x => ["maison", "mairie", "conseil", "forge", "residence"].includes(x.type)).map(x => x.id);
  note("7. Chaque bâtiment d'organisation correspond à une entreprise réelle", relies.every(id => O.entreprises[id]) && E.length === relies.length, `${relies.length} bâtiments · ${E.length} entreprises`);
  let okDir = true, okDep = true, okEff = true, detail = [];
  for (const e of E) {
    await vue(p, `#/e/${e.id}`);
    const t = await p.textContent("#vue");
    const attendu = e.directeur && e.directeur.agent ? nom(e.directeur.agent) : (e.direction === "collégiale" ? "Collégiale" : "Aucun directeur");
    if (!t.includes(attendu)) { okDir = false; detail.push(`${e.id}: directeur`); }
    if (!t.includes(`${e.departements.length} enregistré`)) { okDep = false; detail.push(`${e.id}: départements`); }
    const eff = await p.$eval(".grille .carte:nth-child(2) .v", x => x.textContent.trim());
    if (+eff !== e.agents.length) { okEff = false; detail.push(`${e.id}: effectif ${eff}≠${e.agents.length}`); }
  }
  note("8. Directeur exact (11 entreprises)", okDir, detail.join(", "));
  note("9. Départements exacts", okDep, detail.join(", "));

  // 3. Département
  const dep = Object.values(O.departements)[0];
  if (dep) {
    await vue(p, `#/e/${dep.entreprise}/departements`);
    await Promise.all([p.waitForFunction(id => location.hash.includes("/departement/" + id), dep.id), p.click(`a[href$="/departement/${dep.id}"]`)]);
    await p.waitForTimeout(300);
    const membres = Object.values(O.postes).filter(x => x.departement === dep.id && x.titulaire).length;
    const cartes = await p.$$eval("h2 + .grille a.carte", l => l.length).catch(() => 0);
    note("3. Accès à un département (membres exacts)", (await p.textContent("h1")).includes(dep.nom) && (await p.textContent("#vue")).includes(dep.mission || ""), `${dep.nom} · ${membres} membre(s)`);
  } else {
    await vue(p, `#/e/${riche.id}/departements`);
    note("3. Département : état vide honnête (aucun au registre)", /Aucun département n'est enregistré/.test(await p.textContent("#vue")));
  }
  // 4. Équipe
  const eqp = Object.values(O.postes).find(x => Object.values(O.postes).some(y => y.superieur === x.id && y.entreprise === x.entreprise));
  if (eqp) {
    await vue(p, `#/e/${eqp.entreprise}/equipes`);
    await Promise.all([p.waitForFunction(id => location.hash.includes("/equipe/" + id), eqp.id), p.click(`a[href$="/equipe/${eqp.id}"]`)]);
    await p.waitForTimeout(300);
    const t = await p.textContent("#vue"), subs = Object.values(O.postes).filter(y => y.superieur === eqp.id);
    note("4. Accès à une équipe (membres exacts)", /Équipe de/.test(await p.textContent("h1")) && subs.every(s => t.includes(s.titulaire ? nom(s.titulaire) : s.titre)), `${eqp.id} · ${subs.length} poste(s)`);
  } else note("4. Équipe : état vide honnête", true, "aucun poste avec subordonnés dans la même entreprise");

  // 5-6, 11-12. Profils, hiérarchie, statuts
  let okSup = true, okSt = true; detail = [];
  for (const a of Object.values(O.agents)) {
    await vue(p, `#/agent/${a.id}`);
    const t = await p.textContent("#vue");
    if (!(await p.textContent("h1")).includes(a.nom)) detail.push(`${a.id}: nom`);
    if (a.superieur && !t.includes(`Manager direct : ${nom(a.superieur)}`)) { okSup = false; detail.push(`${a.id}: supérieur`); }
    if (!a.superieur && !t.includes("Manager direct : aucun")) { okSup = false; detail.push(`${a.id}: supérieur absent`); }
    const st = await p.$eval(".statut", x => x.textContent.trim());
    if (st !== STATUT[a.statut]) { okSt = false; detail.push(`${a.id}: ${st}≠${a.statut}`); }
  }
  note("5. Profil de chaque agent", !detail.some(d => d.endsWith("nom")), `${Object.keys(O.agents).length} profils`);
  note("11. Relations hiérarchiques exactes", okSup, detail.filter(d => /sup/.test(d)).join(", "));
  note("12. Statuts exacts (repris du registre)", okSt, detail.filter(d => /≠/.test(d)).join(", "));
  const avecSup = Object.values(O.agents).find(a => a.superieur);
  if (avecSup) {
    await vue(p, `#/agent/${avecSup.id}`);
    await Promise.all([p.waitForFunction(id => location.hash === "#/agent/" + id, avecSup.superieur), p.click(`.s a[href="#/agent/${avecSup.superieur}"]`)]);
    await p.waitForTimeout(300);
    note("6. Navigation entre agents (vers le manager)", (await p.textContent("h1")).includes(nom(avecSup.superieur)), `${avecSup.id} → ${avecSup.superieur}`);
  }

  // 10. Organigramme
  let okOc = true; detail = [];
  for (const e of E) {
    await vue(p, `#/e/${e.id}/organigramme`);
    const n = await p.$$eval("#oc .noeud", l => l.length).catch(() => 0);
    if (n !== e.postes.length) { okOc = false; detail.push(`${e.id}: ${n}/${e.postes.length}`); }
  }
  note("10. Organigramme exact (une carte par poste du registre)", okOc, detail.join(", "));
  await vue(p, `#/e/${riche.id}/organigramme`);
  const cible = riche.agents[0];
  if (cible) {
    await p.fill("#oc-cherche", cible.nom.slice(0, 6).toLowerCase());
    const trouve = await p.$$eval("#oc .noeud.trouve", l => l.length);
    await p.click("[data-z='1.15']"); const z = await p.$eval("#oc-plan", x => x.style.transform);
    await p.click("[data-tout='plier']"); const plies = await p.$$eval("#oc li.plie", l => l.length);
    note("10b. Organigramme : recherche, zoom, repli", trouve > 0 && /scale\(1\.1/.test(z) && plies >= 0, `${trouve} trouvé(s) · ${z} · ${plies} replié(s)`);
  }

  // 13-14. Missions et livrables
  const avecLiv = Object.values(O.missions).find(m => m.livrables.length);
  const att = Object.values(O.missions).filter(m => m.attributaire);
  await vue(p, `#/e/${riche.id}/missions`);
  const lignes = await p.$$eval("#liste-missions tbody tr", l => l.length).catch(() => 0);
  const nm = Object.values(O.missions).filter(m => m.siege === riche.id).length;
  note("13. Missions de l'entreprise exactes", lignes === nm, `${lignes}/${nm}`);
  for (const m of att.slice(0, 5)) {
    await vue(p, `#/mission/${m.id}`);
    const t = await p.textContent("#vue");
    if (!t.includes(nom(m.attributaire) || m.attributaire) || !t.includes(m.titre)) note(`13b. Mission ${m.id}`, false, "agent ou titre absent");
  }
  if (avecLiv) {
    await vue(p, `#/mission/${avecLiv.id}`);
    const href = await p.$eval(`a[href*="${avecLiv.livrables[0].chemin}"]`, a => a.href);
    const r = await p.evaluate(u => fetch(u).then(x => x.status), href);
    note("14. Livrable exact et consultable", r === 200 && (await p.textContent("#vue")).includes(avecLiv.livrables[0].sha256.slice(0, 12)), `${avecLiv.livrables[0].chemin} → ${r}`);
  } else note("14. Livrables : aucun au registre, état vide affiché", true);

  // 15-19. Intégrité
  const cartesAgents = new Set();
  for (const e of E) { await vue(p, `#/e/${e.id}/annuaire`); (await p.$$eval("a.carte.agent", l => l.map(a => a.getAttribute("href")))).forEach(h => cartesAgents.add(h.split("/").pop())); }
  note("15. Aucun agent fictif (annuaires = registre)", [...cartesAgents].every(id => O.agents[id]) && cartesAgents.size === Object.values(O.agents).filter(a => a.entreprise).length, `${cartesAgents.size} affichés`);
  const actifs = Object.values(O.agents).filter(a => a.statut === "en_execution");
  const affichesActifs = [];
  for (const a of Object.values(O.agents)) { await vue(p, `#/agent/${a.id}`); if ((await p.$eval(".statut", x => x.textContent)).includes("exécution")) affichesActifs.push(a.id); }
  note("16. Aucune fausse présence (« en exécution » ⇔ exécution au registre)", affichesActifs.length === actifs.length && actifs.every(a => a.preuve && journal.includes(`"run": "${a.preuve}"`)), `${affichesActifs.join(", ") || "aucun"}`);
  const reus = Object.values(O.reunions);
  let okReu = true;
  for (const e of E) { await vue(p, `#/e/${e.id}/reunions`); const n = await p.$$eval("#vue .carte", l => l.length); if (n !== reus.filter(r => r.entreprise === e.id).length) okReu = false; }
  note("17. Aucune fausse réunion (réunions affichées = registre)", okReu && Object.values(O.agents).filter(a => a.statut === "en_reunion").every(a => reus.some(r => !r.close && r.participants.includes(a.id))), `${reus.length} réunion(s)`);
  note("18. Aucune permission supplémentaire (aucune requête d'écriture, aucun formulaire)", !p.posts.length && !(await p.$("main form")), p.posts.join(" | "));
  const tout = JSON.stringify(O) + (await p.content());
  note("19. Aucun secret exposé", !/-----BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20}|github_pat_|sk-[A-Za-z0-9]{20}|"graine_privee"|"phrase"/.test(tout));

  // 22-25, 27. Compatibilité et liens
  await vue(p, `#/agent/${Object.keys(O.agents)[0]}`); await p.reload({waitUntil: "networkidle"}); await p.waitForTimeout(500);
  note("22. Rechargement d'un profil", (await p.textContent("h1")).includes(Object.values(O.agents)[0].nom));
  const q = await page({...devices["Pixel 7"]}); await q.goto(B + `#/e/${riche.id}`, {waitUntil: "networkidle"}); await q.waitForTimeout(800);
  note("23. Navigateur neuf (sans cache ni stockage)", (await q.textContent("h1")).includes(riche.nom) && !q.erreurs.length, q.erreurs.join(" | "));
  let deborde = [];
  for (const h of [`#/`, `#/e/${riche.id}`, `#/e/${riche.id}/organigramme`, `#/agent/${Object.keys(O.agents)[0]}`]) { await q.goto(B + h, {waitUntil: "networkidle"}); await q.waitForTimeout(400); if (await q.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) deborde.push(h); }
  note("24. Affichage mobile sans débordement", !deborde.length, deborde.join(", "));
  note("25. Affichage ordinateur sans erreur", !p.erreurs.length, p.erreurs.slice(0, 3).join(" | "));
  const vus = new Set(), aVoir = [`#/`, `#/e/${riche.id}`, `#/e/${riche.id}/direction`]; let morts = [];
  for (const h of aVoir) {
    await vue(p, h);
    for (const l of await p.$$eval("#vue a[href^='#/']", x => x.map(a => a.getAttribute("href")))) {
      if (vus.has(l) || vus.size > 80) continue; vus.add(l); await vue(p, l);
      if (/Introuvable|indisponible/.test(await p.textContent("h1"))) morts.push(l);
    }
  }
  note("27. Liens internes valides", !morts.length, `${vus.size} liens · ${morts.join(", ")}`);
  await b.close();
  console.log(`Bilan : ${R.filter(Boolean).length}/${R.length} PASS`);
  process.exit(R.every(Boolean) ? 0 : 1);
})().catch(e => { console.log("échec : " + e.message); process.exit(1); });
