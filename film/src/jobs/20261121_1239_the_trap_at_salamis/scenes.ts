// ============================================================================================================
// LONG — "The Trap at Salamis" (16:9, ~13 min). Plan 7. Sets grown from this story's own engine proof (never
// published): throne hill (Mount Aigaleos), the strait, the night sea, the Greek camp, the shore. New sets drawn fresh
// for this film: Delphi, Athens (Pnyx + Acropolis), Laurium + the shipyard, the trireme, the Hellespont, Thermopylae.
// Era sheet: jobs/20261121-1239-the-trap-at-salamis/era.json (NO Parthenon in 480 BC). Registry cast (r19).
// Every action lands on its word (actions centred on the word), cross-fades, eased starts (r28-r30).
// ============================================================================================================
import type { SceneFn, ShotCtx } from '../../film/sequence';
import { OUT, bg, hand, limb, ln, rng, sh, shade, wrap } from '../../kit/core';
import { aspis, head, hair, hopliteBody, pole } from '../../kit/cast';
import { anticipate, beat, blinkAt, breathe, easeInOut, easeOutBack, tween } from '../../kit/anim';
import { camLayer } from '../../kit/camera';
import { mouthAt } from '../../kit/lipsync';
import { card } from '../../kit/tags';
import { field, house, road, seaTop, shipTop, templeTop, tiny, tree, wall } from '../../kit/town';
import * as xerxes from '../../characters/xerxes';
import * as themistocles from '../../characters/themistocles';
import lip from './lipsync.json';

const W = 1920, H = 1080;
const L = (c: ShotCtx, depth: number, s: string) => camLayer(c.local, depth, c.cam, s);
/** 0..1 progress of beat i's action, centred on its word (the action is mid-motion when the word is heard). */
const bt = (c: ShotCtx, i: number, lead = 0.3, dur = 0.6) => i < c.shot.beats.length ? beat(c.local, c.beatT(i), Math.max(lead, dur * 0.5), dur) : 0;   // an unplanned beat never fires   // centred on the word
const LIP = (lip as any).lines;
/** Index of the planned beat on this word (scenes name their beats by word, so added beats never shift an action). */
const bi = (c: ShotCtx, word: string): number => { const i = c.shot.beats.findIndex((b: any) => b.word.toLowerCase() === word.toLowerCase()); return i < 0 ? 99 : i; };
/** Place an SVG fragment at x,y with scale k (and an optional rotation in degrees). */
const at = (x: number, y: number, k: number, svg: string, rot = 0) => `<g transform="translate(${x.toFixed(1)} ${y.toFixed(1)})${rot ? ` rotate(${rot.toFixed(2)})` : ''} scale(${k})">${svg}</g>`;
/** Expression change landing on beat i: cross-fade from -> to over ~0.2 s (never a one-frame snap). */
const exch = (c: ShotCtx, i: number, from: any, to: any) => ({ expr: from, exprTo: to, exprMix: tween(c.local, c.beatT(i) - 0.16, c.beatT(i) + 0.04, 0, 1) });

// ---------- shared drawing for this video ----------
function skyGrad(c: ShotCtx, name: string, stops: [number, string][]): string {
  const id = c.pid(name);
  return `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">${stops.map(([o, col]) => `<stop offset="${o}" stop-color="${col}"/>`).join('')}</linearGradient></defs>` +
    `<rect x="-300" y="-300" width="${W + 600}" height="${H + 600}" fill="url(#${id})"/>`;
}
function glow(c: ShotCtx, name: string, x: number, y: number, r: number, col: string, op = 1): string {
  const id = c.pid(name);
  return `<defs><radialGradient id="${id}"><stop offset="0" stop-color="${col}" stop-opacity="${op}"/><stop offset="1" stop-color="${col}" stop-opacity="0"/></radialGradient></defs>` +
    `<circle cx="${x}" cy="${y}" r="${r}" fill="url(#${id})"/>`;
}
function waves(t: number, seed: number, y0: number, y1: number, n: number, col: string, speed = 20): string {
  const R = rng(seed); let s = '';
  for (let i = 0; i < n; i++) {
    const y = y0 + Math.pow(R(), 1.3) * (y1 - y0), k = 0.4 + (y - y0) / (y1 - y0) * 1.4, w = 14 * k + R() * 16 * k;
    const x = wrap(R() * (W + 400) + t * speed * k, W + 400) - 200;
    s += `<path d="M${x.toFixed(1)} ${(y + 2 * Math.sin(t * 2 + i)).toFixed(1)} q${w / 2} ${-4 * k} ${w} 0" stroke="${col}" stroke-width="${(1.6 + k).toFixed(1)}" fill="none" stroke-linecap="round" opacity=".7"/>`;
  }
  return s;
}
function pine(x: number, y: number, k: number, col = '#4b6a3a'): string {
  return `<g transform="translate(${x} ${y}) scale(${k})">${sh('rect', { x: -4, y: -8, width: 8, height: 24 }, '#5a3a24')}` +
    bg('M0 -78 L28 -28 L12 -30 L34 4 L-34 4 L-12 -30 L-28 -28 Z', col, 4) + '</g>';
}
// a warship seen from the side, bow to the LEFT. kind greek: dark hull + painted eye; persian: curved stern, sun band.
// Sails are down: triremes fought under oars (era sheet: trireme, persian_ship).
function warship(t: number, kind: 'greek' | 'persian', oarSpeed = 0.8, ph = 0, broken = 0): string {
  const hull = kind === 'greek' ? '#3d2a1e' : '#5a3424', band = kind === 'greek' ? '#b5452c' : '#d9b443';
  let s = `<path d="M480 6 Q700 24 960 16" stroke="#e6f3f5" stroke-width="9" fill="none" stroke-linecap="round" opacity=".6"/>`;
  // oars (behind the hull): rowing cycle with a ripple bow -> stern; broken = share of snapped oars
  let i = 0;
  for (let x = -380; x <= 380; x += 38, i++) {
    const p = t * Math.PI * 2 * oarSpeed + ph - i * 0.12, lift = Math.max(0, Math.cos(p));
    const snapped = broken > 0 && (i * 7919) % 10 < broken * 10;
    const bx = x - 70 + (snapped ? 0 : 30 * Math.sin(p)), by = snapped ? -20 : 44 - 26 * lift;
    s += `<path d="M${x} -52 L${bx.toFixed(1)} ${by.toFixed(1)}" stroke="${OUT}" stroke-width="7" stroke-linecap="round"/><path d="M${x} -52 L${bx.toFixed(1)} ${by.toFixed(1)}" stroke="#b58a56" stroke-width="3" stroke-linecap="round"/>`;
  }
  const d = kind === 'greek'
    ? 'M-470 -6 L-470 -40 Q-480 -108 -436 -122 L400 -122 Q474 -136 500 -200 Q518 -248 490 -288 Q534 -266 534 -200 Q530 -116 446 -38 Q300 4 -400 4 Z'
    : 'M-460 -6 L-466 -46 Q-470 -104 -430 -118 L380 -118 Q470 -128 520 -190 Q560 -250 520 -300 Q580 -270 572 -190 Q556 -100 450 -36 Q300 4 -400 4 Z';
  s += bg(d, hull, 6) + `<path d="M-462 -98 L410 -98 Q470 -104 500 -146" stroke="${band}" stroke-width="13" fill="none"/>`;
  s += `<path d="M-470 -40 L-470 -6 L-400 4 L300 4 Q380 -4 446 -38 Z" fill="rgba(0,0,0,.25)"/>`;
  for (let x = -400; x <= 400; x += 38) s += `<circle cx="${x}" cy="-52" r="5" fill="#1a120c"/>`;
  s += bg('M-470 -12 L-560 -24 L-470 -38 Z', '#c99a45', 4);                                          // bronze ram
  if (kind === 'greek') s += bg('M-452 -90 Q-430 -106 -406 -90 Q-430 -76 -452 -90 Z', '#f2ede0', 3) + `<circle cx="-429" cy="-90" r="7" fill="${OUT}"/>`;
  else s += `<circle cx="-410" cy="-84" r="16" fill="#d9b443" stroke="${OUT}" stroke-width="3"/><circle cx="-410" cy="-84" r="7" fill="#b5452c"/>`; // sun emblem
  // marines on deck: small helmeted heads + shields along the rail
  for (let k = 0; k < 8; k++) {
    const x = -300 + k * 80;
    s += `<circle cx="${x}" cy="-142" r="16" fill="${kind === 'greek' ? '#c99a45' : '#e7dcc6'}" stroke="${OUT}" stroke-width="4"/>`;
    s += `<ellipse cx="${x + 22}" cy="-128" rx="20" ry="22" fill="${kind === 'greek' ? '#b23a2a' : '#7a5a2a'}" stroke="${OUT}" stroke-width="4"/>`;
  }
  return s;
}
// generic extras (not registered characters): Persian scribe, parasol bearer, the slave Sicinnus, Greek soldier
function scribe(t: number, seed: number, pose: { write?: number; look?: number; frozen?: boolean; expr?: any } = {}): string {
  const skin = '#c98f62';
  let s = `<ellipse cx="0" cy="-4" rx="70" ry="12" fill="rgba(0,0,0,.15)"/>`;
  // kneeling: robe as a mound, board on the knees
  s += bg('M-60 -4 Q-70 -110 -40 -150 L40 -150 Q70 -110 64 -4 Z', '#2f5a7a', 5) + ln('M-30 -130 L-40 -10 M10 -140 L14 -10', 3, 'rgba(0,0,0,.25)');
  s += sh('rect', { x: -46, y: -100, width: 92, height: 40, rx: 4 }, '#c9a66b') + ln('M-36 -88 L30 -88 M-36 -76 L22 -76', 2.5, '#6b4a2a');
  const w = pose.write ?? 0;                                                         // 0..1 writing stroke
  const hx = -10 + 40 * w, hy = -78 - 10 * Math.sin(w * Math.PI);
  s += limb(`M30 -140 Q40 -100 ${hx + 10} ${hy}`, 16, '#2f5a7a') + pole(hx, hy - 30, hx + 4, hy + 6, '#6b4a2a') + hand(hx, hy, skin);
  const lift = pose.frozen ? 0 : breathe(t, seed) * -1.5;
  s += `<g transform="translate(0 ${lift.toFixed(2)}) scale(.62) translate(0 ${-30 + (pose.look ?? 0) * -10})">${head(skin, pose.expr ?? 'neutral', { blink: !pose.frozen && blinkAt(t, seed), beard: '#1c1612' })}` +
    sh('path', { d: 'M-58 -300 Q-60 -376 0 -380 Q60 -376 58 -300 Z' }, '#e7dcc6') + '</g>';                  // Persian felt cap
  return s;
}
function sicinnus(t: number, row: number, expr: any = 'worried', blink = false): string {
  const skin = '#c9935f';
  let s = bg('M-46 -238 Q0 -248 46 -238 L50 -120 L-50 -120 Z', '#a8946e', 6);                       // plain slave's tunic
  const a = -0.5 + row;                                                                           // rowing arms
  s += limb(`M-44 -222 Q${-90 - 30 * a} -190 ${-110 - 40 * a} -168`, 18, skin) + hand(-110 - 40 * a, -168, skin);
  s += limb(`M44 -222 Q${-40 - 30 * a} -170 ${-96 - 40 * a} -150`, 18, skin) + hand(-96 - 40 * a, -150, skin);
  s += head(skin, expr, { blink }) + sh('path', { d: 'M-60 -300 Q-64 -360 0 -364 Q64 -360 60 -300 Q50 -334 0 -336 Q-50 -334 -60 -300 Z' }, '#2a1d14');
  return s;
}
function singer(t: number, seed: number, singing: number, raise: number): string {
  const skin = ['#d8a87c', '#cf9e72', '#e0b48c'][seed % 3];
  let s = hopliteBody(skin, false);
  s += limb(`M-44 -222 Q-80 ${-210 - 40 * raise} -82 ${-190 - 60 * raise}`, 20, skin) + hand(-82, -186 - 60 * raise, skin);
  s += aspis(56, -170, 78, undefined, (['owl', 'star', 'crescent', 'none'] as const)[seed % 4]);   // Athenian blazons
  const open = singing > 0 && Math.sin(t * 9 + seed) > -0.6;
  s += `<g transform="translate(0 ${(breathe(t, seed) * -1.5).toFixed(2)})">${head(skin, singing ? 'stern' : 'neutral', { blink: blinkAt(t, seed), beard: '#3a2a1e', extra: true })}`;
  if (open) s += `<ellipse cx="0" cy="-260" rx="12" ry="${(6 + 6 * singing).toFixed(1)}" fill="#7a2b22" stroke="${OUT}" stroke-width="4"/>`;
  s += hair.corinthian() + '</g>';
  return s;
}

