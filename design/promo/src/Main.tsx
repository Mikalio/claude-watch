// The film, scene by scene. Every "from" is a bar of the music (see timeline.ts and SPEC.md).

import React from 'react';
import {AbsoluteFill, Audio, Img, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {B, BAR, beatsAt, clamp01, COLOURS, DONE, easeOutBack, easeOutExpo, NEEDS, S, SLEEP, smooth, STAGE, STALE, WHITE, WORK} from './timeline';
import {Burst, Dancer, FLY, Hopper, MONO, Pixel, PIXEL, ROBOTO, Sleeper, Stale, Words, Wordmark, Worker} from './kit';
import {Terminal, mmss} from './Terminal';
import {WatchLayer} from './WatchLayer';
import {pxPerCm, RING_CM} from './stage';
import {SFX} from './sound';

const Grey = '#B9BEC8';

// --- 1. Claude asked you something -----------------------------------------------------------------
const Hook: React.FC<{frame: number}> = ({frame}) => {
  // The timer holds, then races up to 23:41 and settles
  const from = B(1), to = B(2.6);
  const k = clamp01((frame - from) / (to - from));
  const seconds = (23 * 60 + 41) * (k * k * (3 - 2 * k));
  const push = 1 + 0.05 * (frame / B(3));
  return (
    <AbsoluteFill style={{background: STAGE}}>
      <div style={{position: 'absolute', left: 340, top: 340, transformOrigin: '50% 40%', transform: `scale(${push})`}}>
        <Terminal frame={frame} timer={mmss(seconds)} />
      </div>
      <Words text="Claude asked you something." frame={frame} from={10} x={340} y={100} size={88} width={1300} />
      <Words text="23 minutes ago." frame={frame} from={B(2.55)} x={340} y={200} size={88} width={1300} colour={COLOURS[NEEDS]} />
    </AbsoluteFill>
  );
};

// --- 2. You were making coffee, and the ring draws itself ------------------------------------------
const Coffee: React.FC<{frame: number}> = ({frame}) => {
  const start = B(S.coffee), ringFrom = B(4), ringTo = B(5);
  const k = clamp01((frame - ringFrom) / (ringTo - ringFrom));
  const sweep = k * k * (3 - 2 * k);
  const r = RING_CM * pxPerCm(11);
  const tip = -Math.PI / 2 + sweep * Math.PI * 2;
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <Words text="You were making coffee." frame={frame} from={start + 6} to={ringFrom + 6} x={0} y={490} size={92} width={1920} align="center" stagger={4} />
      {k > 0 && (
        <svg width={1920} height={1080} style={{position: 'absolute', inset: 0, filter: `drop-shadow(0 0 ${10 + 22 * sweep}px ${COLOURS[NEEDS]})`}}>
          <circle cx={960} cy={540} r={r} fill="none" stroke={COLOURS[NEEDS]} strokeWidth={7.5} strokeDasharray={`${sweep * 2 * Math.PI * r} ${2 * Math.PI * r}`} transform="rotate(-90 960 540)" />
          <rect x={960 + Math.cos(tip) * r - 7} y={540 + Math.sin(tip) * r - 7} width={14} height={14} fill={WHITE} />
        </svg>
      )}
    </AbsoluteFill>
  );
};

// --- 3 to 5: the words over the 3D watch -----------------------------------------------------------
const OverWatch: React.FC<{frame: number}> = ({frame}) => {
  const bar = frame / BAR;
  return (
    <AbsoluteFill>
      {bar < S.working && (
        <>
          <Wordmark frame={frame} from={B(6)} to={B(7.72)} x={104} y={330} size={104} />
          <Words text="A little creature on your Galaxy Watch that shows what Claude is doing." frame={frame} from={B(6.5)} to={B(7.72)} x={112} y={470} size={52} weight={500} width={800} colour={Grey} stagger={1.4} />
        </>
      )}
      <Words text="Claude's working." frame={frame} from={B(S.working) + 12} to={B(9.9)} x={70} y={46} size={84} width={800} shadow="0 2px 22px rgba(0,30,90,0.55)" />
      <Words text="So is it." frame={frame} from={B(8.6)} to={B(9.9)} x={760} y={46} size={84} colour="#FFFFFF" width={500} shadow="0 2px 22px rgba(0,30,90,0.55)" />
      <Words text="Which session." frame={frame} from={B(10.1)} to={B(11)} x={112} y={380} size={84} />
      <Words text="How many agents." frame={frame} from={B(10.35)} to={B(11)} x={112} y={476} size={84} colour={COLOURS[WORK]} />
    </AbsoluteFill>
  );
};

