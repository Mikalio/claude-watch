// The one timetable of the film. Everything is in bars of the music: 130 bpm at 30 fps.

export const FPS = 30;
export const BAR = (60 / 130) * 4 * FPS; // 55.38 frames
export const B = (bars: number) => Math.round(bars * BAR);
export const beatsAt = (frame: number) => frame / (BAR / 4);

export const S = {
  terminal: 0, coffee: 3, reveal: 5, working: 8, needs: 11, done: 14, sleep: 16,
  sessions: 19, stale: 23, dim: 25, pipeline: 26, outro: 28, end: 34,
};
export const LENGTH = B(S.end);

export const SLEEP = 0, WORK = 1, NEEDS = 2, DONE = 3, STALE = 4;
export const COLOURS = ['#A9A4F5', '#5BC2FF', '#FFC233', '#3EE6A0', '#AEB4BE'];
export const WHITE = '#F5F6F8';
export const STAGE = '#08090C';

const PC = 'Grocery offers · PC', AGENTS = 'Grocery offers · 3 agents', NONE = 'No sessions running', OLD = 'Last update 42 min ago';

// What the watch shows from each bar on
type Show = {bar: number; value: number; text: string; title?: string; at: [number, number]; battery: number; ambient?: boolean; to?: [number, number]; until?: number};
export const FACE: Show[] = [
  {bar: 5, value: NEEDS, text: PC, at: [10, 8], battery: 84},
  {bar: 8, value: WORK, text: AGENTS, at: [10, 9], battery: 83},
  {bar: 11, value: NEEDS, text: PC, at: [10, 24], battery: 81},
  {bar: 13.25, value: WORK, text: AGENTS, at: [10, 25], battery: 81},
  {bar: 14, value: DONE, text: PC, at: [10, 41], battery: 79},
  {bar: 16, value: SLEEP, text: NONE, at: [17, 56], to: [18, 0], until: 17.5, battery: 62},
  {bar: 17.5, value: SLEEP, text: NONE, at: [18, 0], battery: 61},
  {bar: 19, value: NEEDS, text: AGENTS, title: '1 needs you · 2 working', at: [18, 12], battery: 58},
  {bar: 23, value: STALE, text: OLD, at: [19, 5], battery: 52},
  {bar: 25, value: WORK, text: AGENTS, at: [19, 6], battery: 52, ambient: true},
  {bar: 25.25, value: NEEDS, text: PC, at: [19, 6], battery: 52, ambient: true},
  {bar: 25.5, value: DONE, text: PC, at: [19, 6], battery: 52, ambient: true},
  {bar: 25.75, value: STALE, text: OLD, at: [19, 6], battery: 52, ambient: true},
];

// The real expressions, slowed or sped by at most 8% so hammer blows, hops and sways land on the music
function faceSeconds(value: number, beats: number) {
  if (value === WORK || value === SLEEP) return beats / 2; // one blow every two beats; one breath every two bars
  return beats * 0.44; // a hop every beat and a half; a sway every beat
}

export function faceAt(frame: number) {
  const bar = frame / BAR;
  const shot = [...FACE].reverse().find((f) => f.bar <= bar) ?? FACE[0];
  let [hour, minute] = shot.at;
  if (shot.to) {
    const k = Math.min(1, (bar - shot.bar) / (shot.until - shot.bar));
    const total = hour * 60 + minute + (shot.to[0] * 60 + shot.to[1] - hour * 60 - minute) * k;
    hour = Math.floor(total / 60);
    minute = Math.floor(total % 60);
  }
  return {...shot, hour, minute, seconds: faceSeconds(shot.value, beatsAt(frame)), ambient: !!shot.ambient};
}

