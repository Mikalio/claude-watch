"""Writes the Wristling watch face (Watch Face Format): its images and res/raw/watchface.xml, from the
same pixel maps as the tile (tools/sprites.py), laid out for a 450 px screen.
Run it after changing either: python tools/face.py

The face is resource-only, so everything that changes comes from the Wristling complication (the app's
StatusComplicationService): its value is the state as a number (0 sleeping, 1 working, 2 needs you,
3 your turn, 4 out of date), its text the line below the word, and its title the count per state
when several sessions are active. The home shows the day from 06:00 to 18:00. Movement comes from
expressions on the time, since the face has no code: the sleeper's breath and the worker's blows fit
the minute evenly, so they don't skip when it turns over.
The watch's own battery is a short gauge inside the bottom of the ring, with the percent above it.

The design is drawn for a 450 px screen. On any other, the system would scale it and each block's edge would land
between two screen pixels, so the face is written once per round Galaxy Watch size, with every block on whole pixels.
"""

import struct
import zlib
from pathlib import Path

import sprites

RES = Path(__file__).resolve().parent.parent / "watch" / "face" / "src" / "main" / "res"
MOODS = ["sleeping", "working", "needs", "done", "stale"]  # in the order of their numbers
GROUND = 275  # the grass on the face, lower than on the tile: the clock and date sit above
SIZES = [396, 432, 438, 480]  # the other round Galaxy Watch screens, in px; each gets files named _396 and so on
size = 450  # the screen being written
placed = {}  # each image's spot in the design, as the face being written uses it


def at(v):
    """A position or length in the design, in this screen's whole pixels."""
    return int(v * size / 450 + 0.5)


def amount(v):
    """How far something moves in the design, on this screen."""
    return f"{v * size / 450:.5g}"


def named(resource):
    return resource if size == 450 else f"{resource}_{size}"


STATES = {  # word, its colour, its dimmed colour for always-on, the ring's colour
    "sleeping": ("Sleeping", "#A9A4F5", "#7D79BA", "#2E2C4A"),
    "working": ("Working", "#5BC2FF", "#3F86B0", "#5BC2FF"),
    "needs": ("Needs you", "#FFC233", "#B8892A", "#FFC233"),
    "done": ("Your turn", "#3EE6A0", "#2C9E70", "#3EE6A0"),
    "stale": ("Out of date", "#AEB4BE", "#7C828D", "#5A5F69"),
}

# The clock's digits, 5 x 7 pixels at 8 px, with a pixel of space after each
DIGITS = {
    "0": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    ":": [".", "#", ".", ".", ".", "#", "."],
}
DIGIT_PX = 8

# The battery gauge: an arc this far from the centre and this many degrees wide, centred on
# 6 o'clock and filling from left to right, red at LOW_BATTERY percent or less
BATTERY_R, BATTERY_SPAN, LOW_BATTERY = 194, 34, 15
BATTERY = {  # track, fill, fill when low, the percent, the percent when low
    "lit": ("#38FFFFFF", "#F5F6F8", "#FF6B5E", "#F5F6F8", "#FF6B5E"),
    "dim": ("#2A2D33", "#8A9099", "#B0524A", "#7C828D", "#B0524A"),
}


# --- Images -------------------------------------------------------------------------------------

def rgba(colour):
    """#RRGGBB or #AARRGGBB as (r, g, b, a)."""
    h = colour.lstrip("#")
    a = int(h[:2], 16) if len(h) == 8 else 255
    return int(h[-6:-4], 16), int(h[-4:-2], 16), int(h[-2:], 16), a


