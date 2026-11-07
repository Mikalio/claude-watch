// Runs the real watch face in the page: face.js reads watchface.xml and its PNGs and evaluates the same
// expressions the watch does, at your own local time. The chips only change what the complication would send.

import {loadFace, SCALE} from './face.js';

const MOODS = {
  working: {value: 1, text: 'Grocery offers · 3 agents'},
  needs: {value: 2, text: 'Grocery offers · PC'},
  done: {value: 3, text: 'Grocery offers · PC'},
  sleeping: {value: 0, text: 'No sessions running'},
  stale: {value: 4, text: 'Last update 42 min ago'},
};
const AT_REST = {working: 0.62, needs: 0.33, done: 0.22, sleeping: 1, stale: 0}; // a good pose to stand still in

const canvas = document.getElementById('face');
const context = canvas.getContext('2d');
canvas.width = canvas.height = 450 * SCALE;
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
let mood = 'working';
let forcedNight = null; // null follows the real clock
let paused = reduced;
let onScreen = true;
let dirty = true;
let last = 0;
let drawFace = null;

const realNight = (d) => d.getHours() < 6 || d.getHours() >= 18;
const showingNight = (d) => forcedNight ?? realNight(d);

function draw(now) {
  const d = new Date();
  const night = showingNight(d);
  drawFace(context, {
    ...MOODS[mood],
    hour: night === realNight(d) ? d.getHours() : night ? 22 : 10,
    minute: d.getMinutes(),
    seconds: paused ? AT_REST[mood] : now / 1000,
    battery: 84,
    ambient: false,
    dow: d.toLocaleDateString('en-GB', {weekday: 'short'}),
    day: d.getDate(),
    month: d.toLocaleDateString('en-GB', {month: 'short'}),
  });
}

function tick(now) {
  requestAnimationFrame(tick);
  if (!drawFace || !onScreen) return;
  if (paused && !dirty) return;
  if (now - last < 30) return; // about 30 frames a second is plenty for pixel art
  last = now;
  dirty = false;
  draw(now);
}

for (const chip of document.querySelectorAll('[data-mood]')) {
  chip.addEventListener('click', () => {
    mood = chip.dataset.mood;
    dirty = true;
    for (const other of document.querySelectorAll('[data-mood]')) other.setAttribute('aria-pressed', String(other === chip));
  });
}

const dayNight = document.getElementById('daynight');
const labelDayNight = () => {
  dayNight.textContent = showingNight(new Date()) ? 'Show day' : 'Show night';
};
dayNight.addEventListener('click', () => {
  forcedNight = !showingNight(new Date());
  dirty = true;
  labelDayNight();
});
labelDayNight();

const pause = document.getElementById('pause');
const labelPause = () => {
  pause.textContent = paused ? 'Play' : 'Pause';
};
pause.addEventListener('click', () => {
  paused = !paused;
  dirty = true;
  labelPause();
});
labelPause();

new IntersectionObserver((entries) => {
  onScreen = entries[0].isIntersecting;
}).observe(canvas);

setInterval(() => {
  dirty = true; // keeps the clock right while paused
}, 20000);

document.getElementById('copy').addEventListener('click', async (event) => {
  await navigator.clipboard.writeText(document.getElementById('prompt').textContent);
  event.target.textContent = 'Copied';
  setTimeout(() => {
    event.target.textContent = 'Copy this prompt';
  }, 1800);
});

try {
  await Promise.all([document.fonts.load('700 36px Roboto'), document.fonts.load('400 22px Roboto')]);
  ({drawFace} = await loadFace('face', 'Roboto'));
  requestAnimationFrame(tick);
} catch (error) {
  // If the face can't load, show a still of it rather than a blank screen
  console.error(error);
  document.querySelector('.watch-body').src = 'media/working.jpg';
  canvas.hidden = true;
  document.querySelector('.glass').hidden = true;
  document.querySelector('.controls').hidden = true;
}
