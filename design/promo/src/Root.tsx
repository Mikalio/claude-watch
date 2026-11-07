import React from 'react';
import {Composition} from 'remotion';
import {Promo} from './Main';
import {FPS, LENGTH} from './timeline';
import {Stills, STILLS} from './Stills';

export const Root: React.FC = () => (
  <>
    <Composition id="Promo" component={Promo} width={1920} height={1080} fps={FPS} durationInFrames={LENGTH} defaultProps={{bgm: true}} />
    <Composition id="Stills" component={Stills} width={1920} height={1080} fps={FPS} durationInFrames={STILLS.length} />
  </>
);
