// Every composition the film engine can render. Real videos register their own compositions per job
// (plan 5+); these two are the engine/speed tests from plan 1.
import React from 'react';
import { Composition } from 'remotion';
import { FleetTest } from './compositions/FleetTest';

export const Root: React.FC = () => (
  <>
    {/* 8-second motion test (matches spike/art_dir/fleet_motion.mp4) */}
    <Composition id="FleetTest" component={FleetTest} width={1920} height={1080} fps={24} durationInFrames={192} />
    {/* 15-minute speed test: the same scene for 21,600 frames */}
    <Composition id="FleetTestLong" component={FleetTest} width={1920} height={1080} fps={24} durationInFrames={21600} />
  </>
);
