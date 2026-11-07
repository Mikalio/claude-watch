"""Draws the pixel creature as Android vector drawables for the watch app, from the pixel maps
below. Run it after changing a
map: python tools/sprites.py

Each mood gets its home by night and by day, scene_<mood>.xml and scene_<mood>_day.xml, and its
icon icon_<mood>.xml. Needs you, your turn and out of date are one picture, creature_<mood>.xml.
Sleeping and working are made of the PARTS below, because the tile can only move whole images;
animated images don't play on a tile.
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "watch" / "app" / "src" / "main" / "res" / "drawable"

MOODS = ["sleeping", "working", "needs", "done", "stale"]

# 14 x 12 pixels: O body, L highlight, G leaf, S stem, . empty
BLOB = [
    "......GS......",
    "....OOOOOO....",
    "..OLLOOOOOOO..",
    ".OLOOOOOOOOOO.",
    "OOOOOOOOOOOOOO",
    "OOOOOOOOOOOOOO",
    "OOOOOOOOOOOOOO",
    "OOOOOOOOOOOOOO",
    ".OOOOOOOOOOOO.",
    "..OOOOOOOOOO..",
    "..OO......OO..",
    "..OO......OO..",
]

# Faces as "row,col,colour": D dark, W shine, P cheek
FACES = {
    "needs": "4,3,W 4,4,D 5,3,D 5,4,D 6,3,D 6,4,D 4,9,W 4,10,D 5,9,D 5,10,D 6,9,D 6,10,D "
             "7,2,P 7,11,P 8,6,D 8,7,D 9,6,D 9,7,D",
    "done": "5,4,D 6,3,D 6,5,D 5,9,D 6,8,D 6,10,D 7,2,P 7,11,P 8,5,D 8,8,D 9,6,D 9,7,D",
    "stale": "5,4,D 6,4,D 5,9,D 6,9,D 8,5,D 8,6,D 8,7,D 8,8,D",
}

ACTIVE = {"O": "#F4875A", "L": "#FFB591", "D": "#1A1A1F", "W": "#FFFFFF", "P": "#FF8FA8", "S": "#2E8A47", "G": "#6BD47E"}
PALETTES = {
    "stale": {**ACTIVE, "O": "#7C828D", "L": "#9AA0AA", "P": "#9AA0AA", "S": "#5F646D", "G": "#8A9099"},
}
# m mouth, e f g h sun hat and ribbon, v u nightcap, p q its band and pom-pom
ASLEEP = {**ACTIVE, "O": "#C66F4A", "L": "#DE8E6A", "P": "#E08A86", "S": "#2A6B3E", "G": "#4FA162", "m": "#6E2A22",
          "e": "#EFCF7E", "f": "#FBE7B0", "g": "#C9A255", "h": "#E8574A", "v": "#8C86E0", "u": "#B9B4FA",
          "p": "#E8ECF2", "q": "#B4BAC5"}
# A arm, Y H B R hard hat, T handle, J K N hammer, a b c anvil, w y o sparks
AT_WORK = {**ACTIVE, "A": "#E8744A", "Y": "#FFD23F", "H": "#FFF0A0", "B": "#E0A21B", "R": "#FFE36E", "T": "#B5794A",
           "J": "#E8ECF2", "K": "#B4BAC5", "N": "#7C828D", "a": "#DDE1E8", "b": "#8C919A", "c": "#5F646D",
           "w": "#FFFFFF", "y": "#FFD23F", "o": "#FF8A3D"}

HEADROOM = 4  # empty pixel rows above the creature, so it has room to hop

# Asleep, 20 x 13 pixels, with its legs tucked under, in a sun hat by day and a nightcap at night. Its
# hat and head rise and fall: the top lies behind SLEEP_LOW, which starts at its row 8, so the top's
# last three rows only show as it lifts.
SLEEP_TOP_DAY = [
    ".........GS.........",
    "......ffffeeee......",
    ".....ffeeeeeeee.....",
    ".....feeeeeeeee.....",
    ".....hhhhhhhhhh.....",
    "..feeeeeeeeeeeeeee..",
    "eeeeeeeeeeeeeeeeeeee",
    "..gggggggggggggggg..",
    "...OOOOOOOOOOOOOO...",
    "...OOOOOOOOOOOOOO...",
    "...OOOOOOOOOOOOOO...",
]
SLEEP_TOP_NIGHT = [
    ".........GS.........",
    ".......vvvvvvv......",
    ".....vvuuvvvvvvvv...",
    "....vuuvvvvuuvvvvvv.",
    "....vvvvuuvvvvvuvvvv",
    "...pppppppppppppp.vv",
    "...qqqqqqqqqqqqqq.pp",
    "...OOOOOOOOOOOOOO.pp",
    "...OOOOOOOOOOOOOO...",
    "...OOOOOOOOOOOOOO...",
    "...OOOOOOOOOOOOOO...",
]
SLEEP_LOW = [
    "...OOOOOOOOOOOOOO...",
    "..OODOODOOOODOODOO..",
    "..OOODDOOOOOODDOOO..",
    "..OPPOOOOmmOOOOPPO..",
    "...OOOOOOOOOOOOOO...",
]

# At work, 15 x 12 pixels, in a hard hat with the leaf poking through it, looking at the anvil
WORKER = [
    "......GS.......",
    "....YYRRYY.....",
    "..YHHYRRYYYY...",
    ".YHYYYRRYYYYY..",
    "BBBBBBBBBBBBBBB",
    "OOOOWDOOOOWDOO.",
    "OOOODDOOOODDOO.",
    "OOOPOOOOOOOOPO.",
    ".OOOOOODDOOOO..",
    "..OOOOOOOOOO...",
    "..OO......OO...",
    "..OO......OO...",
]
# The arm and hammer as they strike, from column 13 and row 4 of the worker; they turn at the
# shoulder, the middle of the arm's left end. The anvil's top is at row 9, from column 15.
ARM = [
    "......JKN",
    "......JKN",
    "AAATTTJKN",
    "AAA...JKN",
    "......JKN",
]
ANVIL = [
    "aaaaaaaaa",
    "...bbb...",
    "..ccccc..",
]
# The sparks fly up and out from under the hammer: pixels away from the point of impact, and their colour
SPARKS = [(-4, -1, "w"), (4, -1, "w"), (-3, -3, "y"), (3, -2, "y"), (-5, -2, "o"), (5, -1, "o"),
          (-2, -5, "y"), (2, -5, "o"), (-4, -5, "o"), (-1, -6, "w")]

# The home behind the creature, for a 450 px screen: night sky down to the grass (at 247 px on the
# tile, lower on the watch face), and pixel art at 6 px per pixel starting 27 px in. Rectangles
# are x, y, width, height, colour.
SCENE_W, GROUND, ART_PX, ART_OFF = 450, 247, 6, 27
TALL_STARS = [(8, 3, 1, 1, "star"), (12, -1, 1, 1, "star"), (52, -2, 1, 1, "star"), (55, 4, 1, 1, "star")]
NIGHT_ART = [  # in art pixels: stars and the moon
    (6, 20, 1, 1, "star"), (17, 13, 1, 1, "star"), (22, 13, 1, 1, "star"), (52, 11, 1, 1, "star"),
    (58, 20, 1, 1, "star"),
    (11, 12, 3, 1, "moon"), (10, 13, 3, 1, "moon"), (10, 14, 2, 1, "moon"), (10, 15, 3, 1, "moon"),
    (11, 16, 3, 1, "moon"),
]
DAY_ART = [  # the sun where the moon is, and two clouds
    (11, 12, 3, 1, "sun"), (10, 13, 5, 3, "sun"), (11, 16, 3, 1, "sun"),
    (12, 10, 1, 1, "ray"), (8, 14, 1, 1, "ray"), (16, 14, 1, 1, "ray"), (12, 18, 1, 1, "ray"),
    (9, 11, 1, 1, "ray"), (15, 11, 1, 1, "ray"), (9, 17, 1, 1, "ray"), (15, 17, 1, 1, "ray"),
    (60, 18, 2, 1, "cloud"), (59, 19, 4, 1, "cloud"), (58, 20, 6, 1, "cloudShade"),
    (4, 22, 2, 1, "cloud"), (3, 23, 4, 1, "cloudShade"),
]
GROUND_ART = [  # grass tufts and two flowers
    (4, 29, 1, 1, "grass1"), (29, 29, 1, 1, "grass1"), (51, 29, 1, 1, "grass1"), (56, 29, 1, 1, "grass1"),
    (61, 29, 1, 1, "grass1"),
    (6, 28, 1, 1, "pink"), (6, 29, 1, 1, "grass2"), (9, 28, 1, 1, "yellow"), (9, 29, 1, 1, "grass2"),
]
SMOKE = [(24, 14, 1, 1, "smoke"), (25, 12, 2, 1, "smoke")]  # only while working
HOUSE = [  # in art pixels, from the house's own corner at (12, 16)
    (7, 0, 2, 1, "roof"), (6, 1, 4, 1, "roof"), (11, 1, 2, 2, "chimney"), (5, 2, 6, 1, "roof"),
    (4, 3, 8, 1, "roof"), (3, 4, 10, 1, "roof"), (2, 5, 12, 1, "roof"), (1, 6, 14, 1, "roofShade"),
    (2, 7, 12, 6, "wall"), (2, 13, 12, 1, "wallShade"), (3, 8, 4, 4, "wood"), (4, 9, 2, 2, "win"),
    (9, 9, 3, 5, "wood"), (11, 11, 1, 1, "knob"),
]
NIGHT = {
    "sky1": "#0B1030", "sky2": "#121A47", "sky3": "#1A2660", "grass1": "#46B85E", "grass2": "#2E8A47",
    "star": "#FFF4C2", "moon": "#FFE9A8", "roof": "#EF6B5E", "roofShade": "#B94A48", "chimney": "#A0523D",
    "wall": "#F6E7C8", "wallShade": "#DCC9A2", "wood": "#7A4E34", "knob": "#FFD27A", "pink": "#FF8FC0",
    "yellow": "#FFD27A", "win": "#FFD27A", "smoke": "#B39AA3B5",
    "sun": "#FFD23F", "ray": "#FFE580", "cloud": "#FFFFFF", "cloudShade": "#DCEBFA",
}
DAY = {**NIGHT, "sky1": "#2C7BD4", "sky2": "#4A98E6", "sky3": "#74B6F0", "win": "#BFE3F7", "smoke": "#D9F2F5FA"}
SCENE_PALETTES = {
    "sleeping": {**NIGHT, "win": "#2A3350"},
    "stale": {
        **NIGHT, "sky1": "#101113", "sky2": "#16181C", "sky3": "#1D2026", "grass1": "#5A5F68",
        "grass2": "#464A52", "star": "#6E737C", "moon": "#8C919A", "roof": "#7A7F88", "roofShade": "#5F646D",
        "chimney": "#5F646D", "wall": "#A5AAB3", "wallShade": "#8C919A", "wood": "#5F646D", "knob": "#8C919A",
        "pink": "#8C919A", "yellow": "#8C919A", "win": "#4A4F58", "sun": "#8C919A", "ray": "#6E737C",
        "cloud": "#6E737C", "cloudShade": "#5F646D",
    },
}


def rect_paths(rects, palette, indent):
    """One path per colour, in the order the colours first appear, so later ones draw on top."""
    parts = {}
    for x, y, w, h, colour in rects:
        parts.setdefault(colour, []).append(f"M{x},{y}h{w}v{h}h-{w}z")
    return "\n".join(
        f'{indent}<path android:fillColor="{palette[colour]}" android:pathData="{"".join(p)}" />'
        for colour, p in parts.items()
    )


def scene_rects(mood, day, ground=GROUND, tall=False):
    """The scene's rectangles in px and its palette. A tall scene (the watch face) has more sky and stars."""
    sky = [(0, 0, SCENE_W, ground - 120, "sky1"), (0, ground - 120, SCENE_W, 60, "sky2"),
           (0, ground - 60, SCENE_W, 60, "sky3"), (0, ground, SCENE_W, 6, "grass1"), (0, ground + 6, SCENE_W, 6, "grass2")]
    stars = DAY_ART if day else NIGHT_ART + (TALL_STARS if tall else [])
    art = stars + GROUND_ART + (SMOKE if mood == "working" else []) + [(x + 12, y + 16, w, h, c) for x, y, w, h, c in HOUSE]
    top = ground - 180
    rects = sky + [(ART_OFF + x * ART_PX, top + y * ART_PX, w * ART_PX, h * ART_PX, c) for x, y, w, h, c in art]
    # out of date is grey by day and night; asleep by night has its window dark
    palette = SCENE_PALETTES["stale"] if mood == "stale" else DAY if day else SCENE_PALETTES.get(mood, NIGHT)
    return rects, palette


