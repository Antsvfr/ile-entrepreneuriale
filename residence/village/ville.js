/* Île des Agents — métropole insulaire 3D.
   three.js r147 (CDN), aucun build, aucune texture externe : façades, enseignes et ciel sont générés ici.
   Le registre (registre.json) reste la source de vérité des bâtiments ; etat-de-l-ile.json pilote l'activité réelle. */
"use strict";
const T = THREE;
const Q = new URLSearchParams(location.search);

async function chargerRegistre(){
  for(const url of ["../registre.json", "../../registre.json"]){   // /village/ (serveur) ou residence/village/ (fichier)
    try{ const r = await fetch(url,{cache:"no-store"}); if(r.ok) return await r.json(); }catch(e){}
  }
  return FALLBACK;
}
const nextFrame = () => new Promise(r => requestAnimationFrame(r));

chargerRegistre().then(async REG => {
const B = REG.batiments;
const GROUND = 2, CW = 3, FH = 3.6, BS = .72;   // BS : échelle des bâtiments par rapport à l'île           // niveau du sol, largeur d'une trame de façade, hauteur d'étage
let seed = 11; const rnd = () => (seed = (seed*16807)%2147483647)/2147483647;
const rr = (a,b) => a + (b-a)*rnd(), ri = (a,b) => Math.floor(rr(a,b+1)), pick = a => a[Math.floor(rnd()*a.length)];
const lerp = (a,b,t) => a + (b-a)*t, clamp = (x,a,b) => Math.max(a,Math.min(b,x));

/* ---------- rendu ---------- */
const host = document.getElementById("scene");
const renderer = new T.WebGLRenderer({antialias:true, powerPreference:"high-performance"});
renderer.outputEncoding = T.sRGBEncoding;
renderer.toneMapping = T.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
host.appendChild(renderer.domElement);
const scene = new T.Scene();
const camera = new T.PerspectiveCamera(42, innerWidth/innerHeight, 2, 2600);
const controls = new T.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = .07; controls.screenSpacePanning = false;
controls.minDistance = 14; controls.maxDistance = 360; controls.maxPolarAngle = 1.48; controls.panSpeed = .9;
controls.autoRotate = !matchMedia("(prefers-reduced-motion: reduce)").matches; controls.autoRotateSpeed = .22;

/* qualité adaptative */
const QUAL = {
  bas:   {pr:1,   shadow:1024, cars:36,  lod:.55},
  moyen: {pr:1.5, shadow:2048, cars:70,  lod:.8},
  haut:  {pr:2,   shadow:4096, cars:110, lod:1.1},
};
let qualName = QUAL[Q.get("qualite")] ? Q.get("qualite") : "moyen", qualAuto = !QUAL[Q.get("qualite")];
const lods = [], envMats = [];
const sun = new T.DirectionalLight("#ffd9a8", 2);
function setQuality(name){
  qualName = name; const q = QUAL[name];
  renderer.setPixelRatio(Math.min(devicePixelRatio, q.pr)); renderer.setSize(innerWidth, innerHeight);
  sun.shadow.mapSize.set(q.shadow, q.shadow); if(sun.shadow.map){ sun.shadow.map.dispose(); sun.shadow.map = null; }
  lods.forEach(l => { l.levels[1].distance = 250*q.lod; });
  if(typeof carMeshes !== "undefined") carMeshes.forEach(m => { m.count = Math.min(m.userData.max, q.cars); });
  const sel = document.getElementById("qsel"); if(sel) sel.value = qualAuto ? "auto" : name;
}

/* ---------- jour / nuit ---------- */
const C = s => new T.Color(s);
const KEYS = {   // jour, crépuscule, nuit
  skyTop:[C("#2f6fc4"),C("#2b3a78"),C("#050a1c")], skyMid:[C("#8ec5f0"),C("#e0805a"),C("#0b1a3a")], skyBot:[C("#b9dcee"),C("#f6c27a"),C("#16284f")],
  fog:[C("#bcd9e8"),C("#d99a78"),C("#0c1a35")], hemiSky:[C("#cfe8ff"),C("#ffd2a8"),C("#5a74b8")], hemiGnd:[C("#5b6b5a"),C("#3b3a4a"),C("#101624")],
  sunCol:[C("#fff1d6"),C("#ffb070"),C("#7f9cff")], sea:[C("#0d5f80"),C("#26606e"),C("#0a2438")],
  hemiI:[.42,.5,.3], sunI:[1.25,1.7,.32], elev:[55,14,38], expo:[.95,.92,1.15], win:[.05,.85,1.7], lamp:[0,.9,1.8], env:[.95,.7,.28], stars:[0,0,1], glow:[.1,.45,.9],
};
const tmpC = new T.Color();
function K(n,t){ const a = KEYS[n], u = t < .5 ? t*2 : (t-.5)*2, i = t < .5 ? 0 : 1;
  return typeof a[0] === "number" ? lerp(a[i],a[i+1],u) : tmpC.copy(a[i]).lerp(a[i+1],u); }
const skyU = {top:{value:new T.Color()}, mid:{value:new T.Color()}, bot:{value:new T.Color()}, sunDir:{value:new T.Vector3(0,1,0)}, sunCol:{value:new T.Color()}};
const skyMat = new T.ShaderMaterial({uniforms:skyU, side:T.BackSide, depthWrite:false, fog:false,
  vertexShader:"varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }",
  fragmentShader:"uniform vec3 top,mid,bot,sunCol,sunDir; varying vec3 vP; void main(){ float h = vP.y; vec3 c = mix(bot,mid,smoothstep(-.08,.22,h)); c = mix(c,top,smoothstep(.15,.85,h)); float s = max(dot(normalize(vP),normalize(sunDir)),0.); c += sunCol*(pow(s,300.)*2.2 + pow(s,12.)*.28); gl_FragColor = vec4(c,1.); }"});
const skyMesh = new T.Mesh(new T.SphereGeometry(1500,32,16), skyMat); skyMesh.renderOrder = -10; scene.add(skyMesh);
const starsGeo = new T.BufferGeometry(), sp = [];
for(let i=0;i<700;i++){ const a = rnd()*6.283, e = Math.acos(rnd()*.95+.05); sp.push(1400*Math.sin(e)*Math.cos(a), 1400*Math.cos(e), 1400*Math.sin(e)*Math.sin(a)); }
starsGeo.setAttribute("position", new T.Float32BufferAttribute(sp,3));
const stars = new T.Points(starsGeo, new T.PointsMaterial({color:"#ffffff", size:1.7, sizeAttenuation:false, transparent:true, opacity:0, fog:false, depthWrite:false})); scene.add(stars);
const hemi = new T.HemisphereLight("#ffe7c4", "#2a5b4f", .8); scene.add(hemi);
sun.castShadow = true; sun.shadow.bias = -.0004; sun.shadow.normalBias = .7;
Object.assign(sun.shadow.camera, {left:-125,right:125,top:125,bottom:-125,near:10,far:560});
sun.target.position.set(18,0,-8); scene.add(sun, sun.target);
scene.fog = new T.Fog("#d99a78", 420, 1700);
const SUN_AZ = .85;
let tod = 1, todTarget = 1, todDirty = true;          // 0 jour · .5 crépuscule · 1 nuit
const glassShared = [], lampMats = [], glowMats = [];
const seaMat = new T.MeshPhysicalMaterial({color:"#1d6b73", roughness:.16, metalness:.3, clearcoat:.5, clearcoatRoughness:.2, envMapIntensity:1.5});
envMats.push(seaMat); seaMat.userData.env0 = 1.5;
function applyTod(){
  const t = tod;
  skyU.top.value.copy(K("skyTop",t)); skyU.mid.value.copy(K("skyMid",t)); skyU.bot.value.copy(K("skyBot",t));
  scene.fog.color.copy(K("fog",t)); scene.background = null;
  hemi.color.copy(K("hemiSky",t)); hemi.groundColor.copy(K("hemiGnd",t)); hemi.intensity = K("hemiI",t);
  sun.color.copy(K("sunCol",t)); sun.intensity = K("sunI",t); skyU.sunCol.value.copy(sun.color);
  const e = K("elev",t)*Math.PI/180, d = new T.Vector3(Math.cos(e)*Math.sin(SUN_AZ), Math.sin(e), Math.cos(e)*Math.cos(SUN_AZ));
  skyU.sunDir.value.copy(d); sun.position.copy(sun.target.position).addScaledVector(d,260);
  renderer.toneMappingExposure = K("expo",t);
  const w = K("win",t), l = K("lamp",t), ev = K("env",t), g = K("glow",t);
  glassShared.forEach(m => m.emissiveIntensity = w);
  lampMats.forEach(m => m.emissiveIntensity = l);
  glowMats.forEach(m => m.opacity = g);
  envMats.forEach(m => m.envMapIntensity = m.userData.env0*ev);
  seaMat.color.copy(K("sea",t)); stars.material.opacity = K("stars",t); document.body.classList.toggle("jour", t < .35);
  todDirty = false;
}
function setTime(name){ todTarget = {jour:0, crepuscule:.5, nuit:1}[name]; document.querySelectorAll("[data-time]").forEach(b => b.classList.toggle("on", b.dataset.time === name)); }

/* ---------- environnement PBR (reflets du ciel sur les façades vitrées) ---------- */
{ const envScene = new T.Scene(), um = skyMat.clone();
  um.uniforms = {top:{value:C("#32508f")}, mid:{value:C("#e59a6c")}, bot:{value:C("#f3c88f")}, sunDir:{value:new T.Vector3(.7,.25,.65)}, sunCol:{value:C("#ffc58a")}};
  envScene.add(new T.Mesh(new T.SphereGeometry(100,32,16), um));
  const pm = new T.PMREMGenerator(renderer); scene.environment = pm.fromScene(envScene, .02).texture; pm.dispose(); }

/* ---------- matériaux & façades procédurales ---------- */
const aniso = Math.min(4, renderer.capabilities.getMaxAnisotropy());
function pbr(color, rough=.8, metal=.05, env=.4){
  const m = new T.MeshStandardMaterial({color, roughness:rough, metalness:metal, envMapIntensity:env}); m.userData.env0 = env; envMats.push(m); return m; }
function emis(color, k=1.4){ return new T.MeshStandardMaterial({color:"#111", emissive:color, emissiveIntensity:k, roughness:.5}); }
const SPEC = {
  glassBlue:{base:"#1b3550",frame:"#6d92b3",win:"#0e2740",lit:["#ffe2a8","#bfe4ff"],p:.32},
  glassTeal:{base:"#123c40",frame:"#5fa7a3",win:"#0a2b30",lit:["#ffe9b8","#aef0e6"],p:.3},
  steel:{base:"#2b2f36",frame:"#8a929c",win:"#171b21",lit:["#ffd9a0","#ffffff"],p:.27,bands:true},
  concrete:{base:"#b9b2a6",frame:"#d7d1c6",win:"#1e2a35",lit:["#ffd9a0","#ffe8c4"],p:.24,punched:true},
  resid:{base:"#d9c9b4",frame:"#8a7a68",win:"#223040",lit:["#ffc878","#ffe0a8"],p:.38,balcony:true},
  tech:{base:"#0b0f1a",frame:"#2b3550",win:"#0a1020",lit:["#6ef3ff","#b48cff"],p:.45,led:true},
  amber:{base:"#3a2c1c",frame:"#c79a5a",win:"#201810",lit:["#ffd27a","#fff0c8"],p:.32},
  white:{base:"#e6e8ec",frame:"#ffffff",win:"#2a3a4a",lit:["#ffe3b0","#cfe6ff"],p:.27,punched:true},
};
const FAC = {};
function facade(style){
  if(FAC[style]) return FAC[style];
  const sp = SPEC[style], S = 512, NX = 12, NY = 8, cw = S/NX, ch = S/NY;
  const a = document.createElement("canvas"), b = document.createElement("canvas"); a.width = a.height = b.width = b.height = S;
  const x = a.getContext("2d"), e = b.getContext("2d");
  x.fillStyle = sp.base; x.fillRect(0,0,S,S); e.fillStyle = "#000"; e.fillRect(0,0,S,S);
  const ix = sp.punched ? 7 : 4, iy = sp.punched ? 15 : 11, bal = sp.balcony ? 10 : 0;
  for(let j=0;j<NY;j++) for(let i=0;i<NX;i++){
    const X = i*cw, Y = j*ch, W = cw-2*ix, H = ch-2*iy-bal, lit = rnd() < sp.p;
    x.fillStyle = sp.win; x.fillRect(X+ix, Y+iy, W, H);
    if(lit){ const col = pick(sp.lit); x.globalAlpha = .55; x.fillStyle = col; x.fillRect(X+ix, Y+iy, W, H); x.globalAlpha = 1;
      e.fillStyle = col; e.globalAlpha = .5 + rnd()*.5; e.fillRect(X+ix, Y+iy, W, H); e.globalAlpha = 1; }
    x.strokeStyle = sp.frame; x.lineWidth = sp.punched ? 3 : 2; x.strokeRect(X+ix, Y+iy, W, H);
    if(sp.punched){ x.fillStyle = "rgba(0,0,0,.3)"; x.fillRect(X+ix, Y+iy, W, 5); }
    if(sp.bands){ x.fillStyle = "rgba(0,0,0,.4)"; x.fillRect(X, Y, cw, 6); }
    if(sp.balcony && i%2 === 0){ x.fillStyle = sp.frame; x.fillRect(X, Y+ch-9, cw*2, 9); x.strokeStyle = "rgba(60,50,40,.65)"; x.lineWidth = 1.5;
      for(let k=0;k<9;k++){ x.beginPath(); x.moveTo(X+3+k*(cw*2-6)/8, Y+ch-26); x.lineTo(X+3+k*(cw*2-6)/8, Y+ch-9); x.stroke(); } }
    if(sp.led){ e.fillStyle = i%2 ? "#27e1ff" : "#9b6bff"; e.globalAlpha = .75; e.fillRect(X, Y+ch-5, cw, 3); e.globalAlpha = 1; x.fillStyle = "#12304a"; x.fillRect(X, Y+ch-5, cw, 3); }
  }
  const mk2 = cv => { const t = new T.CanvasTexture(cv); t.wrapS = t.wrapT = T.RepeatWrapping; t.encoding = T.sRGBEncoding; t.anisotropy = aniso; return t; };
  return FAC[style] = {map:mk2(a), emap:mk2(b)};
}
const SHARED = {};
function styleMat(style, own){
  if(!own && SHARED[style]) return SHARED[style];
  const f = facade(style), glassy = ["glassBlue","glassTeal","steel","tech","amber"].includes(style);
  const m = glassy
    ? new T.MeshPhysicalMaterial({map:f.map, emissiveMap:f.emap, emissive:0xffffff, emissiveIntensity:.1, metalness:.6, roughness:.22, clearcoat:.6, clearcoatRoughness:.12, envMapIntensity:1.3})
    : new T.MeshStandardMaterial({map:f.map, emissiveMap:f.emap, emissive:0xffffff, emissiveIntensity:.1, metalness:.08, roughness:.78, envMapIntensity:.7});
  m.userData.env0 = m.envMapIntensity; envMats.push(m);
  if(!own){ SHARED[style] = m; glassShared.push(m); }
  return m;
}
const roofMat = pbr("#5d6168",.85,.1), roofGreen = pbr("#4f8a45",.95,0), concrete = pbr("#a9a69f",.9,.02), metal = pbr("#8d949c",.35,.85), darkMetal = pbr("#2c3036",.5,.7),
      brick = pbr("#6b4a3a",.9,0), stone = pbr("#8f8a80",.9,0), wood = pbr("#9a7b5a",.8,0), asphalt = pbr("#1f2227",.9,0), walk = pbr("#85857f",.9,0);
const beaconMat = emis("#ff3030", 2);
const glowTex = (() => { const c = document.createElement("canvas"); c.width = c.height = 128; const g = c.getContext("2d").createRadialGradient(64,64,0,64,64,64);
  g.addColorStop(0,"rgba(255,255,255,1)"); g.addColorStop(.25,"rgba(255,255,255,.45)"); g.addColorStop(1,"rgba(255,255,255,0)");
  const x = c.getContext("2d"); x.fillStyle = g; x.fillRect(0,0,128,128); return new T.CanvasTexture(c); })();
const aoTex = (() => { const c = document.createElement("canvas"); c.width = c.height = 128; const x = c.getContext("2d"), g = x.createRadialGradient(64,64,10,64,64,64);
  g.addColorStop(0,"rgba(0,0,0,.6)"); g.addColorStop(1,"rgba(0,0,0,0)"); x.fillStyle = g; x.fillRect(0,0,128,128); return new T.CanvasTexture(c); })();
function glow(color, size, y=0, parent){ const m = new T.SpriteMaterial({map:glowTex, color, blending:T.AdditiveBlending, depthWrite:false, transparent:true, opacity:.5, fog:false}); glowMats.push(m);
  const s = new T.Sprite(m); s.scale.setScalar(size); s.position.y = y; if(parent) parent.add(s); return s; }

/* ---------- géométrie : boîtes de façade, dessous de bâtiment, enseignes ---------- */
function mk(geo, mat, x=0, y=0, z=0, parent){ const m = new T.Mesh(geo, mat); m.position.set(x,y,z); m.castShadow = m.receiveShadow = true; if(parent) parent.add(m); return m; }
function uvBox(g, cols, dcols, floors){
  const uv = g.attributes.uv, ou = ri(0,7)/8, ov = ri(0,7)/8;
  for(let f=0;f<6;f++) for(let k=0;k<4;k++){ const i = f*4+k;
    if(f === 2 || f === 3){ uv.setXY(i,0,0); continue; }
    uv.setXY(i, uv.getX(i)*(f<2 ? dcols : cols)/8 + ou, uv.getY(i)*floors/8 + ov); }
  uv.needsUpdate = true;
}
function tbox(cols, floors, dcols, fm, x=0, y=0, z=0, rf=roofMat, parent){
  const g = new T.BoxGeometry(cols*CW, floors*FH, dcols*CW); g.translate(0, floors*FH/2, 0); uvBox(g, cols, dcols, floors);
  return mk(g, [fm,fm,rf,rf,fm,fm], x, y, z, parent);
}
function cylBuild(r, floors, fm, x=0, y=0, z=0, parent, rTop){
  const h = floors*FH, g = new T.CylinderGeometry(rTop ?? r, r, h, 28, 1); g.translate(0,h/2,0);
  const uv = g.attributes.uv, ou = ri(0,7)/8, circ = 2*Math.PI*r;
  for(let i=0;i<uv.count;i++) uv.setXY(i, uv.getX(i)*circ/CW/8 + ou, uv.getY(i)*floors/8);
  return mk(g, [fm,roofMat,roofMat], x, y, z, parent);
}
function shear(mesh, h, lean){ const p = mesh.geometry.attributes.position; for(let i=0;i<p.count;i++) p.setX(i, p.getX(i) + (p.getY(i)/h)*lean); mesh.geometry.computeVertexNormals(); return mesh; }
function sign(text, accent, W=14, parent, x=0, y=0, z=0, ry=0, dbl=true){
  const c = document.createElement("canvas"); c.width = 512; c.height = 128; const g = c.getContext("2d");
  g.fillStyle = "rgba(8,12,22,.9)"; g.fillRect(0,0,512,128); g.fillStyle = accent; g.fillRect(0,0,16,128); g.fillRect(0,120,512,8);
  g.fillStyle = "#fff"; g.textAlign = "center"; g.textBaseline = "middle";
  let size = 62; g.font = `700 ${size}px "Familjen Grotesk",system-ui,sans-serif`; while(g.measureText(text).width > 440 && size > 22){ size -= 3; g.font = `700 ${size}px "Familjen Grotesk",system-ui,sans-serif`; }
  g.fillText(text, 268, 62);
  const t = new T.CanvasTexture(c); t.encoding = T.sRGBEncoding; t.anisotropy = aniso;
  const m = new T.Mesh(new T.PlaneGeometry(W, W/4), new T.MeshBasicMaterial({map:t, toneMapped:false, side:dbl?T.DoubleSide:T.FrontSide}));
  m.position.set(x,y,z); m.rotation.y = ry; if(parent) parent.add(m); return m;
}
function plaza(g, r, accent, solid=true){
  if(solid) mk(new T.CylinderGeometry(r,r,.16,48), stone, 0,.08,0, g).castShadow = false;
  if(accent){ const ring = new T.Mesh(new T.RingGeometry(r-1.1,r-.5,64), new T.MeshBasicMaterial({color:accent, toneMapped:false, side:T.DoubleSide})); ring.rotation.x = -Math.PI/2; ring.position.y = .2; g.add(ring); }
  const ao = new T.Mesh(new T.PlaneGeometry(r*2.8,r*2.8), new T.MeshBasicMaterial({map:aoTex, transparent:true, depthWrite:false, polygonOffset:true, polygonOffsetFactor:-1}));
  ao.rotation.x = -Math.PI/2; ao.position.y = .03; g.add(ao);
}
function roofKit(g, y, w, d, tall){
  for(let i=0;i<ri(2,3);i++) mk(new T.BoxGeometry(rr(2,w*.3), rr(1,2.4), rr(2,d*.3)), pick([metal,darkMetal,concrete]), rr(-w*.28,w*.28), y+.9, rr(-d*.28,d*.28), g);
  if(tall){ const h = rr(8,14); mk(new T.CylinderGeometry(.12,.28,h,6), metal, 0, y+h/2, 0, g); mk(new T.SphereGeometry(.45,8,6), beaconMat, 0, y+h, 0, g); }
}

/* ---------- terrains : 3 îles reliées par des ponts ---------- */
const LANDS = [
  {id:"M", cx:0,  cz:16,  rx:70, rz:58, seed:1, top:"#686e73"},   // île principale : ville, entreprises, plages
  {id:"T", cx:0,  cz:-66, rx:52, rz:16, seed:2, top:"#4d545d"},   // îlot technologique
  {id:"E", cx:94, cz:4,   rx:16, rz:30, seed:3, top:"#6a6d71"},   // île portuaire
  {id:"P", cx:-74, cz:66, rx:13, rz:11, seed:4, top:"#5d7d52"},   // îlot présidentiel (Résidence)
];
const lf = (L,a) => 1 + .045*Math.sin(3*a+L.seed) + .035*Math.sin(5*a+L.seed*2.1) + .02*Math.sin(9*a+L.seed*.7);
function landAt(x,z,m=.92){ for(const L of LANDS){ const dx = (x-L.cx)/L.rx, dz = (z-L.cz)/L.rz, k = lf(L,Math.atan2(dz,dx))*m; if(dx*dx+dz*dz < k*k) return L; } return null; }
function edgePt(L,a,s=1){ const f = lf(L,a)*s; return [L.cx + L.rx*f*Math.cos(a), L.cz + L.rz*f*Math.sin(a)]; }
function slab(L, s, y0, y1, top, side){
  const sh = new T.Shape(), N = 110;
  for(let i=0;i<N;i++){ const [x,z] = edgePt(L, i/N*Math.PI*2, s); i ? sh.lineTo(x,-z) : sh.moveTo(x,-z); }
  const g = new T.ExtrudeGeometry(sh, {depth:y1-y0, bevelEnabled:false, curveSegments:1}); g.rotateX(-Math.PI/2); g.translate(0,y0,0);
  const m = new T.Mesh(g, [top,side]); m.receiveShadow = true; m.castShadow = false; scene.add(m); return m;
}
const sandMat = pbr("#d9c28f",.95,0), wallMat = pbr("#8f9399",.8,.05);
const seaGeo = new T.PlaneGeometry(900,900,72,72); seaGeo.rotateX(-Math.PI/2);
const sea = new T.Mesh(seaGeo, seaMat); sea.position.y = -.6; sea.receiveShadow = true; scene.add(sea);
const seaBase = seaGeo.attributes.position.array.slice();
LANDS.forEach(L => {
  if(L.id === "M" || L.id === "P") slab(L, 1.075, -1.8, 1.35, sandMat, sandMat);
  slab(L, 1, -1.4, GROUND, pbr(L.top,.9,.02), wallMat);
});
function disc(x,z,rx,rz,color,y=GROUND+.02,mat){
  const m = new T.Mesh(new T.CircleGeometry(1,56), mat || pbr(color,.95,0)); m.rotation.x = -Math.PI/2; m.scale.set(rx,rz,1); m.rotation.z = 0;
  m.position.set(x,y,z); m.receiveShadow = true; m.material.polygonOffset = true; m.material.polygonOffsetFactor = -1; scene.add(m); return m;
}
// CircleGeometry est dans le plan XY ; après rotation.x=-90°, scale.y agit sur l'axe z du monde
disc(0,0,40,40,"#777b80"); // centre-ville : dallage
disc(0,0,18,18,null,GROUND+.05,new T.MeshStandardMaterial({color:"#d6d0c4", roughness:.8, map:(() => { const c = document.createElement("canvas"); c.width = c.height = 512; const x = c.getContext("2d");
  x.fillStyle = "#d6d0c4"; x.fillRect(0,0,512,512); x.strokeStyle = "#a8a396"; x.lineWidth = 3; for(let r=60;r<256;r+=44){ x.beginPath(); x.arc(256,256,r,0,6.283); x.stroke(); }
  for(let a=0;a<24;a++){ x.beginPath(); x.moveTo(256,256); x.lineTo(256+256*Math.cos(a*.2618),256+256*Math.sin(a*.2618)); x.stroke(); }
  const t = new T.CanvasTexture(c); t.encoding = T.sRGBEncoding; return t; })()}));
disc(0,38,60,18,"#85827a");          // quartier des entreprises
disc(46,-10,15,17,"#7aa56a");         // résidentiel : pelouses
disc(-52,8,11,11,"#6f9e5a");          // parc Ouest
disc(-52,8,4.5,4.5,"#3c8fb0",GROUND+.06,new T.MeshPhysicalMaterial({color:"#3c8fb0", roughness:.08, metalness:.3, envMapIntensity:1.5}));
disc(-48,44,11,9,"#6f9e5a");          // parc Sud-Ouest
disc(94,10,13,16,"#8b8e92");          // cour des conteneurs

/* ---------- réseau routier (graphe) ---------- */
const nodes = [], edges = [], edgeW = {};
const node = (x,z) => (nodes.push({x,z,adj:[],w:4}), nodes.length-1);
function edge(a,b,w,cls="main"){ if(a===b) return; edges.push({a,b,w,cls}); nodes[a].adj.push(b); nodes[b].adj.push(a); edgeW[a+"-"+b] = edgeW[b+"-"+a] = w; nodes[a].w = Math.max(nodes[a].w,w); nodes[b].w = Math.max(nodes[b].w,w); }
const R1 = [], R2 = [];
for(let k=0;k<16;k++){ const a = k/16*Math.PI*2; R1.push(node(22*Math.cos(a), 22*Math.sin(a))); R2.push(node(62*Math.cos(a), 12+48*Math.sin(a))); }
for(let k=0;k<16;k++){ edge(R1[k],R1[(k+1)%16],8); edge(R2[k],R2[(k+1)%16],8); }
const fixedB = B.filter(b => b.type !== "mairie");
const FOOT = {mairie:17, conseil:15, forge:12, maison:10.5, chantier:7, residence:12};
const footOf = b => (FOOT[b.type] || 10)*BS;
function segDist(px,pz,ax,az,bx,bz){ const dx = bx-ax, dz = bz-az, l2 = dx*dx+dz*dz, t = l2 ? clamp(((px-ax)*dx+(pz-az)*dz)/l2,0,1) : 0; return Math.hypot(px-(ax+t*dx), pz-(az+t*dz)); }
R2.forEach((n,k) => {   // rayons (un sur deux : des blocs assez larges pour des tours)
  if(k % 2) return;   // chaque nœud extérieur se relie au nœud intérieur le plus proche, sauf s'il traverse un bâtiment
  let best = 0, bd = 1e9; R1.forEach((m,i) => { const d = Math.hypot(nodes[n].x-nodes[m].x, nodes[n].z-nodes[m].z); if(d < bd){ bd = d; best = i; } });
  const a = nodes[n], b = nodes[R1[best]];
  if(!B.some(o => o.type !== "mairie" && segDist(o.pos[0],o.pos[1],a.x,a.z,b.x,b.z) < footOf(o)+3.2)) edge(R1[best], n, 6, "ave");
});
// îlot technologique (nord) et île portuaire (est), reliés à l'île principale par deux ponts
const bN1 = node(0,-42.6), bN2 = node(0,-50.4), Ta = node(0,-58), Tw = node(-34,-58), Te = node(34,-58);
edge(R2[12], bN1, 7, "ave"); edge(bN1,bN2,7,"ave"); edge(bN2,Ta,7,"ave"); edge(Ta,Tw,6,"ave"); edge(Ta,Te,6,"ave");
const bE1 = node(70,12), bE2 = node(79.5,12), Ec = node(86,12), En = node(86,-16), Es = node(86,26);
edge(R2[0], bE1, 7, "ave"); edge(bE1,bE2,7,"ave"); edge(bE2,Ec,7,"ave"); edge(Ec,En,6,"ave"); edge(Ec,Es,6,"ave");
const bP1 = node(-56.6,54.4), bP2 = node(-64.6,59.8), Pc = node(-69,63);   // pont vers l'îlot présidentiel
edge(R2[6], bP1, 7, "ave"); edge(bP1,bP2,7,"ave"); edge(bP2,Pc,7,"ave");
// accès aux bâtiments : un nœud proche, et une courte route
const access = {}, spurs = [];
B.forEach(b => {
  const [x,z] = b.pos; let best = 0, bd = 1e9;
  nodes.forEach((n,i) => { const d = Math.hypot(n.x-x, n.z-z); if(d < bd){ bd = d; best = i; } });
  access[b.id] = best;
  const n = nodes[best], dx = n.x-x, dz = n.z-z, l = Math.hypot(dx,dz) || 1, r = footOf(b)-1.5;
  if(l > r + 1) spurs.push({ax:x+dx/l*r, az:z+dz/l*r, bx:n.x, bz:n.z, b:b.id});
});
function dijkstra(s,t){
  const dist = nodes.map(() => 1e9), prev = nodes.map(() => -1), done = new Set(); dist[s] = 0;
  while(done.size < nodes.length){ let u = -1; for(let i=0;i<nodes.length;i++) if(!done.has(i) && (u<0 || dist[i]<dist[u])) u = i;
    if(u<0 || dist[u]>=1e9) break; done.add(u); if(u===t) break;
    for(const v of nodes[u].adj){ const d = dist[u] + Math.hypot(nodes[u].x-nodes[v].x, nodes[u].z-nodes[v].z); if(d < dist[v]){ dist[v] = d; prev[v] = u; } } }
  const p = []; for(let u=t;u>=0;u=prev[u]) p.unshift(u); return p;
}
function roadDist(x,z){ let m = 1e9; for(const e of edges){ const a = nodes[e.a], b = nodes[e.b]; m = Math.min(m, segDist(x,z,a.x,a.z,b.x,b.z) - e.w/2); }
  for(const s of spurs) m = Math.min(m, segDist(x,z,s.ax,s.az,s.bx,s.bz) - 2.5); return m; }

// ponts
function bridge(x1,z1,x2,z2,w,cable){
  const g = new T.Group(), len = Math.hypot(x2-x1,z2-z1); g.position.set((x1+x2)/2,0,(z1+z2)/2); g.rotation.y = -Math.atan2(z2-z1,x2-x1);
  mk(new T.BoxGeometry(len,.9,w+3), concrete, 0, GROUND-.46, 0, g);
  for(const s of [-1,1]) mk(new T.BoxGeometry(len,1,.3), metal, 0, GROUND+.5, s*(w/2+1.3), g);
  for(let x=-len/2+2; x<len/2; x+=8) mk(new T.CylinderGeometry(.9,1.1,4,10), concrete, x, -.4, 0, g);
  if(cable){
    const pts = [];
    for(const sx of [-1,1]) for(const sz of [-1,1]){
      const px = sx*len*.28, pz = sz*(w/2+2); if(sz === 1) mk(new T.BoxGeometry(1.4,26,1.4), concrete, px, GROUND+12, -pz, g); if(sz === 1) mk(new T.BoxGeometry(1.4,26,1.4), concrete, px, GROUND+12, pz, g);
      pts.push(px,GROUND+25,pz, sx*len/2,GROUND+1,pz, px,GROUND+25,pz, sx*len*.05,GROUND+5,pz);
    }
    const lg = new T.BufferGeometry(); lg.setAttribute("position", new T.Float32BufferAttribute(pts,3));
    g.add(new T.LineSegments(lg, new T.LineBasicMaterial({color:"#dfe6ee"})));
  }
  scene.add(g);
}
bridge(0,-41.6,0,-51.4,7,true);
bridge(69,12,80.5,12,7,false);
bridge(-55.6,53.7,-65.6,60.5,7,false);

// routes : instances d'asphalte, trottoirs, marquage, carrefours
{
  const unit = new T.BoxGeometry(1,.1,1), dummy = new T.Object3D(), n = edges.length + spurs.length;
  const road = new T.InstancedMesh(unit, asphalt, n), side = new T.InstancedMesh(unit, walk, n);
  const put = (im,i,ax,az,bx,bz,w,y) => { const l = Math.hypot(bx-ax,bz-az); dummy.position.set((ax+bx)/2,y,(az+bz)/2); dummy.rotation.set(0,-Math.atan2(bz-az,bx-ax),0); dummy.scale.set(l+.1,1,w); dummy.updateMatrix(); im.setMatrixAt(i,dummy.matrix); };
  let i = 0; const dashes = [];
  edges.forEach(e => { const a = nodes[e.a], b = nodes[e.b]; put(side,i,a.x,a.z,b.x,b.z,e.w+3.4,GROUND+.03); put(road,i,a.x,a.z,b.x,b.z,e.w,GROUND+.06); i++;
    const l = Math.hypot(b.x-a.x,b.z-a.z); if(e.cls === "main" || e.w >= 7) for(let d=2; d<l-2; d+=5) dashes.push([a.x+(b.x-a.x)*d/l, a.z+(b.z-a.z)*d/l, -Math.atan2(b.z-a.z,b.x-a.x)]); });
  spurs.forEach(s => { put(side,i,s.ax,s.az,s.bx,s.bz,7,GROUND+.03); put(road,i,s.ax,s.az,s.bx,s.bz,4.2,GROUND+.06); i++; });
  road.receiveShadow = side.receiveShadow = true; scene.add(side, road);
  const disk = new T.CylinderGeometry(1,1,.1,20), nd = new T.InstancedMesh(disk, asphalt, nodes.length), nd2 = new T.InstancedMesh(disk, walk, nodes.length);
  nodes.forEach((p,k) => { dummy.rotation.set(0,0,0); dummy.position.set(p.x,GROUND+.075,p.z); dummy.scale.setScalar(p.w/2); dummy.updateMatrix(); nd.setMatrixAt(k,dummy.matrix);
    dummy.position.y = GROUND+.045; dummy.scale.setScalar(p.w/2+1.7); dummy.updateMatrix(); nd2.setMatrixAt(k,dummy.matrix); });
  nd.receiveShadow = nd2.receiveShadow = true; scene.add(nd2, nd);
  const dm = new T.InstancedMesh(new T.BoxGeometry(2,.03,.22), new T.MeshBasicMaterial({color:"#e9e3cf"}), dashes.length);
  dashes.forEach((d,k) => { dummy.position.set(d[0],GROUND+.13,d[1]); dummy.rotation.set(0,d[2],0); dummy.scale.setScalar(1); dummy.updateMatrix(); dm.setMatrixAt(k,dummy.matrix); }); scene.add(dm);
}

/* ---------- architectures : chaque siège a sa silhouette ---------- */
const occ = B.map(b => ({x:b.pos[0], z:b.pos[1], r:footOf(b)+1}));
function free(x,z,r){
  const h = r*.5, L = landAt(x,z,.9);   // h : demi-largeur réelle de l'empreinte (r est un rayon englobant)
  if(!L || landAt(x+h,z,.88) !== L || landAt(x-h,z,.88) !== L || landAt(x,z+h,.88) !== L || landAt(x,z-h,.88) !== L) return false;
  for(const o of occ) if(Math.hypot(o.x-x,o.z-z) < o.r + h) return false;
  return roadDist(x,z) > h*.8 + 1;
}
function activity(g, vent, own, crown){
  const pm = new T.MeshStandardMaterial({color:"#e8e0d4", transparent:true, opacity:0, flatShading:true}), puffs = [];
  for(let i=0;i<6;i++){ const s = new T.Mesh(new T.IcosahedronGeometry(1,0), pm.clone()); s.userData.t = i/6; s.visible = false; g.add(s); puffs.push(s); }
  const beam = new T.Mesh(new T.CylinderGeometry(1.4,2.6,80,16,1,true), new T.MeshBasicMaterial({color:g.userData.accent || "#ffffff", transparent:true, opacity:0, blending:T.AdditiveBlending, depthWrite:false, side:T.DoubleSide, toneMapped:false, fog:false}));
  beam.position.set(vent[0], vent[1]+40, vent[2]); beam.visible = false; g.add(beam);
  g.userData.house = {own, crown, vent, puffs, beam, act:0};
}
const HQ = {};
HQ.mairie = (b,g) => {
  const own = [styleMat("glassBlue",1)], fm = own[0], acc = b.couleur;
  plaza(g, 19, acc, false);
  tbox(10,3,8, styleMat("concrete"), 0,0,0, roofMat, g);
  let y = 3*FH; [[7,12,6],[5,7,5],[3,5,3]].forEach(([c,f,dc]) => { tbox(c,f,dc,fm,0,y,0,roofMat,g); y += f*FH; });
  for(const s of [-1,1]) mk(new T.BoxGeometry(1.4,36,5), metal, s*11.6, 3*FH+18, 0, g);
  const ringM = emis(acc, 1.8), ring = mk(new T.TorusGeometry(7.5,.5,10,48), ringM, 0, y+3, 0, g); ring.rotation.x = Math.PI/2;
  const orbM = new T.MeshStandardMaterial({color:"#1a1230", emissive:"#e0b23a", emissiveIntensity:1.6, roughness:.3});
  const orb = mk(new T.IcosahedronGeometry(4.4,1), orbM, 0, y+13, 0, g); g.userData.orb = orb; glow("#ffd978", 38, y+13, g);
  mk(new T.CylinderGeometry(.15,.4,30,8), metal, 0, y+15, 0, g); mk(new T.SphereGeometry(.6,8,6), beaconMat, 0, y+30.5, 0, g);
  sign(b.nom.toUpperCase(), acc, 18, g, 0, 7, 12.15, 0);
  sign("LE CERVEAU DE LA MÉTROPOLE", acc, 16, g, 0, y+5, 6.6, 0);
  activity(g, [0,y,0], own, ringM); g.userData.top = y+31; g.userData.rad = 17;
};
HQ.conseil = (b,g) => {
  const own = [styleMat("glassTeal",1)], fm = own[0], acc = b.couleur;
  plaza(g, 19, acc);
  const P = [[0,9,16],[-7.8,-4.5,19],[7.8,-4.5,14]], capM = emis(acc,1.5);
  P.forEach(([x,z,f]) => { cylBuild(5.2,f,fm,x,0,z,g); mk(new T.ConeGeometry(5.5,3.4,28), capM, x, f*FH+1.7, z, g); });
  [[0,1],[1,2],[2,0]].forEach(([i,j]) => { const a = P[i], c = P[j], l = Math.hypot(c[0]-a[0],c[1]-a[1]) - 8;
    const m = mk(new T.BoxGeometry(l,3.2,3.6), metal, (a[0]+c[0])/2, FH*7, (a[1]+c[1])/2, g); m.rotation.y = -Math.atan2(c[1]-a[1],c[0]-a[0]); });
  const orbM = new T.MeshStandardMaterial({color:"#1a1230", emissive:"#b69cff", emissiveIntensity:1.8, roughness:.3});
  const orb = mk(new T.IcosahedronGeometry(3,1), orbM, 0, FH*21+4, 0, g); g.userData.orb = orb; glow("#c9b6ff", 30, FH*21+4, g);
  sign("CONSEIL DES CRITIQUES", acc, 17, g, 0, 6, 17.6, 0);
  activity(g, [0,FH*19+3,0], own, capM); g.userData.top = FH*22; g.userData.rad = 15;
};
HQ.forge = (b,g) => {
  const own = [styleMat("steel",1)], acc = b.couleur;
  plaza(g, 17, "#ff7a2e");
  tbox(8,3,5, own[0], 0,0,0, roofMat, g);
  mk(new T.BoxGeometry(25,1.2,16), darkMetal, 0, 3*FH+.6, 0, g);
  const chim = [[7,-4,32],[2.5,-4,26]];
  chim.forEach(([x,z,h]) => { mk(new T.CylinderGeometry(1.1,1.6,h,10), brick, x, h/2, z, g); mk(new T.TorusGeometry(1.2,.25,6,16), darkMetal, x, h, z, g).rotation.x = Math.PI/2; });
  for(const z of [-1,6]) mk(new T.CylinderGeometry(3,3,9,20), metal, -14, 4.5, z, g);
  mk(new T.BoxGeometry(.9,18,.9), darkMetal, 12, 9, 9, g); mk(new T.BoxGeometry(.9,18,.9), darkMetal, 12, 9, -9, g); mk(new T.BoxGeometry(1,1,19), darkMetal, 12, 18, 0, g);
  const gate = new T.Mesh(new T.PlaneGeometry(9,6), new T.MeshBasicMaterial({color:"#ff8a3d", toneMapped:false})); gate.position.set(0,4,7.7); g.add(gate);
  const light = new T.PointLight("#ff7a2e", 2.4, 46); light.position.set(0,5,12); g.add(light); g.userData.glow = light; glow("#ff8a3d", 22, 4, g).position.z = 8;
  g.userData.smoke = []; for(let i=0;i<10;i++){ const s = new T.Mesh(new T.IcosahedronGeometry(1,0), new T.MeshStandardMaterial({color:"#cfc6ba", transparent:true, opacity:.6, flatShading:true})); s.userData.t = i/10; g.add(s); g.userData.smoke.push(s); }
  sign("LA FORGE", acc, 13, g, 0, 8, 7.7, 0);
  activity(g, [7,32,-4], own, null); g.userData.top = 34; g.userData.rad = 12;
};
HQ["rev-em"] = (b,g) => {
  const own = [styleMat("amber",1)], acc = b.couleur;
  plaza(g, 15, acc); tbox(6,2,5, styleMat("concrete"), 0,0,0, roofMat, g);
  let y = 2*FH; for(let i=0;i<8;i++){ const m = tbox(5,2,5,own[0],0,y,0,roofMat,g); m.rotation.y = i*.15; m.scale.set(1-i*.035,1,1-i*.035); y += 2*FH; }
  const ringM = emis(acc,1.8), ring = mk(new T.TorusGeometry(5,.35,8,40), ringM, 0, y+1, 0, g); ring.rotation.x = Math.PI/2;
  mk(new T.CylinderGeometry(.12,.3,14,6), metal, 0, y+7, 0, g); mk(new T.SphereGeometry(.5,8,6), beaconMat, 0, y+14, 0, g); glow(acc, 24, y+2, g);
  sign(b.nom, acc, 13, g, 0, 4.2, 7.7, 0);
  activity(g, [0,y,0], own, ringM); g.userData.top = y+14; g.userData.rad = 9.5;
};
HQ.lexnote = (b,g) => {
  const own = [styleMat("glassTeal",1)], acc = b.couleur;
  plaza(g, 15, acc); tbox(7,2,5, styleMat("concrete"), 0,0,0, roofMat, g);
  for(const s of [-1,1]){ const m = tbox(3,14,5,own[0], s*5.2, 2*FH, 0, roofMat, g); shear(m, 14*FH, s*7); }
  const ringM = emis(acc,1.6); mk(new T.BoxGeometry(20,.6,1), ringM, 0, 2*FH+14*FH-2, 0, g);
  mk(new T.CylinderGeometry(1.6,1.6,20,12), metal, 0, 2*FH+10, -2, g); glow(acc, 22, 2*FH+16*FH, g);
  sign(b.nom, acc, 12, g, 0, 4.2, 7.7, 0);
  activity(g, [0,2*FH+14*FH,0], own, ringM); g.userData.top = 16*FH+4; g.userData.rad = 10;
};
HQ["upsa-sales-pilot"] = (b,g) => {
  const own = [styleMat("white",1)], acc = b.couleur;
  plaza(g, 15, acc); cylBuild(9.5,3,styleMat("concrete"),0,0,0,g);
  const h = 15*FH, geo = new T.CylinderGeometry(5.6,8,h,6,1); geo.rotateY(Math.PI/6); geo.translate(0,h/2,0);
  const uv = geo.attributes.uv; for(let i=0;i<uv.count;i++) uv.setXY(i, uv.getX(i)*3.2, uv.getY(i)*15/8);
  mk(geo, [own[0],roofMat,roofMat], 0, 3*FH, 0, g);
  const cm = emis(acc,2), y = 3*FH+h; mk(new T.BoxGeometry(2,9,2), cm, 0, y+5, 0, g); mk(new T.BoxGeometry(8,2.4,2), cm, 0, y+5.5, 0, g); glow(acc, 26, y+5, g);
  sign(b.nom, acc, 13, g, 0, 5, 9.7, 0);
  activity(g, [0,y,0], own, cm); g.userData.top = y+11; g.userData.rad = 10;
};
HQ["bde-emergency"] = (b,g) => {
  const own = [styleMat("steel",1)], acc = b.couleur;
  plaza(g, 15, acc); tbox(6,2,5, styleMat("concrete"), 0,0,0, roofMat, g);
  const m = tbox(5,15,4,own[0], -2, 2*FH, 0, roofMat, g); shear(m, 15*FH, 8);
  const fm = emis(acc,1.8), f = mk(new T.BoxGeometry(1.2,15*FH,5), fm, 8, 2*FH+7.5*FH, 0, g); shear(f, 15*FH, 8);
  const y = 17*FH; mk(new T.ConeGeometry(2,16,4), fm, 6, y+8, 0, g); mk(new T.SphereGeometry(.6,8,6), beaconMat, 6, y+16.5, 0, g); glow(acc, 24, y+10, g).position.x = 6;
  sign(b.nom, acc, 13, g, 0, 4.2, 7.7, 0);
  activity(g, [4,y,0], own, fm); g.userData.top = y+16; g.userData.rad = 10;
};
HQ["cuvee-campus"] = (b,g) => {
  const own = [styleMat("resid",1)], acc = b.couleur;
  plaza(g, 15, acc); cylBuild(9,5,own[0],0,0,0,g); cylBuild(6,3,own[0],-1.2,5*FH,0,g);
  mk(new T.CylinderGeometry(5.2,5.2,.5,24), roofGreen, -1.2, 8*FH+.25, 0, g);
  for(let i=0;i<6;i++) mk(new T.IcosahedronGeometry(1.1,1), pbr("#3f7a3a",.9,0), -1.2+Math.cos(i)*3, 8*FH+1.3, Math.sin(i)*3, g);
  for(const x of [-4,0,4]){ const barrel = mk(new T.CylinderGeometry(1.1,1.1,2.2,14), wood, x, 1.1, 11.5, g); barrel.rotation.z = Math.PI/2; }
  const ringM = emis(acc,1.6), ring = mk(new T.TorusGeometry(9.2,.3,8,40), ringM, 0, 5*FH+.2, 0, g); ring.rotation.x = Math.PI/2;
  sign(b.nom, acc, 13, g, 0, 6, 9.2, 0);
  activity(g, [-1.2,8*FH,0], own, ringM); g.userData.top = 8*FH+2; g.userData.rad = 10;
};
HQ.vetotri = (b,g) => {
  const own = [styleMat("tech",1)], acc = b.couleur;
  plaza(g, 15, acc);
  const dome = mk(new T.SphereGeometry(8.5,32,16,0,Math.PI*2,0,Math.PI/2), new T.MeshPhysicalMaterial({color:"#7fd8ff", transparent:true, opacity:.4, metalness:.9, roughness:.05, envMapIntensity:1.8, side:T.DoubleSide, depthWrite:false}), -3, 0, 0, g); dome.castShadow = false;
  tbox(3,3,3, own[0], -3,0,0, roofMat, g); tbox(4,6,4, own[0], 8,0,-1, roofMat, g);
  const dish = mk(new T.ConeGeometry(2.6,1.4,20,1,true), metal, 8, 6*FH+2, -1, g); dish.rotation.x = Math.PI*.8;
  const ringM = emis(acc,1.8), ring = mk(new T.TorusGeometry(8.7,.25,8,40), ringM, -3, .6, 0, g); ring.rotation.x = Math.PI/2; glow(acc, 20, 8, g).position.x = -3;
  sign(b.nom, acc, 12, g, 0, 5, 9.6, 0);
  activity(g, [8,6*FH+3,-1], own, ringM); g.userData.top = 6*FH+4; g.userData.rad = 11;
};
HQ.ecole = (b,g) => {
  const own = [styleMat("white",1)], acc = b.couleur;
  plaza(g, 16, acc);
  tbox(9,4,2, own[0], 0,0,-9, roofMat, g); tbox(2,4,5, own[0], -12,0,-1, roofMat, g); tbox(2,4,5, own[0], 12,0,-1, roofMat, g);
  mk(new T.BoxGeometry(18,.3,12), roofGreen, 0, .2, -2, g).castShadow = false;
  const tw = tbox(2,10,2, own[0], 0,0,-9, roofMat, g); tw.position.y = 4*FH;
  const ty = 4*FH+10*FH; mk(new T.ConeGeometry(5.2,6,4), emis(acc,1.2), 0, ty+3, -9, g).rotation.y = Math.PI/4;
  const clk = new T.MeshBasicMaterial({color:"#fff7dd", toneMapped:false});
  for(const [dx,dz,ry] of [[0,3.1,0],[0,-3.1,Math.PI],[3.1,0,Math.PI/2],[-3.1,0,-Math.PI/2]]){ const c = new T.Mesh(new T.CircleGeometry(1.6,24), clk); c.position.set(dx,ty-4,-9+dz); c.rotation.y = ry; g.add(c); }
  sign(b.nom, acc, 12, g, 0, 4, 4.4, 0);
  activity(g, [0,ty+6,-9], own, null); g.userData.top = ty+6; g.userData.rad = 14;
};
HQ._generic = (b,g) => {
  const own = [styleMat("glassBlue",1)], acc = b.couleur; plaza(g, 14, acc);
  let y = 0, c = 5; [[.55,5],[.3,3],[.15,2]].forEach(([p,w]) => { const f = Math.round(14*p); tbox(w,f,w,own[0],0,y,0,roofMat,g); y += f*FH; });
  const ringM = emis(acc,1.6); mk(new T.BoxGeometry(14,.5,14), ringM, 0, y, 0, g); sign(b.nom, acc, 12, g, 0, 4, 8, 0);
  activity(g, [0,y,0], own, ringM); g.userData.top = y+4; g.userData.rad = 9;
};
HQ.residence = (b,g) => {
  const acc = b.couleur, own = [styleMat("white",1), styleMat("glassTeal",1)];
  plaza(g, 15, acc);
  mk(new T.BoxGeometry(26,1.2,20), stone, 0,.6,0, g);
  tbox(6,2,4, own[1], -3, 1.2, -2, roofMat, g);
  tbox(5,2,4, own[0], 4, 1.2+2*FH, 0, roofMat, g);
  for(const x of [-.8,8.8]) mk(new T.BoxGeometry(.6,2*FH,.6), metal, x, 1.2+FH, 5.4, g);
  const top = 1.2+4*FH; mk(new T.BoxGeometry(15,.4,12), roofGreen, 4, top+.2, 0, g).castShadow = false;
  const pool = new T.Mesh(new T.BoxGeometry(10,.25,4.5), new T.MeshPhysicalMaterial({color:"#3fb3d9", roughness:.05, metalness:.2, envMapIntensity:1.6, emissive:"#0b4f66", emissiveIntensity:.5})); pool.position.set(3,1.25,7.3); g.add(pool);
  mk(new T.CylinderGeometry(4,4,.18,28), darkMetal, -8, 1.3, -5.5, g); mk(new T.TorusGeometry(3.2,.15,6,32), emis("#ffffff",1.2), -8, 1.42, -5.5, g).rotation.x = Math.PI/2;
  mk(new T.CylinderGeometry(.12,.12,9,6), metal, -11, 1.2+4.5, 7, g); mk(new T.BoxGeometry(2.6,1.5,.06), emis(acc,1.4), -9.7, 1.2+8.2, 7, g);
  for(const [x,z] of [[11,-8],[-11,-1],[11,8],[-3,-9]]){ mk(new T.CylinderGeometry(.2,.3,2.4,6), pbr("#6b4e34",.9,0), x, 2.4, z, g); mk(new T.IcosahedronGeometry(1.8,1), pbr("#3f7a3a",.85,0), x, 4.6, z, g); }
  sign("RÉSIDENCE PRÉSIDENTIELLE", acc, 16, g, 0, 4.4, 10.15, 0); glow(acc, 18, top+2, g);
  activity(g, [4,top,0], own, null); g.userData.top = top+6; g.userData.rad = 13;
};
HQ._chantier = (b,g) => {
  const acc = b.couleur, ghost = new T.MeshStandardMaterial({color:acc, transparent:true, opacity:.22, roughness:.6, depthWrite:false});
  const base = mk(new T.BoxGeometry(11,18,11), ghost, 0, 9, 0, g); base.castShadow = false;
  g.add(new T.LineSegments(new T.EdgesGeometry(base.geometry), new T.LineBasicMaterial({color:acc})).translateY(9));
  for(const [x,z] of [[-6,-6],[6,-6],[6,6],[-6,6]]) mk(new T.BoxGeometry(.4,20,.4), pbr("#c9a35a",.6,.4), x, 10, z, g);
  for(let y=4;y<20;y+=5) for(const s of [-1,1]){ mk(new T.BoxGeometry(12.4,.3,.3), pbr("#c9a35a",.6,.4), 0, y, s*6, g); mk(new T.BoxGeometry(.3,.3,12.4), pbr("#c9a35a",.6,.4), s*6, y, 0, g); }
  mk(new T.BoxGeometry(1,34,1), pbr("#e0b23a",.5,.3), 11, 17, -4, g);
  const jib = new T.Group(); jib.position.set(11,34,-4); g.add(jib); mk(new T.BoxGeometry(26,.9,.9), pbr("#e0b23a",.5,.3), 6, 0, 0, jib); mk(new T.BoxGeometry(4,2,2), concrete, -9, -.5, 0, jib); mk(new T.SphereGeometry(.45,8,6), beaconMat, 18, .8, 0, jib);
  g.userData.jib = jib;
  for(let x=-8;x<=8;x+=4) mk(new T.BoxGeometry(3.6,2.2,.2), pbr("#d9d4c8",.9,0), x, 1.1, 10, g);
  sign("EN CONSTRUCTION · "+b.nom, acc, 14, g, 0, 4.2, 10.4, 0);
  g.userData.top = 36; g.userData.rad = 8;
};
const groups = {}, clickables = [];
function construireBatiment(b){
  const g = new T.Group(), [x,z] = b.pos;
  g.position.set(x, GROUND, z); g.rotation.y = b.type === "mairie" ? 0 : Math.atan2(-x,-z); g.userData.accent = b.couleur;
  const fn = b.type === "residence" ? HQ.residence : b.type === "mairie" ? HQ.mairie : b.type === "conseil" ? HQ.conseil : b.type === "forge" ? HQ.forge : b.type === "chantier" ? HQ._chantier : (HQ[b.id] || HQ._generic);
  fn(b,g); g.scale.setScalar(BS); g.userData.top *= BS; g.userData.rad *= BS;
  g.traverse(o => { if(o.isMesh) o.userData.bid = b.id; });
  scene.add(g); groups[b.id] = g; clickables.push(g);
}

/* ---------- décor des quartiers : tours variées, LOD ---------- */
const DSTYLES = ["glassBlue","glassTeal","steel","white","amber"];
const A = {};
A.step = st => { const fm = styleMat(st), cols = ri(4,7), dcols = ri(4,6), floors = ri(10,17), g = new T.Group(); let y = 0, c = cols, dc = dcols;
  [.55,.3,.15].forEach(p => { const f = Math.max(2,Math.round(floors*p)); tbox(c,f,dc,fm,0,y,0,roofMat,g); y += f*FH; c = Math.max(2,c-2); dc = Math.max(2,dc-1); });
  roofKit(g,y,c*CW,dc*CW,true); return {g, w:cols*CW, d:dcols*CW, top:y, style:st}; };
A.taper = st => { const fm = styleMat(st), r = rr(7,10), floors = ri(12,20), sides = pick([4,6]), h = floors*FH, g = new T.Group();
  const geo = new T.CylinderGeometry(r*rr(.4,.65), r, h, sides, 1); geo.rotateY(Math.PI/sides); geo.translate(0,h/2,0);
  const uv = geo.attributes.uv; for(let i=0;i<uv.count;i++) uv.setXY(i, uv.getX(i)*sides*.8, uv.getY(i)*floors/8);
  mk(geo,[fm,roofMat,roofMat],0,0,0,g); roofKit(g,h,6,6,true); return {g, w:r*2, d:r*2, top:h, style:st}; };
A.cyl = st => { const fm = styleMat(st), r = rr(6,8.5), f1 = ri(9,15), g = new T.Group();
  cylBuild(r,f1,fm,0,0,0,g); cylBuild(r*.68,3,fm,0,f1*FH,0,g); const y = (f1+3)*FH;
  const ring = mk(new T.TorusGeometry(r*.7,.3,6,32), emis(pick(["#6ef3ff","#ffd27a","#ff9fd2"]),1.4), 0, f1*FH+.2, 0, g); ring.rotation.x = Math.PI/2;
  roofKit(g,y,r,r,true); return {g, w:r*2, d:r*2, top:y, style:st}; };
A.lean = st => { const fm = styleMat(st), cols = ri(4,5), dcols = ri(4,5), floors = ri(12,18), g = new T.Group(), m = tbox(cols,floors,dcols,fm,0,0,0,roofMat,g);
  const lean = pick([-1,1])*rr(3,6); shear(m, floors*FH, lean); mk(new T.SphereGeometry(.5,8,6), beaconMat, lean, floors*FH+.6, 0, g);
  return {g, w:cols*CW+Math.abs(lean), d:dcols*CW, top:floors*FH, style:st}; };
A.twist = st => { const fm = styleMat(st), n = ri(5,8), g = new T.Group(), tw = rr(.12,.2); let y = 0;
  for(let i=0;i<n;i++){ const m = tbox(5,2,5,fm,0,y,0,roofMat,g); m.rotation.y = i*tw; m.scale.set(1-i*.03,1,1-i*.03); y += 2*FH; }
  roofKit(g,y,10,10,true); return {g, w:15, d:15, top:y, style:st}; };
A.twin = st => { const fm = styleMat(st), g = new T.Group(), f1 = ri(12,16), f2 = ri(14,19);
  tbox(3,f1,4,fm,-6,0,0,roofMat,g); tbox(3,f2,4,fm,6,0,0,roofMat,g); mk(new T.BoxGeometry(12,3.4,5), metal, 0, f1*FH*.7, 0, g);
  roofKit(g,f1*FH,6,10,false); return {g, w:21, d:12, top:Math.max(f1,f2)*FH, style:st}; };
A.dome = st => { const g = new T.Group(), fm = styleMat("tech");
  mk(new T.SphereGeometry(8,28,14,0,Math.PI*2,0,Math.PI/2), new T.MeshPhysicalMaterial({color:"#7fd8ff", transparent:true, opacity:.4, metalness:.9, roughness:.05, envMapIntensity:1.8, side:T.DoubleSide, depthWrite:false}), 0,0,0,g).castShadow = false;
  tbox(3,3,3,fm,0,0,0,roofMat,g); tbox(3,5,3,fm,12,0,2,roofMat,g); return {g, w:30, d:18, top:5*FH, style:"tech"}; };
A.campus = st => { const fm = styleMat(st === "amber" ? "white" : st), g = new T.Group(), f = ri(3,5);
  tbox(9,f,2,fm,0,0,-7,roofMat,g); tbox(2,f,5,fm,-12,0,-1,roofMat,g); tbox(2,f,5,fm,12,0,-1,roofMat,g); mk(new T.BoxGeometry(18,.3,10), roofGreen, 0,.2,-2,g).castShadow = false;
  tbox(3,f+3,2,styleMat("glassBlue"),0,0,5,roofMat,g); return {g, w:30, d:24, top:(f+3)*FH, style:"white"}; };
A.terrace = () => { const fm = styleMat("resid"), g = new T.Group(); let y = 0, x = 0; const w = ri(5,7);
  for(let i=0;i<3;i++){ const f = ri(2,3); tbox(w-i,f,4,fm,x,y,i%2?-1.5:0,roofMat,g); mk(new T.BoxGeometry((w-i)*CW,.5,4*CW), roofGreen, x, y+f*FH+.3, i%2?-1.5:0, g).castShadow = false; y += f*FH; x += 1.2; }
  return {g, w:w*CW, d:12+3, top:y, style:"resid"}; };
A.res = () => { const fm = styleMat("resid"), g = new T.Group(), c = ri(5,8), f = ri(5,9);
  tbox(c,f,4,fm,0,0,0,roofGreen,g); roofKit(g,f*FH,c*CW,12,false); return {g, w:c*CW, d:12, top:f*FH, style:"resid"}; };
function loBox(r){ const m = tbox(Math.max(2,Math.round(r.w/CW)), Math.max(2,Math.round(r.top/FH)), Math.max(2,Math.round(r.d/CW)), styleMat(r.style)); m.position.y = 0; return m; }
function placeDecor(r, x, z, rot, plain){
  r.g.userData.dec = true;
  if(plain){ const w = new T.Group(); w.position.set(x,GROUND,z); w.rotation.y = rot; w.scale.setScalar(BS); w.add(r.g); scene.add(w); return w; }
  const lod = new T.LOD(); lod.position.set(x,GROUND,z); lod.rotation.y = rot; lod.scale.setScalar(BS); lod.addLevel(r.g, 0); lod.addLevel(loBox(r), 250);
  lods.push(lod); scene.add(lod); return lod;
}
const TECHNAMES = ["LABORATOIRE IA","CENTRE DE DÉVELOPPEMENT","CAMPUS INFORMATIQUE","CENTRE DE RECHERCHE","DATA CENTER","CYBERSÉCURITÉ"];
function decorZone(n, tries, test, choose, named){
  let done = 0;
  for(let k=0;k<tries && done<n;k++){
    const x = rr(-72,112), z = rr(-80,64); if(!test(x,z)) continue;
    const [rad0, make] = choose(), rad = rad0*BS; if(!free(x,z,rad)) continue;
    const r = make(); occ.push({x,z,r:rad*.6+1});
    placeDecor(r, x, z, pick([0,Math.PI/2,Math.PI,-Math.PI/2]));
    if(named && done < named.length) sign(named[done], "#6ef3ff", 11, r.g, 0, Math.min(r.top*.45,14), Math.max(r.d,r.w)*.5+.3, 0);
    done++;
  }
  return done;
}

/* ---------- végétation, mobilier urbain, port (tout en instances) ---------- */
const dummy = new T.Object3D();
function instanced(geo, mat, n){ const m = new T.InstancedMesh(geo, mat, n); m.castShadow = true; m.receiveShadow = true; scene.add(m); return m; }
function scatter(n, test, tries=400){ const out = []; for(let k=0;k<tries && out.length<n;k++){ const x = rr(-74,112), z = rr(-80,66); if(test(x,z) && free(x,z,2.2)) { out.push([x,z]); occ.push({x,z,r:2.6}); } } return out; }
function palms(list){
  const trunk = new T.CylinderGeometry(.15,.26,5.2,6); trunk.translate(0,2.6,0);
  const leaf = new T.ConeGeometry(.5,3.6,4); leaf.rotateZ(-Math.PI/2); leaf.translate(1.8,0,0);
  const tm = instanced(trunk, pbr("#8a6a44",.9,0), list.length), lm = instanced(leaf, pbr("#3f8a3a",.8,0), list.length*7);
  let li = 0; list.forEach(([x,z],i) => { const s = rr(.85,1.3), a0 = rnd()*6.28;
    dummy.position.set(x,GROUND,z); dummy.rotation.set(0,a0,0); dummy.scale.set(s,s,s); dummy.updateMatrix(); tm.setMatrixAt(i,dummy.matrix);
    for(let j=0;j<7;j++){ dummy.position.set(x,GROUND+5.2*s,z); dummy.rotation.set(0,a0+j*.9,-.5); dummy.scale.set(s,s,s); dummy.updateMatrix(); lm.setMatrixAt(li++,dummy.matrix); } });
}
function roundTrees(list){
  const trunk = new T.CylinderGeometry(.2,.3,2.4,6); trunk.translate(0,1.2,0); const fol = new T.IcosahedronGeometry(2.3,1); fol.translate(0,4,0);
  const tm = instanced(trunk, pbr("#6b4e34",.9,0), list.length), fm = instanced(fol, pbr("#ffffff",.85,0), list.length), col = new T.Color();
  list.forEach(([x,z],i) => { const s = rr(.8,1.4); dummy.position.set(x,GROUND,z); dummy.rotation.set(0,rnd()*6,0); dummy.scale.set(s,s,s); dummy.updateMatrix(); tm.setMatrixAt(i,dummy.matrix); fm.setMatrixAt(i,dummy.matrix);
    fm.setColorAt(i, col.set(pick(["#3f7a3a","#4f8a45","#5d9a4a","#35703a"]))); });
}
function lamps(){
  const pts = [];
  edges.filter(e => e.cls === "main").forEach(e => { const a = nodes[e.a], b = nodes[e.b], l = Math.hypot(b.x-a.x,b.z-a.z), nx = -(b.z-a.z)/l, nz = (b.x-a.x)/l;
    for(let d=4; d<l-3; d+=13){ const s = Math.floor(d/13)%2 ? 1 : -1, off = (e.w/2+1.4)*s; pts.push([a.x+(b.x-a.x)*d/l+nx*off, a.z+(b.z-a.z)*d/l+nz*off]); } });
  const pole = new T.CylinderGeometry(.1,.14,5.2,6); pole.translate(0,2.6,0);
  const head = new T.BoxGeometry(1.2,.22,.5); head.translate(.4,5.3,0);
  const lm = new T.MeshStandardMaterial({color:"#222", emissive:"#ffd9a0", emissiveIntensity:0}); lampMats.push(lm);
  const pm = new T.InstancedMesh(pole, metal, pts.length), hm = new T.InstancedMesh(head, lm, pts.length);
  pts.forEach(([x,z],i) => { dummy.position.set(x,GROUND,z); dummy.rotation.set(0,rnd()*6.28,0); dummy.scale.setScalar(1); dummy.updateMatrix(); pm.setMatrixAt(i,dummy.matrix); hm.setMatrixAt(i,dummy.matrix); });
  scene.add(pm, hm);
}
function promenade(){
  const L = LANDS[0], N = 150, planks = new T.InstancedMesh(new T.BoxGeometry(1,.12,3.4), wood, N), pts = [];
  for(let i=0;i<N;i++){ const a0 = i/N*6.2832, a1 = (i+1)/N*6.2832, [x0,z0] = edgePt(L,a0,.965), [x1,z1] = edgePt(L,a1,.965), l = Math.hypot(x1-x0,z1-z0);
    dummy.position.set((x0+x1)/2, GROUND+.08, (z0+z1)/2); dummy.rotation.set(0,-Math.atan2(z1-z0,x1-x0),0); dummy.scale.set(l+.05,1,1); dummy.updateMatrix(); planks.setMatrixAt(i,dummy.matrix);
    if(i%6 === 0) pts.push([x0,z0]); }
  planks.receiveShadow = true; scene.add(planks);
  const post = new T.CylinderGeometry(.08,.1,3,6); post.translate(0,1.5,0); const lm = lampMats[0];
  const pm = new T.InstancedMesh(post, metal, pts.length), hm = new T.InstancedMesh(new T.SphereGeometry(.28,8,6), lm, pts.length);
  pts.forEach(([x,z],i) => { dummy.position.set(x,GROUND,z); dummy.rotation.set(0,0,0); dummy.scale.setScalar(1); dummy.updateMatrix(); pm.setMatrixAt(i,dummy.matrix);
    dummy.position.y = GROUND+3.1; dummy.updateMatrix(); hm.setMatrixAt(i,dummy.matrix); }); scene.add(pm, hm);
  // parasols de plage
  const um = new T.InstancedMesh(new T.ConeGeometry(1.5,.8,10), pbr("#ffffff",.8,0), 16), col = new T.Color(); let k = 0;
  for(let i=0;i<16;i++){ const a = 1.2 + i*.16 + rnd()*.05, [x,z] = edgePt(L,a,1.045); dummy.position.set(x,1.9+.9,z); dummy.rotation.set(0,0,0); dummy.scale.setScalar(1); dummy.updateMatrix(); um.setMatrixAt(k,dummy.matrix); um.setColorAt(k++, col.set(pick(["#e0553a","#ffffff","#2e8bd8","#f2c14e"]))); }
  scene.add(um);
}
function port(){
  // conteneurs empilés
  const cm = new T.InstancedMesh(new T.BoxGeometry(5.6,2.4,2.4), pbr("#ffffff",.6,.3), 48), col = new T.Color(); let n = 0;
  for(let ix=0;ix<3;ix++) for(let iz=0;iz<4;iz++){ const h = ri(1,3); for(let l=0;l<h && n<48;l++){ dummy.position.set(89+ix*6.4, GROUND+1.2+l*2.4, 4+iz*3.2); dummy.rotation.set(0,0,0); dummy.scale.setScalar(1); dummy.updateMatrix(); cm.setMatrixAt(n,dummy.matrix); cm.setColorAt(n++, col.set(pick(["#c0392b","#2e86c1","#d4ac0d","#27ae60","#8e44ad","#e67e22"]))); } }
  cm.count = n; cm.castShadow = cm.receiveShadow = true; scene.add(cm);
  // portiques le long du quai est
  for(const z of [-10,14]){ const c = new T.Group(); c.position.set(106,GROUND,z);
    for(const dz of [-3,3]) mk(new T.BoxGeometry(1,16,1), pbr("#d35400",.5,.3), 0,8,dz,c);
    mk(new T.BoxGeometry(1.2,1.2,8), pbr("#d35400",.5,.3), 0,16,0,c); mk(new T.BoxGeometry(18,1,1.2), pbr("#d35400",.5,.3), 6,17,0,c); scene.add(c); }
  // cargo à quai
  const ship = new T.Group(); ship.position.set(118,-.2,-2); ship.rotation.y = Math.PI/2;
  mk(new T.BoxGeometry(48,5,12), pbr("#1d2a38",.6,.3), 0,1.4,0, ship); const prow = mk(new T.ConeGeometry(6,10,4), pbr("#1d2a38",.6,.3), 29,1.4,0, ship); prow.rotation.z = -Math.PI/2; prow.rotation.x = Math.PI/4;
  mk(new T.BoxGeometry(48.2,.5,12.2), pbr("#c0392b",.7,.1), 0,-1.1,0, ship); mk(new T.BoxGeometry(7,9,10), pbr("#e8e4da",.7,.1), -17,8,0, ship);
  for(let i=0;i<6;i++) for(let j=0;j<3;j++) mk(new T.BoxGeometry(5.6,2.4,2.4), pbr(pick(["#c0392b","#2e86c1","#d4ac0d","#27ae60"]),.6,.3), -8+i*5.8, 5.2+(i%2)*2.4, -3.3+j*3.3, ship);
  ship.userData.base = ship.position.y; scene.add(ship); movers.push(ship);
  // ferries en circuit autour de l'île
  for(let i=0;i<3;i++){ const f = new T.Group(); mk(new T.BoxGeometry(9,1.6,3), pbr("#f2f2f2",.5,.1), 0,.2,0,f); mk(new T.BoxGeometry(4,1.6,2.6), pbr("#2e86c1",.5,.2), -.5,1.8,0,f); const bow = mk(new T.ConeGeometry(1.5,3,4), pbr("#f2f2f2",.5,.1), 5.5,.2,0,f); bow.rotation.z = -Math.PI/2; bow.rotation.x = Math.PI/4;
    f.userData.ferry = {a:i*2.1, speed:.035+i*.008, rx:104-i*6, rz:84-i*5}; scene.add(f); movers.push(f); }
}
const movers = [];

/* ---------- véhicules : circulation sur le vrai graphe routier ---------- */
const carMeshes = [], cars = [];
function initCars(max){
  const bg = new T.BoxGeometry(2.2,.7,1.05); bg.translate(0,.55,0); const cg = new T.BoxGeometry(1.1,.5,.9); cg.translate(-.1,1.05,0);
  const hg = new T.BoxGeometry(.15,.2,.8); hg.translate(1.12,.62,0); const tg = new T.BoxGeometry(.15,.2,.8); tg.translate(-1.12,.62,0);
  const body = new T.InstancedMesh(bg, pbr("#ffffff",.3,.6), max), cab = new T.InstancedMesh(cg, pbr("#10161d",.2,.8), max),
        hl = new T.InstancedMesh(hg, new T.MeshBasicMaterial({color:"#fff3c8"}), max), tl = new T.InstancedMesh(tg, new T.MeshBasicMaterial({color:"#ff2a2a"}), max), col = new T.Color();
  [body,cab,hl,tl].forEach(m => { m.userData.max = max; m.castShadow = true; m.frustumCulled = false; scene.add(m); carMeshes.push(m); });
  for(let i=0;i<max;i++){ const a = Math.floor(rnd()*nodes.length); const j = pick(nodes[a].adj);
    cars.push({i:a, j, t:rnd(), v:rr(9,16)}); body.setColorAt(i, col.set(pick(["#e8e8ea","#c0392b","#2e86c1","#f2c14e","#1c1f26","#7f8c8d","#27ae60"]))); }
  setQuality(qualName);
}
function stepCars(dt){
  const n = carMeshes[0].count;
  for(let k=0;k<n;k++){ const c = cars[k], a = nodes[c.i], b = nodes[c.j], l = Math.hypot(b.x-a.x,b.z-a.z) || 1;
    c.t += dt*c.v/l;
    if(c.t >= 1){ const prev = c.i; c.i = c.j; c.t = 0; const opts = nodes[c.i].adj.filter(q => q !== prev); c.j = opts.length ? pick(opts) : prev; continue; }
    const dx = (b.x-a.x)/l, dz = (b.z-a.z)/l, off = (edgeW[c.i+"-"+c.j]||6)*.2;
    dummy.position.set(a.x+(b.x-a.x)*c.t - dz*off, GROUND+.12, a.z+(b.z-a.z)*c.t + dx*off); dummy.rotation.set(0,-Math.atan2(dz,dx),0); dummy.scale.setScalar(1); dummy.updateMatrix();
    for(const m of carMeshes) m.setMatrixAt(k, dummy.matrix); }
  for(const m of carMeshes){ m.instanceMatrix.needsUpdate = true; }
}

/* ---------- courriers : les agents suivent les vraies routes entre les bâtiments ---------- */
const pathCache = {};
const frontPt = id => { const s = spurs.find(q => q.b === id), b = B.find(q => q.id === id); return s ? [s.ax,s.az] : (b ? b.pos : [0,0]); };
function pathBetween(a,b){
  const key = a+">"+b; if(pathCache[key]) return pathCache[key];
  const pts = [frontPt(a)]; dijkstra(access[a], access[b]).forEach(i => pts.push([nodes[i].x,nodes[i].z])); pts.push(frontPt(b));
  const cum = [0]; for(let i=1;i<pts.length;i++) cum.push(cum[i-1] + Math.hypot(pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1]));
  return pathCache[key] = {pts, cum, len:cum[cum.length-1]};
}
function samplePath(p, d, out){
  d = clamp(d,0,p.len); let i = 1; while(i < p.cum.length-1 && p.cum[i] < d) i++;
  const k = (d-p.cum[i-1])/((p.cum[i]-p.cum[i-1])||1), a = p.pts[i-1], b = p.pts[i];
  out.x = lerp(a[0],b[0],k); out.z = lerp(a[1],b[1],k); out.h = Math.atan2(b[1]-a[1], b[0]-a[0]); return out;
}
function makeCourier(big){
  const g = new T.Group(), s = big ? 1.5 : 1;
  const body = mk(new T.BoxGeometry(2.8*s,.8*s,1.3*s), emis(big ? "#e0b23a" : "#6ef3ff", big ? 1.6 : 1.2), 0,.7*s,0,g), cab = mk(new T.BoxGeometry(1.3*s,.5*s,1.1*s), darkMetal, -.2*s,1.3*s,0,g);
  const scroll = mk(new T.OctahedronGeometry(.75*s,0), new T.MeshStandardMaterial({color:"#e0b23a", emissive:"#e0b23a", emissiveIntensity:.8}), 0,3.4*s,0,g);
  g.userData = {scroll, glow:glow(big ? "#ffd978" : "#6ef3ff", 9*s, 1.4*s, g)}; scene.add(g); return g;
}
const stageColors = ["#e0b23a","#8a5fb0","#ffffff","#ff7a2e"];
const houses = B.filter(b => b.type === "maison");
const ambient = [];
for(let i=0;i<Math.max(3,houses.length);i++){ const g = makeCourier(false); ambient.push({g, house:houses[i%houses.length]?.id || "mairie", leg:0, d:i*18, speed:rr(11,15)}); }
const vrai = makeCourier(true); vrai.visible = false; const vraiS = {leg:-1, d:0};
const POOL = Array.from({length:8}, () => { const g = makeCourier(true); g.visible = false; return g; }), coursiers = new Map();   // un courrier par exécution réelle
const legsFor = house => [["mairie","conseil"],["conseil",house],[house,"forge"],["forge","mairie"]];
const pt = {x:0,z:0,h:0};

/* ---------- activité réelle : etat-de-l-ile.json ---------- */
let ETAT = null, ETAT2 = null, MODE = "demo";   // MODE : reel (registre v2) · ancien (etat-de-l-ile.json) · demo (aucune donnée)
const LEG = {conseil:0, maison:1, forge:2, "terminé":3}, ETAPES = {conseil:"Conseil", maison:"Maison", forge:"Forge", "terminé":"Terminé"};
const maisonActive = () => (ETAT && (ETAT.etape === "maison" || ETAT.etape === "forge")) ? ETAT.maison : null;
async function lireV2(){
  for(const url of ["/api/etat", "../orchestrateur/registre/etat.json"]){
    try{ const r = await fetch(url, {cache:"no-store"}); if(!r.ok) continue; const e = await r.json(); if(e && e.version === 2) return sansExpires(e); }catch(_){}
  }
  return null;
}
// orchestrateur/registre/etat.json est un instantané écrit au dernier événement : sans serveur, une exécution jamais close y resterait
// « active » pour toujours. Même règle que ile.py (RUN_ACTIF_MAX_S = 2 h) : au-delà, elle n'allume plus rien.
function sansExpires(e){
  const ok = (e.runs_actifs || []).filter(r => !(Date.now() - Date.parse(r.depuis) >= 2*3600*1000));
  if(ok.length === (e.runs_actifs || []).length) return e;
  return {...e, runs_actifs: ok, sieges_actifs: [...new Set(ok.map(r => r.siege).filter(Boolean))].sort()};
}
async function lireEtat(){
  ETAT2 = await lireV2();
  if(ETAT2){ MODE = "reel"; ETAT = null; majBandeau(); majBadge(); rafraichirJournal(); return; }
  try{
    const r = await fetch("../orchestrateur/etat-de-l-ile.json", {cache:"no-store"}); if(!r.ok) throw 0;
    const e = await r.json(); if(!e || typeof e !== "object" || !(e.etape in LEG)) throw 0;
    const avant = ETAT && JSON.stringify([ETAT.etape, ETAT.maison]); ETAT = e;
    if(avant !== JSON.stringify([e.etape, e.maison])) vraiS.leg = -1;
    MODE = "ancien";
  }catch(_){ ETAT = null; MODE = "demo"; }
  majBandeau(); majBadge(); rafraichirJournal();
}
const nomDe = id => B.find(b => b.id === id)?.nom || id;
function majBandeau(){
  const el = document.getElementById("now");
  if(MODE === "reel"){
    const R = ETAT2.runs_actifs, extra = [];
    if(ETAT2.decisions_en_attente) extra.push(`${ETAT2.decisions_en_attente} décision(s) vous attendent à la Résidence`);
    if(ETAT2.instructions_non_traitees) extra.push(`${ETAT2.instructions_non_traitees} instruction(s) en cours`);
    el.textContent = (R.length ? `${R.length} agent(s) au travail : ` + R.slice(0,3).map(r => `${r.role} → ${r.siege ? nomDe(r.siege) : "hors siège"}`).join(", ") + (R.length > 3 ? "…" : "") : "Aucun agent au travail") + (extra.length ? " · " + extra.join(" · ") : "");
    el.hidden = false; return;
  }
  if(MODE === "demo"){ el.textContent = "Mode démonstration : aucun registre trouvé, les courriers sont décoratifs (lance python3 serveur.py)."; el.hidden = false; return; }
  if(!ETAT){ el.hidden = true; return; }
  const m = B.find(b => b.id === ETAT.maison), h = ETAT.maj ? new Date(ETAT.maj).toLocaleString("fr-FR",{dateStyle:"short",timeStyle:"medium"}) : "";
  const quoi = `${m ? " · " + m.nom : ""}${ETAT.sujet ? " — " + ETAT.sujet : ""}`, tail = h ? " · " + h : "";
  el.textContent = ETAT.etape === "terminé" ? ((m || ETAT.sujet) ? `Dernière demande terminée${quoi}${tail}` : `Île au repos${tail}`) : `En cours : ${ETAPES[ETAT.etape]}${quoi}${tail}`;
  el.hidden = false;
}

/* ---------- étiquettes, carnet, journal ---------- */
const KINDS = {residence:"Résidence · le président", mairie:"Centre stratégique · le Maire", conseil:"Centre de contrôle · 3 critiques", forge:"Centre de contrôle · vérification", maison:"Siège · projet", chantier:"Chantier · futur bâtiment"};
const labelsEl = document.getElementById("labels");
const labels = B.map(b => {
  const el = document.createElement("button"); el.className = "lbl" + (b.type === "chantier" ? " chantier" : ""); el.type = "button";
  el.innerHTML = (b.type === "chantier" ? "" : `<i style="background:${b.couleur}"></i>`) + b.nom; el.addEventListener("click", () => ouvrir(b.id)); labelsEl.appendChild(el);
  return {el, b, v:new T.Vector3(b.pos[0], GROUND + (groups[b.id]?.userData.top || 30) + 4, b.pos[1]), chantier:b.type === "chantier"};
});
const DISTRICTS = [
  {id:"aerien", nom:"Vue aérienne", tgt:[18,4,-8], pos:[150,128,172]},
  {id:"centre", nom:"Centre-ville", tgt:[0,14,-2], pos:[58,60,78]},
  {id:"strategique", nom:"Quartier stratégique", tgt:[0,42,0], pos:[46,72,56]},
  {id:"tech", nom:"Quartier technologique", tgt:[0,12,-62], pos:[44,52,-10]},
  {id:"entreprises", nom:"Quartier des entreprises", tgt:[0,14,36], pos:[10,60,106]},
  {id:"residentiel", nom:"Résidentiel", tgt:[46,8,-8], pos:[102,50,36]},
  {id:"port", nom:"Port", tgt:[98,8,4], pos:[150,54,58]},
  {id:"nature", nom:"Plages & parcs", tgt:[-52,5,12], pos:[-108,38,58]},
  {id:"residence", nom:"Résidence présidentielle", tgt:[-74,6,66], pos:[-34,34,104]},
];
const distLabels = [["Centre-ville",0,-28,12],["Quartier technologique",0,-62,4],["Quartier des entreprises",0,52,6],["Résidentiel",46,-10,6],["Port",98,8,6],["Plages & parcs",-54,24,4]].map(([nom,x,z,h]) => {
  const el = document.createElement("div"); el.className = "dlbl"; el.textContent = nom; labelsEl.appendChild(el); return {el, v:new T.Vector3(x,GROUND+h,z)}; });
const panel = document.getElementById("panel"), openBtn = document.getElementById("open"); let current = 0, dernierJournal = "";
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function majBadge(){
  const el = document.getElementById("live"); if(!el) return; const b = B[current];
  if(MODE === "reel"){ const n = ETAT2.runs_actifs.filter(r => r.siege === b.id).length; el.hidden = !n; if(n) el.textContent = `● ${n} agent(s) au travail (exécution réelle)`; return; }
  const on = ETAT && ETAT.etape !== "terminé" && (ETAT.etape === b.type || (b.id === ETAT.maison && (ETAT.etape === "maison" || ETAT.etape === "forge")));
  el.hidden = !on; if(on) el.textContent = `● Au travail · étape ${ETAPES[ETAT.etape]}`;
}
async function rafraichirJournal(){
  const box = document.getElementById("jr"); if(!box) return; const b = B.find(x => x.id === box.dataset.id); if(!b || !b.dossier) return;
  try{ const r = await fetch(`../${b.dossier}/journal.md`, {cache:"no-store"}); if(!r.ok) throw 0; const txt = await r.text(); if(txt === dernierJournal && !box.hidden) return; dernierJournal = txt;
    const l = txt.split("\n").map(s => s.trim()).filter(s => /^[-*] /.test(s)).map(s => s.slice(2)).slice(-5).reverse(); if(document.getElementById("jr") !== box) return;
    box.querySelector("ul").innerHTML = l.length ? l.map(s => `<li>${esc(s)}</li>`).join("") : "<li>Journal vide.</li>"; box.hidden = false;
  }catch(_){ box.hidden = true; }
}
const ring = new T.Mesh(new T.RingGeometry(1,1.18,64), new T.MeshBasicMaterial({color:"#ffffff", transparent:true, opacity:.85, side:T.DoubleSide, depthWrite:false, toneMapped:false}));
ring.rotation.x = -Math.PI/2; ring.visible = false; scene.add(ring);
function ouvrir(id, focus=true){
  current = B.findIndex(b => b.id === id); const b = B[current];
  document.getElementById("pKind").textContent = KINDS[b.type] || b.type; document.getElementById("pName").textContent = b.nom; document.getElementById("pSw").style.background = b.couleur;
  document.getElementById("pBody").innerHTML = `
    ${b.type === "chantier" ? '<span class="tag">Chantier · pas encore construit</span>' : ""}
    <p>${esc(b.role)}</p><span class="live" id="live" hidden></span>
    ${b.quartier ? `<div class="f"><span>Quartier</span><p>${esc(b.quartier)}${b.fonction ? " — " + esc(b.fonction) : ""}</p></div>` : ""}
    ${b.etat ? `<div class="f"><span>État réel</span><p>${esc(b.etat)}</p></div>` : ""}
    <div class="f"><span>Agent</span><code>${esc(b.agent)}</code></div>
    ${b.depot ? `<div class="f"><span>Dépôt</span><code>${esc(b.depot.replace("https://",""))}</code></div>` : ""}
    ${b.branches ? `<div class="f"><span>Branches (${b.branches.length})</span><ul class="env">${b.branches.map(x => `<li>${x.nom === b.branche_active ? "★ " : ""}${esc(x.nom)}${x.sha ? " · " + esc(x.sha) : ""}<br><small>${esc(x.role)}</small></li>`).join("")}</ul></div>` : ""}
    ${b.dossier ? `<div class="f"><span>Dossier</span><code>${esc(b.dossier === "." ? "/ (racine)" : b.dossier + "/")}</code></div>` : ""}
    ${b.type === "maison" ? `<div class="f" id="jr" data-id="${esc(b.id)}" hidden><span>Journal · 5 dernières entrées</span><ul class="jr"></ul></div>` : ""}
    <div class="f"><span>${b.type === "chantier" ? "Environnement prévu" : "Environnement"}</span><ul class="env">${(b.environnement||[]).map(e => `<li>${esc(e)}</li>`).join("")}</ul></div>
    ${b.type === "residence" ? `<a class="tag" style="text-decoration:none;border-style:solid;font-size:14px;padding:8px 12px" href="residence.html">Entrer dans la Résidence : tableau de bord →</a>` : ""}
    <div class="f"><span>Dans Claude Code</span><div class="cmd"><code id="cmdTxt">${esc(b.commande)}</code><button id="copy">Copier</button></div></div>`;
  document.getElementById("copy").onclick = async e => { try{ await navigator.clipboard.writeText(b.commande); e.target.textContent = "Copié"; }catch{ const r = document.createRange(); r.selectNodeContents(document.getElementById("cmdTxt")); const s = getSelection(); s.removeAllRanges(); s.addRange(r); e.target.textContent = "Sélectionné"; } };
  dernierJournal = ""; rafraichirJournal(); majBadge(); panel.classList.remove("closed"); openBtn.hidden = true;
  const g = groups[b.id]; if(g && focus){ const R = g.userData.rad || 10; ring.scale.setScalar(R+3); ring.position.set(b.pos[0], GROUND+.3, b.pos[1]); ring.material.color.set(b.couleur); ring.visible = true; focusBuilding(b); }
}
document.getElementById("close").onclick = () => { panel.classList.add("closed"); openBtn.hidden = false; };
openBtn.onclick = () => ouvrir(B[current].id);
document.getElementById("prev").onclick = () => ouvrir(B[(current-1+B.length)%B.length].id);
document.getElementById("next").onclick = () => ouvrir(B[(current+1)%B.length].id);

/* ---------- caméra : transitions cinématiques, quartiers, visite guidée ---------- */
let tw = null, tourTimer = null;
const V3 = a => new T.Vector3(a[0],a[1],a[2]);
function flyTo(pos, tgt, dur=2.4, arc=14){
  stopTour(true); controls.autoRotate = false;
  tw = {t:0, dur, p0:camera.position.clone(), t0:controls.target.clone(), p1:pos.clone(), t1:tgt.clone(), arc};
}
function focusBuilding(b){
  const g = groups[b.id], top = g.userData.top || 30, R = g.userData.rad || 10, c = new T.Vector3(b.pos[0],0,b.pos[1]);
  const dir = b.type === "mairie" ? new T.Vector3(.55,0,.83) : new T.Vector3(-b.pos[0],0,-b.pos[1]).normalize();
  const dist = Math.max(52, R*3.4 + top*.8), tgt = new T.Vector3(b.pos[0], top*.42, b.pos[1]), pos = c.clone().addScaledVector(dir, dist).setY(top*.55 + 22);
  flyTo(pos, tgt, 2.2, 10);
}
function goDistrict(id){ const d = DISTRICTS.find(x => x.id === id); if(!d) return; ring.visible = false; flyTo(V3(d.pos), V3(d.tgt), 2.8, 22); if(id === "aerien") setTimeout(() => { if(!tw) controls.autoRotate = !matchMedia("(prefers-reduced-motion: reduce)").matches; }, 3000);
  document.querySelectorAll("[data-d]").forEach(b => b.classList.toggle("on", b.dataset.d === id)); }
function stopTour(silent){ if(tourTimer){ clearInterval(tourTimer); tourTimer = null; } const bt = document.getElementById("tour"); if(bt) bt.classList.remove("on"); }
function startTour(){ stopTour(); document.getElementById("tour").classList.add("on"); let i = 0; const step = () => { const d = DISTRICTS[1 + (i++ % (DISTRICTS.length-1))]; const keep = tourTimer; ring.visible = false; flyTo(V3(d.pos), V3(d.tgt), 3.2, 24); tourTimer = keep || tourTimer; document.getElementById("tour").classList.add("on"); };
  step(); tourTimer = setInterval(step, 8000); }
controls.addEventListener("start", () => { tw = null; controls.autoRotate = false; if(tourTimer) stopTour(); });
const nav = document.getElementById("hud");
DISTRICTS.forEach(d => { const b = document.createElement("button"); b.textContent = d.nom; b.dataset.d = d.id; b.onclick = () => goDistrict(d.id); nav.appendChild(b); });
document.getElementById("tour").onclick = () => tourTimer ? stopTour() : startTour();
{ const r = document.createElement("a"); r.href = "/residence"; r.textContent = "Résidence ↗"; r.className = "res-lien"; r.title = "Ouvrir la Résidence présidentielle (touche R)"; nav.prepend(r); }
document.querySelectorAll("[data-time]").forEach(b => b.onclick = () => setTime(b.dataset.time));
document.getElementById("qsel").onchange = e => { qualAuto = e.target.value === "auto"; setQuality(qualAuto ? "moyen" : e.target.value); };
addEventListener("keydown", e => { if(/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "")) return; if(e.key === "r" || e.key === "R"){ location.href = "/residence"; return; } if(e.key === "Escape") goDistrict("aerien"); else if(/^[1-9]$/.test(e.key)) goDistrict(DISTRICTS[+e.key-1].id); });

