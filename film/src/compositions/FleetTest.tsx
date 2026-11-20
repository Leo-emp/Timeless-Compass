// Remotion composition for the fleet motion test: frame number -> time -> drawFleet(t) -> SVG frame.
import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { SvgFrame } from '../SvgFrame';
import { drawFleet } from './fleet';

export const FleetTest: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return <SvgFrame svg={drawFleet(frame / fps)} />;
};