// ---------- THRONE HILL (Mount Aigaleos at dawn) ----------
function cloud(x: number, y: number, k: number, col = '#fbe7cf'): string {
  return `<g transform="translate(${x.toFixed(1)} ${y}) scale(${k})">${bg('M0 40 Q-14 8 26 6 Q34 -22 72 -10 Q100 -34 132 -4 Q172 -6 166 40 Z', col, 4)}<path d="M22 34 Q80 24 150 34" stroke="#e9c7a6" stroke-width="5" fill="none"/></g>`;
}
function birds(t: number, seed: number, n: number): string {   // gulls drifting and flapping
  const R = rng(seed); let s = '';
  for (let i = 0; i < n; i++) {
    const x = wrap(R() * W + t * (18 + R() * 14), W + 200) - 100, y = 160 + R() * 260, f = 7 * Math.sin(t * 8 + i * 2), k = 0.6 + R() * 0.6;
    s += `<path d="M${(x - 14 * k).toFixed(1)} ${(y - f * 0.2).toFixed(1)} Q${(x - 7 * k).toFixed(1)} ${(y - 8 * k - f).toFixed(1)} ${x.toFixed(1)} ${y} Q${(x + 7 * k).toFixed(1)} ${(y - 8 * k - f).toFixed(1)} ${(x + 14 * k).toFixed(1)} ${(y - f * 0.2).toFixed(1)}" stroke="${OUT}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  }
  return s;
}
function dawnSky(c: ShotCtx, sunY: number): string {
  const t = c.t;   // clouds and birds drift on the global clock so they continue across cuts
  return skyGrad(c, 'dsky', [[0, '#e8a074'], [0.5, '#f6cd94'], [1, '#fde8c2']]) + glow(c, 'dsun', 1380, sunY, 320, '#fff3cf') +
    `<circle cx="1380" cy="${sunY}" r="58" fill="#fff4d2" stroke="#f0c47a" stroke-width="4"/>` +
    cloud(wrap(240 + t * 4, W + 400) - 200, 110, 1.3) + cloud(wrap(820 + t * 3, W + 400) - 200, 200, 0.9) +
    cloud(wrap(1560 + t * 5, W + 400) - 200, 90, 1.1) + cloud(wrap(1120 + t * 2, W + 400) - 200, 300, 0.6, '#f6d8b8') + birds(t, 5, 7);
}
function salamisHills(): string {   // Salamis island across the strait (far layer), aerial haze
  return bg('M-200 560 L80 470 L260 500 L420 440 L620 500 L800 470 L1000 520 L1000 600 L-200 600 Z', '#b7a2b8', 3) +
    bg('M900 600 L1100 520 L1300 545 L1500 500 L1700 540 L2100 520 L2100 610 L900 610 Z', '#a993ad', 3);
}
function farFleet(t: number, n: number, y: number, seed: number, scale = 0.1): string {
  const R = rng(seed); let s = '';
  for (let i = 0; i < n; i++) {
    const x = 200 + R() * 1500, yy = y + R() * 60, k = scale * (0.7 + (yy - y) / 60 * 0.6);
    s += `<g transform="translate(${x.toFixed(1)} ${(yy + Math.sin(t * 1.3 + i) * 2).toFixed(1)}) scale(${k.toFixed(3)})"><path d="M-460 -10 Q0 10 460 -10 L420 -110 L-440 -110 Z" fill="#4a3022" stroke="${OUT}" stroke-width="24"/></g>`;
  }
  return s;
}
function throneSet(c: ShotCtx, opts: { sunY?: number } = {}): { sky: string; far: string; mid: string; ground: string } {
  const t = c.local;
  const sky = dawnSky(c, opts.sunY ?? 330);
  let town = '';                                                   // Salamis town on the far shore: small houses + a temple
  for (let i = 0; i < 14; i++) { const x = 380 + i * 26 + (i % 3) * 6, y = 548 + (i % 2) * 8; town += `<rect x="${x}" y="${y - 14}" width="20" height="14" fill="#e8dcc4" stroke="${OUT}" stroke-width="2"/><path d="M${x - 2} ${y - 14} L${x + 10} ${y - 22} L${x + 22} ${y - 14} Z" fill="#b5674a" stroke="${OUT}" stroke-width="2"/>`; }
  town += `<path d="M700 540 L760 520 L820 540 Z" fill="#f2ead8" stroke="${OUT}" stroke-width="2"/>` + [706, 722, 738, 754, 770, 786, 802].map((x) => `<rect x="${x}" y="540" width="5" height="18" fill="#f2ead8" stroke="${OUT}" stroke-width="1.5"/>`).join('');
  const far = salamisHills() + town + `<rect x="-200" y="590" width="${W + 400}" height="200" fill="#8fb3c0"/>` + waves(t, 11, 600, 760, 70, '#e3f1f4', 6) + farFleet(t, 26, 640, 3);
  let camp = '';                                                    // the Persian camp on the lower slope (tents + banners)
  const R = rng(77);
  for (let i = 0; i < 22; i++) {
    const x = 60 + R() * 760, y = 735 + R() * 40, k = 0.7 + (y - 735) / 40 * 0.5, col = ['#e9e0c8', '#d9c39a', '#b5452c', '#e2d6b4'][i % 4];
    camp += `<g transform="translate(${x.toFixed(0)} ${y.toFixed(0)}) scale(${k.toFixed(2)})">${bg('M-22 0 L0 -26 L22 0 Z', col, 2.5)}<path d="M0 -26 L0 -36" stroke="${OUT}" stroke-width="2"/></g>`;
  }
  for (let i = 0; i < 4; i++) { const x = 140 + i * 180; camp += `<path d="M${x} 740 L${x} 690" stroke="${OUT}" stroke-width="3"/><path d="M${x} 690 L${x + 26} 697 L${x} 704 Z" fill="#7a2a5e" stroke="${OUT}" stroke-width="2"/>`; }
  for (let i = 0; i < 3; i++) { const x = 220 + i * 260; for (let q = 0; q < 5; q++) { const up = (q / 5 + t * 0.07) % 1; camp += `<circle cx="${(x + 14 * Math.sin(q + i) * up).toFixed(1)}" cy="${(730 - 150 * up).toFixed(1)}" r="${(6 + 16 * up).toFixed(1)}" fill="#a49a92" opacity="${(0.4 * (1 - up) * Math.min(1, up * 6)).toFixed(3)}"/>`; } }
  const mid = bg('M-200 760 Q300 690 760 720 Q1200 690 1500 730 Q1800 700 2120 740 L2120 1300 L-200 1300 Z', '#a5835f', 5) + camp +
    pine(140, 740, 1.1) + pine(260, 720, 0.8) + pine(1760, 730, 1.0) + pine(1860, 745, 0.7) + pine(1620, 735, 0.6) +
    Array.from({ length: 9 }, (_, i) => `<g transform="translate(${980 + i * 70} ${738 + (i % 2) * 6}) scale(.22)">${guard(t, 60 + i)}</g>`).join('') +   // guards along the ridge
    [1000, 1300, 1580].map((x, i) => `<path d="M${x} 740 L${x} 640" stroke="${OUT}" stroke-width="4"/><path d="M${x} 640 Q${x + 30} ${646 + 4 * Math.sin(t * 2 + i)} ${x + 54} 642 L${x + 54} 672 Q${x + 30} ${676 + 4 * Math.sin(t * 2 + i)} ${x} 670 Z" fill="#7a2a5e" stroke="${OUT}" stroke-width="3"/><circle cx="${x + 26}" cy="656" r="6" fill="#d9b443"/>`).join('');
  const rock = (x: number, y: number, k: number) => `<g transform="translate(${x} ${y}) scale(${k})">${bg('M-60 10 Q-70 -30 -24 -44 Q20 -56 54 -26 Q70 0 60 10 Z', '#9a7b5c', 4)}<path d="M-30 -30 Q0 -40 30 -24" stroke="#c4a27c" stroke-width="5" fill="none" stroke-linecap="round"/></g>`;
  const shrub = (x: number, y: number, k: number) => `<g transform="translate(${x} ${y}) scale(${k})">${bg('M-34 0 Q-40 -30 -14 -34 Q-4 -52 16 -40 Q40 -40 36 -12 Q42 0 34 0 Z', '#6f8a44', 4)}</g>`;
  const ground = bg('M-200 860 Q500 820 960 840 Q1400 820 2120 860 L2120 1300 L-200 1300 Z', '#8c6a4a', 5) +
    ln('M100 900 q60 -10 120 4 M1500 910 q60 -12 130 2 M700 960 q50 -8 100 3', 4, '#6e5238') +
    rock(90, 1010, 1.4) + rock(1830, 1030, 1.6) + rock(1640, 1060, 0.9) + shrub(260, 1040, 1.2) + shrub(1500, 1050, 1.0) + shrub(40, 950, 0.8);
  return { sky, far, mid, ground };
}
function throne(): string {   // golden Achaemenid throne on a stepped dais, lion feet (era: throne)
  return bg('M-170 0 L170 0 L150 -40 L-150 -40 Z', '#c9b28a', 5) + bg('M-140 -40 L140 -40 L124 -70 L-124 -70 Z', '#d8c39a', 5) +
    bg('M-80 -380 Q0 -410 80 -380 L80 -170 L-80 -170 Z', '#e2b23f', 6) + ln('M-60 -360 L60 -360 M-60 -330 L60 -330', 4, '#a8822a') +
    sh('circle', { cx: -94, cy: -78, r: 12 }, '#e2b23f') + sh('circle', { cx: 94, cy: -78, r: 12 }, '#e2b23f');
}
function seatFront(): string {   // the seat + armrests drawn IN FRONT of the king's legs = he is sitting
  return bg('M-100 -190 L100 -190 L100 -130 L-100 -130 Z', '#e2b23f', 6) + ln('M-100 -170 L100 -170', 4, '#a8822a') +
    bg('M-112 -232 L-92 -232 L-92 -76 L-112 -76 Z', '#d9a536', 5) + bg('M92 -232 L112 -232 L112 -76 L92 -76 Z', '#d9a536', 5) +
    bg('M-60 -76 L60 -76 L50 -70 L-50 -70 Z', '#c99a45', 4);
}
function parasol(t: number): string {   // royal parasol held by an attendant (era: parasol)
  const sw = Math.sin(t * 0.9) * 1.5;
  return `<g transform="rotate(${sw.toFixed(2)} 0 0)">` + pole(0, -560, 0, -120, '#6a4428') +
    bg('M-150 -560 Q0 -660 150 -560 Q75 -580 0 -578 Q-75 -580 -150 -560 Z', '#7a2a5e', 5) + ln('M-150 -560 L150 -560', 4, '#d9b443') + '</g>';
}
function guard(t: number, seed: number): string {   // a royal guard: long robe, wicker shield, spear (Persepolis guards)
  const skin = '#c98f62';
  let s = `<ellipse cx="0" cy="-4" rx="60" ry="10" fill="rgba(0,0,0,.14)"/>` + bg('M-44 -238 Q0 -248 44 -238 Q56 -120 66 -8 L-66 -8 Q-56 -120 -44 -238 Z', '#b5793a', 5);
  s += ln('M-60 -40 L60 -40', 6, '#5b2a6e') + pole(-70, -470, -70, -8, '#6a4428') + sh('path', { d: 'M-70 -500 L-78 -470 L-62 -470 Z' }, '#bdbdbd');
  s += limb('M-44 -222 Q-72 -210 -70 -190', 18, '#b5793a') + hand(-70, -186, skin);
  s += sh('path', { d: 'M30 -230 L80 -230 L86 -110 L24 -110 Z' }, '#c9a96e') + ln('M34 -210 L80 -210 M32 -180 L82 -180 M30 -150 L84 -150', 3, '#8a6a3a');
  s += `<g transform="translate(0 ${(breathe(t, seed) * -1.2).toFixed(2)})">${head(skin, 'stern', { beard: '#1c1612', blink: blinkAt(t, seed), extra: true })}` +
    sh('path', { d: 'M-60 -300 Q-62 -372 0 -376 Q62 -372 60 -300 Z' }, '#e7dcc6') + '</g>';
  return s;
}
function seatedXerxes(c: ShotCtx, pose: any): string {
  const mouth = mouthAt(c.t, LIP, 'XERXES');
  const p = { breath: breathe(c.t, 1), blink: blinkAt(c.t, 1), mouth, ...pose };
  return throne() + `<g transform="translate(0 -40)">${xerxes.draw(p)}</g>` + seatFront();
}

const throne_wide: SceneFn = (c) => {
  // s01 EWS, low angle, crane down: dawn breaks, the king settles, gold catches the light, the strait opens below
  const sunY = tween(c.local, c.beatT(bi(c, 'dawn')) - 0.35, c.beatT(bi(c, 'dawn')) + 0.5, 470, 330, easeOutBack);
  const set = throneSet(c, { sunY });
  const gleam = bt(c, bi(c, 'throne'), 0.1, 0.8);
  const settle = easeOutBack(bt(c, bi(c, 'climbed'), 0.4, 0.8));
  let hero = `<g transform="translate(1190 ${905 + 30 * (1 - settle)}) scale(.9)">${parasol(c.t)}` +
    `<g transform="translate(-300 20) scale(.85)">${guard(c.t, 41)}</g><g transform="translate(320 20) scale(.85)">${guard(c.t, 42)}</g>` +
    `<g transform="translate(-180 40)">${scribe(c.t, 4, { look: 1 })}</g>` + seatedXerxes(c, { expr: 'stern', armR: 'down' }) + '</g>';
  if (gleam > 0 && gleam < 1) hero += glow(c, 'gleam', 1190, 640, 160 * Math.sin(gleam * Math.PI), '#fff8d0', 0.9);
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far) + L(c, 0.6, set.mid) + L(c, 1, hero) + L(c, 1.15, set.ground + pine(-20, 1100, 2.2, '#3e5a30')) +
    card(1440, 60, 420, 62, 'SALAMIS · 480 BC', 27, tween(c.local, 0.6, 1.6, 0, 1));
};

const throne_xerxes: SceneFn = (c) => {
  // s03 CU low angle push-in: "Today, Greece ends." — chin lifts on "Today", cold stare on "ends"
  const set = throneSet(c);
  const lift = anticipate(bt(c, 0, 0.3, 0.6));
  const hero = `<g transform="translate(960 ${1330 - 30 * lift}) scale(2.6)">${parasol(c.t)}${seatedXerxes(c, { ...exch(c, 1, 'neutral', 'stern'), armR: 'down' })}</g>`;
  return L(c, 0.05, set.sky) + L(c, 0.25, set.far) + L(c, 1, hero);
};

const throne_scribes: SceneFn = (c) => {
  // s04 MS high angle pan: three scribes ready; styluses rise, the first stroke, they look up at the king
  const set = throneSet(c);
  const raise = easeOutBack(bt(c, 0)), stroke = bt(c, 1, 0.1, 0.9), look = easeInOut(bt(c, 2));
  let hero = `<g transform="translate(1500 760) scale(.8)">${seatedXerxes(c, { expr: 'sly' })}</g>`;
  [380, 760, 1140].forEach((x, i) => {
    hero += `<g transform="translate(${x} ${930 + i * 18}) scale(1.25)">${scribe(c.t, 10 + i, { write: raise * 0.3 + stroke * 0.7 * (i === 1 ? 1 : 0.6), look })}</g>`;
  });
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far) + L(c, 0.6, set.mid) + L(c, 1, set.ground + hero);
};

const throne_believe: SceneFn = (c) => {
  // s08 MS push-in after a whip: Xerxes smiles on "believed", waves the fleet forward on "word"
  const set = throneSet(c, { sunY: 300 });
  const wave = easeOutBack(bt(c, 1, 0.35, 0.7));
  const hero = `<g transform="translate(960 1000) scale(1.25)">${parasol(c.t)}${seatedXerxes(c, { ...exch(c, 0, 'neutral', 'sly'), armR: { from: 'down', to: 'point', k: wave } })}</g>` +
    `<g transform="translate(420 1020) scale(1.1)">${scribe(c.t, 21, { write: 0.2, look: 1, expr: 'neutral' })}</g>`;
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far) + L(c, 0.6, set.mid) + L(c, 1, set.ground + hero);
};

const throne_silent: SceneFn = (c) => {
  // s13 MS high angle: smoke over the sea; the scribes freeze, a stylus is lowered, the king stares in shock
  const set = throneSet(c, { sunY: 260 });
  const lower = easeOutBack(bt(c, 1, 0.3, 0.5));
  let smoke = '';
  for (let i = 0; i < 6; i++) { const x = 300 + i * 260; for (let q = 0; q < 6; q++) { const up = (q / 6 + c.t * 0.06) % 1; smoke += `<circle cx="${(x + 26 * Math.sin(q + i) * up).toFixed(1)}" cy="${(640 - 220 * up).toFixed(1)}" r="${(16 + 40 * up).toFixed(1)}" fill="#7d7470" opacity="${(0.45 * (1 - up) * Math.min(1, up * 6)).toFixed(3)}"/>`; } }
  let hero = `<g transform="translate(1440 860) scale(.9)">${seatedXerxes(c, { ...exch(c, 2, 'worried', 'shocked'), armR: 'down' })}</g>`;
  [300, 640, 980].forEach((x, i) => {
    hero += `<g transform="translate(${x} ${960 + i * 14}) scale(1.2)">${scribe(c.t, 30 + i, { write: i === 1 ? 0.5 * (1 - lower) : 0.4, look: 1, frozen: true, expr: 'worried' })}</g>`;
  });
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far + smoke) + L(c, 0.6, set.mid) + L(c, 1, set.ground + hero);
};

// ---------- THE STRAIT ----------
function straitBase(c: ShotCtx, time: 'dawn' | 'dusk', narrow = 0): { sky: string; far: string; sea: string } {
  const sky = time === 'dawn' ? dawnSky(c, 300) : skyGrad(c, 'dusk', [[0, '#4f3a6e'], [0.55, '#d77c56'], [1, '#f2b06a']]) + glow(c, 'dsunk', 1500, 520, 300, '#ffcf8a', 0.8);
  const far = bg(`M-200 520 L200 ${450 - narrow * 40} L520 480 L760 430 L900 520 L900 560 L-200 560 Z`, '#a993ad', 3) +
    bg(`M1000 560 L1200 ${470 - narrow * 40} L1500 500 L1800 440 L2120 480 L2120 560 Z`, '#9c86a3', 3);
  const sea = skyGrad(c, 'sea', [[0, time === 'dawn' ? '#6fa6ba' : '#7a6f8a'], [1, time === 'dawn' ? '#285f7c' : '#3a3a58']]).replace('y="-300"', 'y="550"') +
    waves(c.t, 21, 570, 1080, 140, time === 'dawn' ? '#dcf0f3' : '#c9b9c9', 18);
  return { sky, far, sea };
}
function cliffs(narrow: number): string {   // the strait's rocky shores closing in from both sides
  const k = narrow * 160;
  let s = bg(`M-200 1100 L-200 380 Q${100 + k} 460 ${180 + k} 640 Q${250 + k} 820 ${200 + k} 1100 Z`, '#8b6b4f', 5) +
    bg(`M2120 1100 L2120 380 Q${1820 - k} 460 ${1740 - k} 640 Q${1670 - k} 820 ${1720 - k} 1100 Z`, '#7f6148', 5) +
    pine(80 + k, 520, 0.9) + pine(1840 - k, 500, 0.9) + pine(30 + k, 600, 0.7) + pine(1890 - k, 590, 0.7);
  for (let i = 0; i < 6; i++) s += `<path d="M${40 + k * 0.6} ${560 + i * 80} q50 -10 ${90 + i * 8} 6 M${1880 - k * 0.6} ${560 + i * 80} q-50 -10 ${-90 - i * 8} 6" stroke="#5e442e" stroke-width="4" fill="none" stroke-linecap="round"/>`;   // rock strata
  s += `<g transform="translate(${150 + k} 470)">${bg('M-18 0 L-18 -60 L18 -60 L18 0 Z', '#c4a27c', 3)}${bg('M-26 -60 L0 -84 L26 -60 Z', '#9a5a3a', 3)}</g>`;   // a lookout hut on the Salamis shore
  return s;
}

const strait_fleet: SceneFn = (c) => {
  // s02 EWS high angle pull-out: rows of Persian ships appear, oars lift and wait for the order
  const b = strait_base_cached(c, 'dawn');
  const appear = easeInOut(bt(c, 0, 0.25, 1.8)), lift = easeOutBack(bt(c, bi(c, 'morning') < 99 ? bi(c, 'morning') : 2, 0.3, 0.5));
  let fleet = '';
  for (let row = 0; row < 4; row++) for (let i = 0; i < 9; i++) {
    const x = 140 + i * 205 + (row % 2) * 100, y = 640 + row * 105, k = 0.13 + row * 0.035;
    const on = Math.min(1, Math.max(0, appear * 4 - row));
    fleet += `<g opacity="${on.toFixed(2)}" transform="translate(${(x - 46 * lift * (row + 1)).toFixed(1)} ${y + Math.sin(c.t * 1.2 + i + row) * 3}) scale(${k.toFixed(3)})">${warship(c.t, 'persian', 0.2 + 0.8 * lift, i)}</g>`;   // on the order: oars bite, the fleet lurches forward
  }
  return L(c, 0.05, b.sky) + L(c, 0.2, b.far) + L(c, 0.5, b.sea) + L(c, 1, fleet);
};
function strait_base_cached(c: ShotCtx, time: 'dawn' | 'dusk') { return straitBase(c, time); }

const strait_enter: SceneFn = (c) => {
  // s09 EWS high angle track: the sun clears the hills, the Persian fleet surges into the narrows, the cliffs close in
  const b = straitBase(c, 'dawn', 0.5);
  const surge = easeInOut(bt(c, 1, 0.3, 1.2)), close = easeOutBack(bt(c, 2, 0.35, 0.7));
  let fleet = '';
  for (let i = 0; i < 14; i++) {
    const lane = i % 4, x = 1700 - surge * 520 - (i * 120) % 900 + lane * 40, y = 640 + lane * 90 + (i % 3) * 20, k = 0.12 + lane * 0.03;
    fleet += `<g transform="translate(${x.toFixed(1)} ${y}) scale(${k.toFixed(3)})">${warship(c.t, 'persian', 1.0, i)}</g>`;
  }
  return L(c, 0.05, b.sky) + L(c, 0.2, b.far) + L(c, 0.5, b.sea) + L(c, 0.9, fleet) + L(c, 1.2, cliffs(0.4 + close * 0.5));
};

const strait_jam: SceneFn = (c) => {
  // s10 WS eye level, handheld: hulls bump, a ship swings sideways, oars snap
  const b = straitBase(c, 'dawn', 0.9);
  const bump = bt(c, 0, 0.1, 0.4), swing = easeOutBack(bt(c, 1, 0.3, 0.8)), snap = bt(c, 2, 0.05, 0.3);
  const jolt = Math.sin(bump * Math.PI) * 44;
  const ships = [[360, 760, 0.3, 0], [1560, 740, 0.3, 0.3], [520, 820, 0.42, 0], [1300, 790, 0.4, 0.5], [900, 900, 0.5, 0], [1500, 960, 0.48, 0], [300, 1010, 0.62, 0]];
  let fleet = '';
  ships.forEach(([x, y, k, br], i) => {
    const rot = (i === 3 ? -14 * swing : (i === 4 ? 3 * Math.sin(bump * Math.PI) : 0)) + 2.2 * Math.sin(c.t * 1.7 + i * 1.3);   // every hull rolls in the crowd
    fleet += `<g transform="translate(${(x + (i === 4 ? jolt : 0) + 12 * Math.sin(c.t * 0.9 + i)).toFixed(1)} ${(y + 6 * Math.sin(c.t * 1.6 + i)).toFixed(1)}) rotate(${rot.toFixed(2)}) scale(${k})">${warship(c.t, 'persian', 0.9, i, i === 4 ? snap : br)}</g>`;
  });
  let splinters = '';
  if (snap > 0 && snap < 1) { const R = rng(5); for (let i = 0; i < 10; i++) { const a = R() * Math.PI * 2, d = 80 * snap; splinters += `<rect x="${(900 + Math.cos(a) * d).toFixed(1)}" y="${(860 + Math.sin(a) * d - 40 * snap).toFixed(1)}" width="16" height="4" fill="#b58a56" stroke="${OUT}" stroke-width="2" transform="rotate(${(a * 57).toFixed(0)} 900 860)"/>`; } }
  return L(c, 0.05, b.sky) + L(c, 0.25, b.far) + L(c, 0.5, b.sea) + L(c, 1, fleet + splinters) + L(c, 1.25, cliffs(0.95));
};

const strait_ram: SceneFn = (c) => {
  // s12 CU low angle, handheld, letterbox: a Greek warship charges, oars dig in, the ram strikes, planks burst
  const b = straitBase(c, 'dawn', 0.9);
  const charge = easeInOut(bt(c, 0, 0.3, 1.6)), dig = bt(c, 1), hit = bt(c, 2, 0.08, 0.25), burst = bt(c, 3, 0.1, 1.2);
  const gx = -420 + charge * 760 + (hit >= 1 ? 24 : 0);
  let s = `<g transform="translate(1380 760) rotate(${(10 + (hit >= 1 ? 4 * (1 - burst) : 0)).toFixed(2)}) scale(1.05)">${warship(c.t, 'persian', 0.3, 2, hit >= 1 ? 0.6 : 0)}</g>`;
  s += `<g transform="translate(${gx.toFixed(1)} 1010) rotate(${(-9 - 2 * Math.sin(c.t * 2)).toFixed(2)}) scale(1.35)">${warship(c.t, 'greek', 1.2 + dig * 0.6, 0)}</g>`;
  s += waves(c.t, 99, 960, 1080, 30, '#e9f6f8', 40);
  if (hit > 0) {
    const R = rng(9); let parts = '';
    for (let i = 0; i < 18; i++) { const a = -Math.PI * R(), d = 260 * burst + 40 * hit; parts += `<rect x="${(960 + Math.cos(a) * d).toFixed(1)}" y="${(880 + Math.sin(a) * d + 300 * burst * burst).toFixed(1)}" width="${18 + R() * 20}" height="6" fill="#8a5a36" stroke="${OUT}" stroke-width="2.5" transform="rotate(${(R() * 180).toFixed(0)} ${960} 880)"/>`; }
    s += parts + `<ellipse cx="980" cy="980" rx="${(120 + 240 * burst).toFixed(1)}" ry="${(40 + 80 * burst).toFixed(1)}" fill="#e8f6f8" opacity="${(0.9 * (1 - burst)).toFixed(2)}"/>`;
    s += glow(c, 'hit', 960, 880, 260 * Math.sin(Math.min(1, hit) * Math.PI / 2) * (1 - burst * 0.8), '#fff1c0', 0.9);
  }
  return L(c, 0.05, b.sky) + L(c, 0.3, b.far) + L(c, 0.6, b.sea) + L(c, 1, s);
};

const strait_closed: SceneFn = (c) => {
  // s14 EWS high angle pull-out at dusk: smoke over the wrecks, the Greek ships ring them
  const b = straitBase(c, 'dusk', 0.9);
  const smokeUp = easeOutBack(bt(c, 0, 0.3, 0.7)), ring = easeOutBack(bt(c, 1, 0.3, 0.7));
  let s = '';
  for (let i = 0; i < 9; i++) {
    const x = 300 + i * 170, y = 760 + (i % 3) * 50;
    s += `<g transform="translate(${x} ${y}) rotate(${(i % 2 ? 18 : -12)}) scale(.16)">${warship(0, 'persian', 0, i, 0.7)}</g>`;
    for (let q = 0; q < 5; q++) { const up = (q / 5 + c.t * 0.08) % 1 * smokeUp; s += `<circle cx="${(x + 30 * Math.sin(q * 2 + i) * up).toFixed(1)}" cy="${(y - 20 - 260 * up).toFixed(1)}" r="${(14 + 34 * up).toFixed(1)}" fill="#4f4648" opacity="${(0.5 * (1 - up) * Math.min(1, up * 6)).toFixed(3)}"/>`; }
    s += `<circle cx="${x}" cy="${y - 10}" r="${(10 + 6 * Math.sin(c.t * 8 + i)).toFixed(1)}" fill="#ff9a3c" opacity=".85"/>`;
  }
  for (let i = 0; i < 8; i++) {
    const a = Math.PI * (0.1 + i * 0.11), x = 960 + Math.cos(a) * (900 - 120 * ring), y = 1000 - Math.sin(a) * (180 - 20 * ring);
    s += `<g transform="translate(${x.toFixed(1)} ${y.toFixed(1)}) scale(.13)">${warship(c.t, 'greek', 0.4, i)}</g>`;
  }
  return L(c, 0.05, b.sky) + L(c, 0.2, b.far) + L(c, 0.5, b.sea) + L(c, 1, s);
};

// ---------- THE NIGHT CROSSING ----------
const night_crossing: SceneFn = (c) => {
  // s05 WS tracking: the moon comes out, a man in a small boat, he pulls the oars, ripples spread, he looks back
  const moon = easeOutBack(bt(c, 0, 0.3, 0.6)), there = easeOutBack(bt(c, 1, 0.3, 0.5)), look = c.local >= c.beatT(4) - 0.3;
  const row = (Math.sin(c.local * 3.6) + 1) / 2 * (c.local >= c.beatT(2) - 0.3 ? 1.4 : 0.3);
  const sky = skyGrad(c, 'nsky', [[0, '#0b1430'], [1, '#22355a']]) + glow(c, 'moon', 1450, 230, 260 * moon, '#cfe0ff', 0.6) +
    `<circle cx="1450" cy="230" r="46" fill="#eef3ff" opacity="${(0.3 + 0.7 * moon).toFixed(2)}"/>` +
    bg(`M1260 ${250 - 60 * moon} q60 -40 160 -10 q80 -30 150 10 q40 30 -30 40 l-260 0 q-60 -10 -20 -40 Z`, '#1c2a4a', 3);
  const Rs = rng(17); let stars = '';
  for (let i = 0; i < 60; i++) stars += `<circle cx="${(Rs() * W).toFixed(0)}" cy="${(Rs() * 420).toFixed(0)}" r="${(0.8 + Rs() * 1.6).toFixed(1)}" fill="#dfe8ff" opacity="${(0.4 + 0.5 * Math.abs(Math.sin(c.t * 2 + i))).toFixed(2)}"/>`;
  let lanterns = '';                                                // the Persian fleet waiting in the dark: lantern lights on the water
  for (let i = 0; i < 16; i++) { const x = 160 + i * 112 + (i % 3) * 20, y = 622 + (i % 4) * 12; lanterns += glow(c, `ln${i}`, x, y, 18, '#ffcf70', 0.9) + `<path d="M${x} ${y + 8} L${x} ${y + 40}" stroke="#ffcf70" stroke-width="3" opacity="${(0.3 + 0.2 * Math.sin(c.t * 3 + i)).toFixed(2)}"/>`; }
  const far = stars + lanterns + bg('M-200 560 L200 500 L520 530 L900 480 L1300 540 L1700 500 L2120 540 L2120 600 L-200 600 Z', '#16223c', 3) +
    [[300, 548], [640, 530], [1180, 545]].map(([x, y]) => glow(c, `fire${x}`, x, y, 26, '#ffb347', 0.9)).join('') + farFleet(c.t, 18, 610, 41, 0.08).replace(/#4a3022/g, '#121a2c');
  const sea = `<rect x="-300" y="600" width="${W + 600}" height="700" fill="#14284a"/>` + waves(c.t, 51, 610, 1080, 150, '#6a8fc0', 34) +
    `<path d="M1300 610 L1600 610 L1700 1080 L1200 1080 Z" fill="#cfe0ff" opacity="${(0.12 * moon).toFixed(2)}"/>` +
    Array.from({ length: 18 }, (_, i) => `<rect x="${(1260 + (i * 53) % 420).toFixed(0)}" y="${(640 + i * 24).toFixed(0)}" width="${(30 + 20 * Math.abs(Math.sin(c.t * 3 + i))).toFixed(1)}" height="3" fill="#e6efff" opacity="${(moon * (0.3 + 0.5 * Math.abs(Math.sin(c.t * 4 + i * 1.7)))).toFixed(2)}"/>`).join('');
  const bx = 960 + 40 * Math.sin(c.local * 0.5) - 260 * (1 - there);   // the boat glides in on "slave"
  let boat = bg('M-200 -10 Q0 40 200 -10 L170 -70 L-180 -70 Z', '#3a2a1e', 5) + ln('M-180 -60 L170 -60', 4, '#5a4030');
  boat += `<g transform="translate(-10 -40) scale(.55) ${look ? 'scale(-1 1)' : ''}">${sicinnus(c.t, row, look ? 'worried' : 'stern', blinkAt(c.t, 77))}</g>`;
  boat += `<path d="M-120 -20 L${(-260 - 40 * row).toFixed(0)} ${(40 - 20 * row).toFixed(0)}" stroke="${OUT}" stroke-width="7"/><path d="M-120 -20 L${(-260 - 40 * row).toFixed(0)} ${(40 - 20 * row).toFixed(0)}" stroke="#b58a56" stroke-width="3"/>`;
  const ripple = bt(c, 3, 0.1, 1.5);
  if (ripple > 0) boat += `<ellipse cx="-260" cy="44" rx="${(30 + 140 * ripple).toFixed(1)}" ry="${(8 + 30 * ripple).toFixed(1)}" fill="none" stroke="#9cc0e8" stroke-width="3" opacity="${(1 - ripple).toFixed(2)}"/>`;
  const bob = 10 * Math.sin(c.t * 1.9), rock = 3.5 * Math.sin(c.t * 1.5 + 0.7);          // the swell lifts and tilts the little boat
  return L(c, 0.05, sky) + L(c, 0.2, far) + L(c, 0.5, sea) + L(c, 1, `<g opacity="${(0.2 + 0.8 * there).toFixed(2)}" transform="translate(${bx.toFixed(1)} ${(840 + bob).toFixed(1)}) rotate(${rock.toFixed(2)}) scale(1.2)">${boat}</g>`);
};

// ---------- THEMISTOCLES' TENT (lamplight) ----------
function tent(c: ShotCtx): string {
  const flick = 0.9 + 0.1 * Math.sin(c.t * 13) * Math.sin(c.t * 7.3);
  return `<rect x="-300" y="-300" width="${W + 600}" height="${H + 600}" fill="#2a1c16"/>` +
    bg('M-200 1100 L-200 120 Q960 -60 2120 120 L2120 1100 Z', '#5a3e2c', 5) + ln('M300 60 L200 1100 M960 10 L960 1100 M1620 60 L1720 1100', 6, '#3e2a1e') +
    glow(c, 'lamp', 1180, 720, 700 * flick, '#ffb85c', 0.55) +
    bg('M1120 760 L1240 760 L1220 820 L1140 820 Z', '#a8643a', 4) + sh('ellipse', { cx: 1180, cy: 760, rx: 60, ry: 14 }, '#c4844a') +        // clay oil lamp on a stand
    `<path d="M1236 748 q10 -26 2 -44 q16 18 6 44 Z" fill="#ffd27a" stroke="#e8902a" stroke-width="2" transform="scale(1 ${flick.toFixed(3)})" transform-origin="1240 748"/>` +
    bg('M1100 820 L1260 820 L1250 1100 L1110 1100 Z', '#6a4428', 5) +
    bg('M-100 1000 L2020 1000 L2120 1100 L-200 1100 Z', '#7a3a2a', 4) + ln('M-100 1030 L2020 1030', 5, '#d9b443') +              // rug
    `<g transform="translate(300 860)">${bg('M-150 0 L150 0 L130 40 L-130 40 Z', '#6a4428', 4)}${bg('M-130 -6 L130 -6 L120 -2 L-120 -2 Z', '#e8d6a0', 3)}` +          // war table + the strait drawn on a hide
    `<path d="M-90 -4 Q-30 -10 0 -4 Q40 2 90 -4" stroke="#2f6f8e" stroke-width="3" fill="none"/></g>` +
    `<g transform="translate(1620 700)">${pole(0, -200, 0, 300, '#6a4428')}${pole(40, -220, 40, 300, '#6a4428')}${sh('circle', { cx: 80, cy: 60, r: 70 }, '#c99a45')}${sh('circle', { cx: 80, cy: 60, r: 56 }, '#b23a2a')}</g>`;   // spears + a shield against the tent wall
}
const camp_message: SceneFn = (c) => {
  // s06 MS push-in: Themistocles leans in, presses the sealed tablet into the slave's hands, the lamp lights his face
  const lean = easeInOut(bt(c, 0)), give = easeOutBack(bt(c, 1, 0.35, 0.7)), nod = bt(c, 2);
  const tm = `<g transform="translate(${760 + 30 * lean} 1040) scale(1.15) rotate(${(4 * lean).toFixed(2)} 0 -200)">${themistocles.draw({
    expr: 'stern', breath: breathe(c.t, 2), blink: blinkAt(c.t, 2), armL: { from: 'down', to: 'point', k: give }, armR: 'down' })}</g>`;
  const tablet = `<g transform="translate(${tween(c.local, c.beatT(1) - 0.35, c.beatT(1) + 0.35, 640, 980, easeInOut).toFixed(1)} 760)">${sh('rect', { x: -30, y: -20, width: 60, height: 40, rx: 4 }, '#c9a66b')}${sh('circle', { cx: 0, cy: 0, r: 8 }, '#9b2b22')}</g>`;
  const slave = `<g transform="translate(1300 1040) scale(1.1) scale(-1 1)">${sicinnus(c.t, 0.5, nod > 0 ? 'worried' : 'neutral', blinkAt(c.t, 78)).replace(/-110 -/g, '-110 -')}</g>`;
  return L(c, 0.2, tent(c)) + L(c, 1, tm + slave + tablet);
};
const camp_themistocles: SceneFn = (c) => {
  // s07 CU push-in: "Tell the king the Greeks will run. Tell him to strike now." — sly look, points to the sea, fist closes
  const point = easeOutBack(bt(c, 1, 0.35, 0.7)), fist = easeOutBack(bt(c, 2, 0.25, 0.4));
  const arm = fist > 0 ? { from: 'point', to: 'fist_up', k: fist } : { from: 'down', to: 'point', k: point };
  const hero = `<g transform="translate(900 1250) scale(2.7)">${themistocles.draw({ ...exch(c, 0, 'stern', 'sly'), breath: breathe(c.t, 2), blink: blinkAt(c.t, 2),
    mouth: mouthAt(c.t, LIP, 'THEMISTOCLES'), armL: arm as any, armR: 'down' })}</g>`;
  return L(c, 0.3, tent(c)) + L(c, 1, hero);
};

// ---------- THE SHORE (the battle hymn) ----------
const shore_hymn: SceneFn = (c) => {
  // s11 WS low angle push-in: Greek soldiers on the rocks raise their shields and sing
  const reveal = easeInOut(bt(c, 0, 0.3, 0.5)), raise = easeOutBack(bt(c, 1, 0.35, 0.7)), sing = c.local >= c.beatT(2) - 0.15 ? 1 : 0;
  const b = straitBase(c, 'dawn', 0.6);
  const rocks = bg('M-200 1100 L-200 820 Q300 760 700 800 Q1100 750 1500 800 Q1800 780 2120 820 L2120 1100 Z', '#7e5f44', 5);
  let men = '';
  for (let i = 0; i < 9; i++) {
    const x = 160 + i * 205, y = 900 + (i % 2) * 40;
    men += `<g opacity="${Math.max(0, Math.min(1, reveal * 4 - i * 0.3)).toFixed(2)}" transform="translate(${x} ${y}) scale(.72)">${singer(c.t, i, sing, raise)}</g>`;
  }
  const ships = `<g transform="translate(1500 700) scale(.22)">${warship(c.t, 'greek', 0.6, 1)}</g><g transform="translate(500 690) scale(.18)">${warship(c.t, 'greek', 0.6, 2)}</g>`;
  return L(c, 0.05, b.sky) + L(c, 0.25, b.far) + L(c, 0.5, b.sea + ships) + L(c, 1, rocks + men);
};


// =============================== CHAPTER 1 — cold open + Delphi (drawn for this film) ===============================
/** Which line this shot shows (one scene can serve several lines with different beats). */
const lineOf = (c: ShotCtx) => (c.shot as any).line as number;
/** A civilian of 480 BC (era: chiton_himation). kind: man | woman | child. Hands free, robe draped. */
function civilian(t: number, seed: number, o: { kind?: 'man' | 'woman' | 'child'; expr?: any; to?: any; mix?: number; arm?: number; hold?: 'none' | 'bundle' | 'child'; look?: number } = {}): string {
  const kind = o.kind ?? 'man', skin = ['#d8a87c', '#cf9e72', '#e0b48c', '#c99566'][seed % 4];
  const robe = kind === 'woman' ? ['#8e5a7a', '#5a7a8e', '#a8643a', '#6f7a4a'][seed % 4] : ['#e6dcc6', '#b8a68a', '#8a9a7a', '#c9b48a'][seed % 4];
  const k = kind === 'child' ? 0.62 : 1;
  let s = `<g transform="scale(${k})"><ellipse cx="0" cy="-4" rx="62" ry="11" fill="rgba(0,0,0,.15)"/>`;
  s += bg('M-46 -238 Q0 -250 46 -238 Q58 -120 64 -8 L-64 -8 Q-58 -120 -46 -238 Z', robe, 5);               // chiton / peplos to the feet
  s += `<path d="M-46 -236 Q10 -170 52 -60" stroke="rgba(0,0,0,.18)" stroke-width="18" fill="none"/>`;      // himation drape
  const a = o.arm ?? 0;                                                                                     // 0 down .. 1 raised
  s += limb(`M44 -222 Q${70 + 10 * a} ${-180 - 70 * a} ${56 + 20 * a} ${-140 - 140 * a}`, 18, robe) + hand(56 + 20 * a, -140 - 140 * a, skin);
  if (o.hold === 'bundle') s += bg('M-70 -170 Q-96 -150 -86 -110 Q-40 -96 -20 -126 Q-24 -170 -70 -170 Z', '#c9b48a', 4) + limb('M-44 -222 Q-80 -190 -60 -140', 18, robe) + hand(-56, -136, skin);
  else if (o.hold === 'child') s += limb('M-44 -222 Q-86 -200 -70 -150', 18, robe) + hand(-66, -146, skin);
  else s += limb('M-44 -222 Q-60 -180 -52 -140', 18, robe) + hand(-52, -134, skin);
  const lift = (breathe(t, seed) * -1.4).toFixed(2), look = (o.look ?? 0) * 14;
  s += `<g transform="translate(${look} ${lift})">` + head(skin, o.expr ?? 'neutral', { beard: kind === 'man' ? '#3a2a1e' : undefined, blink: blinkAt(t, seed), extra: true, to: o.to, mix: o.mix });
  s += kind === 'woman'
    ? sh('path', { d: 'M-64 -300 Q-70 -372 0 -380 Q70 -372 64 -300 L70 -210 Q40 -250 46 -300 Q0 -330 -46 -300 Q-40 -250 -70 -210 Z' }, '#3a2a1e') +   // long hair
      `<path d="M-70 -320 Q0 -400 70 -320 L78 -230 Q60 -300 0 -330 Q-60 -300 -78 -230 Z" fill="${robe}" stroke="${OUT}" stroke-width="4" opacity=".92"/>`  // veil
    : sh('path', { d: 'M-60 -300 Q-64 -362 0 -366 Q64 -362 60 -300 Q50 -334 0 -336 Q-50 -334 -60 -300 Z' }, kind === 'child' ? '#4a3222' : '#3a2a1e');
  return s + '</g></g>';
}

// ---------- cold open ----------
const aigaleos_dawn: SceneFn = (c) => throne_wide(c);       // the proof's opening, beats: dawn (sun) / climbed (settle) / throne (gleam)
const aigaleos_scribes: SceneFn = (c) => {
  // scribes unroll their scrolls on "scribes", a reed pen dips on "name"
  const set = throneSet(c);
  const raise = easeInOut(bt(c, bi(c, 'scribes'), 0.3, 0.8)), stroke = bt(c, bi(c, 'name'), 0.2, 0.9), look = easeInOut(bt(c, bi(c, 'fleet'), 0.3, 0.6));
  let hero = `<g transform="translate(1500 760) scale(.8)">${seatedXerxes(c, { expr: 'stern' })}</g>`;
  [380, 760, 1140].forEach((x, i) => {
    hero += `<g transform="translate(${x} ${930 + i * 18}) scale(1.25)">${scribe(c.t, 10 + i, { write: raise * 0.3 + stroke * 0.7 * (i === 1 ? 1 : 0.6), look })}</g>`;
    const w = 150 * raise;                                    // the scroll unrolls across the board
    if (w > 2) hero += `<g transform="translate(${x - 70} ${930 + i * 18 - 150})"><rect x="0" y="0" width="${w.toFixed(0)}" height="46" rx="6" fill="#ead6a4" stroke="${OUT}" stroke-width="4"/><circle cx="${w.toFixed(0)}" cy="23" r="14" fill="#c9b07a" stroke="${OUT}" stroke-width="4"/></g>`;
  });
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far) + L(c, 0.6, set.mid) + L(c, 1, set.ground + hero);
};
function greekFleetAtSalamis(c: ShotCtx, n: number, y0: number, k0: number, stir = 0): string {
  let s = '';
  for (let row = 0; row < 3; row++) for (let i = 0; i < n; i++) {
    const x = 160 + i * (1600 / n) + (row % 2) * 60, y = y0 + row * 50, k = k0 + row * 0.02;
    s += `<g transform="translate(${x.toFixed(0)} ${(y + Math.sin(c.t * 1.1 + i + row) * 2).toFixed(1)}) scale(${k.toFixed(3)})">${warship(c.t, 'greek', 0.05 + stir * 0.1, i + row)}</g>`;
  }
  return s;
}
const strait_dawn_wide: SceneFn = (c) => {
  // EWS high pull-out: the strait opens on "strait"; the Greek fleet is revealed on the Salamis shore on "Greek"
  const b = straitBase(c, 'dawn');
  const open = easeInOut(bt(c, 0, 0.3, 1.0)), show = easeInOut(bt(c, 1, 0.3, 0.9));
  const mist = `<rect x="-200" y="520" width="${W + 400}" height="600" fill="#f4e4d0" opacity="${(0.55 * (1 - open)).toFixed(3)}"/>`;
  const fleet = `<g opacity="${show.toFixed(2)}" transform="translate(0 ${(30 * (1 - show)).toFixed(1)})">${greekFleetAtSalamis(c, 8, 650, 0.12)}</g>`;
  return L(c, 0.05, b.sky) + L(c, 0.2, b.far) + L(c, 0.5, b.sea + fleet) + L(c, 1.2, cliffs(0.15)) + mist;
};
const strait_dawn_fleet: SceneFn = (c) => {
  // WS: the Greek ships, oars shipped, have not moved — a gull settles on a stern post on "still"
  const b = straitBase(c, 'dawn');
  const land = easeInOut(bt(c, 0, 0.3, 0.9));
  const fleet = greekFleetAtSalamis(c, 6, 700, 0.16);
  const gx = 1700 - 520 * land, gy = 380 + 220 * land - 60 * Math.sin(land * Math.PI);
  const gull = `<path d="M${gx - 18} ${gy} Q${gx - 9} ${gy - 12 + 10 * land * Math.sin(c.t * 10)} ${gx} ${gy} Q${gx + 9} ${gy - 12} ${gx + 18} ${gy}" stroke="${OUT}" stroke-width="4" fill="none" stroke-linecap="round"/>`;
  return L(c, 0.05, b.sky) + L(c, 0.2, b.far) + L(c, 0.5, b.sea) + L(c, 0.8, fleet + gull);
};
const salamis_families: SceneFn = (c) => {
  // MS: families on the Salamis shore look across the water; a mother pulls her child close on "run"
  const b = straitBase(c, 'dawn');
  const pull = easeInOut(bt(c, bi(c, 'run'), 0.3, 0.8)), turn = easeInOut(bt(c, bi(c, 'families'), 0.3, 0.8));
  const shore = bg('M-200 860 Q400 800 960 830 Q1500 800 2120 850 L2120 1300 L-200 1300 Z', '#b59a70', 5) +
    pine(120, 860, 1.4, '#41603a') + pine(1820, 850, 1.2, '#41603a');
  let people = '';
  const pointShips = easeOutBack(bt(c, bi(c, 'ships'), 0.3, 0.7)), bowHead = easeInOut(bt(c, bi(c, 'lost'), 0.3, 0.8));
  [[260, 'man', 0], [470, 'woman', 1], [1340, 'man', 2], [1560, 'woman', 3], [1760, 'child', 4]].forEach(([x, kind, s], k) => {
    people += at(x as number, 1010 + (k === 3 ? 12 * bowHead : 0), 1.15, civilian(c.t, s as number, { kind: kind as any, expr: 'worried', to: k === 3 ? 'grief' : undefined, mix: k === 3 ? bowHead : 0, arm: k === 0 ? Math.min(1, pointShips) : 0, look: -turn }));
  });
  // the mother and her child, centre: she draws the child in against her
  people += at(900 + 30 * pull, 1040, 1.4, civilian(c.t, 6, { kind: 'woman', expr: 'worried', to: 'grief', mix: pull, hold: 'child' }));
  people += at(1010 - 60 * pull, 1050, 1.4, civilian(c.t, 7, { kind: 'child', expr: 'worried', arm: 0.3 * pull }));
  return L(c, 0.05, b.sky) + L(c, 0.2, b.far + greekFleetAtSalamis(c, 8, 640, 0.07)) + L(c, 0.5, b.sea) + L(c, 1, shore + people);
};
const aigaleos_xerxes: SceneFn = (c) => {
  // CU low push-in: he lifts a hand at the sea on "come", a small proud smile on "mine"
  const set = throneSet(c);
  const wave = anticipate(bt(c, 0, 0.3, 0.7), 0.2);
  const hero = `<g transform="translate(960 1330) scale(2.6)">${parasol(c.t)}${seatedXerxes(c, { ...exch(c, 1, 'stern', 'sly'), armR: { from: 'down', to: 'open', k: Math.max(0, Math.min(1, wave)) } })}</g>`;
  return L(c, 0.05, set.sky) + L(c, 0.25, set.far) + L(c, 1, hero);
};
const aigaleos_xerxes_scribes: SceneFn = (c) => {
  // MS: he points at the scribes on "Write"; they bow and write on "remember"
  const set = throneSet(c, { sunY: 300 });
  const point = easeOutBack(bt(c, 0, 0.3, 0.6)), bow = easeInOut(bt(c, 1, 0.3, 0.8));
  let hero = `<g transform="translate(1200 1000) scale(1.25)">${parasol(c.t)}${seatedXerxes(c, { expr: 'stern', armR: { from: 'down', to: 'point', k: Math.min(1, point) } })}</g>`;
  [360, 640].forEach((x, i) => { hero += `<g transform="translate(${x} ${1020 + i * 10}) rotate(${(-8 * bow).toFixed(2)}) scale(1.1)">${scribe(c.t, 21 + i, { write: 0.2 + 0.7 * bow, look: 1 - bow })}</g>`; });
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far) + L(c, 0.6, set.mid) + L(c, 1, set.ground + hero);
};
const aigaleos_scroll: SceneFn = (c) => {
  // ECU: the scroll. line 7: the blank list on "list", smoke curls across it on "riddle".
  // line 122 (aftermath): the scroll is full of names on "heroes"; the scribe's hand stops on "lost".
  const late = lineOf(c) > 60;   // the aftermath shot of the same scroll
  const ink = late ? 1 : 0.12, smoke = late ? 0 : easeInOut(bt(c, bi(c, 'riddle'), 0.3, 1.0)), stop = late ? easeInOut(bt(c, bi(c, 'lost'), 0.3, 0.6)) : 0;
  let s = skyGrad(c, 'scrollbg', [[0, '#6a4a2e'], [1, '#3a2818']]);
  s += bg('M240 160 L1680 140 L1700 960 L220 980 Z', '#ead6a4', 7) + bg('M200 140 Q170 560 200 1000 L260 1000 Q240 560 260 140 Z', '#c9b07a', 6) + bg('M1660 120 Q1690 560 1660 980 L1720 980 Q1750 560 1720 120 Z', '#c9b07a', 6);
  const R = rng(9);
  for (let r = 0; r < 12; r++) {                                   // lines of Aramaic-style script (shapes, not letters)
    const y = 250 + r * 58, n = Math.round((late ? 1 : (r < 2 ? 1 : 0)) * 14);
    for (let q = 0; q < n; q++) { const x = 320 + q * 92 + R() * 20, w = 40 + R() * 40; s += `<path d="M${x.toFixed(0)} ${y} q${(w / 2).toFixed(0)} -10 ${w.toFixed(0)} 0 m6 -14 l0 18" stroke="#3a2414" stroke-width="5" fill="none" stroke-linecap="round" opacity="${ink}"/>`; }
  }
  if (smoke > 0) for (let i = 0; i < 9; i++) { const u = (i / 9 + c.t * 0.08) % 1; s += `<circle cx="${(300 + smoke * 1300 * u + 60 * Math.sin(i + c.t)).toFixed(0)}" cy="${(700 - 400 * u).toFixed(0)}" r="${(40 + 120 * u).toFixed(0)}" fill="#8a7e76" opacity="${(0.5 * smoke * Math.min(1, u * 5) * (1 - u)).toFixed(3)}"/>`; }
  // the scribe's hand + reed pen
  const hx = 1200 + (late ? 0 : 60 * Math.sin(c.t * 4)) * (1 - stop), hy = 640 + (late ? -40 * stop : 0);
  s += limb(`M1900 1100 Q1500 900 ${hx + 30} ${hy + 20}`, 60, '#2f5a7a') + pole(hx - 40, hy - 120, hx + 10, hy + 10, '#6b4a2a') + `<g transform="translate(${hx} ${hy}) scale(2.4)">${hand(0, 0, '#c98f62')}</g>`;
  return L(c, 0.3, s);
};

// ---------- DELPHI ----------
function parnassus(c: ShotCtx): string {   // the Phaedriades cliffs above the sanctuary, cypresses, an eagle circling
  let s = skyGrad(c, 'dsky2', [[0, '#7fa8c8'], [0.6, '#cfe0e0'], [1, '#efe6cc']]);
  s += bg('M-200 760 L-200 160 Q200 90 420 200 Q600 100 800 180 Q1000 60 1240 190 Q1480 80 1700 200 Q1900 120 2120 180 L2120 760 Z', '#b9a48a', 5);
  for (let i = 0; i < 14; i++) s += `<path d="M${-100 + i * 160} ${200 + (i % 3) * 30} q${30 + (i % 4) * 10} 200 ${10 + (i % 2) * 30} 460" stroke="#8e7a62" stroke-width="6" fill="none" stroke-linecap="round"/>`;   // cliff faces
  const ex = wrap(300 + c.t * 40, W + 400) - 200, ey = 260 + 30 * Math.sin(c.t * 0.7);
  s += `<path d="M${ex - 30} ${ey} Q${ex - 14} ${ey - 16 + 6 * Math.sin(c.t * 3)} ${ex} ${ey} Q${ex + 14} ${ey - 16} ${ex + 30} ${ey}" stroke="${OUT}" stroke-width="5" fill="none" stroke-linecap="round"/>`;
  return s;
}
function cypress(x: number, y: number, k: number): string {
  return at(x, y, k, bg('M0 -260 Q34 -150 30 -20 Q0 0 -30 -20 Q-34 -150 0 -260 Z', '#3e5a34', 4) + sh('rect', { x: -5, y: -20, width: 10, height: 24 }, '#5a3a24'));
}
function doricTemple(t: number, k = 1): string {   // the 6th-century temple of Apollo: painted entablature, columns, steps
  let s = bg('M-560 0 L560 0 L540 -36 L-540 -36 Z', '#d9ccb0', 5) + bg('M-520 -36 L520 -36 L504 -66 L-504 -66 Z', '#e4d8bc', 5);
  for (let i = 0; i < 6; i++) { const x = -430 + i * 172; s += bg(`M${x - 36} -66 L${x + 36} -66 L${x + 30} -400 L${x - 30} -400 Z`, '#efe6d0', 5) + ln(`M${x - 12} -80 L${x - 10} -390 M${x + 12} -80 L${x + 10} -390`, 3, '#cbbd9c'); }
  s += bg('M-520 -400 L520 -400 L520 -470 L-520 -470 Z', '#e8dcc0', 5) + bg('M-520 -470 L520 -470 L520 -500 L-520 -500 Z', '#2f5a8a', 4);   // architrave + painted frieze band
  for (let i = 0; i < 14; i++) s += sh('rect', { x: -500 + i * 74, y: -470, width: 20, height: 70 }, '#9a3a2a');                                  // triglyphs, painted
  s += bg('M-560 -500 L0 -640 L560 -500 Z', '#e8dcc0', 5) + bg('M-470 -514 L0 -612 L470 -514 Z', '#b5452c', 3);                                  // pediment, painted
  s += bg('M-90 -66 L90 -66 L90 -330 L-90 -330 Z', '#2a1c14', 4);                                                                                   // the dark doorway
  const smoke = (0.5 + 0.5 * Math.sin(t * 1.3));
  s += `<circle cx="0" cy="-360" r="${(40 + 14 * smoke).toFixed(1)}" fill="#9a8e86" opacity=".45"/>`;
  return `<g transform="scale(${k})">${s}</g>`;
}
function messenger(t: number, seed: number, o: { kneel?: number; look?: number; branch?: number; expr?: any; to?: any; mix?: number; recoil?: number } = {}): string {
  // an Athenian envoy in himation: kneeling (kneel 1) or standing; raises an olive branch (branch 0..1)
  const skin = ['#d8a87c', '#cf9e72'][seed % 2], robe = ['#e6dcc6', '#c9b48a'][seed % 2];
  const kn = o.kneel ?? 1, br = o.branch ?? 0, rc = o.recoil ?? 0;
  let s = `<ellipse cx="0" cy="-4" rx="80" ry="12" fill="rgba(0,0,0,.18)"/>`;
  s += kn > 0.5
    ? bg('M-70 -4 Q-80 -110 -50 -170 L50 -170 Q80 -110 74 -4 Z', robe, 5)                       // kneeling: robe as a mound
    : bg('M-46 -238 Q0 -250 46 -238 Q58 -120 64 -8 L-64 -8 Q-58 -120 -46 -238 Z', robe, 5);
  const top = kn > 0.5 ? -170 : -238;
  const ax = 70 + 30 * br, ay = top + 30 - 160 * br;
  s += limb(`M40 ${top + 16} Q${70 + 20 * br} ${top - 20 - 60 * br} ${ax} ${ay}`, 18, robe) + hand(ax, ay, skin);
  if (br > 0.05) {                                                                                  // the olive branch
    s += `<path d="M${ax} ${ay} Q${ax + 30} ${ay - 60} ${ax + 20} ${ay - 130}" stroke="#5a3a24" stroke-width="6" fill="none" stroke-linecap="round" opacity="${Math.min(1, br * 3).toFixed(2)}"/>`;
    for (let l = 0; l < 6; l++) { const ly = ay - 30 - l * 18, lx = ax + 18 + (l % 2 ? 14 : -10); s += `<ellipse cx="${lx}" cy="${ly}" rx="14" ry="6" fill="#7a9a4a" stroke="${OUT}" stroke-width="2.5" transform="rotate(${l % 2 ? 30 : -30} ${lx} ${ly})" opacity="${Math.min(1, br * 3).toFixed(2)}"/>`; }
  }
  s += limb(`M-40 ${top + 16} Q-70 ${top + 60} -50 ${top + 110}`, 18, robe) + hand(-50, top + 114, skin);
  s += `<g transform="translate(${(-20 * rc).toFixed(1)} ${(top + 238 + breathe(t, seed) * -1.4 + 14 * (o.look ?? 0) * -1).toFixed(1)}) rotate(${(-10 * rc).toFixed(2)})">` +
    head(skin, o.expr ?? 'worried', { beard: '#3a2a1e', blink: blinkAt(t, seed + 3), extra: true, to: o.to, mix: o.mix }) +
    sh('path', { d: 'M-60 -300 Q-64 -362 0 -366 Q64 -362 60 -300 Q50 -334 0 -336 Q-50 -334 -60 -300 Z' }, '#3a2a1e') + '</g>';
  return s;
}
function adyton(c: ShotCtx, lamp = 1): string {   // the dark inner room: stone walls, the bronze tripod, smoke, one lamp
  const f = 0.92 + 0.08 * Math.sin(c.t * 11) * Math.sin(c.t * 6.7);
  let s = `<rect x="-300" y="-300" width="${W + 600}" height="${H + 600}" fill="#1c1612"/>`;
  const R = rng(17);                              // polygonal masonry: big irregular fitted stones (Delphi's walls)
  for (let r = 0; r < 6; r++) for (let i = 0; i < 9; i++) {
    const x = -160 + i * 250 + (r % 2) * 110 + R() * 30, y = -40 + r * 160 + R() * 20, w = 210 + R() * 60, h = 140 + R() * 30;
    const j = () => (R() - 0.5) * 40;
    s += `<path d="M${x + j()} ${y + j()} L${x + w * 0.55 + j()} ${y - 10 + j()} L${x + w + j()} ${y + 14 + j()} L${x + w - 10 + j()} ${y + h + j()} L${x + w * 0.4 + j()} ${y + h + 12 + j()} L${x - 8 + j()} ${y + h * 0.6 + j()} Z" fill="${['#2e241c', '#33281e', '#2a2119'][(r + i) % 3]}" stroke="#120d09" stroke-width="6" stroke-linejoin="round"/>`;
  }
  s += glow(c, 'lamp', 1500, 520, 700 * f * lamp, '#ffb35c', 0.55) + glow(c, 'cleft', 960, 900, 420, '#9fb39a', 0.25);   // lamp + the greenish breath of the cleft
  s += bg('M1470 560 L1530 560 L1520 600 L1480 600 Z', '#a8643a', 3) + `<path d="M1500 548 q8 -22 0 -40 q14 16 6 40 Z" fill="#ffd27a" stroke="#e8902a" stroke-width="2"/>`;
  s += bg('M-200 900 L2120 900 L2120 1300 L-200 1300 Z', '#2a2018', 4) + bg('M820 900 Q960 870 1100 900 Q960 930 820 900 Z', '#0c0a08', 3);   // floor + the cleft in the rock
  return s;
}
function smokeColumn(c: ShotCtx, x: number, y: number, strength = 1, swirl = 0, shape: 'none' | 'planks' | 'island' = 'none', reveal = 0): string {
  let s = '';
  for (let q = 0; q < 14; q++) {
    const u = (q / 14 + c.t * 0.05) % 1;
    const cx = x + (50 + 220 * swirl) * Math.sin(q * 1.7 + c.t * (0.6 + swirl)) * u, cy = y - 620 * u;
    s += `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${(40 + 150 * u).toFixed(1)}" fill="#8a8478" opacity="${(0.35 * strength * (1 - u) * Math.min(1, u * 5)).toFixed(3)}"/>`;
  }
  if (shape === 'planks' && reveal > 0) for (let i = 0; i < 6; i++) s += `<rect x="${x - 220 + i * 76}" y="${y - 520}" width="58" height="300" rx="8" fill="none" stroke="#d9c7a0" stroke-width="6" opacity="${(0.7 * reveal).toFixed(2)}"/>`;
  if (shape === 'island' && reveal > 0) s += `<path d="M${x - 300} ${y - 300} Q${x - 200} ${y - 420} ${x - 40} ${y - 400} Q${x + 120} ${y - 470} ${x + 300} ${y - 330} Q${x + 100} ${y - 280} ${x - 300} ${y - 300} Z" fill="none" stroke="#d9c7a0" stroke-width="7" opacity="${(0.75 * reveal).toFixed(2)}"/>`;
  return s;
}
function pythia(c: ShotCtx, o: { open?: number; point?: number; lean?: number; expr?: any; to?: any; mix?: number } = {}): string {
  // the Pythia: an older woman in white with a laurel wreath, seated high on the bronze tripod
  const skin = '#d9b08a', p = o.point ?? 0, lean = o.lean ?? 0;
  let s = ln('M-150 0 L-80 -170 M150 0 L80 -170 M0 6 L0 -170', 16, '#6a4a1a') + ln('M-150 0 L-80 -170 M150 0 L80 -170 M0 6 L0 -170', 7, '#c99a45');   // splayed tripod legs
  s += bg('M-150 -170 Q0 -110 150 -170 Q150 -220 0 -228 Q-150 -220 -150 -170 Z', '#b58a3a', 5) + ln('M-140 -196 Q0 -150 140 -196', 4, '#e2c070');      // the deep bronze bowl
  s += `<g transform="translate(0 70) rotate(${(8 * lean).toFixed(2)} 0 -260)">`;
  s += bg('M-72 -240 Q-98 -380 -58 -500 L58 -500 Q98 -380 78 -240 Z', '#efe8da', 5) + `<path d="M-40 -490 Q-10 -380 -50 -260" stroke="rgba(0,0,0,.12)" stroke-width="14" fill="none"/>` +
    ln('M-84 -330 Q0 -312 86 -330', 8, '#c99a45');                                                          // a gold sash at the waist
  s += `<g transform="translate(0 -70)">` + bg('M-110 -205 Q-150 -170 -130 -120 Q-100 -100 -70 -118 Q-40 -96 0 -116 Q40 -96 70 -118 Q100 -100 130 -120 Q150 -170 110 -205 Q0 -232 -110 -205 Z', '#efe8da', 5) +
    ln('M-80 -200 Q-90 -160 -84 -116 M-20 -206 Q-26 -160 -20 -112 M44 -204 Q50 -160 46 -114 M96 -196 Q104 -160 100 -120', 3, 'rgba(0,0,0,.14)') + '</g>';   // the lap drawn IN FRONT of the torso
  s += limb(`M44 -486 Q${110 + 60 * p} ${-470 - 60 * p} ${120 + 140 * p} ${-430 - 80 * p}`, 18, '#efe8da') + hand(120 + 140 * p, -430 - 80 * p, skin);           // pointing arm
  s += limb('M-44 -486 Q-90 -420 -60 -340', 18, '#efe8da') + `<g transform="translate(-58 -330)">${pole(0, -60, 0, 60, '#5a7a3a')}</g>` + hand(-60, -336, skin);   // a laurel sprig in hand
  const mouth = mouthAt(c.t, LIP, 'PYTHIA');
  s += `<g transform="translate(0 -250)">` + head(skin, o.expr ?? 'neutral', { blink: (o.open ?? 1) < 0.5 || blinkAt(c.t, 77), extra: true, to: o.to, mix: o.mix });
  s += sh('path', { d: 'M-64 -300 Q-70 -372 0 -380 Q70 -372 64 -300 L72 -200 Q44 -250 48 -300 Q0 -330 -48 -300 Q-44 -250 -72 -200 Z' }, '#9a9088');   // greying hair
  for (let i = 0; i < 9; i++) { const a = Math.PI * (0.15 + 0.7 * i / 8); s += `<ellipse cx="${(-70 * Math.cos(a)).toFixed(1)}" cy="${(-318 - 40 * Math.sin(a)).toFixed(1)}" rx="16" ry="7" fill="#6f8a44" stroke="${OUT}" stroke-width="2.5"/>`; }   // laurel wreath
  if (mouth && mouth !== 'closed') s += `<ellipse cx="0" cy="-252" rx="${mouth === 'wide' ? 13 : 9}" ry="${mouth === 'wide' ? 11 : 7}" fill="#5a2018" stroke="${OUT}" stroke-width="4"/>`;
  return s + '</g></g>';
}
const delphi_ext: SceneFn = (c) => {
  // EWS crane down: the mountain sanctuary on "Months"; two messengers kneel at the temple door on "knelt"
  const down = easeOutBack(bt(c, 1, 0.3, 0.8));
  const card_ = card(1440, 60, 420, 62, 'DELPHI · 481 BC', 27, tween(c.local, 0.6, 1.6, 0, 1));
  const ground = bg('M-200 820 Q900 780 2120 820 L2120 1300 L-200 1300 Z', '#c9b48a', 5) + ln('M-200 900 L2120 880', 6, 'rgba(0,0,0,.12)');
  const puff = easeInOut(bt(c, bi(c, 'Delphi'), 0.3, 1.2));
  const temple = at(980, 850, 0.95, doricTemple(c.t)) + Array.from({ length: 5 }, (_, i) => `<circle cx="${(980 + 30 * Math.sin(i * 2 + c.t)).toFixed(0)}" cy="${(560 - 160 * puff - i * 40).toFixed(0)}" r="${(30 + 50 * puff + i * 10).toFixed(0)}" fill="#a49a92" opacity="${(0.45 * puff * (1 - i * 0.15)).toFixed(3)}"/>`).join('');
  const men = at(900, 1010 + 40 * (1 - down), 0.7, messenger(c.t, 0, { kneel: down, look: 1 })) + at(1060, 1012 + 40 * (1 - down), 0.7, messenger(c.t, 1, { kneel: down, look: 1 }));
  return L(c, 0.05, parnassus(c)) + L(c, 0.5, cypress(260, 830, 1.2) + cypress(1700, 820, 1.4) + cypress(1820, 840, 1.0) + ground) + L(c, 0.8, temple) + L(c, 1, men) + card_;
};
const delphi_messengers: SceneFn = (c) => {
  // MS inside: the messengers look up on "question"; one clasps his hands on "survive"
  const up = easeInOut(bt(c, 0, 0.3, 0.7)), clasp = easeOutBack(bt(c, 1, 0.3, 0.6));
  const men = at(760, 1000, 1.5, messenger(c.t, 0, { kneel: 1, look: up, expr: 'worried' })) + at(1160, 1006, 1.5, messenger(c.t, 1, { kneel: 1, look: up, branch: 0, expr: 'worried', to: 'shocked', mix: 0.3 * clasp }));
  const hands = clasp > 0 ? `<g transform="translate(1250 ${(840 - 40 * clasp).toFixed(0)}) scale(1.5)" opacity="${Math.min(1, clasp).toFixed(2)}">${hand(0, 0, '#cf9e72')}${hand(16, -4, '#cf9e72')}</g>` : '';
  return L(c, 0.3, adyton(c)) + L(c, 0.7, smokeColumn(c, 960, 900, 0.6)) + L(c, 1, men + hands);
};
const delphi_pythia: SceneFn = (c) => {
  // MS low push-in: the smoke parts and the Pythia appears on her tripod on "priestess"; her eyes open on "hope"
  const part = easeInOut(bt(c, 0, 0.3, 1.0)), eyes = bt(c, 1, 0.2, 0.4);
  const veil = `<rect x="600" y="0" width="720" height="${H}" fill="#6f6a62" opacity="${(0.75 * (1 - part)).toFixed(3)}"/>`;
  return L(c, 0.3, adyton(c)) + L(c, 0.6, smokeColumn(c, 960, 900, 1)) + L(c, 1, at(960, 960, 1.3, pythia(c, { open: eyes > 0.5 ? 1 : 0, expr: 'stern' })) + veil);
};
const delphi_pythia_cu: SceneFn = (c) => {
  // CU of the Pythia. line 11: she points into the dark on "Flee", smoke whirls on "earth".
  // line 14: wooden planks form in the smoke on "wall", her stare on "taken".
  // line 16: an island forms in the smoke on "Salamis", the smoke darkens on "destroy".
  // line 132 (outro): the island in the smoke on "Salamis", her eyes close on "did".
  const ln_ = lineOf(c);
  const a0 = easeInOut(bt(c, 0, 0.3, 0.8)), a1 = easeInOut(bt(c, 1, 0.3, 0.8));
  let point = 0, swirl = 0, shape: 'none' | 'planks' | 'island' = 'none', reveal = 0, dark = 0, open = 1, expr: any = 'stern';
  if (ln_ === 12) { point = anticipate(bt(c, 0, 0.3, 1.1), 0.15); swirl = a1; }
  else if (ln_ === 15) { shape = 'planks'; reveal = a0; expr = 'stern'; }
  else if (ln_ === 17) { shape = 'island'; reveal = a0; dark = a1; }
  else { shape = 'island'; reveal = a0; open = 1 - a1; expr = 'neutral'; }
  const shade_ = `<rect x="-200" y="-200" width="${W + 400}" height="${H + 400}" fill="#0a0604" opacity="${(0.4 * dark).toFixed(3)}"/>`;
  return L(c, 0.3, adyton(c)) + L(c, 0.6, smokeColumn(c, 1380, 980, 1, swirl, shape, reveal)) +
    L(c, 1, at(700, 1900, 2.6, pythia(c, { point: Math.max(0, Math.min(1, point)), open, expr, to: ln_ === 15 ? 'shocked' : undefined, mix: ln_ === 15 ? 0.4 * a1 : 0 }))) + shade_;
};
const delphi_beg: SceneFn = (c) => {
  // MS high: the messengers recoil on "terrified", then raise olive branches on "olive"
  const rc = easeOutBack(bt(c, 0, 0.3, 0.6)), br = easeInOut(bt(c, 1, 0.3, 0.9));
  const men = at(760, 1000, 1.4, messenger(c.t, 0, { kneel: 1, recoil: rc * (1 - br * 0.6), branch: br, expr: 'shocked', to: 'worried', mix: br })) +
    at(1160, 1006, 1.4, messenger(c.t, 1, { kneel: 1, recoil: rc * (1 - br * 0.6), branch: br * 0.9, expr: 'shocked', to: 'worried', mix: br }));
  return L(c, 0.3, adyton(c)) + L(c, 0.6, smokeColumn(c, 1500, 900, 0.7)) + L(c, 1, men);
};
const delphi_riddle: SceneFn = (c) => {
  // MS: the Pythia leans forward on "riddle"; the lamp flares
  const lean = easeInOut(bt(c, 0, 0.3, 0.8));
  return L(c, 0.3, adyton(c, 1 + 0.3 * Math.sin(lean * Math.PI))) + L(c, 0.6, smokeColumn(c, 960, 900, 1, 0.3 * lean)) +
    L(c, 1, at(1100, 1000, 1.3, pythia(c, { lean, expr: 'neutral', to: 'stern', mix: lean })) + at(420, 1020, 1.1, messenger(c.t, 0, { kneel: 1, look: 1, branch: 1 })));
};
function openSea(c: ShotCtx, time: 'dawn' | 'dusk'): { sky: string; sea: string } {
  const sky = time === 'dawn' ? dawnSky(c, 330) : skyGrad(c, 'osky', [[0, '#4f3a6e'], [0.55, '#d77c56'], [1, '#f2b06a']]) + glow(c, 'osun', 1500, 520, 320, '#ffcf8a', 0.8);
  const sea = `<rect x="-200" y="560" width="${W + 400}" height="700" fill="${time === 'dawn' ? '#4f8aa6' : '#5a5a7e'}"/>` + waves(c.t, 41, 570, 1080, 160, time === 'dawn' ? '#dcf0f3' : '#d9b9b0', 30) +
    bg('M-200 560 L300 520 L520 545 L760 515 L900 560 Z', '#8a7a9a', 3);
  return { sky, sea };
}
const opensea_messengers: SceneFn = (c) => {
  // WS track at dusk: a small ship carries the messengers home on "sailed"; they brood at the rail on "riddle"
  const s0 = openSea(c, 'dusk'), brood = easeInOut(bt(c, 1, 0.3, 0.8));
  const ship = at(980 - c.local * 22, 820 + Math.sin(c.t * 1.4) * 6, 0.34, warship(c.t, 'greek', 0.6, 2));
  const men = at(980 - c.local * 22 - 40, 760 + Math.sin(c.t * 1.4) * 6 + 10 * brood, 0.42, messenger(c.t, 0, { kneel: 0, expr: 'worried', to: 'grief', mix: brood }));
  return L(c, 0.05, s0.sky) + L(c, 0.5, s0.sea) + L(c, 1, ship + men);
};

