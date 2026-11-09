import * as THREE from "three";

// Cliente 3D conectado a la misma SalaEnLinea y SimulacionRonda del proyecto Pygame.
const $ = (id) => document.getElementById(id);
const container = $("game-container"), overlay = $("overlay");
const overlayTitle = $("overlay-title"), overlayCopy = $("overlay-copy");
const startButton = $("start-button"), timerLabel = $("timer"), tagLabel = $("tag-status");
const minimap = $("minimap"), mapCtx = minimap.getContext("2d");
const crosshair = $("crosshair"), toast = $("toast");
const nameInput = $("player-name"), statusLabel = $("connection-status");
const colorInput = $("player-color"), accessoryInput = $("player-accessory");
const WORLD = { width: 12.8, depth: 7.2, halfW: 6.4, halfD: 3.6 };
const keys = new Set(), remote = new Map(), obstacleMeshes = [], pickupMeshes = new Map();
let renderer, scene, camera, clock, yaw = 0, pitch = 0;
let token = null, myId = null, myName = "", snapshot = null, joined = false;
let gameStarted = false, readySent = false, lastSync = 0, syncBusy = false, readyPending = false;
let toastTimer = 0, lastPhase = "", lastEventSeq = 0, cameraInitialized = false;

function worldX(px) { return (Number(px) - 640) / 100; }
function worldZ(py) { return (Number(py) - 360) / 100; }
const COLOR_HEX = {azul:0x3dbfff,rojo:0xf04b55,verde:0x45c878,morado:0xb879ff,amarillo:0xf3d34a,rosa:0xf08ab8,negro:0x303844,blanco:0xe9edf2};
function makePlayer(data) {
  const root = new THREE.Group();
  const tint = COLOR_HEX[data.color] || COLOR_HEX.azul;
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(.23, .48, 4, 8), new THREE.MeshStandardMaterial({color:tint, roughness:.7}));
  body.position.y=.78; body.castShadow=true; root.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(.19,16,12), new THREE.MeshStandardMaterial({color:0xe9bd98}));
  head.position.y=1.42; root.add(head);
  const scarf = new THREE.Mesh(new THREE.TorusGeometry(.24,.055,8,20), new THREE.MeshStandardMaterial({color:0xe52e37}));
  scarf.rotation.x=Math.PI/2; scarf.position.y=1.12; root.add(scarf);
  const accessory = new THREE.Group(); root.add(accessory);
  const accessoryMat = new THREE.MeshStandardMaterial({color:0x26394c,roughness:.65});
  if(data.accesorio === "gorra") {
    const crown = new THREE.Mesh(new THREE.CylinderGeometry(.17,.19,.12,16), accessoryMat); crown.position.y=1.62; accessory.add(crown);
    const brim = new THREE.Mesh(new THREE.BoxGeometry(.34,.035,.22), accessoryMat); brim.position.set(0,1.57,.13); accessory.add(brim);
  } else if(data.accesorio === "gafas") {
    for(const x of [-.085,.085]) { const lens = new THREE.Mesh(new THREE.TorusGeometry(.055,.014,6,16), new THREE.MeshStandardMaterial({color:0x101820,metalness:.25})); lens.position.set(x,1.44,.17); accessory.add(lens); }
    const bridge = new THREE.Mesh(new THREE.BoxGeometry(.06,.018,.018), accessoryMat); bridge.position.set(0,1.44,.17); accessory.add(bridge);
  } else if(data.accesorio === "mochila") {
    const bag = new THREE.Mesh(new THREE.BoxGeometry(.3,.38,.16), new THREE.MeshStandardMaterial({color:0x9b5c32,roughness:.85})); bag.position.set(0,.83,-.25); accessory.add(bag);
  }
  const ring = new THREE.Mesh(new THREE.TorusGeometry(.48,.035,8,32), new THREE.MeshBasicMaterial({color:0xff3030}));
  ring.rotation.x=Math.PI/2; ring.position.y=.04; ring.visible=false; root.add(ring);
  scene.add(root);
  return {root, body, ring, accessory, id:Number(data.id), name:data.nombre || `J${data.id}`};
}
function initScene() {
  scene = new THREE.Scene(); scene.background = new THREE.Color(0x9bc6d0); scene.fog = new THREE.Fog(0x9bc6d0,18,42);
  camera = new THREE.PerspectiveCamera(78,1,.05,100);
  renderer = new THREE.WebGLRenderer({antialias:true,powerPreference:"high-performance"});
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,2)); renderer.shadowMap.enabled=true;
  container.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight(0xe6f6ff,0x354a36,2.1));
  const sun=new THREE.DirectionalLight(0xfff2d5,2.4); sun.position.set(-5,12,7); sun.castShadow=true; sun.shadow.mapSize.set(1024,1024); scene.add(sun);
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(WORLD.width,WORLD.depth),new THREE.MeshStandardMaterial({color:0x4d8a58,roughness:.92}));
  ground.rotation.x=-Math.PI/2; ground.receiveShadow=true; scene.add(ground);
  const grid=new THREE.GridHelper(12.8,32,0x8bb58b,0x6a9b70); grid.position.y=.012; grid.scale.z=WORLD.depth/WORLD.width; scene.add(grid);
  const wallMat=new THREE.MeshStandardMaterial({color:0x405767});
  [[0,.8,-3.6,12.8,1.6,.16],[0,.8,3.6,12.8,1.6,.16],[-6.4,.8,0,.16,1.6,7.2],[6.4,.8,0,.16,1.6,7.2]].forEach(([x,y,z,sx,sy,sz])=>{const m=new THREE.Mesh(new THREE.BoxGeometry(sx,sy,sz),wallMat);m.position.set(x,y,z);m.castShadow=true;scene.add(m);});
  clock=new THREE.Clock(); resize(); addEventListener("resize",resize); renderer.setAnimationLoop(frame);
}
function resize(){if(!renderer||!camera)return;const w=container.clientWidth||innerWidth,h=container.clientHeight||innerHeight;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);}
function clearRoundObjects(){for(const p of remote.values())scene.remove(p.root);remote.clear();for(const o of obstacleMeshes)scene.remove(o);obstacleMeshes.length=0;for(const p of pickupMeshes.values())scene.remove(p);pickupMeshes.clear();}
function syncWorld(s) {
  const incoming = new Set();
  for (const d of (s.jugadores||[])) {
    const id=Number(d.id); incoming.add(id);
    let p=remote.get(id); if(!p){p=makePlayer(d);remote.set(id,p);} p.root.visible = id !== myId; p.name=d.nombre||p.name;
    const tx=worldX(d.x), tz=worldZ(d.y); p.root.position.set(tx,0,tz);
    p.root.rotation.y = d.direccion_cara ? (d.direccion_cara>0?Math.PI/2:-Math.PI/2) : 0;
    p.ring.visible=!!d.es_lleva;
    p.body.material.color.setHex(COLOR_HEX[d.color] || COLOR_HEX.azul);
  }
  for(const [id,p] of remote){if(!incoming.has(id)){scene.remove(p.root);remote.delete(id);}}
  const obs=s.obstaculos||[];
  while(obstacleMeshes.length>obs.length){scene.remove(obstacleMeshes.pop());}
  obs.forEach((o,i)=>{
    const isZone=o.tipo==="zona";
    if(!obstacleMeshes[i] || obstacleMeshes[i].userData.kind!==o.tipo){if(obstacleMeshes[i])scene.remove(obstacleMeshes[i]);const mesh=new THREE.Mesh(new THREE.BoxGeometry(isZone?.8:1, isZone?.025:.95, isZone?.8:1),new THREE.MeshStandardMaterial({color:isZone?0x239bc7:0x95613b,transparent:isZone,opacity:isZone?.72:1,roughness:.85}));mesh.userData.kind=o.tipo;mesh.castShadow=!isZone;mesh.receiveShadow=true;scene.add(mesh);obstacleMeshes[i]=mesh;}
    obstacleMeshes[i].position.set(worldX(o.x+(isZone?40:50)),isZone?.02:.48,worldZ(o.y+(isZone?40:50)));
  });
  const active=new Set();
  (s.power_ups||[]).forEach((pu,i)=>{const key=`${pu.x}:${pu.y}:${pu.tipo}`;active.add(key);let mesh=pickupMeshes.get(key);if(!mesh){const colors={velocidad:0x38e58c,congelar:0x44d8ff,escudo:0xffd34d};mesh=new THREE.Mesh(new THREE.OctahedronGeometry(.24),new THREE.MeshStandardMaterial({color:colors[pu.tipo]||0xffffff,emissive:colors[pu.tipo]||0xffffff,emissiveIntensity:.22}));scene.add(mesh);pickupMeshes.set(key,mesh);}mesh.position.set(worldX(pu.x),.48,worldZ(pu.y));mesh.rotation.y+=.04;});
  for(const [key,mesh] of pickupMeshes){if(!active.has(key)){scene.remove(mesh);pickupMeshes.delete(key);}}
}
function drawMinimap(){const w=minimap.width,h=minimap.height;mapCtx.clearRect(0,0,w,h);mapCtx.fillStyle="#183a2b";mapCtx.fillRect(0,0,w,h);mapCtx.strokeStyle="#c2dfbd";mapCtx.lineWidth=3;mapCtx.strokeRect(3,3,w-6,h-6);
  (snapshot?.obstaculos||[]).forEach(o=>{const size=o.tipo==="zona"?80:100;mapCtx.fillStyle=o.tipo==="zona"?"#35a8ce":"#b37b4b";mapCtx.fillRect((o.x/1280)*w,(o.y/720)*h,(size/1280)*w,(size/720)*h);});
  (snapshot?.jugadores||[]).forEach(p=>{const x=(p.x/1280)*w,y=(p.y/720)*h,id=Number(p.id);mapCtx.beginPath();mapCtx.arc(x,y,id===myId?6:5,0,Math.PI*2);mapCtx.fillStyle=p.es_lleva?"#ff3c43":(id===myId?"#42c5ff":"#ffb45c");mapCtx.fill();mapCtx.strokeStyle="#fff";mapCtx.lineWidth=1.5;mapCtx.stroke();});
}
function hud(){if(!snapshot)return;timerLabel.textContent=String(Math.max(0,Math.ceil((snapshot.duracion_ronda||60)-(snapshot.tiempo_ronda||0)))).padStart(2,"0");const holder=(snapshot.jugadores||[]).find(p=>p.es_lleva);tagLabel.textContent=holder?holder.nombre:"—";tagLabel.style.color=holder&&Number(holder.id)===myId?"#66d8ff":"#ffbd74";}
function showToast(msg){toast.textContent=msg;toast.classList.add("show");toastTimer=2;}
async function api(path,data){
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),10000);
  try{
    const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data),signal:controller.signal,cache:"no-store"});
    const raw=await r.text();
    let j;
    try{j=raw?JSON.parse(raw):{};}catch{throw new Error(`Respuesta no válida del servidor (HTTP ${r.status})`);}
    if(!r.ok||j.error)throw new Error(j.error||`HTTP ${r.status}`);
    return j;
  }catch(e){
    if(e.name==="AbortError")throw new Error("El servidor tardó demasiado en responder. Intenta de nuevo.");
    if(e instanceof TypeError)throw new Error("No se pudo conectar con el servidor. Revisa tu conexión.");
    throw e;
  }finally{clearTimeout(timeout);}
}
async function joinRoom(){const name=(nameInput.value||"").trim().slice(0,12)||"Jugador";myName=name;statusLabel.textContent="Conectando…";try{const r=await api("/api/sala/unirse",{nombre:name,color:colorInput.value,accesorio:accessoryInput.value});token=r.token;myId=Number(r.id);joined=true;nameInput.disabled=true;colorInput.disabled=true;accessoryInput.disabled=true;statusLabel.textContent=`Conectado como ${r.nombre} · ${r.jugadores_online}/${r.max_jugadores}`;overlayTitle.textContent="SALA MULTIJUGADOR";overlayCopy.textContent="Comparte la dirección de esta página con otro jugador. Cuando haya al menos 2 conectados, ambos deben pulsar LISTO.";startButton.textContent="LISTO PARA JUGAR";showToast(`Entraste como ${r.nombre}`);await sync(false);}catch(e){statusLabel.textContent=`No se pudo conectar: ${e.message}`;}}
async function sync(ready=false){if(!token)return false;if(syncBusy){if(ready)readyPending=true;return false;}syncBusy=true;const forward=new THREE.Vector3(-Math.sin(yaw),0,-Math.cos(yaw)),right=new THREE.Vector3(Math.cos(yaw),0,-Math.sin(yaw));const dir=new THREE.Vector3();if(keys.has("w")||keys.has("arrowup"))dir.add(forward);if(keys.has("s")||keys.has("arrowdown"))dir.sub(forward);if(keys.has("d")||keys.has("arrowright"))dir.add(right);if(keys.has("a")||keys.has("arrowleft"))dir.sub(right);const input={arriba:dir.z<-.15,abajo:dir.z>.15,izquierda:dir.x<-.15,derecha:dir.x>.15};try{snapshot=await api("/api/sala/sync",{token,entrada:input,listo:ready?true:undefined});syncWorld(snapshot);hud();drawMinimap();statusLabel.textContent=`En sala: ${snapshot.jugadores_online}/${snapshot.max_jugadores} · ${snapshot.fase}`;phaseUI(snapshot);return true;}catch(e){statusLabel.textContent=`Conexión interrumpida: ${e.message}`;if(e.message.includes("token")){token=null;joined=false;readySent=false;nameInput.disabled=false;colorInput.disabled=false;accessoryInput.disabled=false;startButton.textContent="VOLVER A ENTRAR";overlay.classList.remove("hidden");overlayTitle.textContent="SE PERDIÓ LA CONEXIÓN";overlayCopy.textContent="Tu sesión de sala expiró. Pulsa el botón para volver a entrar.";gameStarted=false;crosshair.style.display="none";}return false;}finally{syncBusy=false;if(readyPending){readyPending=false;sync(true).then(ok=>{if(ok)showToast("Marcaste que estás listo");});}}
}
function phaseUI(s){if(s.fase!==lastPhase){lastPhase=s.fase;if(s.fase==="esperando"){overlay.classList.remove("hidden");overlayTitle.textContent="ESPERANDO JUGADORES";overlayCopy.textContent=`Conectados: ${s.jugadores_online}/${s.max_jugadores}. Se necesitan al menos 2 jugadores y que todos estén listos.`;startButton.textContent="LISTO PARA JUGAR";crosshair.style.display="none";gameStarted=false;}else if(s.fase==="countdown"){overlay.classList.remove("hidden");overlayTitle.textContent="¡PREPÁRATE!";overlayCopy.textContent=`La partida comienza en ${s.cuenta_regresiva}…`;startButton.textContent="LISTO";gameStarted=false;}else if(s.fase==="jugando"){overlay.classList.add("hidden");gameStarted=true;if(!cameraInitialized){const me=(s.jugadores||[]).find(p=>Number(p.id)===myId);if(me){const x=worldX(me.x),z=worldZ(me.y);yaw=Math.atan2(x,z);pitch=-0.12;cameraInitialized=true;}}crosshair.style.display="block";showToast("Haz clic en el escenario para mirar con el mouse");}else if(s.fase==="fin"){gameStarted=false;overlay.classList.remove("hidden");overlayTitle.textContent="¡PARTIDA TERMINADA!";const winner=(s.jugadores||[]).find(p=>Number(p.id)===Number(s.ganador));overlayCopy.textContent=winner?`Ganó ${winner.nombre}.`:"La ronda ha terminado.";startButton.textContent="ESPERANDO SIGUIENTE RONDA";crosshair.style.display="none";document.exitPointerLock?.();}}
 if(s.fase==="countdown"){overlayCopy.textContent=`La partida comienza en ${Math.ceil(s.cuenta_regresiva)}…`;}}
