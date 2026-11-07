// Music and sound effects. Every cue is pinned to the action it belongs to, in bars of the film. The picture
// is locked before this was written, as the skill's rule says: change the picture, and re-check this table.

import React from 'react';
import {Audio, Sequence, staticFile} from 'remotion';
import {B, BAR, S} from './timeline';

const ANVIL_A = 'fs-270588', ANVIL_B = 'fs-270589', KEY = 'fs-378085', TICK = 'fs-534094', WHOOSH = 'fs-427823', SWOOSH = 'fs-786514';
const RISER = 'fs-685256', BOOM = 'fs-535615', SPARKLE = 'fs-844398', TAP = 'fs-262958', CLICK = 'fs-144194', STAMP = 'fs-160678', THUD = 'fs-653910', SWITCH = 'fs-348225';

const beat = BAR / 4;
const OUTPUT_LAG = 1; // the AAC encoder's lead-in; everything starts this much sooner

// Frames of silence or build before each sound's hit, measured with tools/sfx_lag.py. The anvil samples
// start with almost half a second of nothing, so a blow would land late without this.
const LEAD: Record<string, number> = {[ANVIL_A]: 13, [ANVIL_B]: 9, [KEY]: 3, [WHOOSH]: 6, [SWOOSH]: 5, [BOOM]: 1, [TICK]: 1, [RISER]: 82, [SPARKLE]: 3};

type Cue = {at: number; src: string; volume: number; length?: number};

const cues: Cue[] = [];
const add = (at: number, src: string, volume: number, length?: number) => cues.push({at: Math.round(at), src, volume, length});

// 1. The timer races: ticks getting closer together, then one soft landing on "23 minutes ago"
{
  let f = B(1), gap = 13;
  while (f < B(2.55)) {
    add(f, TICK, 1.1 - 0.3 * ((f - B(1)) / (B(2.55) - B(1))));
    f += gap;
    gap = Math.max(2.4, gap * 0.9);
  }
  add(B(2.55), THUD, 0.4);
}
// 2 and 3. The ring draws, then the drop
add(B(S.reveal), RISER, 1);
add(B(S.reveal), BOOM, 0.6);
add(B(5.3), WHOOSH, 0.28);
// The wordmark's letters are stamped
for (let i = 0; i < 12; i += 2) add(B(6) + i * 2, STAMP, 1 - i * 0.03);
// 4. The dive, then a blow every two beats on the anvil, as loud as each other
add(B(7.8), SWOOSH, 0.6);
for (let i = 0; i < 6; i++) {
  const close = i < 4 ? 1 : 0.55;
  add(B(S.working) + i * 2 * beat, i % 2 ? ANVIL_B : ANVIL_A, (i % 2 ? 0.82 : 0.5) * close);
}
add(B(10.1), WHOOSH, 0.3);
// 5. Hopping until you come; then the key, in the music's one empty bar
add(B(S.needs) + 6, SWOOSH, 0.3);
for (let i = 0; B(S.needs) + i * 1.5 * beat < B(13); i++) add(B(S.needs) + i * 1.5 * beat, THUD, 0.16);
add(B(13), KEY, 1.8);
// 6. The iris, the leap and its landing
add(B(S.done), WHOOSH, 0.42);
add(B(S.done) + 4, SPARKLE, 1.8);
add(B(S.done) + 14, THUD, 0.42);
// 7. Asleep; the light goes at 18:00
add(B(S.sleep) - 3, SWOOSH, 0.2);
add(B(17.5), SWITCH, 2);
// 8. The tap, then one click of the bezel per beat
add(B(20.5), TAP, 0.6);
add(B(21.45), WHOOSH, 0.22);
for (let i = 0; i < 6; i++) add(B(21.5) + i * beat, CLICK, 1.5);
// 9 and 10. The colour goes; the lights go; four looks click by
add(B(S.stale), THUD, 0.32);
add(B(S.dim), SWITCH, 1.7);
for (let i = 1; i < 4; i++) add(B(S.dim) + i * beat, CLICK, 0.6);
// 11. The packet crosses and each stop lights up
for (let i = 0; i < 3; i++) {
  add(B(S.pipeline) + beat * (1.6 + (5 / 3) * i), SWOOSH, 0.28);
  add(B(S.pipeline) + beat * (1 + (5 / 3) * (i + 1)), CLICK, 1);
}
// 12. The family lands, the wordmark is stamped, the address arrives
add(B(S.outro), BOOM, 0.48);
for (let i = 0; i < 6; i++) add(B(S.outro) + i * 2 * beat + 9, THUD, 0.46 - i * 0.025);
for (let i = 0; i < 12; i += 2) add(B(29.5) + i * 2, STAMP, 1 - i * 0.03);
add(B(29.5) + 24, BOOM, 0.42);
add(B(29.5) + 26, SPARKLE, 1.2);
add(B(30.75), KEY, 1.4);
add(B(30.75) + 3, SPARKLE, 1);

export const SFX: React.FC<{bgm: boolean}> = ({bgm}) => (
  <>
    {bgm && <Audio src={staticFile('audio/music.wav')} volume={0.46} startFrom={OUTPUT_LAG} />}
    {cues.map((c, i) => (
      <Sequence key={i} from={Math.max(0, c.at - (LEAD[c.src] ?? 0) - OUTPUT_LAG)} durationInFrames={c.length ?? 150} layout="none">
        <Audio src={staticFile(`audio/sfx/${c.src}.mp3`)} volume={c.volume} />
      </Sequence>
    ))}
  </>
);
