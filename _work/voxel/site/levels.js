import { THREE, srnd, rr, clamp, sm } from './lib.js';
import { Vox, V, life, logPos, asmAt, outAt, zoomU, look } from './vox.js';
import { noise, fbm, shell, sdfVox, sdCapsule, sdEllipsoid, chain, ringOf, terrain, skydome, starfield } from './shapes.js';

const PC = new THREE.PerspectiveCamera(50, 16 / 9, .05, 4000);
const cam = () => { const c = PC.clone(); c.near = .05; c.far = 4000; c.updateProjectionMatrix(); return c; };
const mix = (a, b, t) => new THREE.Color(a).lerp(new THREE.Color(b), t);

function rig(sc, meshes, lead, D, start, T, endFrac = .10, lookFn = null, ratio = .02) {
  const c = cam();
  const dist = start.distanceTo(T);
  const end = T.clone().add(start.clone().sub(T).normalize().multiplyScalar(dist * endFrac));
  return (t, extra) => {
    life(meshes, t, asmAt(t, lead), outAt(t, D));
    const u = zoomU(t, lead, D);
    const p = logPos(start, end, u, ratio);
    look(c, p, lookFn ? lookFn(Math.min(u, 1)) : T);
    if (extra) extra(t, u, c);
    return c;
  };
}

// ---------------------------------------------------------------- 1. galaxy
export function galaxy(lead, D) {
  const sc = new THREE.Scene(); skydome(sc, '#141043', '#05060f');
  const vx = new Vox(), T = V(15.5, .6, -4.2);
  starfield(vx, 520, 150, ['#dce8ff', '#ffe2b4', '#ffffff']);
  const CO = ['#ffd9a0', '#ffb27a', '#e87ab0', '#9b7ae8', '#6aa8f0', '#8fe0ff'];
  for (let arm = 0; arm < 4; arm++) for (let i = 0; i < 300; i++) {
    const f = i / 300, r = 2.2 + f * 19 + rr(-.5, .5);
    const a = arm * Math.PI / 2 + r * .40 + rr(-.10, .10);
    const y = rr(-1, 1) * (1.5 - f) * .9;
    const s = rr(.14, .40) * (1.5 - f * .7);
    const c = CO[Math.min(CO.length - 1, Math.floor(f * 5 + srnd() * 1.4))];
    vx.add(Math.cos(a) * r, y, Math.sin(a) * r, s, s, s, c, f < .25 ? rr(1.2, 2.1) : rr(.4, 1.3));
  }
  shell(vx, V(0, 0, 0), 1.9, 190, () => ({ c: '#ffeec0', g: 2.3, s: .46 }));
  for (let i = 0; i < 90; i++) { const a = srnd() * 6.283, r = rr(.4, 2.6); vx.add(Math.cos(a) * r, rr(-.5, .5), Math.sin(a) * r, .3, .3, .3, '#fff3d0', 2.1); }
  vx.add(T.x, T.y, T.z, .62, .62, .62, '#fff6d8', 2.2, .99);          // the star we dive into
  const m = vx.mesh({ spread: 3.2, center: T, sky: '#5a6cff', gnd: '#1a1038', amb: .7, sun: .5, glowK: 1.15, fogC: '#0a0a22', fogD: .0015 });
  sc.add(m);
  const up = rig(sc, [m], lead, D, V(-6, 30, 46), T, .055,
    u => V(0, 0, 0).lerp(T, sm(.15, .85, u)), .03);
  return { sc, update: t => up(t, (t, u, c) => { m.rotation.y = t * .035; }), bloom: [.62, .85, .72], exposure: 1.05 };
}

