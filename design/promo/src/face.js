// Draws the Claude face from its own watchface.xml and PNGs, so the film shows what the watch runs: the
// same Conditions pick the scene and pose, and the same expressions move them. Also draws the Sessions
// screen, laid out as MainActivity.kt lays it out.

export const SCALE = 6; // canvas pixels per face pixel, so the pixel art stays sharp when the camera dives in

const FUNCS = {
  sin: Math.sin, cos: Math.cos, abs: Math.abs, round: Math.round,
  clamp: (v, lo, hi) => Math.min(hi, Math.max(lo, v)),
};
const compiled = new Map();

function evaluate(expr, vars) {
  let fn = compiled.get(expr);
  if (!fn) {
    const js = expr.replace(/\[([A-Z_0-9.]+)\]/g, (_, name) => `V["${name}"]`);
    fn = new Function('V', ...Object.keys(FUNCS), `return (${js});`);
    compiled.set(expr, fn);
  }
  return fn(vars, ...Object.values(FUNCS));
}

function colour(hex) {
  const h = hex.slice(1);
  if (h.length === 6) return `#${h}`;
  return `rgba(${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${parseInt(h.slice(6, 8), 16)},${parseInt(h.slice(0, 2), 16) / 255})`;
}

const num = (el, name, fallback = 0) => (el.hasAttribute(name) ? +el.getAttribute(name) : fallback);
const kids = (el, tag) => [...el.children].filter((c) => c.tagName === tag);

function alphaOf(el, vars) {
  if (vars.ambient) {
    const variant = kids(el, 'Variant').find((v) => v.getAttribute('mode') === 'AMBIENT' && v.getAttribute('target') === 'alpha');
    if (variant) return +variant.getAttribute('value');
  }
  return num(el, 'alpha', 255);
}

function moved(el, target, fallback, vars) {
  const t = kids(el, 'Transform').find((m) => m.getAttribute('target') === target);
  return t ? evaluate(t.getAttribute('value'), vars) : fallback;
}

