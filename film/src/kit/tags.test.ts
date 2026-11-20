// Tests for the tags the still checks read (data-role on faces, hands, props, text) and the place/date card.
import { expect, test } from 'vitest';
import { head, pole, aspis } from './cast';
import { hand } from './core';
import { card } from './tags';

test('a head is one face group', () => { expect(head('#f0cfa8', 'neutral').startsWith('<g data-role="face"')).toBe(true); });
test('a hand can say what it holds', () => {
  expect(hand(0, 0, '#fff', 'spear1')).toContain('data-holds="spear1"');
  expect(hand(0, 0, '#fff')).toContain('data-role="hand"');
});
test('props carry their id', () => {
  expect(pole(0, 0, 0, 10, '#8b5a2b', 'spear1')).toContain('data-id="spear1"');
  expect(aspis(0, 0, 30, 'shield1')).toContain('data-id="shield1"');
  expect(pole(0, 0, 0, 10)).toContain('data-role="prop"');
});
test('the card is a textbox with text inside', () => {
  const c = card(100, 50, 460, 62, 'THE GREEK FLEET · 480 BC');
  expect(c).toContain('data-role="textbox"'); expect(c).toContain('data-role="text"'); expect(c).toContain('Cinzel');
});