// ---------------------------------------------------------------- 2. solar system
export function solar(lead, D) {
  const sc = new THREE.Scene(); skydome(sc, '#1b1248', '#06060f');
  const vx = new Vox(), T = V(15.0, 0, 3.4);
  starfield(vx, 320, 140, ['#dbe7ff', '#ffffff', '#ffe6bc']);
  shell(vx, V(0, 0, 0), 3.4, 420, (p, i, n) => ({ c: srnd() < .25 ? '#ffd86a' : '#ffb13a', g: rr(2.0, 2.8), s: rr(.44, .62) }));
  const PL = [[7.0, .55, '#c08a6a'], [10.6, .78, '#d8a860'], [15.0, 1.15, '#3f86d8'], [20.5, .72, '#c4603f']];
  PL.forEach(([R, r, c], k) => {
    ringOf(vx, V(0, 0, 0), R, 150, .085, '#6f7bd0', .55, .06 * (k - 1.5));
    const cen = V(Math.cos(k * 1.9 + .6) * R, 0, Math.sin(k * 1.9 + .6) * R);
    if (k === 2) cen.set(T.x, T.y, T.z);
    shell(vx, cen, r, k === 2 ? 190 : 90, (p) => ({
      c: k === 2 ? (fbm(p.x * 1.6, p.y * 1.6, p.z * 1.6, 2) > .52 ? '#4e9b4a' : '#2f6fd0') : c,
      g: .35, s: k === 2 ? .22 : r * .34,
    }), 1);
    if (k === 2) shell(vx, cen, r * 1.16, 60, () => srnd() < .55 ? ({ c: '#ffffff', g: .5, s: .2 }) : null);
  });
  const m = vx.mesh({ spread: 3.0, center: T, sky: '#6a7cff', gnd: '#160f33', amb: .55, sun: .9, light: V(-1, .25, .2), glowK: 1.1, fogC: '#090a1c', fogD: .002 });
  sc.add(m);
  const up = rig(sc, [m], lead, D, V(-13, 11, 30), T, .07,
    u => V(2.5, 0, 1).lerp(T, sm(.1, .8, u)), .035);
  return { sc, update: t => up(t), bloom: [.58, .8, .78], exposure: 1.0 };
}

// ---------------------------------------------------------------- 3. earth
export function earth(lead, D) {
  const sc = new THREE.Scene(); skydome(sc, '#2a5fb0', '#07102a');
  const vx = new Vox(), R = 9, T = V(0, 0, 0);
  starfield(vx, 220, 160, ['#eef4ff', '#ffffff']);
  // the dive point: a coast on the near face
  const dir = V(.26, .30, .92).normalize(); T.copy(dir).multiplyScalar(R);
  shell(vx, V(0, 0, 0), R, 3000, (p, i, n) => {
    const land = fbm(n.x * 2.1 + 3, n.y * 2.1, n.z * 2.1, 4);
    const near = n.dot(dir);
    const isLand = land > .505 || (near > .93 && land > .47);
    const ice = Math.abs(n.y) > .82;
    let c = ice ? '#eaf3ff' : isLand ? (land > .60 ? '#4f8f3f' : '#79a84e') : (land > .49 ? '#2f74c9' : '#1f5aa8');
    if (!ice && isLand && land > .505 && land < .525) c = '#d8c38a';
    return { c, g: .3, s: .40 };
  });
  vx.add(T.x, T.y, T.z, .40, .40, .40, '#ffd9a0', 1.3, .99);
  const cl = new Vox();
  for (let i = 0; i < 2600; i++) {
    const u = srnd() * 2 - 1, th = srnd() * 6.283, r = Math.sqrt(1 - u * u);
    const n = V(Math.cos(th) * r, u, Math.sin(th) * r);
    if (fbm(n.x * 3.1 + 11, n.y * 3.1, n.z * 3.1, 3) < .575) continue;
    const p2 = n.clone().multiplyScalar(R * 1.045 + srnd() * .12);
    cl.add(p2.x, p2.y, p2.z, .30, .22, .30, '#ffffff', .4);
  }
  const mc = cl.mesh({ spread: 2.4, center: T, sky: '#ffffff', gnd: '#9fc0e8', amb: .9, sun: .8, opacity: .45, glowK: .5 });
  sc.add(mc);
  const m = vx.mesh({ spread: 2.4, center: T, sky: '#8fc8ff', gnd: '#20406a', amb: .62, sun: 1.15, light: V(.35, .5, .9), glowK: .9, fogC: '#0c1a38', fogD: .004 });
  sc.add(m);
  const up = rig(sc, [m, mc], lead, D, T.clone().add(dir.clone().multiplyScalar(30)).add(V(-7, 8, 0)), T, .075,
    u => V(0, 0, 0).lerp(T, sm(.0, .7, u)), .03);
  return { sc, update: t => up(t, () => { mc.rotation.y = 0; }), bloom: [.42, .8, .85], exposure: 1.0 };
}

