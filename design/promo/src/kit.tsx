// Shared pieces: fonts, words that enter with blur-slide, the pixel creature in each of its poses.

import React from 'react';
import {Easing, Img, interpolate, staticFile} from 'remotion';
import {loadFont as loadRoboto} from '@remotion/google-fonts/Roboto';
import {loadFont as loadPixel} from '@remotion/google-fonts/Silkscreen';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';
import {easeOutBack, WHITE} from './timeline';

export const ROBOTO = loadRoboto('normal', {weights: ['400', '500', '700'], subsets: ['latin', 'latin-ext']}).fontFamily;
export const PIXEL = loadPixel('normal', {weights: ['400', '700'], subsets: ['latin']}).fontFamily;
export const MONO = loadMono('normal', {weights: ['400', '500', '700'], subsets: ['latin', 'latin-ext']}).fontFamily;

// The hand-off curve from the outro recipe: a real overshoot on landing
export const FLY = Easing.bezier(0.34, 1.4, 0.44, 1);

/** A line whose words slide up out of a blur one after another, then fade away together. */
export const Words: React.FC<{
  text: string; frame: number; from: number; to?: number; x?: number; y: number; size?: number; colour?: string; weight?: number;
  width?: number; align?: 'left' | 'center'; font?: string; stagger?: number; shadow?: string;
}> = ({text, frame, from, to = Infinity, x = 112, y, size = 72, colour = WHITE, weight = 700, width = 900, align = 'left', font = ROBOTO, stagger = 3, shadow}) => {
  if (frame < from || frame > to) return null;
  const out = to === Infinity ? 1 : interpolate(frame, [to - 8, to], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const words = text.split(' ');
  return (
    <div style={{position: 'absolute', left: x, top: y, width, fontFamily: font, fontSize: size, fontWeight: weight, color: colour, lineHeight: 1.12, opacity: out, textAlign: align, letterSpacing: font === PIXEL ? 0 : '-0.012em', textShadow: shadow}}>
      {words.map((word, i) => {
        const p = interpolate(frame - from - i * stagger, [0, 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)});
        return (
          <span key={i} style={{display: 'inline-block', marginRight: '0.26em', opacity: p, transform: `translateY(${(1 - p) * 0.38}em)`, filter: p >= 0.999 ? undefined : `blur(${(1 - p) * 18}px)`}}>
            {word}
          </span>
        );
      })}
    </div>
  );
};