class Canvas:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.px = bytearray(width * height * 4)

    def rect(self, x, y, w, h, colour):
        r, g, b, a = rgba(colour) if isinstance(colour, str) else colour
        for yy in range(max(0, y), min(self.h, y + h)):
            for xx in range(max(0, x), min(self.w, x + w)):
                i = (yy * self.w + xx) * 4
                if a == 255:
                    self.px[i:i + 4] = bytes((r, g, b, 255))
                else:  # paint over what is there
                    k = a / 255
                    under = self.px[i:i + 4]
                    out_a = a + under[3] * (1 - k)
                    self.px[i:i + 4] = bytes((
                        round(r * k + under[0] * (1 - k)), round(g * k + under[1] * (1 - k)),
                        round(b * k + under[2] * (1 - k)), round(out_a)))

    def paste(self, other, x, y):
        for yy in range(other.h):
            for xx in range(other.w):
                j = (yy * other.w + xx) * 4
                if other.px[j + 3]:
                    self.rect(x + xx, y + yy, 1, 1, tuple(other.px[j:j + 4]))

    def on_screen(self, x, y):
        """This picture, which sits at x, y in the design, on this screen. Each pixel takes the colour under its
        centre, so blocks stay one colour and all the pictures on the face share one grid of whole pixels."""
        left, top = at(x), at(y)
        out = Canvas(at(x + self.w) - left, at(y + self.h) - top)
        for yy in range(out.h):
            row = min(self.h - 1, max(0, int((top + yy + 0.5) * 450 / size) - y))
            for xx in range(out.w):
                column = min(self.w - 1, max(0, int((left + xx + 0.5) * 450 / size) - x))
                j, i = (row * self.w + column) * 4, (yy * out.w + xx) * 4
                out.px[i:i + 4] = self.px[j:j + 4]
        return out

    def save(self, path):
        raw = b"".join(b"\x00" + bytes(self.px[y * self.w * 4:(y + 1) * self.w * 4]) for y in range(self.h))

        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

        path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
                         + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def scene(mood, day):
    rects, palette = sprites.scene_rects(mood, day, ground=GROUND, tall=True)
    c = Canvas(450, GROUND + 12)
    for x, y, w, h, colour in rects:
        c.rect(x, y, w, h, palette[colour])
    return c


def dim(colour):
    r, g, b, a = rgba(colour)
    return round(r * 0.55), round(g * 0.55), round(b * 0.55), a


def creature(mood, dimmed=False):
    palette = sprites.PALETTES.get(mood, sprites.ACTIVE)
    c = Canvas(14 * 7, 12 * 7)
    for y, row in enumerate(sprites.pixels(mood)):
        for x, key in enumerate(row):
            if key != ".":
                c.rect(x * 7, y * 7, 7, 7, dim(palette[key]) if dimmed else palette[key])
    return c


def part(width, height, rects, palette, dimmed=False):
    """One of the two poses' parts from tools/sprites.py, at 7 px per pixel."""
    c = Canvas(width * 7, height * 7)
    for x, y, w, h, key in rects:
        c.rect(x * 7, y * 7, w * 7, h * 7, dim(palette[key]) if dimmed else palette[key])
    return c


def icon(mood):
    c = Canvas(40, 50)
    for x, y, w, h, key in sprites.ICONS[mood]:
        c.rect(x * 5, y * 5, w * 5, h * 5, sprites.ICON_COLOURS[key])
    return c


def digit(char, colour):
    rows = DIGITS[char]
    c = Canvas((len(rows[0]) + 1) * DIGIT_PX, 7 * DIGIT_PX)
    for y, row in enumerate(rows):
        for x, on in enumerate(row):
            if on == "#":
                c.rect(x * DIGIT_PX, y * DIGIT_PX, DIGIT_PX, DIGIT_PX, colour)
    return c


def preview():
    """What the watch's face picker shows: the home at night with the creature needing you."""
    c = Canvas(450, 450)
    c.rect(0, 0, 450, 450, "#000000")
    c.paste(scene("needs", day=False), 0, 0)
    c.paste(creature("needs"), 219, 191)
    c.paste(icon("needs"), 329, 177)
    x = 225 - (4 * 48 + 16 - DIGIT_PX) // 2
    for char in "10:08":
        g = digit(char, "#F5F6F8")
        c.paste(g, x, 67)
        x += g.w
    return c


def name(char):
    return "colon" if char == ":" else char


# --- The face -----------------------------------------------------------------------------------

def is_state(n):
    return f"round([COMPLICATION.RANGED_VALUE_VALUE]) == {n}"


DAY_TIME = "[HOUR_0_23] &gt;= 6 &amp;&amp; [HOUR_0_23] &lt; 18"
T = "[SECOND_MILLISECOND]"
CREATURE_X, CREATURE_Y, ICON_X, ICON_Y = 219, 191, 329, 177
SLEEPER_X, WORKER_X = 198, 212  # a hat's brim and working take more room than standing
SLEEP_ICON_X, SLEEP_ICON_Y = 346, 150  # clear of the hats
WORK_ICON_X, WORK_ICON_Y = 358, 156  # the hammer swings through the usual spot
HAMMER_TOP = -78  # degrees, raised
S = f"({T} % 1)"  # how far into this second: the hammer lands on each one

