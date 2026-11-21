// ============================================================================================================
// PROOF CLIP — "The Trap at Salamis" (60 s cold open, plan 4 task 8). Every set, prop and composition here is
// drawn fresh for this video (rule r17); one set per place, shot many ways (r23):
//   throne  the golden throne of Xerxes on the slopes of Mount Aigaleos, above the strait, at dawn
//   strait  the narrow strait of Salamis: the Persian fleet, the jam, the ram strike, the end at dusk
//   night   the slave Sicinnus rowing across the dark water
//   camp    Themistocles' tent by lamplight
//   shore   the Greek soldiers singing the battle hymn on the rocks
// Era sheet: jobs/20261121-0752-the-trap-at-salamis-proof/era.json. Characters from the registry (r19).
// Every action lands on its word (beat), with anticipation / easing / follow-through (r28-r30).
// ============================================================================================================
import type { SceneFn, ShotCtx } from '../../film/sequence';
import { OUT, bg, hand, limb, ln, rng, sh, shade, wrap } from '../../kit/core';
import { aspis, head, hair, hopliteBody, pole } from '../../kit/cast';
import { anticipate, beat, blinkAt, breathe, easeInOut, easeOutBack, tween } from '../../kit/anim';
import { camLayer } from '../../kit/camera';
import { mouthAt } from '../../kit/lipsync';
import { card } from '../../kit/tags';
import * as xerxes from '../../characters/xerxes';
import * as themistocles from '../../characters/themistocles';
import lip from './lipsync.json';

const W = 1920, H = 1080;
const L = (c: ShotCtx, depth: number, s: string) => camLayer(c.local, depth, c.cam, s);
/** 0..1 progress of beat i landing on its word (starts lead s early, takes dur s). */
const bt = (c: ShotCtx, i: number, lead = 0.3, dur = 0.6) => beat(c.local, c.beatT(i), lead, dur);
const LIP = (lip as any).lines;
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
  const sunY = tween(c.local, c.beatT(0) - 0.35, c.beatT(0) + 0.5, 470, 330, easeOutBack);
  const set = throneSet(c, { sunY });
  const gleam = bt(c, 2, 0.1, 0.8);
  const settle = easeOutBack(bt(c, 1, 0.4, 0.8));
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
  const appear = easeInOut(bt(c, 1, 0.25, 0.6)), lift = easeOutBack(bt(c, 2, 0.3, 0.5));
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
    const rot = i === 3 ? -14 * swing : (i === 4 ? 3 * Math.sin(bump * Math.PI) : 0);
    fleet += `<g transform="translate(${x + (i === 4 ? jolt : 0)} ${y}) rotate(${rot.toFixed(2)}) scale(${k})">${warship(c.t, 'persian', 0.9, i, i === 4 ? snap : br)}</g>`;
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
  const sea = `<rect x="-300" y="600" width="${W + 600}" height="700" fill="#14284a"/>` + waves(c.t, 51, 610, 1080, 110, '#5a7fb0', 10) +
    `<path d="M1300 610 L1600 610 L1700 1080 L1200 1080 Z" fill="#cfe0ff" opacity="${(0.12 * moon).toFixed(2)}"/>`;
  const bx = 960 + 40 * Math.sin(c.local * 0.5) - 260 * (1 - there);   // the boat glides in on "slave"
  let boat = bg('M-200 -10 Q0 40 200 -10 L170 -70 L-180 -70 Z', '#3a2a1e', 5) + ln('M-180 -60 L170 -60', 4, '#5a4030');
  boat += `<g transform="translate(-10 -40) scale(.55) ${look ? 'scale(-1 1)' : ''}">${sicinnus(c.t, row, look ? 'worried' : 'stern', blinkAt(c.t, 77))}</g>`;
  boat += `<path d="M-120 -20 L${(-260 - 40 * row).toFixed(0)} ${(40 - 20 * row).toFixed(0)}" stroke="${OUT}" stroke-width="7"/><path d="M-120 -20 L${(-260 - 40 * row).toFixed(0)} ${(40 - 20 * row).toFixed(0)}" stroke="#b58a56" stroke-width="3"/>`;
  const ripple = bt(c, 3, 0.1, 1.5);
  if (ripple > 0) boat += `<ellipse cx="-260" cy="44" rx="${(30 + 140 * ripple).toFixed(1)}" ry="${(8 + 30 * ripple).toFixed(1)}" fill="none" stroke="#9cc0e8" stroke-width="3" opacity="${(1 - ripple).toFixed(2)}"/>`;
  return L(c, 0.05, sky) + L(c, 0.2, far) + L(c, 0.5, sea) + L(c, 1, `<g opacity="${(0.2 + 0.8 * there).toFixed(2)}" transform="translate(${bx.toFixed(1)} 840) scale(1.2)">${boat}</g>`);
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

export const SCENES: Record<string, SceneFn> = {
  throne_wide, strait_fleet, throne_xerxes, throne_scribes, night_crossing, camp_message, camp_themistocles,
  throne_believe, strait_enter, strait_jam, shore_hymn, strait_ram, throne_silent, strait_closed,
};
