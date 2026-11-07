// The 3D watch for the stretches of the film it's in. Asks the stage for a picture each frame, then adds the
// stage's colour glow behind it and the screen's bloom over it.

import React, {useLayoutEffect, useRef, useState} from 'react';
import {continueRender, delayRender} from 'remotion';
import {getStage, RING_CM} from './stage';
import {SCALE} from './face.js';
import {B, BAR, beatsAt, camAt, clamp01, COLOURS, faceAt, S, SESSIONS, smooth, STAGE, WORK} from './timeline';

export const useStage = () => {
  const [stage, setStage] = useState<any>(null);
  const [handle] = useState(() => delayRender('the 3D watch'));
  useLayoutEffect(() => {
    getStage().then((s) => {
      setStage(s);
      continueRender(handle);
    });
  }, [handle]);
  return stage;
};

// How the screen changes for Sessions: bars from S.sessions
const TAP = S.sessions + 1.5;
const SCROLL_FROM = S.sessions + 2.5;

function sessionsScroll(frame: number) {
  // One click of the bezel per beat, each eased: 15 degrees of bezel, one row and a bit of list
  const beats = (frame - B(SCROLL_FROM)) / (BAR / 4);
  if (beats <= 0) return {detents: 0};
  const whole = Math.floor(beats), part = beats - whole;
  return {detents: Math.min(6, whole + smooth(part / 0.45))};
}

export function shotFor(frame: number, stage: any) {
  const bar = frame / BAR;
  const shown = faceAt(frame);
  const face = bar >= 7.9 && bar < 9.98 ? {...shown, text: '', date: false} : shown;
  const cam = camAt(frame);
  const glow = COLOURS[face.value];
  const showSessions = bar >= TAP + 0.06 && bar < S.stale;
  const {detents} = sessionsScroll(frame);
  const tapAge = frame - B(TAP);

  const draw = (c: CanvasRenderingContext2D) => {
    if (showSessions) {
      const k = clamp01((frame - B(TAP + 0.06)) / 12);
      stage.drawSessions(c, {
        rows: SESSIONS, scroll: detents * 44, rise: (1 - smooth(k)) * 36, alpha: smooth(k),
        note: 'Last update 18:12:41, took 2 s', reveal: clamp01((frame - B(TAP + 0.06)) / 22),
      });
    } else {
      stage.drawFace(c, face);
    }
    if (tapAge >= 0 && tapAge < 16) { // a touch on the glass
      const k = tapAge / 16;
      c.setTransform(SCALE, 0, 0, SCALE, 0, 0);
      c.strokeStyle = `rgba(255,255,255,${0.75 * (1 - k)})`;
      c.lineWidth = 7 * (1 - k) + 1;
      c.beginPath();
      c.arc(225, 225, 22 + 70 * (1 - (1 - k) ** 2), 0, Math.PI * 2);
      c.stroke();
      c.fillStyle = `rgba(255,255,255,${0.22 * (1 - k)})`;
      c.beginPath();
      c.arc(225, 225, 22 + 20 * k, 0, Math.PI * 2);
      c.fill();
    }
  };

  // Light levels: the reveal brings the studio up; always-on takes it down
  const reveal = smooth((frame - B(S.reveal)) / 26);
  const asleep = bar >= S.sleep && bar < S.sessions;
  const lightsDown = bar >= S.dim ? 1 - 0.8 * smooth((frame - B(S.dim)) / 10) : 1;
  const stale = bar >= S.stale && bar < S.dim;
  return {
    cam,
    draw,
    level: reveal * lightsDown * (asleep ? 0.8 : 1) * (stale ? 0.7 : 1),
    glow,
    glowPower: face.ambient ? 0.1 : stale ? 0.3 : 1,
    bezel: -15 * detents,
    sweep: frame * 0.16,
    screen: 1,
  };
}

export const WatchLayer: React.FC<{frame: number}> = ({frame}) => {
  const stage = useStage();
  const ref = useRef<HTMLCanvasElement>(null);
  const shot = stage ? shotFor(frame, stage) : null;

  useLayoutEffect(() => {
    if (!stage || !ref.current) return;
    const out = ref.current.getContext('2d');
    const where = stage.render(shot);
    const face = faceAt(frame);
    const colour = COLOURS[face.value];
    const stale = frame >= B(S.stale) && frame < B(S.dim);
    const dimmed = frame >= B(S.dim);

    out.globalCompositeOperation = 'source-over';
    out.filter = 'none';
    out.globalAlpha = 1;
    out.fillStyle = STAGE;
    out.fillRect(0, 0, 1920, 1080);
    // The screen's colour falling on the wall behind it
    const r = (RING_CM + 0.6) * where.scale;
    const wall = out.createRadialGradient(where.x, where.y, r * 0.5, where.x, where.y, r * 3.2);
    const strength = dimmed ? 0.03 : stale ? 0.06 : frame >= B(S.reveal) ? 0.2 : 0;
    wall.addColorStop(0, `${colour}${Math.round(strength * 255).toString(16).padStart(2, '0')}`);
    wall.addColorStop(1, `${colour}00`);
    out.fillStyle = wall;
    out.fillRect(0, 0, 1920, 1080);

    out.drawImage(stage.renderer.domElement, 0, 0, 1920, 1080);

    // The screen glows: a blurred copy added on top, less of it when the camera is inside the screen
    const inside = clamp01((10 - shot.cam.dist) / 5);
    out.globalCompositeOperation = 'screen';
    out.globalAlpha = dimmed ? 0.1 : 0.5 - 0.3 * inside;
    out.filter = `blur(${Math.round(16 + 16 * (1 - inside))}px)`;
    out.drawImage(ref.current, 0, 0);
    out.filter = 'none';
    out.globalAlpha = 1;
    out.globalCompositeOperation = 'source-over';
  });

  if (!stage) return null;
  return <canvas ref={ref} width={1920} height={1080} style={{position: 'absolute', inset: 0}} />;
};