# Each line of words keeps at least 12 px from the ring; a longer text ends in dots
WORD_X, WORD_W = 55, 340
DETAIL_X, DETAIL_W = 77, 296
COUNTS_X, COUNTS_W = 106, 238


def sleeper(hat):
    """In its sun hat by day and its nightcap at night, with hat and head rising and falling: one breath every 4 s."""
    top_y = GROUND - 105
    breath = f'<Transform target="y" value="{at(top_y)} - {amount(4.375)} * (1 - cos({T} * 1.5708))"/>'
    return [image(f"sleep_top_{hat}", SLEEPER_X, top_y, 140, 91, [breath]),
            image("sleep_low", SLEEPER_X, GROUND - 35, 140, 35)]


def sleeper_at_rest(hat, suffix=""):
    return image(f"creature_sleeping_{hat}{suffix}", SLEEPER_X, GROUND - 91, 140, 91)


def worker():
    """In its hard hat at the anvil: slow raise, fast strike and a small rebound, once a second. The
    sparks come only after the hit and grow in two steps, and the anvil and sparks stay put in the jump."""
    y = GROUND - 112
    raised = f"clamp(({S} - 0.17) / 0.56, 0, 1)"
    strike = f"clamp(({S} - 0.88) / 0.12, 0, 1)"
    rebound = f"12 * sin(3.14159 * clamp(({S} - 0.04) / 0.13, 0, 1))"
    angle = f"{HAMMER_TOP} * {raised} * {raised} * (3 - 2 * {raised}) * (1 - {strike} * {strike}) - {rebound}"
    near = f"round(255 * clamp((0.08 - {S}) * 1000, 0, 1))"
    far = f"round(255 * clamp(({S} - 0.08) * 1000, 0, 1) * clamp((0.2 - {S}) * 1000, 0, 1))"
    # the worker's small jump as it lands
    jump = f'<Transform target="y" value="{at(y)} - {amount(8.4)} * sin(3.14159 * clamp({S} / 0.19, 0, 1))"/>'
    return [image("anvil", WORKER_X + 105, GROUND - 21, 63, 21),
            image("sparks_near", WORKER_X + 98, GROUND - 77, 98, 56, [f'<Transform target="alpha" value="{near}"/>']),
            image("sparks", WORKER_X + 98, GROUND - 77, 98, 56, [f'<Transform target="alpha" value="{far}"/>']),
            image("creature_working", WORKER_X, y, 105, 112, [jump]),
            image("work_arm", WORKER_X + 21, y, 140, 147,
                  [jump, f'<Transform target="angle" value="{angle}"/>'], ' pivotX="0.5" pivotY="0.5"')]


def creature_moves(mood):
    """The creature hops when it needs you and dances on your turn: sways, bobs and tilts."""
    if mood == "needs":
        return [f'<Transform target="y" value="{at(CREATURE_Y)} - {amount(28)} * abs(sin({T} * 4.76))"/>']
    if mood == "done":
        return [f'<Transform target="x" value="{at(CREATURE_X)} + {amount(7)} * sin({T} * 7.14)"/>',
                f'<Transform target="y" value="{at(CREATURE_Y)} - {amount(7)} * abs(sin({T} * 7.14))"/>',
                f'<Transform target="angle" value="6 * sin({T} * 7.14)"/>']
    return []


def icon_moves(mood):
    """The bubble bounces, the spinner turns, the Zs float, the sparkles twinkle."""
    return {
        "needs": [f'<Transform target="y" value="{at(ICON_Y)} - {amount(5)} * abs(sin({T} * 3.93))"/>'],
        "working": [f'<Transform target="angle" value="({T} * 562.5) % 360"/>'],
        "sleeping": [f'<Transform target="y" value="{at(SLEEP_ICON_Y)} - {amount(5)} * abs(sin({T} * 1.57))"/>'],
        "done": [f'<Transform target="alpha" value="round(155 + 100 * abs(sin({T} * 3.5)))"/>'],
    }.get(mood, [])


def image(resource, x, y, w, h, moves=(), pivot=""):
    inner = "".join(moves)
    placed[resource] = (x, y)
    return (f'<PartImage x="{at(x)}" y="{at(y)}" width="{at(x + w) - at(x)}" height="{at(y + h) - at(y)}"{pivot}>'
            f'<Image resource="{named(resource)}"/>{inner}</PartImage>')


