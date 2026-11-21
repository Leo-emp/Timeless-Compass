// ============================================================================================================
// THUMBNAILS — "300 Spartans Got One Last Chance" (Short, 1080x1920). Drawn fresh for this video (r17, r21).
//   a: Leonidas huge and defiant, the endless Persian host behind him at dusk        words: TAKE THEM
//   b: Xerxes looming over the sky, the tiny red Spartan line holding the pass below    words: ONE LAST CHANCE
// Rules: <= 3 big words, strong emotion, one striking object, rich background, readable at 160 px (tc thumb).
// ============================================================================================================
import type { ShotCtx } from '../../film/sequence';
import { textPath, textWidth } from '../../kit/text';
import * as leonidas from '../../characters/leonidas';
import * as xerxes from '../../characters/xerxes';
import { at, columns, passSet, sky, spartan } from './scenes';

export const THUMB_SIZE = { w: 1080, h: 1920 };
export const WORDS: Record<'a' | 'b', string[]> = { a: ['TAKE', 'THEM'], b: ['ONE', 'LAST', 'CHANCE'] };

const W = 1080, H = 1920;
/** A still "moment" for the scene helpers (they read time + make unique ids). */
const ctx = (name: string): ShotCtx => ({ t: 3.2, local: 3.2, dur: 5, w: W, h: H, pid: (s: string) => `th${name}_${s}`, beatT: () => 99 } as unknown as ShotCtx);

/** Big poster words: cream fill, thick dark outline drawn first, fitted to the width. */
function bigWords(line: string, y: number, maxSize: number, fill = '#fff1d0'): string {
  let size = maxSize;
  while (textWidth(line, size) > W - 120) size -= 6;
  const stroke = (w: number) => ` stroke="#140a06" stroke-width="${Math.round(size * w)}" stroke-linejoin="round"`;
  return `<g transform="translate(8 12)">${textPath(line, size, W / 2, y, 'middle', '#140a06', stroke(0.16))}</g>` +   // shadow
    textPath(line, size, W / 2, y, 'middle', '#140a06', stroke(0.16)) + textPath(line, size, W / 2, y, 'middle', fill);
}
/** A dark band at the top so the words pop at phone size. */
function topBand(id: string, to = 620): string {
  return `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#140a10" stop-opacity=".85"/>` +
    `<stop offset="1" stop-color="#140a10" stop-opacity="0"/></linearGradient></defs><rect width="${W}" height="${to}" fill="url(#${id})"/>`;
}
function vignette(id: string, strength = 0.75): string {
  return `<defs><radialGradient id="${id}" cx=".5" cy=".45" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/>` +
    `<stop offset="1" stop-color="#000" stop-opacity="${strength}"/></radialGradient></defs><rect width="${W}" height="${H}" fill="url(#${id})"/>`;
}

function thumbA(): string {
  const c = ctx('a');
  // dusk sky, the plain filled to the horizon with the Persian host (no end in sight)
  let s = sky(c, 'dusk', 560, 1060);     // the sun sets right behind his helmet: a halo that separates him
  s += `<rect x="0" y="980" width="${W}" height="${H}" fill="#7a5a44"/>`;
  s += `<g opacity=".92">${columns(3.2, 0, 11, 1000, 1560)}</g>`;
  s += `<rect x="0" y="900" width="${W}" height="700" fill="#4a2030" opacity=".25"/>`;
  // Leonidas: huge, chest-up, stern, spear upright — the defiant answer
  s += `<circle cx="560" cy="1120" r="430" fill="#ffd9a0" opacity=".35"/><circle cx="560" cy="1120" r="300" fill="#ffe9c4" opacity=".35"/>`;
  s += at(560, 2560, 3.4, leonidas.draw({ expr: 'stern', breath: 0, blink: false }));
  s += `<circle cx="262" cy="790" r="30" fill="#fff3c4" opacity=".35"/><path d="M262 730 Q267 785 322 790 Q267 795 262 850 Q257 795 202 790 Q257 785 262 730 Z" fill="#fffbe8"/>`;   // the spear tip glints
  s += `<rect width="${W}" height="${H}" fill="#ff6a2a" opacity=".08"/>` + vignette('thA_v', 0.8);
  s += topBand('thA_b') + bigWords('TAKE THEM', 330, 250);
  return s;
}

function thumbB(): string {
  const c = ctx('b');
  const p = passSet(c, 'dusk');
  // the pass, low in frame: cliff, gulf, the wall, the tiny red line
  let world = p.far + p.mid + p.ground;
  for (let i = 0; i < 9; i++) world += at(400 + i * 80, 1440, 0.3, spartan(3.2, i, { helmet: 'closed' }));
  let s = p.sky;
  // Xerxes looms over the sky (huge, a little ghostly), reaching out with the offer
  s += `<g opacity=".82">${at(560, 2260, 4.0, xerxes.draw({ expr: 'stern', breath: 0, blink: false, armL: 'hold_spear', armR: 'open' }))}</g>`;
  s += `<defs><linearGradient id="thB_fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".45" stop-color="#2a1830" stop-opacity="0"/>` +
       `<stop offset=".62" stop-color="#2a1830" stop-opacity=".85"/></linearGradient></defs><rect width="${W}" height="${H}" fill="url(#thB_fade)"/>`;
  s += `<g transform="translate(0 320)">${world}</g>`;
  s += `<defs><radialGradient id="thB_hope"><stop offset="0" stop-color="#ffc070" stop-opacity=".6"/><stop offset="1" stop-color="#ffc070" stop-opacity="0"/></radialGradient></defs>` +
       `<ellipse cx="720" cy="1780" rx="520" ry="240" fill="url(#thB_hope)"/>`;   // warm light on the 300: the one hope in frame
  s += vignette('thB_v', 0.7);
  s += topBand('thB_b', 700) + bigWords('ONE LAST', 250, 210) + bigWords('CHANCE', 480, 250, '#ffcf5a');
  return s;
}

export const THUMBS: Record<'a' | 'b', () => string> = { a: thumbA, b: thumbB };
