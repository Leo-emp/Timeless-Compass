// Tests for natural motion (r29): easing, anticipation, overshoot that settles, beats that land on the word.
import { expect, test } from 'vitest';
import { anticipate, beat, blinkAt, breathe, easeInOut, easeOutBack, tween } from './anim';
import { figure, part } from '../characters/figure';

test('tween settles exactly on its end value', () => {
  expect(tween(2, 0, 1, 0, 10, easeOutBack)).toBe(10);
  expect(tween(-1, 0, 1, 0, 10)).toBe(0);
});
test('easeOutBack overshoots then settles', () => {
  expect(Math.max(...[0.6, 0.7, 0.8, 0.9].map((x) => easeOutBack(x)))).toBeGreaterThan(1);
  expect(easeOutBack(1)).toBeCloseTo(1, 10);
});
test('anticipate moves back a little first', () => { expect(anticipate(0.1)).toBeLessThan(0); expect(anticipate(1)).toBeCloseTo(1, 10); });
test('easeInOut is smooth at both ends', () => { expect(easeInOut(0)).toBe(0); expect(easeInOut(1)).toBe(1); expect(easeInOut(0.05)).toBeLessThan(0.05); });
test('a beat starts lead seconds early and finishes after dur', () => {
  expect(beat(0.70, 1.0, 0.25, 0.5)).toBe(0);
  expect(beat(1.30, 1.0, 0.25, 0.5)).toBe(1);
  expect(beat(1.0, 1.0, 0.25, 0.5)).toBeGreaterThan(0.3);
});
test('blinks happen every few seconds and are short', () => {
  const frames = Array.from({ length: 24 * 12 }, (_, i) => blinkAt(i / 24, 7));
  for (let s = 0; s + 144 <= frames.length; s += 24) expect(frames.slice(s, s + 144).some(Boolean)).toBe(true);
  let run = 0, maxRun = 0; for (const f of frames) { run = f ? run + 1 : 0; maxRun = Math.max(maxRun, run); }
  expect(maxRun).toBeLessThanOrEqual(6);
});
test('breathing stays in -1..1 and differs per character', () => {
  expect(Math.abs(breathe(3.3, 1))).toBeLessThanOrEqual(1);
  expect(breathe(3.3, 1)).not.toBe(breathe(3.3, 2));
});
test('a blended arm sits between its two poses', () => {
  const look = { skin: '#dcae84', parts: {}, build: { height: 1, width: 1 } };
  const draw = (armL: any) => figure('t', look, { expr: 'neutral', armL }, { body: part('t', 'skin', '', '#dcae84'), head: () => '' });
  const mid = draw({ from: 'down', to: 'raise', k: 0.5 });
  expect(mid).not.toBe(draw('down')); expect(mid).not.toBe(draw('raise'));
});
