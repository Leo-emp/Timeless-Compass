// Tests for the camera: eased moves, parallax by depth, deterministic handheld, rack focus (r34).
import { expect, test } from 'vitest';
import { camLayer, camTransform, rackFocus, type Cam } from './camera';

const PUSH: Cam = { move: 'push_in', amount: 0.1, t0: 0, t1: 4 };

test('push_in scales by 1 + amount for the hero layer and less for far layers', () => {
  expect(camTransform(4, 1, PUSH).scale).toBeCloseTo(1.1, 6);
  expect(camTransform(4, 0.2, PUSH).scale).toBeCloseTo(1.02, 6);
  expect(camTransform(0, 1, PUSH).scale).toBeCloseTo(1, 6);
});
test('the move eases (slow at the start)', () => {
  expect(camTransform(0.4, 1, PUSH).scale - 1).toBeLessThan(0.1 * 0.1);
});
test('static leaves the layer untouched', () => {
  const t = camTransform(2, 1, { move: 'static', amount: 0, t0: 0, t1: 4 });
  expect([t.scale, t.dx, t.dy]).toEqual([1, 0, 0]);
});
test('pans move near layers further than far ones', () => {
  const c: Cam = { move: 'pan_left', amount: 0.1, t0: 0, t1: 2 };
  expect(Math.abs(camTransform(2, 1, c).dx)).toBeGreaterThan(Math.abs(camTransform(2, 0.3, c).dx));
});
test('handheld is deterministic and small', () => {
  const c: Cam = { move: 'handheld', amount: 1, t0: 0, t1: 10 };
  expect(camTransform(3.3, 1, c)).toEqual(camTransform(3.3, 1, c));
  expect(Math.abs(camTransform(3.3, 1, c).dx)).toBeLessThan(12);
});
test('rack focus moves the blur from the near layer to the far layer', () => {
  const c: Cam = { move: 'rack_focus', amount: 6, t0: 0, t1: 2 };
  expect(rackFocus(0, 1, c)).toBe(0); expect(rackFocus(0, 0.2, c)).toBeGreaterThan(0);
  expect(rackFocus(2, 1, c)).toBeGreaterThan(0); expect(rackFocus(2, 0.2, c)).toBe(0);
});
test('camLayer wraps content in a transform group', () => { expect(camLayer(1, 1, PUSH, '<rect/>')).toContain('<rect/>'); });
test('pans use the frame width they are given', () => {
  const c: Cam = { move: 'pan_left', amount: 0.1, t0: 0, t1: 2 };
  expect(camTransform(2, 1, c, 1080, 1920).dx).toBeCloseTo(108, 6);
});
