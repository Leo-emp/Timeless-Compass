// Tests for text drawn as vector shapes (no runtime font loading; identical on every machine).
import { expect, test } from 'vitest';
import { textPath, textWidth } from './text';

test('text becomes a path, not a <text> element', () => {
  const s = textPath('THE GREEK FLEET', 27, 0, 0);
  expect(s).toContain('<path'); expect(s).not.toContain('<text'); expect(s).toContain(' d="M');
});
test('same text, same shapes', () => { expect(textPath('480 BC', 27, 10, 20)).toBe(textPath('480 BC', 27, 10, 20)); });
test('width grows with text and size', () => {
  expect(textWidth('AB', 27)).toBeGreaterThan(textWidth('A', 27));
  expect(textWidth('AB', 54)).toBeCloseTo(textWidth('AB', 27) * 2, 3);
});
test('middle anchor centres the text', () => {
  const w = textWidth('SALAMIS', 30);
  const m = textPath('SALAMIS', 30, 100, 0, 'middle').match(/M(-?[\d.]+)/);
  expect(Number(m![1])).toBeGreaterThanOrEqual(100 - w / 2 - 1);
  expect(Number(m![1])).toBeLessThan(100);
});
