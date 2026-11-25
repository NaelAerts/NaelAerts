import * as THREE from 'three';
export { THREE };
export const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
export const sm = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export const GLOW = 2.0;
// deterministic rng so every frame of the render agrees
let _s = 1337;
export const seed = n => { _s = (n >>> 0) || 1; };
export const srnd = () => { _s = (_s * 1664525 + 1013904223) % 4294967296; return _s / 4294967296; };
export const rr = (a, b) => a + (b - a) * srnd();
export const pick = a => a[Math.floor(srnd() * a.length) % a.length];
export const rnd = () => srnd();