// =============================== CHAPTER 2 — Athens argues, the silver, the king comes (drawn for this film) ===============================
/** Beat progress by WORD (never by index). */
const bw = (c: ShotCtx, word: string, lead = 0.3, dur = 0.6) => bt(c, bi(c, word), lead, dur);
function noonSky(c: ShotCtx, name: string): string {
  return skyGrad(c, name, [[0, '#7fb0d0'], [0.6, '#cfe3e6'], [1, '#f3e7c8']]) + glow(c, name + 'sun', 1500, 200, 260, '#fff6d8', 0.9) +
    `<circle cx="1500" cy="200" r="52" fill="#fff6d8" stroke="#f0d08a" stroke-width="4"/>` + cloud(wrap(300 + c.t * 4, W + 400) - 200, 120, 1.1, '#fdf6ea') + cloud(wrap(1100 + c.t * 3, W + 400) - 200, 210, 0.8, '#fdf6ea');
}
/** The Acropolis of 480 BC: the rock, the archaic Old Temple of Athena (painted), small shrines, the thorn hedge. NO Parthenon. */
function acropolisRock(k = 1, hedge = 1, fire = 0, t = 0): string {
  let s = bg('M-520 0 Q-480 -150 -380 -210 Q-200 -250 0 -246 Q220 -250 380 -210 Q480 -150 520 0 Z', '#b59a74', 6);
  for (let i = 0; i < 9; i++) s += `<path d="M${-420 + i * 100} -40 q20 -80 ${10 + (i % 3) * 10} -170" stroke="#8e7656" stroke-width="5" fill="none" stroke-linecap="round"/>`;
  // the Old Temple of Athena (archaic, smaller than the later Parthenon) + two shrines
  s += bg('M-190 -246 L190 -246 L180 -262 L-180 -262 Z', '#ddd0b4', 4);
  for (let i = 0; i < 7; i++) s += bg(`M${-160 + i * 53} -262 L${-148 + i * 53} -262 L${-146 + i * 53} -370 L${-162 + i * 53} -370 Z`, '#efe4cc', 3);
  s += bg('M-180 -370 L180 -370 L180 -392 L-180 -392 Z', '#2f5a8a', 3) + bg('M-196 -392 L0 -450 L196 -392 Z', '#b5452c', 4);
  s += bg('M240 -246 L330 -246 L330 -300 L240 -300 Z', '#e4d8bc', 3) + bg('M232 -300 L285 -326 L338 -300 Z', '#9a3a2a', 3);
  s += bg('M-330 -246 L-250 -246 L-250 -290 L-330 -290 Z', '#e4d8bc', 3) + bg('M-338 -290 L-290 -312 L-242 -290 Z', '#9a3a2a', 3);
  if (hedge > 0) for (let i = 0; i < 22; i++) { const x = -470 + i * 44, y = -150 - 90 * Math.sin(Math.PI * (i / 21)); s += `<g opacity="${hedge.toFixed(2)}" transform="translate(${x} ${y.toFixed(0)})">${bg('M-26 0 Q-30 -30 -10 -34 Q0 -50 14 -36 Q30 -32 26 0 Z', '#5c6e34', 3)}<path d="M-14 -20 l-10 -6 M8 -28 l10 -8" stroke="${OUT}" stroke-width="2"/></g>`; }
  if (fire > 0) for (let q = 0; q < 12; q++) {                // flame tongues on the temple roof
    const fx = -176 + q * 32, fh = (70 + 60 * Math.abs(Math.sin(t * 5 + q * 1.9))) * fire;
    s += `<path d="M${fx - 16} -392 Q${fx - 8} ${(-392 - fh * 0.6).toFixed(0)} ${(fx + 6 * Math.sin(t * 6 + q)).toFixed(1)} ${(-392 - fh).toFixed(0)} Q${fx + 10} ${(-392 - fh * 0.5).toFixed(0)} ${fx + 16} -392 Z" fill="${q % 3 ? '#ff8a2a' : '#ffd25a'}" stroke="#c0451a" stroke-width="2" opacity="${(0.92 * fire).toFixed(2)}"/>`;
  }
  return `<g transform="scale(${k})">${s}</g>`;
}
function pnyxSet(c: ShotCtx): { sky: string; far: string; mid: string; ground: string } {
  const sky = noonSky(c, 'pnyxsky');
  const far = `<rect x="-200" y="560" width="${W + 400}" height="140" fill="#7fb3c4"/>` + waves(c.t, 61, 570, 690, 50, '#e3f1f4', 8) +
    farFleet(c.t, 18, 600, 9, 0.07) + bg('M-200 640 Q400 600 900 640 Q1400 610 2120 640 L2120 760 L-200 760 Z', '#c7b28c', 4);
  const mid = at(560, 690, 0.9, acropolisRock(1, 1));
  let ground = bg('M-200 760 Q900 700 2120 760 L2120 1300 L-200 1300 Z', '#b59a70', 5);
  for (let r = 0; r < 4; r++) ground += `<path d="M-200 ${800 + r * 70} Q900 ${760 + r * 70} 2120 ${800 + r * 70}" stroke="#8e7656" stroke-width="5" fill="none"/>`;   // the stone terraces of the assembly hill
  ground += bg('M860 860 L1060 860 L1050 800 L870 800 Z', '#cbb48c', 5) + bg('M900 800 L1020 800 L1014 770 L906 770 Z', '#d9c39a', 4);              // the speaker's platform (bema), cut from the rock
  return { sky, far, mid, ground };
}
function crowd(t: number, seed: number, n: number, y: number, k: number, x0: number, x1: number, o: { cheer?: number; fold?: number; split?: boolean } = {}): string {
  let s = '';
  for (let i = 0; i < n; i++) {
    const x = x0 + (i + 0.5) * (x1 - x0) / n, left = x < (x0 + x1) / 2;
    const arm = o.split ? (left ? (o.cheer ?? 0) * (0.6 + 0.4 * Math.sin(t * 6 + i)) : 0) : (o.cheer ?? 0) * (i % 3 === 0 ? 1 : 0.3);
    const ex: any = o.split && !left ? 'stern' : 'neutral';
    s += at(x, y + (i % 2) * 10, k, civilian(t, seed + i, { kind: i % 5 === 3 ? 'woman' : 'man', expr: ex, to: o.split && !left ? 'sly' : undefined, mix: o.split && !left ? (o.fold ?? 0) * 0.5 : 0, arm }));
  }
  return s;
}
function themSpeaker(c: ShotCtx, pose: any): string {
  const mouth = mouthAt(c.t, LIP, 'THEMISTOCLES');
  return themistocles.draw({ breath: breathe(c.t, 3), blink: blinkAt(c.t, 3), mouth, ...pose });
}
const athens_pnyx: SceneFn = (c) => {
  // the assembly on the hill. line 19: the crowd argues on "argued". line 28: the vote — hands go up on "vote".
  // line 141-ish (outro): they vote him out — hands up against him.
  const set = pnyxSet(c), ln_ = lineOf(c);
  const argue = easeInOut(bw(c, ln_ === 19 ? 'argued' : ln_ === 28 ? 'vote' : 'throw', 0.3, 0.8)), reveal = ln_ === 19 ? easeInOut(bw(c, 'wood', 0.3, 1.0)) : 1;
  const hands = ln_ === 28 || ln_ > 120 ? argue : 0, shout = ln_ === 19 ? argue : 0;
  let people = crowd(c.t, 3, 14, 900, 0.62, 80, 1840, { cheer: hands + 0.6 * shout * Math.abs(Math.sin(c.t * 5)) });
  people += crowd(c.t, 40, 11, 1010, 0.78, 40, 1880, { cheer: hands });
  const speaker = at(960, 790, 0.62, themSpeaker(c, { expr: ln_ > 120 ? 'grief' : 'stern', armR: ln_ === 28 ? { from: 'down', to: 'raise', k: easeInOut(bw(c, 'sea', 0.3, 0.6)) } : 'point' }));
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far) + L(c, 0.4, `<g opacity="${(0.4 + 0.6 * reveal).toFixed(2)}">${set.mid}</g>`) + L(c, 1, set.ground + speaker + people);
};
const acropolis_hedge: SceneFn = (c) => {
  // the old thorn hedge (reveal on "hedge"), the rock behind it (pull out on "Acropolis")
  const sky = noonSky(c, 'hedgesky'), show = easeInOut(bw(c, 'hedge', 0.3, 0.9)), rock = easeInOut(bw(c, 'Acropolis', 0.3, 0.9));
  const ground = bg('M-200 900 Q900 860 2120 900 L2120 1300 L-200 1300 Z', '#a8906a', 5) + pine(160, 920, 1.3) + pine(1780, 930, 1.1);
  return L(c, 0.05, sky) + L(c, 0.6, at(960, 940 + 40 * (1 - rock), 1.5 + 0.2 * (1 - rock), acropolisRock(1, show))) + L(c, 1, ground);
};
const athens_themistocles: SceneFn = (c) => {
  // Themistocles on the bema. line 21: steps out of the crowd ("one"), the name lands ("Themistocles").
  // line 23 (CU): points to the harbour on "ships". line 25: a knowing look on "sure", turns to the sea on "built".
  const set = pnyxSet(c), ln_ = lineOf(c);
  let hero = '';
  if (ln_ === 21) {
    const step = easeInOut(bw(c, 'one', 0.3, 0.9)), name = easeOutBack(bw(c, 'Themistocles', 0.3, 0.6));
    hero = crowd(c.t, 70, 8, 1080, 1.0, -100, 2020) + at(960, 1060 - 60 * step - 20 * name, 1.25, themSpeaker(c, { expr: 'neutral', exprTo: 'stern', exprMix: name, armR: 'down' }));
  } else if (ln_ === 23) {
    const pt = easeOutBack(bw(c, 'ships', 0.35, 0.8));
    hero = at(900, 1620, 2.6, themSpeaker(c, { expr: 'stern', armR: { from: 'down', to: 'point', k: Math.min(1, pt) } }));
  } else {
    const sure = bw(c, 'sure', 0.3, 0.5), turn = easeInOut(bw(c, 'built', 0.3, 0.9));
    hero = at(960 + 40 * turn, 1180, 1.6, `<g transform="scale(${(1 - 2 * turn).toFixed(3)} 1)">${themSpeaker(c, { expr: 'stern', exprTo: 'sly', exprMix: Math.min(1, sure * 2), armR: 'hip' })}</g>`);
  }
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far) + L(c, 0.45, set.mid) + L(c, 1, set.ground + hero);
};
const athens_crowd_split: SceneFn = (c) => {
  // half the crowd cheers on "admired"; the other half folds its arms on "trust"
  const set = pnyxSet(c), cheer = easeOutBack(bw(c, 'admired', 0.3, 0.6)), fold = easeInOut(bw(c, 'trust', 0.3, 0.7));
  const divider = `<path d="M960 820 L960 1300" stroke="rgba(0,0,0,.0)" stroke-width="2"/>`;
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far) + L(c, 0.45, set.mid) +
    L(c, 1, set.ground + divider + crowd(c.t, 90, 12, 980, 0.95, 40, 1880, { split: true, cheer: Math.min(1, cheer), fold }));
};
const athens_scroll_word: SceneFn = (c) => {
  // ECU: the oracle's words on a papyrus (shapes, no letters — r3); his finger finds ONE word ("word"), taps it twice ("cruel")
  const find = easeInOut(bw(c, 'word', 0.3, 0.8)), tap = bw(c, 'cruel', 0.2, 0.7), glowW = Math.max(find, bw(c, 'Salamis', 0.3, 0.6));
  let s = skyGrad(c, 'papbg', [[0, '#6a4a2e'], [1, '#3a2818']]) + bg('M220 200 L1700 180 L1720 920 L200 940 Z', '#e8d6a0', 7);
  const R = rng(31);
  for (let r = 0; r < 7; r++) for (let q = 0; q < 10; q++) {
    const x = 300 + q * 130 + R() * 20, y = 300 + r * 85, w = 60 + R() * 40, key = r === 3 && q === 5;
    s += `<path d="M${x.toFixed(0)} ${y} q${(w / 2).toFixed(0)} -12 ${w.toFixed(0)} 0 m8 -16 l0 20" stroke="${key ? '#9b2b22' : '#3a2414'}" stroke-width="${key ? 8 : 5}" fill="none" stroke-linecap="round"/>`;
    if (key) s += glow(c, 'wordglow', x + w / 2, y - 6, 90, '#ffe08a', 0.6 * glowW);
  }
  const fx = 900 + 50 * (1 - find), fy = 560 - 16 * Math.abs(Math.sin(tap * Math.PI * 2));
  s += limb(`M1400 1200 Q1100 900 ${fx + 30} ${fy + 40}`, 70, '#efe6d2') + `<g transform="translate(${fx} ${fy}) scale(2.6)">${hand(0, 0, '#d9a87c')}</g>`;
  return L(c, 0.3, s);
};
const laurium_mine: SceneFn = (c) => {
  // the silver mines: a miner lifts a shining lump on "silver"; citizens hold out their hands on "share";
  // the silver goes into a shipwright's hands instead on "warships"
  const sky = noonSky(c, 'lausky'), lift = easeOutBack(bw(c, 'silver', 0.3, 0.7)), share = easeInOut(bw(c, 'share', 0.3, 0.8)), give = easeInOut(bw(c, 'warships', 0.3, 1.0));
  let s = bg('M-200 700 Q300 560 700 640 Q1100 520 1500 620 Q1800 560 2120 640 L2120 1300 L-200 1300 Z', '#a88a62', 5);
  s += bg('M380 760 L560 760 L540 640 L400 640 Z', '#2a1c14', 5) + ln('M380 760 L400 640 M560 760 L540 640 M392 700 L548 700', 8, '#6a4a2a');                 // a shaft mouth with timber frame
  for (let i = 0; i < 4; i++) s += bg(`M${900 + i * 160} 820 L${1040 + i * 160} 820 L${1030 + i * 160} 860 L${910 + i * 160} 860 Z`, '#c9b48a', 4);           // the washing tables
  const lump = `<g transform="translate(${(470 + 600 * give).toFixed(0)} ${(700 - 160 * lift + 120 * give).toFixed(0)})"><path d="M-30 0 L-10 -26 L22 -20 L34 6 L6 22 Z" fill="#dfe6ee" stroke="${OUT}" stroke-width="4"/>${glow(c, 'silverglow', 0, 0, 90, '#ffffff', 0.7 * lift)}</g>`;
  const miner = at(470, 900, 1.2, civilian(c.t, 5, { kind: 'man', expr: 'neutral', to: 'sly', mix: lift, arm: Math.min(1, lift) }));
  let citizens = '';
  for (let i = 0; i < 4; i++) citizens += at(780 + i * 120, 960, 1.0, civilian(c.t, 20 + i, { kind: 'man', expr: 'neutral', arm: share * (1 - give) * 0.6, to: give > 0.5 ? 'worried' : undefined, mix: give }));
  const wright = at(1180, 960, 1.1, civilian(c.t, 33, { kind: 'man', expr: 'neutral', to: 'sly', mix: give, arm: give * 0.7 }));
  return L(c, 0.05, sky) + L(c, 1, s + miner + citizens + `<g opacity="${Math.min(1, give * 3).toFixed(2)}">${wright}</g>` + lump);
};
const shipyard: SceneFn = (c) => {
  // rows of new triremes on the slipways (reveal on "walls"); hammers fall on "wood"
  const sky = noonSky(c, 'yardsky'), show = easeInOut(bw(c, bi(c, 'walls') < 99 ? 'walls' : 'ships', 0.3, 1.1)), hammer = bw(c, 'wood', 0.2, 1.4);
  let s = `<rect x="-200" y="580" width="${W + 400}" height="200" fill="#7fb3c4"/>` + waves(c.t, 71, 590, 760, 60, '#e3f1f4', 10);
  s += bg('M-200 760 L2120 700 L2120 1300 L-200 1300 Z', '#b59a70', 5);
  for (let r = 0; r < 3; r++) for (let i = 0; i < 5; i++) {
    const x = 220 + i * 360 + r * 60, y = 820 + r * 130, k = 0.2 + r * 0.06, on = Math.max(0, Math.min(1, show * 5 - (i + r * 1.5) * 0.6));
    s += `<g opacity="${on.toFixed(2)}" transform="translate(${x} ${y}) scale(${k.toFixed(3)})">${warship(c.t, 'greek', 0, i + r)}${ln('M-380 30 L-380 160 M0 30 L0 160 M380 30 L380 160', 30, '#6a4a2a')}</g>`;   // on its slipway props
  }
  for (let i = 0; i < 4; i++) { const sw = Math.sin((hammer * 6 + i * 0.4) * Math.PI) * (hammer > 0 && hammer < 1 ? 1 : 0); s += at(380 + i * 380, 1120, 1.0, civilian(c.t, 50 + i, { kind: 'man', expr: 'neutral', arm: 0.5 + 0.5 * sw })); }
  return L(c, 0.05, sky) + L(c, 1, s);
};
function hellespontBridge(c: ShotCtx, march: number, sway = 0): string {
  // two bridges of ships lashed side by side, a plank road on top, the army marching over the sea
  let s = '';
  for (let b = 0; b < 2; b++) {
    const y = 720 + b * 170, k = 0.07 + b * 0.03;
    for (let i = 0; i < 26; i++) s += at(-100 + i * 82, y + Math.sin(c.t * 1.2 + i) * 2 + sway * Math.sin(c.t * 3 + i) * 4, k, warship(c.t, 'persian', 0, i));
    s += `<rect x="-200" y="${y - 22 - b * 2}" width="${W + 400}" height="${14 + b * 6}" fill="#8a6a44" stroke="${OUT}" stroke-width="3"/>`;
    const step = 30 + b * 14, off = wrap(c.t * 40 * march, step);
    for (let x = -step + off; x < W + step; x += step) s += at(x, y - 24 - b * 2, 0.06 + b * 0.03, guard(c.t, Math.floor(x) + b));
  }
  return s;
}
const hellespont: SceneFn = (c) => {
  // the army marching over a bridge of ships: reveal on "coming", ships lashed on "bridges", columns over the sea on "sea".
  // aftermath (line ~124): the same bridge, guards watching the sea nervously
  const ln_ = lineOf(c), dusk = ln_ > 100;
  const sky = dusk ? skyGrad(c, 'hdusk', [[0, '#4f3a6e'], [0.55, '#d77c56'], [1, '#f2b06a']]) : dawnSky(c, 330);
  const reveal = easeInOut(bw(c, dusk ? 'bridges' : 'coming', 0.3, 1.0)), march = dusk ? 0.15 : 1;
  const sea = `<rect x="-200" y="600" width="${W + 400}" height="700" fill="${dusk ? '#4a4a6e' : '#4f8aa6'}"/>` + waves(c.t, 81, 610, 1080, 140, '#dcf0f3', 20) +
    bg('M-200 610 L300 560 L600 590 L900 550 L1200 600 Z', '#9c86a3', 3) + bg('M1100 610 L1500 560 L1900 590 L2120 570 L2120 620 Z', '#a993ad', 3);
  const king = easeInOut(bw(c, 'Xerxes', 0.3, 1.0)), swayB = Math.sin(Math.min(1, bw(c, 'bridges', 0.3, 1.2)) * Math.PI), more = easeInOut(bw(c, 'sea', 0.3, 1.0));
  const royal = king > 0 ? at(-80 + 420 * king, 690, 0.32, parasol(c.t) + guard(c.t, 99)) : '';
  const column2 = more > 0 ? `<g opacity="${more.toFixed(2)}">${Array.from({ length: 24 }, (_, i) => at(wrap(i * 90 + c.t * 30, W + 200) - 100, 880, 0.1, guard(c.t, 200 + i))).join('')}</g>` : '';
  return L(c, 0.05, sky) + L(c, 0.3, sea) + L(c, 1, `<g opacity="${(0.3 + 0.7 * reveal).toFixed(2)}">${hellespontBridge(c, march, 3 * swayB)}</g>` + royal + column2);
};
const hellespont_close: SceneFn = (c) => {
  // MS low: the plank road sways under the feet on "stop"; endless feet on the planks on "walk"
  const sway = easeInOut(bw(c, 'stop', 0.3, 0.8)), walk = easeInOut(bw(c, 'walk', 0.3, 0.8));
  const sky = dawnSky(c, 330);
  let s = `<rect x="-200" y="700" width="${W + 400}" height="600" fill="#4f8aa6"/>` + waves(c.t, 91, 710, 1080, 90, '#dcf0f3', 30);
  const tilt = 2 * sway * Math.sin(c.t * 2.5);
  let deck = `<rect x="-300" y="760" width="${W + 600}" height="70" fill="#8a6a44" stroke="${OUT}" stroke-width="5"/>`;
  for (let i = 0; i < 30; i++) deck += `<path d="M${-300 + i * 90} 760 L${-300 + i * 90} 830" stroke="#5a3f24" stroke-width="5"/>`;
  const tw = c.beatT(bi(c, 'walk')) - 0.4, step = 230, off = wrap(c.t * 36 + 54 * Math.max(0, c.local - tw) * walk, step);   // speed changes never jump
  for (let x = -step + off; x < W + step; x += step) deck += at(x, 770, 0.9, guard(c.t, Math.floor(x)));
  s += `<g transform="rotate(${tilt.toFixed(2)} 960 790)">${deck}</g>`;
  return L(c, 0.05, sky) + L(c, 1, s);
};
const thermopylae: SceneFn = (c) => {
  // Thermopylae, drawn for this film: the red line in the pass ("Spartans"), shields lock ("held"), one spear left standing ("died")
  const sky = skyGrad(c, 'thsky', [[0, '#5a3a5e'], [0.55, '#d77c56'], [1, '#f2b06a']]) + glow(c, 'thsun', 1550, 520, 300, '#ffcf8a', 0.8);
  const line = easeInOut(bw(c, 'Spartans', 0.3, 0.8)), lock = easeOutBack(bw(c, 'held', 0.3, 0.6)), fall = easeInOut(bw(c, 'died', 0.3, 1.2));
  let s = `<rect x="-200" y="640" width="${W + 400}" height="300" fill="#6a6a8a"/>` + waves(c.t, 101, 650, 900, 60, '#d9c3c9', 10) +   // the gulf, behind the cliff
    bg('M-200 1300 L-200 200 Q300 260 420 520 Q520 760 760 860 L760 1300 Z', '#7a5a44', 6);
  s += bg('M-200 1300 L-200 960 Q700 900 2120 900 L2120 1300 Z', '#a07a52', 5) + bg('M780 905 L1700 890 L1700 850 L780 865 Z', '#c9b48a', 4);   // the ground across the pass + the old wall
  let men = '';
  for (let i = 0; i < 9; i++) {
    const gone = fall > (i + 1) / 10;
    if (gone) continue;
    men += at(820 + i * 95, 900 + 8 * (1 - line), 0.28, hopliteBody('#d8a87c', true) + aspis(56, -170, 78 * (0.9 + 0.1 * lock), undefined, 'lambda') + head('#d8a87c', 'stern', { extra: true }));
  }
  const spear = fall > 0.5 ? `<g opacity="${Math.min(1, (fall - 0.5) * 3).toFixed(2)}">${pole(1300, 640, 1300, 900, '#8b5a2b')}<path d="M1300 600 L1290 640 L1310 640 Z" fill="#bdbdbd" stroke="${OUT}" stroke-width="3"/></g>` : '';
  const rise = easeOutBack(bw(c, 'pass', 0.3, 0.6)), hit = bw(c, 'held', 0.3, 0.8);
  let spears = '';
  for (let i = 0; i < 9; i++) if (fall <= (i + 1) / 10) spears += pole(838 + i * 95, 860 - 60 * rise, 838 + i * 95, 890, '#8b5a2b');
  let wave = '';
  if (hit > 0 && hit < 1) for (let i = 0; i < 6; i++) { const x = 1900 - 520 * Math.sin(hit * Math.PI / 2) + 180 * Math.max(0, hit - 0.6) * 2.5 + i * 50; wave += at(x, 905 + (i % 2) * 6, 0.26, guard(c.t, 300 + i), 10 * Math.max(0, hit - 0.6)); }
  return L(c, 0.05, sky) + L(c, 1, s + `<g opacity="${line.toFixed(2)}">${spears}${men}</g>` + wave + spear);
};
const opensea_fleet_south: SceneFn = (c) => {
  // the Greek fleet turns south at dusk ("fleet"); Salamis rises ahead ("Salamis")
  const s0 = openSea(c, 'dusk'), turn = easeInOut(bw(c, 'fleet', 0.3, 1.0)), isle = easeInOut(bw(c, 'Salamis', 0.3, 1.0));
  let fleet = '';
  for (let i = 0; i < 10; i++) { const x = 300 + i * 150 + 60 * turn, y = 700 + (i % 3) * 60; fleet += at(x, y + Math.sin(c.t * 1.3 + i) * 4, 0.11 + (i % 3) * 0.02, `<g transform="scale(${(1 - 2 * turn).toFixed(3)} 1)">${warship(c.t, 'greek', 0.7, i)}</g>`); }
  const island = bg('M1300 600 Q1450 520 1600 560 Q1750 520 1900 590 L1900 610 L1300 610 Z', '#7a6a8a', 3);
  return L(c, 0.05, s0.sky) + L(c, 0.3, `<g opacity="${isle.toFixed(2)}">${island}</g>`) + L(c, 0.5, s0.sea) + L(c, 1, fleet);
};
const hellespont_army_road: SceneFn = (c) => {
  // the Persian army pours south ("largest"); Athens on the horizon ("Athens")
  const sky = skyGrad(c, 'rdsky', [[0, '#4f3a6e'], [0.55, '#d77c56'], [1, '#f2b06a']]), pour = easeInOut(bw(c, 'largest', 0.3, 1.2)), city = easeInOut(bw(c, 'Athens', 0.3, 1.0));
  let s = bg('M-200 640 Q900 600 2120 640 L2120 1300 L-200 1300 Z', '#9a7a52', 5) + `<path d="M-200 1200 Q700 900 1500 680" stroke="#c9b48a" stroke-width="120" fill="none"/>`;
  s += `<g opacity="${city.toFixed(2)}">${at(1560, 660, 0.25, acropolisRock(1, 0))}</g>`;
  for (let i = 0; i < 70; i++) { const u = ((i / 70) * pour + c.t * 0.01) % 1; const x = -200 + 1700 * u, y = 1200 - 520 * u + (i % 3) * 14; s += at(x, y, 0.05 + 0.25 * (1 - u), guard(c.t, i)); }
  return L(c, 0.05, sky) + L(c, 1, s);
};

