// ============================================================================================================
// SHORT — "Come and Take Them" (Thermopylae, 480 BC), vertical 1080x1920, ~2 min. Plan 5 task 4.
// Drawn fresh for this video (rule r17); one set per place, shot many ways (r23):
//   army   the Persian host on the plain           throne  Xerxes on his throne in the camp
//   pass   the narrow pass of Thermopylae: cliff, sea, the old Phocian wall (noon, dawn, dusk)
//   tent   the royal tent at night                  path   the mountain path in the moonlight
// Characters: Leonidas + Xerxes from the registry (r19); Dienekes, scouts, heralds, Immortals = extras.
// Era sheet: jobs/20261121-0919-come-and-take-them-thermopylae/era.json. Composed for 9:16 (ART_BIBLE 2.9).
// ============================================================================================================
import type { SceneFn, ShotCtx } from '../../film/sequence';
import { OUT, bg, hand, limb, ln, rng, sh, wrap } from '../../kit/core';
import { aspis, corinthClosed, hair, head, hopliteBody, pole, type Expr } from '../../kit/cast';
import { anticipate, beat, blinkAt, breathe, easeInOut, easeOutBack, tween } from '../../kit/anim';
import { camLayer } from '../../kit/camera';
import { mouthAt } from '../../kit/lipsync';
import { card } from '../../kit/tags';
import * as leonidas from '../../characters/leonidas';
import * as xerxes from '../../characters/xerxes';
import lip from './lipsync.json';

const W = 1080, H = 1920;
const LIP = (lip as any).lines;
const L = (c: ShotCtx, depth: number, s: string) => camLayer(c.local, depth, c.cam, s, c.w, c.h);
/** Pass layers lifted 380 px: the action sits in the middle of the tall frame, not under a huge empty sky. */
const LP = (c: ShotCtx, depth: number, s: string) => L(c, depth, `<g transform="translate(0 -380)">${s}</g>`);
const bt = (c: ShotCtx, i: number, lead = 0.3, dur = 0.55) => beat(c.local, c.beatT(i), lead, dur);
const exch = (c: ShotCtx, i: number, from: Expr, to: Expr) => ({ expr: from, exprTo: to, exprMix: tween(c.local, c.beatT(i) - 0.16, c.beatT(i) + 0.04, 0, 1) });
const at = (x: number, y: number, k: number, svg: string, rot = 0) => `<g transform="translate(${x.toFixed(1)} ${y.toFixed(1)})${rot ? ` rotate(${rot.toFixed(2)})` : ''} scale(${k})">${svg}</g>`;

// ---------- light + sky ----------
const SKIES: Record<string, [string, string, string]> = {
  dawn: ['#e9a97c', '#f7d3a0', '#fde9c6'], noon: ['#7db2d4', '#c9e0e6', '#f3e6c4'], dusk: ['#4f3a6e', '#d77c56', '#f2b06a'],
  night: ['#0b1430', '#1a2a4c', '#26385c'],
};
function sky(c: ShotCtx, time: string, sunX = 760, sunY = 300): string {
  const [a, b, d] = SKIES[time], id = c.pid('sky'), gid = c.pid('glow');
  let s = `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${a}"/><stop offset=".55" stop-color="${b}"/><stop offset="1" stop-color="${d}"/></linearGradient>` +
    `<radialGradient id="${gid}"><stop offset="0" stop-color="${time === 'night' ? '#cfe0ff' : '#fff4d0'}" stop-opacity=".9"/><stop offset="1" stop-color="#fff4d0" stop-opacity="0"/></radialGradient></defs>` +
    `<rect x="-400" y="-400" width="${W + 800}" height="${H + 800}" fill="url(#${id})"/>` +
    `<circle cx="${sunX}" cy="${sunY}" r="${time === 'night' ? 200 : 300}" fill="url(#${gid})"/>` +
    `<circle cx="${sunX}" cy="${sunY}" r="${time === 'night' ? 40 : 54}" fill="${time === 'night' ? '#eef3ff' : '#fff4d2'}" stroke="${time === 'night' ? '#b8c8e8' : '#f0c47a'}" stroke-width="4"/>`;
  if (time !== 'night') {                                         // drifting clouds on the global clock
    const cl = (x: number, y: number, k: number) => at(wrap(x + c.t * 5, W + 500) - 250, y, k, bg('M0 40 Q-14 8 26 6 Q34 -22 72 -10 Q100 -34 132 -4 Q172 -6 166 40 Z', time === 'dusk' ? '#f0b49a' : '#fdf3e2', 4));
    s += cl(80, 160, 1.2) + cl(560, 260, 0.9) + cl(880, 120, 1.0);
  } else {
    const R = rng(3);
    for (let i = 0; i < 70; i++) s += `<circle cx="${(R() * W).toFixed(0)}" cy="${(R() * 900).toFixed(0)}" r="${(0.8 + R() * 1.8).toFixed(1)}" fill="#e6eeff" opacity="${(0.4 + 0.5 * Math.abs(Math.sin(c.t * 2 + i))).toFixed(2)}"/>`;
  }
  return s;
}
function pine(x: number, y: number, k: number, col = '#46643a'): string {
  return at(x, y, k, sh('rect', { x: -4, y: -8, width: 8, height: 24 }, '#5a3a24') + bg('M0 -78 L28 -28 L12 -30 L34 4 L-34 4 L-12 -30 L-28 -28 Z', col, 4));
}