// ---------------------------------------------------------------- 4. coastline
export function coast(lead, D) {
  const sc = new THREE.Scene(); skydome(sc, '#8fd0ff', '#dff0ff');
  const vx = new Vox(), T = V(3.2, 2.9, -2.0);
  const H = (x, z) => {
    const coast = (x * .55 + z * .83) * .34;                       // the shoreline runs diagonally
    const b = coast + fbm(x * .05 + 7, z * .05 + 2, 0, 4) * 5.4 - 3.4;
    const cliff = Math.max(0, 1 - Math.hypot(x - 3.2, z + 2.0) / 7.5) ** 1.7 * 6.0;
    return b + cliff;
  };
  terrain(vx, 78, 78, .86, (x, z) => Math.max(0, H(x, z)) * .5, (x, z, h) => {
    const d = H(x, z);
    if (d <= .05) return { c: d < -1.6 ? '#1b56a6' : (d < -.6 ? '#2470c4' : '#3c9ad8'), g: .3, d: .5 };
    if (d < .75) return { c: srnd() < .3 ? '#efe0b4' : '#e3d2a0', g: .3, d: .8 };
    const onCliff = Math.hypot(x - 3.2, z + 2.0) < 6.2 && d > 2.4;
    if (onCliff) return { c: srnd() < .35 ? '#8e8577' : '#9d9488', g: .3, d: 1.1 };
    return { c: srnd() < .3 ? '#74a349' : '#5e8c3c', g: .3, d: .9 };
  });
  for (let i = 0; i < 46; i++) { const x = rr(-30, 30), z = rr(-30, 30), h = Math.max(0, H(x, z)) * .5; if (h < .6) continue; const s = rr(.35, .7); vx.add(x, h + s, z, s, s * 1.5, s, srnd() < .5 ? '#3f6f33' : '#4f8040', .3); }
  vx.add(T.x, T.y, T.z, .5, .5, .5, '#ffcf7a', 1.15, .99);
  const m = vx.mesh({ spread: 2.0, center: T, sky: '#bfe4ff', gnd: '#4a5a3a', amb: .66, sun: 1.2, light: V(-.45, .78, .42), fogC: '#cfe8ff', fogD: .0075 });
  sc.add(m);
  const up = rig(sc, [m], lead, D, V(-16, 24, 30), T, .085, null, .03);
  return { sc, update: t => up(t), bloom: [.3, .75, .9], exposure: 1.0 };
}