def text(x, y, w, h, font, colour, template, params=(), bold=False):
    """A centred line. A template needs at least one parameter, so fixed words become a quoted one."""
    if not params:
        template, params = "%s", (f"&quot;{template}&quot;",)
    weight = ' weight="BOLD"' if bold else ""
    p = "".join(f'<Parameter expression="{e}"/>' for e in params)
    return (f'<PartText x="{at(x)}" y="{at(y)}" width="{at(x + w) - at(x)}" height="{at(y + h) - at(y)}"><Text align="CENTER" ellipsis="TRUE">'
            f'<Font family="SYNC_TO_DEVICE" size="{at(font)}" color="{colour}"{weight}>'
            f'<Template>{template}{p}</Template></Font></Text></PartText>')


def ring(mood):
    dashes = f' dashIntervals="{at(12)} {at(12)}"' if mood == "stale" else ""
    inside = size - 2 * at(9)
    return (f'<PartDraw x="0" y="0" width="{size}" height="{size}"><Ellipse x="{at(9)}" y="{at(9)}" width="{inside}" height="{inside}">'
            f'<Stroke color="{STATES[mood][3]}" thickness="{at(6)}"{dashes}/></Ellipse></PartDraw>')


def gauge_arc(colour, level=None):
    """The battery gauge's track, or with a level (0 to 100) the part of it that is filled."""
    half, d = BATTERY_SPAN // 2, 2 * at(BATTERY_R)
    # An arc runs clockwise, which is right to left at the bottom: the left end stays and the start moves
    right, left = 180 - half, 180 + half
    fill = (f'<Transform target="startAngle" value="{left} - {BATTERY_SPAN} * clamp({level}, 0, 100) / 100"/>'
            if level else "")
    return (f'<PartDraw x="0" y="0" width="{size}" height="{size}"><Arc centerX="{size // 2}" centerY="{size // 2}" width="{d}" '
            f'height="{d}" startAngle="{right}" endAngle="{left}"><Stroke color="{colour}" thickness="{at(6)}"/>{fill}'
            f'</Arc></PartDraw>')


def battery(look):
    """The gauge and the percent above it, lit or dimmed for always-on."""
    track, fill, fill_low, words, words_low = BATTERY[look]
    level = "[BATTERY_PERCENT]"

    def reading(arc_colour, text_colour):
        return [gauge_arc(arc_colour, level), text(175, 390, 100, 24, 20, text_colour, "%s%%", (level,))]

    return gauge_arc(track) + condition([(f"{level} &lt;= {LOW_BATTERY}", reading(fill_low, words_low))],
                                        reading(fill, words))


def condition(cases, default):
    """A Condition that shows the first matching case: [(expression, [elements])]."""
    exprs = "".join(f'<Expression name="e{i}">{e}</Expression>' for i, (e, _) in enumerate(cases))
    compares = "".join(f'<Compare expression="e{i}">{"".join(els)}</Compare>' for i, (_, els) in enumerate(cases))
    return f"<Condition><Expressions>{exprs}</Expressions>{compares}<Default>{''.join(default)}</Default></Condition>"


def lit_state(mood, hat):
    word, colour, _, _ = STATES[mood]
    if mood == "sleeping":
        body = sleeper(hat)
    elif mood == "working":
        body = worker()
    else:
        body = [image(f"creature_{mood}", CREATURE_X, CREATURE_Y, 98, 84, creature_moves(mood), ' pivotX="0.5" pivotY="1"')]
    icon_x, icon_y = {"working": (WORK_ICON_X, WORK_ICON_Y), "sleeping": (SLEEP_ICON_X, SLEEP_ICON_Y)}.get(mood, (ICON_X, ICON_Y))
    return [
        ring(mood),
        *body,
        image(f"icon_{mood}", icon_x, icon_y, 40, 50, icon_moves(mood), ' pivotX="0.5" pivotY="0.5"'),
        text(WORD_X, 291, WORD_W, 40, 36, colour, word, bold=True),
    ]


def dim_state(mood, hat):
    word, _, dim_colour, _ = STATES[mood]
    if mood == "sleeping":
        body = sleeper_at_rest(hat, "_dim")
    elif mood == "working":
        body = image("working_rest_dim", WORKER_X, GROUND - 112, 168, 112)
    else:
        body = image(f"creature_{mood}_dim", CREATURE_X, CREATURE_Y, 98, 84)
    return [body, text(WORD_X, 291, WORD_W, 40, 36, dim_colour, word, bold=True)]


