// ============================================================================================================
// STYLE KIT — CAST PARTS (generic building blocks for characters; named characters live in the character
// registry, plan 3 / rule r19)
// ------------------------------------------------------------------------------------------------------------
// Approved construction (rule r16, cast sheet v1, 2026-11-21):
//   - big round head ≈ 40% of body height, small solid dot eyes, short thick brows, a tiny nose
//   - the emotion lives in the brows + mouth (six base expressions)
//   - costume carries the era: helmets, crowns, wigs, beards are separate pieces drawn over the head
// Coordinates: every figure stands with its feet at y = 0, centred on x = 0; the head centre is (0, -300),
// radius ~60. Scenes place figures with <g transform="translate(x y) scale(s)">.
// Ported from spike/art_dir/cast_lib.js + cast_lib2.js.
// ============================================================================================================
import { OUT, sh, ln, limb, shade } from './core';

export type Expr = 'neutral' | 'stern' | 'worried' | 'shocked' | 'sly' | 'grief';
export const EXPRESSIONS: Expr[] = ['neutral', 'stern', 'worried', 'shocked', 'sly', 'grief'];

export interface HeadOpts {
  age?: boolean;   // forehead + cheek wrinkles for older characters
  beard?: string;  // colour of a short beard (big flowing beards use bigBeard)
  blink?: boolean; // eyelids closed this frame
  extra?: boolean; // a background extra (crowd, crew behind a rail): may be partly hidden (still check)
  to?: Expr;       // expression being changed to (cross-fade, no snap - rule r29)
  mix?: number;    // 0..1 progress of that change
}

// ---------- head + face ----------
/** The shared head: ears, round face, one soft shade, faint cheeks, the expression, optional wrinkles/beard/blink. */
export function head(skin: string, ex: Expr = 'neutral', opt: HeadOpts = {}): string {
  // one group = one face for the still check; acting faces must never be covered, extras may be
  let s = `<g data-role="face"${opt.extra ? ' data-acting="false"' : ''}>`;
  s += sh('ellipse', { cx: -58, cy: -296, rx: 11, ry: 15 }, skin) + sh('ellipse', { cx: 58, cy: -296, rx: 11, ry: 15 }, skin); // ears first
  s += sh('ellipse', { cx: 0, cy: -300, rx: 60, ry: 63 }, skin);
  s += shade('<ellipse cx="0" cy="-300" rx="57" ry="60"/>', 52, -296, 42, 70);                    // shade on the right cheek
  s += '<ellipse cx="-30" cy="-280" rx="11" ry="6" fill="rgba(230,110,90,.22)"/><ellipse cx="30" cy="-280" rx="11" ry="6" fill="rgba(230,110,90,.22)"/>';
  if (opt.to && opt.mix !== undefined && opt.mix > 0 && opt.to !== ex) {
    // cross-fade between two expressions over a few frames: a face never snaps from one emotion to another
    const m = Math.min(1, opt.mix);
    s += m < 1 ? `<g opacity="${(1 - m).toFixed(3)}">${face(ex)}</g><g opacity="${m.toFixed(3)}">${face(opt.to)}</g>` : face(opt.to);
  } else {
    s += face(ex);
  }
  if (opt.blink) {                                                                                    // lids over the eyes
    s += `<ellipse cx="-21" cy="-300" rx="11" ry="14" fill="${skin}"/><ellipse cx="21" cy="-300" rx="11" ry="14" fill="${skin}"/>`;
    s += ln('M-30 -299 Q-21 -293 -12 -299', 4.5) + ln('M12 -299 Q21 -293 30 -299', 4.5);
  }
  if (opt.age) s += ln('M-40 -322 Q-30 -326 -20 -322', 2.5) + ln('M20 -322 Q30 -326 40 -322', 2.5) +
                    ln('M-46 -284 Q-42 -276 -44 -268', 2.5) + ln('M46 -284 Q42 -276 44 -268', 2.5);
  if (opt.beard) s += sh('path', { d: 'M-50 -282 Q-48 -232 0 -226 Q48 -232 50 -282 Q40 -258 0 -256 Q-40 -258 -50 -282 Z' }, opt.beard);
  return s + '</g>';
}