// ---------- figures (extras, drawn for this video) ----------
/** A Spartan hoplite. helmet 'up' shows the face, 'closed' is the battle look. arms: 'spear' | 'comb' | 'rest'. */
function spartan(t: number, seed: number, o: { helmet?: 'up' | 'closed'; arms?: 'spear' | 'comb' | 'rest' | 'thrust'; expr?: Expr; to?: Expr; mix?: number; amp?: number; k?: number; shield?: boolean } = {}): string {
  const skin = ['#d8a87c', '#cf9e72', '#dcae84', '#c99566'][seed % 4];
  let s = `<ellipse cx="0" cy="-4" rx="70" ry="12" fill="rgba(0,0,0,.15)"/>` + hopliteBody(skin, true);
  const arms = o.arms ?? 'spear';
  if (arms === 'spear' || arms === 'thrust') {
    const k = o.k ?? 0;                                           // thrust: spear swings from upright to levelled
    const ang = arms === 'thrust' ? -90 * easeInOut(k) : 0;
    s += `<g transform="rotate(${ang.toFixed(1)} -82 -190)">${pole(-82, -480, -82, -6, '#8b5a2b', `sp${seed}`)}${sh('path', { d: 'M-82 -530 L-92 -480 L-72 -480 Z' }, '#bdbdbd')}</g>`;
    s += limb('M-44 -222 Q-80 -210 -82 -190', 20, skin) + hand(-82, -186, skin, `sp${seed}`);
  } else if (arms === 'comb') {                                   // combing the long hair before battle (Herodotus 7.208)
    const k = o.k ?? 0, cy = -330 + 60 * (o.amp ?? 1) * Math.sin(k * Math.PI * 2);
    s += limb(`M-44 -222 Q-96 -270 -70 ${cy.toFixed(0)}`, 20, skin) + sh('rect', { x: -96, y: cy - 22, width: 12, height: 44, rx: 3 }, '#efe0b8') + hand(-74, cy, skin);
  } else {
    s += limb('M-44 -222 Q-62 -180 -54 -140', 20, skin) + hand(-54, -134, skin);
  }
  if (o.shield !== false) s += aspis(62, -168, 80, undefined, 'lambda');
  const lift = (breathe(t, seed) * -1.5).toFixed(2);
  s += `<g transform="translate(0 ${lift})">`;
  if (o.helmet === 'closed') s += head(skin, 'stern', { extra: true }) + corinthClosed('fan');
  else {
    s += sh('path', { d: 'M-62 -300 Q-76 -240 -58 -200 L-36 -210 Q-50 -258 -44 -300 Z' }, '#3a2a1e') + sh('path', { d: 'M62 -300 Q76 -240 58 -200 L36 -210 Q50 -258 44 -300 Z' }, '#3a2a1e');
    s += head(skin, o.expr ?? 'neutral', { beard: '#3a2a1e', blink: blinkAt(t, seed), extra: true, to: o.to, mix: o.mix }) + (arms === 'comb' ? sh('path', { d: 'M-60 -300 Q-64 -366 0 -368 Q64 -366 60 -300 Q52 -336 0 -338 Q-52 -336 -60 -300 Z' }, '#3a2a1e') : hair.corinthian());
  }
  return s + '</g>';
}
/** A Persian soldier (Immortal): long robe, wicker shield, spear with an apple butt, felt cap (Susa frieze). */
function persian(t: number, seed: number, o: { run?: number; back?: number; gold?: boolean } = {}): string {
  const skin = '#c98f62', robe = o.gold ? '#d9b443' : ['#b5793a', '#7a5a8e', '#4f7a6a', '#a8463a'][seed % 4];
  const leg = (o.run ?? 0) * 26 * Math.sin(t * 9 + seed);
  let s = `<ellipse cx="0" cy="-4" rx="60" ry="10" fill="rgba(0,0,0,.14)"/>`;
  s += limb(`M-14 -110 L${(-20 + leg).toFixed(1)} -14`, 18, '#5a3a24') + limb(`M14 -110 L${(20 - leg).toFixed(1)} -14`, 18, '#5a3a24');
  s += bg('M-44 -238 Q0 -248 44 -238 Q54 -140 62 -70 L-62 -70 Q-54 -140 -44 -238 Z', robe, 5) + ln('M-58 -84 L58 -84', 6, '#f2ead8');
  s += pole(-70, -470, -70, -10, '#6a4428') + sh('circle', { cx: -70, cy: -6, r: 10 }, '#d9b443') + sh('path', { d: 'M-70 -500 L-78 -470 L-62 -470 Z' }, '#bdbdbd');
  s += limb('M-44 -222 Q-72 -210 -70 -190', 18, robe) + hand(-70, -186, skin);
  s += sh('path', { d: 'M28 -232 L82 -232 L88 -110 L22 -110 Z' }, '#c9a96e') + ln('M32 -212 L82 -212 M30 -182 L84 -182 M28 -152 L86 -152', 3, '#8a6a3a');
  s += `<g transform="translate(0 ${(breathe(t, seed + 9) * -1.2).toFixed(2)})">${head(skin, 'stern', { beard: '#1c1612', blink: blinkAt(t, seed + 9), extra: true, to: 'shocked', mix: Math.min(1, o.back ?? 0) })}` +
    sh('path', { d: 'M-60 -300 Q-62 -372 0 -376 Q62 -372 60 -300 Z' }, '#e7dcc6') + '</g>';
  return s;
}
/** A herald (envoy) with a staff of office, robe and cap. */
function herald(t: number, point = 0): string {
  const skin = '#c98f62';
  let s = `<ellipse cx="0" cy="-4" rx="60" ry="10" fill="rgba(0,0,0,.14)"/>` + bg('M-44 -238 Q0 -248 44 -238 Q56 -120 66 -8 L-66 -8 Q-56 -120 -44 -238 Z', '#5b2a6e', 5) + ln('M-60 -40 L60 -40', 6, '#d9b443');
  s += pole(-76, -430, -76, -10, '#d9b443') + sh('circle', { cx: -76, cy: -440, r: 14 }, '#d9b443') + limb('M-44 -222 Q-74 -210 -76 -190', 18, '#5b2a6e') + hand(-76, -186, skin);
  s += limb(`M44 -222 Q${(70 + 40 * point).toFixed(0)} ${(-200 - 30 * point).toFixed(0)} ${(60 + 90 * point).toFixed(0)} ${(-150 - 80 * point).toFixed(0)}`, 18, '#5b2a6e') + hand(60 + 90 * point, -150 - 80 * point, skin);
  return s + head(skin, 'stern', { beard: '#1c1612', blink: blinkAt(t, 31), extra: true }) + sh('path', { d: 'M-60 -300 Q-62 -380 0 -388 Q62 -380 60 -300 Z' }, '#e7dcc6');
}

