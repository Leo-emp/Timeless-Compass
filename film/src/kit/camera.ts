// ============================================================================================================
// CAMERA (rule r34): every move eases in and out (r29) and is felt through DEPTH — each layer of a set has a
// depth (0 = sky / far mountains, 1 = the hero layer, > 1 = foreground in front) and moves by that much, so near
// things slide past faster than far ones (parallax). Moves:
//   push_in / pull_out  zoom toward / away from a focus point (tension, a reveal / scale, loneliness)
//   pan_left/right, tilt_up/down   follow action or reveal a place
//   track     move sideways with marching troops, ships, a running messenger
//   crane_up/down   rise or sink with a slight zoom (openings, endings)
//   handheld  small seeded shake (battle, chaos)
//   rack_focus   blur shifts from the near layer to the far one (move attention between characters)
// ============================================================================================================
import { easeInOut } from './anim';

export interface Cam { move: string; amount: number; t0: number; t1: number; focus?: [number, number] }
export interface CamT { scale: number; dx: number; dy: number }

const W = 1920, H = 1080;

/** Scale + offset for one layer at time t. */
export function camTransform(t: number, depth: number, cam: Cam): CamT {
  const k = easeInOut(cam.t1 > cam.t0 ? (t - cam.t0) / (cam.t1 - cam.t0) : 1) * cam.amount * depth;
  switch (cam.move) {
    case 'push_in': return { scale: 1 + k, dx: 0, dy: 0 };
    case 'pull_out': return { scale: 1 + cam.amount * depth - k, dx: 0, dy: 0 };   // starts zoomed in, pulls back to 1
    case 'pan_left': return { scale: 1 + 0.06 * depth, dx: k * W, dy: 0 };
    case 'pan_right': return { scale: 1 + 0.06 * depth, dx: -k * W, dy: 0 };
    case 'tilt_up': return { scale: 1 + 0.06 * depth, dx: 0, dy: k * H };
    case 'tilt_down': return { scale: 1 + 0.06 * depth, dx: 0, dy: -k * H };
    case 'track': return { scale: 1 + 0.04 * depth, dx: -k * W, dy: 0 };
    case 'crane_up': return { scale: 1 + k * 0.3, dx: 0, dy: k * H * 0.6 };
    case 'crane_down': return { scale: 1 + k * 0.3, dx: 0, dy: -k * H * 0.6 };
    case 'handheld': {                                     // two slow sines + a faster one, seeded by time only
      const a = cam.amount * depth;
      return { scale: 1 + 0.02 * depth, dx: a * (5 * Math.sin(t * 1.7) + 2 * Math.sin(t * 5.3)), dy: a * (4 * Math.sin(t * 1.3 + 1) + 1.5 * Math.sin(t * 6.1)) };
    }
    default: return { scale: 1, dx: 0, dy: 0 };            // static, rack_focus (focus is handled by rackFocus)
  }
}

/** One layer's content under the camera at time t (zoom about the focus point, then offset). */
export function camLayer(t: number, depth: number, cam: Cam, content: string): string {
  const { scale, dx, dy } = camTransform(t, depth, cam);
  if (scale === 1 && dx === 0 && dy === 0) return `<g>${content}</g>`;
  const [fx, fy] = cam.focus ?? [W / 2, H / 2];
  return `<g transform="translate(${(fx + dx).toFixed(2)} ${(fy + dy).toFixed(2)}) scale(${scale.toFixed(5)}) translate(${-fx} ${-fy})">${content}</g>`;
}

/** Blur (px) for a layer during a rack focus: starts sharp on the NEAR layer (depth >= 0.8), ends sharp on the FAR one. */
export function rackFocus(t: number, depth: number, cam: Cam): number {
  if (cam.move !== 'rack_focus') return 0;
  const k = easeInOut(cam.t1 > cam.t0 ? (t - cam.t0) / (cam.t1 - cam.t0) : 1);
  const near = depth >= 0.8;
  return +(cam.amount * (near ? k : 1 - k)).toFixed(2);
}

/** A blur filter for one layer (id must be unique inside the frame: prefix it with the shot id). */
export function blurFilter(id: string, px: number): string {
  return `<filter id="${id}" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="${px}"/></filter>`;
}