export async function loadFace(res, fontFamily) {
  const text = await (await fetch(`${res}/raw/watchface.xml`)).text();
  const xml = new DOMParser().parseFromString(text, 'application/xml');
  const names = new Set([...xml.querySelectorAll('Image, Character')].map((e) => e.getAttribute('resource')));
  const images = {};
  await Promise.all([...names].map(async (name) => {
    const img = new Image();
    img.src = `${res}/drawable/${name}.png`;
    await img.decode();
    images[name] = img;
  }));
  const fonts = {};
  for (const font of xml.querySelectorAll('BitmapFont[name]')) {
    fonts[font.getAttribute('name')] = Object.fromEntries(kids(font, 'Character').map((c) => [c.getAttribute('name'),
      {image: images[c.getAttribute('resource')], w: num(c, 'width'), h: num(c, 'height')}]));
  }
  const scene = xml.querySelector('Scene');

  function partImage(c, el, vars) {
    const alpha = moved(el, 'alpha', 255, vars);
    if (alpha <= 0) return;
    const w = num(el, 'width'), h = num(el, 'height');
    const x = moved(el, 'x', num(el, 'x'), vars), y = moved(el, 'y', num(el, 'y'), vars);
    const px = num(el, 'pivotX', 0.5) * w, py = num(el, 'pivotY', 0.5) * h;
    c.save();
    c.globalAlpha = alpha / 255;
    c.translate(x + px, y + py);
    c.rotate((moved(el, 'angle', 0, vars) * Math.PI) / 180);
    c.drawImage(images[kids(el, 'Image')[0].getAttribute('resource')], -px, -py, w, h);
    c.restore();
  }

  function fit(c, line, width) {
    if (c.measureText(line).width <= width) return line;
    let cut = line;
    while (cut && c.measureText(`${cut}…`).width > width) cut = cut.slice(0, -1);
    return `${cut.trimEnd()}…`;
  }

  function partText(c, el, vars) {
    const font = el.querySelector('Font');
    const template = font.querySelector('Template');
    const params = kids(template, 'Parameter').map((p) => evaluate(p.getAttribute('expression'), vars) ?? '');
    let i = 0;
    const line = template.firstChild.nodeValue.replace(/%s|%%/g, (m) => (m === '%%' ? '%' : params[i++]));
    if (!line.trim()) return;
    const x = num(el, 'x'), w = num(el, 'width');
    c.font = `${font.getAttribute('weight') === 'BOLD' ? 700 : 400} ${num(font, 'size')}px "${fontFamily}"`;
    c.fillStyle = colour(font.getAttribute('color'));
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    c.fillText(fit(c, line, w), x + w / 2, num(el, 'y') + num(el, 'height') / 2 + 1);
  }

  function partDraw(c, el, vars) {
    for (const shape of el.children) {
      const stroke = kids(shape, 'Stroke')[0];
      if (shape.tagName === 'Rectangle') {
        c.fillStyle = colour(kids(shape, 'Fill')[0].getAttribute('color'));
        c.fillRect(num(el, 'x') + num(shape, 'x'), num(el, 'y') + num(shape, 'y'), num(shape, 'width'), num(shape, 'height'));
        continue;
      }
      c.beginPath();
      if (shape.tagName === 'Ellipse') {
        c.arc(num(shape, 'x') + num(shape, 'width') / 2, num(shape, 'y') + num(shape, 'height') / 2, num(shape, 'width') / 2, 0, Math.PI * 2);
      } else if (shape.tagName === 'Arc') {
        const start = moved(shape, 'startAngle', num(shape, 'startAngle'), vars);
        const toRad = (deg) => ((deg - 90) * Math.PI) / 180; // the format counts from 12 o'clock, a canvas from 3
        c.arc(num(shape, 'centerX'), num(shape, 'centerY'), num(shape, 'width') / 2, toRad(start), toRad(num(shape, 'endAngle')));
      }
      c.lineWidth = num(stroke, 'thickness');
      c.strokeStyle = colour(stroke.getAttribute('color'));
      c.setLineDash(stroke.hasAttribute('dashIntervals') ? stroke.getAttribute('dashIntervals').split(' ').map(Number) : []);
      c.stroke();
      c.setLineDash([]);
    }
  }

  function clock(c, el, vars) {
    for (const time of kids(el, 'TimeText')) {
      if (alphaOf(time, vars) === 0) continue;
      const font = fonts[kids(time, 'BitmapFont')[0].getAttribute('family')];
      const hh = String(vars.hour).padStart(2, '0'), mm = String(vars.minute).padStart(2, '0');
      const glyphs = [...`${hh}:${mm}`].map((ch) => font[ch]);
      let x = num(el, 'x') + (num(time, 'width') - glyphs.reduce((sum, g) => sum + g.w, 0)) / 2;
      for (const g of glyphs) {
        c.drawImage(g.image, x, num(el, 'y'), g.w, g.h);
        x += g.w;
      }
    }
  }

  function walk(c, el, vars) {
    switch (el.tagName) {
      case 'Scene': case 'Default': case 'Compare':
        for (const child of el.children) walk(c, child, vars);
        break;
      case 'ComplicationSlot': {
        const type = vars['COMPLICATION.RANGED_VALUE_VALUE'] === null ? 'EMPTY' : 'RANGED_VALUE';
        const chosen = kids(el, 'Complication').find((k) => k.getAttribute('type') === type);
        for (const child of chosen.children) walk(c, child, vars);
        break;
      }
      case 'Group':
        if (alphaOf(el, vars) !== 0) for (const child of el.children) walk(c, child, vars);
        break;
      case 'Condition': {
        const exprs = Object.fromEntries(kids(kids(el, 'Expressions')[0], 'Expression').map((e) => [e.getAttribute('name'), e.textContent]));
        const hit = kids(el, 'Compare').find((k) => evaluate(exprs[k.getAttribute('expression')], vars));
        walk(c, hit ?? kids(el, 'Default')[0], vars);
        break;
      }
      case 'PartImage': partImage(c, el, vars); break;
      case 'PartText': partText(c, el, vars); break;
      case 'PartDraw': partDraw(c, el, vars); break;
      case 'DigitalClock': clock(c, el, vars); break;
      default: break;
    }
  }

  function drawFace(c, {value, text: detail, title, hour, minute, seconds, battery, ambient, date = true, dow = 'Sat', day = 7, month = 'Nov'}) {
    const vars = {
      ambient,
      hour,
      minute,
      'COMPLICATION.RANGED_VALUE_VALUE': value,
      'COMPLICATION.TEXT': detail,
      'COMPLICATION.TITLE': title ?? '',
      HOUR_0_23: hour,
      SECOND_MILLISECOND: seconds,
      BATTERY_PERCENT: battery,
      DAY_OF_WEEK_S: date ? dow : '',
      DAY: date ? day : '',
      MONTH_S: date ? month : '',
    };
    c.setTransform(SCALE, 0, 0, SCALE, 0, 0);
    c.imageSmoothingEnabled = false;
    c.fillStyle = '#000';
    c.fillRect(0, 0, 450, 450);
    walk(c, scene, vars);
  }

  // The Sessions screen: same sizes, colours and order as MainActivity.kt
  const STATUS = {working: '#5BC2FF', needs: '#FFC233', done: '#3EE6A0', sleeping: '#A9A4F5'};
  const SPRITE = {working: 'creature_working', needs: 'creature_needs', done: 'creature_done'};
  const WORD = {working: 'Working', needs: 'Needs you', done: 'Your turn'};
  const spriteSize = {working: [42, 48], needs: [56, 48], done: [56, 48]};

  function drawSessions(c, {rows, scroll = 0, rise = 0, alpha = 1, note, reveal = 1}) {
    c.setTransform(SCALE, 0, 0, SCALE, 0, 0);
    c.imageSmoothingEnabled = false;
    c.save();
    c.globalAlpha = alpha;
    c.fillStyle = '#000';
    c.fillRect(0, 0, 450, 450);
    c.translate(0, rise - scroll);
    c.textBaseline = 'middle';
    c.textAlign = 'center';
    c.fillStyle = '#F5F6F8';
    c.font = `700 26px "${fontFamily}"`;
    c.fillText('Sessions', 225, 60);
    let y = 74;
    rows.forEach((row, i) => {
      const k = Math.max(0, Math.min(1, reveal * (rows.length + 1) - i));
      const eased = 1 - (1 - k) ** 3;
      y += 10;
      c.save();
      c.globalAlpha = alpha * eased;
      c.translate(0, (1 - eased) * 26);
      c.fillStyle = '#1C1E23';
      c.beginPath();
      c.roundRect(55, y, 340, 92, 28);
      c.fill();
      const [sw, sh] = spriteSize[row.state];
      c.drawImage(images[SPRITE[row.state]], 75 + (56 - sw) / 2, y + (92 - sh) / 2, sw, sh);
      c.textAlign = 'left';
      c.fillStyle = '#F5F6F8';
      c.font = `700 24px "${fontFamily}"`;
      c.fillText(fit(c, row.name, 280), 145, y + 33);
      c.fillStyle = STATUS[row.state];
      c.font = `400 18px "${fontFamily}"`;
      c.fillText(fit(c, `${WORD[row.state]} · ${row.place} · ${row.age}`, 240), 145, y + 62);
      c.restore();
      y += 92;
    });
    c.textAlign = 'center';
    c.fillStyle = '#B9BEC8';
    c.font = `400 18px "${fontFamily}"`;
    c.fillText(note, 225, y + 26);
    c.restore();
    // Wear OS draws its own scroll bar along the screen's edge
    const height = y + 110, view = 450;
    const start = -38 + (76 * scroll) / Math.max(1, height - view);
    const span = 76 * (view / height);
    c.save();
    c.globalAlpha = alpha;
    c.lineWidth = 6;
    c.lineCap = 'round';
    c.strokeStyle = 'rgba(255,255,255,0.22)';
    c.beginPath();
    c.arc(225, 225, 212, (-38 * Math.PI) / 180, (38 * Math.PI) / 180);
    c.stroke();
    c.strokeStyle = '#F5F6F8';
    c.beginPath();
    c.arc(225, 225, 212, (start * Math.PI) / 180, ((start + span) * Math.PI) / 180);
    c.stroke();
    c.restore();
  }

  return {drawFace, drawSessions};
}