// ---------- THE PASS (one set for the whole video, many angles and times of day) ----------
function passSet(c: ShotCtx, time: string): { sky: string; far: string; mid: string; ground: string } {
  const t = c.t;
  const sunY = time === 'dawn' ? 420 : time === 'dusk' ? 520 : 240;
  const s0 = sky(c, time, time === 'dusk' ? 860 : 760, sunY);
  // far: Euboea across the gulf, the gulf itself on the right
  const far = bg('M300 900 L520 820 L700 860 L900 800 L1200 860 L1200 960 L300 960 Z', time === 'dusk' ? '#8a6a8e' : '#a993ad', 3) +
    `<rect x="300" y="950" width="${W + 300}" height="400" fill="${time === 'dusk' ? '#6f6a8a' : '#6fa3b8'}"/>` +
    Array.from({ length: 26 }, (_, i) => { const R = rng(i + 7); const x = 340 + R() * 760, y = 970 + R() * 360, w = 14 + R() * 24; return `<path d="M${(wrap(x + t * 12, 800) + 300).toFixed(0)} ${y.toFixed(0)} q${w / 2} -4 ${w} 0" stroke="#e3f1f4" stroke-width="3" fill="none" opacity=".7"/>`; }).join('');
  // mid: Mount Kallidromos as a tall cliff wall on the left, pines on its ledges
  let mid = bg('M-300 2600 L-300 -200 L180 -200 Q340 200 300 600 Q260 900 420 1160 Q520 1320 470 2600 Z', time === 'dusk' ? '#6e5240' : '#8b6b4f', 6) +
    `<path d="M180 -200 Q340 200 300 600 Q260 900 420 1160 Q520 1320 470 2600 L380 2600 Q420 1340 330 1180 Q180 920 220 600 Q260 200 120 -200 Z" fill="${time === 'dusk' ? '#8a6650' : '#a5835f'}"/>`;
  for (let i = 0; i < 12; i++) mid += `<path d="M${-80 + (i % 3) * 30} ${120 + i * 150} q120 -20 ${230 + (i % 4) * 20} 10" stroke="#5e442e" stroke-width="5" fill="none" stroke-linecap="round"/>`;
  mid += pine(140, 300, 1.1) + pine(250, 520, 0.9) + pine(110, 760, 1.2) + pine(330, 1010, 0.8);
  // ground: the road through the pass + the old Phocian wall across it
  let ground = bg('M300 1180 Q700 1150 1200 1170 L1200 2600 L300 2600 Z', time === 'dusk' ? '#a07a52' : '#c9ab78', 5);
  for (let r = 0; r < 4; r++) for (let i = 0; i < 12; i++) {
    const x = 360 + i * 64 + (r % 2) * 32, y = 1250 - r * 30;
    ground += `<rect x="${x}" y="${y}" width="${58 + (i * 7) % 10}" height="28" rx="6" fill="${['#c9b89a', '#b8a688', '#d6c6a6'][(i + r) % 3]}" stroke="${OUT}" stroke-width="3"/>`;
  }
  ground += `<path d="M380 1300 L1100 1300" stroke="rgba(0,0,0,.18)" stroke-width="10"/>`;
  ground += bg('M300 2600 L300 2180 Q420 2120 560 2170 Q640 2140 700 2200 L700 2600 Z', time === 'dusk' ? '#6e5240' : '#8b6b4f', 5) +
    bg('M880 2600 Q900 2200 1040 2180 Q1160 2170 1200 2240 L1200 2600 Z', time === 'dusk' ? '#6e5240' : '#8b6b4f', 5) +
    Array.from({ length: 9 }, (_, i) => `<path d="M${560 + i * 40} 2240 q${4 + 3 * Math.sin(t * 2 + i)} -36 8 -70" stroke="#6f8a44" stroke-width="5" fill="none" stroke-linecap="round"/>`).join('');
  return { sky: s0, far, mid, ground };
}

// ---------- THE PERSIAN HOST + THE CAMP ----------
function plainSet(c: ShotCtx, time: string, sunX = 780, sunY = 300): { sky: string; far: string; ground: string } {
  const s0 = sky(c, time, sunX, sunY);
  const far = bg('M-200 820 L200 740 L460 780 L760 720 L1280 780 L1280 860 L-200 860 Z', '#a993ad', 3) + bg('M-200 860 L1280 860 L1280 2100 L-200 2100 Z', time === 'noon' ? '#c2a86e' : '#b89a62', 4);
  let tents = '';
  const R = rng(55);
  for (let i = 0; i < 40; i++) {
    const y = 880 + Math.pow(R(), 1.6) * 260, x = R() * W, k = 0.6 + (y - 880) / 260 * 0.9, col = ['#e9e0c8', '#d9c39a', '#a8463a', '#e2d6b4', '#5b2a6e'][i % 5];
    tents += at(x, y, k, bg('M-26 0 L0 -30 L26 0 Z', col, 2.5) + `<path d="M0 -30 L0 -42" stroke="${OUT}" stroke-width="2"/>`);
  }
  return { sky: s0, far, ground: tents };
}
/** Endless columns of soldiers marching toward the horizon (vertical composition: rows recede upward). */
function columns(t: number, march: number, n = 9, y0 = 900, y1 = 1900): string {
  let s = '';
  for (let r = 0; r < n; r++) {
    const f = r / (n - 1), y = y0 + Math.pow(f, 1.7) * (y1 - y0), k = 0.08 + f * 0.36;
    const step = 140 * k, off = wrap(t * 30 * march * k, step);
    for (let x = -step + off; x < W + step; x += step) s += at(x, y, k, persian(t, Math.floor(x) + r, { run: march * 0.5 }));
  }
  return s;
}
function throneSeat(c: ShotCtx, pose: any): string {   // Xerxes seated: throne behind, seat + armrests in front of his legs
  const back = bg('M-90 -400 Q0 -430 90 -400 L90 -170 L-90 -170 Z', '#e2b23f', 6) + ln('M-70 -380 L70 -380 M-70 -350 L70 -350', 4, '#a8822a') + bg('M-170 0 L170 0 L150 -40 L-150 -40 Z', '#c9b28a', 5);
  const front = bg('M-104 -190 L104 -190 L104 -128 L-104 -128 Z', '#e2b23f', 6) + bg('M-118 -236 L-96 -236 L-96 -70 L-118 -70 Z', '#d9a536', 5) + bg('M96 -236 L118 -236 L118 -70 L96 -70 Z', '#d9a536', 5);
  const mouth = mouthAt(c.t, LIP, 'XERXES');
  return back + `<g transform="translate(0 -40)">${xerxes.draw({ breath: breathe(c.t, 1), blink: blinkAt(c.t, 1), mouth, ...pose })}</g>` + front;
}