// clic dans la scène
const ray = new T.Raycaster(), ptr = new T.Vector2(); let down = null;
renderer.domElement.addEventListener("pointerdown", e => down = [e.clientX, e.clientY]);
renderer.domElement.addEventListener("pointerup", e => {
  if(!down || Math.hypot(e.clientX-down[0], e.clientY-down[1]) > 6) return;
  ptr.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1); ray.setFromCamera(ptr, camera);
  const hit = ray.intersectObjects(clickables, true).find(h => h.object.userData.bid); if(hit) ouvrir(hit.object.userData.bid);
});
addEventListener("resize", () => { camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });

/* ---------- construction progressive de la métropole ---------- */
const loader = document.getElementById("loader"), bar = document.getElementById("lbar");
let tLast = performance.now(), step = 0; const STEPS = 12;
async function yieldIf(force){ if(force || performance.now()-tLast > 12){ await nextFrame(); tLast = performance.now(); } }
function progress(txt){ step++; bar.style.width = Math.min(100, step/STEPS*100) + "%"; loader.querySelector("span").textContent = txt; }
async function construire(){
  progress("Terrain, ponts et avenues…"); await yieldIf(true);
  for(const b of B){ construireBatiment(b); await yieldIf(); } labels.forEach(l => l.v.y = GROUND + (groups[l.b.id]?.userData.top || 30) + 4); progress("Sièges des projets…"); await yieldIf(true);
  const inCenter = (x,z) => Math.hypot(x,z) > 27 && Math.hypot(x,z) < 62 && z < 30 && landAt(x,z) && landAt(x,z).id === "M";
  progress("Centre-ville : tours…");
  { const pick1 = () => { const k = rnd(), s = pick(DSTYLES); return k<.3 ? [11,() => A.step(s)] : k<.45 ? [11,() => A.taper(s)] : k<.6 ? [10.5,() => A.cyl(s)] : k<.72 ? [11,() => A.lean(s)] : k<.82 ? [12,() => A.twist(s)] : [14,() => A.twin(s)]; };
    for(let k=0;k<30;k++){ decorZone(1, 40, inCenter, pick1); await yieldIf(); } }
  progress("Quartier technologique…"); await yieldIf(true);
  { const tp = () => { const k = rnd(); return k<.3 ? [17,() => A.dome()] : k<.55 ? [10.5,() => A.cyl("tech")] : k<.8 ? [11,() => A.taper("tech")] : [17,() => A.campus("white")]; };
    for(let k=0;k<7;k++){ decorZone(1, 80, (x,z) => landAt(x,z)?.id === "T", tp, [TECHNAMES[k]]); await yieldIf(); } }
  progress("Résidentiel…"); await yieldIf(true);
  { const rp = () => rnd() < .5 ? [13,() => A.terrace()] : [13,() => A.res()];
    for(let k=0;k<12;k++){ decorZone(1, 50, (x,z) => x > 30 && x < 62 && z > -26 && z < 6 && landAt(x,z)?.id === "M", rp); await yieldIf(); } }
  progress("Entreprises et campus…"); await yieldIf(true);
  { for(let k=0;k<4;k++){ decorZone(1, 60, (x,z) => z > 40 && z < 62 && landAt(x,z)?.id === "M", () => rnd() < .5 ? [17,() => A.campus("glassTeal")] : [11,() => A.step("white")]); await yieldIf(); } }
  progress("Végétation…"); await yieldIf(true);
  { const M = LANDS[0], beach = []; for(let i=0;i<70;i++){ const a = rnd()*6.2832, [x,z] = edgePt(M,a,1.04); beach.push([x,z]); }
    const park = (cx,cz,r,n) => scatter(n, (x,z) => Math.hypot(x-cx,z-cz) < r);
    palms(beach.concat(park(-52,8,10,14), park(-48,44,10,12), scatter(26,(x,z) => x>30&&x<62&&z>-24&&z<6)));
    roundTrees(park(-52,8,10,12).concat(park(-48,44,10,10), scatter(40,(x,z) => Math.hypot(x,z)>26&&Math.hypot(x,z)<64&&landAt(x,z)?.id==="M"))); }
  progress("Éclairage urbain et promenade…"); await yieldIf(true); lamps(); promenade();
  progress("Port, cargos et ferries…"); await yieldIf(true); port();
  progress("Circulation…"); await yieldIf(true); initCars(QUAL.haut.cars);
  progress("Prête."); setQuality(qualName); applyTod();
  loader.classList.add("done"); setTimeout(() => loader.remove(), 900);
  window.__metropole.ready = true;
}

