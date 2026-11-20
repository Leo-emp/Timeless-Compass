// Tests for the fleet motion test scene (port of spike/art_dir/scene_fleet_anim.html).
import { expect, test } from 'vitest';
import { drawFleet } from './fleet';

test('same moment -> same picture (every machine renders identically)', () => {
  expect(drawFleet(4.0)).toBe(drawFleet(4.0));
});
test('the place + date card is there (its letters are drawn as shapes)', () => {
  expect(drawFleet(2)).toContain('data-role="textbox"');
  expect(drawFleet(2)).toContain('data-role="text"');
});
test('it moves', () => {
  expect(drawFleet(0)).not.toBe(drawFleet(1));
});
test('the commander blinks at 2.5 s and not at 1 s', () => {
  const lid = 'M-30 -299 Q-21 -293 -12 -299';
  expect(drawFleet(2.5)).toContain(lid);
  expect(drawFleet(1)).not.toContain(lid);
});
