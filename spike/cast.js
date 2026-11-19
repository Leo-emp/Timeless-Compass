// ============================================================================
// TIMELESS COMPASS CAST KIT (spike, throwaway)
// Our own funny-but-smart cartoon people: ~2.7 heads tall, warm skin tones,
// thick warm-brown outlines, one cel-shadow tone, big expressive eyes + brows.
// Faces are 3/4 view looking toward "front" (+x before flipping).
//
// chibi({...}) returns an SVG string. Feet sit at (x, y). face: 1 = looks right, -1 = looks left.
// ============================================================================
const OL = '#2a1610';          // outline colour (warm, never pure black)
const OW = 6;                  // outline width in character units

// a filled path with an outline drawn OUTSIDE it (paint-order=stroke)
const P = (d, fill, extra = '') => `<path d="${d}" fill="${fill}" stroke="${OL}" stroke-width="${OW * 2}" stroke-linejoin="round" paint-order="stroke" ${extra}/>`;
const E = (cx, cy, rx, ry, fill, extra = '') => `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}" stroke="${OL}" stroke-width="${OW * 2}" paint-order="stroke" ${extra}/>`;
const C = (cx, cy, r, fill) => E(cx, cy, r, r, fill);
// an outlined limb: dark capsule underneath, coloured capsule on top
const limb = (a, b, r, fill) => capsule(a, r + OW, b, r + OW, OL) + capsule(a, r, b, r, fill);
let _cid = 0;                  // unique ids for clip paths

