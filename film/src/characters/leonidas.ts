// ============================================================================================================
// LEONIDAS I, king of Sparta (c. 540-480 BC) - the locked character (sheet: library/characters/leonidas).
// Design sources: the "Leonidas" marble hoplite head from Sparta (strong brow, straight nose, full beard);
// Herodotus 7.208-209 (long hair, combed before battle); transverse crest = officer/king on vase paintings.
// Colours come ONLY from sheet.json (imported), so he is identical in every shot of every video (r19).
// Default pose: spear in the near hand, shield on the far arm.
// ============================================================================================================
import sheet from '../../../library/characters/leonidas/sheet.json';
import { aspis, corinthKingUp, head, pole } from '../kit/cast';
import { limb, ln, sh, shade } from '../kit/core';
import { figure, part, type Look, type Pose } from './figure';

const C = sheet.look.parts, SKIN = sheet.look.skin, HAIR = sheet.look.hair.colour, BEARD = sheet.look.beard.colour;
export const LOOK: Look = { skin: SKIN, parts: C, build: sheet.look.build };
const ID = 'leonidas';

function body(): string {
  let s = limb('M-18 -90 L-20 -16', 20, SKIN) + limb('M18 -90 L20 -16', 20, SKIN);                         // legs
  s += part(ID, 'armour', sh('path', { d: 'M-32 -80 L-30 -24 L-8 -24 L-8 -80 Z' }, C.armour) +
    sh('path', { d: 'M32 -80 L30 -24 L8 -24 L8 -80 Z' }, C.armour), C.armour);                               // bronze greaves
  s += sh('ellipse', { cx: -24, cy: -9, rx: 20, ry: 10 }, '#6a4a30') + sh('ellipse', { cx: 24, cy: -9, rx: 20, ry: 10 }, '#6a4a30'); // sandals
  const skirt = 'M-50 -130 L-58 -76 L58 -76 L50 -130 Z';                                                       // red chiton hem
  s += part(ID, 'tunic', sh('path', { d: skirt }, C.tunic) +
    ln('M-30 -126 L-34 -80 M0 -128 L0 -78 M30 -126 L34 -80', 3, 'rgba(42,28,19,.35)'), C.tunic);
  const cuirass = 'M-48 -240 Q0 -252 48 -240 L52 -126 Q0 -114 -52 -126 Z';                                    // bronze muscle cuirass
  s += part(ID, 'armour', sh('path', { d: cuirass }, C.armour) + shade(`<path d="${cuirass}"/>`, 56, -180, 34, 80, 'rgba(90,50,10,.22)') +
    ln('M-30 -212 Q-16 -200 -4 -210 M4 -210 Q16 -200 30 -212', 3.5, 'rgba(90,50,10,.55)') +                    // chest
    ln('M-14 -186 L-14 -140 M14 -186 L14 -140 M-24 -166 L24 -166', 3, 'rgba(90,50,10,.4)'), C.armour);          // abs
  return s;
}

function headPart(pose: Pose): string {
  // long combed hair falls behind the shoulders (drawn first), then the head, beard, helmet pushed up
  let s = part(ID, 'hair', sh('path', { d: 'M-62 -306 Q-78 -246 -60 -206 L-36 -214 Q-50 -258 -44 -300 Z' }, HAIR) +
    sh('path', { d: 'M62 -306 Q78 -246 60 -206 L36 -214 Q50 -258 44 -300 Z' }, HAIR), HAIR);
  s += head(SKIN, pose.expr, { blink: pose.blink, age: true });
  const beard = 'M-54 -286 Q-60 -214 -26 -196 Q0 -186 26 -196 Q60 -214 54 -286 Q40 -256 0 -254 Q-40 -256 -54 -286 Z';
  s += part(ID, 'beard', sh('path', { d: beard }, BEARD) +
    sh('path', { d: 'M-26 -266 Q-12 -278 0 -270 Q12 -278 26 -266 Q12 -260 0 -264 Q-12 -260 -26 -266 Z' }, BEARD) +
    ln('M-30 -236 q4 10 -2 18 M0 -232 l0 18 M30 -236 q-4 10 2 18', 2.5, '#8a8078'), BEARD);                    // grey streaks (age ~60)
  s += ln('M-9 -254 Q0 -250 9 -254', 4);                                                                    // the mouth shows through the beard
  s += part(ID, 'helmet', corinthKingUp(), C.helmet);
  return s;
}

/** Leonidas in any pose. */
export function draw(pose: Pose): string {
  const p: Pose = { armL: 'hold_spear', armR: 'hold_shield', ...pose };
  const holdsSpear = p.armL === 'hold_spear', holdsShield = p.armR === 'hold_shield';
  let front = '';
  if (holdsSpear) front += pole(-82, -480, -82, -6, '#8b5a2b', 'spear') + sh('path', { d: 'M-82 -530 L-92 -480 L-72 -480 Z' }, '#bdbdbd');
  if (holdsShield) front += part(ID, 'shield', aspis(64, -160, 84, 'shield'), C.shield);
  return figure(ID, LOOK, { ...p, holds: holdsSpear ? 'spear' : p.holds }, {
    back: part(ID, 'cloak', sh('path', { d: 'M-48 -236 Q-92 -120 -82 -30 L82 -30 Q92 -120 48 -236 Z' }, C.cloak), C.cloak) +
          '<ellipse cx="0" cy="-4" rx="80" ry="12" fill="rgba(0,0,0,.14)"/>',
    body: body(), head: headPart, front, sleeve: SKIN, mouthBg: BEARD,
  });
}
