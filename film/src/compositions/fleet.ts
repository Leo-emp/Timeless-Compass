// ============================================================================================================
// MOTION TEST SCENE: the Greek fleet under way, Spartan hoplites on the lead ship (engine + speed test only;
// a real video draws its own scenes fresh — rule r17). Port of spike/art_dir/scene_fleet_anim.html.
// drawFleet(t) returns the whole 1920x1080 picture for time t (seconds) as an SVG string.
// Motion (only what the line needs): parallax camera push, ship bob + rock, rowing oars in a ripple,
// breathing sail, sliding waves, far ships bobbing, gulls flapping, the commander blinking.
// ============================================================================================================
import { OUT, bg, ease, hand, limb, ln, resetIds, rng, sh, wrap } from '../kit/core';
import { aspis, corinthClosed, corinthKingUp, hair, head, hopliteBody, pole } from '../kit/cast';
import { card } from '../kit/tags';

const T = 8; // the camera push takes 8 s (then holds) so the 15-min speed test keeps a steady frame

const DEFS = `<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7fb4d6"/><stop offset=".6" stop-color="#cfe2e6"/><stop offset="1" stop-color="#f8e3b8"/></linearGradient>
  <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5fa6bd"/><stop offset=".5" stop-color="#2f7d9e"/><stop offset="1" stop-color="#1f5f80"/></linearGradient>
  <radialGradient id="sunGlow"><stop offset="0" stop-color="#fff8dc" stop-opacity="1"/><stop offset="1" stop-color="#fff8dc" stop-opacity="0"/></radialGradient>
</defs>`;

const cloud = (x: number, y: number, s: number) =>
  `<g transform="translate(${x} ${y}) scale(${s})">${bg('M0 40 Q-14 8 26 6 Q34 -22 72 -10 Q100 -34 132 -4 Q172 -6 166 40 Z', '#fdf7ec', 4)}<path d="M22 34 Q80 24 150 34" stroke="#d9e4e6" stroke-width="5" fill="none"/></g>`;

// Leonidas-like commander (test scene only; real named characters come from the character registry)
function commander(blink: boolean): string {
  const skin = '#dcae84';
  let s = `<ellipse cx="0" cy="-4" rx="80" ry="12" fill="rgba(0,0,0,.14)"/>` + hopliteBody(skin);
  s += sh('path', { d: 'M-46 -236 L-30 -222 L-46 -208 Z' }, '#d9b443');                     // cloak clasp
  s += pole(-82, -470, -82, -6, '#8b5a2b', 'cmd-spear') + sh('path', { d: 'M-82 -520 L-92 -470 L-72 -470 Z' }, '#bdbdbd');
  s += limb('M-44 -222 Q-80 -210 -82 -190', 20, skin) + hand(-82, -186, skin, 'cmd-spear');  // hand over the spear = grip
  s += aspis(64, -160);
  return s + head(skin, 'stern', { beard: '#2a1d14', blink }) + corinthKingUp();
}

function deckSpartan(skin: string, helmetUp: boolean, blink: boolean): string {
  let s = hopliteBody(skin, true);
  s += pole(-60, -500, -60, -20) + sh('path', { d: 'M-60 -548 L-70 -500 L-50 -500 Z' }, '#cfcfcf');
  s += limb('M-44 -222 Q-60 -214 -60 -200', 20, skin) + hand(-60, -196, skin);
  s += helmetUp ? head(skin, 'stern', { beard: '#2a1d14', blink }) + hair.corinthian() : head(skin, 'stern') + corinthClosed('fan');
  return s;
}