function chibi(o) {
  const {
    x, y, s = 1, face = 1, skin = '#e8b48a', skinSh = '#c88a62', tunic = '#efe2c8', tunicSh = '#c4b096',
    cloak = null, cloakSh = '#7a1c18', belt = '#8a5a2a', hair = 'curly', hairCol = '#3a2216',
    beard = null, beardCol = '#3a2216', hat = null, exp = 'normal', look = [1, 0], pose = 'rest', prop = null, sweat = false,
  } = o;
  const id = 'c' + (_cid++);
  const HX = 0, HY = -310, HRX = 86, HRY = 92;      // head centre + radii
  let g = '';

  // ---------------- arms (pose presets: shoulder -> elbow -> hand) ----------------
  const poses = {
    rest:    { back: [[-50, -196], [-64, -150], [-60, -104]], front: [[50, -196], [66, -150], [62, -104]] },
    whisper: { back: [[-50, -196], [-64, -150], [-60, -104]], front: [[50, -196], [104, -206], [104, -262]] },
    point:   { back: [[-50, -196], [-64, -150], [-60, -104]], front: [[50, -196], [110, -214], [168, -232]] },
    cheer:   { back: [[-50, -196], [-90, -262], [-96, -330]], front: [[50, -196], [96, -266], [104, -336]] },
    hold:    { back: [[-50, -196], [-40, -146], [10, -136]], front: [[50, -196], [74, -146], [52, -130]] },
    sit:     { back: [[-50, -196], [-70, -150], [-36, -126]], front: [[50, -196], [86, -156], [70, -122]] },
  };
  const A = poses[pose] || poses.rest;
  const arm = ([sh, el, ha]) => limb(sh, el, 17, tunic) + limb(el, ha, 14, skin) + C(ha[0], ha[1], 18, skin);

  // ---------------- behind the body: cloak + back arm ----------------
  if (cloak) g += P(`M -58 -214 C -100 -150, -112 -60, -104 -20 L 40 -20 C 30 -90, 20 -170, 40 -214 Z`, cloak) +
                 `<path d="M -70 -170 C -90 -110, -96 -60, -92 -26" stroke="${cloakSh}" stroke-width="10" fill="none"/>`;
  g += arm(A.back);

  // ---------------- legs ----------------
  if (pose === 'sit') {
    g += limb([-20, -86], [52, -84], 18, skin) + limb([52, -84], [58, -14], 16, skin);
    g += limb([10, -90], [70, -88], 18, skin) + limb([70, -88], [80, -14], 16, skin);
    g += P(`M 50 -14 L 94 -14 C 100 -6, 96 0, 90 0 L 50 0 Z`, '#6a3e1e') + P(`M 72 -14 L 114 -14 C 120 -6, 116 0, 110 0 L 72 0 Z`, '#6a3e1e');
  } else {
    g += limb([-26, -84], [-30, -14], 17, skin) + limb([24, -84], [28, -14], 17, skin);
    g += P(`M -48 -14 L -6 -14 C 2 -6, -2 0, -10 0 L -48 0 Z`, '#6a3e1e') + P(`M 10 -14 L 56 -14 C 64 -6, 60 0, 52 0 L 10 0 Z`, '#6a3e1e');
  }

  // ---------------- tunic (chiton) with belt + cel shadow ----------------
  const tunicD = pose === 'sit'
    ? `M -56 -214 C -30 -226, 40 -226, 58 -214 C 70 -160, 76 -110, 80 -74 L -64 -74 C -66 -120, -66 -170, -56 -214 Z`
    : `M -56 -214 C -30 -226, 40 -226, 58 -214 C 70 -160, 80 -110, 84 -64 L -78 -64 C -72 -120, -66 -170, -56 -214 Z`;
  g += `<clipPath id="${id}t"><path d="${tunicD}"/></clipPath>` + P(tunicD, tunic);
  g += `<g clip-path="url(#${id}t)"><path d="M -90 -230 C -40 -170, -40 -110, -70 -40 L -120 -40 Z" fill="${tunicSh}"/>
        <path d="M -10 -150 L -20 -66 M 30 -150 L 36 -66" stroke="${tunicSh}" stroke-width="6"/></g>`;
  g += `<rect x="-66" y="-152" width="140" height="16" rx="6" fill="${belt}" stroke="${OL}" stroke-width="5"/>`;
  if (cloak) g += P(`M 40 -214 C 20 -200, -10 -196, -58 -214 L -50 -190 C -10 -180, 20 -184, 46 -196 Z`, cloak);   // cloak over shoulders

  // ---------------- prop held in front (scroll / goblet) ----------------
  if (prop === 'scroll') g += `<g transform="rotate(-12 30 -134)">${P('M -10 -150 L 70 -150 L 70 -118 L -10 -118 Z', '#f2e2b8')}
     ${E(-10, -134, 10, 16, '#d8c090')}${E(70, -134, 10, 16, '#d8c090')}<rect x="26" y="-152" width="10" height="36" fill="#b0302a"/></g>`;

  // ---------------- head ----------------
  g += E(-72, -300, 15, 21, skin);                                             // back ear
  g += `<clipPath id="${id}h"><ellipse cx="${HX}" cy="${HY}" rx="${HRX}" ry="${HRY}"/></clipPath>`;
  g += E(HX, HY, HRX, HRY, skin);
  g += `<g clip-path="url(#${id}h)"><ellipse cx="-118" cy="-300" rx="92" ry="120" fill="${skinSh}"/>
        <ellipse cx="74" cy="-262" rx="16" ry="10" fill="#f08a7a" opacity=".45"/></g>`;    // cel shadow on the back + rosy cheek

  // hair styles
  if (hair === 'curly') {
    let under = '', top = '';
    for (let a = 160; a <= 322; a += 13) { const r = a * Math.PI / 180, cx = HX + Math.cos(r) * 78, cy = HY + Math.sin(r) * 84;
      under += `<circle cx="${cx}" cy="${cy}" r="${26 + OW}" fill="${OL}"/>`; top += `<circle cx="${cx}" cy="${cy}" r="26" fill="${hairCol}"/>`; }
    g += under + `<ellipse cx="-14" cy="-352" rx="72" ry="44" fill="${hairCol}"/>` + top;
    for (let a = 175; a <= 310; a += 26) { const r = a * Math.PI / 180;
      g += `<path d="M ${HX + Math.cos(r) * 74} ${HY + Math.sin(r) * 80} a 9 9 0 1 1 9 6" stroke="#6a4430" stroke-width="4" fill="none"/>`; }
  } else if (hair === 'bald') {
    g += `<ellipse cx="-20" cy="-378" rx="26" ry="10" fill="#fff" opacity=".45" transform="rotate(-18 -20 -378)"/>`;
  }
  if (hat === 'crown') {                                                        // Persian royal crown (tall, crenellated)
    g += P(`M -62 -362 L -66 -470 L -44 -470 L -44 -488 L -22 -488 L -22 -470 L 0 -470 L 0 -488 L 22 -488 L 22 -470 L 44 -470 L 44 -488 L 66 -488 L 66 -470 L 80 -470 L 74 -360 C 30 -376, -20 -376, -62 -362 Z`, '#f0b83a');
    g += `<path d="M -60 -392 C -10 -404, 40 -404, 76 -392" stroke="#b07a1a" stroke-width="7" fill="none"/>`;
    [[-30, -430], [8, -432], [46, -430]].forEach(([cx, cy], i) => g += C(cx, cy, 8, ['#c0302a', '#2a6ac0', '#c0302a'][i]));
  }

  // beards (drawn before the mouth so the mouth sits on top)
  if (beard === 'short') {
    g += P(`M -58 -300 C -62 -226, 4 -196, 58 -210 C 84 -218, 96 -246, 92 -278 C 76 -262, 64 -250, 48 -246 C 20 -244, -16 -262, -40 -300 Z`, beardCol);
    g += `<path d="M -30 -254 a 8 8 0 1 1 10 6 M 0 -230 a 8 8 0 1 1 10 6 M 34 -226 a 8 8 0 1 1 10 6" stroke="#6a4430" stroke-width="4" fill="none"/>`;
  } else if (beard === 'persian') {                                            // long, square, rows of curls
    g += P(`M -54 -296 C -56 -240, -40 -170, -4 -146 L 84 -146 C 98 -186, 98 -240, 92 -278 C 76 -262, 64 -250, 48 -246 C 20 -244, -16 -262, -54 -296 Z`, beardCol);
    for (let k = 0; k < 4; k++) g += `<path d="M ${-30 + k * 4} ${-222 + k * 20} q 14 -12 28 0 q 14 -12 28 0 q 14 -12 28 0" stroke="#6a4430" stroke-width="4" fill="none"/>`;
    g += P(`M 30 -262 C 50 -272, 80 -270, 96 -258 C 80 -252, 56 -252, 30 -262 Z`, beardCol);   // moustache
  }

  // ---------------- face: eyes, brows, nose, mouth (by expression) ----------------
  const eyes = [[24, -306, 1], [64, -302, .85]];                                // near eye, far eye (smaller)
  const pdx = look[0] * 6, pdy = look[1] * 6;
  const eyeOpen = (big = 1, pr = 7) => eyes.map(([ex, ey, k]) =>
    E(ex, ey, 15 * k * big, 20 * k * big, '#fff', `stroke-width="${OW}"`) + `<circle cx="${ex + pdx}" cy="${ey + pdy}" r="${pr * k}" fill="${OL}"/>` +
    `<circle cx="${ex + pdx - 3}" cy="${ey + pdy - 4}" r="${2.4 * k}" fill="#fff"/>`).join('');
  const brow = (d) => `<path d="${d}" stroke="${OL}" stroke-width="9" fill="none" stroke-linecap="round"/>`;
  let face2 = '';
  if (exp === 'normal' || exp === 'nervous') {
    face2 += eyeOpen(1, exp === 'nervous' ? 5 : 7);
    face2 += brow(exp === 'nervous' ? 'M 8 -330 Q 22 -342 36 -338 M 52 -336 Q 64 -342 76 -332' : 'M 8 -336 Q 22 -346 38 -338 M 52 -336 Q 64 -344 78 -334');
    face2 += exp === 'nervous' ? `<path d="M 30 -262 q 6 -6 12 0 q 6 6 12 0 q 6 -6 12 0" stroke="${OL}" stroke-width="5" fill="none" stroke-linecap="round"/>`
                               : `<path d="M 32 -264 Q 48 -254 64 -264" stroke="${OL}" stroke-width="5" fill="none" stroke-linecap="round"/>`;
  } else if (exp === 'smug') {
    face2 += eyeOpen(1, 7);
    // heavy upper lids = scheming look
    eyes.forEach(([ex, ey, k]) => face2 += `<path d="M ${ex - 17 * k} ${ey} C ${ex - 17 * k} ${ey - 26 * k}, ${ex + 17 * k} ${ey - 26 * k}, ${ex + 17 * k} ${ey} Z" fill="${skin}" stroke="${OL}" stroke-width="${OW}"/>`);
    face2 += brow('M 8 -330 Q 22 -334 38 -328 M 50 -344 Q 64 -356 80 -342');
    face2 += `<path d="M 30 -266 Q 50 -256 70 -274" stroke="${OL}" stroke-width="5" fill="none" stroke-linecap="round"/>`;
  } else if (exp === 'happy') {
    face2 += eyes.map(([ex, ey, k]) => `<path d="M ${ex - 13 * k} ${ey + 4} Q ${ex} ${ey - 16 * k} ${ex + 13 * k} ${ey + 4}" stroke="${OL}" stroke-width="7" fill="none" stroke-linecap="round"/>`).join('');
    face2 += brow('M 8 -342 Q 22 -354 38 -346 M 52 -344 Q 64 -354 78 -342');
    face2 += P('M 24 -272 Q 50 -230 78 -274 Z', '#5a1a14') + `<path d="M 38 -252 Q 50 -244 62 -254" stroke="#e06a6a" stroke-width="9" fill="none" stroke-linecap="round"/>`;
  } else if (exp === 'shock') {
    face2 += eyeOpen(1.25, 4);
    face2 += brow('M 6 -350 Q 22 -362 38 -352 M 52 -350 Q 64 -360 80 -348');
    face2 += E(48, -254, 11, 16, '#5a1a14');
  } else if (exp === 'angry') {
    face2 += eyeOpen(1, 6);
    face2 += brow('M 6 -340 L 38 -326 M 82 -340 L 52 -326');
    face2 += P('M 28 -266 L 70 -266 L 66 -248 L 32 -248 Z', '#fff') + `<path d="M 30 -257 L 68 -257" stroke="${OL}" stroke-width="3"/>`;
  }
  g += face2;
  g += `<path d="M 86 -296 Q 102 -284 88 -272" stroke="${OL}" stroke-width="5" fill="${skin}" stroke-linecap="round"/>`;   // nose bump
  if (sweat) g += P('M -40 -392 C -30 -372, -24 -364, -32 -356 C -42 -350, -52 -360, -48 -372 Z', '#9ad4ff');

  // front arm last (in front of the body)
  g += arm(A.front);
  if (prop === 'goblet') g += P(`M ${A.front[2][0] - 14} ${A.front[2][1] - 40} L ${A.front[2][0] + 14} ${A.front[2][1] - 40} L ${A.front[2][0] + 6} ${A.front[2][1] - 16} L ${A.front[2][0] - 6} ${A.front[2][1] - 16} Z`, '#f0b83a');

  return `<g transform="translate(${x} ${y}) scale(${s * face} ${s})">${g}</g>`;
}

// A comic speech bubble with a tail pointing at (tx, ty).
function bubble(x, y, w, h, tx, ty, lines, size = 34) {
  const tail = `M ${x + w * .3} ${y + h - 4} L ${tx} ${ty} L ${x + w * .45} ${y + h - 4} Z`;
  return `<g>${P(tail, '#fff8ea')}<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="34" fill="#fff8ea" stroke="${OL}" stroke-width="7"/>
    <path d="${tail.replace(/ Z$/, '')}" fill="#fff8ea"/>
    ${lines.map((l, i) => `<text x="${x + w / 2}" y="${y + 58 + i * (size + 10)}" text-anchor="middle" font-family="'Patrick Hand', 'Comic Sans MS', cursive" font-size="${size}" fill="${OL}">${l}</text>`).join('')}</g>`;
}