// --- 5. It hops until you come, and the timer finally stops ------------------------------------------
const Needs: React.FC<{frame: number}> = ({frame}) => {
  const pressed = B(13);
  const picked = frame >= pressed;
  const seconds = picked ? 41 : 41 * clamp01((frame - B(11.4)) / (pressed - B(11.4)));
  const enter = easeOutExpo((frame - B(11) - 2) / 20);
  const punch = picked ? 1 + 0.05 * (1 - easeOutExpo((frame - pressed) / 12)) : 1;
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 70 - (1 - enter) * 1100, top: 420, transformOrigin: '50% 50%', transform: `scale(${punch})`}}>
        <Terminal frame={frame} timer={mmss(seconds)} picked={picked} width={990} font={30} timerSize={84} />
      </div>
      <Words text="Claude needs you." frame={frame} from={B(11) + 6} to={B(13)} x={84} y={160} size={84} colour={COLOURS[NEEDS]} width={900} />
      <Words text="It hops until you come." frame={frame} from={B(11.7)} to={B(13)} x={84} y={260} size={84} width={1000} />
      <Words text="41 seconds." frame={frame} from={pressed + 2} to={B(14)} x={84} y={160} size={84} colour={COLOURS[DONE]} width={900} />
      <Words text="Not 23 minutes." frame={frame} from={B(13.32)} to={B(14)} x={84} y={260} size={84} width={1000} />
    </AbsoluteFill>
  );
};

// --- 6. All done: the creature leaps out of the watch ------------------------------------------------
const WATCH_X = 1398, WATCH_Y = 540;
const YourTurn: React.FC<{frame: number}> = ({frame}) => {
  const start = B(S.done), t = beatsAt(frame) * 0.44;
  const s = 4; // 28 screen pixels per art pixel
  const leap = easeOutBack((frame - start - 3) / 16, 1.5);
  const y = interpolate(leap, [0, 1], [320, 0]);
  const scale = interpolate(leap, [0, 1], [0.5, 1]);
  const green = COLOURS[DONE];
  // The ring pushes the iris open, as the recipe says; the circle is centred on the watch's screen
  const opened = (frame - start) / 11;
  const radius = 340 + 2000 * opened ** 2.4;
  const closing = (frame - B(S.sleep) + 9) / 9;
  const hole = closing > 0 ? 2300 * closing ** 2 : 0;
  const mask = closing > 0 ? `radial-gradient(circle at 760px 540px, transparent ${hole}px, black ${hole + 2}px)` : undefined;
  return (
    <AbsoluteFill style={{clipPath: opened < 1 ? `circle(${radius}px at ${WATCH_X}px ${WATCH_Y}px)` : undefined, WebkitMaskImage: mask, maskImage: mask}}>
      <AbsoluteFill style={{background: STAGE}} />
      <AbsoluteFill style={{background: `radial-gradient(circle at 50% 70%, ${green}3A 0%, ${green}00 60%)`}} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 880, height: 16, background: green, opacity: 0.85}} />
      <div style={{position: 'absolute', left: 960 - 196, top: 0, width: 0, height: 0, transform: `translate(0px, ${y}px) scale(${scale})`, transformOrigin: '196px 880px'}}>
        <Dancer t={t} x={0} ground={880 / s} s={s} icon={false} />
      </div>
      {Array.from({length: 6}, (_, i) => {
        // Sparkles from the real icon, twinkling on either side
        const spots = [[170, 300], [420, 520], [150, 660], [1450, 290], [1660, 520], [1390, 680]];
        const on = Math.abs(Math.sin(t * 3.5 + i * 1.1));
        return <Img key={i} src={staticFile('face/drawable/icon_done.png')} style={{position: 'absolute', left: spots[i][0], top: spots[i][1], width: 120, height: 150, imageRendering: 'pixelated', opacity: 0.25 + 0.75 * on * clamp01((frame - start - 8) / 10)}} />;
      })}
      <Words text="All done." frame={frame} from={start + 10} x={0} y={82} size={104} align="center" width={1920} />
      <Words text="Your turn." frame={frame} from={start + 22} x={0} y={196} size={104} align="center" width={1920} colour={green} />
      <Burst frame={frame} from={start + 14} x={960} y={840} colours={[green, WHITE]} count={22} reach={480} size={18} seed={3} life={34} />
      {opened < 1 && <div style={{position: 'absolute', left: WATCH_X - radius, top: WATCH_Y - radius, width: radius * 2, height: radius * 2, borderRadius: '50%', boxShadow: `inset 0 0 0 ${Math.max(6, 22 * (1 - opened))}px ${green}`}} />}
    </AbsoluteFill>
  );
};

