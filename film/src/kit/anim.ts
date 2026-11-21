// ============================================================================================================
// NATURAL MOTION (rules r28-r30): the animation principles that make movement feel like a film, not a slideshow.
//   - easing: things speed up and slow down, never move at robot speed
//   - anticipation: a small move back before the action (the wind-up before a throw)
//   - overshoot + settle: the action goes a touch past its end and settles (follow-through)
//   - beats: an action starts a little BEFORE its word so the key pose lands ON the word
//   - nobody freezes: breathing and blinking on every living character, each with its own rhythm (seed)
// All pure functions of time, so every machine draws the same frame.
// ============================================================================================================

/** Smooth start and stop. */
export function easeInOut(x: number): number {
  const c = Math.min(1, Math.max(0, x));
  return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2;
}

/** Overshoot a little past 1, then settle exactly on 1 (follow-through). s = how far it overshoots. */
export function easeOutBack(x: number, s = 1.4): number {
  const c = Math.min(1, Math.max(0, x)) - 1;
  return 1 + (s + 1) * c * c * c + s * c * c;
}

/** Wind-up: dips below 0 first (by about a), then moves forward smoothly to 1. */
export function anticipate(x: number, a = 0.15): number {
  const c = Math.min(1, Math.max(0, x));
  const back = Math.sin(Math.min(1, c / 0.3) * Math.PI) * a;     // the small backward move in the first 30 %
  return easeInOut(c) - (c < 0.3 ? back : 0);
}

/** Value between a and b over [t0, t1] with an easing; exactly a before t0 and exactly b after t1. */
export function tween(t: number, t0: number, t1: number, a: number, b: number, ease: (x: number) => number = easeInOut): number {
  if (t <= t0) return a;
  if (t >= t1) return b;
  return a + (b - a) * ease((t - t0) / (t1 - t0));
}

/** 0 -> 1 progress of an action that LANDS on its word at time `at`: it starts `lead` s early and takes `dur` s. */
export function beat(t: number, at: number, lead = 0.25, dur = 0.5): number {
  const start = at - lead;
  if (t <= start) return 0;
  if (t >= start + dur) return 1;
  return (t - start) / dur;
}

// small deterministic hash -> 0..1 (so each character has its own rhythm)
function hash(n: number): number {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

/** Breathing: -1..1, about one breath every 4 s, phase per character (seed). */
export function breathe(t: number, seed: number): number {
  return Math.sin((t / (3.6 + hash(seed) * 0.8)) * Math.PI * 2 + hash(seed + 1) * 6.28);
}

/** Blink: true for 4 frames (at 24 fps) every 3-5 s, timing per character (seed). */
export function blinkAt(t: number, seed: number): boolean {
  const period = 3 + hash(seed) * 2;                              // 3-5 s between blinks
  const phase = (t + hash(seed + 7) * period) % period;
  return phase < 4 / 24;
}

/** Gentle idle sway (weight shift), amplitude amp, per character. */
export function sway(t: number, seed: number, amp = 2): number {
  return amp * Math.sin((t / (5 + hash(seed + 3) * 2)) * Math.PI * 2 + hash(seed + 5) * 6.28);
}
