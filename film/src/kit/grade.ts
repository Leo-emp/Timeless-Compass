// ============================================================================================================
// COLOUR GRADING + FILM FINISH (rule r34, ART_BIBLE section 3): every shot is graded by time of day and mood,
// then finished like film: soft vignette, light grain, optional 2.39:1 letterbox for big cinematic moments.
// Grades are SVG filters (colour matrix + saturation + contrast). Grain is a cheap seeded dot pattern (a full-frame
// noise filter would slow every cloud render down).
// ============================================================================================================
import { rng } from './core';

export type TimeOfDay = 'dawn' | 'noon' | 'dusk' | 'night' | 'storm' | 'interior';
export type Mood = 'hope' | 'neutral' | 'tension' | 'battle' | 'loss' | 'triumph';

// colour matrix rows: R' = a*R + b*G + c*B + d*A + e (5 values per row, 4 rows)
const m = (r: number, g: number, b: number, lift: [number, number, number] = [0, 0, 0]) =>
  [r, 0, 0, 0, lift[0], 0, g, 0, 0, lift[1], 0, 0, b, 0, lift[2], 0, 0, 0, 1, 0];

export const GRADES: Record<TimeOfDay, { matrix: number[] }> = {
  dawn: { matrix: m(1.08, 1.0, 0.86, [0.03, 0.01, 0]) },          // warm gold
  noon: { matrix: m(1.0, 1.0, 0.98) },                            // neutral, clear
  dusk: { matrix: m(1.06, 0.88, 0.86, [0.03, 0, 0.03]) },         // orange-purple
  night: { matrix: m(0.52, 0.6, 0.82, [0, 0.01, 0.05]) },         // cold blue, dark
  storm: { matrix: m(0.78, 0.8, 0.84) },                          // grey, flat
  interior: { matrix: m(0.92, 0.82, 0.66, [0.02, 0.01, 0]) },     // warm lamp light, dim
};

// mood: saturation multiplier + contrast slope (applied after the time-of-day grade)
export const MOODS: Record<Mood, { saturate: number; contrast: number }> = {
  hope: { saturate: 1.06, contrast: 1.0 }, neutral: { saturate: 1.0, contrast: 1.0 },
  tension: { saturate: 0.82, contrast: 1.08 }, battle: { saturate: 1.12, contrast: 1.15 },
  loss: { saturate: 0.55, contrast: 0.95 }, triumph: { saturate: 1.15, contrast: 1.05 },
};

/** How bright a grade leaves mid-grey (for tests and sanity checks). */
export function luminance(matrix: number[]): number {
  return 0.2126 * (matrix[0] * 0.5 + matrix[4]) + 0.7152 * (matrix[6] * 0.5 + matrix[9]) + 0.0722 * (matrix[12] * 0.5 + matrix[14]);
}

/** The grade filter for one shot (id prefixed per shot so two shots in a dissolve never clash). */
export function gradeDefs(id: string, time: TimeOfDay, mood: Mood): string {
  const g = GRADES[time], md = MOODS[mood];
  const slope = md.contrast, intercept = (1 - slope) / 2;            // contrast around mid-grey
  return `<filter id="${id}grade" color-interpolation-filters="sRGB">` +
    `<feColorMatrix type="matrix" values="${g.matrix.join(' ')}"/>` +
    `<feColorMatrix type="saturate" values="${md.saturate}"/>` +
    `<feComponentTransfer><feFuncR type="linear" slope="${slope}" intercept="${intercept}"/><feFuncG type="linear" slope="${slope}" intercept="${intercept}"/><feFuncB type="linear" slope="${slope}" intercept="${intercept}"/></feComponentTransfer>` +
    `</filter>`;
}

/** Content under the shot's grade. */
export function graded(id: string, time: TimeOfDay, mood: Mood, content: string): string {
  return `<defs>${gradeDefs(id, time, mood)}</defs><g filter="url(#${id}grade)">${content}</g>`;
}

/** Film finish on top of everything: vignette + grain (+ letterbox). t picks the grain pattern for this frame. */
export function finish(t: number, id: string, opts: { vignette?: number; grain?: number; letterbox?: boolean } = {}): string {
  const vig = opts.vignette ?? 0.38, grain = opts.grain ?? 0.05;
  let s = `<defs><radialGradient id="${id}vig" cx="50%" cy="50%" r="75%"><stop offset="0.55" stop-color="#000" stop-opacity="0"/>` +
    `<stop offset="1" stop-color="#000" stop-opacity="${vig}"/></radialGradient>`;
  // grain: 240x240 tile of tiny dots, a new random layout every frame (seeded by the frame number)
  const R = rng(Math.floor(t * 24) * 7919 + 13);
  let dots = '';
  for (let i = 0; i < 260; i++) dots += `<rect x="${(R() * 240).toFixed(1)}" y="${(R() * 240).toFixed(1)}" width="1.6" height="1.6" fill="${R() > 0.5 ? '#fff' : '#000'}"/>`;
  s += `<pattern id="${id}grain" width="240" height="240" patternUnits="userSpaceOnUse">${dots}</pattern></defs>`;
  s += `<rect width="1920" height="1080" fill="url(#${id}vig)"/>`;
  s += `<rect width="1920" height="1080" fill="url(#${id}grain)" opacity="${grain}"/>`;
  if (opts.letterbox) s += '<rect width="1920" height="138" fill="#000"/><rect y="942" width="1920" height="138" fill="#000"/>';
  return s;
}
