// Tests for the film sequence: shots in order, transitions that never shift the timeline, unique ids per shot.
import { expect, test } from 'vitest';
import { frameAt, type TimedPlan, type SceneFn } from './sequence';
import { nextId, shade } from '../kit/core';

const scene: SceneFn = (ctx) => `<g data-shot="${ctx.shot.id}">${shade('<rect width="10" height="10"/>', 0, 0, 5, 5)}<rect id="${ctx.pid('sky')}"/></g>`;
const shot = (id: string, s: number, e: number, kind = 'cut', frames = 0) => ({
  id, start_f: s, end_f: e, scene: 'main', place: 'p', camera: { move: 'static', amount: 0 }, grade: { time: 'noon', mood: 'neutral' },
  transition_in: { kind, frames }, beats: [], sfx: [],
});
const PLAN: TimedPlan = { fps: 24, frames: 72, shots: [shot('s1', 0, 24), shot('s2', 24, 48, 'dissolve', 12), shot('s3', 48, 72, 'fade_black', 12)] as any };
const SCENES = { main: scene };

test('timeline total equals the voice (transitions overlap around the cut, never add frames)', () => {
  const total = PLAN.shots.reduce((a, s) => a + (s.end_f - s.start_f), 0);
  expect(total).toBe(PLAN.frames);
});
test('a hard cut frame shows exactly one shot', () => {
  const f = frameAt(10, PLAN, SCENES);
  expect(f.match(/data-shot=/g)!.length).toBe(1); expect(f).toContain('data-shot="s1"');
});
test('dissolve scenes have unique ids', () => {
  const f = frameAt(24, PLAN, SCENES);
  expect(f).toContain('data-shot="s1"'); expect(f).toContain('data-shot="s2"');
  expect(f).toContain('id="s1sky"'); expect(f).toContain('id="s2sky"');
  expect(f).toContain('s1c0'); expect(f).toContain('s2c0');
});
test('fade to black is fully black at the cut', () => {
  expect(frameAt(48, PLAN, SCENES)).toMatch(/fill="#000" opacity="1(\.0+)?"/);
});
test('ids outside a shot are plain', () => { expect(nextId('c')).toMatch(/^c\d+$/); });