/** Eyes, brows, nose and mouth for one expression. */
export function face(ex: Expr): string {
  const eyeY = -300;
  const eye = (x: number, ry = 9) => `<ellipse cx="${x}" cy="${eyeY}" rx="6.5" ry="${ry}" fill="${OUT}"/><circle cx="${x - 2}" cy="${eyeY - 3}" r="2" fill="#fff"/>`;
  let s = ln('M-3 -288 Q3 -284 -1 -279', 3.5);                                                         // nose
  switch (ex) {
    case 'neutral':
      s += eye(-21) + eye(21) + ln('M-31 -322 L-12 -321', 6) + ln('M12 -321 L31 -322', 6) + ln('M-10 -264 Q0 -260 10 -264', 4.5); break;
    case 'stern':   // inner brow ends pushed down
      s += eye(-21, 8) + eye(21, 8) + ln('M-33 -331 L-11 -318', 7) + ln('M11 -318 L33 -331', 7) + ln('M-13 -259 Q0 -266 13 -259', 5); break;
    case 'worried': // inner brow ends raised, wobbly mouth, sweat drop
      s += eye(-21) + eye(21) + ln('M-32 -318 L-11 -330', 6) + ln('M11 -330 L32 -318', 6) + ln('M-12 -262 Q-6 -267 0 -262 Q6 -257 12 -262', 4.5);
      s += `<path d="M56 -342 Q64 -326 56 -320 Q48 -326 56 -342 Z" fill="#8fc6e8" stroke="${OUT}" stroke-width="3.5"/>`; break;
    case 'shocked': // bigger eyes, high brows, open mouth
      s += `<ellipse cx="-21" cy="${eyeY}" rx="9" ry="12" fill="${OUT}"/><ellipse cx="21" cy="${eyeY}" rx="9" ry="12" fill="${OUT}"/><circle cx="-24" cy="-305" r="2.5" fill="#fff"/><circle cx="18" cy="-305" r="2.5" fill="#fff"/>`;
      s += ln('M-32 -334 Q-21 -340 -10 -334', 6) + ln('M10 -334 Q21 -340 32 -334', 6) + sh('ellipse', { cx: 0, cy: -260, rx: 9, ry: 12 }, '#7a2b22'); break;
    case 'sly':     // one brow up, half-closed eyes, smirk
      s += ln('M-29 -301 Q-21 -296 -13 -301', 5) + ln('M13 -301 Q21 -296 29 -301', 5) + ln('M-31 -318 L-12 -317', 6) +
           ln('M12 -326 Q22 -332 32 -324', 6) + ln('M-10 -264 Q4 -262 14 -270', 4.5); break;
    case 'grief':   // brows up in the middle, eyes down, a tear
      s += `<ellipse cx="-21" cy="-296" rx="6" ry="7" fill="${OUT}"/><ellipse cx="21" cy="-296" rx="6" ry="7" fill="${OUT}"/>`;
      s += ln('M-31 -316 L-12 -326', 6) + ln('M12 -326 L31 -316', 6) + ln('M-11 -258 Q0 -266 11 -258', 4.5);
      s += '<path d="M-24 -288 Q-21 -278 -24 -272" stroke="#8fc6e8" stroke-width="4" fill="none" stroke-linecap="round"/>'; break;
  }
  return s;
}

/** Eyelash flicks for female faces (draw after the head). */
export const lashes = (): string => ln('M-28 -306 L-34 -312', 3.5) + ln('M28 -306 L34 -312', 3.5);

