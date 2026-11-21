// ============================================================================================================
// THEMISTOCLES of Athens (c. 524-459 BC) - the locked character (sheet: library/characters/themistocles).
// Design sources: the Ostia herm (Roman copy of a c. 470 BC Greek portrait): broad face, heavy brow, short full
// beard, short curly hair; Athenian citizen dress from Attic red-figure vases: cream chiton + draped himation.
// No armour: he wins with words and tricks. Colours only from sheet.json (r19).
// ============================================================================================================
import sheet from '../../../library/characters/themistocles/sheet.json';
import { head } from '../kit/cast';
import { limb, ln, sh, shade } from '../kit/core';
import { figure, part, type Look, type Pose } from './figure';

const C = sheet.look.parts, SKIN = sheet.look.skin, HAIR = sheet.look.hair.colour, BEARD = sheet.look.beard.colour;
export const LOOK: Look = { skin: SKIN, parts: C, build: sheet.look.build };
const ID = 'themistocles';

function body(): string {
  let s = limb('M-16 -84 L-18 -16', 19, SKIN) + limb('M16 -84 L18 -16', 19, SKIN);
  s += part(ID, 'boots', sh('ellipse', { cx: -22, cy: -9, rx: 20, ry: 10 }, C.boots) +
    sh('ellipse', { cx: 22, cy: -9, rx: 20, ry: 10 }, C.boots), C.boots);
  const chiton = 'M-46 -240 Q0 -250 46 -240 L56 -72 L-56 -72 Z';
  s += part(ID, 'tunic', sh('path', { d: chiton }, C.tunic) + shade(`<path d="${chiton}"/>`, 60, -150, 34, 110) +
    ln('M-34 -200 L-40 -78 M-12 -206 L-14 -76 M12 -206 L14 -76', 2.5, 'rgba(42,28,19,.22)'), C.tunic);
  // the himation: wool cloak wrapped round the body and thrown over the left shoulder (vase-painting drape)
  const drape = 'M-52 -244 Q-6 -150 58 -96 L60 -138 Q12 -178 -18 -248 Z';
  const wrap = 'M-58 -150 Q-20 -128 30 -98 L58 -96 L56 -72 L-58 -72 Z';
  s += part(ID, 'robe', sh('path', { d: wrap }, C.robe) + sh('path', { d: drape }, C.robe) +
    ln('M-40 -222 Q0 -150 52 -110 M-50 -132 Q-10 -112 40 -86', 3, 'rgba(42,28,19,.35)'), C.robe);
  s += part(ID, 'trim', ln('M-58 -78 L56 -78', 5, C.trim) + ln('M-18 -248 Q12 -178 60 -138', 4, C.trim), C.trim);
  return s;
}

function headPart(pose: Pose): string {
  let s = head(SKIN, pose.expr, { blink: pose.blink, to: pose.exprTo, mix: pose.exprMix });
  s += ln('M-34 -326 L-10 -322 M10 -322 L34 -326', 4, 'rgba(42,28,19,.5)');                                // the heavy brow ridge
  const beard = 'M-52 -284 Q-54 -236 -22 -222 Q0 -214 22 -222 Q54 -236 52 -284 Q38 -258 0 -256 Q-38 -258 -52 -284 Z';
  s += part(ID, 'beard', sh('path', { d: beard }, BEARD) +
    sh('path', { d: 'M-22 -266 Q-10 -276 0 -269 Q10 -276 22 -266 Q10 -261 0 -264 Q-10 -261 -22 -266 Z' }, BEARD), BEARD);
  s += ln('M-9 -253 Q0 -249 9 -253', 4);
  let curls = '';                                                                                           // short curly hair
  for (let i = 0; i < 9; i++) {
    const a = Math.PI * (0.08 + i * 0.105);
    curls += sh('circle', { cx: -Math.cos(a) * 54, cy: -306 - Math.sin(a) * 58, r: 13 }, HAIR);
  }
  s += part(ID, 'hair', sh('path', { d: 'M-60 -300 Q-64 -366 0 -368 Q64 -366 60 -300 Q50 -338 0 -340 Q-50 -338 -60 -300 Z' }, HAIR) + curls, HAIR);
  return s;
}

/** Themistocles in any pose. */
export function draw(pose: Pose): string {
  return figure(ID, LOOK, { armL: 'down', armR: 'hip', ...pose }, {
    back: '<ellipse cx="0" cy="-4" rx="72" ry="12" fill="rgba(0,0,0,.14)"/>',
    body: body(), head: headPart, sleeve: SKIN, mouthBg: BEARD,
  });
}
