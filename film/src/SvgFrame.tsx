// One full video frame: the SVG string a scene's draw(t) returns, shown at the composition's size.
import React from 'react';
import { AbsoluteFill } from 'remotion';

export const SvgFrame: React.FC<{ svg: string; width?: number; height?: number }> = ({ svg, width = 1920, height = 1080 }) => (
  <AbsoluteFill style={{ backgroundColor: '#000' }}>
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} xmlns="http://www.w3.org/2000/svg"
      dangerouslySetInnerHTML={{ __html: svg }} />
  </AbsoluteFill>
);
