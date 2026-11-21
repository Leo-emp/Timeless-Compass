// ============================================================================================================
// THE FILM SEQUENCE: which shot(s) are on screen at a frame, drawn with their camera, grade and transitions.
// A timed plan (film/src/jobs/<id>/plan.json, from `tc shotplan`) lists shots with start/end frames that tile the
// voice exactly. A transition of n frames is CENTRED on the cut (n/2 before, n/2 after), so it never adds or
// removes frames — the picture can never drift away from the voice (r28).
//   cut / match   hard switch on the cut frame (a match cut = two shots composed to rhyme)
//   dissolve      the next shot fades in over the last
//   fade_black    down to black, up from black (between acts)
//   flash_white   a white flash (lightning, a divine moment)
//   whip          fast slide with motion blur (simultaneous places)
// Each shot is drawn inside its own id prefix (withIdPrefix) so two shots in a dissolve never share an id.
// ============================================================================================================
import { pid, resetIds, withIdPrefix } from '../kit/core';
import type { Cam } from '../kit/camera';
import { finish, graded, type Mood, type TimeOfDay } from '../kit/grade';

export interface TimedShot {
  id: string; start_f: number; end_f: number; scene: string; place: string;
  camera: { move: string; amount: number; focus?: [number, number] };
  grade: { time: TimeOfDay; mood: Mood };
  transition_in: { kind: string; frames: number };
  beats: { frame: number; word_frame?: number; do: string; kind: string; word?: string }[];
  sfx: unknown[]; letterbox?: boolean;
}
export interface TimedPlan { fps: number; frames: number; width?: number; height?: number; shots: TimedShot[] }

/** What a scene function receives for one frame. */
export interface ShotCtx {
  shot: TimedShot; fps: number;
  frame: number;          // global frame
  w: number; h: number;   // frame size (1920x1080 long, 1080x1920 Shorts)
  t: number;              // global seconds (for lip sync, which uses absolute times)
  local: number;          // seconds since this shot started (may be < 0 or > duration during a transition)
  dur: number;            // shot length in seconds
  cam: Cam;               // the shot's camera move over its own length
  beatT: (i: number) => number;   // local time (s) when beat i should LAND (its frame + lead)
  pid: (name: string) => string;  // shot-unique id for gradients/filters
}
export type SceneFn = (ctx: ShotCtx) => string;

function drawShot(shot: TimedShot, frame: number, fps: number, scenes: Record<string, SceneFn>, w = 1920, h = 1080): string {
  const fn = scenes[shot.scene];
  if (!fn) throw new Error(`scene ${shot.scene} not found for shot ${shot.id}`);
  const dur = (shot.end_f - shot.start_f) / fps;
  const ctx: ShotCtx = {
    shot, fps, frame, w, h, t: frame / fps, local: (frame - shot.start_f) / fps, dur,
    cam: { move: shot.camera.move, amount: shot.camera.amount, t0: 0, t1: dur, focus: shot.camera.focus },
    beatT: (i) => ((shot.beats[i].word_frame ?? shot.beats[i].frame + 6) - shot.start_f) / fps,   // when the action LANDS
    pid,
  };
  return withIdPrefix(shot.id, () => graded(shot.id, shot.grade.time, shot.grade.mood, fn({ ...ctx, pid })));
}

/** The whole picture at a frame. */
export function frameAt(frame: number, plan: TimedPlan, scenes: Record<string, SceneFn>): string {
  resetIds();
  const W = plan.width ?? 1920, H = plan.height ?? 1080;
  const draw = (s: TimedShot) => drawShot(s, frame, plan.fps, scenes, W, H);
  const shots = plan.shots;
  const i = Math.max(0, shots.findIndex((s) => frame >= s.start_f && frame < s.end_f));
  const cur = shots[i], prev = shots[i - 1], next = shots[i + 1];
  let body = '';
  // transition with the previous shot (we are in its second half) or the next shot (its first half)
  let pair: [TimedShot, TimedShot, string, number] | null = null;
  const half = (s: TimedShot) => Math.floor((s.transition_in.frames || 0) / 2);
  if (prev && half(cur) > 0 && frame < cur.start_f + half(cur)) pair = [prev, cur, cur.transition_in.kind, (frame - (cur.start_f - half(cur))) / (2 * half(cur))];
  else if (next && half(next) > 0 && frame >= next.start_f - half(next)) pair = [cur, next, next.transition_in.kind, (frame - (next.start_f - half(next))) / (2 * half(next))];
  if (!pair || ['cut', 'match'].includes(pair[2])) {
    body = draw(cur);
  } else {
    const [a, b, kind, p] = pair;
    if (kind === 'dissolve') {
      body = draw(a) + `<g opacity="${p.toFixed(3)}">${draw(b)}</g>`;
    } else if (kind === 'fade_black' || kind === 'flash_white') {
      const colour = kind === 'fade_black' ? '#000' : '#fff';
      const op = p < 0.5 ? p * 2 : (1 - p) * 2;                       // 0 -> 1 at the cut -> 0
      body = (p < 0.5 ? draw(a) : draw(b)) +
        `<rect width="${W}" height="${H}" fill="${colour}" opacity="${+op.toFixed(3)}"/>`;
    } else if (kind === 'whip') {
      const x = p * W;                                                  // A slides out left, B slides in from the right
      body = `<defs><filter id="whip${frame}"><feGaussianBlur stdDeviation="${(40 * Math.sin(p * Math.PI)).toFixed(1)} 0"/></filter></defs>` +
        `<g filter="url(#whip${frame})"><g transform="translate(${-x} 0)">${draw(a)}</g>` +
        `<g transform="translate(${W - x} 0)">${draw(b)}</g></g>`;
    } else {
      body = draw(cur);
    }
  }
  return body + finish(frame / plan.fps, 'fin', { letterbox: !!cur.letterbox }, W, H);
}