def scene_image(mood, day):
    return image(f"scene_{mood}_{'day' if day else 'night'}", 0, 0, 450, GROUND + 12)


def by_state(draw):
    """One case per state; asleep, the first case wears the day's hat and the others the night's."""
    return condition([(f"{is_state(0)} &amp;&amp; {DAY_TIME}", draw("sleeping", "day")),
                      *((is_state(n), draw(m, "night")) for n, m in enumerate(MOODS))],
                     draw("sleeping", "night"))


def watchface():
    scenes = condition(
        [(f"{is_state(n)} &amp;&amp; {DAY_TIME}" if day else is_state(n), [scene_image(m, day)])
         for n, m in enumerate(MOODS) for day in (True, False)],
        [scene_image("sleeping", False)])
    lit = by_state(lit_state)
    dimmed = by_state(dim_state)
    detail = ("[COMPLICATION.TEXT]",)
    counts = ("[COMPLICATION.TITLE]",)
    empty_scene = condition([(DAY_TIME, [scene_image("sleeping", True), sleeper_at_rest("day")])],
                            [scene_image("sleeping", False), sleeper_at_rest("night")])
    chars = list(DIGITS)
    fonts = "".join(
        f'<BitmapFont name="{font}">'
        + "".join(f'<Character name="{c}" resource="{named(prefix + name(c))}" width="{at((len(DIGITS[c][0]) + 1) * DIGIT_PX)}" '
                  f'height="{at(7 * DIGIT_PX)}"/>' for c in chars)
        + "</BitmapFont>"
        for font, prefix in (("pixel", "digit_"), ("pixel_dim", "digit_dim_")))
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Written by tools/face.py; change it there, not here. -->
<WatchFace width="{size}" height="{size}">
  <Metadata key="CLOCK_TYPE" value="DIGITAL"/>
  <Metadata key="PREVIEW_TIME" value="10:08:32"/>
  <BitmapFonts>{fonts}</BitmapFonts>
  <Scene backgroundColor="#FF000000">
    <ComplicationSlot slotId="0" x="0" y="0" width="{size}" height="{size}" displayName="claude_slot" supportedTypes="RANGED_VALUE EMPTY" isCustomizable="TRUE">
      <DefaultProviderPolicy defaultSystemProvider="EMPTY" defaultSystemProviderType="EMPTY" primaryProvider="io.github.mikalio.wristling/io.github.mikalio.wristling.StatusComplicationService" primaryProviderType="RANGED_VALUE"/>
      <BoundingOval x="0" y="0" width="{size}" height="{size}"/>
      <Complication type="RANGED_VALUE">
        <Group name="lit" x="0" y="0" width="{size}" height="{size}">
          <Variant mode="AMBIENT" target="alpha" value="0"/>
          {scenes}
          {lit}
          {text(DETAIL_X, 333, DETAIL_W, 28, 22, "#F5F6F8", "%s", detail)}
          {text(COUNTS_X, 361, COUNTS_W, 26, 20, "#D5D8DF", "%s", counts)}
        </Group>
        <Group name="dim" x="0" y="0" width="{size}" height="{size}" alpha="0">
          <Variant mode="AMBIENT" target="alpha" value="255"/>
          <PartDraw x="{at(67)}" y="{at(GROUND)}" width="{size - 2 * at(67)}" height="{at(3)}"><Rectangle x="0" y="0" width="{size - 2 * at(67)}" height="{at(3)}"><Fill color="#2A2D33"/></Rectangle></PartDraw>
          {dimmed}
          {text(DETAIL_X, 333, DETAIL_W, 28, 22, "#8A9099", "%s", detail)}
        </Group>
      </Complication>
      <Complication type="EMPTY">
        <Group name="setup" x="0" y="0" width="{size}" height="{size}">
          <Variant mode="AMBIENT" target="alpha" value="0"/>
          {empty_scene}
          {text(WORD_X, 291, WORD_W, 40, 30, "#F5F6F8", "Not connected", bold=True)}
          {text(DETAIL_X, 333, DETAIL_W, 28, 20, "#B9BEC8", "Hold the face, pick Wristling")}
        </Group>
      </Complication>
    </ComplicationSlot>
    <DigitalClock x="{at(75)}" y="{at(67)}" width="{size - 2 * at(75)}" height="{at(56)}">
      <TimeText format="hh:mm" hourFormat="24" align="CENTER" x="0" y="0" width="{size - 2 * at(75)}" height="{at(56)}">
        <Variant mode="AMBIENT" target="alpha" value="0"/>
        <BitmapFont family="pixel" size="{at(56)}"/>
      </TimeText>
    </DigitalClock>
    <DigitalClock x="{at(75)}" y="{at(67)}" width="{size - 2 * at(75)}" height="{at(56)}">
      <TimeText format="hh:mm" hourFormat="24" align="CENTER" x="0" y="0" width="{size - 2 * at(75)}" height="{at(56)}" alpha="0">
        <Variant mode="AMBIENT" target="alpha" value="255"/>
        <BitmapFont family="pixel_dim" size="{at(56)}"/>
      </TimeText>
    </DigitalClock>
    <Group name="date" x="0" y="0" width="{size}" height="{size}">
      <Variant mode="AMBIENT" target="alpha" value="0"/>
      {text(75, 127, 300, 24, 22, "#B9BEC8", "%s %s %s", ("[DAY_OF_WEEK_S]", "[DAY]", "[MONTH_S]"))}
    </Group>
    <Group name="date_dim" x="0" y="0" width="{size}" height="{size}" alpha="0">
      <Variant mode="AMBIENT" target="alpha" value="255"/>
      {text(75, 127, 300, 24, 22, "#7C828D", "%s %s %s", ("[DAY_OF_WEEK_S]", "[DAY]", "[MONTH_S]"))}
    </Group>
    <Group name="battery" x="0" y="0" width="{size}" height="{size}">
      <Variant mode="AMBIENT" target="alpha" value="0"/>
      {battery("lit")}
    </Group>
    <Group name="battery_dim" x="0" y="0" width="{size}" height="{size}" alpha="0">
      <Variant mode="AMBIENT" target="alpha" value="255"/>
      {battery("dim")}
    </Group>
  </Scene>
