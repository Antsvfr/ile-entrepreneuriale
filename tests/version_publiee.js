// Test navigateur de la VERSION PUBLIÉE (GitHub Pages ou tout serveur statique) : node tests/version_publiee.js <url de base>
// Exemple : node tests/version_publiee.js https://antsvfr.github.io/ile-entrepreneuriale/
// Vérifie l'accueil, la Résidence en lecture seule, la vérification publique, la métropole 3D, l'affichage mobile.
// Codes : 0 PASS · 1 FAIL · 3 NOT TESTED (Playwright absent).
let chromium;
try { ({chromium} = require("playwright")); } catch { console.log("Playwright absent"); process.exit(3); }
const base = (process.argv[2] || "").replace(/\/?$/, "/");
if (!/^https?:\/\//.test(base)) { console.log("usage : node tests/version_publiee.js <url de base>"); process.exit(1); }
const res = [];
const note = (nom, ok, detail) => { res.push(ok); console.log(`${ok ? "PASS" : "FAIL"}  ${nom}${detail ? " — " + detail : ""}`); };

(async () => {
  const b = await chromium.launch({args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]});
  const page = async (vp) => {
    const p = await b.newPage({viewport: vp || {width: 1360, height: 900}});
    p.erreurs = [];
    p.on("pageerror", e => p.erreurs.push(e.message));
    p.on("console", m => { if (m.type() === "error" && !/favicon/.test(m.text()) && !(/404/.test(m.text()) && attendu(m.location().url || base))) p.erreurs.push(m.text()); });
    p.on("response", r => { if (r.status() >= 400 && !/favicon/.test(r.url()) && !(r.status() === 404 && attendu(r.url()))) p.erreurs.push(`HTTP ${r.status()} ${r.url()}`); });
    return p;
  };
  const registre = await (await fetch(base + "registre.json")).json();
  const meta = await (await fetch(base + "residence/instantane/meta.json")).json();
  // 404 attendus, et seulement ceux-là : la recherche d'un serveur local (/api/sante, sauf sur *.github.io) et les anciens
  // emplacements des documents gelés, contrôlés exprès (une copie leurre y serait détectée).
  const anciens = meta.anciens_chemins.map(([a]) => "/" + a);
  const attendu = u => { const c = new URL(u).pathname; return c === "/api/sante" || anciens.some(a => c.includes(a)); };

  // 1. Accueil
  let p = await page();
  await p.goto(base, {waitUntil: "networkidle"});
  await p.waitForFunction(() => !/Chargement/.test(document.querySelector("#etat").textContent), null, {timeout: 30000});
  const etat = await p.textContent("#etat"), inst = await p.$$eval("#institutions a", l => l.length);
  note("Accueil : état réel de l'île", /intègre/.test(etat) && etat.includes(`${meta.evenements} événements`), etat.replace(/\s+/g, " ").trim());
  note("Accueil : toutes les institutions du registre", inst === registre.batiments.length, `${inst}/${registre.batiments.length}`);
  note("Accueil : aucune erreur", !p.erreurs.length, p.erreurs.join(" | "));

  // 2. Résidence (lecture seule)
  p = await page();
  await p.goto(base + "residence/village/residence.html", {waitUntil: "networkidle"});
  await p.waitForSelector("#publie:not([hidden])", {timeout: 30000});
  await p.waitForFunction(() => document.querySelectorAll("#journal-t tbody tr").length > 1, null, {timeout: 30000});
  const bandeau = await p.textContent("#publie"), puce = await p.textContent("#chip-id");
  const kpis = await p.$$eval("#kpis > *", l => l.length), projets = await p.$$eval("#projets-liste > *", l => l.length);
  const lignes = await p.$$eval("#journal-t tbody tr", l => l.length);
  const actions = await p.$$eval("[data-appr],[data-dec],[data-mis],[data-prio],#f-ins button", l => ({n: l.length, actives: l.filter(e => !e.disabled).length}));
  const horsLigne = await p.isVisible("#hors-ligne");
  note("Résidence : bandeau « version publiée » avec date et intégrité", /Version publiée/.test(bandeau) && /intègre/.test(bandeau), bandeau.replace(/\s+/g, " ").trim().slice(0, 160));
  note("Résidence : données réelles affichées", kpis > 0 && projets > 0 && lignes > 1 && !horsLigne, `${kpis} indicateurs · ${projets} projets · ${lignes} lignes de journal`);
  note("Résidence : aucune action possible en ligne", /lecture seule/.test(puce) && actions.actives === 0, `${actions.n} commandes, ${actions.actives} actives`);
  note("Résidence : aucune erreur", !p.erreurs.length, p.erreurs.join(" | "));

  // 3. Vérification publique
  p = await page();
  await p.goto(base + "residence/village/verification.html", {waitUntil: "networkidle"});
  await p.waitForFunction(() => /Intègre|Altéré|impossible/.test(document.querySelector("#cartes").textContent) && !/^—$/.test(document.querySelector("#artefacts").textContent.trim()), null, {timeout: 60000});
  await p.waitForFunction(() => !/^\s*—\s*$/.test(document.querySelector("#artefacts td").textContent), null, {timeout: 60000});
  const cartes = await p.textContent("#cartes"), arts = await p.$$eval("#artefacts tr", l => l.map(r => r.textContent));
  note("Vérification : journal recalculé dans le navigateur", /Intègre/.test(cartes) && cartes.includes(`${meta.evenements} événements`) && /identique/.test(cartes), cartes.replace(/\s+/g, " ").trim().slice(0, 200));
  note("Vérification : documents gelés intacts", arts.length > 0 && arts.every(t => /intact/.test(t) && !/MODIFIÉ|introuvable/.test(t)), `${arts.length} documents`);
  note("Vérification : aucune erreur", !p.erreurs.length, p.erreurs.join(" | "));

  // 4. Métropole 3D
  p = await page({width: 1400, height: 860});
  await p.goto(base + "residence/village/index.html?qualite=bas&ouvrir=forge");
  await p.waitForFunction(() => window.__metropole && window.__metropole.ready, null, {timeout: 300000});
  await p.waitForFunction(() => /Version publiée/.test(document.getElementById("now").textContent), null, {timeout: 30000}).catch(() => {});
  const m = await p.evaluate(() => ({mode: window.__metropole.mode(), now: document.getElementById("now").textContent,
    acces: [...document.querySelectorAll("#pBody .acces a")].map(a => a.getAttribute("href")), res: document.getElementById("lien-residence")?.href}));
  note("Métropole : chargée avec les données du registre", m.mode === "reel" && /Version publiée/.test(m.now), m.now.slice(0, 140));
  note("Métropole : le bâtiment ouvre ses fonctions réelles", m.acces.length >= 2 && /residence\.html$/.test(m.res), m.acces.join(" , "));
  await p.screenshot({path: require("os").tmpdir() + "/version-publiee-metropole.png"});
  note("Métropole : aucune erreur", !p.erreurs.length, p.erreurs.join(" | "));

  // 5. Mobile
  for (const chemin of ["", "residence/village/residence.html", "residence/village/verification.html"]) {
    p = await page({width: 390, height: 844});
    await p.goto(base + chemin, {waitUntil: "networkidle"});
    await p.waitForTimeout(1500);
    const deborde = await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    note(`Mobile 390 px : ${chemin || "accueil"}`, !deborde);
  }
  await b.close();
  const ok = res.every(Boolean);
  console.log(`Bilan : ${res.filter(Boolean).length}/${res.length} PASS`);
  process.exit(ok ? 0 : 1);
})().catch(e => { console.log("échec : " + e.message); process.exit(1); });