function frame(){const dt=Math.min(clock.getDelta(),.05);if(snapshot){const me=remote.get(myId);if(me&&gameStarted){camera.position.set(me.root.position.x,1.62,me.root.position.z);camera.rotation.order="YXZ";camera.rotation.y=yaw;camera.rotation.x=pitch;}for(const p of remote.values())p.ring.visible=(snapshot.jugadores||[]).some(d=>Number(d.id)===p.id&&d.es_lleva);}
 if(token&&performance.now()-lastSync>90&&!syncBusy){lastSync=performance.now();sync(false);}if(toastTimer>0){toastTimer-=dt;if(toastTimer<=0)toast.classList.remove("show");}drawMinimap();renderer.render(scene,camera);}
startButton.addEventListener("click",async()=>{if(!joined){await joinRoom();return;}readySent=true;const ok=await sync(true);if(ok)showToast("Marcaste que estás listo");});
window.addEventListener("keydown",e=>{const k=e.key.toLowerCase();keys.add(k);if(k.startsWith("arrow")||k===" ")e.preventDefault();if(k==="escape"&&gameStarted){document.exitPointerLock?.();}});
window.addEventListener("keyup",e=>keys.delete(e.key.toLowerCase()));
container.addEventListener("click",()=>{if(gameStarted&&document.pointerLockElement!==renderer?.domElement)renderer.domElement.requestPointerLock?.();});
document.addEventListener("mousemove",e=>{if(document.pointerLockElement!==renderer?.domElement||!gameStarted)return;yaw-=e.movementX*.0022;pitch=THREE.MathUtils.clamp(pitch-e.movementY*.0022,-1.25,1.25);});
document.addEventListener("pointerlockchange",()=>{if(gameStarted&&document.pointerLockElement!==renderer?.domElement)crosshair.style.display="none";else if(gameStarted)crosshair.style.display="block";});
window.addEventListener("beforeunload",()=>{if(token)navigator.sendBeacon("/api/sala/salir",new Blob([JSON.stringify({token})],{type:"application/json"}));});
try{initScene();overlayTitle.textContent="LA LLEVA 3D";overlayCopy.textContent="Escribe tu nombre y entra a la sala. Cada jugador verá el mundo desde su propia cámara y tendrá su propio minimapa.";statusLabel.textContent="Sin conexión";startButton.textContent="ENTRAR A LA SALA";}catch(error){console.error(error);overlayTitle.textContent="No se pudo iniciar el juego";overlayCopy.textContent="Comprueba WebGL y tu conexión a Internet para cargar Three.js.";startButton.disabled=true;}
