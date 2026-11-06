// Test navigateur de la Résidence (appelé par audit/preuves.py avec le port et la phrase de TEST).
// Codes : 0 PASS · 1 FAIL · 3 NOT TESTED (Playwright absent).
const path = require("path"), {execFileSync} = require("child_process");
let chromium;
try { ({chromium} = require("playwright")); } catch { console.log("Playwright absent"); process.exit(3); }
const [port, phrase] = process.argv.slice(2), ILE = path.resolve(__dirname, "..");
const cli = (...a) => execFileSync("python3", [path.join(ILE, "orchestrateur", "ile.py"), ...a], {env: process.env}).toString();
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport: {width: 1360, height: 900}});
  await p.route("https://fonts.googleapis.com/**", r => r.fulfill({body: "", contentType: "text/css"}));
  const errs = []; p.on("pageerror", e => errs.push(e.message)); p.on("console", m => { if (m.type() === "error" && !/401|favicon/.test(m.text())) errs.push(m.text()); });
  const aid = cli("approbation", "demander", "--categorie", "git", "--raison", "push vers main (test navigateur)", "--commande", "git push origin main # test-ui").match(/A-\d+/)[0];
  await p.goto(`http://localhost:${port}/residence`);
  await p.waitForSelector(`[data-appr="${aid}"]`, {timeout: 30000});
  const alerte = await p.isVisible("#alerte.on");
  const verrouillee = (await p.textContent("#chip-id")).includes("Lecture seule");
  await p.click(`[data-appr="${aid}"][data-v="accordee"]`);                 // verrouillée : la fenêtre de phrase s'ouvre
  await p.waitForSelector("#dlg-lock[open]", {timeout: 5000});
  await p.fill("#phrase", phrase); await p.click("#lock-go");
  await p.waitForFunction(() => document.querySelector("#chip-id").textContent.includes("Déverrouillée"), null, {timeout: 30000});
  await p.waitForFunction(id => !document.querySelector(`[data-appr="${id}"]`), aid, {timeout: 30000});   // l'action reprend après déverrouillage
  const statut = cli("approbation", "liste").split("\n").find(l => l.startsWith(aid)) || "";
  await p.screenshot({path: require("os").tmpdir() + "/residence-ui.png", fullPage: false});
  const mobile = await b.newPage({viewport: {width: 390, height: 844}});
  await mobile.route("https://fonts.googleapis.com/**", r => r.fulfill({body: "", contentType: "text/css"}));
  await mobile.goto(`http://localhost:${port}/residence`); await mobile.waitForSelector("#kpis .kpi");
  const deborde = await mobile.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  await b.close();
  const ok = alerte && verrouillee && /accordee/.test(statut) && !deborde && !errs.length;
  console.log(`alerte visible : ${alerte} · lecture seule avant phrase : ${verrouillee} · après phrase et clic : « ${statut.trim()} » · mobile sans débordement : ${!deborde} · erreurs console : ${errs.length ? errs.join(" | ") : "aucune"}`);
  process.exit(ok ? 0 : 1);
})().catch(e => { console.log("échec : " + e.message); process.exit(1); });
