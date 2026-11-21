// Tests for lip sync: Rhubarb mouth cues -> our mouth shapes, only while that character speaks.
import { expect, test } from 'vitest';
import { mouthAt, RHUBARB_TO_MOUTH } from './lipsync';

const LINES = [{ speaker: 'XERXES', at: 2.0, cues: [{ start: 2.0, end: 2.2, shape: 'D' }, { start: 2.2, end: 2.5, shape: 'F' }] },
               { speaker: 'THEMISTOCLES', at: 5.0, cues: [{ start: 5.0, end: 5.3, shape: 'C' }] }];

test('inside a cue the mapped mouth shape is returned', () => {
  expect(mouthAt(2.1, LINES, 'XERXES')).toBe(RHUBARB_TO_MOUTH.D);
  expect(mouthAt(2.3, LINES, 'XERXES')).toBe('o');
});
test('outside every line the expression keeps its own mouth', () => { expect(mouthAt(3.0, LINES, 'XERXES')).toBeUndefined(); });
test("another speaker's line doesn't move this mouth", () => { expect(mouthAt(5.1, LINES, 'XERXES')).toBeUndefined(); });
test('speaker names match case-insensitively', () => { expect(mouthAt(5.1, LINES, 'themistocles')).toBe('open'); });