def scene(mood, day):
    rects, palette = scene_rects(mood, day, tall=True)
    height = GROUND + 12
    return (
        '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        f'    android:width="{SCENE_W / 2}dp" android:height="{height / 2}dp"\n'
        f'    android:viewportWidth="{SCENE_W}" android:viewportHeight="{height}">\n'
        f"{rect_paths(rects, palette, '    ')}\n"
        "</vector>\n"
    )


# The state icons beside the creature: the first frame of each, on an 8 x 10 pixel grid
def z(x, y, c):
    return [(x, y, 3, 1, c), (x + 2, y + 1, 1, 1, c), (x + 1, y + 2, 1, 1, c), (x, y + 3, 3, 1, c)]


def big_z(x, y, c):
    return [(x, y, 5, 1, c), (x + 3, y + 1, 1, 1, c), (x + 2, y + 2, 1, 1, c), (x + 1, y + 3, 1, 1, c), (x, y + 4, 5, 1, c)]


GLASS = [(0, 1, 8, 1), (0, 8, 8, 1), (1, 2, 1, 1), (6, 2, 1, 1), (2, 3, 1, 1), (5, 3, 1, 1), (3, 4, 2, 2),
         (2, 6, 1, 1), (5, 6, 1, 1), (1, 7, 1, 1), (6, 7, 1, 1)]