// Where the camera heads from each bar on. dist is in cm from the screen; 3.6 is inside it.
export type Cam = {dist: number; yaw: number; pitch: number; roll: number; px: number; py: number};
type Key = Cam & {bar: number; tau: number; cut?: boolean; drift?: number};
const KEYS: Key[] = [
  {bar: 4.9, cut: true, dist: 11, yaw: 0, pitch: 0, roll: 0, px: 0, py: 0, tau: 0.5},
  {bar: 5.4, dist: 15.5, yaw: -13, pitch: -6, roll: 0, px: -2.9, py: 0, tau: 0.75, drift: 0.012},
  {bar: 7.72, dist: 3.34, yaw: 0, pitch: 0, roll: 0, px: 0, py: -0.06, tau: 0.17},
  {bar: 10, dist: 13, yaw: 13, pitch: -8, roll: 0.5, px: -2.25, py: -0.15, tau: 0.42, drift: 0.01},
  {bar: 11, dist: 13.2, yaw: -15, pitch: -5, roll: -0.5, px: -3.25, py: 0, tau: 0.42, drift: 0.008},
  {bar: 15.7, cut: true, dist: 12.5, yaw: -12, pitch: -8, roll: -0.5, px: -2.1, py: 0, tau: 0.8, drift: 0.008},
  {bar: 17.4, dist: 10.8, yaw: 9, pitch: -7, roll: 0.5, px: -1.85, py: -0.05, tau: 0.8, drift: 0.008},
  {bar: 19, dist: 11.8, yaw: 0, pitch: -5, roll: 0, px: -2, py: -0.2, tau: 0.4, drift: 0.008},
  {bar: 20.4, dist: 10.4, yaw: 8, pitch: -4, roll: 0, px: -1.8, py: 0, tau: 0.45},
  {bar: 21.4, dist: 10, yaw: -30, pitch: -15, roll: -1, px: -1.75, py: 0.1, tau: 0.5, drift: 0.006},
  {bar: 23, dist: 12.6, yaw: 11, pitch: -6, roll: 0, px: -2.15, py: -0.05, tau: 0.45, drift: 0.008},
  {bar: 25, dist: 13.5, yaw: 0, pitch: -7, roll: 0, px: -2.3, py: 0, tau: 0.4},
];

const track: Cam[] = (() => {
  const names: (keyof Cam)[] = ['dist', 'yaw', 'pitch', 'roll', 'px', 'py'];
  const out: Cam[] = [];
  let a: any = null, b: any = null;
  const steps = 4;
  for (let n = 0; n <= LENGTH; n++) {
    for (let s = 0; s < steps; s++) {
      const f = n + s / steps;
      const key = [...KEYS].reverse().find((k) => B(k.bar) <= f) ?? KEYS[0];
      const target: any = {...key, dist: key.dist * (1 - (key.drift ?? 0) * ((f - B(key.bar)) / FPS))};
      if (!a || (key.cut && f - B(key.bar) < 1)) {
        a = {...target};
        b = {...target};
      }
      const k = 1 - Math.exp(-1 / (FPS * steps) / key.tau);
      for (const name of names) {
        a[name] += (target[name] - a[name]) * k;
        b[name] += (a[name] - b[name]) * k;
      }
    }
    out.push({dist: b.dist, yaw: b.yaw, pitch: b.pitch, roll: b.roll, px: b.px, py: b.py});
  }
  return out;
})();
export const camAt = (frame: number) => track[Math.max(0, Math.min(track.length - 1, frame))];

// The hook's timer, and the sample sessions on the Sessions screen
export const SESSIONS = [
  {name: 'Grocery offers', state: 'needs', place: 'PC', age: '2 min'},
  {name: 'Claude watch', state: 'working', place: '3 agents', age: '6 min'},
  {name: 'Trip planner', state: 'working', place: 'PC', age: '11 min'},
  {name: 'Invoice tool', state: 'done', place: 'PC', age: '4 min'},
  {name: 'Blog redesign', state: 'done', place: 'Cloud', age: '9 min'},
];

export const easeOutExpo = (k: number) => (k >= 1 ? 1 : 1 - 2 ** (-10 * Math.max(0, k)));
export const easeOutBack = (k: number, s = 1.70158) => {
  const t = Math.min(1, Math.max(0, k)) - 1;
  return t * t * ((s + 1) * t + s) + 1;
};
export const smooth = (k: number) => {
  const t = Math.min(1, Math.max(0, k));
  return t * t * (3 - 2 * t);
};
export const clamp01 = (k: number) => Math.min(1, Math.max(0, k));
