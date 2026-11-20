// ============================================================================================================
// STYLE KIT — CORE (the only drawing code shared between videos; rule r17: scenes themselves are never shared)
// ------------------------------------------------------------------------------------------------------------
// Every Timeless Compass frame is an SVG picture built from plain text strings. These helpers produce the
// pieces every drawing needs, in the approved house style (rule r16):
//   - one thick warm-brown outline on every shape (never pure black)
//   - flat colour + ONE soft shade on the side away from the light
//   - "rubber" limbs: a dark wide stroke with a thinner coloured stroke on top = a tube with an outline
// Ported from the approved spike (spike/art_dir/cast_lib.js) on 2026-11-21.
//
// DETERMINISM: a video is rendered in parts on many machines at once (GitHub + Kaggle). Every frame must come
// out pixel-identical no matter which machine draws it or in which order. So:
//   - random numbers come from a seeded generator (rng), never Math.random()
//   - clipPath ids restart from zero at the start of every frame (resetIds), never a global running counter
// ============================================================================================================

export const OUT = '#2a1c13'; // the one outline colour: dark warm brown
export const SW = 7;          // character outline thickness in figure units

// ---------- unique ids (restarted every frame) ----------
let counter = 0;
/** Call at the top of every frame's draw function so ids are the same on every machine. */
export function resetIds(): void { counter = 0; }
/** Next unique id inside this frame, e.g. nextId('c') -> 'c0', 'c1', ... */
export function nextId(prefix: string): string { return `${prefix}${counter++}`; }

// ---------- numbers ----------
/** Seeded random generator (mulberry32): same seed -> same sequence on every machine. Returns [0, 1). */
export function rng(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
/** Smooth start + smooth stop (in-out quad) for camera moves and actions: 0 -> 0, 0.5 -> 0.5, 1 -> 1. */
export function ease(x: number): number { return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2; }
/** Wrap v into [0, w) — used for things that scroll forever (waves, clouds). Works for negative v too. */
export function wrap(v: number, w: number): number { return ((v % w) + w) % w; }

// ---------- shapes ----------
type Attrs = Record<string, string | number>;
const attrs = (a: Attrs) => Object.entries(a).map(([k, v]) => `${k}="${v}"`).join(' ');

/** Any SVG shape, filled, with the house outline. sh('circle', {cx, cy, r}, '#fff') */
export function sh(tag: string, a: Attrs, fill: string): string {
  return `<${tag} ${attrs(a)} fill="${fill}" stroke="${OUT}" stroke-width="${SW}" stroke-linejoin="round" stroke-linecap="round"/>`;
}
/** A plain line in the outline colour (folds, lacing, brows). */
export function ln(d: string, w = 5, col = OUT): string {
  return `<path d="${d}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
}
/** Background shape: thinner outline than characters (default 4) so heroes stay the focus. */
export function bg(d: string, fill: string, w = 4): string {
  return `<path d="${d}" fill="${fill}" stroke="${OUT}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round"/>`;
}
/** A "rubber" limb: outline-coloured wide stroke, then the limb colour on top. */
export function limb(d: string, w: number, col: string): string {
  return `<path d="${d}" fill="none" stroke="${OUT}" stroke-width="${w + SW * 2}" stroke-linecap="round" stroke-linejoin="round"/>` +
         `<path d="${d}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
}
/** A fist. Draw it AFTER the prop it holds so the hand really wraps the spear/scroll (grip rule). */
export function hand(x: number, y: number, skin: string, holds?: string): string {
  // data-role / data-holds let the still check see the hand on screen and test that it touches what it holds
  const tag = `<g data-role="hand"${holds ? ` data-holds="${holds}"` : ''}>`;
  return tag + sh('circle', { cx: x, cy: y, r: 15 }, skin) + ln(`M${x - 8} ${y - 3} Q${x} ${y + 4} ${x + 8} ${y - 3}`, 3.5) + '</g>';
}
/** Soft shade: a darker ellipse clipped to a shape (light comes from the upper left). */
export function shade(clipInner: string, cx: number, cy: number, rx: number, ry: number, col = 'rgba(80,35,15,.16)'): string {
  const id = nextId('c');
  return `<clipPath id="${id}">${clipInner}</clipPath>` +
         `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${col}" clip-path="url(#${id})"/>`;
}
