// Tests for the cast kit: heads, faces, headgear and hoplite parts in the approved style (r16).
import { expect, test } from 'vitest';
import { head, face, hair, aspis, corinthClosed, corinthKingUp, hopliteBody, pole, bigBeard, longHairBack, longHairTop,
  lashes, gown, crown, tiara, circlet, laurel, aura, shadow, EXPRESSIONS } from './cast';
import { resetIds } from './core';

test('neutral head has two small dot eyes', () => {
  expect(head('#f0cfa8', 'neutral').match(/rx="6.5"/g)?.length).toBe(2);
});
test('blink closes the eyes with lids', () => {
  expect(head('#f0cfa8', 'neutral', { blink: true })).toContain('M-30 -299 Q-21 -293 -12 -299');
  expect(head('#f0cfa8', 'neutral')).not.toContain('M-30 -299 Q-21 -293 -12 -299');
});
test('every expression draws', () => {
  for (const ex of EXPRESSIONS) { expect(face(ex).length).toBeGreaterThan(50); }
});
test('shield emblem scales with the shield', () => {
  const s = aspis(0, 0, 30);
  expect(s).toContain(`stroke-width="${12 * 30 / 84}"`);
});
test('headgear, bodies and props all draw', () => {
  resetIds();
  const parts = [hair.chonmage(), hair.kabuto(), hair.corinthian(), hair.roman(), hair.wig(), hair.fedora(),
    corinthClosed('fan'), corinthClosed('king'), corinthClosed('none'), corinthKingUp(), hopliteBody('#d8a87c'),
    hopliteBody('#d8a87c', false), pole(0, 0, 0, 10), bigBeard('#fff', '#ccc'), longHairBack('#000'), longHairTop('#000'),
    lashes(), gown('#fff', '#d9b443'), crown(), tiara(), circlet(), laurel(), aura('gGold'), shadow(70)];
  for (const p of parts) expect(p).toMatch(/^</);
});
test('a closed helmet with no crest has no crest shape', () => {
  expect(corinthClosed('none')).not.toContain('#b23a2a');
});