// =============================== CHAPTER 3 — the city leaves, the Acropolis burns (drawn for this film) ===============================
function streetSet(c: ShotCtx, time: 'dawn' | 'noon'): string {   // an Athenian street: whitewashed houses, tiled roofs, an open door
  let s = time === 'dawn' ? dawnSky(c, 360) : noonSky(c, 'strsky');
  s += bg('M-200 760 L2120 760 L2120 1300 L-200 1300 Z', '#c9b48a', 5) + ln('M-200 820 L2120 800 M-200 900 L2120 880', 4, 'rgba(0,0,0,.08)');
  for (let i = 0; i < 6; i++) {
    const x = -120 + i * 360, h = 300 + (i % 3) * 40;
    s += bg(`M${x} 770 L${x + 320} 770 L${x + 320} ${770 - h} L${x} ${770 - h} Z`, ['#efe6d2', '#e6dcc4', '#f2ead8'][i % 3], 5) +
      bg(`M${x - 20} ${770 - h} L${x + 160} ${700 - h} L${x + 340} ${770 - h} Z`, '#b5674a', 5) +
      bg(`M${x + 130} 770 L${x + 190} 770 L${x + 190} 650 L${x + 130} 650 Z`, '#5a3a24', 4);
  }
  return s + at(1700, 690, 0.35, acropolisRock(1, 1));
}
const athens_streets_empty: SceneFn = (c) => {
  // line 34: a door swings open on "left"; the street is empty. line 38: Persian soldiers march in on "king", nobody there on "empty"
  const ln_ = lineOf(c), early = ln_ < 36;
  let s = streetSet(c, early ? 'dawn' : 'noon');
  if (early) {
    const door = easeInOut(bw(c, 'left', 0.3, 0.9)), ever = easeInOut(bw(c, 'ever', 0.3, 0.8));
    s += `<g transform="translate(850 770) scale(${(1 - 0.85 * door).toFixed(3)} 1)">${bg('M-60 0 L0 0 L0 -120 L-60 -120 Z', '#7a5234', 4)}</g>`;   // a door left swinging open
    s += at(1300 + 300 * ever, 940, 0.9, civilian(c.t, 11, { kind: 'woman', expr: 'grief', hold: 'bundle', look: -1 }));                          // the last family leaving
  } else {
    const inn = easeInOut(bw(c, 'king', 0.3, 1.2)), look = easeInOut(bw(c, 'empty', 0.3, 0.8));
    for (let i = 0; i < 6; i++) s += at(-200 + 700 * inn + i * 110, 960 + (i % 2) * 20, 0.75, guard(c.t, 400 + i), 6 * look * (i % 2 ? 1 : -1));
  }
  return L(c, 0.5, s);
};
function harbourSet(c: ShotCtx): string {
  let s = dawnSky(c, 360) + `<rect x="-200" y="600" width="${W + 400}" height="700" fill="#5f97ae"/>` + waves(c.t, 111, 610, 1080, 120, '#dcf0f3', 16);
  return s + bg('M-200 860 L800 860 L800 1300 L-200 1300 Z', '#c9b48a', 5) + ln('M-200 860 L800 860', 8, '#8e7656');    // the stone quay
}
function rowboat(t: number, seed: number, people = 3): string {
  let s = bg('M-160 0 Q0 30 160 0 L140 -40 L-140 -40 Z', '#7a5234', 5);
  for (let i = 0; i < people; i++) s += at(-90 + i * 80, -36, 0.32, civilian(t, seed + i, { kind: i % 2 ? 'woman' : 'child', expr: 'worried' }));
  s += ln(`M-120 -20 L-200 ${(30 + 14 * Math.sin(t * 4 + seed)).toFixed(0)} M120 -20 L200 ${(30 + 14 * Math.sin(t * 4 + seed)).toFixed(0)}`, 6, '#b58a56');
  return s;
}
const harbour_evac: SceneFn = (c) => {
  // families carry bundles to the boats ("carried"), women lift children aboard ("Women"), the boats push off ("rowed")
  const carry = easeInOut(bw(c, 'carried', 0.3, 1.0)), lift = easeOutBack(bw(c, 'Women', 0.3, 0.7)), row = easeInOut(bw(c, 'rowed', 0.3, 1.4));
  let s = harbourSet(c);
  for (let i = 0; i < 3; i++) s += at(1000 + i * 300 + 260 * row, 900 + i * 40 + Math.sin(c.t * 1.4 + i) * 4, 1.0, rowboat(c.t, 60 + i * 3));
  for (let i = 0; i < 5; i++) s += at(80 + i * 150 + 200 * carry, 1000 + (i % 2) * 20, 1.0, civilian(c.t, 80 + i, { kind: i % 2 ? 'woman' : 'man', expr: 'worried', hold: 'bundle', arm: i === 2 ? Math.min(1, lift) : 0 }));
  return L(c, 0.6, s);
};
const opensea_boats_salamis: SceneFn = (c) => {
  // EWS: boats cross to the island ("Salamis"); the coast is close ("just")
  const s0 = openSea(c, 'dawn'), cross = tween(c.local, 0, c.dur, 0, 1, (x) => x), near = easeInOut(bw(c, 'just', 0.3, 1.0));
  const isle = bg(`M${1200 - 200 * near} 600 Q1450 ${520 - 30 * near} 1650 560 Q1850 520 2120 580 L2120 610 L${1200 - 200 * near} 610 Z`, '#8a7a6a', 3);
  let boats = '';
  for (let i = 0; i < 14; i++) boats += at(200 + i * 110 + 500 * cross, 700 + (i % 4) * 70, 0.18 + (i % 4) * 0.05, rowboat(c.t, 120 + i, 2));
  return L(c, 0.05, s0.sky) + L(c, 0.3, isle) + L(c, 0.5, s0.sea) + L(c, 1, boats);
};
const salamis_shore_look: SceneFn = (c) => {
  // a girl turns to look back across the water ("see"); Athens across the strait ("homes")
  const look = easeInOut(bw(c, 'see', 0.3, 0.8)), city = easeInOut(bw(c, 'homes', 0.3, 1.0));
  const b = straitBase(c, 'dawn');
  const far = b.far + `<g opacity="${(0.4 + 0.6 * city).toFixed(2)}">${at(1300, 600, 0.3 + 0.08 * city, acropolisRock(1, 1))}</g>`;
  const shore = bg('M-200 860 Q400 820 960 840 Q1500 820 2120 850 L2120 1300 L-200 1300 Z', '#b59a70', 5);
  const girl = at(700, 1080, 1.6, `<g transform="scale(${(1 - 2 * look).toFixed(3)} 1)">${civilian(c.t, 9, { kind: 'child', expr: 'worried', to: 'grief', mix: city })}</g>`);
  return L(c, 0.05, b.sky) + L(c, 0.2, far) + L(c, 0.5, b.sea) + L(c, 1, shore + girl + at(420, 1060, 1.3, civilian(c.t, 12, { kind: 'woman', expr: 'grief' })));
};
function summit(c: ShotCtx, time: 'noon' | 'dusk' | 'night', fire = 0): string {   // on the Acropolis: the temple, the gate with its barricade
  let s = time === 'noon' ? noonSky(c, 'sumsky') : time === 'dusk' ? skyGrad(c, 'sumdusk', [[0, '#4f3a6e'], [0.55, '#d77c56'], [1, '#f2b06a']]) : skyGrad(c, 'sumnight', [[0, '#0b1430'], [1, '#26385c']]) + glow(c, 'summoon', 1650, 180, 220, '#cfe0ff', 0.5) + `<circle cx="1650" cy="180" r="38" fill="#eef3ff" stroke="#b8c8e8" stroke-width="3"/>` +
      Array.from({ length: 40 }, (_, i) => `<circle cx="${(i * 197) % W}" cy="${(i * 89) % 520}" r="${1 + (i % 3)}" fill="#e6eeff" opacity="${(0.4 + 0.5 * Math.abs(Math.sin(c.t * 2 + i))).toFixed(2)}"/>`).join('');
  s += bg('M-200 820 L2120 820 L2120 1300 L-200 1300 Z', '#b59a74', 5);
  s += at(1240, 830, 1.7, acropolisRock(1, 0, fire, c.t).replace('<g transform="scale(1)">', '<g transform="scale(1) translate(0 0)">')).replace(/M-520 0 Q-480 -150[^"]*Z/, 'M-520 0 L520 0 L520 -246 L-520 -246 Z');
  return s;
}
const acropolis_defenders: SceneFn = (c) => {
  // line 39: a few old men on the rock ("handful", "Acropolis"); they look at each other ("poor").
  // line 41 (CU): an old man touches the planks, hopeful ("wooden")
  const ln_ = lineOf(c);
  let s = summit(c, 'noon');
  if (ln_ === 39) {
    const appear = easeInOut(bw(c, 'handful', 0.3, 0.9)), glance = easeInOut(bw(c, 'poor', 0.3, 0.6));
    for (let i = 0; i < 4; i++) s += `<g opacity="${Math.min(1, appear * 2 - i * 0.3).toFixed(2)}">${at(380 + i * 170, 1080, 1.1, civilian(c.t, 140 + i, { kind: 'man', expr: 'worried', look: i % 2 ? glance : -glance }))}</g>`;
  } else {
    const touch = easeInOut(bw(c, 'wooden', 0.3, 0.9));
    s += barricade(0) + at(620, 1500, 2.4, civilian(c.t, 141, { kind: 'man', expr: 'worried', to: 'neutral', mix: touch, arm: 0.4 * touch }));
  }
  return L(c, 0.6, s);
};
function barricade(burnt: number): string {   // planks and timber across the gate (era: wooden barricade)
  let s = bg('M120 1080 L120 600 L320 600 L320 1080 Z', '#cbb894', 5) + bg('M720 1080 L720 600 L920 600 L920 1080 Z', '#cbb894', 5);   // gate posts
  for (let i = 0; i < 8; i++) s += `<rect x="${310}" y="${640 + i * 55}" width="420" height="44" rx="6" fill="${burnt ? '#2a1c14' : '#9a6a3a'}" stroke="${OUT}" stroke-width="4" transform="rotate(${(i % 2 ? 2 : -2)} 520 ${662 + i * 55})"/>`;
  return s;
}
const acropolis_barricade: SceneFn = (c) => {
  // planks are hammered across the gate ("barricade"); a beam drops into place ("timber")
  const ham = bw(c, 'barricade', 0.3, 1.2), beam = easeOutBack(bw(c, 'timber', 0.3, 0.6));
  let s = summit(c, 'noon') + barricade(0);
  s += `<rect x="290" y="${(400 + 210 * beam).toFixed(0)}" width="460" height="56" rx="8" fill="#7a5234" stroke="${OUT}" stroke-width="5"/>`;
  s += at(1050, 1080, 1.2, civilian(c.t, 150, { kind: 'man', expr: 'stern', arm: 0.5 + 0.5 * Math.sin(ham * Math.PI * 6) * (ham > 0 && ham < 1 ? 1 : 0) }));
  return L(c, 0.6, s);
};
const acropolis_cliff_climb: SceneFn = (c) => {
  // the gate is quiet ("gate"); Persians climb the steep back cliff ("climbed")
  const quiet = easeInOut(bw(c, 'gate', 0.3, 0.8)), climb = easeInOut(bw(c, 'climbed', 0.3, 2.0));
  let s = skyGrad(c, 'clsky', [[0, '#4f3a6e'], [0.55, '#d77c56'], [1, '#f2b06a']]);
  s += bg('M300 1300 L420 300 Q700 220 1100 260 L1300 1300 Z', '#9a7b5c', 6);
  for (let i = 0; i < 10; i++) s += `<path d="M${440 + i * 80} ${360 + (i % 3) * 40} q20 300 ${(i % 2 ? 30 : -20)} 900" stroke="#7a5f44" stroke-width="6" fill="none"/>`;
  for (let i = 0; i < 7; i++) { const u = Math.max(0, Math.min(1, climb * 1.4 - i * 0.08)); s += at(560 + i * 70, 1240 - 860 * u, 0.32, guard(c.t, 500 + i), -8); }
  s += `<g opacity="${(0.5 + 0.5 * quiet).toFixed(2)}">${at(1600, 700, 0.6, barricade(0))}</g>`;
  return L(c, 0.6, s);
};
const acropolis_burning: SceneFn = (c) => {
  // Persians on the summit ("killed"), fire takes the temple ("fire")
  const on = easeInOut(bw(c, 'killed', 0.3, 0.9)), fire = easeInOut(bw(c, 'fire', 0.3, 1.4));
  let s = skyGrad(c, 'bsky', [[0, '#3a2440'], [0.55, '#b5583a'], [1, '#e8904a']]) + `<rect x="-200" y="700" width="${W + 400}" height="600" fill="#6a5a52"/>`;
  s += at(960, 860, 1.1, acropolisRock(1, 0, fire, c.t));
  for (let q = 0; q < 12; q++) { const u = (q / 12 + c.t * 0.06) % 1; s += `<circle cx="${(820 + 260 * Math.sin(q) * u).toFixed(0)}" cy="${(420 - 400 * u).toFixed(0)}" r="${(40 + 110 * u).toFixed(0)}" fill="#3a3030" opacity="${(0.5 * fire * (1 - u)).toFixed(3)}"/>`; }
  s += glow(c, 'blaze', 960, 420, 520 * fire, '#ffb04a', 0.8 * fire);
  for (let q = 0; q < 14; q++) { const fx = 790 + q * 26, fh = (120 + 90 * Math.abs(Math.sin(c.t * 5 + q * 1.7))) * fire; s += `<path d="M${fx - 22} 470 Q${fx - 10} ${(470 - fh * 0.6).toFixed(0)} ${(fx + 8 * Math.sin(c.t * 6 + q)).toFixed(1)} ${(470 - fh).toFixed(0)} Q${fx + 14} ${(470 - fh * 0.5).toFixed(0)} ${fx + 22} 470 Z" fill="${q % 3 ? '#ff8a2a' : '#ffd25a'}" stroke="#c0451a" stroke-width="2" opacity="${(0.9 * fire).toFixed(2)}"/>`; }
  for (let i = 0; i < 6; i++) s += `<g opacity="${on.toFixed(2)}">${at(700 + i * 90, 600, 0.18, guard(c.t, 600 + i))}</g>`;
  return L(c, 0.6, s);
};
const acropolis_temple_fire: SceneFn = (c) => {
  // the old temple of Athena in flames ("temples"); a roof beam falls ("burned")
  const glowF = easeInOut(bw(c, 'temples', 0.3, 0.9)), drop = easeInOut(bw(c, 'burned', 0.3, 0.8));
  let s = skyGrad(c, 'tfsky', [[0, '#2a1a24'], [1, '#b5583a']]);
  s += at(960, 1180, 2.6, acropolisRock(1, 0, 0.6 + 0.4 * glowF, c.t));
  s += `<rect x="760" y="${(260 + 600 * drop).toFixed(0)}" width="420" height="40" rx="6" fill="#3a2414" stroke="${OUT}" stroke-width="5" transform="rotate(${(25 * drop).toFixed(1)} 970 ${(280 + 600 * drop).toFixed(0)})"/>`;
  return L(c, 0.6, s) + `<rect width="${W}" height="${H}" fill="#ff7a2a" opacity="${(0.12 * glowF).toFixed(3)}"/>`;
};
const acropolis_barricade_burnt: SceneFn = (c) => {
  // the charred planks ("barricade"); smoke drifts ("else"). Outro (line ~132): the old hedge + the burnt barricade
  const show = easeInOut(bw(c, 'barricade', 0.3, 0.9)), drift = easeInOut(bw(c, bi(c, 'else') < 99 ? 'else' : 'hedge', 0.3, 1.2));
  let s = summit(c, 'night') + barricade(1);
  for (let q = 0; q < 8; q++) { const u = (q / 8 + c.t * 0.05) % 1; s += `<circle cx="${(520 + 120 * Math.sin(q + c.t) * u + 300 * drift * u).toFixed(0)}" cy="${(700 - 500 * u).toFixed(0)}" r="${(30 + 90 * u).toFixed(0)}" fill="#6a6260" opacity="${(0.45 * (1 - u)).toFixed(3)}"/>`; }
  return L(c, 0.6, `<g opacity="${(0.4 + 0.6 * show).toFixed(2)}">${s}</g>`);
};
const salamis_shore_smoke: SceneFn = (c) => {
  // families on the shore ("families") watch the smoke rise over the far city ("smoke")
  const fam = easeInOut(bw(c, 'families', 0.3, 0.8)), smoke = easeInOut(bw(c, 'smoke', 0.3, 1.4));
  const sky = skyGrad(c, 'sssky', [[0, '#1a1a36'], [0.6, '#4a3a5a'], [1, '#8a5a4a']]);
  let far = `<rect x="-200" y="600" width="${W + 400}" height="300" fill="#2e3a58"/>` + at(1300, 620, 0.3, acropolisRock(1, 0, 0.5, c.t));
  for (let q = 0; q < 10; q++) { const u = (q / 10 + c.t * 0.05) % 1; far += `<circle cx="${(1300 + 80 * Math.sin(q) * u).toFixed(0)}" cy="${(520 - 380 * u).toFixed(0)}" r="${(20 + 80 * u).toFixed(0)}" fill="#4a4040" opacity="${(0.55 * smoke * (1 - u)).toFixed(3)}"/>`; }
  let people = bg('M-200 880 Q960 840 2120 880 L2120 1300 L-200 1300 Z', '#4a3e34', 5);
  for (let i = 0; i < 6; i++) people += at(200 + i * 160, 1080 - 20 * fam * (i % 2), 1.1, civilian(c.t, 170 + i, { kind: i % 3 === 1 ? 'woman' : i % 3 === 2 ? 'child' : 'man', expr: 'grief', look: 1 }));
  return L(c, 0.05, sky) + L(c, 0.3, far) + L(c, 1, people);
};
const road_rider: SceneFn = (c) => {
  // a horseman gallops east ("rider"); dust behind him ("fallen"). Aftermath variant: the king's column heads home.
  const ln_ = lineOf(c);
  const sky = dawnSky(c, 360);
  let s = bg('M-200 700 Q900 660 2120 700 L2120 1300 L-200 1300 Z', '#b59a70', 5) + `<path d="M-200 960 Q900 900 2120 940" stroke="#d9c39a" stroke-width="110" fill="none"/>`;
  if (ln_ < 60) {
    const go = tween(c.local, c.beatT(bi(c, 'rider')) - 0.3, c.dur, 0, 1, (x) => x), dust = easeInOut(bw(c, 'fallen', 0.3, 1.0));
    const x = -100 + 1900 * go, gal = Math.sin(c.t * 14);
    const horse = bg('M-110 -70 Q-120 -110 -60 -116 L60 -112 Q110 -110 120 -80 L176 -150 Q196 -172 214 -150 L226 -120 Q206 -116 186 -128 L140 -72 Q130 -40 90 -40 L-90 -40 Q-130 -40 -110 -70 Z', '#6a4428', 5) +
      `<path d="M-110 -80 Q-170 -70 -180 -20" stroke="#3a2414" stroke-width="14" fill="none" stroke-linecap="round"/>` + `<path d="M150 -130 Q140 -150 170 -168" stroke="#3a2414" stroke-width="10" fill="none"/>` +   // tail + mane
      ln(`M-80 -44 L${-110 + 30 * gal} 30 M-40 -44 L${-20 - 30 * gal} 30 M60 -44 L${40 + 30 * gal} 30 M100 -44 L${130 - 30 * gal} 30`, 14, '#5a3a24');
    s += at(x, 930, 0.9, horse + at(0, -110, 0.42, guard(c.t, 700)));
    for (let q = 0; q < 6; q++) s += `<circle cx="${(x - 160 - q * 60).toFixed(0)}" cy="${(940 - q * 8).toFixed(0)}" r="${(20 + q * 12) * (0.5 + dust)}" fill="#d9c3a0" opacity="${(0.5 * (1 - q / 6)).toFixed(2)}"/>`;
  } else {
    const turn = easeInOut(bw(c, 'trick', 0.3, 1.2));
    for (let i = 0; i < 30; i++) s += at(200 + i * 55 - 300 * turn, 930 - i * 4, 0.22 - i * 0.004, parasol(c.t).repeat(i === 6 ? 1 : 0) + guard(c.t, 800 + i));
  }
  return L(c, 0.05, sky) + L(c, 1, s);
};

// =============================== RICH PASS — bird's-eye establishing shots (owner 2026-11-21) ===============================
/** Athens from a high view: the city packed with houses, the Acropolis (480 BC temple, NO Parthenon), the agora with its
 *  colonnade, roads, olives and cypresses, the old wall, the harbour + ships far away, and the assembly on the Pnyx
 *  (a dense crowd arguing around the speaker's stone). act: 0..1 how hard the crowd argues / votes. */
function athensBird(c: ShotCtx, o: { argue?: number; vote?: number; reveal?: number; focus?: number; zoom?: number; cx?: number; cy?: number } = {}): string {
  const t = c.t, argue = o.argue ?? 0, vote = o.vote ?? 0;
  const R = rng(4242);
  // sky band + distant hills + the sea with the harbour and ships (the top of the frame is far away)
  let g = skyGrad(c, 'abSky', [[0, '#9cc4dc'], [1, '#e8eedf']]).replace(`height="${H + 600}"`, 'height="480"');
  g += poly2([[-200, 150], [200, 96], [520, 128], [860, 84], [1200, 120], [1560, 80], [2120, 118], [2120, 190], [-200, 190]], '#a7a0b8');
  g += seaTop(c.pid('abSea'), -200, 150, 2120, 250, t, '#6fa6ba', 3);
  for (let i = 0; i < 9; i++) g += shipTop(1250 + i * 70, 205 + (i % 3) * 14, 0.22, 'greek', t, 0.3, i);                 // the fleet at Phaleron
  g += poly2([[-200, 240], [2120, 228], [2120, 1300], [-200, 1300]], '#cdb98e');                                         // the plain of Attica
  for (let i = 0; i < 40; i++) g += `<ellipse cx="${(R() * 2000).toFixed(0)}" cy="${(260 + R() * 900).toFixed(0)}" rx="${(60 + R() * 140).toFixed(0)}" ry="${(14 + R() * 30).toFixed(0)}" fill="${['#bfb27a', '#d6c49a', '#b9b07c'][i % 3]}" opacity=".55"/>`;
  // fields + olive groves far off (left), the old city wall around the town
  for (let i = 0; i < 6; i++) { const x = -120 + i * 150, y = 262 + (i % 2) * 22; g += field([[x, y], [x + 140, y - 6], [x + 150, y + 30], [x + 6, y + 36]], ['#b8c27a', '#c9b97a', '#a8b46a'][i % 3], 5, i % 3 === 2); }
  for (let i = 0; i < 26; i++) g += tree(40 + R() * 1800, 300 + R() * 40, 0.55, 'olive', i);
  g += wall(-200, 360, 700, 336, 0.7) + wall(700, 336, 1900, 352, 0.7) + wall(1900, 352, 2120, 380, 0.7);
  // the town: rows of houses, smaller further away; a main road (the Panathenaic Way) toward the Acropolis
  const rows: string[] = [];
  for (let r = 0; r < 9; r++) {
    const y0 = 400 + r * 78, s = 0.42 + r * 0.075;
    let row = '';
    let x = -80 + R() * 60, n = 0;
    for (let i = 0; i < 40 && x < 2100; i++) {
      const y = y0 + (R() - 0.5) * 14 * s;
      if (n >= 3 + Math.floor(R() * 3)) { x += (34 + R() * 40) * s; n = 0; }            // an alley between blocks
      const big = R() > 0.86, w = (big ? 150 : 80 + R() * 40) * s;
      x += w / 2;
      const inAcro = Math.hypot((x - 1240) / 1.6, y - 470) < 200, inAgora = x > 360 && x < 840 && y > 510 && y < 710, inPnyx = x < 800 && y > 750;
      if (!(inAcro || inAgora || inPnyx || x > 2060)) {
        row += house(x, y, s, r * 31 + i, { w: w / s, flat: R() > 0.82, court: big || R() > 0.75 });
        if (big || R() > 0.8) row += tree(x + w / 2 + 18 * s, y - 4, s * 1.1, R() > 0.5 ? 'cypress' : 'olive', i + r);
      }
      x += w / 2 + 6 * s; n++;
    }
    rows.push(row);
  }
  // the Acropolis: the rock, the old temple of Athena, two shrines, the thorn hedge
  const acro = poly2([[930, 640], [960, 560], [1540, 560], [1580, 650], [1500, 668], [1000, 664]], '#9a7f5c') +       // the cliff faces
    Array.from({ length: 12 }, (_, i) => `<path d="M${970 + i * 50} 566 q${(i % 2 ? 6 : -4)} 40 ${(i % 3) * 4} 92" stroke="#7a6248" stroke-width="3" fill="none"/>`).join('') +
    poly2([[930, 640], [880, 700], [940, 706], [990, 640]], '#b59a74') +                                                         // the ramp up the west side
    poly2([[960, 560], [1000, 470], [1120, 420], [1360, 412], [1480, 450], [1540, 560]], '#c4a982') +
    Array.from({ length: 8 }, (_, i) => `<path d="M${990 + i * 68} 548 q8 -50 ${4 + (i % 3) * 6} -100" stroke="#8e7656" stroke-width="3" fill="none" stroke-linecap="round"/>`).join('') +
    templeTop(1250, 470, 0.62) + house(1090, 470, 0.4, 7, { h: 26, w: 70 }) + house(1420, 468, 0.4, 9, { h: 26, w: 70 }) +
    Array.from({ length: 16 }, (_, i) => tree(1000 + i * 34, 520 + 22 * Math.sin(i / 15 * Math.PI) * -1, 0.5, 'shrub', i)).join('');
  // the agora: an open square, a long colonnade (stoa), stalls, people walking and carrying
  let agora = poly2([[380, 700], [820, 692], [800, 520], [400, 528]], '#dccb9e');
  agora += `<g>${poly2([[420, 560], [780, 552], [780, 534], [420, 542]], '#e8dcc0')}</g>`;
  for (let i = 0; i < 12; i++) agora += poly2([[430 + i * 29, 562], [436 + i * 29, 562], [436 + i * 29, 590], [430 + i * 29, 590]], '#f3ebd6');   // stoa columns
  agora += poly2([[420, 596], [780, 588], [780, 600], [420, 608]], '#cbbd9c');
  for (let i = 0; i < 5; i++) agora += poly2([[470 + i * 70, 650], [520 + i * 70, 648], [520 + i * 70, 668], [470 + i * 70, 670]], ['#b5452c', '#2f5a8a', '#d9b443'][i % 3]);   // market awnings
  for (let i = 0; i < 26; i++) agora += tiny(400 + R() * 400, 610 + R() * 80, 0.8, i, (['walk', 'carry', 'talk', 'stand'] as const)[i % 4], t, { flip: i % 2 === 0 });
  const road_ = road('M300 1100 Q600 900 760 720 Q860 640 930 650', 30) + road('M-200 730 Q900 700 2120 740', 18) + road('M1000 1300 Q1100 950 1080 680', 18);   // streets (drawn UNDER the houses, around the rock)
  // the Pnyx: a semicircle of terraces, the speaker's stone, and the assembly — a dense crowd
  let pnyx = poly2([[-200, 1300], [-200, 820], [200, 760], [620, 780], [860, 900], [900, 1300]], '#c4ad80');
  for (let r = 0; r < 4; r++) pnyx += `<path d="M-120 ${880 + r * 80} Q330 ${790 + r * 80} 780 ${920 + r * 70}" stroke="#a08a62" stroke-width="3" fill="none"/>`;
  pnyx += poly2([[300, 830], [380, 828], [384, 812], [304, 814]], '#d9c39a');                                            // the bema
  pnyx += (o.zoom ?? 1) > 1.5 ? at(342, 812, 0.17, themSpeaker(c, { expr: 'stern', armR: 'point' })) : tiny(342, 812, 1.25, 77, argue > 0.2 ? 'point' : 'talk', t, { robe: '#f2ead8' });   // the speaker (Themistocles up close)
  for (let i = 0; i < 150; i++) {
    const a = Math.PI * (0.05 + 0.9 * R()), rr = 120 + R() * 360, x = 340 + Math.cos(a) * rr * 1.35, y = 830 + Math.sin(a) * rr * 0.55;
    if (y < 845) continue;
    const loud = argue * (i % 3 === 0 ? 1 : 0.4), hands = vote > 0.1 && i % 4 !== 0;
    const ss = 0.9 + (y - 830) / 600, det = (o.zoom ?? 1) > 1.5;
    pnyx += det ? at(x, y, 0.13 * ss, civilian(t, 100 + i, { kind: i % 5 === 3 ? 'woman' : 'man', expr: (['stern', 'worried', 'neutral', 'sly'] as const)[i % 4], arm: hands ? 0.8 + 0.2 * Math.sin(t * 4 + i) : loud * 0.5 }))
      : tiny(x, y, ss, 100 + i, hands ? 'point' : loud > 0.5 ? (i % 2 ? 'point' : 'talk') : (i % 5 ? 'stand' : 'talk'), t, { flip: x > 342 });
  }
  const reveal = o.reveal ?? 1;
  // one layer for the whole town (roads first, then far -> near), so a camera move never slides streets off the houses
  const town = road_ + rows.slice(0, 2).join('') + acro + rows.slice(2, 4).join('') + agora + rows.slice(4).join('');
  const z = o.zoom ?? 1, zx = o.cx ?? 960, zy = o.cy ?? 540, zt = (svg: string) => z === 1 ? svg : `<g transform="translate(960 540) scale(${z}) translate(${-zx} ${-zy})">${svg}</g>`;
  return L(c, 0.05, zt(g)) + L(c, 0.7, zt(town)) + L(c, 0.85, zt(`<g opacity="${(0.6 + 0.4 * reveal).toFixed(2)}">${pnyx}</g>`));
}
function poly2(pts: number[][], fill: string, w = 2.2): string {
  return `<path d="M${pts.map((p) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' L')} Z" fill="${fill}" stroke="${OUT}" stroke-width="${w}" stroke-linejoin="round"/>`;
}
const athens_bird: SceneFn = (c) => {
  // line 19: the whole city argues ("argued"); line 28: the assembly votes ("vote"); outro: they vote him out ("throw")
  const ln_ = lineOf(c);
  const argue = easeInOut(bw(c, ln_ === 19 ? 'argued' : 'vote', 0.3, 0.9)), vote = ln_ === 19 ? 0 : easeOutBack(bw(c, ln_ === 28 ? 'vote' : 'throw', 0.3, 0.7));
  const close = ln_ === 28;                                   // the vote: a CLOSE bird's-eye on the assembly (people big, faces readable)
  return athensBird(c, { argue, vote: Math.min(1, vote), reveal: ln_ === 19 ? easeInOut(bw(c, 'wood', 0.3, 1.0)) : 1, zoom: close ? 2.6 : 1, cx: 380, cy: 900 });
};

// ---------- bird's-eye: THE STRAIT OF SALAMIS ----------
/** The strait from high above: Salamis (top-left) with its town and the Greek fleet on the beach, the narrow channel running
 *  diagonally, the islet of Psyttaleia, the Attic shore (bottom-right) with the slopes of Aigaleos and the Persian camp.
 *  persian = 0..1 how much of the Persian fleet is in view; greek = 0..1 how visible the Greek fleet is; mist 0..1. */
function straitBird(c: ShotCtx, o: { persian?: number; greek?: number; mist?: number; lurch?: number; night?: boolean; zoom?: number; cx?: number; cy?: number } = {}): string {
  const t = c.t, R = rng(901), per = o.persian ?? 0, gre = o.greek ?? 1, z = o.zoom ?? 1;
  let g = (o.night ? skyGrad(c, 'sbN', [[0, '#0b1430'], [1, '#26385c']]) : skyGrad(c, 'sbS', [[0, '#e8a074'], [1, '#fde8c2']])).replace(`height="${H + 600}"`, 'height="760"');
  g += poly2([[-200, 120], [300, 70], [700, 100], [1100, 60], [1600, 96], [2120, 70], [2120, 160], [-200, 160]], o.night ? '#2a3050' : '#b7a2b8');   // far mountains
  g += seaTop(c.pid('sbSea'), -200, 150, 2120, 1300, t, o.night ? '#24385a' : '#4f8aa6', 9);
  // Salamis island: a long shore from the top-left, a beach strip, its town and families
  let sal = poly2([[-200, 150], [900, 150], [980, 230], [860, 330], [640, 420], [380, 500], [120, 560], [-200, 600]], o.night ? '#4a4a40' : '#b59a70');
  sal += `<path d="M900 150 Q980 230 860 330 Q640 420 380 500 Q120 560 -200 600" stroke="${o.night ? '#6a6a5a' : '#e2d2a8'}" stroke-width="16" fill="none"/>`;   // the beach
  sal += `<path d="M900 150 Q980 230 860 330 Q640 420 380 500 Q120 560 -200 600" stroke="#9ccad6" stroke-width="60" fill="none" opacity=".45" transform="translate(16 22)"/>`;   // shallows
  for (let i = 0; i < 46; i++) { const u = R(), v = R(); const x = -150 + 1000 * u - 200 * v, y = 200 + 260 * v + 120 * u * (1 - v); if (y > 540 - 400 * u) continue; sal += house(x, y, 0.36, 600 + i); }
  for (let i = 0; i < 60; i++) { const x = -180 + R() * 1060, y = 170 + R() * 330; if (y > 560 - 420 * ((x + 200) / 1100)) continue; sal += tree(x, y, 0.55, R() > 0.6 ? 'pine' : 'olive', i); }
  for (let i = 0; i < 40; i++) { const u = R(); sal += tiny(-150 + 1000 * u, 560 - 420 * u + R() * 30, 0.7, 700 + i, (['stand', 'walk', 'carry', 'talk'] as const)[i % 4], t); }   // the families on the shore
  let gf = '';
  for (let r = 0; r < 2; r++) for (let i = 0; i < 24; i++) { const u = i / 23; gf += shipTop(-140 + 1000 * u + r * 40, 600 - 420 * u + 44 + r * 46, 0.5, 'greek', t, 0.05, i + r * 30); }   // the Greek fleet along the beach
  // Psyttaleia + the Attic shore with Aigaleos and the Persian camp
  const shoreY = (x: number) => 380 + (2120 - x) * 0.66;                       // the Attic shoreline (diagonal)
  let att = poly2([[2120, 380], [1400, 855], [900, 1185], [720, 1300], [2120, 1300]], o.night ? '#3a342c' : '#a5835f');
  att += `<path d="M2120 380 L1400 855 L900 1185 L720 1300" stroke="${o.night ? '#5a5048' : '#e2d2a8'}" stroke-width="16" fill="none"/>` +
    `<path d="M2120 380 L1400 855 L900 1185 L720 1300" stroke="#9ccad6" stroke-width="50" fill="none" opacity=".4" transform="translate(-18 -14)"/>`;   // beach + shallows
  for (let i = 0; i < 160; i++) { const x = 800 + R() * 1320, y = 420 + R() * 880; if (y < shoreY(x) + 40) continue; att += `<path d="M${x.toFixed(0)} ${y.toFixed(0)} l-14 0 l14 -18 l14 18 Z" fill="${['#e9e0c8', '#d9c39a', '#b5452c', '#e2d6b4'][i % 4]}" stroke="${OUT}" stroke-width="1.6"/>`; if (i % 5 === 0) att += tiny(x + 18, y + 2, 0.7, 960 + i, (['walk', 'stand', 'talk'] as const)[i % 3], t, { spear: i % 2 === 0, robe: '#b5793a' }); }   // the camp: tents + soldiers
  for (let i = 0; i < 40; i++) { const x = 900 + R() * 1220, y = 460 + R() * 840; if (y < shoreY(x) + 30) continue; att += tree(x, y, 0.75, R() > 0.5 ? 'pine' : 'olive', 40 + i); }
  att += poly2([[1760, 800], [1820, 750], [1890, 800]], '#e2b23f') + tiny(1825, 790, 1.4, 950, 'sit', t, { robe: '#5b2a6e', hat: '#e2b23f' });   // the throne on the slope of Aigaleos
  const psy = `<path d="M1450 330 Q1460 282 1520 274 Q1580 260 1630 284 Q1680 310 1664 350 Q1640 386 1570 388 Q1490 390 1460 366 Q1440 350 1450 330 Z" fill="${o.night ? '#4a4a40' : '#9a8a6a'}" stroke="${OUT}" stroke-width="2.2"/>` +
    `<path d="M1450 330 Q1460 282 1520 274 Q1580 260 1630 284 Q1680 310 1664 350 Q1640 386 1570 388 Q1490 390 1460 366 Q1440 350 1450 330 Z" fill="none" stroke="#9ccad6" stroke-width="14" opacity=".5" transform="translate(6 8)"/>` +
    tree(1530, 320, 0.6, 'shrub', 3) + tree(1580, 338, 0.5, 'shrub', 4) + tree(1620, 310, 0.55, 'shrub', 5);   // Psyttaleia, a rocky islet
  let pf = '';
  const n = Math.round(72 * per);
  for (let i = 0; i < n; i++) { const row = (i % 4) - 1.5, k = Math.floor(i / 4), u = k / 18 + 0.06 * (o.lurch ?? 0);
    const x = 2160 - 1500 * u + row * 40, y = 190 + 760 * u + row * 54 + (k % 2) * 10; pf += shipTop(x, y, 0.55, 'persian', t, 0.4 + 0.6 * (o.lurch ?? 0), i); }
  const mist = o.mist ? `<rect x="-200" y="140" width="${W + 400}" height="1200" fill="#f4e4d0" opacity="${(0.6 * o.mist).toFixed(3)}"/>` : '';
  const body = sal + `<g opacity="${gre.toFixed(2)}">${gf}</g>` + psy + pf + att;
  const cx = o.cx ?? 960, cy = o.cy ?? 600;
  return L(c, 0.05, g) + L(c, 0.8, `<g transform="translate(960 600) scale(${z}) translate(${-cx} ${-cy})">${body}</g>`) + mist;
}
const strait_fleet_persian_bird: SceneFn = (c) => straitBird(c, { persian: easeInOut(bw(c, 'navy', 0.3, 2.4)), lurch: easeInOut(bw(c, 'morning', 0.3, 1.0)) });
const strait_dawn_wide_bird: SceneFn = (c) => straitBird(c, { persian: 0.5, mist: 1 - easeInOut(bw(c, 'strait', 0.3, 1.2)), greek: 0.35 + 0.65 * easeInOut(bw(c, 'Greek', 0.3, 0.9)) });
const strait_dawn_fleet_bird: SceneFn = (c) => straitBird(c, { persian: 0.5, zoom: 1.9 + 0.15 * easeInOut(bw(c, 'still', 0.3, 1.2)), cx: 420, cy: 400 });   // close on the Greek fleet on the beach

// ---------- bird's-eye: DELPHI ----------
const delphi_ext_bird: SceneFn = (c) => {
  // DELPHI from high up, packed like the reference: terraces stacked up the mountain under the cliffs, treasuries, a long
  // colonnade, the great altar, statues on their bases, the town below, the temple of Apollo at the top, and pilgrims
  // crowding the Sacred Way. The messengers kneel at the temple ("knelt"); smoke billows from its door ("Delphi").
  const t = c.t, R = rng(77), down = easeOutBack(bw(c, 'knelt', 0.3, 0.8)), puff = easeInOut(bw(c, 'Delphi', 0.3, 1.2)), rev = easeInOut(bw(c, 'Months', 0.3, 1.2));
  let g = skyGrad(c, 'dbSky', [[0, '#7fa8c8'], [1, '#efe6cc']]).replace(`height="${H + 600}"`, 'height="760"');
  g += poly2([[-200, 300], [-200, 40], [300, 0], [700, 50], [1100, -10], [1500, 40], [2120, 0], [2120, 300]], '#b9a48a');            // the Phaedriades cliffs
  for (let i = 0; i < 18; i++) g += `<path d="M${-100 + i * 125} ${30 + (i % 3) * 14} q${20 + (i % 4) * 6} 130 ${10 + (i % 2) * 20} 250" stroke="#8e7a62" stroke-width="4" fill="none"/>`;
  g += poly2([[-200, 290], [2120, 280], [2120, 1300], [-200, 1300]], '#c4ad80');
  for (let i = 0; i < 40; i++) g += `<ellipse cx="${(R() * 2000).toFixed(0)}" cy="${(300 + R() * 900).toFixed(0)}" rx="${(60 + R() * 120).toFixed(0)}" ry="${(14 + R() * 26).toFixed(0)}" fill="${['#b8ad7a', '#d6c49a', '#a8a070'][i % 3]}" opacity=".5"/>`;
  // terraces: retaining walls stepping down the slope
  let s = '';
  const terr = [380, 560, 740, 920];
  for (const y of terr) s += wall(-200, y + 10, 2120, y - 20, 1.3, '#cdbd9a');
  // the Sacred Way zigzags up across the terraces
  const wayPts = [[260, 1300], [520, 1080], [1500, 1000], [1560, 860], [520, 800], [460, 650], [1420, 600], [1440, 470], [1000, 420]];
  s += road('M' + wayPts.map((q) => q.join(' ')).join(' L'), 44);
  // the town below (bottom), houses and gardens
  for (let i = 0; i < 26; i++) { const x = -120 + i * 86 + R() * 20, y = 1170 + (i % 3) * 46; if (Math.abs(x - 300) < 90) continue; s += house(x, y, 0.62, 3000 + i, { court: R() > 0.6 }); if (R() > 0.6) s += tree(x + 50, y - 4, 0.8, 'olive', i); }
  // treasuries of the Greek cities along the way (small painted temples), the colonnade, statues, the great altar
  for (let i = 0; i < 6; i++) s += templeTop(180 + i * 300 + (i % 2) * 40, 990 - (i % 2) * 20, 0.36, { roof: ['#b5452c', '#9a5a3a', '#c07a52'][i % 3], frieze: ['#2f5a8a', '#7a2a5e', '#3a6a4a'][i % 3] });
  s += poly2([[640, 760], [1380, 748], [1380, 728], [640, 740]], '#e8dcc0');
  for (let i = 0; i < 22; i++) s += poly2([[650 + i * 33, 762], [657 + i * 33, 762], [657 + i * 33, 800], [650 + i * 33, 800]], '#f3ebd6', 1.4);   // the colonnade
  s += poly2([[640, 806], [1380, 794], [1380, 806], [640, 818]], '#cbbd9c');
  for (let i = 0; i < 9; i++) { const x = 300 + i * 170, y = 880 + (i % 2) * 10; s += poly2([[x - 14, y], [x + 14, y], [x + 14, y - 16], [x - 14, y - 16]], '#d9ccb0', 1.4) + tiny(x, y - 16, 1.3, 4000 + i, i % 2 ? 'point' : 'stand', 0, { robe: '#d8c49a', spear: i % 3 === 0 }); }   // bronze/stone statues on bases
  s += poly2([[1180, 520], [1300, 516], [1300, 490], [1180, 494]], '#e2d6ba') + poly2([[1180, 494], [1300, 490], [1312, 480], [1192, 484]], '#cfc2a2');   // the great altar
  for (let i = 0; i < 70; i++) { const x = R() * 1950, y = 330 + R() * 880; s += tree(x, y, 0.8, (['cypress', 'olive', 'shrub'] as const)[i % 3], 50 + i); }
  for (let i = 0; i < 8; i++) { const x = 100 + i * 240, y = 520 + (i % 2) * 18; if (Math.abs(x - 1240) < 120) continue; s += templeTop(x, y, 0.22, { roof: ['#9a5a3a', '#b5452c'][i % 2], frieze: '#3a6a4a' }); }   // small shrines on the upper terrace
  for (let i = 0; i < 12; i++) { const x = 80 + i * 165, y = 690 + (i % 3) * 8; s += poly2([[x - 10, y], [x + 10, y], [x + 8, y - 22], [x - 8, y - 22]], ['#c99a45', '#b58a3a', '#e2c070'][i % 3], 1.4) + `<ellipse cx="${x}" cy="${y - 24}" rx="12" ry="4" fill="#c99a45" stroke="${OUT}" stroke-width="1.2"/>`; }   // bronze tripods and offerings
  for (let i = 0; i < 60; i++) s += tiny(R() * 1900, 340 + R() * 760, 0.85, 6000 + i, (['stand', 'talk', 'point', 'sit'] as const)[i % 4], t, { flip: i % 2 === 0 });   // people across the terraces
  // the temple of Apollo on the top terrace, with its smoking door
  s += templeTop(980, 430, 0.9);
  s += Array.from({ length: 6 }, (_, i) => `<circle cx="${(980 + 26 * Math.sin(i * 2 + t)).toFixed(0)}" cy="${(300 - 120 * puff - i * 30).toFixed(0)}" r="${(20 + 40 * puff + i * 8).toFixed(0)}" fill="#a49a92" opacity="${(0.5 * puff * (1 - i * 0.13)).toFixed(3)}"/>`).join('');
  // pilgrims crowding the Sacred Way, priests, people with offerings
  for (let i = 0; i < 120; i++) {
    const u = R(), seg = Math.min(wayPts.length - 2, Math.floor(u * (wayPts.length - 1))), k = u * (wayPts.length - 1) - seg, a = wayPts[seg], b = wayPts[seg + 1];
    s += tiny(a[0] + (b[0] - a[0]) * k + (R() - 0.5) * 30, a[1] + (b[1] - a[1]) * k + (R() - 0.5) * 16 + 10, 0.95, 5000 + i, (['walk', 'carry', 'talk', 'walk'] as const)[i % 4], t, { flip: b[0] < a[0] });
  }
  s += tiny(950, 442 + 8 * (1 - down), 1.4, 7, down > 0.5 ? 'sit' : 'walk', t, { robe: '#e6dcc6' }) + tiny(1010, 442 + 8 * (1 - down), 1.4, 8, down > 0.5 ? 'sit' : 'walk', t, { robe: '#c9b48a' });   // the two messengers
  return L(c, 0.05, g) + L(c, 0.8, `<g opacity="${(0.5 + 0.5 * rev).toFixed(2)}">${s}</g>`) + card(1440, 60, 420, 62, 'DELPHI · 481 BC', 27, tween(c.local, 0.6, 1.6, 0, 1));
};

// ---------- bird's-eye: THE HELLESPONT ----------
function hellespontDraw(c: ShotCtx, z = 1, zx = 960, zy = 600, swayWord = 'bridges'): string {
  // two shores (Asia far, Europe near), two bridges of ships lashed side by side, columns of soldiers marching over them;
  // the king's parasol on "Xerxes", the bridges sway on "bridges", a second column on "sea". Aftermath: guards watching.
  const t = c.t, ln_ = lineOf(c), dusk = ln_ > 100, R = rng(55);
  const king = easeInOut(bw(c, 'Xerxes', 0.3, 1.2)), swayB = Math.sin(Math.min(1, bw(c, swayWord, 0.3, 1.2)) * Math.PI), more = easeInOut(bw(c, 'sea', 0.3, 1.0)), rev = easeInOut(bw(c, dusk ? 'bridges' : 'coming', 0.3, 1.0));
  let g = (dusk ? skyGrad(c, 'hbD', [[0, '#4f3a6e'], [1, '#f2b06a']]) : skyGrad(c, 'hbS', [[0, '#e8a074'], [1, '#fde8c2']])).replace(`height="${H + 600}"`, 'height="760"');
  g += seaTop(c.pid('hbSea'), -200, 160, 2120, 1300, t, dusk ? '#4a4a6e' : '#4f8aa6', 13);
  g += poly2([[-200, 160], [2120, 150], [2120, 300], [1400, 330], [700, 310], [-200, 330]], dusk ? '#7a6a6a' : '#b59a70');        // Asia
  for (let i = 0; i < 40; i++) g += `<path d="M${(R() * 2000).toFixed(0)} ${(190 + R() * 110).toFixed(0)} l-12 0 l12 -16 l12 16 Z" fill="${['#e9e0c8', '#b5452c', '#d9c39a'][i % 3]}" stroke="${OUT}" stroke-width="1.4"/>`;   // the camp left behind
  g += poly2([[-200, 1300], [-200, 960], [700, 1000], [1400, 980], [2120, 1010], [2120, 1300]], dusk ? '#7a6a6a' : '#b59a70');   // Europe
  let b = '';
  for (let k = 0; k < 2; k++) {
    const x0 = 520 + k * 520, sway = 6 * swayB * Math.sin(t * 3 + k);
    for (let i = 0; i < 15; i++) { const y = 340 + i * 44; b += `<path d="M${(x0 - 90 + sway).toFixed(1)} ${y} Q${(x0 + sway).toFixed(1)} ${y + 22} ${(x0 + 90 + sway).toFixed(1)} ${y} L${(x0 + 80 + sway).toFixed(1)} ${y - 18} L${(x0 - 80 + sway).toFixed(1)} ${y - 18} Z" fill="#5a3424" stroke="${OUT}" stroke-width="2"/>` + `<path d="M${(x0 - 90 + sway).toFixed(1)} ${y + 6} q-30 10 -50 30 M${(x0 + 90 + sway).toFixed(1)} ${y + 6} q30 10 50 30" stroke="${OUT}" stroke-width="1.2" fill="none"/>`; }   // hulls lashed side by side, anchor cables
    b += `<rect x="${x0 - 40 + sway}" y="320" width="80" height="${670}" fill="#a07a4a" stroke="${OUT}" stroke-width="2.4"/>` + Array.from({ length: 34 }, (_, j) => `<path d="M${x0 - 40 + sway} ${330 + j * 20} l80 0" stroke="#7a5a34" stroke-width="1.2"/>`).join('');   // the plank road with its boards
    const step = 34, off = (t * 26 * (dusk ? 0.1 : 1)) % step;
    for (let y = 330 + off; y < 990; y += step) for (let a = -1; a <= 1; a++) b += tiny(x0 + sway + a * 22, y + a * 3, 0.95, Math.floor(y) + k * 7 + a, 'walk', t, { spear: true, robe: ['#b5793a', '#7a5a8e', '#4f7a6a', '#a8463a'][(Math.floor(y / step) + a + 3) % 4] });
  }
  if (more > 0) for (let i = 0; i < 30; i++) b += `<g opacity="${more.toFixed(2)}">${tiny(200 + i * 60, 1040 + (i % 3) * 18, 0.8, 300 + i, 'walk', t, { spear: true })}</g>`;
  if (king > 0) b += `<g opacity="${king.toFixed(2)}">${tiny(520, 330 + 640 * king, 1.5, 999, 'walk', t, { robe: '#5b2a6e', hat: '#e2b23f' })}<path d="M${520 - 22} ${(300 + 640 * king).toFixed(0)} Q520 ${(280 + 640 * king).toFixed(0)} ${520 + 22} ${(300 + 640 * king).toFixed(0)} Z" fill="#7a2a5e" stroke="${OUT}" stroke-width="1.6"/></g>`;
  for (let i = 0; i < 22; i++) { const x = 60 + (i * 197) % 1900, y = 380 + (i * 89) % 560; if (Math.abs(x - 520) < 140 || Math.abs(x - 1040) < 140) continue; b += shipTop(x, y, 0.42, i % 3 ? 'boat' : 'persian', t, 0.3, i); }   // supply boats + escort ships
  for (let i = 0; i < 50; i++) b += tiny(40 + i * 40, 300 - (i % 3) * 14, 0.7, 1500 + i, (['stand', 'walk', 'talk'] as const)[i % 3], t, { spear: i % 2 === 0 });   // the army waiting on the Asian shore
  for (let i = 0; i < 40; i++) b += tiny(60 + i * 50, 1030 + (i % 3) * 16, 0.85, 1600 + i, 'walk', t, { spear: true, robe: '#b5793a' });   // landing in Europe
  const zt = (svg: string) => z === 1 ? svg : `<g transform="translate(960 540) scale(${z}) translate(${-zx} ${-zy})">${svg}</g>`;
  return L(c, 0.05, zt(g)) + L(c, 0.8, zt(`<g opacity="${(0.5 + 0.5 * rev).toFixed(2)}">${b}</g>`));
};
const hellespont_bird: SceneFn = (c) => hellespontDraw(c);
const hellespont_close_bird: SceneFn = (c) => hellespontDraw(c, 3.2, 520, 640, 'stop');   // CLOSE bird's-eye on one bridge: soldiers big
const hellespont_army_road_bird: SceneFn = (c) => {
  // the Persian army pours south across the plain ("largest"); Athens on the horizon ("Athens"); villages smoke
  const t = c.t, R = rng(66), pour = easeInOut(bw(c, 'largest', 0.3, 1.6)), city = easeInOut(bw(c, 'Athens', 0.3, 1.0));
  let g = skyGrad(c, 'arSky', [[0, '#4f3a6e'], [1, '#f2b06a']]).replace(`height="${H + 600}"`, 'height="760"');
  g += poly2([[-200, 220], [2120, 200], [2120, 1300], [-200, 1300]], '#b59a70');
  for (let i = 0; i < 30; i++) g += `<ellipse cx="${(R() * 2000).toFixed(0)}" cy="${(240 + R() * 900).toFixed(0)}" rx="${(60 + R() * 140).toFixed(0)}" ry="${(14 + R() * 30).toFixed(0)}" fill="${['#a8986a', '#c4ae80'][i % 2]}" opacity=".5"/>`;
  g += `<path d="M-200 520 Q500 600 900 560 Q1400 500 2120 600" stroke="#6fa6ba" stroke-width="46" fill="none"/>` + `<path d="M-200 520 Q500 600 900 560 Q1400 500 2120 600" stroke="#9ccad6" stroke-width="14" fill="none" opacity=".6"/>`;   // a river
  for (let i = 0; i < 10; i++) { const x = -100 + i * 220, y = 300 + (i % 3) * 90; g += field([[x, y], [x + 180, y - 10], [x + 190, y + 50], [x + 10, y + 60]], ['#b8c27a', '#c9b97a', '#a8b46a'][i % 3], 5, i % 4 === 1); }
  for (let i = 0; i < 70; i++) g += tree(R() * 2000, 620 + R() * 640, 0.8, 'olive', 60 + i);
  g += road('M-100 1300 Q500 900 1000 600 Q1300 400 1600 250', 110, '#d9c39a');
  g += `<g opacity="${(0.4 + 0.6 * city).toFixed(2)}">${templeTop(1660, 240, 0.3)}${Array.from({ length: 10 }, (_, i) => house(1540 + i * 30, 260 + (i % 2) * 10, 0.22, 1300 + i)).join('')}</g>`;
  for (let v = 0; v < 4; v++) { const vx = 300 + v * 420, vy = 500 + (v % 2) * 260; g += house(vx, vy, 0.5, 1400 + v) + house(vx + 60, vy + 10, 0.45, 1410 + v); for (let q = 0; q < 6; q++) { const u = (q / 6 + t * 0.05) % 1; g += `<circle cx="${(vx + 20 * Math.sin(q + v) * u).toFixed(0)}" cy="${(vy - 40 - 220 * u).toFixed(0)}" r="${(14 + 40 * u).toFixed(0)}" fill="#6a6260" opacity="${(0.45 * (1 - u)).toFixed(3)}"/>`; } }   // burning villages
  let army = '';
  for (let i = 0; i < 260; i++) {
    const u = ((i / 260) * (0.25 + 0.75 * pour) + t * 0.004) % 1, lane = (i % 7) - 3;
    const bx = -100 + 1700 * u, by = 1300 - 1050 * u + Math.sin(u * 9) * 40, s = 0.4 + 1.0 * (1 - u);
    army += at(bx + lane * 18 * s, by + lane * 12 * s + Math.abs(Math.sin(t * 6 + i)) * -2 * s, 0.066 * s, guard(t, 2000 + i));
    if (i % 40 === 0) army += `<path d="M${bx} ${by - 40 * s} l0 ${-30 * s} l${22 * s} ${6 * s} l${-22 * s} ${6 * s}" fill="#7a2a5e" stroke="${OUT}" stroke-width="1.4"/>`;   // banners
  }
  const zt = (svg: string) => `<g transform="translate(960 540) scale(1.7) translate(-640 -860)">${svg}</g>`;   // medium: the column big enough to read
  return L(c, 0.05, zt(g)) + L(c, 0.9, zt(army));
};

export const SCENES: Record<string, SceneFn> = {
  strait_fleet_persian: strait_fleet_persian_bird,                    // the Persian fleet fills the bay (beats: appear / lift)
  aigaleos_dawn, aigaleos_scribes, strait_dawn_wide: strait_dawn_wide_bird, strait_dawn_fleet: strait_dawn_fleet_bird, salamis_families, aigaleos_xerxes, aigaleos_xerxes_scribes, aigaleos_scroll,
  delphi_ext: delphi_ext_bird, delphi_messengers, delphi_pythia, delphi_pythia_cu, delphi_beg, delphi_riddle, opensea_messengers,
  athens_pnyx: athens_bird, athens_pnyx_old: athens_pnyx, acropolis_hedge, athens_themistocles, athens_crowd_split, athens_scroll_word, laurium_mine, shipyard,
  hellespont: hellespont_bird, hellespont_close, hellespont_close_bird, thermopylae, opensea_fleet_south, hellespont_army_road: hellespont_army_road_bird,
  athens_streets_empty, harbour_evac, opensea_boats_salamis, salamis_shore_look, acropolis_defenders, acropolis_barricade,
  acropolis_cliff_climb, acropolis_burning, acropolis_temple_fire, acropolis_barricade_burnt, salamis_shore_smoke, road_rider,
  road_xerxes_home: road_rider,
};
