// Still pictures of the watch for the landing page, one frame each, drawn by the same stage as the film.
// The first has a blank screen: on the page, the real face runs live on top of it.

import React, {useLayoutEffect, useRef} from 'react';
import {useCurrentFrame} from 'remotion';
import {useStage} from './WatchLayer';
import {COLOURS, DONE, NEEDS, SESSIONS, SLEEP, STAGE, STALE, WORK} from './timeline';

const PC = 'Grocery offers · PC', AGENTS = 'Grocery offers · 3 agents', NONE = 'No sessions running', OLD = 'Last update 42 min ago';
const SIDE = {dist: 12.4, yaw: -14, pitch: -6, roll: 0, px: 0, py: 0};

// dist 13 straight on: the screen is a true circle, 593 px across on a 1080 px frame
export const STILLS: any[] = [
  {id: 'watch', blank: true, cam: {dist: 13, yaw: 0, pitch: 0, roll: 0, px: 0, py: 0}, sweep: 40},
  {id: 'working', value: WORK, text: AGENTS, at: [10, 9], battery: 83, seconds: 0.62},
  {id: 'needs', value: NEEDS, text: PC, at: [10, 24], battery: 81, seconds: 0.33},
  {id: 'done', value: DONE, text: PC, at: [10, 41], battery: 79, seconds: 0.22},
  {id: 'sleeping', value: SLEEP, text: NONE, at: [22, 8], battery: 62, seconds: 1},
  {id: 'stale', value: STALE, text: OLD, at: [19, 5], battery: 52, seconds: 0, level: 0.75, power: 0.3},
  {id: 'sessions', sessions: true, value: NEEDS, cam: {dist: 10.6, yaw: -30, pitch: -15, roll: -1, px: 0, py: 0.1}, bezel: -30},
];

export const Stills: React.FC = () => {
  const frame = useCurrentFrame();
  const stage = useStage();
  const ref = useRef<HTMLCanvasElement>(null);
  const shot = STILLS[frame];

  useLayoutEffect(() => {
    if (!stage || !ref.current) return;
    const colour = shot.blank ? '#000000' : COLOURS[shot.value];
    const where = stage.render({
      cam: shot.cam ?? SIDE,
      draw: (c: CanvasRenderingContext2D) => {
        if (shot.blank) {
          c.setTransform(1, 0, 0, 1, 0, 0);
          c.fillStyle = '#000';
          c.fillRect(0, 0, c.canvas.width, c.canvas.height);
        } else if (shot.sessions) {
          stage.drawSessions(c, {rows: SESSIONS, scroll: 88, alpha: 1, note: 'Last update 18:12:41, took 2 s'});
        } else {
          stage.drawFace(c, {value: shot.value, text: shot.text, hour: shot.at[0], minute: shot.at[1], seconds: shot.seconds, battery: shot.battery, ambient: false});
        }
      },
      level: shot.level ?? 1,
      glow: colour,
      glowPower: shot.blank ? 0 : shot.power ?? 1,
      bezel: shot.bezel ?? 0,
      sweep: shot.sweep ?? 112,
    });
    const out = ref.current.getContext('2d');
    out.globalCompositeOperation = 'source-over';
    out.filter = 'none';
    out.globalAlpha = 1;
    out.fillStyle = STAGE;
    out.fillRect(0, 0, 1920, 1080);
    if (!shot.blank) {
      const wall = out.createRadialGradient(where.x, where.y, 120, where.x, where.y, 780);
      wall.addColorStop(0, `${colour}30`);
      wall.addColorStop(1, `${colour}00`);
      out.fillStyle = wall;
      out.fillRect(0, 0, 1920, 1080);
    }
    out.drawImage(stage.renderer.domElement, 0, 0, 1920, 1080);
    if (!shot.blank) {
      out.globalCompositeOperation = 'screen';
      out.globalAlpha = 0.45;
      out.filter = 'blur(26px)';
      out.drawImage(ref.current, 0, 0);
    }
  });

  if (!stage) return null;
  return <canvas ref={ref} width={1920} height={1080} style={{position: 'absolute', inset: 0}} />;
};
