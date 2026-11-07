# Claude watch promo: design spec

**Goal.** Someone with a Galaxy Watch4 Classic who uses Claude Code watches this and wants it.
**Format.** 1920x1080, 30 fps, about 63 s, full animation. Two versions: with music, and sound effects only.
**Promise, only what the code does.** No buzz (the app doesn't vibrate). You can't approve from the watch, so you walk back.

## Look (from the product, not a promo skin)
- Near black stage, the five state colours: sleeping #A9A4F5, working #5BC2FF, needs #FFC233, your turn #3EE6A0, stale #AEB4BE. White #F5F6F8.
- Silkscreen for the wordmark, Roboto Flex for words (both already in the design canvas), JetBrains Mono for the terminal.
- The hero is the 3D watch with the real face (watchface.xml and its PNGs). The pixel creature is the star, drawn at whole-number scales.
- Motion voice: playful and punchy. Landings overshoot (1.08), words enter with blur-slide, and every cut sits on a bar.

## Music
Cat Walk (Arulo, Mixkit free licence). 130 bpm, 13.85 frames per beat, a bar is 55.38 frames. Edited on bar lines to fit the story.

## Storyboard (bars)
| # | Bars | Shot | Main motion | Words |
|---|---|---|---|---|
| 1 | 0-3 | Terminal permission prompt, cursor blinking | Slow push, timer races to 23:41 | Claude asked you something. / 23 minutes ago. |
| 2 | 3-5 | Black | Words, then an amber ring draws itself | You were making coffee. |
| 3 | 5-8 | Ring becomes the watch: the drop | Watch lights up, pulls back, wordmark stamps | CLAUDE WATCH / what it is |
| 4 | 8-11 | Dive through the screen | Hammer full frame on the beat, then pull out | Claude's working. So is it. / Which session. How many agents. |
| 5 | 11-14 | Terminal and watch side by side | Hops until you press 1; timer stops | Claude needs you. / 41 seconds. Not 23 minutes. |
| 6 | 14-16 | Green iris, creature leaps out full size | Dance on the beat | All done. Your turn. |
| 7 | 16-19 | Breakdown: watch asleep | Clock passes 18:00, sun hat to nightcap | Nothing running? It naps. |
| 8 | 19-23 | Counts, tap, Sessions, bezel turns | Bezel clicks scroll the list (the Classic moment) | It keeps count. / Tap for every session. / Turn the bezel to scroll. |
| 9 | 23-25 | Colour drains, dashed ring | Desaturate | No news for 40 minutes? It says so. |
| 10 | 25-26 | Lights down, always-on looks | Four dim looks on the beat | Arm down, it dims and keeps still. |
| 11 | 26-28 | Hook to relay to push to watch | A packet travels the line | Your hooks. Your relay. Your watch. / Pushes are kept few, to save your watch's battery. |
| 12 | 28-34 | Family photo around the wordmark: the peak | Every state lands on the beat | CLAUDE WATCH / github.com/Mikalio/claude-watch |

## Recipes used
circle-match-iris (ring-to-ring wipes, concentric), blur-slide (words), brand-ink-open (letters stamped),
outro-group-photo-launch (the ending), spotlight-hero-card (one hero, one full arc).

## Deliberate departures from the skill
- Portrait of a hardware product, not a web page, so no page captures. The face comes from its real files instead (Q1 in spirit).
- No motion workbench export (`src/workbench.ts`): not needed unless someone wants to edit the film by hand.

## Sample and story details, not facts about the app
- The session names are made up, and "23 minutes" and "41 seconds" are the story's numbers, not measurements.
- The screen is rendered from the face's real files, in Roboto; on the watch the words use the device's font.
- The watch model is hand-built to match a Classic 46 mm. It carries no maker's logos.

## Rebuilding
1. `npm install`
2. Copy `watch/face/src/main/res/raw/watchface.xml` to `public/face/raw/` and the PNGs from `res/drawable/` to `public/face/drawable/`.
3. `python tools/music.py` cuts the track into `public/audio/music.wav` (needs the video-shotcraft skill for the source track).
4. `npx remotion render src/index.ts Promo out/film.mp4 --audio-codec=aac --audio-bitrate=256k`
5. Effects only: `AUDIO_ONLY=1 npx remotion render src/index.ts Promo out/fx.aac --codec=aac --audio-bitrate=256k --props=props-nobgm.json`
6. Finish each with ffmpeg: `-c:v copy -af "volume=2.5dB,alimiter=limit=0.89:attack=3:release=80:level=disabled" -c:a aac -b:a 256k -movflags +faststart`
7. `python tools/check_audio.py out/film.mp4 out/fx.aac` measures clipping and where each sound lands. If the picture changes, re-pin `src/sound.tsx`.

Sound credits are in `public/audio/sfx/FREESOUND-CREDITS.md` (all CC0). Music: Cat Walk by Arulo, Mixkit Stock Music Free License.