ICONS = {
    "needs": [(1, 2, 6, 1, "A"), (0, 3, 8, 4, "A"), (1, 7, 6, 1, "A"), (1, 8, 2, 1, "A"), (3, 3, 2, 2, "K"), (3, 6, 2, 1, "K")],
    "working": [(3, 1, 2, 2, "B"), (6, 4, 2, 2, "d"), (3, 7, 2, 2, "d"), (0, 4, 2, 2, "b")],
    "sleeping": z(0, 6, "Z") + big_z(3, 1, "Z"),
    "done": [(0, 4, 5, 1, "M"), (2, 2, 1, 5, "M"), (2, 4, 1, 1, "W"), (5, 8, 3, 1, "m"), (6, 7, 1, 3, "m")],
    "stale": [(x, y, w, h, "G") for x, y, w, h in GLASS] + [(2, 2, 4, 1, "s"), (3, 3, 2, 1, "s")],
}
ICON_COLOURS = {"A": "#FFC233", "K": "#1A1A1F", "B": "#5BC2FF", "b": "#3A86B5", "d": "#1E4561", "Z": "#A9A4F5",
                "M": "#3EE6A0", "m": "#B8FFE0", "W": "#FFFFFF", "G": "#AEB4BE", "s": "#7C828D"}


def icon(mood):
    return (
        '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:width="20dp" android:height="25dp"\n'
        '    android:viewportWidth="8" android:viewportHeight="10">\n'
        f"{rect_paths(ICONS[mood], ICON_COLOURS, '    ')}\n"
        "</vector>\n"
    )


