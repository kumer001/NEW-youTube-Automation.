import React from 'react';
import {Composition} from 'remotion';
import {Story, StoryProps} from './Story';

const defaultProps: StoryProps = {
  durationInFrames: 300,
  music: '',
  scenes: [
    {
      caption: 'Preview scene',
      emojis: [
        {char: '🐓', x: 50, y: 45, size: 280, anim: 'bounce'},
        {char: '☀️', x: 78, y: 24, size: 200, anim: 'float'},
      ],
      bg: ['#ffb347', '#ff6f91'],
      audio: '',
      frames: 300,
    },
  ],
};

export const Root: React.FC = () => (
  <Composition
    id="Story"
    component={Story}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={300}
    defaultProps={defaultProps}
    calculateMetadata={({props}) => ({durationInFrames: Math.max(30, props.durationInFrames)})}
  />
);