/* ---------- boucle principale ---------- */
const clock = new T.Clock(), tmp = new T.Vector3(); let frameN = 0, fpsAcc = 0, fpsN = 0, slow = 0, fast = 0;
function ease(k){ return k<.5 ? 4*k*k*k : 1-Math.pow(-2*k+2,3)/2; }
function frame(){
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), .05), t = clock.elapsedTime; frameN++;
  if(Math.abs(tod-todTarget) > .001){ tod += (todTarget-tod)*Math.min(1,dt*1.6); todDirty = true; } else if(tod !== todTarget){ tod = todTarget; todDirty = true; }
  if(todDirty) applyTod();
  if(tw){ tw.t += dt; const k = Math.min(1, tw.t/tw.dur), e = ease(k);
    camera.position.lerpVectors(tw.p0, tw.p1, e); camera.position.y += Math.sin(Math.PI*e)*tw.arc; controls.target.lerpVectors(tw.t0, tw.t1, e); if(k >= 1) tw = null; }
  controls.target.x = clamp(controls.target.x,-90,130); controls.target.z = clamp(controls.target.z,-100,80); controls.target.y = clamp(controls.target.y,0,90);
  if(frameN % 2 === 0){ const p = seaGeo.attributes.position.array; for(let i=0;i<p.length;i+=3){ const x = seaBase[i], z = seaBase[i+2]; p[i+1] = Math.sin(x*.07+t*.9)*.22 + Math.cos(z*.09+t*.7)*.2; } seaGeo.attributes.position.needsUpdate = true; if(frameN % 6 === 0) seaGeo.computeVertexNormals(); }
  beaconMat.emissiveIntensity = Math.sin(t*3) > 0 ? 2.6 : .15;
  // vie des bâtiments
  const actSet = MODE === "reel" ? new Set(ETAT2.sieges_actifs.concat(ETAT2.decisions_en_attente ? ["residence"] : [])) : new Set([maisonActive()].filter(Boolean));
  const forgeOn = MODE === "reel" ? actSet.has("forge") : (ETAT && ETAT.etape === "forge");
  for(const b of B){ const g = groups[b.id]; if(!g) continue; const h = g.userData.house, ud = g.userData;
    if(ud.orb){ ud.orb.rotation.y += dt*.8; ud.orb.position.y += Math.sin(t*1.4)*.01; }
    if(ud.jib) ud.jib.rotation.y = Math.sin(t*.15 + b.pos[0])*1.2;
    if(ud.glow) ud.glow.intensity = (forgeOn ? 3.4 : 2.2) + Math.sin(t*9)*.3 + Math.sin(t*23)*.2;
    if(ud.smoke) ud.smoke.forEach(s => { s.userData.t = (s.userData.t + dt*.12) % 1; const k = s.userData.t; s.position.set(7 + Math.sin(k*5+t)*1.2, 33 + k*20, -4); s.scale.setScalar(1.2 + k*3.8); s.material.opacity = .6*(1-k); });
    if(!h) continue;
    const on = actSet.has(b.id); h.on = on; h.act += ((on ? 1 : 0) - h.act)*Math.min(1,dt*3);
    h.own.forEach(m => m.emissiveIntensity = K("win",tod) + h.act*1.6); h.beam.visible = h.act > .02; h.beam.material.opacity = h.act*(.28 + Math.sin(t*4)*.06); if(h.crown) h.crown.emissiveIntensity = 1.6 + h.act*3;
    h.puffs.forEach(s => { s.userData.t = (s.userData.t + dt*.25) % 1; const k = s.userData.t; s.position.set(h.vent[0] + Math.sin(k*6+t)*.8, h.vent[1] + 1 + k*9, h.vent[2]); s.scale.setScalar(.9 + k*2.4);
      s.material.opacity = on ? .7*(1-k) : Math.max(0, s.material.opacity - dt); s.visible = s.material.opacity > .01; }); }
  // bateaux
  for(const m of movers){ const f = m.userData.ferry; if(f){ f.a += dt*f.speed; m.position.set(4 + f.rx*Math.cos(f.a), -.1+Math.sin(t*1.3+f.a)*.12, 12 + f.rz*Math.sin(f.a)); m.rotation.y = -Math.atan2(f.rz*Math.cos(f.a), -f.rx*Math.sin(f.a)); } else m.position.y = m.userData.base + Math.sin(t*.8)*.12; }
  if(carMeshes.length) stepCars(dt);
  // courriers
  if(MODE === "reel"){
    vrai.visible = false; ambient.forEach(a => a.g.visible = false);
    const vus = new Set();
    for(const r of ETAT2.runs_actifs.slice(0, POOL.length)){
      vus.add(r.run); let c = coursiers.get(r.run);
      if(!c){ const g = POOL.find(x => ![...coursiers.values()].some(y => y.g === x)); if(!g) break; c = {g, d:0}; coursiers.set(r.run, c); }
      const cible = r.siege && groups[r.siege] ? r.siege : "mairie", p = pathBetween("mairie", cible);
      c.d = Math.min(p.len, c.d + dt*22); samplePath(p, c.d, pt); const arrive = c.d >= p.len;
      c.g.visible = true; c.g.position.set(pt.x, GROUND + .15 + (arrive ? Math.abs(Math.sin(t*3 + c.d))*.15 : 0), pt.z); if(!arrive) c.g.rotation.y = -pt.h;
      const sc = c.g.userData.scroll; sc.rotation.y += dt*3;
    }
    for(const [id,c] of coursiers) if(!vus.has(id)){ c.g.visible = false; coursiers.delete(id); }
  } else if(ETAT){
    const leg = LEG[ETAT.etape], p = pathBetween(...legsFor(ETAT.maison || "conseil")[leg]);
    if(vraiS.leg !== leg){ vraiS.leg = leg; vraiS.d = 0; }
    vraiS.d += dt*22; samplePath(p, vraiS.d, pt); const arrive = vraiS.d >= p.len;
    vrai.visible = !(ETAT.etape === "terminé" && !ETAT.maison && arrive);
    vrai.position.set(pt.x, GROUND + .15 + (arrive ? Math.abs(Math.sin(t*3))*.15 : 0), pt.z); vrai.rotation.y = -pt.h;
    const sc = vrai.userData.scroll; sc.rotation.y += dt*3; sc.material.color.set(stageColors[leg]); sc.material.emissive.set(stageColors[leg]);
    ambient.forEach(a => a.g.visible = false);
  } else {
    vrai.visible = false; POOL.forEach(g => g.visible = false);
    ambient.forEach(a => { const p = pathBetween(...legsFor(a.house)[a.leg]); a.d += dt*a.speed; if(a.d >= p.len){ a.d = 0; a.leg = (a.leg+1) % 4; if(a.leg === 0) a.house = pick(houses)?.id || "mairie"; }
      const q = pathBetween(...legsFor(a.house)[a.leg]); samplePath(q, a.d, pt); a.g.position.set(pt.x, GROUND+.15, pt.z); a.g.rotation.y = -pt.h; a.g.visible = a.d > 1 && a.d < q.len-1;
      a.g.userData.scroll.rotation.y += dt*3; a.g.userData.scroll.material.color.set(stageColors[a.leg]); a.g.userData.scroll.material.emissive.set(stageColors[a.leg]); });
  }
  if(ring.visible){ const s = ring.scale.x; ring.material.opacity = .55 + Math.sin(t*3)*.3; }
  controls.update(); renderer.render(scene, camera);
  labels.forEach(({el,v,chantier}) => { tmp.copy(v).project(camera); const d = camera.position.distanceTo(v), vis = tmp.z < 1 && Math.abs(tmp.x) < 1.1 && Math.abs(tmp.y) < 1.1 && d > 42 && !(chantier && (d > 230 || d < 110));
    el.style.display = vis ? "" : "none"; if(vis){ el.style.left = ((tmp.x+1)/2*innerWidth) + "px"; el.style.top = ((1-tmp.y)/2*innerHeight) + "px"; el.style.opacity = d > 330 ? .65 : 1; } });
  distLabels.forEach(({el,v}) => { tmp.copy(v).project(camera); const d = camera.position.distanceTo(v), vis = tmp.z < 1 && Math.abs(tmp.x) < 1.1 && Math.abs(tmp.y) < 1.1 && d > 120;
    el.style.display = vis ? "" : "none"; if(vis){ el.style.left = ((tmp.x+1)/2*innerWidth) + "px"; el.style.top = ((1-tmp.y)/2*innerHeight) + "px"; el.style.opacity = clamp((d-120)/60,0,.85); } });
  // qualité adaptative
  if(qualAuto && window.__metropole.ready){ fpsAcc += dt; fpsN++;
    if(fpsAcc > 2){ const avg = fpsAcc/fpsN, order = ["bas","moyen","haut"], i = order.indexOf(qualName); fpsAcc = fpsN = 0;
      if(avg > .036){ fast = 0; if(++slow >= 1 && i > 0){ slow = 0; setQuality(order[i-1]); } } else if(avg < .019){ slow = 0; if(++fast >= 3 && i < 2){ fast = 0; setQuality(order[i+1]); } } else { slow = fast = 0; } } }
}