const army_vast: SceneFn = (c) => {
  const set = plainSet(c, 'dawn'), reveal = easeInOut(bt(c, 0, 0.3, 0.9)), red = easeOutBack(bt(c, 1)), halt = bt(c, 2);
  const march = 1 - halt;
  let spartans = '';
  for (let i = 0; i < 9; i++) spartans += `<rect x="${470 + i * 16}" y="${838}" width="9" height="14" rx="2" fill="#b23a2a" stroke="${OUT}" stroke-width="1.5" opacity="${red.toFixed(2)}"/>`;
  return L(c, 0.05, set.sky) + L(c, 0.2, set.far + set.ground + spartans) + L(c, 1, `<g opacity="${(0.25 + 0.75 * reveal).toFixed(2)}">${columns(c.t, march)}</g>`);
};
const throne_offer: SceneFn = (c) => {
  const set = plainSet(c, 'noon'), lean = anticipate(bt(c, 0));
  return L(c, 0.05, set.sky) + L(c, 0.25, set.far + set.ground) +
    L(c, 1, at(540, 2650 - 40 * lean, 3.2, throneSeat(c, { ...exch(c, 1, 'stern', 'sly'), armR: { from: 'down', to: 'open', k: lean } })));
};
const army_nations: SceneFn = (c) => {
  const set = plainSet(c, 'noon'), rise = easeOutBack(bt(c, 1));
  let banners = '';
  [180, 480, 800].forEach((x, i) => { banners += at(x, 1300 - 60 * rise, 1.4, pole(0, -300, 0, 0, '#6a4428') + bg(`M0 -300 Q40 ${-294 + 6 * Math.sin(c.t * 3 + i)} 80 -298 L80 -240 Q40 ${-236 + 6 * Math.sin(c.t * 3 + i)} 0 -242 Z`, ['#7a2a5e', '#d9b443', '#2f6f8e'][i], 4)); });
  let rows = '';
  for (let r = 0; r < 3; r++) for (let i = 0; i < 6; i++) rows += at(wrap(i * 230 + c.local * 70 + r * 80, W + 300) - 150, 1500 + r * 190, 0.85 + r * 0.15, persian(c.t, i * 3 + r, { run: 0.6 }));
  return L(c, 0.05, set.sky) + L(c, 0.25, set.far + set.ground) + L(c, 0.8, banners) + L(c, 1, rows);
};
const pass_envoy: SceneFn = (c) => {
  const p = passSet(c, 'noon'), walk = tween(c.local, c.beatT(0) - 0.3, c.dur, 0, 1, (x) => x), pair = easeOutBack(bt(c, 3, 0.3, 0.8));
  const cardOp = tween(c.local, c.beatT(1) - 0.3, c.beatT(1) + 0.4, 0, 1);
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid) + LP(c, 0.9, p.ground + at(980 - 300 * walk, 1640, 0.85, herald(c.t)) + `<g opacity="${Math.min(1, pair).toFixed(2)}">${at(560, 1440 + 30 * (1 - pair), 0.42, spartan(c.t, 1, { helmet: 'closed' }))}${at(660, 1440 + 30 * (1 - pair), 0.42, spartan(c.t, 2, { helmet: 'closed' }))}</g>`) +
    card(240, 120, 600, 76, 'THERMOPYLAE · 480 BC', 34, cardOp);
};
const pass_scout: SceneFn = (c) => {
  const p = passSet(c, 'noon'), peek = easeOutBack(bt(c, 0, 0.3, 0.9)), count = bt(c, 1, 0.2, 1.2), handUp = easeOutBack(bt(c, 1, 0.3, 0.6)), tips = easeInOut(bt(c, 2, 0.3, 0.9)), widen = easeInOut(bt(c, 3, 0.3, 0.5));
  let men = '';
  for (let i = 0; i < 5; i++) men += at(470 + i * 130, 1440, 0.42, spartan(c.t, i, { helmet: 'up' }));
  const fingers = Math.max(0, Math.min(5, Math.ceil(count * 5)));
  const scout = at(860, 1980 - 140 * peek, 1.5, persian(c.t, 7, { back: widen })) + `<g transform="translate(${(860 - 100).toFixed(0)} ${(1680 + 120 * (1 - handUp)).toFixed(0)})">${Array.from({ length: fingers }, (_, i) => `<rect x="${i * 14}" y="0" width="9" height="${(26 - (i === 4 ? 6 : 0))}" rx="4" fill="#c98f62" stroke="${OUT}" stroke-width="2.5"/>`).join('')}</g>`;
  const rock = bg('M560 2100 Q600 1780 860 1720 Q1100 1700 1200 1820 L1200 2100 Z', '#8b6b4f', 6);
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid + Array.from({ length: 10 }, (_, i) => `<path d="M${380 + i * 72} 1170 L${380 + i * 72} ${(1170 - 110 * tips).toFixed(0)}" stroke="#8b5a2b" stroke-width="6"/><path d="M${372 + i * 72} ${(1172 - 110 * tips).toFixed(0)} l8 -26 l8 26 Z" fill="#bdbdbd" stroke="#2b211c" stroke-width="2"/>`).join('') + p.ground + men) + LP(c, 1.1, scout + rock);
};
const pass_comb: SceneFn = (c) => {
  const p = passSet(c, 'noon'), laugh = easeInOut(bt(c, 2, 0.25, 0.4)), hop = Math.sin(Math.min(1, bt(c, 2, 0.1, 0.5)) * Math.PI);
  const amps = [tween(c.local, c.beatT(0) - 0.3, c.beatT(0) + 0.4, 0, 1), 0, tween(c.local, c.beatT(1) - 0.3, c.beatT(1) + 0.4, 0, 1)];
  let s = '';
  [[300, 1640, 0.85, 0], [620, 1700, 0.95, 1], [900, 1660, 0.88, 2]].forEach(([x, y, k, i]) => {
    s += at(x, y - (i === 1 ? 26 * hop : 0), k, spartan(c.t, i, { helmet: 'up', arms: i === 1 ? 'rest' : 'comb', amp: amps[i], k: (c.local * 0.8 + i * 0.3) % 1, expr: 'neutral', to: 'sly', mix: i === 1 ? laugh : 0, shield: false }));
  });
  s += at(620, 1880, 0.6, aspis(0, 0, 90, undefined, 'lambda'));             // a shield resting on the ground
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid + p.ground) + LP(c, 1, s);
};
const throne_laugh: SceneFn = (c) => {
  // the sun races across the sky = four days pass while the king waits
  const days = tween(c.local, c.beatT(1) - 0.3, c.dur, 0, 2, (x) => x);
  const dimDay = days > 0 ? 0.42 * Math.pow(Math.cos(days * Math.PI), 2) * Math.min(1, days * 4) : 0;   // darkest when the sun is down (hides its wrap)
  const sunX = -100 + (days % 1) * 1300, sunY = 700 - 500 * Math.sin((days % 1) * Math.PI);
  const set = plainSet(c, 'noon', sunX, sunY);   // the set's own sun is the one that crosses the sky
  return L(c, 0.05, set.sky) + L(c, 0.25, set.far + set.ground) +
    L(c, 1, at(540, 2150, 2.0, throneSeat(c, { ...exch(c, 0, 'neutral', 'sly'), armR: { from: 'down', to: 'hip', k: easeInOut(bt(c, 2, 0.3, 0.6)) } }))) + `<rect width="${W}" height="${H}" fill="#2a1838" opacity="${dimDay.toFixed(3)}"/>`;
};
const pass_firm: SceneFn = (c) => {
  const p = passSet(c, 'dawn');
  let men = '';
  for (let i = 0; i < 6; i++) men += at(420 + i * 120, 1500 + (i % 2) * 30, 0.5, spartan(c.t, i + 3, { helmet: 'closed' }));
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid) + LP(c, 1, p.ground + men);
};
const pass_demand: SceneFn = (c) => {
  const p = passSet(c, 'noon'), point = easeOutBack(bt(c, 0)), stand = easeOutBack(bt(c, 2));
  const leo = at(380, 1760 - 40 * stand - 24 * easeOutBack(bt(c, 1, 0.3, 0.5)), 1.0, leonidas.draw({ ...exch(c, 1, 'neutral', 'stern'), breath: breathe(c.t, 5), blink: blinkAt(c.t, 5) }));
  const her = at(900, 1900, 1.25, herald(c.t, point));
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid + p.ground) + LP(c, 1, leo + her);
};
const pass_leonidas: SceneFn = (c) => {
  const p = passSet(c, 'noon');
  const mouth = mouthAt(c.t, LIP, 'LEONIDAS');
  return L(c, 0.05, p.sky) + LP(c, 0.3, p.far + p.mid) +
    LP(c, 1, at(540, 2380, 3.0, leonidas.draw({ expr: 'stern', mouth, breath: breathe(c.t, 5), blink: blinkAt(c.t, 5) })));
};
const pass_waves: SceneFn = (c) => {
  const p = passSet(c, 'noon'), pour = easeInOut(tween(c.local, c.beatT(0) - 0.3, c.dur, 0, 1)), hit = bt(c, 1, 0.1, 0.4), dust = bt(c, 2, 0.2, 1.4);
  let wall = '';
  for (let i = 0; i < 7; i++) wall += at(420 + i * 100, 1430 + (i % 2) * 14, 0.4, spartan(c.t, i, { helmet: 'closed', arms: 'thrust', k: 1 }));
  let foes = '';
  for (let r = 0; r < 3; r++) for (let i = 0; i < 6; i++) {
    const x = 1150 - pour * 420 + i * 70 + r * 40 - (hit > 0 ? 0 : 0), y = 1480 + r * 70;
    foes += at(x + (hit > 0 && r === 0 ? 30 * Math.sin(hit * Math.PI) : 0), y, 0.38 + r * 0.04, persian(c.t, i + r * 6, { run: 1, back: r === 0 ? Math.min(1, hit * 2) : 0 }));
  }
  const cloud = dust > 0 ? Array.from({ length: 10 }, (_, i) => `<circle cx="${(560 + i * 50).toFixed(0)}" cy="${(1520 - 60 * dust - (i % 3) * 20).toFixed(0)}" r="${(30 + 50 * dust).toFixed(0)}" fill="#d9c3a0" opacity="${(0.55 * Math.min(1, dust * 6) * (1 - dust * 0.7)).toFixed(2)}"/>`).join('') : '';
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid) + LP(c, 1, p.ground + wall + foes + cloud);
};
const pass_wall: SceneFn = (c) => {
  const p = passSet(c, 'noon'), lock = easeOutBack(bt(c, 0, 0.3, 0.7)), bounce = bt(c, 1, 0.1, 0.6);
  let s = '';
  for (let i = 0; i < 4; i++) s += at(160 + i * 250 - 20 * (1 - lock), 1880, 1.15, spartan(c.t, i, { helmet: 'closed', arms: 'thrust', k: lock }));
  for (let i = 0; i < 3; i++) s += at(300 + i * 280 + 60 * Math.sin(bounce * Math.PI), 1260 - 40 * Math.sin(bounce * Math.PI), 0.7, persian(c.t, i, { back: Math.min(1, bounce * 3) }), -12 * Math.sin(bounce * Math.PI));
  return L(c, 0.05, p.sky) + LP(c, 0.3, p.far + p.mid + p.ground) + LP(c, 1, s);
};
const pass_feint: SceneFn = (c) => {
  const p = passSet(c, 'noon'), away = easeInOut(bt(c, 0, 0.3, 0.5)), wheel = easeOutBack(bt(c, 1, 0.3, 0.4)), fall = bt(c, 2, 0.2, 0.8);
  const dir = Math.max(-1, Math.min(1, 1 - 2 * away + 2 * Math.min(1, wheel)));
  let s = '';
  for (let i = 0; i < 5; i++) s += at(380 + i * 150 - 80 * away + 80 * wheel, 1620, 0.62, `<g transform="scale(${dir} 1)">${spartan(c.t, i, { helmet: 'closed', arms: 'thrust', k: wheel })}</g>`);
  for (let i = 0; i < 4; i++) s += at(1000 + i * 120 - 200 * away + 260 * fall, 1700, 0.55, persian(c.t, i + 2, { run: 1 - fall, back: Math.min(1, fall * 3) }), fall * 20);
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid) + LP(c, 1, p.ground + s);
};
const throne_leap: SceneFn = (c) => {
  const set = plainSet(c, 'noon');
  const jump = Math.max(...[0, 1, 2].map((i) => Math.sin(Math.min(1, bt(c, i, 0.25, 0.75)) * Math.PI)));
  return L(c, 0.05, set.sky) + L(c, 0.25, set.far + set.ground) +
    L(c, 1, at(540, 2200 - 90 * jump, 2.0, throneSeat(c, { ...exch(c, 0, 'stern', 'shocked'), armR: { from: 'down', to: 'raise', k: jump } })));
};
const pass_warning: SceneFn = (c) => {
  const p = passSet(c, 'noon'), point = easeOutBack(bt(c, 1)), dark = easeInOut(bt(c, 2, 0.3, 1.0));
  let arrows = '';
  const R = rng(21);
  for (let i = 0; i < 70; i++) { const x = R() * W, y = 100 + R() * 700 + dark * 120; arrows += `<path d="M${x.toFixed(0)} ${y.toFixed(0)} l26 14" stroke="${OUT}" stroke-width="3" opacity="${dark.toFixed(2)}"/>`; }
  const officer = at(600, 1900, 1.4, persian(c.t, 12, {})) + at(600, 1900, 1.4, limb(`M44 -222 Q${70 + 30 * point} ${-280 - 60 * point} ${60 + 40 * point} ${-330 - 120 * point}`, 18, '#b5793a') + hand(60 + 40 * point, -330 - 120 * point, '#c98f62'));
  return L(c, 0.05, p.sky + `<rect width="${W}" height="${H}" fill="#000" opacity="${(0.25 * dark).toFixed(2)}"/>` + arrows) + LP(c, 0.6, p.mid + p.ground) + LP(c, 1, officer);
};
const pass_dienekes: SceneFn = (c) => {
  const p = passSet(c, 'noon'), shade = easeInOut(bt(c, 1, 0.3, 0.8));
  const mouth = mouthAt(c.t, LIP, 'DIENEKES');
  let face = spartan(c.t, 2, { helmet: 'up', arms: 'spear', expr: c.local >= c.beatT(0) - 0.2 ? 'sly' : 'stern' });
  if (mouth) face += `<ellipse cx="0" cy="-252" rx="${mouth === 'wide' ? 12 : mouth === 'o' ? 7 : 10}" ry="${mouth === 'closed' ? 2 : 8}" fill="#7a2b22" stroke="${OUT}" stroke-width="4"/>`;
  return L(c, 0.05, p.sky) + LP(c, 0.3, p.far + p.mid) + LP(c, 1, at(540, 2380, 3.0, face)) + `<rect width="${W}" height="${H}" fill="#1a1020" opacity="${(0.32 * shade).toFixed(2)}"/>`;
};
const pass_immortals: SceneFn = (c) => {
  const p = passSet(c, 'noon'), charge = easeInOut(bt(c, 0, 0.3, 1.6)), back = easeInOut(bt(c, 1, 0.2, 1.0));
  let s = '';
  for (let i = 0; i < 6; i++) s += at(380 + i * 120, 1460, 0.45, spartan(c.t, i, { helmet: 'closed', arms: 'thrust', k: 1 }));
  for (let r = 0; r < 2; r++) for (let i = 0; i < 6; i++) s += at(1150 - 380 * charge + 300 * back + i * 75, 1540 + r * 80, 0.44, persian(c.t, i + r * 6, { gold: true, run: 1 - back, back: Math.min(1, back * 3) }), back * 16 * (i % 2 ? 1 : -1));
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid) + LP(c, 1, p.ground + s);
};
const pass_dusk: SceneFn = (c) => {
  const p = passSet(c, 'dusk');
  let men = '';
  for (let i = 0; i < 8; i++) men += at(400 + i * 90, 1440, 0.34, spartan(c.t, i, { helmet: 'closed' }));
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid) + LP(c, 1, p.ground + men);
};

