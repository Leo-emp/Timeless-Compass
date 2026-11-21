// ============================================================================================================
// TOWN KIT — building blocks for BUSY BIRD'S-EYE scenes (owner 2026-11-21: "not good enough" next to the reference;
// wide shots must be packed with detail like the reference's Nara / Heian-kyo / battlefield frames).
// Everything is drawn in a 3/4 high view: a top face (roof / ground), one front face, thin outlines, flat colours
// with one shade. These are SHARED PARTS ONLY; every video composes its own places fresh (r17).
// Coordinates: (x, y) = the point where the object meets the ground; s = scale (1 = a house ~110 px wide).
// ============================================================================================================
import { OUT, rng } from './core';

const LW = 2.2;                                   // thin line weight for distant detail (the reference look)
const f = (n: number) => n.toFixed(1);
const poly = (pts: number[][], fill: string, w = LW, extra = '') =>
  `<path d="M${pts.map((p) => `${f(p[0])} ${f(p[1])}`).join(' L')} Z" fill="${fill}" stroke="${OUT}" stroke-width="${w}" stroke-linejoin="round"${extra}/>`;
const line = (x1: number, y1: number, x2: number, y2: number, col = OUT, w = 1.4, op = 1) =>
  `<path d="M${f(x1)} ${f(y1)} L${f(x2)} ${f(y2)}" stroke="${col}" stroke-width="${w}" stroke-linecap="round" opacity="${op}"/>`;

export const WALLS = ['#f2ead8', '#ebe0c8', '#e6d8bc', '#f4ecdc', '#e2d2b2'];
export const ROOFS = ['#b5674a', '#a85a3e', '#c07a52', '#9e5236', '#b86e4e'];

/** A Greek house: whitewashed walls, a terracotta tiled roof (two slopes, tile rows), a door, a small window.
 *  w = width, d = depth (how far the roof reaches back), h = wall height (all at scale 1). */
