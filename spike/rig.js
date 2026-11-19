// ============================================================================
// GRAPHIC-NOVEL CHARACTER RIG (spike, throwaway)  -- art direction "C"
// Realistic proportions (~7 heads), bold flat shapes, no outlines, rim light.
// A figure is built from JOINT ANGLES, so any pose (walk, row, fight, bow)
// is just numbers. Later this is what animates every voiceover line.
//
// Angle convention: 0 = pointing straight down, +90 = pointing forward (+x), -90 = backward.
// Figures are built facing right; face:-1 mirrors them.
// ============================================================================
const D2R = Math.PI / 180;
const dir = a => [Math.sin(a * D2R), Math.cos(a * D2R)];            // unit vector for an angle
const addv = (p, v, L) => [p[0] + v[0] * L, p[1] + v[1] * L];
// rotate a torso-local point (y up is negative) by lean degrees (+ = top moves forward)
const rot = ([x, y], lean) => { const t = lean * D2R; return [x * Math.cos(t) - y * Math.sin(t), x * Math.sin(t) + y * Math.cos(t)]; };
const poly = pts => 'M ' + pts.map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' L ') + ' Z';

// A tapered limb a->b: width w1 at a, bulge wm a third of the way, w2 at b, rounded joints.
function limbD(a, b, w1, wm, w2) {
  const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
  const at = (t, w, side) => [a[0] + dx * t + nx * w * side, a[1] + dy * t + ny * w * side];
  const pts = [at(0, w1, 1), at(.35, wm, 1), at(1, w2, 1), at(1, w2, -1), at(.35, wm, -1), at(0, w1, -1)];
  const circ = (p, r) => `M ${p[0] - r} ${p[1]} a ${r} ${r} 0 1 0 ${r * 2} 0 a ${r} ${r} 0 1 0 ${-r * 2} 0 Z`;
  return poly(pts) + ' ' + circ(a, w1) + ' ' + circ(b, w2);
}

