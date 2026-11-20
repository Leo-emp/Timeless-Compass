// Fonts embedded in the bundle (OFL licence, public/fonts/OFL.txt) so laptop, GitHub and Kaggle draw identical
// text. The font is a data: URL — nothing is fetched from the render server, so no tab can stall waiting for it
// (two cloud renders stalled on font fetches on 2026-11-21). Remotion's loader still holds frames until it is ready.
import { loadFont } from '@remotion/fonts';
import { CINZEL_TTF_BASE64 } from './fontdata';

let started = false;

/** Load every font (safe to call many times). */
export function loadFonts(): void {
  if (started) return;
  started = true;
  loadFont({ family: 'Cinzel', url: `data:font/ttf;base64,${CINZEL_TTF_BASE64}`, weight: '700', format: 'truetype' });
}