export function house(x: number, y: number, s = 1, seed = 0, o: { w?: number; d?: number; h?: number; flat?: boolean; court?: boolean } = {}): string {
  const R = rng(seed + 11), w = (o.w ?? 90 + R() * 40) * s, d = (o.d ?? 50 + R() * 20) * s, h = (o.h ?? 34 + R() * 12) * s;
  const wall = WALLS[seed % WALLS.length], roof = ROOFS[(seed * 3) % ROOFS.length];
  const x0 = x - w / 2, x1 = x + w / 2, yb = y, yt = y - h;
  let g = poly([[x0, yb], [x1, yb], [x1, yt], [x0, yt]], wall);                                          // front wall
  g += poly([[x1, yb], [x1 + d * 0.35, yb - d * 0.5], [x1 + d * 0.35, yt - d * 0.5], [x1, yt]], shadeOf(wall)); // side wall
  if (o.flat) {
    g += poly([[x0, yt], [x1, yt], [x1 + d * 0.35, yt - d * 0.5], [x0 + d * 0.35, yt - d * 0.5]], '#d9c9a6');   // flat roof terrace
  } else {
    const ridgeY = yt - d * 0.5 - 10 * s;
    g += poly([[x0 - 4 * s, yt + 2 * s], [x1 + 4 * s, yt + 2 * s], [x1 + d * 0.35, ridgeY], [x0 + d * 0.35, ridgeY]], roof);   // roof slope
    for (let r = 1; r < 4; r++) { const k = r / 4; g += line(x0 - 4 * s + d * 0.35 * k, yt + 2 * s - (yt - ridgeY + 2 * s) * k, x1 + 4 * s + (d * 0.35 - 4 * s) * k, yt + 2 * s - (yt - ridgeY + 2 * s) * k, '#7a3a24', 1.1, 0.8); }  // tile rows
    g += poly([[x1 + 4 * s, yt + 2 * s], [x1 + d * 0.35, ridgeY], [x1 + d * 0.35 + 6 * s, yt - d * 0.5 + 4 * s]], shadeOf(roof), LW);
  }
  g += poly([[x - 7 * s, yb], [x + 7 * s, yb], [x + 7 * s, yb - 18 * s], [x - 7 * s, yb - 18 * s]], '#6a4428', 1.6);   // door
  if (R() > 0.4) g += poly([[x0 + 12 * s, yt + 10 * s], [x0 + 22 * s, yt + 10 * s], [x0 + 22 * s, yt + 18 * s], [x0 + 12 * s, yt + 18 * s]], '#3a2a1e', 1.2);
  if (o.court) g += poly([[x1 + 6 * s, yb], [x1 + 46 * s, yb], [x1 + 46 * s, yb - 14 * s], [x1 + 6 * s, yb - 14 * s]], shadeOf(wall), 1.6);   // courtyard wall
  return g;
}
export function shadeOf(hex: string, k = 0.82): string {
  const n = parseInt(hex.slice(1), 16), r = Math.round(((n >> 16) & 255) * k), g = Math.round(((n >> 8) & 255) * k), b = Math.round((n & 255) * k);
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}
/** A Doric temple seen from high up: stepped base, a ring of columns, a painted pediment, a tiled roof. */
export function templeTop(x: number, y: number, s = 1, o: { roof?: string; frieze?: string; burning?: number; t?: number } = {}): string {
  const w = 260 * s, d = 120 * s, h = 70 * s, x0 = x - w / 2, x1 = x + w / 2;
  let g = poly([[x0 - 14 * s, y], [x1 + 14 * s, y], [x1 + 14 * s + d * 0.35, y - d * 0.5], [x0 - 14 * s + d * 0.35, y - d * 0.5]], '#e2d6ba');   // stylobate
  g += poly([[x0 - 14 * s, y], [x1 + 14 * s, y], [x1 + 14 * s, y + 8 * s], [x0 - 14 * s, y + 8 * s]], '#cbbd9c');
  for (let i = 0; i < 8; i++) { const cx = x0 + 10 * s + i * (w - 20 * s) / 7; g += poly([[cx - 6 * s, y], [cx + 6 * s, y], [cx + 5 * s, y - h], [cx - 5 * s, y - h]], '#f3ebd6', 1.4); }
  g += poly([[x0, y - h], [x1, y - h], [x1, y - h - 12 * s], [x0, y - h - 12 * s]], o.frieze ?? '#2f5a8a', 1.6);
  const ry = y - h - 12 * s;
  g += poly([[x0 - 6 * s, ry], [x1 + 6 * s, ry], [x1 + d * 0.35, ry - d * 0.5 - 18 * s], [x0 + d * 0.35, ry - d * 0.5 - 18 * s]], o.roof ?? '#b5452c');
  for (let r = 1; r < 6; r++) { const k = r / 6; g += line(x0 - 6 * s + d * 0.35 * k, ry - (d * 0.5 + 18 * s) * k, x1 + 6 * s + (d * 0.35 - 6 * s) * k, ry - (d * 0.5 + 18 * s) * k, '#7a2a1a', 1.1, 0.8); }
  g += poly([[x0 - 6 * s, ry], [x0 + 10 * s, ry - 22 * s], [x0 + 26 * s, ry]], '#e8dcc0', 1.4);                            // pediment end
  if (o.burning) {
    const t = o.t ?? 0;
    for (let q = 0; q < 10; q++) { const fx = x0 + q * w / 9, fh = (40 + 40 * Math.abs(Math.sin(t * 5 + q * 1.7))) * s * o.burning; g += `<path d="M${f(fx - 12 * s)} ${f(ry - 10 * s)} Q${f(fx)} ${f(ry - fh * 0.6)} ${f(fx + 4 * Math.sin(t * 6 + q))} ${f(ry - fh)} Q${f(fx + 8 * s)} ${f(ry - fh * 0.5)} ${f(fx + 12 * s)} ${f(ry - 10 * s)} Z" fill="${q % 3 ? '#ff8a2a' : '#ffd25a'}" stroke="#c0451a" stroke-width="1.4"/>`; }
  }
  return g;
}
/** A tree from a high view. kind olive (silvery round crown), cypress (dark spire), pine (umbrella), shrub. */
export function tree(x: number, y: number, s = 1, kind: 'olive' | 'cypress' | 'pine' | 'shrub' = 'olive', seed = 0): string {
  const R = rng(seed + 5), sh = `<ellipse cx="${f(x + 6 * s)}" cy="${f(y)}" rx="${f(16 * s)}" ry="${f(5 * s)}" fill="rgba(0,0,0,.14)"/>`;
  if (kind === 'cypress') return sh + poly([[x, y - 70 * s], [x + 10 * s, y - 30 * s], [x + 8 * s, y - 2 * s], [x - 8 * s, y - 2 * s], [x - 10 * s, y - 30 * s]], '#3e5a34');
  if (kind === 'pine') return sh + line(x, y, x, y - 26 * s, '#5a3a24', 4 * s) + `<ellipse cx="${f(x)}" cy="${f(y - 32 * s)}" rx="${f(28 * s)}" ry="${f(11 * s)}" fill="#4b6a3a" stroke="${OUT}" stroke-width="${LW}"/>`;
  const col = kind === 'olive' ? ['#8a9a62', '#7f9058', '#94a46c'][seed % 3] : '#6f8a44';
  const r = (kind === 'olive' ? 15 : 9) * s * (0.85 + R() * 0.3);
  return sh + line(x, y, x - 2 * s, y - r, '#6a4a2a', 3 * s) +
    `<path d="M${f(x - r)} ${f(y - r)} q${f(-2 * s)} ${f(-r * 0.9)} ${f(r * 0.7)} ${f(-r)} q${f(r * 0.6)} ${f(-r * 0.5)} ${f(r * 1.1)} ${f(r * 0.3)} q${f(r * 0.4)} ${f(r * 0.8)} ${f(-r * 0.4)} ${f(r * 1.2)} Z" fill="${col}" stroke="${OUT}" stroke-width="${LW}"/>`;
}
/** A field patch with furrows (or a vineyard with dotted rows). */
export function field(pts: number[][], col: string, rows = 6, vine = false): string {
  let g = poly(pts, col, 1.6);
  const [a, b, c, d] = pts;
  for (let r = 1; r < rows; r++) {
    const k = r / rows, p = [a[0] + (d[0] - a[0]) * k, a[1] + (d[1] - a[1]) * k], q = [b[0] + (c[0] - b[0]) * k, b[1] + (c[1] - b[1]) * k];
    g += vine ? `<path d="M${f(p[0])} ${f(p[1])} L${f(q[0])} ${f(q[1])}" stroke="#4b6a3a" stroke-width="4" stroke-dasharray="3 7" stroke-linecap="round"/>`
      : line(p[0], p[1], q[0], q[1], shadeOf(col, 0.75), 1.2, 0.9);
  }
  return g;
}
/** A road or path: a light band with a darker edge. */
export function road(d: string, w = 26, col = '#e2d2a8'): string {
  return `<path d="${d}" stroke="${shadeOf(col, 0.8)}" stroke-width="${w + 5}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>` +
    `<path d="${d}" stroke="${col}" stroke-width="${w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
}
/** A stretch of stone wall (city / sanctuary wall), seen from high up, with a coping and block joints. */
export function wall(x1: number, y1: number, x2: number, y2: number, s = 1, col = '#d9c9a6'): string {
  const h = 22 * s, dx = 0, top = (y: number) => y - h;
  let g = poly([[x1, y1], [x2, y2], [x2 + dx, top(y2)], [x1 + dx, top(y1)]], col, 1.8);
  g += poly([[x1, top(y1)], [x2, top(y2)], [x2 + 6 * s, top(y2) - 6 * s], [x1 + 6 * s, top(y1) - 6 * s]], shadeOf(col, 1.05), 1.4);
  const n = Math.max(2, Math.round(Math.hypot(x2 - x1, y2 - y1) / (26 * s)));
  for (let i = 1; i < n; i++) { const k = i / n, x = x1 + (x2 - x1) * k, y = y1 + (y2 - y1) * k; g += line(x, y, x, y - h, shadeOf(col, 0.75), 1, 0.8); }
  return g;
}
export type Act = 'stand' | 'walk' | 'carry' | 'point' | 'row' | 'fight' | 'talk' | 'sit';
/** A small person for busy wide shots (~30 px tall at s=1): round head, tunic, simple limbs, ONE action. */
export function tiny(x: number, y: number, s = 1, seed = 0, act: Act = 'stand', t = 0, o: { robe?: string; hat?: string; flip?: boolean; spear?: boolean; shield?: string } = {}): string {
  const R = rng(seed * 7 + 3), robe = o.robe ?? ['#e6dcc6', '#8e5a7a', '#5a7a8e', '#a8643a', '#6f7a4a', '#c9b48a', '#b5452c'][Math.floor(R() * 7)];
  const skin = ['#d8a87c', '#cf9e72', '#e0b48c', '#c98f62'][seed % 4], ph = t * 6 + seed;
  const k = s * (o.flip ? -1 : 1);
  const sw = act === 'walk' || act === 'carry' ? Math.sin(ph) * 5 : 0;
  let g = `<ellipse cx="0" cy="0" rx="8" ry="2.6" fill="rgba(0,0,0,.18)"/>`;
  g += line(-2, -10, -2 - sw, 0, OUT, 2.4) + line(2, -10, 2 + sw, 0, OUT, 2.4);                                         // legs
  g += poly([[-6, -22], [6, -22], [7, -8], [-7, -8]], robe, 1.4);                                                        // tunic
  const arm = act === 'point' ? [10, -26] : act === 'fight' ? [10 + 3 * Math.sin(ph * 1.5), -28] : act === 'talk' ? [9, -20 + 3 * Math.sin(ph)] :
    act === 'row' ? [9 + 4 * Math.sin(ph), -14] : act === 'carry' ? [0, -30] : [7, -10];
  g += line(5, -20, arm[0], arm[1], OUT, 2) + line(-5, -20, act === 'carry' ? 0 : -7, act === 'carry' ? -30 : -10, OUT, 2);
  if (act === 'carry') g += poly([[-8, -36], [8, -36], [7, -29], [-7, -29]], '#c9a66b', 1.2);                           // a bundle on the head
  if (o.spear) g += line(arm[0], arm[1] + 8, arm[0] + 2, arm[1] - 26, '#6a4428', 1.6) + `<path d="M${arm[0] + 2} ${arm[1] - 26} l-2 -6 l4 0 Z" fill="#bdbdbd"/>`;
  if (o.shield) g += `<circle cx="-7" cy="-16" r="6" fill="${o.shield}" stroke="${OUT}" stroke-width="1.2"/>`;
  g += `<circle cx="0" cy="-27" r="5.2" fill="${skin}" stroke="${OUT}" stroke-width="1.3"/>`;
  if (s >= 1.6) {                          // CLOSE bird's-eye: the figure is big on screen, so it gets a face and costume detail
    const hairC = ['#3a2a1e', '#1c1612', '#5a3a24', '#2a1d14'][seed % 4], man = seed % 3 !== 1;
    g += `<path d="M-5.2 -28 Q-5 -33.5 0 -33.6 Q5 -33.5 5.2 -28 Q3 -30.5 0 -30.6 Q-3 -30.5 -5.2 -28 Z" fill="${hairC}"/>`;          // hair
    if (man) g += `<path d="M-4.4 -25.6 Q0 -20.2 4.4 -25.6 Q2.6 -23.4 0 -23.4 Q-2.6 -23.4 -4.4 -25.6 Z" fill="${hairC}"/>`;          // beard
    const mood = (seed * 13) % 4;                                                                                                    // brows set the mood
    g += `<circle cx="-1.9" cy="-27.6" r=".75" fill="${OUT}"/><circle cx="1.9" cy="-27.6" r=".75" fill="${OUT}"/>`;
    g += mood === 0 ? `<path d="M-3 -29.6 L-0.9 -28.9 M3 -29.6 L0.9 -28.9" stroke="${OUT}" stroke-width=".7"/>` :                    // angry
      mood === 1 ? `<path d="M-3 -29 L-0.9 -29.6 M3 -29 L0.9 -29.6" stroke="${OUT}" stroke-width=".7"/>` :                             // worried
      `<path d="M-3 -29.4 L-1 -29.4 M3 -29.4 L1 -29.4" stroke="${OUT}" stroke-width=".6"/>`;
    g += `<path d="M-6.6 -14 L6.6 -14" stroke="${shadeOf(robe, 0.6)}" stroke-width="1.6"/>` + `<path d="M-6 -21.5 L6 -21.5" stroke="${shadeOf(robe, 0.7)}" stroke-width="1"/>`;   // belt + neckline
  }
  if (o.hat) g += `<path d="M-5.5 -28 Q0 -36 5.5 -28 Z" fill="${o.hat}" stroke="${OUT}" stroke-width="1.1"/>`;
  return `<g transform="translate(${f(x)} ${f(y)}) scale(${k.toFixed(3)} ${s.toFixed(3)})">${g}</g>`;
}
/** A small ship from a high angle (trireme or merchant), with oar banks that row. */
export function shipTop(x: number, y: number, s = 1, kind: 'greek' | 'persian' | 'boat' = 'greek', t = 0, rowing = 0.6, seed = 0): string {
  const L = (kind === 'boat' ? 60 : 160) * s, B = (kind === 'boat' ? 16 : 26) * s;
  const hull = kind === 'greek' ? '#3d2a1e' : kind === 'persian' ? '#5a3424' : '#7a5234';
  let g = `<path d="M${f(x - L / 2 - 10 * s)} ${f(y + 6 * s)} Q${f(x)} ${f(y + 14 * s)} ${f(x + L / 2 + 10 * s)} ${f(y + 6 * s)}" stroke="#e6f3f5" stroke-width="${f(3 * s)}" fill="none" opacity=".6"/>`;
  if (kind !== 'boat') for (let i = 0; i < 12; i++) { const ox = x - L / 2 + 14 * s + i * (L - 28 * s) / 11, sw = 6 * s * Math.sin(t * 6 * rowing + i * 0.4 + seed); g += line(ox, y, ox - 4 * s + sw, y + 16 * s, '#b58a56', 1.4 * s); }
  g += poly([[x - L / 2, y], [x + L / 2 - 14 * s, y], [x + L / 2 + 6 * s, y - B * 0.5], [x + L / 2 - 14 * s, y - B], [x - L / 2 + 10 * s, y - B]], hull, 1.6);
  g += poly([[x - L / 2 + 10 * s, y - B], [x + L / 2 - 14 * s, y - B], [x + L / 2 - 20 * s, y - B - 6 * s], [x - L / 2 + 14 * s, y - B - 6 * s]], shadeOf(hull, 1.4), 1.2);   // deck
  if (kind === 'greek') g += `<circle cx="${f(x + L / 2 - 6 * s)}" cy="${f(y - B * 0.5)}" r="${f(3 * s)}" fill="#f2ede0" stroke="${OUT}" stroke-width="1"/>`;   // painted eye
  if (kind !== 'boat') for (let i = 0; i < 6; i++) g += `<circle cx="${f(x - L / 2 + 24 * s + i * 20 * s)}" cy="${f(y - B - 8 * s)}" r="${f(3.4 * s)}" fill="${kind === 'greek' ? '#c99a45' : '#e7dcc6'}" stroke="${OUT}" stroke-width="1"/>`;   // marines
  return g;
}
/** Sea from a high view: gradient water + many short wave strokes drifting. */
export function seaTop(id: string, x0: number, y0: number, x1: number, y1: number, t: number, col = '#4f8aa6', seed = 1): string {
  const R = rng(seed);
  let g = `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${shadeOf(col, 1.18)}"/><stop offset="1" stop-color="${shadeOf(col, 0.85)}"/></linearGradient></defs>` +
    `<rect x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}" fill="url(#${id})"/>`;
  for (let i = 0; i < 140; i++) { const x = x0 + ((R() * (x1 - x0) + t * 8) % (x1 - x0)), y = y0 + R() * (y1 - y0), w = 8 + R() * 14; g += `<path d="M${f(x)} ${f(y)} q${f(w / 2)} -3 ${f(w)} 0" stroke="#e3f1f4" stroke-width="1.6" fill="none" opacity=".55"/>`; }
  return g;
}