// ---------- hair + headgear ----------
export const hair = {
  /** Edo/Sengoku topknot: shaved crown, hair on the sides, small knot on top. */
  chonmage: (): string => sh('path', { d: 'M-60 -292 Q-64 -330 -46 -344 L-40 -318 Q-50 -306 -52 -284 Z' }, '#22201f') +
    sh('path', { d: 'M60 -292 Q64 -330 46 -344 L40 -318 Q50 -306 52 -284 Z' }, '#22201f') +
    sh('rect', { x: -8, y: -388, width: 16, height: 34, rx: 8 }, '#22201f') + ln('M-8 -362 L8 -362', 3, '#c9b27a'),
  /** Sengoku kabuto: lacquered bowl, flared neck guard, turned-back flaps, gold crescent crest. */
  kabuto: (): string => sh('path', { d: 'M-70 -318 Q-92 -290 -96 -262 L-62 -276 L-60 -318 Z' }, '#7a1f1a') +
    sh('path', { d: 'M70 -318 Q92 -290 96 -262 L62 -276 L60 -318 Z' }, '#7a1f1a') +
    ln('M-66 -300 L-90 -286', 3.5) + ln('M66 -300 L90 -286', 3.5) +
    sh('path', { d: 'M-68 -316 Q-68 -380 0 -384 Q68 -380 68 -316 Z' }, '#2b2a33') +
    ln('M-40 -372 L-42 -318', 3, '#55546a') + ln('M0 -384 L0 -318', 3, '#55546a') + ln('M40 -372 L42 -318', 3, '#55546a') +
    sh('path', { d: 'M-74 -318 Q0 -326 74 -318 L74 -306 Q0 -314 -74 -306 Z' }, '#2b2a33') +
    sh('path', { d: 'M-30 -330 Q-62 -392 -40 -440 Q-46 -386 0 -350 Q46 -386 40 -440 Q62 -392 30 -330 Z' }, '#e0b347'),
  /** Greek Corinthian helmet pushed up (face visible), red horsehair fan crest. */
  corinthian: (): string => sh('path', { d: 'M-64 -404 Q-66 -488 0 -492 Q66 -488 64 -404 Q40 -436 0 -438 Q-40 -436 -64 -404 Z' }, '#b23a2a') +
    ln('M-40 -440 Q-44 -470 -20 -480 M0 -440 L0 -488 M40 -440 Q44 -470 20 -480', 2.5, '#7e2419') +
    sh('path', { d: 'M-62 -330 Q-66 -404 0 -408 Q66 -404 62 -330 L48 -326 L44 -350 L-44 -350 L-48 -326 Z' }, '#c99a45') +
    ln('M-44 -350 L44 -350', 3, '#8a6427') +
    shade('<path d="M-62 -330 Q-66 -404 0 -408 Q66 -404 62 -330 Z"/>', 50, -370, 40, 60, 'rgba(90,50,10,.2)') +
    sh('rect', { x: -8, y: -428, width: 16, height: 24, rx: 3 }, '#8a6427'),
  /** Roman senator: short greying hair combed forward. */
  roman: (): string => sh('path', { d: 'M-60 -300 Q-66 -366 0 -368 Q66 -366 60 -300 Q56 -334 30 -340 Q0 -332 -30 -340 Q-56 -334 -60 -300 Z' }, '#9c958d') +
    ln('M-30 -340 L-26 -330', 3) + ln('M-6 -336 L-4 -326', 3) + ln('M18 -338 L16 -328', 3),
  /** Egyptian New Kingdom wig: black bob with straight fringe. */
  wig: (): string => sh('path', { d: 'M-70 -240 Q-80 -380 0 -376 Q80 -380 70 -240 L48 -240 L50 -300 Q46 -330 30 -334 L-30 -334 Q-46 -330 -50 -300 L-48 -240 Z' }, '#1c1a22') +
    ln('M-60 -300 L-60 -250', 2.5, '#3a3846') + ln('M60 -300 L60 -250', 2.5, '#3a3846'),
  /** 1950s fedora. */
  fedora: (): string => sh('path', { d: 'M-58 -300 Q-62 -340 -40 -346 L40 -346 Q62 -340 58 -300 Z' }, '#4b3a2a') +
    sh('ellipse', { cx: 0, cy: -346, rx: 88, ry: 16 }, '#3b2e22') +
    sh('path', { d: 'M-50 -348 Q-50 -404 0 -398 Q50 -404 50 -348 Z' }, '#3b2e22') +
    ln('M0 -398 L0 -386', 4) + sh('rect', { x: -50, y: -364, width: 100, height: 14, rx: 3 }, '#1f1814'),
};