/** A trireme at time t, bow to the left, waterline y = 0. detail = near ship with crew; ph = phase offset. */
function trireme(t: number, detail: boolean, sailCol = '#efe2c4', ph = 0, blink = false): string {
  let s = '';
  const b = 10 * Math.sin(t * 1.4 + ph);                                                      // sail breathing
  s += `<path d="M480 8 Q700 30 1000 20 M460 16 Q700 50 980 54" stroke="#e6f6f8" stroke-width="10" fill="none" stroke-linecap="round" opacity="${0.7 + 0.15 * Math.sin(t * 3 + ph)}"/>`;
  s += `<path d="M10 -120 L10 -640" stroke="${OUT}" stroke-width="18" stroke-linecap="round"/><path d="M10 -120 L10 -640" stroke="#7a5230" stroke-width="9" stroke-linecap="round"/>`;
  s += bg('M-250 -600 L270 -600 L270 -588 L-250 -588 Z', '#6a4428', 4);
  s += bg(`M-236 -590 Q10 ${-560 + b} 256 -590 Q${290 + b} -440 250 -300 Q10 ${-330 + b} -230 -300 Q${-268 - b} -440 -236 -590 Z`, sailCol, 5);
  s += `<path d="M-150 -580 Q${-170 - b / 2} -440 -150 -310 M-60 -574 Q-74 -440 -60 -320 M80 -574 Q92 -440 80 -320 M170 -580 Q${190 + b / 2} -440 170 -310" stroke="#cdbf9c" stroke-width="4" fill="none"/>`;
  s += ln(`M-50 -360 L10 ${-520 + b / 2} L70 -360`, 22, '#a8322a');                            // lambda on the sail
  if (detail) {
    s += `<path d="M10 -640 L-470 -150 M10 -640 L470 -170" stroke="${OUT}" stroke-width="3" fill="none"/>`;
    for (let i = 0; i < 11; i++) {                                                            // crew behind the bulwark
      const x = -330 + i * 64, sway = 2 * Math.sin(t * 1.6 + i * 0.7);
      s += `<g transform="translate(${x} ${-40 + sway}) scale(.42)">${deckSpartan(['#d8a87c', '#dcae84', '#cf9e72'][i % 3], i === 0, blink)}</g>`;
    }
  }
  s += bg('M-470 -6 L-470 -42 Q-486 -112 -440 -128 L400 -128 Q478 -142 506 -210 Q524 -262 494 -304 Q540 -280 540 -210 Q538 -120 450 -40 Q300 4 -400 4 Z', '#5b3a26', 6);
  s += '<path d="M-466 -104 L420 -104 Q470 -110 500 -150" stroke="#b5452c" stroke-width="16" fill="none"/><path d="M-462 -80 L430 -80" stroke="#d8b36a" stroke-width="5" fill="none"/>';
  s += '<path d="M-470 -42 L-470 -6 L-400 4 L300 4 Q380 -4 450 -40 Z" fill="rgba(0,0,0,.22)"/>';
  for (let x = -400; x <= 400; x += 32) s += `<circle cx="${x}" cy="-56" r="6" fill="#2a1c13"/>`;   // oar ports
  s += bg('M-470 -14 L-572 -26 L-470 -40 Z', '#c99a45', 4);                                    // bronze ram
  s += bg('M-454 -96 Q-432 -112 -408 -96 Q-432 -82 -454 -96 Z', '#f4efe2', 3) + `<circle cx="-431" cy="-96" r="7" fill="${OUT}"/>`; // painted eye
  // oars: one stroke ~1.25 s; a small delay per oar makes the ripple run bow -> stern
  let i = 0;
  for (let x = -390; x <= 390; x += 32, i++) {
    const p = t * 2 * Math.PI * 0.8 + ph - i * 0.12;
    const bx = x - 70 + 34 * Math.sin(p);                    // sweep fore and aft
    const lift = Math.max(0, Math.cos(p));                   // return stroke: blade out of the water
    const by = 46 - 30 * lift;
    s += `<path d="M${x} -56 L${bx} ${by}" stroke="${OUT}" stroke-width="8" stroke-linecap="round"/><path d="M${x} -56 L${bx} ${by}" stroke="#c49a62" stroke-width="3.5" stroke-linecap="round"/>`;
    if (lift < 0.15) s += `<ellipse cx="${bx - 2}" cy="48" rx="${12 + 8 * (1 - lift)}" ry="5" fill="#e6f6f8" opacity=".9"/>`; // splash only while in the water
  }
  s += `<path d="M-580 -4 Q-520 ${-30 - 4 * Math.sin(t * 3 + ph)} -470 -10 Q-520 10 -600 14" stroke="#f2fbfc" stroke-width="10" fill="none" stroke-linecap="round"/>`;
  if (detail) {
    for (let k = 0; k < 14; k++) s += aspis(-390 + k * 58, -150, 30);                       // shields along the rail
    s += `<path d="M470 -150 L560 40" stroke="${OUT}" stroke-width="14" stroke-linecap="round"/><path d="M470 -150 L560 40" stroke="#8b5a2b" stroke-width="7" stroke-linecap="round"/>`;
    const hs = '#d8a87c';                                                                     // helmsman, both hands on the steering oar
    s += `<g transform="translate(450 -120) scale(.4)">${sh('path', { d: 'M-46 -238 Q0 -248 46 -238 L50 -120 L-50 -120 Z' }, '#e9dcc0')}${limb('M44 -222 Q90 -120 100 30', 18, hs)}${limb('M-44 -222 Q40 -120 90 6', 18, hs)}${hand(100, 30, hs)}${hand(90, 6, hs)}${head(hs, 'neutral', { beard: '#3a2a1e', blink })}${sh('path', { d: 'M-62 -296 Q-70 -372 0 -374 Q70 -372 62 -296 Q56 -330 30 -338 Q0 -330 -30 -338 Q-56 -330 -62 -296 Z' }, '#3a2a1e')}</g>`;
    s += `<g transform="translate(-412 -118) scale(.5)">${commander(blink)}</g>`;
  } else {
    for (let k = 0; k < 12; k++) s += `<circle cx="${-380 + k * 68}" cy="-140" r="22" fill="#b23a2a" stroke="${OUT}" stroke-width="5"/>`; // far shields read as red dots
  }
  return s;
}

