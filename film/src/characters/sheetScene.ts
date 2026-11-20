// ============================================================================================================
// CHARACTER SHEET (turnaround) — the locked reference image of one character (rule r19):
// full body front, full body facing the other way with a gesture, six expressions, colour swatches, name + who.
// Rendered by film/scripts/sheet.mjs into library/characters/<id>/sheet.png.
// ============================================================================================================
import { EXPRESSIONS } from '../kit/cast';
import { OUT, resetIds, sh } from '../kit/core';
import { textPath } from '../kit/text';
import type { Pose } from './figure';

export interface SheetData { id: string; name: string; who: string; look: { skin: string; hair: { colour: string }; beard?: { colour: string } | null; parts: Record<string, string> } }

/** draw = the character's draw(pose) function; sheet = its sheet.json. */
export function drawSheet(draw: (p: Pose) => string, sheet: SheetData): string {
  resetIds();
  let s = '<rect width="1920" height="1080" fill="#efe4cf"/>';
  s += textPath(sheet.name.toUpperCase(), 46, 70, 92, 'start', OUT, ' stroke="#2a1c13" stroke-width="1.6"');
  s += textPath(sheet.who, 22, 72, 130, 'start', '#6b5442');
  s += '<rect x="0" y="770" width="1920" height="8" fill="#d9c9a8"/>';
  s += `<g transform="translate(330 770) scale(1.25)">${draw({ expr: 'neutral' })}</g>`;
  s += `<g transform="translate(760 770) scale(1.25)">${draw({ expr: 'stern', facing: -1, armL: 'point' })}</g>`;
  EXPRESSIONS.forEach((expr, i) => {                       // six expression heads in a 3 x 2 grid
    const x = 1180 + (i % 3) * 240, y = 560 + Math.floor(i / 3) * 300;
    s += `<g transform="translate(${x} ${y}) scale(.9)"><clipPath id="hc${i}"><rect x="-140" y="-470" width="280" height="300"/></clipPath><g clip-path="url(#hc${i})">${draw({ expr })}</g></g>`;
    s += textPath(expr, 22, x, y - 130, 'middle', '#6b5442');
  });
  const sw = { skin: sheet.look.skin, hair: sheet.look.hair.colour, ...(sheet.look.beard ? { beard: sheet.look.beard.colour } : {}), ...sheet.look.parts };
  Object.entries(sw).forEach(([k, c], i) => {             // colour swatches = the sheet's locked palette
    s += sh('rect', { x: 70 + i * 150, y: 960, width: 60, height: 60, rx: 8 }, c);
    s += textPath(`${k} ${c}`, 18, 140 + i * 150, 996, 'start', '#6b5442');
  });
  return s;
}
