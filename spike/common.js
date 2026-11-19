// Shared helpers for the art-direction spike scenes (throwaway).
// Each scene page: <script src="common.js"></script> then builds SVG strings with add().

// Seeded random numbers: the same picture every render.
function rng(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
// Frame size: vertical Short by default; a page can set window.SIZE = [1920, 1080] before loading this file.
const W = (window.SIZE || [1080, 1920])[0], H = (window.SIZE || [1080, 1920])[1];
const out = []; const add = s => out.push(s);

// Blur filters are created on demand, measured in page space (so thin lines blur too).
const usedBlur = new Set();
const blur = n => { usedBlur.add(n); return `filter="url(#b${n})"`; };

// A tapered limb between two joints (circle at each end + a quad between).
function capsule(a, ra, b, rb, fill) {
  const dx = b[0]-a[0], dy = b[1]-a[1], L = Math.hypot(dx, dy) || 1, nx = -dy/L, ny = dx/L;
  const p = [[a[0]+nx*ra, a[1]+ny*ra],[b[0]+nx*rb, b[1]+ny*rb],[b[0]-nx*rb, b[1]-ny*rb],[a[0]-nx*ra, a[1]-ny*ra]];
  return `<g fill="${fill}"><circle cx="${a[0]}" cy="${a[1]}" r="${ra}"/><circle cx="${b[0]}" cy="${b[1]}" r="${rb}"/>
    <polygon points="${p.map(q=>q.join(',')).join(' ')}"/></g>`;
}

// ---------- CHARACTER KIT ----------
// One bearded Greek man's head + shoulders in PROFILE, facing LEFT, in local coordinates
// (roughly x 380-960, y 520-1760). Each style draws the SAME geometry its own way:
// poster = flat lit planes, paper-cut = layered paper, silhouette = pure shape.
// Flip to face right with transform="translate(X Y) scale(-s s)".
const HEAD = {
  // skin: forehead -> straight Greek nose -> under nose, then hidden edges + neck
  face: `M 470 770 C 452 800, 444 840, 442 880 L 436 905 C 432 912, 433 922, 430 930 L 398 1028
         C 392 1040, 398 1054, 414 1054 L 430 1058 L 432 1090 L 440 1180 L 560 1250 C 568 1300, 574 1350, 580 1420
         L 770 1420 C 762 1330, 760 1240, 775 1150 L 800 900 C 790 760, 650 700, 470 770 Z`,
  hair: `M 478 790 C 470 720, 560 640, 680 650 C 790 660, 860 740, 860 850 C 860 960, 830 1040, 800 1110
         C 790 1140, 770 1160, 745 1150 C 760 1080, 740 1010, 700 990 C 680 930, 650 880, 600 860
         C 560 840, 520 820, 478 790 Z`,
  beard: `M 430 1058 C 455 1062, 480 1060, 500 1052 C 540 1050, 570 1070, 590 1060 C 620 1040, 650 1020, 680 1030
          C 700 1080, 680 1160, 640 1220 C 600 1270, 540 1300, 470 1320 C 440 1300, 420 1250, 418 1200
          C 415 1150, 412 1110, 422 1085 C 410 1080, 412 1066, 430 1058 Z`,
  ear: `M 650 940 C 680 925, 700 960, 690 1000 C 685 1025, 665 1030, 655 1015 C 660 990, 655 965, 650 940 Z`,
  eye: `M 452 930 C 465 920, 485 920, 498 928 C 485 936, 466 938, 452 930 Z`,
  iris: [463, 929],
  brow: `M 440 906 C 460 893, 490 892, 516 903`,
  mouth: `M 428 1090 C 438 1093, 450 1092, 460 1088`,
  // shadow side of the face (light comes from the front)
  shade: `M 585 840 C 612 920, 602 1000, 577 1060 C 562 1110, 562 1160, 602 1200 L 900 1450 L 900 800 Z`,
  // tunic + cloak over the shoulders
  tunic: `M 470 1400 C 520 1360, 600 1350, 640 1380 L 860 1400 C 900 1500, 920 1650, 930 1770 L 290 1770
          C 310 1600, 380 1460, 470 1400 Z`,
  cloak: `M 640 1360 C 720 1330, 820 1360, 880 1420 C 930 1520, 950 1650, 960 1770 L 560 1770
          C 600 1640, 640 1520, 640 1360 Z`,
};

// Random points inside an SVG path (for hair curls, beard strands, texture marks).
const _ctx = document.createElement('canvas').getContext('2d');
function scatterIn(d, n, R, [x0, y0, x1, y1]) {
  const p = new Path2D(d), pts = [];
  for (let k = 0; k < n * 40 && pts.length < n; k++) {
    const x = x0 + R() * (x1 - x0), y = y0 + R() * (y1 - y0);
    if (_ctx.isPointInPath(p, x, y)) pts.push([x, y]);
  }
  return pts;
}
// A point on a cubic bezier at t (0..1), used to place bristles along a curve.
function bez(a, b, c, d, t) {
  const u = 1 - t;
  return [0, 1].map(i => u*u*u*a[i] + 3*u*u*t*b[i] + 3*u*t*t*c[i] + t*t*t*d[i]);
}

// Film grain + vignette + blur defs. Call once at the very end of a scene.
function finish({ grain = .18, vignette = .85 } = {}) {
  add(`<defs>
    <filter id="grainF"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" stitchTiles="stitch"/>
      <feColorMatrix values="0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 .6 0"/></filter>
    <radialGradient id="vigF" cx="50%" cy="48%" r="75%"><stop offset=".55" stop-opacity="0"/><stop offset="1" stop-opacity="${vignette}"/></radialGradient>
    ${[...usedBlur].map(b=>`<filter id="b${b}" filterUnits="userSpaceOnUse" x="-500" y="-500" width="${W + 1000}" height="${H + 1000}"><feGaussianBlur stdDeviation="${b}"/></filter>`).join('')}
  </defs>`);
  add(`<rect width="${W}" height="${H}" fill="url(#vigF)"/>`);
  add(`<rect width="${W}" height="${H}" filter="url(#grainF)" opacity="${grain}" style="mix-blend-mode:overlay"/>`);
  document.getElementById('s').innerHTML = out.join('\n');
}