/* ---------- démarrage ---------- */
window.__metropole = {ready:false, mode:() => MODE, coursiersVisibles:() => POOL.filter(g => g.visible).length + ambient.filter(a => a.g.visible).length + (vrai.visible ? 1 : 0), siegesAllumes:() => Object.entries(groups).filter(([,g]) => g.userData.house && g.userData.house.on).map(([id]) => id), dbg:{free, landAt:(x,z,m)=>landAt(x,z,m)&&landAt(x,z,m).id, roadDist, occ, spurs}, renderer, scene, camera, controls, setTime, goDistrict, ouvrir, setQuality, flyTo, DISTRICTS, groups, nodes, edges, cars, info:() => ({calls:renderer.info.render.calls, tris:renderer.info.render.triangles, geos:renderer.info.memory.geometries, tex:renderer.info.memory.textures, lods:lods.length, decor:occ.length, qual:qualName})};
const start = DISTRICTS.find(d => d.id === Q.get("vue")) || DISTRICTS[0];
camera.position.set(...start.pos); controls.target.set(...start.tgt); camera.lookAt(controls.target);
tod = todTarget = {jour:0, crepuscule:.5, nuit:1}[Q.get("heure")] ?? .5; setTime(Q.get("heure") in {jour:1,crepuscule:1,nuit:1} ? Q.get("heure") : "crepuscule"); applyTod();
setQuality(qualName);
panel.classList.add("closed"); openBtn.hidden = false;   // carnet fermé au départ : la vue aérienne reste dégagée
lireEtat(); setInterval(lireEtat, 3000);
frame();
await construire();
if(Q.get("ouvrir")) ouvrir(Q.get("ouvrir")); else ouvrir("mairie", false), panel.classList.add("closed"), openBtn.hidden = false;
});