// ---------------------------------------------------------------- 5. the oak on the cliff
export function tree(lead, D) {
  const sc = new THREE.Scene(); skydome(sc, '#7ec8ff', '#e8f4ff');
  const vx = new Vox(), T = V(1.55, 7.35, 1.25);
  terrain(vx, 54, 54, .62, (x, z) => {
    const r = Math.hypot(x, z);
    return 2.6 - Math.max(0, (r - 7.5)) * 1.5 + fbm(x * .22 + 4, z * .22, 0, 3) * .9;
  }, (x, z, h) => {
    const r = Math.hypot(x, z);
    if (h < -4) return null;
    if (r > 8.6) return { c: srnd() < .4 ? '#6f9b45' : '#5e8c3c', g: .3, d: .9 };
    return (h > 2.75) ? { c: srnd() < .35 ? '#7a5a3a' : '#6b4f31', g: .3, d: .8 }
                      : { c: srnd() < .45 ? '#9a9080' : '#857c6e', g: .3, d: 1.2 };
  });
  const trunk = (x, y, z) => Math.min(
    sdCapsule(x, y, z, [0, 3.0, 0], [.15, 5.4, .1], .42),
    sdCapsule(x, y, z, [.1, 5.0, .05], [1.5, 6.6, 1.1], .22),
    sdCapsule(x, y, z, [.1, 5.0, .05], [-1.6, 6.5, -.7], .22),
    sdCapsule(x, y, z, [.1, 5.2, .05], [.2, 6.9, -1.5], .2));
  sdfVox(vx, trunk, [-2.4, 2.6, -2.4, 2.4, 7.2, 2.4], .30, () => ({ c: srnd() < .4 ? '#7b5736' : '#6a4a2e', g: .3 }));
  const can = (x, y, z) => Math.min(
    sdEllipsoid(x, y, z, [0, 7.6, 0], [2.9, 2.0, 2.7]),
    sdEllipsoid(x, y, z, [1.7, 7.0, 1.2], [1.7, 1.3, 1.6]),
    sdEllipsoid(x, y, z, [-1.8, 7.1, -.9], [1.6, 1.25, 1.5]),
    sdEllipsoid(x, y, z, [.3, 8.6, -.7], [1.7, 1.2, 1.5]));
  sdfVox(vx, can, [-4.4, 5.4, -4.4, 4.4, 10.2, 4.4], .30, (x, y, z) => {
    const n = fbm(x * .9 + 2, y * .9, z * .9, 3);
    const c = n > .60 ? '#e08a3c' : n > .55 ? '#f0b05a' : (srnd() < .4 ? '#4e8f3e' : '#3f7a33');
    return { c, g: .3, s: .94 };
  });
  vx.add(T.x, T.y, T.z, .34, .34, .34, '#ffe08a', 1.2, .99);
  const m = vx.mesh({ spread: 1.5, center: T, sky: '#b6e2ff', gnd: '#4b5a36', amb: .68, sun: 1.2, light: V(-.5, .8, .35), fogC: '#d6ecff', fogD: .011 });
  sc.add(m);
  const up = rig(sc, [m], lead, D, V(-11, 13, 19), T, .10,
    u => V(0, 6.2, 0).lerp(T, sm(.1, .8, u)), .03);
  return { sc, update: t => up(t), bloom: [.3, .75, .9], exposure: 1.0 };
}

// ---------------------------------------------------------------- 6. grasshopper on the leaf
export function hopper(lead, D) {
  const sc = new THREE.Scene(); skydome(sc, '#9ad8ff', '#dff2e8');
  const vx = new Vox(), T = V(2.1, .62, 1.0);
  const LH = (x, z) => -.12 * (x * x + z * z) * .06 + Math.sin(x * .5) * .12;
  terrain(vx, 56, 56, .42, (x, z) => LH(x, z), (x, z, h) => {
    const r = Math.hypot(x / 6.2, z / 4.2);
    if (r > 1) return null;
    const vein = Math.abs(Math.sin(z * .9 - x * .18)) < .09 || Math.abs(x) < .18;
    return { c: vein ? '#6fae55' : (srnd() < .35 ? '#2f6b34' : '#35793a'), g: .3, d: .32 };
  });
  const body = (x, y, z) => Math.min(
    sdEllipsoid(x, y, z, [-1.2, .86, -.1], [1.35, .46, .42]),
    sdEllipsoid(x, y, z, [.25, .96, -.08], [.46, .40, .38]));
  sdfVox(vx, body, [-2.8, .3, -.8, 1.0, 1.6, .7], .17, (x, y, z) =>
    ({ c: y > 1.0 ? '#c8e24a' : (srnd() < .3 ? '#9fc63a' : '#b4d842'), g: .3 }));
  vx.add(.52, 1.12, .24, .17, .17, .17, '#2a2a1c', .4); vx.add(.52, 1.12, -.36, .17, .17, .17, '#2a2a1c', .4);
  chain(vx, V(.5, 1.18, .12), V(1.5, 1.75, .5), 7, .09, '#9fc63a', .35);
  chain(vx, V(.5, 1.18, -.26), V(1.5, 1.8, -.6), 7, .09, '#9fc63a', .35);
  [[-.1, .2], [-.75, .26], [-1.55, .3]].forEach(([bx, w], i) => {
    [1, -1].forEach(s => {
      const knee = V(bx - .25, 1.45 - i * .08, s * (w + .85));
      chain(vx, V(bx, .78, s * .3), knee, 5, .12, '#a8cf3e', .35);
      chain(vx, knee, V(bx + .55, .12, s * (w + .62)), 6, .105, '#8fb832', .35);
    });
  });
  sdfVox(vx, (x, y, z) => sdEllipsoid(x, y, z, [-1.1, 1.18, 0], [1.15, .18, .5]), [-2.4, .9, -.7, .2, 1.5, .7], .17,
    () => ({ c: srnd() < .3 ? '#d8ec66' : '#c2dd4e', g: .3 }));
  vx.add(T.x, T.y, T.z, .22, .22, .22, '#fff0a0', 1.15, .99);
  const m = vx.mesh({ spread: 1.2, center: T, sky: '#cdeaff', gnd: '#2f4a2a', amb: .70, sun: 1.15, light: V(-.4, .85, .4), fogC: '#dff0ff', fogD: .02 });
  sc.add(m);
  const up = rig(sc, [m], lead, D, V(-4.6, 4.2, 7.6), T, .11,
    u => V(-.6, 1.0, 0).lerp(T, sm(.2, .9, u)), .03);
  return { sc, update: t => up(t), bloom: [.3, .75, .88], exposure: 1.0 };
}