</WatchFace>
"""


def pictures():
    """Every picture of the face, as drawn for 450 px, by name."""
    art = {}
    for mood in MOODS:
        art[f"scene_{mood}_night"] = scene(mood, day=False)
        art[f"scene_{mood}_day"] = scene(mood, day=True)
        art[f"icon_{mood}"] = icon(mood)
    for mood in sprites.FACES:
        art[f"creature_{mood}"] = creature(mood)
        art[f"creature_{mood}_dim"] = creature(mood, dimmed=True)
    for picture, shape in {**sprites.PARTS, **sprites.FACE_PARTS}.items():
        if picture != "working_rest":
            art[picture] = part(*shape)
    for hat in ("day", "night"):
        art[f"creature_sleeping_{hat}_dim"] = part(*sprites.PARTS[f"creature_sleeping_{hat}"], dimmed=True)
    art["working_rest_dim"] = part(*sprites.FACE_PARTS["working_rest"], dimmed=True)
    for char in DIGITS:
        art[f"digit_{name(char)}"] = digit(char, "#F5F6F8")
        art[f"digit_dim_{name(char)}"] = digit(char, "#C8CCD4")
    return art


def main():
    global size
    drawable, raw = RES / "drawable", RES / "raw"
    drawable.mkdir(parents=True, exist_ok=True)
    raw.mkdir(exist_ok=True)
    (RES / "xml").mkdir(exist_ok=True)
    art = pictures()
    for picture, canvas in art.items():
        canvas.save(drawable / f"{picture}.png")
    preview().save(drawable / "preview.png")
    (raw / "watchface.xml").write_text(watchface(), encoding="utf-8")

    for size in SIZES:
        placed.clear()
        (raw / f"watchface_{size}.xml").write_text(watchface(), encoding="utf-8")
        digits = {picture: (0, 0) for picture in art if picture.startswith("digit_")}
        for picture, (x, y) in {**digits, **placed}.items():
            art[picture].on_screen(x, y).save(drawable / f"{named(picture)}.png")
    size = 450

    shapes = "".join(f'    <WatchFace shape="CIRCLE" width="{s}" height="{s}" file="@raw/watchface{"" if s == 450 else f"_{s}"}"/>\n'
                     for s in sorted([*SIZES, 450]))
    (RES / "xml" / "watch_face_shapes.xml").write_text(
        f'<?xml version="1.0" encoding="utf-8"?>\n<!-- Written by tools/face.py -->\n<WatchFaces>\n{shapes}</WatchFaces>\n', encoding="utf-8")
    print(f"wrote the face to {RES}")


if __name__ == "__main__":
    main()