/** Closed Corinthian helmet (battle look): face hidden, T-opening, dark eye slits with a glint. */
export function corinthClosed(crest: 'fan' | 'king' | 'none' = 'fan'): string {
  let s = '';
  if (crest === 'fan') s += sh('path', { d: 'M-64 -404 Q-66 -488 0 -492 Q66 -488 64 -404 Q40 -436 0 -438 Q-40 -436 -64 -404 Z' }, '#b23a2a') +
    sh('rect', { x: -8, y: -428, width: 16, height: 24, rx: 3 }, '#8a6427');
  if (crest === 'king') s += sh('path', { d: 'M-104 -392 Q0 -466 104 -392 Q0 -420 -104 -392 Z' }, '#b23a2a') +
    ln('M-70 -410 L-60 -396 M-36 -424 L-30 -406 M0 -430 L0 -412 M36 -424 L30 -406 M70 -410 L60 -396', 2.5, '#7e2419') +
    sh('rect', { x: -8, y: -418, width: 16, height: 24, rx: 3 }, '#8a6427');
  const d = 'M-66 -244 Q-72 -384 0 -388 Q72 -384 66 -244 L24 -240 L20 -282 L8 -290 L8 -242 L-8 -242 L-8 -290 L-20 -282 L-24 -240 Z';
  s += sh('path', { d }, '#c99a45') + shade(`<path d="${d}"/>`, 56, -300, 40, 90, 'rgba(90,50,10,.22)');
  s += '<path d="M-44 -318 Q-26 -326 -8 -312 L-8 -300 Q-26 -304 -44 -302 Z" fill="#20140c"/><path d="M44 -318 Q26 -326 8 -312 L8 -300 Q26 -304 44 -302 Z" fill="#20140c"/>';
  s += '<circle cx="-24" cy="-309" r="3" fill="#fff"/><circle cx="24" cy="-309" r="3" fill="#fff"/>';
  return s + ln('M-50 -340 Q0 -352 50 -340', 3, '#8a6427');
}

/** Open helmet with a side-to-side (transverse) crest = officer / king. */
export function corinthKingUp(): string {
  return sh('path', { d: 'M-104 -398 Q0 -476 104 -398 Q0 -426 -104 -398 Z' }, '#b23a2a') +
    ln('M-70 -416 L-60 -402 M-36 -430 L-30 -412 M0 -436 L0 -418 M36 -430 L30 -412 M70 -416 L60 -402', 2.5, '#7e2419') +
    sh('path', { d: 'M-62 -330 Q-66 -404 0 -408 Q66 -404 62 -330 L48 -326 L44 -350 L-44 -350 L-48 -326 Z' }, '#c99a45') +
    ln('M-44 -350 L44 -350', 3, '#8a6427') +
    shade('<path d="M-62 -330 Q-66 -404 0 -408 Q66 -404 62 -330 Z"/>', 50, -370, 40, 60, 'rgba(90,50,10,.2)') +
    sh('rect', { x: -8, y: -424, width: 16, height: 24, rx: 3 }, '#8a6427');
}

/** Big flowing beard + moustache; the mouth is redrawn on top so the face can still act. */
export function bigBeard(col: string, curls?: string): string {
  let s = sh('path', { d: 'M-58 -292 Q-70 -206 -30 -180 Q0 -164 30 -180 Q70 -206 58 -292 Q42 -258 0 -256 Q-42 -258 -58 -292 Z' }, col);
  s += sh('path', { d: 'M-28 -266 Q-14 -280 0 -270 Q14 -280 28 -266 Q14 -258 0 -263 Q-14 -258 -28 -266 Z' }, col);
  if (curls) s += ln('M-40 -230 q6 8 0 14 M-14 -218 q6 8 0 14 M14 -218 q6 8 0 14 M40 -230 q6 8 0 14', 3, curls);
  return s + ln('M-9 -254 Q0 -250 9 -254', 4);
}
/** Long hair falling behind the shoulders — draw BEFORE the head. */
export const longHairBack = (col: string): string =>
  sh('path', { d: 'M-66 -300 Q-76 -384 0 -382 Q76 -384 66 -300 L74 -190 Q44 -180 42 -226 L-42 -226 Q-44 -180 -74 -190 Z' }, col);