// ---------- THE ROYAL TENT (night) ----------
function tentSet(c: ShotCtx): string {
  const f = 0.9 + 0.1 * Math.sin(c.t * 13) * Math.sin(c.t * 7.3), gid = c.pid('lamp');
  return `<rect x="-300" y="-300" width="${W + 600}" height="${H + 600}" fill="#1e1420"/>` +
    bg(`M-200 2100 L-200 400 Q540 120 1280 400 L1280 2100 Z`, '#4a2a3e', 5) + ln('M200 300 L120 2100 M540 200 L540 2100 M880 300 L960 2100', 6, '#2e1a28') +
    Array.from({ length: 6 }, (_, i) => `<path d="M${-100 + i * 240} 520 q60 30 120 0" stroke="#d9b443" stroke-width="5" fill="none"/>`).join('') +
    `<defs><radialGradient id="${gid}"><stop offset="0" stop-color="#ffb85c" stop-opacity=".6"/><stop offset="1" stop-color="#ffb85c" stop-opacity="0"/></radialGradient></defs>` +
    `<circle cx="760" cy="1260" r="${(760 * f).toFixed(0)}" fill="url(#${gid})"/>` +
    bg('M700 1300 L820 1300 L800 1380 L720 1380 Z', '#a8643a', 4) + sh('ellipse', { cx: 760, cy: 1300, rx: 64, ry: 14 }, '#c4844a') +
    `<path d="M816 1288 q10 -26 2 -44 q16 18 6 44 Z" fill="#ffd27a" stroke="#e8902a" stroke-width="2"/>` + bg('M-200 1880 L1280 1880 L1280 2100 L-200 2100 Z', '#7a3a2a', 4);
}
function ephialtes(t: number, kneel = 1): string {   // a local Greek in a rough tunic, kneeling
  const skin = '#cf9e72';
  return bg('M-50 -150 Q-60 -40 -70 0 L70 0 Q60 -40 50 -150 Z', '#7a6a4e', 5) + limb('M-40 -140 Q-80 -100 -60 -60', 18, skin) + hand(-60, -56, skin) +
    `<g transform="translate(0 ${(80 * (1 - kneel)).toFixed(0)}) scale(.9) translate(0 160)">${head(skin, 'sly', { beard: '#4a3222', blink: blinkAt(t, 44), extra: true })}${sh('path', { d: 'M-60 -300 Q-64 -362 0 -366 Q64 -362 60 -300 Q50 -334 0 -336 Q-50 -334 -60 -300 Z' }, '#4a3222')}</g>`;
}
const tent_ephialtes: SceneFn = (c) => {
  const kneel = easeOutBack(bt(c, 1, 0.3, 0.9)), lean = easeInOut(bt(c, 2, 0.3, 0.9));
  return L(c, 0.2, tentSet(c)) + L(c, 1, at(700, 1980, 1.9, throneSeat(c, { expr: 'neutral', exprTo: 'sly', exprMix: lean }), -4 * lean) + at(300, 1640, 1.9, ephialtes(c.t, kneel)));
};
const tent_map: SceneFn = (c) => {
  const trace = tween(c.local, c.beatT(0) - 0.3, c.dur - 0.2, 0, 1, (x) => x);
  const path = 'M160 1500 Q300 1300 380 1180 Q470 1040 640 1000 Q780 960 880 760';
  const len = 1100;
  let map = bg('M60 600 L1020 640 L1000 1700 L80 1660 Z', '#e8d6a0', 6) + `<path d="M60 1300 Q500 1200 1000 1260" stroke="#2f6f8e" stroke-width="40" fill="none" opacity=".6"/>` +
    bg('M120 1000 L300 760 L520 980 L700 700 L900 960 L980 900 L980 1200 L120 1200 Z', '#b59a6a', 4) +
    `<path d="${path}" stroke="#9b2b22" stroke-width="10" fill="none" stroke-dasharray="${len}" stroke-dashoffset="${(len * (1 - trace)).toFixed(0)}" stroke-linecap="round"/>`;
  const fx = 160 + trace * 720, fy = 1500 - trace * 740;
  map += at(fx, fy, 1.4, limb('M40 200 Q20 120 0 0', 22, '#cf9e72') + sh('ellipse', { cx: 0, cy: 0, rx: 16, ry: 22 }, '#cf9e72'));
  return L(c, 0.2, tentSet(c)) + L(c, 1, map);
};