def pixels(mood):
    rows = [list(row) for row in BLOB]
    for spot in FACES[mood].split():
        row, col, colour = spot.split(",")
        rows[int(row)][int(col)] = colour
    return rows


def runs(rows, x0=0, y0=0):
    """Each pixel run of a map as a small rectangle: x, y, width, height, colour."""
    out = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            colour, start = row[x], x
            while x < len(row) and row[x] == colour:
                x += 1
            if colour != ".":
                out.append((x0 + start, y0 + y, x - start, 1, colour))
    return out


def sparks(spread):
    """The burst at this distance from the point of impact, in a picture 14 x 8 from column 14, row 1."""
    return [(round(20 + dx * spread) - 14, round(9 + dy * spread) - 1, 1, 1, c) for dx, dy, c in SPARKS]


# The parts of the two poses that move or rest apart: name, then width and height in pixels, its
# rectangles and its colours. The arm's picture has the shoulder at its centre, so turning it needs
# no pivot. A picture that lifts has room for it above: the jump and the breath are clipped otherwise.
PARTS = {
    "sleep_top_day": (20, 13, runs(SLEEP_TOP_DAY, 0, 2), ASLEEP),
    "sleep_top_night": (20, 13, runs(SLEEP_TOP_NIGHT, 0, 2), ASLEEP),
    "sleep_low": (20, 5, runs(SLEEP_LOW), ASLEEP),
    # whole and at rest, for the Sessions screen, "Not connected" and always-on
    "creature_sleeping_day": (20, 13, runs(SLEEP_TOP_DAY[:8]) + runs(SLEEP_LOW, 0, 8), ASLEEP),
    "creature_sleeping_night": (20, 13, runs(SLEEP_TOP_NIGHT[:8]) + runs(SLEEP_LOW, 0, 8), ASLEEP),
    "creature_working": (15, 12 + HEADROOM, runs(WORKER, 0, HEADROOM), AT_WORK),
    "work_arm": (20, 21, runs(ARM, 10, 8), AT_WORK),
    "anvil": (9, 3, runs(ANVIL), AT_WORK),
    "sparks": (14, 8, sparks(1.15), AT_WORK),
}
# Only the watch face needs these: its sparks grow in two steps, and always-on shows the worker at rest
FACE_PARTS = {
    "sparks_near": (14, 8, sparks(0.7), AT_WORK),
    "working_rest": (24, 12 + HEADROOM, runs(ANVIL, 15, 9 + HEADROOM) + runs(WORKER, 0, HEADROOM) + runs(ARM, 13, 4 + HEADROOM), AT_WORK),
}