/** Fringe/top of the same long hair — draw AFTER the head. */
export const longHairTop = (col: string): string =>
  sh('path', { d: 'M-62 -296 Q-66 -374 0 -374 Q66 -374 62 -296 Q52 -338 10 -340 Q-26 -336 -44 -312 Q-54 -304 -62 -296 Z' }, col);

// ---------- royal + divine pieces ----------
export const crown = (jewel = '#b02a2a'): string =>
  sh('path', { d: 'M-46 -346 L-48 -398 L-28 -370 L-14 -406 L0 -374 L14 -406 L28 -370 L48 -398 L46 -346 Z' }, '#e2b23f') +
  sh('circle', { cx: 0, cy: -358, r: 7 }, jewel) + sh('circle', { cx: -28, cy: -356, r: 5 }, '#2f6fb0') + sh('circle', { cx: 28, cy: -356, r: 5 }, '#2f6fb0');
export const tiara = (): string => sh('path', { d: 'M-38 -348 Q0 -392 38 -348 Q0 -364 -38 -348 Z' }, '#e9c25a') + sh('circle', { cx: 0, cy: -372, r: 6 }, '#d0507a');
export const circlet = (): string => sh('path', { d: 'M-56 -336 Q0 -350 56 -336 L56 -326 Q0 -340 -56 -326 Z' }, '#e2b23f') + sh('circle', { cx: 0, cy: -340, r: 5 }, '#2f6fb0');
export function laurel(): string {
  let s = '';
  for (let i = 0; i < 5; i++) {
    const x = -50 + i * 12, y = -338 - i * 5;
    s += sh('ellipse', { cx: x, cy: y, rx: 9, ry: 5, transform: `rotate(-30 ${x} ${y})` }, '#d9b443');
    s += sh('ellipse', { cx: -x, cy: y, rx: 9, ry: 5, transform: `rotate(30 ${-x} ${y})` }, '#d9b443');
  }
  return s;
}
/** Divine glow behind a god; gradientId must be defined in the scene's <defs>. */
export const aura = (gradientId: string): string => `<ellipse cx="0" cy="-250" rx="190" ry="270" fill="url(#${gradientId})"/>`;
/** Soft contact shadow under the feet. */
export const shadow = (rx = 70): string => `<ellipse cx="0" cy="-4" rx="${rx}" ry="12" fill="rgba(0,0,0,.14)"/>`;
/** Floor-length gown/robe (hides legs) with an optional hem trim colour. */
export function gown(col: string, trim?: string): string {
  const d = 'M-44 -238 Q0 -248 44 -238 Q58 -120 80 -8 L-80 -8 Q-58 -120 -44 -238 Z';
  return sh('path', { d }, col) + shade(`<path d="${d}"/>`, 70, -120, 50, 140) + (trim ? ln('M-78 -22 L78 -22', 6, trim) : '') +
    ln('M-20 -150 L-36 -16 M16 -150 L30 -16', 3, 'rgba(42,28,19,.35)');
}

// ---------- weapons + soldier bodies ----------
/** A held pole weapon (spear, trident, sceptre). Draw the shaft FIRST, then the hand on top (grip rule). */
export const pole = (x1: number, y1: number, x2: number, y2: number, col = '#8b5a2b', id?: string): string =>
  `<g data-role="prop"${id ? ` data-id="${id}"` : ''}>` + ln(`M${x1} ${y1} L${x2} ${y2}`, 10, OUT) + ln(`M${x1} ${y1} L${x2} ${y2}`, 5, col) + '</g>';

/** Shield devices (episemata): Spartans carried the lambda; Athenians painted personal blazons (vase paintings). */
export type Device = 'lambda' | 'owl' | 'star' | 'crescent' | 'none';