let _rid = 0;
// o: { x, ground, s, face, lean, headLean, arms:{front:[upper,fore], back:[upper,fore]}, legs:{front:[thigh,shin], back:[thigh,shin]},
//      skin, tunic, cloak, hair, beard, prop, rim, rimLight }
function figure(o) {
  const s = o.s || 1, face = o.face || 1, id = 'r' + (_rid++);
  const L = { thigh: 160, shin: 160, upper: 118, fore: 108, torso: 190 };
  // ---- legs decide the hip height so the feet sit on the ground ----
  const legDrop = ([t, sh]) => L.thigh * Math.cos(t * D2R) + L.shin * Math.cos(sh * D2R);
  const hipY = -Math.max(legDrop(o.legs.front), legDrop(o.legs.back)) - 12;
  const hip = [0, hipY];
  const T = p => { const r = rot(p, o.lean || 0); return [hip[0] + r[0], hip[1] + r[1]]; };   // torso-local -> figure space

  const parts = [];            // {d, fill}: drawn in order; also used as the silhouette for the rim light
  const details = [];          // small marks drawn on top (eyes, brows, folds) - not part of the silhouette
  const add2 = (d, fill) => parts.push({ d, fill });

  const shF = T([22, -184]), shB = T([-18, -180]), neckBase = T([4, -196]);
  const legParts = ([t, sh], hipOff) => {
    const h = T([hipOff, -6]), knee = addv(h, dir(t), L.thigh), ank = addv(knee, dir(sh), L.shin);
    const foot = [[ank[0] - 14, ank[1] - 8], [ank[0] + 8, ank[1] - 14], [ank[0] + 50, ank[1] + 4], [ank[0] + 50, ank[1] + 12], [ank[0] - 16, ank[1] + 12]];
    return { leg: limbD(h, knee, 25, 27, 17) + ' ' + limbD(knee, ank, 17, 19, 10), foot: poly(foot) };
  };
  const armParts = ([u, f], sh) => {
    const el = addv(sh, dir(u), L.upper), wr = addv(el, dir(f), L.fore), hand = addv(wr, dir(f), 22);
    return { arm: limbD(sh, el, 20, 22, 15) + ' ' + limbD(el, wr, 15, 17, 11), hand: limbD(wr, hand, 13, 16, 12), wr, hand };
  };

  // ---- back of the body first ----
  if (o.cloak) add2(poly([T([-20, -192]), T([-62, -120]), T([-100, 40]), T([-84, 120]), T([-40, 150]), T([-30, 40]), T([-26, -150])]), o.cloak);
  const backArm = armParts(o.arms.back, shB);
  add2(backArm.arm, o.skinSh || o.skin); add2(backArm.hand, o.skinSh || o.skin);
  const backLeg = legParts(o.legs.back, -10);
  add2(backLeg.leg, o.skinSh || o.skin); add2(backLeg.foot, '#2a1a12');
  const frontLeg = legParts(o.legs.front, 10);
  add2(frontLeg.leg, o.skin); add2(frontLeg.foot, '#2a1a12');
  // ---- tunic (chiton) over the torso and both thighs, hem above the knee ----
  add2(poly([T([-34, -190]), T([30, -194]), T([42, -140]), T([26, -64]), T([32, 0]), T([44, 84]), T([-42, 80]), T([-32, 0]), T([-24, -64]), T([-42, -150])]), o.tunic);
  details.push(`<path d="M ${T([-30, -66]).join(' ')} L ${T([28, -66]).join(' ')}" stroke="${o.belt || '#3a2212'}" stroke-width="10"/>`);
  details.push(`<path d="M ${T([0, -50]).join(' ')} L ${T([4, 78]).join(' ')} M ${T([-18, -40]).join(' ')} L ${T([-24, 74]).join(' ')}" stroke="#000" stroke-opacity=".18" stroke-width="4"/>`);

  // ---- neck + head (profile, angular) ----
  const hl = o.headLean || 0, neckTop = T([8, -214]);
  const Hd = p => { const r = rot(p, hl); return [neckTop[0] + r[0], neckTop[1] + r[1]]; };
  const H = pts => poly(pts.map(Hd));
  add2(limbD(neckBase, neckTop, 15, 15, 14), o.skin);
  add2(H([[-26, 2], [-34, -36], [-36, -62], [-24, -88], [0, -98], [24, -96], [38, -86], [43, -72], [44, -58], [40, -54], [53, -36], [50, -31], [40, -30], [42, -22], [38, -18], [36, -6], [26, 4], [6, 8], [-8, 6]]), o.skin);
  if (o.hair === 'full') add2(H([[-38, -30], [-44, -62], [-34, -90], [-8, -104], [20, -102], [38, -94], [46, -78], [30, -84], [12, -84], [4, -74], [-4, -58], [-12, -44], [-16, -30], [-24, -8]]), o.hairCol);
  if (o.hair === 'short') add2(H([[-34, -36], [-40, -64], [-28, -92], [-2, -102], [22, -100], [38, -92], [43, -80], [26, -86], [10, -86], [2, -78], [-6, -62], [-14, -46], [-20, -34]]), o.hairCol);
  if (o.beard) add2(H([[40, -30], [47, -22], [45, -8], [36, 10], [16, 18], [-6, 10], [-12, -14], [-6, -8], [6, -6], [20, -12], [30, -22]]), o.hairCol);
  details.push(`<path d="${H([[-4, -52], [4, -48], [4, -38], [-4, -34], [-8, -44]])}" fill="#000" fill-opacity=".25"/>`);           // ear
  details.push(`<path d="${H([[18, -67], [45, -63], [43, -58], [20, -61]])}" fill="${o.hairCol}"/>`);                             // heavy brow
  details.push(`<path d="${H([[25, -57], [38, -56], [33, -51]])}" fill="#140a06"/>`);                                            // eye in shadow
  details.push(`<path d="${H([[34, -60], [44, -58], [42, -54]])}" fill="#000" fill-opacity=".18"/>`);                             // eye socket shade
  if (!o.beard) details.push(`<path d="M ${Hd([38, -16]).join(' ')} L ${Hd([30, -15]).join(' ')}" stroke="#3a1a10" stroke-width="3"/>`); // mouth

  // ---- front arm + prop ----
  const frontArm = armParts(o.arms.front, shF);
  add2(frontArm.arm, o.skin); add2(frontArm.hand, o.skin);
  if (o.cloak) add2(poly([T([-24, -196]), T([26, -198]), T([30, -180]), T([-20, -172])]), o.cloak);   // cloak pinned over the shoulders
  if (o.prop === 'scroll') {
    const h = frontArm.hand, v = [frontArm.hand[0] - frontArm.wr[0], frontArm.hand[1] - frontArm.wr[1]];
    const m = [h[0] + v[0] * .2, h[1] + v[1] * .2];
    add2(limbD([m[0], m[1] - 26], [m[0], m[1] + 26], 9, 9, 9), '#e8d6a8');
    details.push(`<circle cx="${m[0]}" cy="${m[1]}" r="7" fill="#9a1a14"/>`);                                                   // wax seal
  }

  // ---- render: rim light = whole silhouette in the light colour, body shifted away from the light ----
  const rim = o.rim || '#ffb070';
  const sil = parts.map(p => `<path d="${p.d}"/>`).join('');
  let svg = `<clipPath id="${id}">${sil}</clipPath><g clip-path="url(#${id})">`;
  svg += `<g fill="${rim}">${sil}</g>`;
  svg += `<g transform="translate(6 3)">${parts.map(p => `<path d="${p.d}" fill="${p.fill}"/>`).join('')}${details.join('')}</g>`;
  if (o.glow) svg += `<circle cx="${o.glow[0]}" cy="${o.glow[1]}" r="${o.glow[2]}" fill="url(#lanternLight)" style="mix-blend-mode:screen"/>`;
  svg += `</g>`;
  // hand positions in world space (so other figures/props can line up with them)
  const W2 = p => [o.x + p[0] * s * face, o.ground + p[1] * s];
  figure.last = { frontHand: W2(frontArm.hand), backHand: W2(backArm.hand) };
  return `<g transform="translate(${o.x} ${o.ground}) scale(${s * face} ${s})">${svg}</g>`;
}
