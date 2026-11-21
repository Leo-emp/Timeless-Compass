// ============================================================================================================
// CHARACTER DRAWING CONTRACT (rule r19): every named character is ONE function of a Pose, always drawn from
// the colours on its sheet (library/characters/<id>/sheet.json). This file is the shared skeleton:
//   - a Pose says what the character is doing this frame (expression, blink, mouth for lip sync, arm poses,
//     what the hand holds, which way they face)
//   - figure() puts the layers together in the right order and adds arms, hands, mouth and build scaling
//   - part() tags every coloured piece (data-char / data-part / data-fill) so `tc still --chars` can prove the
//     colours match the sheet in every single still
// Coordinates: feet at y = 0, body centred on x = 0, head centre (0, -300), shoulders at (±44, -222).
// ============================================================================================================
import { hand, limb, ln, sh } from '../kit/core';
import type { Expr } from '../kit/cast';
import { OUT } from '../kit/core';

export type ArmPose = 'down' | 'hip' | 'point' | 'raise' | 'hold_spear' | 'hold_shield' | 'fist_up' | 'open';
export type Mouth = 'closed' | 'open' | 'wide' | 'o' | 'smile';

export interface Pose {
  expr: Expr;
  blink?: boolean;
  mouth?: Mouth;          // set only while the character speaks (lip sync), otherwise the expression's mouth
  armL?: ArmPose;         // viewer's left arm
  armR?: ArmPose;         // viewer's right arm
  holds?: string;         // id of the prop the left hand grips (pole/aspis id) — the hand is tagged with it
  facing?: 1 | -1;        // -1 = mirrored (faces the other way)
}

export interface Look {
  skin: string;
  parts: Record<string, string>;                 // part name -> sheet colour
  build: { height: number; width: number };
}

export interface Layers {
  back?: string;                                  // cloak, long hair, things behind the body
  body: string;                                   // legs + torso + costume (already tagged with part())
  head: (pose: Pose) => string;                   // head + hair/headgear for this pose
  front?: string;                                 // props held in front (spear, shield) — drawn before the hands
  sleeve?: string;                                // arm colour (default: skin)
  mouthBg?: string;                               // colour behind a lip-sync mouth (beard colour for bearded faces)
}

/** Tag a coloured piece of a character so the still check can compare it with the sheet. */
export function part(char: string, name: string, svg: string, fill: string): string {
  return `<g data-char="${char}" data-part="${name}" data-fill="${fill}">${svg}</g>`;
}

// arm end points per pose for the LEFT arm (x mirrored for the right arm): [control x, control y, hand x, hand y]
const ARM: Record<ArmPose, [number, number, number, number]> = {
  down: [-62, -182, -54, -138],
  hip: [-104, -176, -60, -140],           // elbow out, fist on the hip
  point: [-92, -232, -136, -238],
  raise: [-76, -282, -62, -336],
  hold_spear: [-80, -210, -82, -188],
  hold_shield: [-70, -196, -58, -166],
  fist_up: [-94, -250, -80, -300],
  open: [-84, -200, -98, -172],
};

function arm(side: -1 | 1, pose: ArmPose, colour: string, skin: string, holds?: string): string {
  const [cx, cy, hx, hy] = ARM[pose];
  const sx = 44 * side, k = -side;   // side -1 = left (x negative), mirror for the right arm
  const d = `M${sx} -222 Q${cx * k} ${cy} ${hx * k} ${hy}`;
  if (pose === 'open') {             // an open hand: palm shape instead of a fist
    return limb(d, 20, colour) + `<g data-role="hand">${sh('ellipse', { cx: hx * k, cy: hy, rx: 13, ry: 17 }, skin)}</g>`;
  }
  return limb(d, 20, colour) + hand(hx * k, hy, skin, holds);
}

const MOUTHS: Record<Mouth, string> = {
  closed: ln('M-10 -263 L10 -263', 4.5),
  open: `<ellipse cx="0" cy="-261" rx="9" ry="6" fill="#7a2b22" stroke="${OUT}" stroke-width="4"/>`,
  wide: `<ellipse cx="0" cy="-260" rx="12" ry="9" fill="#7a2b22" stroke="${OUT}" stroke-width="4"/>`,
  o: `<ellipse cx="0" cy="-260" rx="6" ry="8" fill="#7a2b22" stroke="${OUT}" stroke-width="4"/>`,
  smile: ln('M-12 -265 Q0 -255 12 -265', 4.5),
};

/** A lip-sync mouth drawn over the expression's mouth (skin patch first, then the shape). */
function mouth(m: Mouth, bgColour: string): string {
  return `<ellipse cx="0" cy="-262" rx="16" ry="10" fill="${bgColour}"/>` + MOUTHS[m];
}

/** The whole character for one pose, layers in film order: back, body, far arm, front props, near arm, head. */
export function figure(char: string, look: Look, pose: Pose, layers: Layers): string {
  const sleeve = layers.sleeve ?? look.skin;
  const f = pose.facing ?? 1;
  let s = layers.back ?? '';
  s += layers.body;
  s += arm(1, pose.armR ?? 'down', sleeve, look.skin);                       // far arm behind the props
  s += layers.front ?? '';
  s += arm(-1, pose.armL ?? 'down', sleeve, look.skin, pose.holds);         // near arm: hand over the prop = grip
  s += layers.head(pose);
  if (pose.mouth) s += mouth(pose.mouth, layers.mouthBg ?? look.skin);
  const { height, width } = look.build;
  return `<g data-figure="${char}" transform="scale(${f * width} ${height})">${s}</g>`;   // build + facing
}
