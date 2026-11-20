// Tests for the character drawing contract: one function draws a character in any Pose (rule r19).
import { expect, test } from 'vitest';
import { EXPRESSIONS, head } from '../kit/cast';
import { figure, part, type Look, type Pose } from './figure';

const LOOK: Look = { skin: '#dcae84', parts: { tunic: '#efe6cf' }, build: { height: 1, width: 1 } };
const draw = (pose: Pose) => figure('test', LOOK, pose, {
  body: part('test', 'tunic', '<rect width="10" height="10"/>', '#efe6cf'),
  head: (p) => head(LOOK.skin, p.expr, { blink: p.blink }),
});

test('every expression differs', () => {
  const out = new Set(EXPRESSIONS.map((expr) => draw({ expr })));
  expect(out.size).toBe(EXPRESSIONS.length);
});
test('part tags carry character, part and fill', () => {
  const s = part('leonidas', 'beard', '<path d="M0 0"/>', '#2a1d14');
  expect(s).toContain('data-char="leonidas"'); expect(s).toContain('data-part="beard"'); expect(s).toContain('data-fill="#2a1d14"');
});
test('facing left mirrors the figure', () => { expect(draw({ expr: 'neutral', facing: -1 })).toContain('scale(-1 1)'); });
test('mouth shapes change the face', () => {
  expect(draw({ expr: 'neutral', mouth: 'o' })).not.toBe(draw({ expr: 'neutral', mouth: 'closed' }));
});
test('arm poses change the arms', () => {
  expect(draw({ expr: 'neutral', armL: 'raise' })).not.toBe(draw({ expr: 'neutral', armL: 'down' }));
});
test('a held prop id reaches the hand', () => {
  expect(draw({ expr: 'neutral', armL: 'hold_spear', holds: 'spear1' })).toContain('data-holds="spear1"');
});
test('build scales the figure', () => {
  const tall = figure('test', { ...LOOK, build: { height: 1.1, width: 1 } }, { expr: 'neutral' }, { body: '', head: () => '' });
  expect(tall).toContain('scale(1 1.1)');
});
