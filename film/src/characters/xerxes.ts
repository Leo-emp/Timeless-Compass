// ============================================================================================================
// XERXES I, King of Kings (c. 518-465 BC) - the locked character (sheet: library/characters/xerxes).
// Design sources: Persepolis reliefs (Treasury audience relief, Gate of All Nations): long squared beard in rows
// of tight curls, curled hair bunched at the nape, crenellated royal crown, long court robe with wide sleeves.
// Colours only from sheet.json (r19). Default pose: golden sceptre in the near hand.
// ============================================================================================================
import sheet from '../../../library/characters/xerxes/sheet.json';
import { head, pole } from '../kit/cast';
import { ln, sh, shade } from '../kit/core';
import { figure, part, type Look, type Pose } from './figure';

const C = sheet.look.parts, SKIN = sheet.look.skin, HAIR = sheet.look.hair.colour, BEARD = sheet.look.beard.colour;
export const LOOK: Look = { skin: SKIN, parts: C, build: sheet.look.build };
const ID = 'xerxes';

function body(): string {
  let s = part(ID, 'boots', sh('ellipse', { cx: -26, cy: -8, rx: 22, ry: 10 }, C.boots) +
    sh('ellipse', { cx: 26, cy: -8, rx: 22, ry: 10 }, C.boots), C.boots);
  const robe = 'M-50 -240 Q0 -252 50 -240 Q64 -120 84 -14 L-84 -14 Q-64 -120 -50 -240 Z';                   // floor-length court robe
  s += part(ID, 'robe', sh('path', { d: robe }, C.robe) + shade(`<path d="${robe}"/>`, 74, -120, 50, 140) +
    ln('M-30 -150 Q-46 -80 -60 -20 M30 -150 Q46 -80 60 -20 M-10 -140 L-14 -18', 3, 'rgba(20,0,30,.35)'), C.robe);  // pleats
  s += part(ID, 'trim', ln('M-82 -26 L82 -26', 8, C.trim) + ln('M0 -238 L0 -30', 9, C.trim) +
    ln('M-46 -236 Q0 -220 46 -236', 6, C.trim), C.trim);
  return s;
}

function headPart(pose: Pose): string {
  let s = part(ID, 'hair', sh('ellipse', { cx: -46, cy: -244, rx: 22, ry: 26 }, HAIR) +
    sh('ellipse', { cx: 46, cy: -244, rx: 22, ry: 26 }, HAIR), HAIR);                                     // hair bunched at the nape
  s += head(SKIN, pose.expr, { blink: pose.blink });
  // the long squared Persian beard, worked in rows of tight curls
  const beard = 'M-50 -284 L-50 -176 Q0 -160 50 -176 L50 -284 Q32 -256 0 -254 Q-32 -256 -50 -284 Z';
  let curls = '';
  for (let r = 0; r < 5; r++) {                         // staggered rows of small spiral curls, as on the reliefs
    const n = r % 2 ? 5 : 6, x0 = r % 2 ? -32 : -40;
    for (let c = 0; c < n; c++) { const x = x0 + c * 16, y = -240 + r * 14; curls += `<path d="M${x - 4} ${y} q4 -6 8 0 q-2 5 -6 2" fill="none" stroke="#4a3e34" stroke-width="2.5" stroke-linecap="round"/>`; }
  }
  s += part(ID, 'beard', sh('path', { d: beard }, BEARD) + curls +
    sh('path', { d: 'M-26 -266 Q-12 -278 0 -270 Q12 -278 26 -266 Q12 -260 0 -264 Q-12 -260 -26 -266 Z' }, BEARD), BEARD);
  s += ln('M-9 -253 Q0 -249 9 -253', 4);
  s += part(ID, 'hair', sh('path', { d: 'M-60 -304 Q-64 -352 0 -354 Q64 -352 60 -304 Q48 -334 0 -336 Q-48 -334 -60 -304 Z' }, HAIR), HAIR);
  let cren = 'M-52 -334 L-52 -396';                                                                         // crenellated gold crown
  for (let i = 0; i < 7; i++) { const x = -52 + i * 14.86; cren += ` L${x + 7.43} -396 L${x + 7.43} -382 L${x + 14.86} -382 L${x + 14.86} -396`; }
  cren += ' L52 -334 Z';
  s += part(ID, 'crown', sh('path', { d: cren }, C.crown) + ln('M-52 -350 L52 -350', 3, '#a8822a'), C.crown);
  return s;
}

/** Xerxes in any pose. */
export function draw(pose: Pose): string {
  const p: Pose = { armL: 'hold_spear', armR: 'down', ...pose };
  const sceptre = p.armL === 'hold_spear';
  const front = sceptre ? part(ID, 'trim', pole(-82, -420, -82, -30, C.trim, 'sceptre') + sh('circle', { cx: -82, cy: -428, r: 13 }, C.trim), C.trim) : '';
  return figure(ID, LOOK, { ...p, holds: sceptre ? 'sceptre' : p.holds }, {
    back: '<ellipse cx="0" cy="-4" rx="86" ry="12" fill="rgba(0,0,0,.14)"/>',
    body: body(), head: headPart, front, sleeve: C.robe, mouthBg: BEARD,
  });
}
