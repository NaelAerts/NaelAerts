import { THREE, srnd, rr, clamp } from './lib.js';
import { V } from './vox.js';

// --- deterministic value noise
const H = (x, y, z) => { const s = Math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453; return s - Math.floor(s); };
export function noise(x, y, z = 0) {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
  const xf = x - xi, yf = y - yi, zf = z - zi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
  const l = (a, b, t) => a + (b - a) * t;
  const c = (i, j, k) => H(xi + i, yi + j, zi + k);
  return l(l(l(c(0,0,0), c(1,0,0), u), l(c(0,1,0), c(1,1,0), u), v),
           l(l(c(0,0,1), c(1,0,1), u), l(c(0,1,1), c(1,1,1), u), v), w);
}
export const fbm = (x, y, z = 0, o = 3) => { let s = 0, a = .5, f = 1; for (let i = 0; i < o; i++) { s += a * noise(x * f, y * f, z * f); a *= .5; f *= 2; } return s; };

// --- a lattice sphere shell: cubes spread evenly over a sphere (planets, cells, nuclei)
export function shell(vx, c, R, n, fn, scale = 1) {
  const ga = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2, r = Math.sqrt(Math.max(0, 1 - y * y)), th = ga * i;
    const p = V(c.x + R * Math.cos(th) * r, c.y + R * y, c.z + R * Math.sin(th) * r);
    const o = fn(p, i, V(Math.cos(th) * r, y, Math.sin(th) * r));
    if (!o) continue;
    const s = (o.s ?? 1) * scale;
    vx.add(p.x, p.y, p.z, s, s, s, o.c, o.g ?? .4, o.st);
  }
}

// --- voxelise an SDF: keep only the surface cells (trees, insects, blobs)
export function sdfVox(vx, f, bb, step, colorFn) {
  for (let x = bb[0]; x <= bb[3]; x += step)
    for (let y = bb[1]; y <= bb[4]; y += step)
      for (let z = bb[2]; z <= bb[5]; z += step) {
        const d = f(x, y, z);
        if (d > 0) continue;
        if (f(x + step, y, z) < 0 && f(x - step, y, z) < 0 && f(x, y + step, z) < 0 &&
            f(x, y - step, z) < 0 && f(x, y, z + step) < 0 && f(x, y, z - step) < 0) continue;  // interior
        const o = colorFn(x, y, z, d);
        if (!o) continue;
        const s = (o.s ?? .96) * step;
        vx.add(x, y, z, s, s, s, o.c, o.g ?? .4, o.st);
      }
}
export const sdCapsule = (x, y, z, a, b, r) => {
  const pa = [x - a[0], y - a[1], z - a[2]], ba = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
  const h = clamp((pa[0] * ba[0] + pa[1] * ba[1] + pa[2] * ba[2]) / (ba[0] ** 2 + ba[1] ** 2 + ba[2] ** 2), 0, 1);
  return Math.hypot(pa[0] - ba[0] * h, pa[1] - ba[1] * h, pa[2] - ba[2] * h) - r;
};
export const sdEllipsoid = (x, y, z, c, r) => {
  const k = Math.hypot((x - c[0]) / r[0], (y - c[1]) / r[1], (z - c[2]) / r[2]);
  return (k - 1) * Math.min(r[0], r[1], r[2]);
};

// --- a line of cubes (legs, antennae, orbits, gluons)
export function chain(vx, a, b, n, s, c, glow = .4, st) {
  for (let i = 0; i < n; i++) {
    const t = n === 1 ? .5 : i / (n - 1);
    vx.add(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t, s, s, s, c, glow, st);
  }
}
export function ringOf(vx, c, R, n, s, color, glow = .4, tilt = 0, phase = 0, squash = 1) {
  for (let i = 0; i < n; i++) {
    const a = phase + 2 * Math.PI * i / n;
    const x = Math.cos(a) * R, z = Math.sin(a) * R * squash;
    const y = z * Math.sin(tilt), zz = z * Math.cos(tilt);
    vx.add(c.x + x, c.y + y, c.z + zz, s, s, s, color, glow);
  }
}

// --- heightfield columns (terrain)
export function terrain(vx, nx, nz, cell, hFn, colFn, y0 = 0) {
  for (let i = 0; i < nx; i++) for (let j = 0; j < nz; j++) {
    const x = (i - nx / 2 + .5) * cell, z = (j - nz / 2 + .5) * cell;
    const h = hFn(x, z);
    const o = colFn(x, z, h);
    if (!o) continue;
    const top = y0 + h;
    vx.add(x, top - (o.d ?? cell) / 2, z, cell * .98, (o.d ?? cell), cell * .98, o.c, o.g ?? .35, o.st);
  }
}

// --- sky dome: a big gradient box the camera sits inside
export function skydome(scene, top, bot) {
  const g = new THREE.SphereGeometry(1, 16, 10);
  const m = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, depthTest: false,
    uniforms: { cT: { value: new THREE.Color(top) }, cB: { value: new THREE.Color(bot) } },
    vertexShader: 'varying float vy; void main(){ vy = normalize(position).y; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }',
    fragmentShader: 'uniform vec3 cT,cB; varying float vy; void main(){ vec3 c = mix(cB,cT, smoothstep(-.45,.65,vy)); gl_FragColor = vec4(c*c,1.); }',
  });
  const s = new THREE.Mesh(g, m); s.renderOrder = -1; s.frustumCulled = false;
  s.scale.setScalar(900); s.updateMatrixWorld(true);
  scene.add(s); return s;
}
export const starfield = (vx, n, R, cols) => {
  for (let i = 0; i < n; i++) {
    const u = srnd() * 2 - 1, th = srnd() * Math.PI * 2, r = Math.sqrt(1 - u * u);
    const d = R * (.75 + srnd() * .5), s = R * rr(.0022, .0065);
    vx.add(Math.cos(th) * r * d, u * d * .7, Math.sin(th) * r * d, s, s, s,
           cols[Math.floor(srnd() * cols.length)], rr(1.4, 2.6));
  }
};
