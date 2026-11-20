// Fonts bundled with the film (OFL licence, film/public/fonts/OFL.txt) so laptop, GitHub and Kaggle draw
// identical text. Uses Remotion's official loader (@remotion/fonts): it holds every frame until the font is ready,
// in every browser tab Remotion opens (a hand-made FontFace loader stalled mid-render on GitHub, 2026-11-21).
import { loadFont } from '@remotion/fonts';
import { staticFile } from 'remotion';

let started = false;

/** Load every bundled font (safe to call many times). */
export function loadFonts(): void {
  if (started) return;
  started = true;
  loadFont({ family: 'Cinzel', url: staticFile('fonts/Cinzel.ttf'), weight: '700' });
}
