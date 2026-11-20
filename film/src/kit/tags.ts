// ============================================================================================================
// TAGGED PIECES the still check reads on screen. The kit marks faces (head), hands (hand), props (pole, aspis)
// with data-role attributes; this file adds the one allowed on-screen text: the place/date card (rule r3).
// film/scripts/inspect.mjs renders a scene, reads the screen box of every tagged element and tc still checks them:
// hands touch what they hold, nothing drawn later covers a face, text fits its box, everything in the safe area.
// ============================================================================================================
import { OUT } from './core';
import { textPath } from './text';

/** The place/date card (parchment, Cinzel bold). x,y = top-left; it is a textbox with the text inside. */
export function card(x: number, y: number, w: number, h: number, text: string, size = 27, opacity = 1): string {
  return `<g transform="translate(${x} ${y})" opacity="${opacity}">` +
    `<rect data-role="textbox" width="${w}" height="${h}" rx="8" fill="#f4e6c6" stroke="${OUT}" stroke-width="4"/>` +
    // letters are vector shapes (no font loading); a thin same-colour stroke gives Cinzel its bold card weight
    textPath(text, size, w / 2, h / 2 + size * 0.36, 'middle', OUT, ` data-role="text" stroke="${OUT}" stroke-width="${(size * 0.055).toFixed(2)}" stroke-linejoin="round"`) + '</g>';
}