// --- 7 to 10: the words over the 3D watch again -------------------------------------------------------
const OverWatch2: React.FC<{frame: number}> = ({frame}) => (
  <AbsoluteFill>
    <Words text="Nothing running?" frame={frame} from={B(S.sleep) + 8} to={B(17.42)} x={112} y={390} size={84} width={900} />
    <Words text="It naps." frame={frame} from={B(16.5)} to={B(17.42)} x={112} y={488} size={84} colour={COLOURS[SLEEP]} width={900} />
    <Words text="In a sun hat by day." frame={frame} from={B(17.5)} to={B(19)} x={112} y={350} size={84} width={780} />
    <Words text="In a nightcap by night." frame={frame} from={B(18)} to={B(19)} x={112} y={448} size={84} colour={COLOURS[SLEEP]} width={720} />

    <Words text="Several sessions?" frame={frame} from={B(S.sessions) + 6} to={B(20.42)} x={112} y={390} size={84} width={900} />
    <Words text="It keeps count." frame={frame} from={B(19.5)} to={B(20.42)} x={112} y={488} size={84} colour={COLOURS[NEEDS]} width={900} />
    <Words text="Tap for every session." frame={frame} from={B(20.6)} to={B(21.42)} x={112} y={400} size={84} width={640} />
    <Words text="Turn the bezel to scroll." frame={frame} from={B(21.6)} to={B(23)} x={112} y={390} size={84} width={760} />
    <Words text="On a Classic, it really turns." frame={frame} from={B(22.25)} to={B(23)} x={112} y={590} size={56} weight={500} colour={Grey} width={760} />

    <Words text="No news for 40 minutes?" frame={frame} from={B(S.stale) + 6} to={B(25)} x={112} y={370} size={84} width={720} colour={COLOURS[STALE]} />
    <Words text="It says so." frame={frame} from={B(23.7)} to={B(25)} x={112} y={572} size={84} width={720} />

    <Words text="Arm down, it dims and keeps still." frame={frame} from={B(S.dim) + 2} to={B(26)} x={112} y={420} size={72} weight={700} width={760} colour={Grey} stagger={1.6} />
  </AbsoluteFill>
);

// --- 11. How it gets there ----------------------------------------------------------------------------
const ICONS: Record<string, string[]> = {
  prompt: ['...........', '.##........', '..##.......', '...##......', '....##.....', '...##......', '..##.......', '.##........', '...........', '.....######', '.....######'],
  server: ['###########', '#.........#', '#.##....#.#', '#.........#', '###########', '...........', '###########', '#.........#', '#.##....#.#', '#.........#', '###########'],
  push: ['.....#.....', '....###....', '...#####...', '..#######..', '.#########.', '....###....', '....###....', '....###....', '....###....', '....###....', '....###....'],
};
const PixelIcon: React.FC<{rows: string[]; colour: string}> = ({rows, colour}) => (
  <svg width={110} height={110} viewBox="0 0 11 11" shapeRendering="crispEdges">
    {rows.flatMap((row, y) => [...row].map((c, x) => (c === '#' ? <rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill={colour} /> : null)))}
  </svg>
);

