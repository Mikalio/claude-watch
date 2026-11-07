// The Claude Code permission prompt everyone has walked away from, plus the timer that makes it hurt.

import React from 'react';
import {COLOURS, NEEDS} from './timeline';
import {MONO} from './kit';

const AMBER = COLOURS[NEEDS];
const GREY = '#7C828D', TEXT = '#D5D8DF', GREEN = '#3EE6A0';

export const Terminal: React.FC<{frame: number; timer: string; picked?: boolean; width?: number; font?: number; timerSize?: number}> = ({frame, timer, picked = false, width = 1240, font = 33, timerSize = 96}) => {
  const blink = Math.floor(frame / 16) % 2 === 0;
  const line = (children: React.ReactNode, colour = TEXT, weight = 400) => (
    <div style={{color: colour, fontWeight: weight, minHeight: font * 1.42, whiteSpace: 'pre'}}>{children}</div>
  );
  return (
    <div style={{width, background: '#111318', borderRadius: 22, boxShadow: '0 0 0 1px #262A32, 0 40px 120px rgba(0,0,0,0.7)', overflow: 'hidden', fontFamily: MONO, fontSize: font, lineHeight: 1.42}}>
      <div style={{height: 54, background: '#191C22', display: 'flex', alignItems: 'center', gap: 12, paddingLeft: 24}}>
        {[0, 1, 2].map((i) => <div key={i} style={{width: 16, height: 16, borderRadius: 8, background: '#3A3F49'}} />)}
      </div>
      <div style={{padding: '30px 40px 36px', position: 'relative'}}>
        {line('> Refactor the checkout and add tests', GREY)}
        {line(' ')}
        {line('Do you want to run this command?', TEXT, 700)}
        {line('  pytest tests/checkout -q', GREY)}
        {line(' ')}
        {line(<span>{picked ? '  ' : '❯ '}1. Yes{picked ? ' ' : ''}{picked ? <span style={{color: GREEN}}>✓</span> : null}</span>, picked ? GREEN : AMBER, 700)}
        {line("  2. Yes, don't ask again", GREY)}
        {line(<span>  3. No{!picked && blink ? <span style={{background: TEXT, color: TEXT, marginLeft: font * 0.4}}>_</span> : null}</span>, GREY)}
        <div style={{position: 'absolute', right: 40, bottom: 36, textAlign: 'right'}}>
          <div style={{color: GREY, fontSize: font * 0.8}}>{picked ? 'waited' : 'waiting on you'}</div>
          <div style={{color: picked ? GREEN : AMBER, fontSize: timerSize, fontWeight: 700, lineHeight: 1.05, fontVariantNumeric: 'tabular-nums'}}>{timer}</div>
        </div>
      </div>
    </div>
  );
};

export const mmss = (seconds: number) => {
  const s = Math.floor(seconds);
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
};