/** Camera: zoom about the frame centre + drift, scaled by layer depth (0 = far, 1 = hero layer). */
function cam(t: number, depth: number, content: string): string {
  const k = ease(Math.min(1, t / T));
  const z = 1 + 0.07 * k * depth, dx = -26 * k * depth, dy = -10 * k * depth;
  return `<g transform="translate(${960 + dx} ${560 + dy}) scale(${z}) translate(-960 -560)">${content}</g>`;
}

/** The full frame at time t (seconds). */
export function drawFleet(t: number): string {
  resetIds();                                   // same ids on every machine
  const R = rng(1805);                          // same random layout every frame
  let sky = DEFS + '<rect x="-200" y="-200" width="2320" height="1480" fill="url(#sky)"/>';
  sky += `<circle cx="330" cy="300" r="${300 + 6 * Math.sin(t * 1.1)}" fill="url(#sunGlow)"/><circle cx="330" cy="300" r="58" fill="#fff6d6" stroke="#f0cf86" stroke-width="4"/>`;
  const cd = (v: number) => wrap(v, 2400) - 240;  // clouds drift and wrap (needed for the 15-min test)
  sky += cloud(cd(700 + t * 3), 90, 1.5) + cloud(cd(1180 + t * 2), 160, 1.1) + cloud(cd(1580 + t * 3), 180, 0.9) + cloud(cd(980 + t * 1.5), 300, 0.7) + cloud(cd(1700 + t * 2), 300, 0.8);
  let isl = bg('M-100 470 L90 420 L170 440 L260 390 L360 430 L460 410 L560 460 L560 480 L-100 480 Z', '#8fa3a0', 3);
  isl += bg('M1240 476 Q1320 420 1420 430 Q1500 400 1580 440 Q1660 430 1720 476 Z', '#9aaeab', 3);
  isl += `<path d="M300 420 l0 -18 l6 0 l0 18 M296 402 l14 0" stroke="${OUT}" stroke-width="2" fill="#e8e0cc"/>`;
  for (let i = 0; i < 5; i++) isl += `<rect x="${290 + i * 5}" y="404" width="2" height="16" fill="${OUT}"/>`;
  let sea = `<rect x="-200" y="476" width="2320" height="800" fill="url(#sea)"/><path d="M-200 476 L2120 476" stroke="${OUT}" stroke-width="3"/>`;
  sea += `<path d="M270 478 L400 478 L470 1180 L180 1180 Z" fill="#fff6d6" opacity="${0.14 + 0.05 * Math.sin(t * 2.3)}"/>`;
  for (let i = 0; i < 170; i++) {
    const y0 = 490 + Math.pow(R(), 1.4) * 600, x0 = R() * 2200, k = 0.4 + (y0 - 476) / 600 * 1.6, w = 12 * k + R() * 14 * k;
    const x = wrap(x0 + t * 30 * k, 2300) - 200, y = y0 + 3 * k * Math.sin(t * 2 + x0);
    sea += `<path d="M${x} ${y} q${w / 2} ${-5 * k} ${w} 0" stroke="#d8f0f4" stroke-width="${2 + k * 1.6}" fill="none" stroke-linecap="round" opacity="${0.55 + 0.25 * Math.sin(t * 3 + i)}"/>`;
  }
  let fleet = '';
  const far: [number, number, number][] = [[1500, 520, 0.16], [1260, 540, 0.2], [1000, 566, 0.25], [720, 600, 0.32], [1700, 560, 0.22], [1480, 610, 0.3]];
  far.sort((a, b) => a[1] - b[1]).forEach(([x, y, k], i) => {
    const ph = i * 1.7, bob = 16 * k * Math.sin(t * 1.5 + ph), rot = 0.8 * Math.sin(t * 1.2 + ph);
    const fx = wrap(x - t * 40 * k + 400, 2400) - 400;              // creep forward, wrap round in long tests
    fleet += `<g transform="translate(${fx} ${y + bob}) rotate(${rot}) scale(${k})">${trireme(t, false, i % 2 ? '#efe2c4' : '#e8d0a8', ph)}</g>`;
  });
  const bob = 7 * Math.sin(t * 1.5), rock = 0.7 * Math.sin(t * 1.2 + 0.6);
  const tm = t % 8;                                                // blink twice in every 8 s
  const blink = (tm > 2.4 && tm < 2.56) || (tm > 6.1 && tm < 6.26);
  const hero = `<g transform="translate(980 ${960 + bob}) rotate(${rock}) scale(1.02)">${trireme(t, true, '#efe2c4', 0, blink)}</g>`;
  let fore = '';
  ([[260, 640, 1.4], [420, 700, 1], [1760, 720, 1.2], [1600, 640, 0.8]] as [number, number, number][]).forEach(([x, y, k], i) => {
    const f = 10 * Math.sin(t * 7 + i * 2), gx = wrap(x + t * (14 + i * 4), 2200) - 140, gy = y + 6 * Math.sin(t * 1.3 + i);
    fore += `<g transform="translate(${gx} ${gy}) scale(${k})"><path d="M-26 ${-f * 0.3} Q-14 ${-14 - f} 0 0 Q14 ${-14 - f} 26 ${-f * 0.3}" stroke="${OUT}" stroke-width="6" fill="none" stroke-linecap="round"/><path d="M-24 ${-f * 0.3} Q-14 ${-11 - f} -2 -1 M2 -1 Q14 ${-11 - f} 24 ${-f * 0.3}" stroke="#fafafa" stroke-width="2.5" fill="none" stroke-linecap="round"/></g>`;
  });
  for (let i = 0; i < 30; i++) { const x = wrap(R() * 2200 + t * 60, 2300) - 200, y = 1000 + R() * 80; fore += `<path d="M${x} ${y} q14 -8 28 0" stroke="#e6f6f8" stroke-width="5" fill="none" stroke-linecap="round"/>`; }
  // place + date card: fixed to the screen (not the camera), fades in over the first second
  const label = card(1410, 50, 460, 62, 'THE GREEK FLEET · 480 BC', 27, Math.min(1, t / 1));
  return cam(t, 0.05, sky) + cam(t, 0.15, isl) + cam(t, 0.5, sea) + cam(t, 0.4, fleet) + cam(t, 1, hero) + cam(t, 1.2, fore) + label;
}
