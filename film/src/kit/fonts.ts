// Fonts bundled with the film (OFL licence, film/public/fonts/OFL.txt) so laptop, GitHub and Kaggle draw
// identical text. Remotion waits (delayRender) until they are loaded before taking any frame.
import { continueRender, delayRender, staticFile } from 'remotion';

let loaded: Promise<void> | null = null;

/** Load every bundled font once per render process. */
export function loadFonts(): Promise<void> {
  if (loaded) return loaded;
  const handle = delayRender('loading fonts');
  const cinzel = new FontFace('Cinzel', `url(${staticFile('fonts/Cinzel.ttf')})`, { weight: '400 900' });
  loaded = cinzel.load().then((f) => { document.fonts.add(f); continueRender(handle); });
  return loaded;
}
