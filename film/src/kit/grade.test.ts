// Tests for colour grading + film finish (r34): a grade per time of day and mood, vignette, grain, letterbox.
import { expect, test } from 'vitest';
import { GRADES, finish, gradeDefs, graded, luminance } from './grade';

test('each time of day has its own grade', () => {
  const ms = Object.values(GRADES).map((g) => g.matrix.join(','));
  expect(new Set(ms).size).toBe(ms.length);
});
test('night is darker than noon', () => { expect(luminance(GRADES.night.matrix)).toBeLessThan(luminance(GRADES.noon.matrix)); });
test('grain changes every frame but is the same for the same moment', () => {
  expect(finish(1.0, 's1')).toBe(finish(1.0, 's1'));
  expect(finish(1.0, 's1')).not.toBe(finish(1.0 + 1 / 24, 's1'));
});
test('letterbox bars are 2.39:1', () => {
  const f = finish(0, 's1', { letterbox: true });
  expect(f).toContain('height="138"');
});
test('a grade wraps content with its filter', () => {
  const g = graded('s2', 'dusk', 'tension', '<rect/>');
  expect(g).toContain('filter="url(#s2grade)"'); expect(g).toContain('<rect/>'); expect(gradeDefs('s2', 'dusk', 'tension')).toContain('id="s2grade"');
});
