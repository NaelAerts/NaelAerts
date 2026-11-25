import { THREE, rnd, clamp, sm, GLOW } from './lib.js';
export const V = (x, y, z) => new THREE.Vector3(x, y, z);
const col = new THREE.Color();

const VS = `
attribute vec3 iPos, iScl, iCol; attribute float iGlow; attribute vec4 iRnd;
uniform float uT,uAsm,uOut,uSpread,uPulse,uWaveF,uWaveS,uGlowW,uCol; uniform vec3 uCenter,uWaveD;
varying vec3 vN,vW,vCol,vLN; varying vec2 vUv; varying float vGlow;
mat3 rotA(vec3 a,float g){a=normalize(a);float s=sin(g),c=cos(g),o=1.-c;
 return mat3(o*a.x*a.x+c,o*a.x*a.y+a.z*s,o*a.z*a.x-a.y*s, o*a.x*a.y-a.z*s,o*a.y*a.y+c,o*a.y*a.z+a.x*s, o*a.z*a.x+a.y*s,o*a.y*a.z-a.x*s,o*a.z*a.z+c);}
void main(){
 float st=iRnd.w;
 float ai=clamp((uAsm-st*.45)/.55,0.,1.);ai=ai*ai*(3.-2.*ai);
 float oi=clamp((uOut-st*.45)/.55,0.,1.);oi=oi*oi*(3.-2.*oi);
 float k=(1.-ai)+oi;
 vec3 rd=normalize(iRnd.xyz*2.-1.+vec3(1e-3));
 vec3 rc=iPos-uCenter;vec3 radial=rc/(length(rc)+1e-3);
 vec3 off=(rd*(1.-ai)*1.6+(radial*1.6+rd*.9)*oi)*uSpread*(k*k*.75+k*.25);
 float wv=sin(dot(iPos,uWaveD)*uWaveF-uT*uWaveS+st*2.)*.5+.5;
 vec3 sc=iScl*mix(.15,1.,clamp(1.-k,0.,1.))*(1.+uPulse*(wv-.5));
 float colH=0.;
 if(uCol>.5){float d=length(iPos.xz);float T=uT*2.2+1.5;colH=.25+max(0.,sin(d*1.1-T*2.2)*1.1+sin(iPos.x*.45+T*.6)*sin(iPos.z*.4-T*.45)*1.1+.45)*uCol;sc.y*=colH;}
 mat3 R=rotA(rd,k*3.6);
 vec3 lp=R*(position*sc);
 vec4 w=modelMatrix*vec4(lp+iPos+off+vec3(0.,colH*.5,0.),1.);
 vN=normalize(mat3(modelMatrix)*(R*normal));vLN=normal;vW=w.xyz;vUv=uv;vCol=iCol;
 vGlow=iGlow*(1.+uGlowW*(wv-.5)*2.)+k*.25+(uCol>.5?smoothstep(1.9,2.6,colH)*.9:0.);
 gl_Position=projectionMatrix*viewMatrix*w;}`;
const FS = `
uniform vec3 uL,uFogC,uSky,uGnd;uniform float uAmb,uFogD,uSun,uSpec,uSat,uGlowK,uOp;
varying vec3 vN,vW,vCol,vLN;varying vec2 vUv;varying float vGlow;
float hh(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
void main(){vec2 e2=min(vUv,1.-vUv);float e=min(e2.x,e2.y);
 vec3 N=normalize(vN);vec3 V=normalize(cameraPosition-vW);
 float lum=dot(vCol,vec3(.299,.587,.114));vec3 alb=mix(vec3(lum),vCol,uSat);
 float bev=mix(.7,1.,smoothstep(.0,.11,e));
 float face=vLN.y>.5?1.:(vLN.y<-.5?.62:(abs(vLN.x)>.5?.86:.78));
 float grain=.94+.06*hh(floor(vUv*14.)+vCol.xy*31.);
 float wrap=max((dot(N,uL)+.25)/1.25,0.);
 vec3 hemi=mix(uGnd,uSky,N.y*.5+.5);
 vec3 c=alb*(hemi*uAmb+vec3(1.,.96,.9)*wrap*uSun)*bev*face*grain;
 c+=vec3(1.)*pow(max(dot(reflect(-uL,N),V),0.),20.)*uSpec*bev;
 c+=alb*pow(1.-max(dot(N,V),0.),3.)*.3;
 float em=max(vGlow-1.,0.);c+=vCol*em*uGlowK*mix(.6,1.,smoothstep(.06,.16,e));
 float d=length(vW-cameraPosition);c=mix(c,uFogC,1.-exp(-d*uFogD));
 gl_FragColor=vec4(c,uOp);}`;

