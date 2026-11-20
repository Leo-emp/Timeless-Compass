// ============================================================================================================
// TEXT AS VECTOR SHAPES: card and map-label text is turned into SVG paths from the bundled font (Cinzel, OFL)
// at draw time, with opentype.js. Nothing is loaded by the browser, so no render tab can ever stall waiting for
// a font (two cloud renders did, 2026-11-21), every machine draws identical letters, and the exact width is
// known for the "text fits its card" check.
// ============================================================================================================
// @ts-expect-error opentype.js ships without type declarations
import opentype from 'opentype.js';
import { CINZEL_TTF_BASE64 } from './fontdata';

type Font = { getPath(t: string, x: number, y: number, size: number): { toPathData(d: number): string }; getAdvanceWidth(t: string, size: number): number };
let font: Font | null = null;

function cinzel(): Font {
  if (font) return font;
  const bin = atob(CINZEL_TTF_BASE64);                       // base64 -> bytes (works in browsers and Node)
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  font = opentype.parse(bytes.buffer) as Font;
  return font;
}

/** Width of a text at a size (font units -> pixels). */
export function textWidth(text: string, size: number): number { return cinzel().getAdvanceWidth(text, size); }

/** The text as one SVG path. (x, y) = baseline start, or baseline centre when anchor = 'middle'. */
export function textPath(text: string, size: number, x: number, y: number, anchor: 'start' | 'middle' = 'start',
                         fill = '#2a1c13', extra = ''): string {
  const x0 = anchor === 'middle' ? x - textWidth(text, size) / 2 : x;
  const d = cinzel().getPath(text, x0, y, size).toPathData(2);
  return `<path${extra} d="${d}" fill="${fill}"/>`;
}
