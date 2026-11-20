// ============================================================================================================
// TAGGED PIECES the still check reads on screen. The kit marks faces (head), hands (hand), props (pole, aspis)
// with data-role attributes; this file adds the one allowed on-screen text: the place/date card (rule r3).
// film/scripts/inspect.mjs renders a scene, reads the screen box of every tagged element and tc still checks them:
// hands touch what they hold, nothing drawn later covers a face, text fits its box, everything in the safe area.
// ============================================================================================================
import { OUT } from './core';

/** The place/date card (parchment, Cinzel bold). x,y = top-left; it is a textbox with the text inside. */
export function card(x: number, y: number, w: number, h: number, text: string, size = 27, opacity = 1): string {
  return `<g transform="translate(${x} ${y})" opacity="${opacity}">` +
    `<rect data-role="textbox" width="${w}" height="${h}" rx="8" fill="#f4e6c6" stroke="${OUT}" stroke-width="4"/>` +
    `<text data-role="text" x="${w / 2}" y="${h / 2 + size * 0.36}" text-anchor="middle" font-family="Cinzel" font-size="${size}" font-weight="700" fill="${OUT}">${text}</text></g>`;
}
