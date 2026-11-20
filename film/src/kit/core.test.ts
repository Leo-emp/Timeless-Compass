// Tests for the style-kit core: the helpers every drawing uses (outline, shading, limbs, random, easing).
import { expect, test } from 'vitest';
import { OUT, SW, rng, ease, wrap, sh, shade, resetIds, limb, hand, ln, bg } from './core';

test('rng is deterministic per seed', () => {
  const a = rng(480), b = rng(480);
  expect([a(), a()]).toEqual([b(), b()]);
});
test('rng values stay in [0, 1)', () => {
  const r = rng(7);
  for (let i = 0; i < 1000; i++) { const v = r(); expect(v).toBeGreaterThanOrEqual(0); expect(v).toBeLessThan(1); }
});
test('ease hits 0, 0.5, 1', () => { expect(ease(0)).toBe(0); expect(ease(0.5)).toBe(0.5); expect(ease(1)).toBe(1); });
test('wrap handles negatives', () => { expect(wrap(-10, 100)).toBe(90); expect(wrap(250, 100)).toBe(50); });
test('sh uses the house outline', () => {
  expect(sh('circle', { cx: 1, cy: 2, r: 3 }, '#fff')).toContain(`stroke="${OUT}" stroke-width="${SW}"`);
});
test('ids restart each frame so every machine draws the same frame', () => {
  resetIds(); const a = shade('<circle r="1"/>', 0, 0, 1, 1);
  resetIds(); const b = shade('<circle r="1"/>', 0, 0, 1, 1);
  expect(a).toBe(b);
});
test('two shades in one frame get different clip ids', () => {
  resetIds(); const a = shade('<circle r="1"/>', 0, 0, 1, 1), b = shade('<circle r="1"/>', 0, 0, 1, 1);
  expect(a).not.toBe(b);
});
test('limb is an outline tube (dark wide stroke under a coloured stroke)', () => {
  const s = limb('M0 0 L10 10', 20, '#abc');
  expect(s).toContain(`stroke-width="${20 + SW * 2}"`); expect(s).toContain('stroke="#abc"');
});
test('hand, ln and bg produce svg', () => {
  expect(hand(1, 2, '#fff')).toContain('<circle'); expect(ln('M0 0 L1 1')).toContain('<path');
  expect(bg('M0 0 L1 1 Z', '#fff')).toContain('stroke-width="4"');
});