export class Vox {
  constructor() { this.p = []; this.s = []; this.c = []; this.g = []; this.r = []; }
  add(x, y, z, sx, sy, sz, color, glow = .5, st) {
    this.p.push(x, y, z); this.s.push(sx, sy ?? sx, sz ?? sx);
    if (Array.isArray(color)) this.c.push(...color); else { col.set(color); this.c.push(col.r, col.g, col.b); }
    this.g.push(glow); this.r.push(rnd(), rnd(), rnd(), st ?? rnd() * .98); return this;
  }
  get n() { return this.g.length; }
  mesh(o = {}) {
    const box = new THREE.BoxGeometry(1, 1, 1); const g = new THREE.InstancedBufferGeometry();
    g.index = box.index; g.setAttribute('position', box.attributes.position); g.setAttribute('normal', box.attributes.normal); g.setAttribute('uv', box.attributes.uv);
    const A = (a, k) => new THREE.InstancedBufferAttribute(new Float32Array(a), k);
    g.setAttribute('iPos', A(this.p, 3)); g.setAttribute('iScl', A(this.s, 3)); g.setAttribute('iCol', A(this.c, 3)); g.setAttribute('iGlow', A(this.g, 1)); g.setAttribute('iRnd', A(this.r, 4));
    g.instanceCount = this.n;
    const u = {
      uT: { value: 0 }, uAsm: { value: 1 }, uOut: { value: 0 }, uSpread: { value: o.spread ?? 1 }, uPulse: { value: o.pulse ?? .2 }, uWaveF: { value: o.waveF ?? 2 }, uWaveS: { value: o.waveS ?? 3 }, uGlowW: { value: o.glowW ?? .4 }, uCol: { value: o.col ?? 0 },
      uCenter: { value: o.center ?? V(0, 0, 0) }, uWaveD: { value: (o.waveD ?? V(.7, .3, .6)).clone().normalize() },
      uL: { value: (o.light ?? V(-.5, .8, .4)).clone().normalize() }, uFogC: { value: new THREE.Color(o.fogC ?? 0x000000) }, uAmb: { value: o.amb ?? .55 }, uFogD: { value: o.fogD ?? 0 }, uSun: { value: o.sun ?? 1.0 }, uSpec: { value: o.specM ?? .04 }, uSat: { value: o.sat ?? 1.08 }, uOp: { value: o.opacity ?? 1 }, uGlowK: { value: o.glowK ?? 1.0 },
      uSky: { value: new THREE.Color(o.sky ?? '#8fa6c0') }, uGnd: { value: new THREE.Color(o.gnd ?? '#3a3128') },
    };
    const m = new THREE.Mesh(g, new THREE.ShaderMaterial({ uniforms: u, vertexShader: VS, fragmentShader: FS, transparent: (o.opacity ?? 1) < 1, depthWrite: (o.opacity ?? 1) >= 1 }));
    m.frustumCulled = false; m.u = u; return m;
  }
}
export function life(meshes, t, asm, out) { for (const m of meshes) { m.u.uT.value = t; m.u.uAsm.value = asm; m.u.uOut.value = out; } }
export function logPos(start, end, u, ratio) { const uu = Math.max(0, u); const e = 1 - Math.pow(ratio, uu); return start.clone().lerp(end, e); }
export const asmAt = (t, lead) => sm(lead - .45, lead + .05, t);
export const outAt = (t, D) => sm(D - .20, D + .16, t);
export function zoomU(t, lead, D) {
  const t0 = lead - .45; const x = Math.max(0, (t - t0) / (D - t0));
  const U = y => (1 - Math.exp(-12 * y)) / 12 + .25 * y + .6667 * Math.pow(y, 4);
  if (x <= 1) return U(x);
  const v1 = Math.exp(-12) + .25 + 2.6668; return U(1) + v1 * (x - 1);
}
export function look(cam, pos, target) { cam.position.copy(pos); cam.lookAt(target); }