// ---------- THE MOUNTAIN PATH (night) ----------
const path_night: SceneFn = (c) => {
  const climb = tween(c.local, 0, c.dur, 0, 1);
  let s = bg('M-200 2100 L-200 700 Q200 500 500 760 Q800 1000 1280 600 L1280 2100 Z', '#1c2a40', 5) + bg('M-200 2100 L-200 1200 Q300 1000 600 1260 Q900 1500 1280 1180 L1280 2100 Z', '#24344e', 5);
  const zig = (u: number) => [100 + Math.abs(((u * 4) % 2) - 1) * 880, 1900 - u * 1250];
  s += `<path d="M${zig(0).join(' ')} ${Array.from({ length: 40 }, (_, i) => 'L' + zig((i + 1) / 40).join(' ')).join(' ')}" stroke="#4a5a74" stroke-width="22" fill="none" stroke-linejoin="round"/>`;
  for (let i = 0; i < 18; i++) { const u = (i / 18 + climb * 0.12) % 1, [x, y] = zig(u); s += at(x, y, 0.2 + (1 - u) * 0.22, persian(c.t, i, { run: 0.5 }).replace(/#b5793a|#7a5a8e|#4f7a6a|#a8463a/g, '#2a2a3a')); }
  s += pine(180, 1500, 1.2, '#1a3020') + pine(900, 1300, 1.0, '#1a3020') + pine(600, 1800, 1.4, '#1a3020') + pine(80, 1100, 0.8, '#1a3020');
  return L(c, 0.05, sky(c, 'night', 820, 260)) + L(c, 1, s) + `<rect width="${W}" height="${H}" fill="#000" opacity="${(0.65 * (1 - tween(c.local, c.beatT(0) - 0.3, c.beatT(0) + 0.8, 0, 1))).toFixed(3)}"/>`;
};

// ---------- DAWN: SURROUNDED, THE LAST STAND, THE STONE, THE WEAPONS ----------
const pass_ridge: SceneFn = (c) => {
  const p = passSet(c, 'dawn'), turn = easeInOut(bt(c, 1, 0.35, 0.9)), show = easeInOut(bt(c, 2, 0.3, 0.8));
  let ridge = '';
  for (let i = 0; i < 9; i++) ridge += at(40 + i * 44, 620 + (i % 2) * 14, 0.26, persian(c.t, i, {}));
  return L(c, 0.05, p.sky) + LP(c, 0.4, p.mid + `<g opacity="${show.toFixed(2)}">${ridge}</g>`) + LP(c, 0.8, p.ground) +
    LP(c, 1, at(700, 2100, 1.6, `<g transform="scale(${(1 - 2 * turn).toFixed(3)} 1)">${leonidas.draw({ ...exch(c, 2, 'neutral', 'shocked'), breath: breathe(c.t, 5), blink: blinkAt(c.t, 5) })}</g>`));
};
const pass_resolve: SceneFn = (c) => {
  const p = passSet(c, 'dawn');
  const e = c.local < c.beatT(1) - 0.2 ? exch(c, 0, 'shocked', 'stern') : exch(c, 1, 'stern', 'sly');
  const nod = Math.sin(bt(c, 2, 0.1, 0.5) * Math.PI) * 10;
  return L(c, 0.05, p.sky) + LP(c, 0.3, p.far + p.mid) +
    LP(c, 1, at(540, 2380 + nod, 3.0, leonidas.draw({ ...e, armL: c.local >= c.beatT(3) - 0.3 ? 'point' : 'hold_spear', breath: breathe(c.t, 5), blink: blinkAt(c.t, 5) })));
};
const pass_allies: SceneFn = (c) => {
  const p = passSet(c, 'dawn'), go = tween(c.local, c.beatT(0) - 0.3, c.dur, 0, 1, (x) => x);
  let s = '';
  for (let i = 0; i < 12; i++) s += at(560 + i * 40 + go * 260, 1300 - i * 6 - go * 60, 0.2, spartan(c.t, i + 5, { helmet: 'up', shield: true }).replace(/#9b2b22/g, '#6a6a7a'));
  for (let i = 0; i < 5; i++) s += at(380 + i * 120, 1700, 0.62, spartan(c.t, i, { helmet: 'closed' }));
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid) + LP(c, 1, p.ground + s);
};
const pass_laststand: SceneFn = (c) => {
  const p = passSet(c, 'dawn'), turn = easeOutBack(bt(c, 0)), fill = easeInOut(bt(c, 1, 0.3, 1.2)), charge = easeInOut(bt(c, 3, 0.3, 1.4));
  let foes = '';
  for (let r = 0; r < 4; r++) for (let i = 0; i < 9; i++) foes += at(380 + i * 90, 1200 + r * 50 + 400 * (1 - fill), 0.22 + r * 0.04, persian(c.t, i + r * 9, { run: 0.4 }));
  let men = '';
  for (let i = 0; i < 6; i++) men += at(200 + i * 150, 1820 - 260 * charge, 0.9 - 0.3 * charge, spartan(c.t, i, { helmet: 'closed', arms: 'thrust', k: turn }));
  const dust = charge > 0 ? `<rect width="${W}" height="${H}" fill="#d9c3a0" opacity="${(0.5 * charge).toFixed(2)}"/>` : '';
  return L(c, 0.05, p.sky) + LP(c, 0.3, p.mid + p.ground + `<g opacity="${(0.3 + 0.7 * fill).toFixed(2)}">${foes}</g>`) + LP(c, 1, men + dust);
};
const pass_stone: SceneFn = (c) => {
  const carve = tween(c.local, c.beatT(0) - 0.3, c.beatT(0) + 1.4, 0, 1, (x) => x), gust = 1 + 2.5 * Math.sin(Math.min(1, bt(c, 1, 0.2, 1.4)) * Math.PI), dim = tween(c.local, c.beatT(2) - 0.3, c.dur, 0, 1);
  const p = passSet(c, 'dusk'), sway = Math.sin(c.t * 2) * 6 * gust;
  let grass = '';
  for (let i = 0; i < 26; i++) { const x = 60 + i * 40; grass += `<path d="M${x} 1900 q${(4 + sway).toFixed(1)} -40 ${(8 + sway * 1.6).toFixed(1)} -80" stroke="#6f8a44" stroke-width="5" fill="none" stroke-linecap="round"/>`; }
  const stone = bg('M300 1900 L320 1180 Q540 1100 760 1180 L780 1900 Z', '#c9bba0', 6) + [[1300, 320], [1360, 300], [1420, 320], [1480, 270]].map(([y, w], i) => `<path d="M380 ${y} l${w} 0" stroke="#6e5e48" stroke-width="6" stroke-linecap="round" stroke-dasharray="${w}" stroke-dashoffset="${(w * (1 - Math.max(0, Math.min(1, carve * 4 - i)))).toFixed(1)}"/>`).join('');
  return L(c, 0.05, p.sky) + LP(c, 0.3, p.far + p.mid) + LP(c, 1, stone + grass) + `<rect width="${W}" height="${H}" fill="#1a1020" opacity="${(0.38 * dim).toFixed(3)}"/>`;
};
const pass_weapons: SceneFn = (c) => {
  const p = passSet(c, 'dusk'), show = easeOutBack(bt(c, 1, 0.3, 0.8));
  const relic = at(760, 1250, 1.1 * (0.6 + 0.4 * show), pole(0, -560, 0, 0, '#8b5a2b') + sh('path', { d: 'M0 -610 L-10 -560 L10 -560 Z' }, '#bdbdbd') + aspis(-10, -120, 96, undefined, 'lambda'));
  return L(c, 0.05, p.sky) + LP(c, 0.2, p.far) + LP(c, 0.6, p.mid) + LP(c, 1, p.ground + relic) + `<rect width="${W}" height="${H}" fill="#ffb060" opacity="${(0.2 * tween(c.local, c.beatT(0) - 0.3, c.beatT(0) + 0.9, 0, 1)).toFixed(3)}"/>`;
};

export const SCENES: Record<string, SceneFn> = {
  army_vast, throne_offer, army_nations, pass_envoy, pass_scout, pass_comb, throne_laugh, pass_firm, pass_demand, pass_leonidas,
  pass_waves, pass_wall, pass_feint, throne_leap, pass_warning, pass_dienekes, pass_immortals, pass_dusk, tent_ephialtes, tent_map,
  path_night, pass_ridge, pass_resolve, pass_allies, pass_laststand, pass_stone, pass_weapons,
};
