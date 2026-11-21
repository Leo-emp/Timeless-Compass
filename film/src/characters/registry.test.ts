// Every registered character: draws all six expressions, and every tagged part uses exactly its sheet colour (r19).
import { expect, test } from 'vitest';
import fs from 'node:fs';
import { EXPRESSIONS } from '../kit/cast';
import * as leonidas from './leonidas';
import * as themistocles from './themistocles';
import * as xerxes from './xerxes';

const MODULES: Record<string, { draw: (p: any) => string }> = { leonidas, themistocles, xerxes };

for (const [id, mod] of Object.entries(MODULES)) {
  const sheet = JSON.parse(fs.readFileSync(`../library/characters/${id}/sheet.json`, 'utf8'));
  const colours: Record<string, string> = { skin: sheet.look.skin, hair: sheet.look.hair.colour, ...(sheet.look.beard ? { beard: sheet.look.beard.colour } : {}), ...sheet.look.parts };

  test(`${id}: every expression looks different`, () => {
    expect(new Set(EXPRESSIONS.map((expr) => mod.draw({ expr }))).size).toBe(EXPRESSIONS.length);
  });
  test(`${id}: every tagged part uses its sheet colour`, () => {
    const svg = mod.draw({ expr: 'neutral' });
    const tags = [...svg.matchAll(/data-char="([^"]+)" data-part="([^"]+)" data-fill="([^"]+)"/g)];
    expect(tags.length).toBeGreaterThan(3);
    for (const [, char, part, fill] of tags) {
      expect(char).toBe(id);
      expect(fill.toLowerCase()).toBe(colours[part]?.toLowerCase());
    }
  });
}