// ---------------------------------------------------------------- 7. leaf cells
export function cells(lead, D) {
  const sc = new THREE.Scene(); skydome(sc, '#1f7f82', '#06363f');
  const vx = new Vox(), T = V(1.4, .2, .8);
  for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) {
    const c = V(i * 6.2 + rr(-.4, .4), rr(-1.2, 1.2) - (i * i + j * j) * .5, j * 6.2 + rr(-.4, .4));
    const R = 2.5 + rr(-.25, .25);
    shell(vx, c, R, 300, () => ({ c: srnd() < .22 ? '#8ff0d2' : '#3fb99f', g: .5, s: .34 }));
    const nc = (i === 0 && j === 0) ? V(T.x, T.y, T.z) : c.clone().add(V(rr(-.5, .5), rr(-.4, .4), rr(-.5, .5)));
    shell(vx, nc, R * .40, 150, () => ({ c: srnd() < .3 ? '#b07ae8' : '#8a5cd0', g: .75, s: .24 }));
    for (let k = 0; k < 16; k++) { const a = srnd() * 6.283, b = srnd() * 3.14, r = rr(1.2, R * .82); vx.add(c.x + Math.sin(b) * Math.cos(a) * r, c.y + Math.cos(b) * r, c.z + Math.sin(b) * Math.sin(a) * r, .22, .22, .22, srnd() < .5 ? '#2a9b84' : '#5fd9b8', .5); }
  }
  vx.add(T.x, T.y, T.z, .26, .26, .26, '#e8c8ff', 1.25, .99);
  const m = vx.mesh({ spread: 1.6, center: T, sky: '#6ff0d8', gnd: '#0a3a44', amb: .8, sun: .75, light: V(-.3, .8, .5), glowK: 1.0, fogC: '#0d4a52', fogD: .018 });
  sc.add(m);
  const up = rig(sc, [m], lead, D, V(-7.5, 7.0, 13.0), T, .095, null, .03);
  return { sc, update: t => up(t), bloom: [.5, .8, .78], exposure: 1.05 };
}

