// Test 3D du village piloté par le registre v2. Appelé par audit/preuves.py avec le port du serveur de test.
// Codes de sortie : 0 PASS · 1 FAIL · 3 NOT TESTED (Playwright absent).
// THREE_DIR (facultatif) : copie locale de three@0.147.0 si le navigateur n'a pas accès au CDN.
const path = require("path"), fs = require("fs"), {execFileSync} = require("child_process");
let chromium;
try { ({chromium} = require("playwright")); } catch { console.log("Playwright absent"); process.exit(3); }
const port = process.argv[2], ILE = path.resolve(__dirname, "..");
const cli = (...a) => execFileSync("python3", [path.join(ILE, "orchestrateur", "ile.py"), "--auteur", "maire", ...a], {env: process.env}).toString();
(async () => {
  const b = await chromium.launch({args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]});
  const p = await b.newPage({viewport: {width: 1400, height: 860}});
  const local = process.env.THREE_DIR || "/tmp/claude-0/x/package";
  if (fs.existsSync(local)) await p.route("https://cdn.jsdelivr.net/npm/three@0.147.0/**", r => r.fulfill({body: fs.readFileSync(path.join(local, r.request().url().split("three@0.147.0/")[1])), contentType: "application/javascript", headers: {"Access-Control-Allow-Origin": "*"}}));
  await p.route("https://fonts.googleapis.com/**", r => r.fulfill({body: "", contentType: "text/css"}));
  const errs = []; p.on("pageerror", e => errs.push(e.message)); p.on("console", m => { if (m.type() === "error" && !/favicon/.test(m.text())) errs.push(m.text()); });
  await p.goto(`http://localhost:${port}/village/?qualite=bas&heure=nuit&vue=entreprises`);
  await p.waitForFunction(() => window.__metropole && window.__metropole.ready, null, {timeout: 300000});
  const lire = () => p.evaluate(() => ({mode: window.__metropole.mode(), courriers: window.__metropole.coursiersVisibles(), allumes: window.__metropole.siegesAllumes(), bandeau: document.getElementById("now").textContent}));
  await p.waitForTimeout(7000);
  // Exécutions réellement ouvertes avant le test (ex. la Forge qui lance les preuves) : elles restent allumées, légitimement.
  const base = await p.evaluate(async () => (await (await fetch("/api/etat", {cache: "no-store"})).json()));
  const avant = await lire();
  const r1 = cli("run", "debut", "--role", "chef-rev-em").match(/R-\d+/)[0], r2 = cli("run", "debut", "--role", "chef-lexnote").match(/R-\d+/)[0];
  // Le rendu logiciel (swiftshader) est lent : un délai fixe de 12 s échouait 1 fois sur 3, avant comme après la migration.
  // On attend que l'état attendu apparaisse (au plus 45 s) ; s'il n'apparaît pas, le critère ci-dessous échoue comme avant.
  const attendre = (fn, arg) => p.waitForFunction(fn, arg, {timeout: 45000, polling: 500}).catch(() => {});
  await attendre(n => ["rev-em", "lexnote"].every(x => window.__metropole.siegesAllumes().includes(x)) && window.__metropole.coursiersVisibles() === n + 2,
                 Math.min(base.runs_actifs.length, 6));
  const pendant = await lire();
  const shot = path.join(require("os").tmpdir(), "village-v2-pendant.png"); await p.screenshot({path: shot});
  cli("run", "fin", r1); cli("run", "fin", r2);
  await attendre(([n, permis]) => window.__metropole.coursiersVisibles() === n && window.__metropole.siegesAllumes().every(x => permis.includes(x)),
                 [Math.min(base.runs_actifs.length, 6), ["residence", ...base.sieges_actifs]]);
  const apres = await lire();
  await b.close();
  const permis = new Set(["residence", ...base.sieges_actifs]), nBase = Math.min(base.runs_actifs.length, 6);
  const sansAgent = s => s.courriers === nBase && s.allumes.every(x => permis.has(x));
  const ok = avant.mode === "reel" && sansAgent(avant) && pendant.courriers === nBase + 2 && ["rev-em", "lexnote"].every(x => pendant.allumes.includes(x)) && sansAgent(apres) && !errs.length;
  console.log(`exécutions ouvertes avant le test : ${base.runs_actifs.length} · avant : ${avant.courriers} courrier(s), allumés ${JSON.stringify(avant.allumes)} · pendant : ${pendant.courriers} courrier(s), allumés ${JSON.stringify(pendant.allumes)} — « ${pendant.bandeau} » · après : ${apres.courriers} courrier(s), allumés ${JSON.stringify(apres.allumes)} · erreurs console : ${errs.length ? errs.join(" | ") : "aucune"} · capture : ${shot}`);
  process.exit(ok ? 0 : 1);
})().catch(e => { console.log("échec : " + e.message); process.exit(1); });