def vector(width, height, rects, palette):
    """A picture of this many pixels, at 5 dp per pixel until the tile or a screen sizes it."""
    return (
        f'<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        f'    android:width="{width * 5}dp" android:height="{height * 5}dp"\n'
        f'    android:viewportWidth="{width}" android:viewportHeight="{height}">\n'
        '    <group android:name="body">\n'
        f"{rect_paths(rects, palette, '        ')}\n"
        "    </group>\n"
        "</vector>\n"
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    note = "<!-- Drawn by tools/sprites.py; change the pixel maps there, not here. -->\n"
    written = 0
    for mood in MOODS:
        (OUT / f"scene_{mood}.xml").write_text(note + scene(mood, day=False), encoding="utf-8")
        (OUT / f"scene_{mood}_day.xml").write_text(note + scene(mood, day=True), encoding="utf-8")
        (OUT / f"icon_{mood}.xml").write_text(note + icon(mood), encoding="utf-8")
        written += 3
    for mood in FACES:
        whole = vector(14, 12 + HEADROOM, runs(pixels(mood), 0, HEADROOM), PALETTES.get(mood, ACTIVE))
        (OUT / f"creature_{mood}.xml").write_text(note + whole, encoding="utf-8")
        written += 1
    for name, (width, height, rects, palette) in PARTS.items():
        (OUT / f"{name}.xml").write_text(note + vector(width, height, rects, palette), encoding="utf-8")
        written += 1
    print(f"wrote {written} drawables to {OUT}")


if __name__ == "__main__":
    main()