const Pipeline: React.FC<{frame: number}> = ({frame}) => {
  const start = B(S.pipeline), beat = BAR / 4;
  const xs = [270, 730, 1190, 1650], y = 500;
  const nodes = [
    {label: 'Claude Code hooks', icon: 'prompt', colour: WHITE},
    {label: 'Your relay', icon: 'server', colour: WHITE},
    {label: 'Firebase push', icon: 'push', colour: WHITE},
    {label: 'Your watch', icon: '', colour: WHITE},
  ];
  // The packet crosses one gap per two beats, with a little ease
  const travelled = clamp01((frame - start - beat) / (beat * 5)) * 3;
  const px = xs[0] + (xs[3] - xs[0]) * (travelled / 3);
  const colourNow = COLOURS[NEEDS];
  return (
    <AbsoluteFill style={{background: STAGE}}>
      <Words text="Your hooks. Your relay. Your watch." frame={frame} from={start + 4} x={0} y={140} size={92} align="center" width={1920} stagger={2} />
      <div style={{position: 'absolute', left: xs[0], top: y - 3, width: px - xs[0], height: 6, background: colourNow, boxShadow: `0 0 18px ${colourNow}`}} />
      <div style={{position: 'absolute', left: xs[0], top: y - 3, width: xs[3] - xs[0], height: 6, background: '#262A32', zIndex: -1}} />
      {nodes.map((n, i) => {
        const k = easeOutBack((frame - start - i * 5 - 6) / 12);
        const lit = travelled >= i - 0.02;
        return (
          <div key={i} style={{position: 'absolute', left: xs[i] - 200, top: y - 92, width: 400, textAlign: 'center', opacity: clamp01(k), transform: `scale(${k})`}}>
            <div style={{width: 184, height: 184, margin: '0 auto', borderRadius: i === 3 ? 92 : 30, overflow: 'hidden', background: '#111318', boxShadow: `0 0 0 ${lit ? 5 : 2}px ${lit ? colourNow : '#30343D'}${lit ? `, 0 0 30px ${colourNow}55` : ''}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: MONO, fontSize: 68, fontWeight: 700, color: n.colour}}>
              {i === 3 ? <Img src={staticFile('face/drawable/preview.png')} style={{width: 184, height: 184}} /> : <PixelIcon rows={ICONS[n.icon]} colour={lit ? colourNow : WHITE} />}
            </div>
            <div style={{fontFamily: ROBOTO, fontSize: 44, fontWeight: 700, color: WHITE, marginTop: 28, lineHeight: 1.1}}>{n.label}</div>
          </div>
        );
      })}
      <div style={{position: 'absolute', left: px - 13, top: y - 13, width: 26, height: 26, background: WHITE, boxShadow: `0 0 26px ${colourNow}`, opacity: travelled < 3 ? 1 : 0}} />
      <Words text="Pushes are kept few, to save your watch's battery." frame={frame} from={B(27)} x={0} y={880} size={48} weight={500} colour={Grey} align="center" width={1920} stagger={1} />
    </AbsoluteFill>
  );
};

// --- 12. The family photo --------------------------------------------------------------------------------
const Outro: React.FC<{frame: number}> = ({frame}) => {
  const start = B(S.outro), beat = BAR / 4;
  const s = 2; // 14 screen pixels per art pixel
  const ground = 930;
  const groundFace = ground / s;
  const t = beatsAt(frame);
  // Each family member lands on a beat, from a different side of the frame
  const family: {from: number; x: number; dx: number; dy: number; node: React.ReactNode; dust: string}[] = [
    {from: 0, x: 35, dx: -520, dy: -80, dust: COLOURS[SLEEP], node: <Sleeper hat="day" t={t / 2} x={0} ground={groundFace} s={s} />},
    {from: 2, x: 1510, dx: 620, dy: -60, dust: COLOURS[SLEEP], node: <Sleeper hat="night" t={t / 2 + 1.3} x={0} ground={groundFace} s={s} />},
    {from: 4, x: 446, dx: -300, dy: -800, dust: COLOURS[WORK], node: <Worker t={t / 2} x={0} ground={groundFace} s={s} />},
    {from: 6, x: 1279, dx: 300, dy: -800, dust: COLOURS[STALE], node: <Stale x={0} ground={groundFace} s={s} icon={false} />},
    {from: 8, x: 817, dx: -60, dy: -900, dust: COLOURS[NEEDS], node: <Hopper t={t * 0.44} x={0} ground={groundFace} s={s} icon={false} />},
    {from: 10, x: 1048, dx: 60, dy: -900, dust: COLOURS[DONE], node: <Dancer t={t * 0.44} x={0} ground={groundFace} s={s} icon={false} />},
  ];
  // A gentle crane down onto the group
  const crane = 1.1 - 0.1 * smooth((frame - start) / (BAR * 2));
  return (
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 92%, #1B2340 0%, #0B0E1C 46%, #06070C 100%)'}}>
      {Array.from({length: 46}, (_, i) => { // stars, on the same chunky pixels as everything else
        const a = Math.sin(i * 91.7) * 43758.5, b = Math.sin(i * 47.3) * 12741.3;
        const x = (a - Math.floor(a)) * 1920, y = (b - Math.floor(b)) * 620;
        const size = i % 3 === 0 ? 10 : 6;
        return <div key={i} style={{position: 'absolute', left: x - (x % 6), top: y - (y % 6), width: size, height: size, background: WHITE, opacity: 0.2 + 0.5 * Math.abs(Math.sin(t * 0.8 + i))}} />;
      })}
      <AbsoluteFill style={{transformOrigin: '50% 86%', transform: `scale(${crane})`}}>
        <div style={{position: 'absolute', left: -200, right: -200, top: ground, height: 16, background: '#4FBF67'}} />
        <div style={{position: 'absolute', left: -200, right: -200, top: ground + 16, height: 16, background: '#2F8F49'}} />
        {family.map((m, i) => {
          const k = (frame - start - m.from * beat) / 14;
          if (k < 0) return null;
          const e = FLY(clamp01(k));
          return (
            <div key={i} style={{position: 'absolute', left: m.x + (1 - e) * m.dx, top: (1 - e) * m.dy, width: 0, height: 0}}>
              {m.node}
            </div>
          );
        })}
        {family.map((m, i) => <Burst key={i} frame={frame} from={Math.round(start + m.from * beat + 11)} x={m.x + 90} y={ground} colours={[m.dust, WHITE]} count={10} reach={120} size={10} seed={i + 2} life={20} />)}
      </AbsoluteFill>
      <Wordmark frame={frame} from={B(29.5)} x={0} y={130} size={168} align="center" width={1920} />
      <Words text="Get it for your Galaxy Watch4 to Watch8." frame={frame} from={B(30.25)} x={0} y={322} size={60} weight={500} colour={Grey} align="center" width={1920} stagger={2} />
      {frame >= B(30.75) && (
        <div style={{position: 'absolute', left: 0, right: 0, top: 418, textAlign: 'center', opacity: clamp01((frame - B(30.75)) / 8), transform: `scale(${easeOutBack((frame - B(30.75)) / 14, 1.2)})`}}>
          <span style={{display: 'inline-block', fontFamily: MONO, fontWeight: 700, fontSize: 56, color: '#06070C', background: COLOURS[DONE], padding: '14px 34px', borderRadius: 18}}>github.com/Mikalio/wristling</span>
        </div>
      )}
      <Burst frame={frame} from={B(29.5)} x={420} y={250} colours={[COLOURS[NEEDS], WHITE]} count={18} reach={260} size={12} seed={11} life={34} />
      <Burst frame={frame} from={B(29.5)} x={1500} y={230} colours={[COLOURS[WORK], WHITE]} count={18} reach={260} size={12} seed={12} life={34} />
      <Burst frame={frame} from={B(30.75)} x={210} y={420} colours={[COLOURS[DONE], WHITE]} count={18} reach={230} size={12} seed={13} life={34} />
      <Burst frame={frame} from={B(30.75)} x={1710} y={420} colours={[COLOURS[SLEEP], WHITE]} count={18} reach={230} size={12} seed={14} life={34} />
      <Words text="Unofficial side project. Not affiliated with Anthropic or Samsung." frame={frame} from={B(31.25)} x={0} y={996} size={32} weight={400} colour="#8A9099" align="center" width={1920} stagger={0.5} />
    </AbsoluteFill>
  );
};

export const Promo: React.FC<{bgm?: boolean}> = ({bgm = true}) => {
  const frame = useCurrentFrame();
  const inHook = frame < B(S.coffee);
  const inCoffee = frame >= B(S.coffee) && frame < B(S.reveal);
  const watchA = frame >= B(S.reveal) && frame < B(S.done) + 12;
  const watchB = frame >= B(S.sleep) - 10 && frame < B(S.pipeline);
  const inDone = frame >= B(S.done) && frame < B(S.sleep);
  const fade = interpolate(frame, [B(S.end) - 34, B(S.end) - 4], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      {inHook && <Hook frame={frame} />}
      {inCoffee && <Coffee frame={frame} />}
      {(watchA || watchB) && <WatchLayer frame={frame} />}
      {watchA && frame < B(S.needs) && <OverWatch frame={frame} />}
      {watchA && frame >= B(S.needs) && <Needs frame={frame} />}
      {inDone && <YourTurn frame={frame} />}
      {watchB && <OverWatch2 frame={frame} />}
      {frame >= B(S.pipeline) && frame < B(S.outro) && <Pipeline frame={frame} />}
      {frame >= B(S.outro) && <Outro frame={frame} />}
      <AbsoluteFill style={{background: '#000', opacity: fade}} />
      <SFX bgm={bgm} />
    </AbsoluteFill>
  );
};