// ---------------------------------------------------------------- 8. DNA
export function dna(lead, D) {
  const sc = new THREE.Scene(); skydome(sc, '#4a2a8c', '#160a30');
  const vx = new Vox(), T = V(0, 2.6, 1.35);
  const R = 1.9, PITCH = 5.2, N = 150;
  for (let i = 0; i < N; i++) {
    const y = -9 + i * .14, a = y * (6.283 / PITCH);
    for (const s of [0, Math.PI]) {
      const x = Math.cos(a + s) * R, z = Math.sin(a + s) * R;
      vx.add(x, y, z, .36, .36, .36, s ? '#ff7ac0' : '#7ad0ff', .8);
    }
    if (i % 4 === 0) {
      const A = V(Math.cos(a) * R, y, Math.sin(a) * R), B = V(Math.cos(a + Math.PI) * R, y, Math.sin(a + Math.PI) * R);
      const pal = ['#ffd45e', '#8affc0', '#ff9a6a', '#c0a0ff'];
      chain(vx, A, B, 7, .26, pal[(i / 4) % 4], .55);
    }
  }
  for (let i = 0; i < 160; i++) { const a = srnd() * 6.283, r = rr(3.2, 11), y = rr(-9, 11); vx.add(Math.cos(a) * r, y, Math.sin(a) * r, rr(.12, .22), 0, 0, srnd() < .5 ? '#b58aff' : '#ff9ad8', rr(1.2, 2.2)); }
  vx.add(T.x, T.y, T.z, .3, .3, .3, '#fff0b0', 1.4, .99);
  const m = vx.mesh({ spread: 1.8, center: T, sky: '#c89aff', gnd: '#2a1050', amb: .78, sun: .7, light: V(-.4, .6, .7), glowK: 1.15, fogC: '#1e0e40', fogD: .012 });
  sc.add(m);
  const up = rig(sc, [m], lead, D, V(-9.5, 7.5, 14.0), T, .09,
    u => V(0, 1.2, 0).lerp(T, sm(.1, .8, u)), .03);
  return { sc, update: t => up(t, (t2) => { m.rotation.y = t2 * .22; }), bloom: [.6, .85, .72], exposure: 1.05 };
}

// ---------------------------------------------------------------- 9. atom (ending)
export function atom(lead, D) {
  const sc = new THREE.Scene(); skydome(sc, '#9c2a7a', '#2a0a2e');
  const vx = new Vox(), T = V(0, 0, 0);
  const NU = [];
  for (let i = 0; i < 12; i++) {
    const a = srnd() * 6.283, b = srnd() * 3.14, r = rr(.0, 1.25);
    const c = V(Math.sin(b) * Math.cos(a) * r, Math.cos(b) * r, Math.sin(b) * Math.sin(a) * r);
    NU.push(c);
    shell(vx, c, .62, 60, () => ({ c: i % 2 ? '#ff6a8a' : '#ffb45e', g: .9, s: .20 }));
  }
  for (let k = 0; k < 3; k++) ringOf(vx, V(0, 0, 0), 5.2 + k * 2.1, 170, .085, '#ffd1f0', 1.5, (k - 1) * .85, k * .7);
  const EL = [];
  for (let k = 0; k < 3; k++) {
    const e = new Vox(); e.add(0, 0, 0, .42, .42, .42, '#9ff0ff', 2.6, .2);
    const em = e.mesh({ spread: 1, center: T, sky: '#ffd0f4', gnd: '#3a0a30', amb: .9, sun: .4, glowK: 1.4 });
    sc.add(em); EL.push({ m: em, R: 5.2 + k * 2.1, tilt: (k - 1) * .85, ph: k * 2.1 });
  }
  const m = vx.mesh({ spread: 2.2, center: T, sky: '#ffbdf0', gnd: '#3a0a30', amb: .85, sun: .6, light: V(-.3, .7, .6), glowK: 1.25, fogC: '#2e0a36', fogD: .01 });
  sc.add(m);
  const c = cam();
  return {
    sc, bloom: [.7, .9, .7], exposure: 1.1,
    update: t => {
      life([m, ...EL.map(e => e.m)], t, asmAt(t, lead), 0);
      EL.forEach((e, k) => {
        const a = e.ph + t * (1.5 - k * .28);
        const x = Math.cos(a) * e.R, z = Math.sin(a) * e.R;
        e.m.position.set(x, z * Math.sin(e.tilt), z * Math.cos(e.tilt));
      });
      m.rotation.y = t * .25;
      const u = zoomU(t, lead, D);
      const p = logPos(V(-9, 7.5, 16), V(-1.1, .9, 3.0), Math.min(u, 1.0), .02);
      const k = sm(D - 1.9, D + .6, t);                     // final crane up and out
      const endP = V(-3.0, 7.2, 12.5);
      look(c, p.clone().lerp(endP, k * k * (3 - 2 * k)), V(0, 0, 0));
      return c;
    },
  };
}
