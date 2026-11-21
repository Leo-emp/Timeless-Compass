// ============================================================================================================
// LIP SYNC: a character's mouth follows THEIR OWN dialogue line (Rhubarb mouth cues from tc dialogue), and only
// while they speak; the rest of the time the expression's mouth shows. (r28: mouths follow their own dialogue.)
// Cue times are absolute seconds in the video (film/src/jobs/<id>/lipsync.json, written by `tc lipsync <job>`).
// ============================================================================================================
import type { Mouth } from '../characters/figure';

/** Rhubarb's 9 shapes -> our 5 cartoon mouths (A/G = lips closed, D = wide open, F = rounded oo, B = teeth/ee). */
export const RHUBARB_TO_MOUTH: Record<string, Mouth> = {
  A: 'closed', B: 'smile', C: 'open', D: 'wide', E: 'open', F: 'o', G: 'closed', H: 'open', X: 'closed',
};

export interface LipLine { speaker: string; at: number | null; cues: { start: number; end: number; shape: string }[] }

/** The mouth `speaker` makes at time t, or undefined when they are not speaking. */
export function mouthAt(t: number, lines: LipLine[], speaker: string): Mouth | undefined {
  const who = speaker.toUpperCase();
  for (const l of lines) {
    if (l.speaker.toUpperCase() !== who || !l.cues.length) continue;
    if (t < l.cues[0].start || t >= l.cues[l.cues.length - 1].end) continue;
    const c = l.cues.find((q) => t >= q.start && t < q.end);
    if (c) return RHUBARB_TO_MOUTH[c.shape] ?? 'open';
  }
  return undefined;
}
