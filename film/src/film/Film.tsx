// Remotion component that plays a job's timed plan with its fresh scenes (one frame = frameAt(frame)).
import React from 'react';
import { useCurrentFrame } from 'remotion';
import { SvgFrame } from '../SvgFrame';
import { frameAt, type SceneFn, type TimedPlan } from './sequence';

export const Film: React.FC<{ plan: TimedPlan; scenes: Record<string, SceneFn> }> = ({ plan, scenes }) => {
  const frame = useCurrentFrame();
  return <SvgFrame svg={frameAt(frame, plan, scenes)} />;
};