/** Letters stamped down one by one: the wordmark. */
export const Wordmark: React.FC<{frame: number; from: number; to?: number; x: number; y: number; size: number; align?: 'left' | 'center'; width?: number}> = ({frame, from, to = Infinity, x, y, size, align = 'left', width = 1000}) => {
  const letters = 'CLAUDE WATCH'.split('');
  return (
    <div style={{position: 'absolute', left: x, top: y, width, fontFamily: PIXEL, fontSize: size, lineHeight: 1, color: WHITE, textAlign: align, whiteSpace: 'nowrap', opacity: to === Infinity ? 1 : interpolate(frame, [to - 8, to], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
      {letters.map((l, i) => {
        const k = (frame - from - i * 2) / 7;
        if (k < 0) return <span key={i} style={{opacity: 0}}>{l === ' ' ? ' ' : l}</span>;
        return (
          <span key={i} style={{display: 'inline-block', transform: `scale(${1.35 - 0.35 * easeOutBack(k, 2.2)})`}}>
            {l === ' ' ? ' ' : l}
          </span>
        );
      })}
    </div>
  );
};

const png = (name: string) => staticFile(`face/drawable/${name}.png`);

export const Pixel: React.FC<{name: string; x: number; y: number; w: number; h: number; s: number; style?: React.CSSProperties}> = ({name, x, y, w, h, s, style}) => (
  <Img src={png(name)} style={{position: 'absolute', left: x * s, top: y * s, width: w * s, height: h * s, imageRendering: 'pixelated', ...style}} />
);

// Each pose stands with its feet at (x, ground) in face pixels, and moves as watchface.xml moves it.
export const Sleeper: React.FC<{hat: 'day' | 'night'; t: number; x: number; ground: number; s: number; icon?: boolean}> = ({hat, t, x, ground, s, icon = true}) => (
  <>
    <Pixel name={`sleep_top_${hat}`} x={x} y={ground - 105 - 4.375 * (1 - Math.cos(t * 1.5708))} w={140} h={91} s={s} />
    <Pixel name="sleep_low" x={x} y={ground - 35} w={140} h={35} s={s} />
    {icon && <Pixel name="icon_sleeping" x={x + 148} y={ground - 125 - 5 * Math.abs(Math.sin(t * 1.57))} w={40} h={50} s={s} />}
  </>
);

export const Worker: React.FC<{t: number; x: number; ground: number; s: number}> = ({t, x, ground, s}) => {
  const k = ((t % 1) + 1) % 1, c = (v: number) => Math.min(1, Math.max(0, v));
  const raised = c((k - 0.17) / 0.56), strike = c((k - 0.88) / 0.12), rebound = 12 * Math.sin(Math.PI * c((k - 0.04) / 0.13));
  const angle = -78 * raised * raised * (3 - 2 * raised) * (1 - strike * strike) - rebound;
  const jump = 8.4 * Math.sin(Math.PI * c(k / 0.19));
  const y = ground - 112 - jump;
  return (
    <>
      <Pixel name="anvil" x={x + 105} y={ground - 21} w={63} h={21} s={s} />
      {k < 0.08 && <Pixel name="sparks_near" x={x + 98} y={ground - 77} w={98} h={56} s={s} />}
      {k >= 0.08 && k < 0.2 && <Pixel name="sparks" x={x + 98} y={ground - 77} w={98} h={56} s={s} />}
      <Pixel name="creature_working" x={x} y={y} w={105} h={112} s={s} />
      <Pixel name="work_arm" x={x + 21} y={y} w={140} h={147} s={s} style={{transform: `rotate(${angle}deg)`}} />
    </>
  );
};

export const Hopper: React.FC<{t: number; x: number; ground: number; s: number; icon?: boolean}> = ({t, x, ground, s, icon = true}) => (
  <>
    <Pixel name="creature_needs" x={x} y={ground - 84 - 28 * Math.abs(Math.sin(t * 4.76))} w={98} h={84} s={s} />
    {icon && <Pixel name="icon_needs" x={x + 110} y={ground - 98 - 5 * Math.abs(Math.sin(t * 3.93))} w={40} h={50} s={s} />}
  </>
);

export const Dancer: React.FC<{t: number; x: number; ground: number; s: number; icon?: boolean}> = ({t, x, ground, s, icon = true}) => {
  const wave = Math.sin(t * 7.14);
  return (
    <>
      <Pixel name="creature_done" x={x + 7 * wave} y={ground - 84 - 7 * Math.abs(wave)} w={98} h={84} s={s} style={{transformOrigin: '50% 100%', transform: `rotate(${6 * wave}deg)`}} />
      {icon && <Pixel name="icon_done" x={x + 110} y={ground - 98} w={40} h={50} s={s} style={{opacity: (155 + 100 * Math.abs(Math.sin(t * 3.5))) / 255}} />}
    </>
  );
};

export const Stale: React.FC<{x: number; ground: number; s: number; icon?: boolean}> = ({x, ground, s, icon = true}) => (
  <>
    <Pixel name="creature_stale" x={x} y={ground - 84} w={98} h={84} s={s} />
    {icon && <Pixel name="icon_stale" x={x + 110} y={ground - 98} w={40} h={50} s={s} />}
  </>
);

/** Square pixel specks flying out from a point: dust on a landing, or a firework. */
export const Burst: React.FC<{frame: number; from: number; x: number; y: number; colours: string[]; count?: number; reach?: number; size?: number; seed?: number; life?: number}> = ({frame, from, x, y, colours, count = 14, reach = 170, size = 14, seed = 1, life = 26}) => {
  const k = (frame - from) / life;
  if (k < 0 || k > 1) return null;
  const rnd = (i: number) => {
    const v = Math.sin(i * 127.1 + seed * 311.7) * 43758.5453;
    return v - Math.floor(v);
  };
  return (
    <>
      {Array.from({length: count}, (_, i) => {
        const a = rnd(i) * Math.PI * 2, r = (0.45 + rnd(i + 50) * 0.55) * reach * (1 - (1 - k) ** 3);
        return (
          <div key={i} style={{
            position: 'absolute', left: x + Math.cos(a) * r, top: y + Math.sin(a) * r + 90 * k * k, width: size, height: size,
            background: colours[i % colours.length], opacity: k > 0.7 ? (1 - k) / 0.3 : 1,
          }} />
        );
      })}
    </>
  );
};