/** Greek bronze shield (aspis) with a painted device; everything scales with the radius. */
export function aspis(cx: number, cy: number, r = 84, id?: string, device: Device = 'lambda'): string {
  const k = r / 84, paint = '#efe0b8';
  let dev = '';
  if (device === 'lambda') dev = ln(`M${cx - 30 * k} ${cy + 38 * k} L${cx} ${cy - 40 * k} L${cx + 30 * k} ${cy + 38 * k}`, 12 * k, paint);
  if (device === 'owl') dev = `<circle cx="${cx - 16 * k}" cy="${cy - 8 * k}" r="${13 * k}" fill="${paint}" stroke="${OUT}" stroke-width="${3 * k}"/>` +
    `<circle cx="${cx + 16 * k}" cy="${cy - 8 * k}" r="${13 * k}" fill="${paint}" stroke="${OUT}" stroke-width="${3 * k}"/>` +
    `<circle cx="${cx - 16 * k}" cy="${cy - 8 * k}" r="${5 * k}" fill="${OUT}"/><circle cx="${cx + 16 * k}" cy="${cy - 8 * k}" r="${5 * k}" fill="${OUT}"/>` +
    ln(`M${cx - 6 * k} ${cy + 10 * k} L${cx} ${cy + 22 * k} L${cx + 6 * k} ${cy + 10 * k}`, 4 * k, paint);
  if (device === 'star') { let d = ''; for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; d += `M${cx} ${cy} L${(cx + Math.cos(a) * 36 * k).toFixed(1)} ${(cy + Math.sin(a) * 36 * k).toFixed(1)} `; } dev = ln(d, 7 * k, paint); }
  if (device === 'crescent') dev = `<path d="M${cx - 10 * k} ${cy - 34 * k} A ${36 * k} ${36 * k} 0 1 0 ${cx - 10 * k} ${cy + 34 * k} A ${26 * k} ${28 * k} 0 1 1 ${cx - 10 * k} ${cy - 34 * k} Z" fill="${paint}" stroke="${OUT}" stroke-width="${3 * k}"/>`;
  return `<g data-role="prop"${id ? ` data-id="${id}"` : ''}>` + sh('circle', { cx, cy, r }, '#c99a45') + sh('circle', { cx, cy, r: r * 0.81 }, '#b23a2a') +
    shade(`<circle cx="${cx}" cy="${cy}" r="${r}"/>`, cx + 56 * k, cy + 10 * k, 50 * k, 100 * k, 'rgba(70,30,10,.18)') + dev + '</g>';
}

/** Hoplite lower body + linothorax with pteruges strips, optional red cloak behind. */
export function hopliteBody(skin: string, cloak = true): string {
  let s = '';
  if (cloak) s += sh('path', { d: 'M-46 -236 Q-84 -120 -74 -40 L74 -40 Q84 -120 46 -236 Z' }, '#9b2b22');
  s += limb('M-18 -90 L-20 -16', 20, skin) + limb('M18 -90 L20 -16', 20, skin);
  s += sh('path', { d: 'M-32 -78 L-30 -24 L-8 -24 L-8 -78 Z' }, '#c99a45') + sh('path', { d: 'M32 -78 L30 -24 L8 -24 L8 -78 Z' }, '#c99a45'); // greaves
  s += sh('ellipse', { cx: -24, cy: -9, rx: 20, ry: 10 }, '#6a4a30') + sh('ellipse', { cx: 24, cy: -9, rx: 20, ry: 10 }, '#6a4a30');   // sandals
  for (let i = -3; i <= 3; i++) s += sh('rect', { x: i * 15 - 7, y: -122, width: 14, height: 42, rx: 3 }, '#efe6cf');           // pteruges
  const d = 'M-46 -238 Q0 -248 46 -238 L50 -120 L-50 -120 Z';
  s += sh('path', { d }, '#efe6cf') + shade(`<path d="${d}"/>`, 52, -180, 34, 80) + ln('M-48 -150 L48 -150', 4, '#b23a2a') + ln('M-44 -214 L44 -214', 3, '#c99a45');
  return s;
}
